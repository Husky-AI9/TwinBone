from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import Engine, text

from services.agent.bonetwin_agent.bedrock import BedrockDecisionContext, BedrockRuntime
from services.agent.bonetwin_agent.policies.safety import SAFETY_NOTICE
from services.agent.bonetwin_agent.schemas import AgentDecision, EvidenceReference, ProposedAction
from services.agent.bonetwin_agent.trust import deterministic_embedding
from services.api.app.auth import DEMO_SUBJECT_ID
from services.api.app.auth.principal import DEMO_PRINCIPALS
from services.api.app.config import Settings
from services.api.app.schemas import ReviewDecisionRequest, UploadIntentRequest
from services.api.app.services.cockroach_store import CockroachWorkflowStore
from services.api.app.services.document_storage import RawDocumentReference, UploadTarget
from services.api.app.services.synthetic_seed import seed_synthetic_workflow

pytestmark = pytest.mark.integration


class StubLiveBedrockRuntime(BedrockRuntime):
    def __init__(self) -> None:
        self.chat_model_id = "stub-live-chat-model"
        self.embedding_model_id = "amazon.titan-embed-text-v2:0"
        self.embed_calls = 0
        self.decision_calls = 0

    def embed(self, text: str) -> list[float]:
        self.embed_calls += 1
        return deterministic_embedding(text)

    def decide(self, context: BedrockDecisionContext) -> AgentDecision:
        self.decision_calls += 1
        primary = next(item for item in context.evidence if item.disposition != "EXCLUDED")
        return AgentDecision(
            summary="Bedrock organized the synthetic measurements for human review.",
            uncertainty="Scanner context requires human confirmation.",
            safety_notice=SAFETY_NOTICE,
            evidence=[
                EvidenceReference(
                    memory_id=primary.memory_id,
                    source_type=primary.source_type,
                    role="PRIMARY",
                )
            ],
            proposed_action=ProposedAction(
                action_type=(
                    "NO_ACTION" if context.prior_review_applied else "CREATE_CLINICIAN_REVIEW"
                ),
                title="Review synthetic scanner context",
                rationale="Source scanner metadata requires confirmation.",
                payload={"focus": "scanner metadata"},
                requires_human_approval=not context.prior_review_applied,
            ),
            memory_impact_statement="Verified durable evidence changed the comparison context.",
            counterfactual_without_key_memory="The excluded lumbar evidence might be compared.",
        )


class DirectUploadStore:
    """S3-shaped storage double that bypasses FastAPI's local PUT route."""

    def __init__(self) -> None:
        self.content: dict[UUID, bytes] = {}
        self.deleted: set[UUID] = set()

    @property
    def label(self) -> str:
        return "s3-kms"

    def reference(self, document_id: UUID) -> RawDocumentReference:
        return RawDocumentReference(
            bucket="synthetic-integration-bucket",
            key=f"bonetwin/raw-local/{document_id}.upload",
        )

    def upload_target(
        self,
        document_id: UUID,
        *,
        content_type: str,
        sha256_hex: str,
    ) -> UploadTarget:
        del content_type, sha256_hex
        return UploadTarget(
            url=f"https://synthetic-integration-bucket.s3.amazonaws.com/{document_id}",
            headers={"x-amz-server-side-encryption": "aws:kms"},
            expires_in_seconds=900,
        )

    def accept_local(self, document_id: UUID, content: bytes) -> None:
        del document_id, content
        raise AssertionError("direct S3 uploads must not use the local PUT adapter")

    def read(self, document_id: UUID) -> bytes:
        return self.content[document_id]

    def delete(self, document_id: UUID) -> None:
        self.content.pop(document_id, None)
        self.deleted.add(document_id)


def test_local_vertical_slice_survives_store_restart(
    database_engine: Engine,
    tmp_path: Path,
) -> None:
    clinician = DEMO_PRINCIPALS["demo-clinician"]
    with database_engine.begin() as connection:
        seed_synthetic_workflow(connection)

    content = (
        Path(__file__).resolve().parents[4] / "output" / "pdf" / "bonetwin-demo-dxa-2026.pdf"
    ).read_bytes()
    digest = sha256(content).hexdigest()
    store = CockroachWorkflowStore(database_engine, upload_directory=tmp_path)
    intent = store.create_upload_intent(
        UploadIntentRequest(
            original_filename="bonetwin-demo-dxa-2026.pdf",
            content_type="application/pdf",
            byte_size=len(content),
            sha256=digest,
        ),
        "persistent-upload-0001",
        clinician,
    )
    uploaded = store.accept_local_upload(
        intent.document_id,
        content,
        "persistent-bytes-0001",
        clinician,
    )
    assert uploaded.status == "UPLOADED"

    ready = store.complete_upload(
        intent.document_id,
        "persistent-complete-0001",
        clinician,
    )
    assert ready.status == "READY"
    assert ready.report is not None
    assert len(ready.report.measurements) == 3
    assert list(tmp_path.glob("*.upload")) == []
    replayed_completion = store.complete_upload(
        intent.document_id,
        "persistent-complete-0001",
        clinician,
    )
    assert replayed_completion.report == ready.report
    replayed_bytes = store.accept_local_upload(
        intent.document_id,
        content,
        "persistent-bytes-0001",
        clinician,
    )
    assert replayed_bytes.status == "READY"
    assert list(tmp_path.glob("*.upload")) == []

    first_run = store.run_agent(
        principal=clinician,
        request_type="COMPARE_REPORTS",
        query="Compare the synthetic reports using trusted memory.",
        idempotency_key="persistent-run-0001",
    )
    assert first_run.persisted_review_applied is False
    assert first_run.review_task_id is not None
    task = store.resolve_task(
        first_run.review_task_id,
        decision="approve",
        payload=ReviewDecisionRequest(note="Synthetic clinician approval"),
        idempotency_key="persistent-review-0001",
        principal=clinician,
    )
    assert task.status == "APPLIED"
    assert (
        store.resolve_task(
            task.id,
            decision="approve",
            payload=ReviewDecisionRequest(note="Replay must not duplicate memory"),
            idempotency_key="persistent-review-0001",
            principal=clinician,
        ).id
        == task.id
    )

    restarted_store = CockroachWorkflowStore(database_engine, upload_directory=tmp_path)
    restored_run = restarted_store.get_run(first_run.id)
    assert restored_run.decision == first_run.decision
    assert restarted_store.get_task(task.id).status == "APPLIED"
    second_run = restarted_store.run_agent(
        principal=clinician,
        request_type="COMPARE_REPORTS",
        query="Start a new session and retrieve the prior review.",
        idempotency_key="persistent-run-0002",
    )
    assert second_run.persisted_review_applied is True
    assert second_run.decision.proposed_action.action_type == "NO_ACTION"
    assert "CockroachDB durable memory" in second_run.decision.memory_impact_statement

    with database_engine.connect() as connection:
        counts = (
            connection.execute(
                text(
                    """
                SELECT
                    (SELECT count(*) FROM scan_reports
                     WHERE subject_id = :subject_id) AS reports,
                    (SELECT count(*) FROM measurements
                     WHERE subject_id = :subject_id) AS measurements,
                        (SELECT count(*) FROM agent_runs
                         WHERE subject_id = :subject_id
                           AND run_idempotency_key LIKE 'persistent-run-%') AS runs,
                    (SELECT count(*) FROM review_events
                     WHERE subject_id = :subject_id) AS reviews,
                    (SELECT count(*) FROM memories
                     WHERE subject_id = :subject_id
                       AND source_type = 'REVIEWER_STATEMENT') AS reviewer_memories,
                    (SELECT count(*) FROM audit_events
                     WHERE subject_id = :subject_id) AS audits
                """
                ),
                {"subject_id": DEMO_SUBJECT_ID},
            )
            .mappings()
            .one()
        )
    assert int(counts["reports"]) >= 3
    assert int(counts["measurements"]) >= 5
    assert int(counts["runs"]) == 2
    assert int(counts["reviews"]) == 1
    assert int(counts["reviewer_memories"]) == 1
    assert int(counts["audits"]) >= 5


def test_direct_s3_completion_verifies_persists_and_deletes_raw_object(
    database_engine: Engine,
) -> None:
    with database_engine.begin() as connection:
        seed_synthetic_workflow(connection)
    content = (
        Path(__file__).resolve().parents[4] / "output" / "pdf" / "bonetwin-demo-dxa-2022.pdf"
    ).read_bytes()
    direct_store = DirectUploadStore()
    settings = Settings.model_validate(
        {
            "raw_document_store_mode": "s3",
            "s3_document_bucket": "synthetic-integration-bucket",
        }
    )
    store = CockroachWorkflowStore(
        database_engine,
        settings=settings,
        raw_document_store=direct_store,
    )
    clinician = DEMO_PRINCIPALS["demo-clinician"]
    intent = store.create_upload_intent(
        UploadIntentRequest(
            original_filename="bonetwin-demo-dxa-2022.pdf",
            content_type="application/pdf",
            byte_size=len(content),
            sha256=sha256(content).hexdigest(),
        ),
        "direct-s3-upload-0001",
        clinician,
    )
    assert intent.upload_url.startswith("https://synthetic-integration-bucket")
    assert intent.upload_headers["x-amz-server-side-encryption"] == "aws:kms"
    assert store.get_document(intent.document_id).status == "UPLOADING"

    direct_store.content[intent.document_id] = content
    ready = store.complete_upload(
        intent.document_id,
        "direct-s3-complete-0001",
        clinician,
    )

    assert ready.status == "READY"
    assert ready.report is not None
    assert len(ready.report.measurements) == 3
    assert intent.document_id in direct_store.deleted
    with database_engine.connect() as connection:
        stored = (
            connection.execute(
                text(
                    """
                    SELECT s3_bucket, s3_key,
                           (SELECT count(*) FROM audit_events
                            WHERE resource_id = CAST(:document_id AS STRING)
                              AND action = 'RAW_UPLOAD_VERIFIED') AS verification_audits
                    FROM documents WHERE id = :document_id
                    """
                ),
                {"document_id": intent.document_id},
            )
            .mappings()
            .one()
        )
    assert stored["s3_bucket"] == "synthetic-integration-bucket"
    assert stored["s3_key"].endswith(f"/{intent.document_id}.upload")
    assert int(stored["verification_audits"]) == 1


def test_live_bedrock_runtime_is_wired_to_durable_store_and_replay_is_free(
    database_engine: Engine,
    tmp_path: Path,
) -> None:
    with database_engine.begin() as connection:
        seed_synthetic_workflow(connection)
    runtime = StubLiveBedrockRuntime()
    settings = Settings.model_validate(
        {
            "bedrock_mode": "live",
            "bedrock_chat_model_id": runtime.chat_model_id,
        }
    )
    store = CockroachWorkflowStore(
        database_engine,
        settings=settings,
        upload_directory=tmp_path,
        bedrock_runtime=runtime,
    )
    clinician = DEMO_PRINCIPALS["demo-clinician"]
    result = store.run_agent(
        principal=clinician,
        request_type="COMPARE_REPORTS",
        query="Run the credentialed synthetic comparison.",
        idempotency_key="stub-live-bedrock-run-0001",
    )
    assert runtime.embed_calls == 1
    assert runtime.decision_calls == 1
    assert store.transparency().mode == "LOCAL_BEDROCK"

    replay = store.run_agent(
        principal=clinician,
        request_type="COMPARE_REPORTS",
        query="Run the credentialed synthetic comparison.",
        idempotency_key="stub-live-bedrock-run-0001",
    )
    assert replay.id == result.id
    assert runtime.embed_calls == 1
    assert runtime.decision_calls == 1
    with database_engine.connect() as connection:
        model_id = connection.execute(
            text("SELECT model_id FROM agent_runs WHERE id = :id"), {"id": result.id}
        ).scalar_one()
    assert model_id == runtime.chat_model_id
