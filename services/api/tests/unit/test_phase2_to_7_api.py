import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["WORKFLOW_STORE_MODE"] = "memory"

from services.api.app.auth import DEMO_SUBJECT_ID  # noqa: E402
from services.api.app.main import app
from services.api.app.services import demo_store

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-clinician"}


@pytest.fixture(autouse=True)
def reset_store() -> None:
    demo_store.reset()


def test_authentication_and_subject_isolation() -> None:
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401
    other_subject = uuid4()
    response = client.get(f"/v1/subjects/{other_subject}/timeline", headers=AUTH)
    assert response.status_code == 404
    assert response.json() == {"detail": "Subject not found"}


def test_dashboard_snapshot_is_authenticated_and_bundled() -> None:
    path = f"/v1/subjects/{DEMO_SUBJECT_ID}/dashboard"
    assert client.get(path).status_code == 401

    response = client.get(path, headers=AUTH)

    assert response.status_code == 200
    assert set(response.json()) == {"timeline", "tasks", "transparency"}
    assert response.json()["timeline"]["subject"]["id"] == str(DEMO_SUBJECT_ID)
    assert response.json()["tasks"] == response.json()["timeline"]["tasks"]


def test_local_demo_reset_is_clinician_only_and_replay_safe() -> None:
    denied = client.delete(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/demo-data",
        headers={
            "Authorization": "Bearer demo-judge",
            "Idempotency-Key": "reset-test-0001",
        },
    )
    assert denied.status_code == 403

    cleared = client.delete(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/demo-data",
        headers={**AUTH, "Idempotency-Key": "reset-test-0001"},
    )
    assert cleared.status_code == 200
    assert cleared.json()["status"] == "CLEARED"
    assert cleared.json()["replayed"] is False
    assert cleared.json()["deleted_records"]["scan_reports"] == 2

    timeline = client.get(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/timeline",
        headers=AUTH,
    )
    assert timeline.status_code == 200
    assert timeline.json()["reports"] == []
    assert timeline.json()["memories"] == []

    replay = client.delete(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/demo-data",
        headers={**AUTH, "Idempotency-Key": "reset-test-0001"},
    )
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["deleted_records"] == cleared.json()["deleted_records"]


def test_synthetic_ingestion_is_ready_duplicate_safe_and_recoverable() -> None:
    content = (
        Path(__file__).resolve().parents[4] / "output" / "pdf" / "bonetwin-demo-dxa-2026.pdf"
    ).read_bytes()
    digest = sha256(content).hexdigest()
    headers = {**AUTH, "Idempotency-Key": "upload-test-0001"}
    intent = client.post(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/documents/upload-intent",
        headers=headers,
        json={
            "original_filename": "bonetwin-demo-dxa-2026.pdf",
            "content_type": "application/pdf",
            "byte_size": len(content),
            "sha256": digest,
        },
    )
    assert intent.status_code == 200
    document_id = intent.json()["document_id"]
    rejected = client.put(
        f"/v1/local-uploads/{document_id}",
        headers={
            **AUTH,
            "Content-Type": "application/pdf",
            "Idempotency-Key": "bytes-test-0001",
        },
        content=content + b"mismatch",
    )
    assert rejected.status_code == 422
    uploaded = client.put(
        f"/v1/local-uploads/{document_id}",
        headers={
            **AUTH,
            "Content-Type": "application/pdf",
            "Idempotency-Key": "bytes-test-0001",
        },
        content=content,
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["status"] == "UPLOADED"
    completed = client.post(
        f"/v1/documents/{document_id}/complete-upload",
        headers={**AUTH, "Idempotency-Key": "complete-test-0001"},
        json={"acknowledge_synthetic_only": True},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "READY"
    assert len(completed.json()["report"]["measurements"]) == 3
    assert {event["service"] for event in completed.json()["processing_events"]} == {
        "Local document storage",
        "BoneTwin parser",
        "Local memory adapter",
    }
    duplicate = client.post(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/documents/upload-intent",
        headers={**AUTH, "Idempotency-Key": "different-upload-key"},
        json={
            "original_filename": "duplicate.pdf",
            "content_type": "application/pdf",
            "byte_size": len(content),
            "sha256": digest,
        },
    )
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["document_id"] == document_id


def test_demo_pdf_download_and_parser_failure_are_safe() -> None:
    download = client.get("/demo-documents/bonetwin-demo-dxa-2026.pdf")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF-")
    today = client.get("/demo-documents/bonetwin-demo-dxa-2026-08-16.pdf")
    assert today.status_code == 200
    assert today.content.startswith(b"%PDF-")

    content = b"BONETWIN SYNTHETIC DXA\nSYNTHETIC DEMO - NOT A MEDICAL RECORD\nFAIL_PARSE"
    digest = sha256(content).hexdigest()
    intent = client.post(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/documents/upload-intent",
        headers={**AUTH, "Idempotency-Key": "upload-failure-0001"},
        json={
            "original_filename": "synthetic-parser-failure.txt",
            "content_type": "text/plain",
            "byte_size": len(content),
            "sha256": digest,
        },
    )
    document_id = intent.json()["document_id"]
    uploaded = client.put(
        f"/v1/local-uploads/{document_id}",
        headers={
            **AUTH,
            "Content-Type": "text/plain",
            "Idempotency-Key": "bytes-failure-0001",
        },
        content=content,
    )
    assert uploaded.status_code == 200
    completed = client.post(
        f"/v1/documents/{document_id}/complete-upload",
        headers={**AUTH, "Idempotency-Key": "complete-failure-0001"},
        json={"acknowledge_synthetic_only": True},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "FAILED"
    assert completed.json()["failure_code"] == "PARSER_VALIDATION_FAILED"
    assert completed.json()["report"] is None


def test_review_decision_is_remembered_across_new_agent_run() -> None:
    first = client.post(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/agent/runs",
        headers={**AUTH, "Idempotency-Key": "run-test-0000001"},
        json={"request_type": "COMPARE_REPORTS", "query": "Compare reports"},
    )
    assert first.status_code == 200
    assert first.json()["persisted_review_applied"] is False
    assert first.json()["processing_events"][0]["operation"] == ("Scoped trusted-memory retrieval")
    task_id = first.json()["review_task_id"]
    judge = client.post(
        f"/v1/tasks/{task_id}/approve",
        headers={
            "Authorization": "Bearer demo-judge",
            "Idempotency-Key": "review-test-0001",
        },
        json={"note": "Judge cannot approve"},
    )
    assert judge.status_code == 403
    approved = client.post(
        f"/v1/tasks/{task_id}/approve",
        headers={**AUTH, "Idempotency-Key": "review-test-0001"},
        json={"note": "Synthetic clinician approval"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPLIED"
    replay = client.post(
        f"/v1/tasks/{task_id}/approve",
        headers={**AUTH, "Idempotency-Key": "review-test-0001"},
        json={"note": "Replay"},
    )
    assert replay.json()["id"] == approved.json()["id"]
    new_session = client.post(
        f"/v1/subjects/{DEMO_SUBJECT_ID}/agent/runs",
        headers={**AUTH, "Idempotency-Key": "run-test-0000002"},
        json={"request_type": "COMPARE_REPORTS", "query": "Compare again"},
    )
    assert new_session.json()["persisted_review_applied"] is True
    assert new_session.json()["decision"]["proposed_action"]["action_type"] == "NO_ACTION"
    excluded = [
        item for item in new_session.json()["memory_trace"] if item["disposition"] == "EXCLUDED"
    ]
    assert {item["verification_status"] for item in excluded} == {
        "REJECTED",
        "SUPERSEDED",
    }
