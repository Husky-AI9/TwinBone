"""Deterministic structured demo records for the local CockroachDB runtime."""

from __future__ import annotations

import json
from collections.abc import Callable
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Connection, text

from services.agent.bonetwin_agent.trust import deterministic_embedding
from services.api.app.auth import DEMO_SUBJECT_ID, DEMO_TENANT_ID
from services.api.app.db.vector import vector_literal

CLINICIAN_ID = UUID("20000000-0000-4000-8000-000000000002")
PATIENT_ID = UUID("20000000-0000-4000-8000-000000000003")


def _content_hash(content: str) -> str:
    return sha256(" ".join(content.split()).encode("utf-8")).hexdigest()


def seed_synthetic_workflow(
    connection: Connection,
    *,
    embed: Callable[[str], list[float]] = deterministic_embedding,
    embedding_model: str = "bonetwin-deterministic-local-v1",
) -> None:
    """Upsert the visibly synthetic baseline used by the local UI."""
    connection.execute(
        text(
            """
            INSERT INTO app_users (
                id, tenant_id, cognito_subject, role, display_name
            ) VALUES (
                :id, :tenant_id, 'demo-patient', 'PATIENT', 'Synthetic Patient'
            )
            ON CONFLICT (id) DO UPDATE SET
                role = excluded.role,
                display_name = excluded.display_name
            """
        ),
        {"id": PATIENT_ID, "tenant_id": DEMO_TENANT_ID},
    )

    baseline_reports = (
        {
            "document_id": UUID("42000000-0000-4000-8000-000000000001"),
            "report_id": UUID("41000000-0000-4000-8000-000000000001"),
            "measurement_id": UUID("43000000-0000-4000-8000-000000000001"),
            "scan_date": "2019-05-03",
            "bmd": 0.781,
            "t_score": -1.3,
            "label": "Baseline",
            "sha256": "1" * 64,
        },
        {
            "document_id": UUID("42000000-0000-4000-8000-000000000002"),
            "report_id": UUID("41000000-0000-4000-8000-000000000002"),
            "measurement_id": UUID("43000000-0000-4000-8000-000000000002"),
            "scan_date": "2022-06-08",
            "bmd": 0.756,
            "t_score": -1.5,
            "label": "Prior",
            "sha256": "2" * 64,
        },
    )
    for item in baseline_reports:
        connection.execute(
            text(
                """
                INSERT INTO documents (
                    id, tenant_id, subject_id, status, original_filename,
                    content_type, byte_size, sha256, upload_idempotency_key,
                    created_by, created_at
                ) VALUES (
                    :document_id, :tenant_id, :subject_id, 'READY',
                    :filename, 'application/pdf', 0, :sha256, :upload_key,
                    :created_by, CAST(:scan_date AS TIMESTAMPTZ)
                )
                ON CONFLICT (id) DO UPDATE SET status = 'READY'
                """
            ),
            {
                **item,
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": DEMO_SUBJECT_ID,
                "filename": f"synthetic-baseline-{str(item['scan_date'])[:4]}.pdf",
                "upload_key": f"synthetic-baseline-{str(item['scan_date'])[:4]}",
                "created_by": CLINICIAN_ID,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO scan_reports (
                    id, tenant_id, subject_id, document_id, scan_date,
                    facility_pseudonym, scanner_manufacturer, scanner_model,
                    parser_name, parser_version, extraction_confidence,
                    review_required, created_at
                ) VALUES (
                    :report_id, :tenant_id, :subject_id, :document_id,
                    CAST(:scan_date AS DATE), :facility, 'Hologic',
                    'Synthetic Discovery', 'bonetwin-seed', '1.0.0',
                    0.99, false, CAST(:scan_date AS TIMESTAMPTZ)
                )
                ON CONFLICT (id) DO UPDATE SET scan_date = excluded.scan_date
                """
            ),
            {
                **item,
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": DEMO_SUBJECT_ID,
                "facility": f"Synthetic Imaging Center - {item['label']}",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO measurements (
                    id, tenant_id, subject_id, report_id, skeletal_site,
                    region, side, bmd_g_cm2, t_score, extraction_confidence,
                    source_page, source_text, usable_for_longitudinal, created_at
                ) VALUES (
                    :measurement_id, :tenant_id, :subject_id, :report_id,
                    'HIP', 'TOTAL_HIP', 'LEFT', :bmd, :t_score, 0.99, 1,
                    :source_text, true, CAST(:scan_date AS TIMESTAMPTZ)
                )
                ON CONFLICT (id) DO UPDATE SET
                    bmd_g_cm2 = excluded.bmd_g_cm2,
                    t_score = excluded.t_score
                """
            ),
            {
                **item,
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": DEMO_SUBJECT_ID,
                "source_text": (
                    f"Left total hip BMD {item['bmd']:.3f}; T-score {item['t_score']:.1f}"
                ),
            },
        )

    connection.execute(
        text(
            """
            INSERT INTO treatment_events (
                id, tenant_id, subject_id, event_date, category, description,
                source_type, verification_status, created_by
            ) VALUES (
                '61000000-0000-4000-8000-000000000001', :tenant_id,
                :subject_id, '2023-02-15', 'CONTEXT',
                'Synthetic treatment-context date confirmed by reviewer.',
                'SYNTHETIC_FIXTURE', 'VERIFIED', :created_by
            )
            ON CONFLICT (id) DO UPDATE SET description = excluded.description
            """
        ),
        {
            "tenant_id": DEMO_TENANT_ID,
            "subject_id": DEMO_SUBJECT_ID,
            "created_by": CLINICIAN_ID,
        },
    )

    correction_id = UUID("51000000-0000-4000-8000-000000000001")
    memories = (
        {
            "id": correction_id,
            "title": "Do not compare the lumbar measurement",
            "content": (
                "A clinician verified that the 2022 lumbar value is unsuitable for "
                "longitudinal comparison; use comparable hip sites."
            ),
            "source_type": "CLINICIAN_CORRECTION",
            "source_id": UUID("41000000-0000-4000-8000-000000000002"),
            "source_label": "Clinician correction - Jun 8, 2022",
            "status": "VERIFIED",
            "confidence": 1.0,
            "created_at": "2022-06-08T16:00:00Z",
            "valid_from": "2022-06-08T16:00:00Z",
            "superseded_by_id": None,
        },
        {
            "id": UUID("51000000-0000-4000-8000-000000000002"),
            "title": "2022 left total hip measurement",
            "content": "Left total hip BMD was 0.756 g/cm2 with source-backed confidence.",
            "source_type": "SOURCE_REPORT",
            "source_id": UUID("41000000-0000-4000-8000-000000000002"),
            "source_label": "Synthetic report - Jun 8, 2022",
            "status": "VERIFIED",
            "confidence": 0.98,
            "created_at": "2022-06-08T16:00:00Z",
            "valid_from": "2022-06-08T16:00:00Z",
            "superseded_by_id": None,
        },
        {
            "id": UUID("51000000-0000-4000-8000-000000000003"),
            "title": "Earlier lumbar comparison note",
            "content": "Include lumbar values in all comparisons.",
            "source_type": "AGENT_OBSERVATION",
            "source_id": UUID("41000000-0000-4000-8000-000000000002"),
            "source_label": "Superseded observation - Jun 8, 2022",
            "status": "SUPERSEDED",
            "confidence": 0.42,
            "created_at": "2022-06-08T16:00:00Z",
            "valid_from": None,
            "superseded_by_id": correction_id,
        },
        {
            "id": UUID("51000000-0000-4000-8000-000000000004"),
            "title": "Unverified scanner equivalence",
            "content": "Scanner models may be directly comparable.",
            "source_type": "PARSER_INFERENCE",
            "source_id": UUID("41000000-0000-4000-8000-000000000002"),
            "source_label": "Parser inference - Apr 12, 2026",
            "status": "REJECTED",
            "confidence": 0.55,
            "created_at": "2026-04-12T10:00:00Z",
            "valid_from": None,
            "superseded_by_id": None,
        },
    )
    for memory in memories:
        content = str(memory["content"])
        connection.execute(
            text(
                """
                INSERT INTO memories (
                    id, tenant_id, subject_id, memory_type, source_type,
                    source_id, title, content, content_hash, confidence,
                    verification_status, valid_from, superseded_by_id,
                    privacy_classification, embedding_model, embedding,
                    metadata, created_by_actor_type, created_by_actor_id,
                    created_at
                ) VALUES (
                    :id, :tenant_id, :subject_id, 'EVIDENCE', :source_type,
                    :source_id, :title, :content, :content_hash, :confidence,
                    :status, CAST(:valid_from AS TIMESTAMPTZ), :superseded_by_id,
                    'DEIDENTIFIED', :embedding_model,
                    CAST(:embedding AS VECTOR(1024)), CAST(:metadata AS JSONB),
                    'SYSTEM', :created_by, CAST(:created_at AS TIMESTAMPTZ)
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    verification_status = excluded.verification_status,
                    superseded_by_id = excluded.superseded_by_id,
                    embedding_model = excluded.embedding_model,
                    embedding = excluded.embedding,
                    metadata = excluded.metadata
                """
            ),
            {
                **memory,
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": DEMO_SUBJECT_ID,
                "content_hash": _content_hash(content),
                "embedding": vector_literal(embed(content)),
                "embedding_model": embedding_model,
                "metadata": json.dumps({"source_label": memory["source_label"]}),
                "created_by": CLINICIAN_ID,
            },
        )
