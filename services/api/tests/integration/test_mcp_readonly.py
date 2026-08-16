from __future__ import annotations

from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import Engine, text

from scripts.check_mcp_readonly import MCP_VIEWS, audit_mcp_boundary
from services.api.app.auth import AccessScope
from services.api.app.config import get_settings
from services.api.app.models import UserRole
from services.api.app.repositories import MemoryRepository

pytestmark = pytest.mark.integration

TENANT_ID = UUID("10000000-0000-4000-8000-000000000001")
SUBJECT_ID = UUID("30000000-0000-4000-8000-000000000001")
CLINICIAN_ID = UUID("20000000-0000-4000-8000-000000000002")
MCP_TEST_USER = "bonetwin_mcp_test"


def _embedding() -> list[float]:
    return [1.0] + [0.0] * 1023


def test_mcp_views_are_demo_scoped_and_exclude_sensitive_columns(
    database_engine: Engine,
) -> None:
    scope = AccessScope(
        tenant_id=TENANT_ID,
        subject_id=SUBJECT_ID,
        role=UserRole.CLINICIAN,
    )
    run_id = uuid4()
    task_id = uuid4()
    with database_engine.begin() as connection:
        memory = MemoryRepository().add(
            connection,
            scope,
            title="Synthetic verified correction for MCP trace",
            content="Sensitive evidence content must not appear in the MCP view.",
            embedding=_embedding(),
            source_id=uuid4(),
        )
        connection.execute(
            text(
                """
                INSERT INTO agent_runs (
                    id, tenant_id, subject_id, user_id, request_type, user_query,
                    model_id, prompt_version, run_idempotency_key, status,
                    response_summary, uncertainty, completed_at
                ) VALUES (
                    :id, :tenant_id, :subject_id, :user_id, 'COMPARE_REPORTS',
                    'Synthetic MCP verification query', 'deterministic-local',
                    'system-v1', :key, 'SUCCEEDED', 'Synthetic summary',
                    'Source context needs review', now()
                )
                """
            ),
            {
                "id": run_id,
                "tenant_id": TENANT_ID,
                "subject_id": SUBJECT_ID,
                "user_id": CLINICIAN_ID,
                "key": f"mcp-run-{uuid4()}",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO agent_run_memories (
                    agent_run_id, memory_id, vector_distance, trust_score,
                    retrieval_rank, disposition, disposition_reason
                ) VALUES (
                    :run_id, :memory_id, 0, 1, 1, 'USED', NULL
                )
                """
            ),
            {"run_id": run_id, "memory_id": memory.id},
        )
        connection.execute(
            text(
                """
                INSERT INTO review_tasks (
                    id, tenant_id, subject_id, agent_run_id, action_type, status,
                    title, proposed_payload, action_idempotency_key
                ) VALUES (
                    :id, :tenant_id, :subject_id, :run_id,
                    'CREATE_CLINICIAN_REVIEW', 'AWAITING_REVIEW',
                    'Synthetic MCP review task', '{}'::JSONB, :key
                )
                """
            ),
            {
                "id": task_id,
                "tenant_id": TENANT_ID,
                "subject_id": SUBJECT_ID,
                "run_id": run_id,
                "key": f"mcp-task-{uuid4()}",
            },
        )

    with database_engine.connect() as connection:
        summary = audit_mcp_boundary(connection)
        memory_row = connection.execute(
            text(
                """
                SELECT memory_id, title, verification_status
                FROM mcp_subject_memory_trace
                WHERE memory_id = :memory_id
                """
            ),
            {"memory_id": memory.id},
        ).one()
        run_row = connection.execute(
            text(
                """
                SELECT run_id, memory_id, disposition
                FROM mcp_agent_run_trace
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        ).one()
        task_row = connection.execute(
            text(
                """
                SELECT task_id, title, status
                FROM mcp_open_review_tasks
                WHERE task_id = :task_id
                """
            ),
            {"task_id": task_id},
        ).one()

    views = summary["views"]
    assert isinstance(views, list)
    assert set(views) == MCP_VIEWS
    assert memory_row[0] == memory.id
    assert run_row == (run_id, memory.id, "USED")
    assert task_row[0] == task_id


def test_mcp_role_can_read_curated_views_but_cannot_write(
    database_engine: Engine,
) -> None:
    with database_engine.begin() as connection:
        connection.execute(text(f"CREATE USER IF NOT EXISTS {MCP_TEST_USER}"))
        connection.execute(text(f"GRANT bonetwin_mcp_reader TO {MCP_TEST_USER}"))

    database_url = get_settings().reveal_database_url()
    reader_url = database_url.replace("root@", f"{MCP_TEST_USER}@", 1)
    with (
        psycopg.connect(reader_url, autocommit=True) as reader_connection,
        reader_connection.cursor() as cursor,
    ):
        cursor.execute("SELECT count(*) FROM mcp_subject_memory_trace")
        assert cursor.fetchone() is not None
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cursor.execute("SELECT content FROM memories LIMIT 1")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cursor.execute(
                """
                INSERT INTO subjects (tenant_id, pseudonym)
                VALUES (
                    '10000000-0000-4000-8000-000000000001',
                    'SYNTH-MCP-WRITE-MUST-FAIL'
                )
                """
            )
