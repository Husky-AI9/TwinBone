from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from scripts.seed import SEED_FILE, execute_sql_file
from services.api.app.auth import AccessScope
from services.api.app.db.vector import EMBEDDING_DIMENSIONS
from services.api.app.models import UserRole, VerificationStatus
from services.api.app.repositories import MemoryRepository, SubjectRepository

pytestmark = pytest.mark.integration

TENANT_ID = UUID("10000000-0000-4000-8000-000000000001")
CLINICIAN_ID = UUID("20000000-0000-4000-8000-000000000002")
SUBJECT_ID = UUID("30000000-0000-4000-8000-000000000001")


def _embedding(axis: int) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[axis] = 1.0
    return values


def _create_subject(engine: Engine, *, tenant_id: UUID = TENANT_ID) -> AccessScope:
    subject_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO subjects (id, tenant_id, pseudonym, status)
                VALUES (:id, :tenant_id, :pseudonym, 'ACTIVE')
                """
            ),
            {
                "id": subject_id,
                "tenant_id": tenant_id,
                "pseudonym": f"SYNTH-{subject_id}",
            },
        )
    return AccessScope(
        tenant_id=tenant_id,
        subject_id=subject_id,
        role=UserRole.CLINICIAN,
    )


def test_migrations_apply_from_zero_and_seed_is_idempotent(database_engine: Engine) -> None:
    with database_engine.begin() as connection:
        execute_sql_file(connection, SEED_FILE)
        execute_sql_file(connection, SEED_FILE)

    with database_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        table_names = set(
            connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            ).scalars()
        )
        vector_index = connection.execute(
            text(
                """
                SELECT count(*)
                FROM information_schema.statistics
                WHERE table_name = 'memories'
                  AND index_name = 'memories_subject_embedding_idx'
                """
            )
        ).scalar_one()
        seed_counts = connection.execute(
            text(
                """
                SELECT
                    (SELECT count(*) FROM tenants),
                    (SELECT count(*) FROM app_users),
                    (SELECT count(*) FROM subjects)
                """
            )
        ).one()

    assert revision == "0004_durable_workflow_state"
    assert {
        "tenants",
        "app_users",
        "subjects",
        "documents",
        "scan_reports",
        "measurements",
        "treatment_events",
        "memories",
        "memory_relations",
        "agent_runs",
        "agent_run_memories",
        "review_tasks",
        "review_events",
        "consent_records",
        "audit_events",
    } <= table_names
    assert vector_index >= 1
    assert seed_counts == (1, 2, 1)


def test_vector_similarity_is_subject_scoped(database_engine: Engine) -> None:
    repository = MemoryRepository()
    target_scope = _create_subject(database_engine)
    other_scope = _create_subject(database_engine)

    with database_engine.begin() as connection:
        expected = repository.add(
            connection,
            target_scope,
            title="Synthetic hip timeline",
            content="Synthetic left total hip measurement prepared for review.",
            embedding=_embedding(0),
            source_id=uuid4(),
        )
        repository.add(
            connection,
            target_scope,
            title="Synthetic unrelated site",
            content="Synthetic forearm measurement prepared for review.",
            embedding=_embedding(1),
            source_id=uuid4(),
        )
        forbidden = repository.add(
            connection,
            other_scope,
            title="Cross-subject similarity trap",
            content="Synthetic record that must never cross the subject boundary.",
            embedding=_embedding(0),
            source_id=uuid4(),
        )

    with database_engine.connect() as connection:
        nearest = repository.nearest(connection, target_scope, _embedding(0))
        leaked = repository.get(connection, target_scope, forbidden.id)

    assert nearest[0].memory.id == expected.id
    assert nearest[0].cosine_distance == pytest.approx(0.0)
    assert all(item.memory.subject_id == target_scope.subject_id for item in nearest)
    assert leaked is None


def test_subject_repository_denies_cross_tenant_scope(database_engine: Engine) -> None:
    other_tenant = uuid4()
    other_subject = uuid4()
    with database_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO tenants (id, name) VALUES (:id, 'Synthetic Isolation Tenant')"),
            {"id": other_tenant},
        )
        connection.execute(
            text(
                """
                INSERT INTO subjects (id, tenant_id, pseudonym)
                VALUES (:id, :tenant_id, 'SYNTH-ISOLATION')
                """
            ),
            {"id": other_subject, "tenant_id": other_tenant},
        )

    forged_scope = AccessScope(
        tenant_id=TENANT_ID,
        subject_id=other_subject,
        role=UserRole.CLINICIAN,
    )
    with database_engine.connect() as connection:
        result = SubjectRepository().get(connection, forged_scope)
    assert result is None


def test_duplicate_document_hash_is_rejected(database_engine: Engine) -> None:
    values = {
        "tenant_id": TENANT_ID,
        "subject_id": SUBJECT_ID,
        "created_by": CLINICIAN_ID,
        "sha256": "a" * 64,
    }
    insert = text(
        """
        INSERT INTO documents (
            tenant_id, subject_id, status, original_filename, content_type,
            byte_size, sha256, upload_idempotency_key, created_by
        ) VALUES (
            :tenant_id, :subject_id, 'UPLOADED', 'synthetic-dxa.pdf',
            'application/pdf', 1024, :sha256, :idempotency_key, :created_by
        )
        """
    )
    with database_engine.begin() as connection:
        connection.execute(insert, values | {"idempotency_key": f"upload-{uuid4()}"})

    with pytest.raises(IntegrityError), database_engine.begin() as connection:
        connection.execute(insert, values | {"idempotency_key": f"upload-{uuid4()}"})


def test_concurrent_corrections_leave_one_active_verified_memory(
    database_engine: Engine,
) -> None:
    repository = MemoryRepository()
    scope = _create_subject(database_engine)
    source_id = uuid4()
    with database_engine.begin() as connection:
        original = repository.add(
            connection,
            scope,
            title="Synthetic lumbar comparison instruction",
            content="Include the synthetic lumbar measurement.",
            embedding=_embedding(2),
            source_id=source_id,
        )

    barrier = Barrier(2)

    def correct(index: int) -> UUID:
        barrier.wait(timeout=10)
        corrected = repository.correct(
            database_engine,
            scope,
            original.id,
            corrected_title=f"Synthetic verified correction {index}",
            corrected_content=f"Exclude synthetic lumbar measurement revision {index}.",
            embedding=_embedding(3 + index),
            reviewer_user_id=CLINICIAN_ID,
            request_id=uuid4(),
        )
        return corrected.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        corrected_ids = list(executor.map(correct, (0, 1)))

    with database_engine.connect() as connection:
        chain = (
            connection.execute(
                text(
                    """
                SELECT id, verification_status, supersedes_id, superseded_by_id
                FROM memories
                WHERE tenant_id = :tenant_id
                  AND subject_id = :subject_id
                  AND source_id = :source_id
                """
                ),
                {
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "source_id": source_id,
                },
            )
            .mappings()
            .all()
        )

    active = [
        row
        for row in chain
        if row["verification_status"] == VerificationStatus.VERIFIED.value
        and row["superseded_by_id"] is None
    ]
    assert len(set(corrected_ids)) == 2
    assert len(chain) == 3
    assert len(active) == 1
    assert sum(row["verification_status"] == "SUPERSEDED" for row in chain) == 2
