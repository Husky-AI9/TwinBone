"""CockroachDB-backed workflow store used by the local production-parity demo."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, TypeVar, cast
from uuid import UUID, uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import RowMapping

from services.agent.bonetwin_agent.bedrock import (
    BedrockDecisionContext,
    BedrockEvidence,
    BedrockInvocationError,
    BedrockRuntime,
)
from services.agent.bonetwin_agent.policies.safety import SAFETY_NOTICE, assert_safe_text
from services.agent.bonetwin_agent.schemas import (
    AgentDecision,
    EvidenceReference,
    ProposedAction,
)
from services.agent.bonetwin_agent.trust import (
    calculate_trust_score,
    deterministic_embedding,
    utc_now,
)
from services.api.app.auth import DEMO_SUBJECT_ID, DEMO_TENANT_ID, AccessScope, Principal
from services.api.app.config import Settings, get_settings
from services.api.app.db import create_database_engine, run_transaction
from services.api.app.models import ActorType, MemoryType, VerificationStatus
from services.api.app.repositories import MemoryRepository
from services.api.app.schemas import (
    AgentRunResponse,
    DemoDataResetResponse,
    DemoRecordDeleteResponse,
    DocumentResponse,
    Measurement,
    MemoryTraceItem,
    ProcessingEvent,
    Report,
    ReviewDecisionRequest,
    ReviewTask,
    SubjectSummary,
    TimelineResponse,
    TransparencyResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)
from services.api.app.services.cockroach_mcp import LangChainCockroachMcpRetriever
from services.api.app.services.demo_store import MemoryState
from services.api.app.services.document_storage import (
    RawDocumentStore,
    create_raw_document_store,
)
from services.ingestion.parser import parse_synthetic_dxa

T = TypeVar("T")


class CockroachWorkflowStore:
    """Persist the complete local vertical slice in CockroachDB."""

    def __init__(
        self,
        engine: Engine | None = None,
        *,
        settings: Settings | None = None,
        upload_directory: Path | None = None,
        raw_document_store: RawDocumentStore | None = None,
        bedrock_runtime: BedrockRuntime | None = None,
        mcp_retriever: LangChainCockroachMcpRetriever | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._engine = engine or create_database_engine(self._settings)
        self._raw_documents = raw_document_store or create_raw_document_store(
            self._settings,
            upload_directory=upload_directory,
        )
        self._bedrock = bedrock_runtime
        if self._settings.bedrock_mode == "live" and self._bedrock is None:
            self._bedrock = BedrockRuntime.from_aws(
                region=self._settings.aws_region,
                profile=self._settings.aws_profile,
                chat_model_id=self._settings.bedrock_chat_model_id,
                embedding_model_id=self._settings.bedrock_embedding_model_id,
                guardrail_id=self._settings.bedrock_guardrail_id,
                guardrail_version=self._settings.bedrock_guardrail_version,
                timeout_seconds=self._settings.bedrock_timeout_seconds,
            )
        self._mcp = mcp_retriever
        if self._settings.cockroach_mcp_mode == "langchain" and self._mcp is None:
            self._mcp = LangChainCockroachMcpRetriever(self._settings)

    @property
    def _embedding_model_id(self) -> str:
        if self._bedrock is not None:
            return self._bedrock.embedding_model_id
        return "bonetwin-deterministic-local-v1"

    @property
    def _database_service(self) -> str:
        if self._mcp is not None or self._settings.app_env.strip().lower() == "hosted":
            return "CockroachDB Cloud"
        return "CockroachDB local single-node"

    def _embed(self, content: str) -> list[float]:
        if self._bedrock is not None:
            return self._bedrock.embed(content)
        return deterministic_embedding(content)

    def _document_processing_events(self, status: str) -> list[ProcessingEvent]:
        if status not in {"READY", "FAILED"}:
            return []
        storage_service = (
            "Amazon S3" if self._raw_documents.label == "s3-kms" else "Local document storage"
        )
        events: list[ProcessingEvent] = []
        if self._settings.app_env.strip().lower() == "hosted":
            events.append(
                ProcessingEvent(
                    id="backend-lambda",
                    service="AWS Lambda",
                    operation="Authenticated ingestion workflow",
                    status="COMPLETED" if status == "READY" else "FAILED",
                    detail="Executed the scoped upload completion contract in the hosted API.",
                )
            )
        events.extend(
            [
                ProcessingEvent(
                    id="backend-storage-verified",
                    service=storage_service,
                    operation="Object integrity verification",
                    status="COMPLETED",
                    detail="PDF signature, byte count, and SHA-256 matched the upload intent.",
                ),
                ProcessingEvent(
                    id="backend-parser",
                    service="BoneTwin parser",
                    operation="Source-backed measurement extraction",
                    status="COMPLETED" if status == "READY" else "FAILED",
                    detail=(
                        "The approved report contract produced validated measurements and evidence."
                        if status == "READY"
                        else "Parser failed safely; no partial measurements were committed."
                    ),
                ),
            ]
        )
        if status == "READY":
            events.extend(
                [
                    ProcessingEvent(
                        id="backend-embedding",
                        service=(
                            "Amazon Bedrock" if self._bedrock is not None else "Local embedder"
                        ),
                        operation="Trusted-memory embedding",
                        status="COMPLETED",
                        detail=(
                            "Generated a validated 1,024-dimensional vector with "
                            f"{self._embedding_model_id}."
                        ),
                    ),
                    ProcessingEvent(
                        id="backend-cockroach-commit",
                        service=self._database_service,
                        operation="Serializable evidence commit",
                        status="COMPLETED",
                        detail=(
                            "Stored the report, original measurements, memory vector, "
                            "and audit event atomically."
                        ),
                    ),
                    ProcessingEvent(
                        id="backend-raw-cleanup",
                        service=storage_service,
                        operation="Raw-object cleanup",
                        status="COMPLETED",
                        detail=(
                            "Removed the temporary raw object after the durable "
                            "transaction committed."
                        ),
                    ),
                ]
            )
        return events

    def _transaction(self, operation: Callable[[Connection], T]) -> T:
        return run_transaction(
            self._engine,
            operation,
            max_retries=self._settings.db_transaction_max_retries,
            base_delay_seconds=self._settings.db_transaction_base_delay_seconds,
            max_delay_seconds=self._settings.db_transaction_max_delay_seconds,
        )

    @staticmethod
    def _scope(principal: Principal) -> AccessScope:
        return AccessScope(
            tenant_id=principal.tenant_id,
            subject_id=DEMO_SUBJECT_ID,
            role=principal.role,
        )

    @staticmethod
    def _json_object(value: object) -> dict[str, Any]:
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("stored JSON payload must be an object")
            return parsed
        if isinstance(value, dict):
            return dict(value)
        raise ValueError("stored JSON payload must be an object")

    def health(self) -> dict[str, str]:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        return {
            "status": "ready",
            "database": ("cockroachdb-cloud" if self._mcp is not None else "cockroachdb"),
            "database_revision": str(revision),
            "mcp_retrieval": "langchain" if self._mcp is not None else "disabled",
            "raw_document_store": self._raw_documents.label,
        }

    @staticmethod
    def _write_audit(
        connection: Connection,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        actor_type: str,
        actor_id: str | None,
        outcome: str = "SUCCESS",
        subject_id: UUID | None = DEMO_SUBJECT_ID,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        connection.execute(
            text(
                """
                INSERT INTO audit_events (
                    tenant_id, subject_id, actor_type, actor_id, action,
                    resource_type, resource_id, request_id, outcome, metadata
                ) VALUES (
                    :tenant_id, :subject_id, :actor_type, :actor_id, :action,
                    :resource_type, :resource_id, :request_id, :outcome,
                    CAST(:metadata AS JSONB)
                )
                """
            ),
            {
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": subject_id,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "request_id": request_id,
                "outcome": outcome,
                "metadata": json.dumps(dict(metadata or {}), sort_keys=True),
            },
        )

    def record_http_audit(
        self,
        *,
        method: str,
        path: str,
        request_id: str,
        outcome: str,
        actor: str,
    ) -> None:
        def operation(connection: Connection) -> None:
            self._write_audit(
                connection,
                action=f"HTTP_{method.upper()}",
                resource_type="api_route",
                resource_id=path,
                request_id=request_id,
                actor_type="USER" if actor == "authenticated" else "SYSTEM",
                actor_id=actor,
                outcome=outcome,
                subject_id=DEMO_SUBJECT_ID if actor == "authenticated" else None,
            )

        self._transaction(operation)

    def subject_summary(self) -> SubjectSummary:
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        """
                        SELECT s.id, s.pseudonym, s.date_of_birth_year, s.status,
                               count(DISTINCT r.id) AS report_count,
                               count(DISTINCT CASE WHEN t.status IN (
                                   'PROPOSED', 'AWAITING_REVIEW'
                               ) THEN t.id END) AS open_task_count,
                               max(r.scan_date) AS latest_scan_date
                        FROM subjects AS s
                        LEFT JOIN scan_reports AS r
                          ON r.tenant_id = s.tenant_id AND r.subject_id = s.id
                        LEFT JOIN review_tasks AS t
                          ON t.tenant_id = s.tenant_id AND t.subject_id = s.id
                        WHERE s.tenant_id = :tenant_id AND s.id = :subject_id
                        GROUP BY s.id, s.pseudonym, s.date_of_birth_year, s.status
                        """
                    ),
                    {"tenant_id": DEMO_TENANT_ID, "subject_id": DEMO_SUBJECT_ID},
                )
                .mappings()
                .one()
            )
        return SubjectSummary(
            id=row["id"],
            pseudonym=row["pseudonym"],
            year_of_birth=row["date_of_birth_year"],
            status=row["status"],
            report_count=int(row["report_count"]),
            open_task_count=int(row["open_task_count"]),
            latest_scan_date=row["latest_scan_date"],
        )

    @staticmethod
    def _report_from_row(connection: Connection, row: RowMapping) -> Report:
        measurement_rows = (
            connection.execute(
                text(
                    """
                    SELECT id, report_id, skeletal_site, region, side, bmd_g_cm2,
                           t_score, z_score, extraction_confidence, source_page,
                           source_text, usable_for_longitudinal
                    FROM measurements
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND report_id = :report_id
                    ORDER BY skeletal_site, region, side
                    """
                ),
                {
                    "tenant_id": DEMO_TENANT_ID,
                    "subject_id": DEMO_SUBJECT_ID,
                    "report_id": row["id"],
                },
            )
            .mappings()
            .all()
        )
        measurements = [
            Measurement(
                id=item["id"],
                report_id=item["report_id"],
                skeletal_site=str(item["skeletal_site"]),
                region=str(item["region"] or "UNKNOWN"),
                side=item["side"],
                bmd_g_cm2=float(item["bmd_g_cm2"]),
                t_score=float(item["t_score"]),
                z_score=None if item["z_score"] is None else float(item["z_score"]),
                confidence=float(item["extraction_confidence"]),
                source_page=int(item["source_page"] or 1),
                source_text=str(item["source_text"] or "Source text unavailable"),
                usable_for_longitudinal=bool(item["usable_for_longitudinal"]),
                verification_status=(
                    "AWAITING_REVIEW"
                    if str(row["parser_name"]) != "bonetwin-seed"
                    and bool(item["usable_for_longitudinal"])
                    else ("EXCLUDED" if not bool(item["usable_for_longitudinal"]) else "VERIFIED")
                ),
            )
            for item in measurement_rows
        ]
        return Report(
            id=row["id"],
            document_id=row["document_id"],
            scan_date=row["scan_date"],
            report_type=str(row["report_type"]),
            facility_pseudonym=str(row["facility_pseudonym"] or "Synthetic facility"),
            scanner_manufacturer=str(row["scanner_manufacturer"] or "Unknown"),
            scanner_model=str(row["scanner_model"] or "Unknown"),
            parser_name=str(row["parser_name"]),
            parser_version=str(row["parser_version"]),
            extraction_confidence=float(row["extraction_confidence"] or 0),
            review_required=bool(row["review_required"]),
            measurements=measurements,
        )

    def _reports(self, connection: Connection) -> list[Report]:
        rows = (
            connection.execute(
                text(
                    """
                    SELECT id, document_id, scan_date, report_type,
                           facility_pseudonym, scanner_manufacturer, scanner_model,
                           parser_name, parser_version, extraction_confidence,
                           review_required
                    FROM scan_reports
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                    ORDER BY scan_date DESC
                    """
                ),
                {"tenant_id": DEMO_TENANT_ID, "subject_id": DEMO_SUBJECT_ID},
            )
            .mappings()
            .all()
        )
        return [self._report_from_row(connection, row) for row in rows]

    @staticmethod
    def _status_details(status: str) -> tuple[int, str]:
        return {
            "UPLOADING": (8, "Upload intent created"),
            "UPLOADED": (20, "Uploaded bytes verified by local storage adapter"),
            "EXTRACTING": (45, "Extracting source-backed text"),
            "PARSING": (70, "Parsing synthetic report"),
            "INDEXING": (88, "Writing structured memory and vector index"),
            "READY": (100, "Report parsed, screened, and indexed in CockroachDB"),
            "FAILED": (100, "Parsing failed safely; retry is available"),
            "DELETED": (100, "Logical deletion recorded; object cleanup requested"),
        }.get(status, (30, status.replace("_", " ").title()))

    def _document_from_connection(
        self, connection: Connection, document_id: UUID
    ) -> DocumentResponse:
        row = (
            connection.execute(
                text(
                    """
                    SELECT id, subject_id, status, original_filename, content_type,
                           byte_size, sha256, failure_code, failure_message, created_at
                    FROM documents
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND id = :document_id
                    """
                ),
                {
                    "tenant_id": DEMO_TENANT_ID,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise KeyError("Document not found")
        report_row = (
            connection.execute(
                text(
                    """
                    SELECT id, document_id, scan_date, report_type,
                           facility_pseudonym, scanner_manufacturer, scanner_model,
                           parser_name, parser_version, extraction_confidence,
                           review_required
                    FROM scan_reports
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND document_id = :document_id
                    """
                ),
                {
                    "tenant_id": DEMO_TENANT_ID,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        progress, message = self._status_details(str(row["status"]))
        return DocumentResponse(
            id=row["id"],
            subject_id=row["subject_id"],
            status=str(row["status"]),
            original_filename=str(row["original_filename"]),
            content_type=str(row["content_type"]),
            byte_size=int(row["byte_size"]),
            sha256=str(row["sha256"]),
            progress=progress,
            status_message=message,
            report=(
                self._report_from_row(connection, report_row)
                if report_row is not None and row["status"] != "DELETED"
                else None
            ),
            failure_code=row["failure_code"],
            failure_message=row["failure_message"],
            processing_events=self._document_processing_events(str(row["status"])),
            created_at=row["created_at"],
        )

    def get_document(self, document_id: UUID) -> DocumentResponse:
        with self._engine.connect() as connection:
            return self._document_from_connection(connection, document_id)

    def create_upload_intent(
        self,
        payload: UploadIntentRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> UploadIntentResponse:
        def operation(connection: Connection) -> tuple[UUID, bool]:
            existing = (
                connection.execute(
                    text(
                        """
                        SELECT id, upload_idempotency_key, original_filename,
                               content_type, byte_size, sha256
                        FROM documents
                        WHERE tenant_id = :tenant_id
                          AND (
                              upload_idempotency_key = :idempotency_key
                              OR (subject_id = :subject_id AND sha256 = :sha256)
                          )
                        ORDER BY CASE WHEN upload_idempotency_key = :idempotency_key
                                     THEN 0 ELSE 1 END
                        LIMIT 1
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "idempotency_key": idempotency_key,
                        "sha256": payload.sha256,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if existing["upload_idempotency_key"] == idempotency_key and (
                    existing["original_filename"] != payload.original_filename
                    or existing["content_type"] != payload.content_type
                    or int(existing["byte_size"]) != payload.byte_size
                    or existing["sha256"] != payload.sha256
                ):
                    raise ValueError("idempotency key was already used for a different upload")
                document_id = existing["id"]
                return document_id, True

            document_id = uuid4()
            reference = self._raw_documents.reference(document_id)
            connection.execute(
                text(
                    """
                    INSERT INTO documents (
                        id, tenant_id, subject_id, status, original_filename,
                        content_type, byte_size, sha256, s3_bucket, s3_key,
                        upload_idempotency_key, raw_retention_until, created_by
                    ) VALUES (
                        :id, :tenant_id, :subject_id, 'UPLOADING', :filename,
                        :content_type, :byte_size, :sha256, :s3_bucket, :s3_key,
                        :idempotency_key, :raw_retention_until, :created_by
                    )
                    """
                ),
                {
                    "id": document_id,
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "filename": payload.original_filename,
                    "content_type": payload.content_type,
                    "byte_size": payload.byte_size,
                    "sha256": payload.sha256,
                    "s3_bucket": reference.bucket,
                    "s3_key": reference.key,
                    "idempotency_key": idempotency_key,
                    "raw_retention_until": utc_now()
                    + timedelta(days=self._settings.raw_document_retention_days),
                    "created_by": principal.user_id,
                },
            )
            self._write_audit(
                connection,
                action="UPLOAD_INTENT_CREATED",
                resource_type="document",
                resource_id=str(document_id),
                request_id=idempotency_key,
                actor_type=principal.role.value if principal.role.value == "CLINICIAN" else "USER",
                actor_id=str(principal.user_id),
                metadata={
                    "sha256": payload.sha256,
                    "synthetic_only": True,
                    "raw_storage": self._raw_documents.label,
                },
            )
            return document_id, False

        document_id, duplicate = self._transaction(operation)
        target = self._raw_documents.upload_target(
            document_id,
            content_type=payload.content_type,
            sha256_hex=payload.sha256,
        )
        return UploadIntentResponse(
            document_id=document_id,
            upload_url=target.url,
            upload_method="PUT",
            upload_headers=target.headers,
            expires_in_seconds=target.expires_in_seconds,
            duplicate=duplicate,
        )

    def accept_local_upload(
        self,
        document_id: UUID,
        content: bytes,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        document = self.get_document(document_id)
        if document.status in {"READY", "FAILED", "DELETED"}:
            self._raw_documents.delete(document_id)
            return document
        if len(content) != document.byte_size:
            raise ValueError("uploaded byte count does not match upload intent")
        if sha256(content).hexdigest() != document.sha256:
            raise ValueError("uploaded SHA-256 does not match upload intent")
        if document.content_type == "application/pdf" and not content.startswith(b"%PDF-"):
            raise ValueError("uploaded content is not a PDF")
        if document.content_type == "text/plain":
            content.decode("utf-8")

        self._raw_documents.accept_local(document_id, content)

        def operation(connection: Connection) -> DocumentResponse:
            current = self._document_from_connection(connection, document_id)
            if current.status in {"READY", "FAILED", "DELETED"}:
                return current
            connection.execute(
                text(
                    """
                    UPDATE documents SET status = 'UPLOADED'
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :document_id
                    """
                ),
                {
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                },
            )
            self._write_audit(
                connection,
                action="RAW_UPLOAD_VERIFIED",
                resource_type="document",
                resource_id=str(document_id),
                request_id=idempotency_key,
                actor_type=principal.role.value if principal.role.value == "CLINICIAN" else "USER",
                actor_id=str(principal.user_id),
                metadata={
                    "byte_size": len(content),
                    "raw_storage": self._raw_documents.label,
                },
            )
            return self._document_from_connection(connection, document_id)

        result = self._transaction(operation)
        if result.status in {"READY", "FAILED", "DELETED"}:
            self._raw_documents.delete(document_id)
        return result

    def _mark_direct_upload_verified(
        self,
        document_id: UUID,
        *,
        idempotency_key: str,
        principal: Principal,
        byte_size: int,
    ) -> DocumentResponse:
        """Authorize and audit the S3 upload observed by the completion endpoint."""

        def operation(connection: Connection) -> DocumentResponse:
            current = self._document_from_connection(connection, document_id)
            if current.status != "UPLOADING":
                return current
            connection.execute(
                text(
                    """
                    UPDATE documents SET status = 'UPLOADED'
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :document_id AND status = 'UPLOADING'
                    """
                ),
                {
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                },
            )
            self._write_audit(
                connection,
                action="RAW_UPLOAD_VERIFIED",
                resource_type="document",
                resource_id=str(document_id),
                request_id=idempotency_key,
                actor_type=(
                    principal.role.value if principal.role.value == "CLINICIAN" else "USER"
                ),
                actor_id=str(principal.user_id),
                metadata={
                    "byte_size": byte_size,
                    "raw_storage": self._raw_documents.label,
                },
            )
            return self._document_from_connection(connection, document_id)

        return self._transaction(operation)

    @staticmethod
    def _extract_text(document: DocumentResponse, content: bytes) -> str:
        if document.content_type == "text/plain":
            return content.decode("utf-8")
        try:
            reader = PdfReader(BytesIO(content))
        except PdfReadError as error:
            raise ValueError("PDF could not be read") from error
        if reader.is_encrypted:
            raise ValueError("encrypted PDFs are not supported in local demo mode")
        if len(reader.pages) > 10:
            raise ValueError("PDF exceeds the 10-page local demo limit")
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not extracted.strip():
            raise ValueError("PDF contains no extractable text")
        return extracted

    def complete_upload(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        document = self.get_document(document_id)
        if document.status == "READY":
            self._raw_documents.delete(document_id)
            return document
        try:
            content = self._raw_documents.read(document_id)
            if len(content) != document.byte_size:
                raise ValueError("uploaded byte count does not match upload intent")
            if sha256(content).hexdigest() != document.sha256:
                raise ValueError("uploaded SHA-256 does not match upload intent")
            if document.content_type == "application/pdf" and not content.startswith(b"%PDF-"):
                raise ValueError("uploaded content is not a PDF")
            if document.status == "UPLOADING":
                self._mark_direct_upload_verified(
                    document_id,
                    idempotency_key=idempotency_key,
                    principal=principal,
                    byte_size=len(content),
                )
            parsed = parse_synthetic_dxa(self._extract_text(document, content))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            error_message = str(error)

            def fail(connection: Connection) -> None:
                connection.execute(
                    text(
                        """
                        UPDATE documents
                        SET status = 'FAILED', failure_code = 'PARSER_VALIDATION_FAILED',
                            failure_message = :message
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                          AND id = :document_id AND status != 'READY'
                        """
                    ),
                    {
                        "message": error_message,
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "document_id": document_id,
                    },
                )
                self._write_audit(
                    connection,
                    action="INGESTION_FAILED",
                    resource_type="document",
                    resource_id=str(document_id),
                    request_id=idempotency_key,
                    actor_type="SYSTEM",
                    actor_id=str(principal.user_id),
                    outcome="FAILED",
                    metadata={"failure_code": "PARSER_VALIDATION_FAILED"},
                )

            self._transaction(fail)
            self._raw_documents.delete(document_id)
            return self.get_document(document_id)

        total_hip = next(item for item in parsed.measurements if item.region == "TOTAL_HIP")
        memory_content = (
            f"Left total hip BMD is {total_hip.bmd_g_cm2:.3f} g/cm2 in the "
            f"synthetic {parsed.scan_date.year} report."
        )
        memory_embedding = self._embed(memory_content)

        def operation(connection: Connection) -> DocumentResponse:
            current = self._document_from_connection(connection, document_id)
            if current.status == "READY":
                return current
            if current.status != "UPLOADED":
                raise ValueError("document is not ready for ingestion")
            report_id = uuid4()
            connection.execute(
                text(
                    """
                    INSERT INTO scan_reports (
                        id, tenant_id, subject_id, document_id, scan_date,
                        report_type, facility_pseudonym, scanner_manufacturer,
                        scanner_model, parser_name, parser_version,
                        extraction_confidence, review_required
                    ) VALUES (
                        :id, :tenant_id, :subject_id, :document_id, :scan_date,
                        :report_type, :facility, :manufacturer, :model,
                        :parser_name, :parser_version, :confidence, :review_required
                    )
                    """
                ),
                {
                    "id": report_id,
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                    "scan_date": parsed.scan_date,
                    "report_type": parsed.report_type,
                    "facility": parsed.facility_pseudonym,
                    "manufacturer": parsed.scanner_manufacturer,
                    "model": parsed.scanner_model,
                    "parser_name": parsed.parser_name,
                    "parser_version": parsed.parser_version,
                    "confidence": parsed.extraction_confidence,
                    "review_required": parsed.review_required,
                },
            )
            for value in parsed.measurements:
                connection.execute(
                    text(
                        """
                        INSERT INTO measurements (
                            id, tenant_id, subject_id, report_id, skeletal_site,
                            region, side, bmd_g_cm2, t_score, z_score, unit,
                            extraction_confidence, source_page, source_text,
                            usable_for_longitudinal
                        ) VALUES (
                            :id, :tenant_id, :subject_id, :report_id,
                            :skeletal_site, :region, :side, :bmd, :t_score,
                            :z_score, 'g/cm2', :confidence, :source_page,
                            :source_text, :usable
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "report_id": report_id,
                        "skeletal_site": value.skeletal_site,
                        "region": value.region,
                        "side": value.side,
                        "bmd": value.bmd_g_cm2,
                        "t_score": value.t_score,
                        "z_score": value.z_score,
                        "confidence": value.extraction_confidence,
                        "source_page": value.source_page,
                        "source_text": value.source_text,
                        "usable": value.usable_for_longitudinal,
                    },
                )
            MemoryRepository().add(
                connection,
                self._scope(principal),
                title=f"{parsed.scan_date.year} left total hip measurement",
                content=memory_content,
                embedding=memory_embedding,
                embedding_model=self._embedding_model_id,
                memory_type=MemoryType.EVIDENCE,
                source_type="SOURCE_REPORT",
                source_id=report_id,
                verification_status=VerificationStatus.AWAITING_REVIEW,
                actor_type=ActorType.SYSTEM,
                actor_id=principal.user_id,
                metadata={
                    "source_label": f"Synthetic report - {parsed.scan_date:%b %d, %Y}",
                    "document_id": str(document_id),
                },
            )
            connection.execute(
                text(
                    """
                    UPDATE documents
                    SET status = 'READY', failure_code = NULL, failure_message = NULL
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :document_id
                    """
                ),
                {
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "document_id": document_id,
                },
            )
            self._write_audit(
                connection,
                action="INGESTION_COMMITTED",
                resource_type="document",
                resource_id=str(document_id),
                request_id=idempotency_key,
                actor_type="SYSTEM",
                actor_id=str(principal.user_id),
                metadata={
                    "report_id": str(report_id),
                    "measurement_count": len(parsed.measurements),
                    "raw_deleted_after_commit": True,
                },
            )
            return self._document_from_connection(connection, document_id)

        result = self._transaction(operation)
        self._raw_documents.delete(document_id)
        return result

    def delete_document(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        def operation(connection: Connection) -> DocumentResponse:
            current = self._document_from_connection(connection, document_id)
            if current.status != "DELETED":
                connection.execute(
                    text(
                        """
                        UPDATE documents SET status = 'DELETED'
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                          AND id = :document_id
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "document_id": document_id,
                    },
                )
                self._write_audit(
                    connection,
                    action="DOCUMENT_LOGICALLY_DELETED",
                    resource_type="document",
                    resource_id=str(document_id),
                    request_id=idempotency_key,
                    actor_type=(
                        principal.role.value if principal.role.value == "CLINICIAN" else "USER"
                    ),
                    actor_id=str(principal.user_id),
                )
            return self._document_from_connection(connection, document_id)

        result = self._transaction(operation)
        self._raw_documents.delete(document_id)
        return result

    def delete_demo_record(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DemoRecordDeleteResponse:
        """Purge one fabricated report and its direct evidence with an audit tombstone."""
        database_name = (
            "cockroachdb-cloud"
            if "cockroachlabs.cloud" in self._settings.reveal_database_url()
            else "cockroachdb"
        )

        def operation(
            connection: Connection,
        ) -> tuple[UUID | None, date | None, dict[str, int], bool, datetime]:
            replay = (
                connection.execute(
                    text(
                        """
                        SELECT resource_id, metadata, created_at
                        FROM audit_events
                        WHERE tenant_id = :tenant_id
                          AND subject_id = :subject_id
                          AND action = 'DEMO_RECORD_DELETED'
                          AND request_id = :request_id
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "request_id": idempotency_key,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if replay is not None:
                if replay["resource_id"] != str(document_id):
                    raise ValueError("idempotency key was already used for another record")
                metadata = self._json_object(replay["metadata"])
                stored_counts = metadata.get("deleted_records", {})
                if not isinstance(stored_counts, dict):
                    raise ValueError("record deletion audit metadata is invalid")
                stored_report_id = metadata.get("report_id")
                stored_scan_date = metadata.get("scan_date")
                return (
                    UUID(str(stored_report_id)) if stored_report_id else None,
                    date.fromisoformat(str(stored_scan_date)) if stored_scan_date else None,
                    {str(key): int(value) for key, value in stored_counts.items()},
                    True,
                    replay["created_at"],
                )

            document = (
                connection.execute(
                    text(
                        """
                        SELECT id, original_filename, sha256
                        FROM documents
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                          AND id = :document_id
                        FOR UPDATE
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "document_id": document_id,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if document is None:
                raise KeyError("Demo record not found")
            report = (
                connection.execute(
                    text(
                        """
                        SELECT id, scan_date
                        FROM scan_reports
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                          AND document_id = :document_id
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "document_id": document_id,
                    },
                )
                .mappings()
                .one_or_none()
            )
            report_id = report["id"] if report is not None else None
            scan_date = report["scan_date"] if report is not None else None
            scope = {
                "tenant_id": principal.tenant_id,
                "subject_id": DEMO_SUBJECT_ID,
                "document_id": document_id,
                "report_id": report_id,
            }
            deleted_records = {
                "documents": 1,
                "scan_reports": int(report_id is not None),
                "measurements": 0,
                "memories": 0,
                "agent_run_memory_links": 0,
                "review_task_evidence_links": 0,
            }
            if report_id is not None:
                counts = (
                    connection.execute(
                        text(
                            """
                            SELECT
                              (SELECT count(*) FROM measurements
                               WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                                 AND report_id = :report_id) AS measurements,
                              (SELECT count(*) FROM memories
                               WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                                 AND source_id = :report_id) AS memories,
                              (SELECT count(*) FROM agent_run_memories
                               WHERE memory_id IN (
                                 SELECT id FROM memories
                                 WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                                   AND source_id = :report_id
                               )) AS agent_run_memory_links,
                              (SELECT count(*) FROM review_task_evidence
                               WHERE memory_id IN (
                                 SELECT id FROM memories
                                 WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                                   AND source_id = :report_id
                               )) AS review_task_evidence_links
                            """
                        ),
                        scope,
                    )
                    .mappings()
                    .one()
                )
                deleted_records.update({key: int(value) for key, value in counts.items()})
                for statement in [
                    """DELETE FROM review_task_evidence WHERE memory_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)""",
                    """DELETE FROM agent_run_memories WHERE memory_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)""",
                    """DELETE FROM memory_relations
                       WHERE from_memory_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)
                          OR to_memory_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)""",
                    """UPDATE memories SET supersedes_id = NULL
                       WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                         AND supersedes_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)""",
                    """UPDATE memories SET superseded_by_id = NULL
                       WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                         AND superseded_by_id IN (
                           SELECT id FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                             AND source_id = :report_id)""",
                    """DELETE FROM memories
                       WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                         AND source_id = :report_id""",
                    """DELETE FROM measurements
                       WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                         AND report_id = :report_id""",
                    """DELETE FROM scan_reports
                       WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                         AND id = :report_id""",
                ]:
                    connection.execute(text(statement), scope)
            connection.execute(
                text(
                    """
                    DELETE FROM documents
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :document_id
                    """
                ),
                scope,
            )
            deleted_at = utc_now()
            self._write_audit(
                connection,
                action="DEMO_RECORD_DELETED",
                resource_type="document",
                resource_id=str(document_id),
                request_id=idempotency_key,
                actor_type="CLINICIAN",
                actor_id=str(principal.user_id),
                metadata={
                    "scope": "authorized-fabricated-demo-record",
                    "original_filename": str(document["original_filename"]),
                    "sha256": str(document["sha256"]),
                    "report_id": str(report_id) if report_id else None,
                    "scan_date": scan_date.isoformat() if scan_date else None,
                    "deleted_records": deleted_records,
                },
            )
            return report_id, scan_date, deleted_records, False, deleted_at

        report_id, scan_date, deleted_records, replayed, deleted_at = self._transaction(operation)
        self._raw_documents.delete(document_id)
        return DemoRecordDeleteResponse(
            subject_id=DEMO_SUBJECT_ID,
            document_id=document_id,
            report_id=report_id,
            scan_date=scan_date,
            status="DELETED",
            database=database_name,
            deleted_records=deleted_records,
            replayed=replayed,
            deleted_at=deleted_at,
            timeline=self.timeline(),
        )

    def clear_demo_data(
        self,
        idempotency_key: str,
        principal: Principal,
    ) -> DemoDataResetResponse:
        """Delete every row owned by the authorized synthetic demo subject."""
        pending_upload_ids: list[UUID] = []
        database_name = (
            "cockroachdb-cloud"
            if "cockroachlabs.cloud" in self._settings.reveal_database_url()
            else "cockroachdb"
        )

        def operation(connection: Connection) -> DemoDataResetResponse:
            replay = (
                connection.execute(
                    text(
                        """
                        SELECT metadata, created_at
                        FROM audit_events
                        WHERE tenant_id = :tenant_id
                          AND subject_id = :subject_id
                          AND action = 'DEMO_DATA_RESET'
                          AND request_id = :request_id
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "request_id": idempotency_key,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if replay is not None:
                metadata = self._json_object(replay["metadata"])
                stored_counts = metadata.get("deleted_records", {})
                if not isinstance(stored_counts, dict):
                    raise ValueError("reset audit metadata is invalid")
                return DemoDataResetResponse(
                    subject_id=DEMO_SUBJECT_ID,
                    status="CLEARED",
                    database=database_name,
                    deleted_records={str(key): int(value) for key, value in stored_counts.items()},
                    replayed=True,
                    reset_at=replay["created_at"],
                )

            scope = {
                "tenant_id": principal.tenant_id,
                "subject_id": DEMO_SUBJECT_ID,
            }
            document_rows = connection.execute(
                text(
                    """
                    SELECT id FROM documents
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                    """
                ),
                scope,
            ).all()
            pending_upload_ids.extend(row[0] for row in document_rows)
            counts = (
                connection.execute(
                    text(
                        """
                        SELECT
                          (SELECT count(*) FROM documents
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS documents,
                          (SELECT count(*) FROM scan_reports
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS scan_reports,
                          (SELECT count(*) FROM measurements
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS measurements,
                          (SELECT count(*) FROM treatment_events
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS treatment_events,
                          (SELECT count(*) FROM memories
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS memories,
                          (SELECT count(*) FROM agent_runs
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS agent_runs,
                          (SELECT count(*) FROM review_tasks
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS review_tasks,
                          (SELECT count(*) FROM review_events
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS review_events,
                          (SELECT count(*) FROM consent_records
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS consent_records,
                          (SELECT count(*) FROM audit_events
                           WHERE tenant_id = :tenant_id AND subject_id = :subject_id)
                            AS audit_events
                        """
                    ),
                    scope,
                )
                .mappings()
                .one()
            )
            deleted_records = {key: int(value) for key, value in counts.items()}

            statements = [
                """DELETE FROM review_events
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM review_task_evidence
                   WHERE task_id IN (
                     SELECT id FROM review_tasks
                     WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                   )""",
                """DELETE FROM review_tasks
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM agent_run_memories
                   WHERE agent_run_id IN (
                     SELECT id FROM agent_runs
                     WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                   )""",
                """DELETE FROM agent_runs
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM memory_relations
                   WHERE from_memory_id IN (
                     SELECT id FROM memories
                     WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                   ) OR to_memory_id IN (
                     SELECT id FROM memories
                     WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                   )""",
                """UPDATE memories
                   SET supersedes_id = NULL, superseded_by_id = NULL
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM memories
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM measurements
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM scan_reports
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM treatment_events
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM consent_records
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM documents
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
                """DELETE FROM audit_events
                   WHERE tenant_id = :tenant_id AND subject_id = :subject_id""",
            ]
            for statement in statements:
                connection.execute(text(statement), scope)

            reset_at = utc_now()
            self._write_audit(
                connection,
                action="DEMO_DATA_RESET",
                resource_type="subject",
                resource_id=str(DEMO_SUBJECT_ID),
                request_id=idempotency_key,
                actor_type="CLINICIAN",
                actor_id=str(principal.user_id),
                metadata={
                    "deleted_records": deleted_records,
                    "scope": "authorized-synthetic-subject",
                },
            )
            return DemoDataResetResponse(
                subject_id=DEMO_SUBJECT_ID,
                status="CLEARED",
                database=database_name,
                deleted_records=deleted_records,
                replayed=False,
                reset_at=reset_at,
            )

        result = self._transaction(operation)
        for document_id in set(pending_upload_ids):
            self._raw_documents.delete(document_id)
        return result

    @staticmethod
    def _memory_state(row: RowMapping) -> MemoryState:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        label = metadata.get("source_label") if isinstance(metadata, dict) else None
        return MemoryState(
            id=row["id"],
            title=str(row["title"]),
            content=str(row["content"]),
            source_type=str(row["source_type"]),
            source_label=str(label or row["source_type"].replace("_", " ").title()),
            verification_status=str(row["verification_status"]),
            confidence=float(row["confidence"]),
            created_at=row["created_at"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            superseded_by_id=row["superseded_by_id"],
        )

    def _memory_trace(
        self,
        connection: Connection,
        *,
        vector_distances: Mapping[UUID, float] | None = None,
        allowed_memory_ids: set[UUID] | None = None,
    ) -> list[MemoryTraceItem]:
        rows = (
            connection.execute(
                text(
                    """
                    SELECT id, title, content, source_type, verification_status,
                           confidence, valid_from, valid_until, superseded_by_id,
                           metadata, created_at
                    FROM memories
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                    ORDER BY created_at DESC, id
                    """
                ),
                {"tenant_id": DEMO_TENANT_ID, "subject_id": DEMO_SUBJECT_ID},
            )
            .mappings()
            .all()
        )
        now = utc_now()
        result: list[MemoryTraceItem] = []
        for row in rows:
            if allowed_memory_ids is not None and row["id"] not in allowed_memory_ids:
                continue
            memory = self._memory_state(row)
            distance = (vector_distances or {}).get(memory.id)
            if vector_distances is None:
                similarity = 0.96
            elif distance is None:
                similarity = 0.25
            else:
                similarity = max(0.1, 1.0 - distance)
            if memory.source_type == "CLINICIAN_CORRECTION":
                similarity = max(similarity, 0.9)
            trust = calculate_trust_score(
                memory,
                now=now,
                vector_similarity=similarity,
                subject_match=True,
            )
            reason = None
            if memory.verification_status == "SUPERSEDED":
                reason = "Superseded by a later clinician-verified correction"
            elif memory.verification_status == "REJECTED":
                reason = "Rejected evidence cannot influence a new run"
            elif memory.verification_status == "EXPIRED":
                reason = "Memory is outside its validity window"
            excluded = trust == 0.0
            if excluded and reason is None:
                reason = "Memory did not meet the deterministic trust threshold"
            result.append(
                MemoryTraceItem(
                    id=memory.id,
                    title=memory.title,
                    content=memory.content,
                    source_type=memory.source_type,
                    source_label=memory.source_label,
                    verification_status=memory.verification_status,
                    confidence=memory.confidence,
                    trust_score=round(trust, 4),
                    disposition=(
                        "EXCLUDED"
                        if excluded
                        else (
                            "USED"
                            if memory.source_type in {"CLINICIAN_CORRECTION", "REVIEWER_STATEMENT"}
                            else "SUPPORTING"
                        )
                    ),
                    disposition_reason=reason,
                    created_at=memory.created_at,
                )
            )
        return sorted(
            result,
            key=lambda item: (
                item.disposition == "EXCLUDED",
                -item.trust_score,
                item.title,
            ),
        )

    def memory_trace(self) -> list[MemoryTraceItem]:
        with self._engine.connect() as connection:
            return self._memory_trace(connection)

    def timeline(self) -> TimelineResponse:
        with self._engine.connect() as connection:
            reports = self._reports(connection)
            memories = self._memory_trace(connection)
            tasks = self._list_tasks(connection)
            event_rows = (
                connection.execute(
                    text(
                        """
                        SELECT id, event_date, category, description, verification_status
                        FROM treatment_events
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                        ORDER BY event_date DESC
                        """
                    ),
                    {"tenant_id": DEMO_TENANT_ID, "subject_id": DEMO_SUBJECT_ID},
                )
                .mappings()
                .all()
            )
        return TimelineResponse(
            subject=self.subject_summary(),
            reports=reports,
            memories=memories,
            tasks=tasks,
            treatment_events=[
                {
                    "id": str(row["id"]),
                    "date": row["event_date"].isoformat() if row["event_date"] else None,
                    "category": row["category"],
                    "description": row["description"],
                    "verification_status": row["verification_status"],
                }
                for row in event_rows
            ],
        )

    @staticmethod
    def _deterministic_agent_decision(
        *,
        evidence: list[EvidenceReference],
        hip_series: list[str],
        prior_review: bool,
    ) -> AgentDecision:
        return AgentDecision(
            summary=(
                f"The comparable left total hip series is {', '.join(hip_series)} g/cm2. "
                "Lumbar values marked for review remain visible as source evidence "
                "but are excluded from the longitudinal comparison."
            ),
            uncertainty=(
                "Scanner metadata still needs human confirmation. Measurement differences "
                "are presented without diagnostic interpretation."
            ),
            safety_notice=SAFETY_NOTICE,
            evidence=evidence,
            proposed_action=ProposedAction(
                action_type="NO_ACTION" if prior_review else "CREATE_CLINICIAN_REVIEW",
                title=(
                    "Prior review decision remains active"
                    if prior_review
                    else "Confirm scanner comparability"
                ),
                rationale=(
                    "A verified reviewer decision is already stored and was reused."
                    if prior_review
                    else "The latest report and prior report list different scanner metadata."
                ),
                payload={"focus": "scanner metadata", "site": "left total hip"},
                requires_human_approval=not prior_review,
            ),
            memory_impact_statement=(
                "A verified prior review and the lumbar correction were retrieved from "
                "CockroachDB durable memory and changed this comparison."
                if prior_review
                else "The verified lumbar correction changed which skeletal sites were compared."
            ),
            counterfactual_without_key_memory=(
                "Without the verified correction, the lumbar value would have been included "
                "even though it was previously marked unsuitable."
            ),
        )

    def run_agent(
        self,
        *,
        principal: Principal,
        request_type: str,
        query: str,
        idempotency_key: str,
    ) -> AgentRunResponse:
        with self._engine.connect() as connection:
            existing_id = connection.execute(
                text(
                    """
                    SELECT id FROM agent_runs
                    WHERE tenant_id = :tenant_id AND run_idempotency_key = :key
                    """
                ),
                {"tenant_id": principal.tenant_id, "key": idempotency_key},
            ).scalar_one_or_none()
            if existing_id is not None:
                return self._run_from_connection(connection, existing_id)
        allowed_memory_ids = self._mcp.allowed_memory_ids() if self._mcp is not None else None
        query_embedding = self._embed(query)

        def operation(connection: Connection) -> AgentRunResponse:
            existing_id = connection.execute(
                text(
                    """
                    SELECT id FROM agent_runs
                    WHERE tenant_id = :tenant_id AND run_idempotency_key = :key
                    """
                ),
                {"tenant_id": principal.tenant_id, "key": idempotency_key},
            ).scalar_one_or_none()
            if existing_id is not None:
                return self._run_from_connection(connection, existing_id)

            nearest = MemoryRepository().nearest(
                connection,
                self._scope(principal),
                query_embedding,
                limit=20,
            )
            distances = {item.memory.id: item.cosine_distance for item in nearest}
            trace = self._memory_trace(
                connection,
                vector_distances=distances,
                allowed_memory_ids=allowed_memory_ids,
            )
            included = [item for item in trace if item.disposition != "EXCLUDED"]
            evidence = [
                EvidenceReference(
                    memory_id=item.id,
                    source_type=item.source_type,
                    role=(
                        "PRIMARY"
                        if item.source_type in {"CLINICIAN_CORRECTION", "REVIEWER_STATEMENT"}
                        else "SUPPORTING"
                    ),
                )
                for item in included[:6]
            ]
            evidence.extend(
                EvidenceReference(
                    memory_id=item.id,
                    source_type=item.source_type,
                    role="EXCLUDED",
                    exclusion_reason=item.disposition_reason,
                )
                for item in trace
                if item.disposition == "EXCLUDED"
            )
            prior_review = bool(
                connection.execute(
                    text(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM memories
                            WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                              AND source_type = 'REVIEWER_STATEMENT'
                              AND verification_status = 'VERIFIED'
                              AND superseded_by_id IS NULL
                        )
                        """
                    ),
                    {"tenant_id": principal.tenant_id, "subject_id": DEMO_SUBJECT_ID},
                ).scalar_one()
            )
            reports = self._reports(connection)
            hip_series: list[str] = []
            for report in sorted(reports, key=lambda item: item.scan_date):
                total_hip = next(
                    (
                        item
                        for item in report.measurements
                        if item.region == "TOTAL_HIP" and item.usable_for_longitudinal
                    ),
                    None,
                )
                if total_hip is not None:
                    hip_series.append(f"{total_hip.bmd_g_cm2:.3f} ({report.scan_date.year})")
            used_bedrock_fallback = False
            if self._bedrock is not None:
                try:
                    decision = self._bedrock.decide(
                        BedrockDecisionContext(
                            request_type=cast(
                                Literal[
                                    "COMPARE_REPORTS",
                                    "EXPLAIN_MEMORY",
                                    "PREPARE_VISIT",
                                    "REVIEW_OPEN_TASKS",
                                ],
                                request_type,
                            ),
                            query=query,
                            prior_review_applied=prior_review,
                            hip_series=hip_series,
                            evidence=[
                                BedrockEvidence(
                                    memory_id=item.id,
                                    title=item.title,
                                    content=item.content,
                                    source_type=item.source_type,
                                    verification_status=item.verification_status,
                                    disposition=item.disposition,
                                    disposition_reason=item.disposition_reason,
                                    trust_score=item.trust_score,
                                )
                                for item in trace
                            ],
                        )
                    )
                except BedrockInvocationError:
                    used_bedrock_fallback = True
                    decision = self._deterministic_agent_decision(
                        evidence=evidence,
                        hip_series=hip_series,
                        prior_review=prior_review,
                    )
            else:
                decision = self._deterministic_agent_decision(
                    evidence=evidence,
                    hip_series=hip_series,
                    prior_review=prior_review,
                )
            assert_safe_text(
                decision.summary,
                decision.uncertainty,
                decision.memory_impact_statement,
            )
            run_id = uuid4()
            now = utc_now()
            connection.execute(
                text(
                    """
                    INSERT INTO agent_runs (
                        id, tenant_id, subject_id, user_id, request_type, user_query,
                        model_id, prompt_version, run_idempotency_key, status,
                        response_summary, uncertainty, completed_at, decision_payload,
                        persisted_review_applied
                    ) VALUES (
                        :id, :tenant_id, :subject_id, :user_id, :request_type,
                        :query, :model_id, 'system-v1', :key, 'SUCCEEDED',
                        :summary, :uncertainty, :completed_at,
                        CAST(:decision_payload AS JSONB), :prior_review
                    )
                    """
                ),
                {
                    "id": run_id,
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "user_id": principal.user_id,
                    "request_type": request_type,
                    "query": query,
                    "model_id": (
                        self._bedrock.chat_model_id
                        if self._bedrock is not None
                        else "bonetwin-deterministic-local-v1"
                    ),
                    "key": idempotency_key,
                    "summary": decision.summary,
                    "uncertainty": decision.uncertainty,
                    "completed_at": now,
                    "decision_payload": decision.model_dump_json(),
                    "prior_review": prior_review,
                },
            )
            for rank, item in enumerate(trace, start=1):
                connection.execute(
                    text(
                        """
                        INSERT INTO agent_run_memories (
                            agent_run_id, memory_id, vector_distance, trust_score,
                            retrieval_rank, disposition, disposition_reason
                        ) VALUES (
                            :run_id, :memory_id, :distance, :trust_score,
                            :rank, :disposition, :reason
                        )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "memory_id": item.id,
                        "distance": distances.get(item.id),
                        "trust_score": item.trust_score,
                        "rank": rank,
                        "disposition": item.disposition,
                        "reason": item.disposition_reason,
                    },
                )
            task_id: UUID | None = None
            if decision.proposed_action.action_type != "NO_ACTION":
                task_id = uuid4()
                connection.execute(
                    text(
                        """
                        INSERT INTO review_tasks (
                            id, tenant_id, subject_id, agent_run_id, action_type,
                            status, title, proposed_payload, action_idempotency_key
                        ) VALUES (
                            :id, :tenant_id, :subject_id, :run_id, :action_type,
                            'AWAITING_REVIEW', :title, CAST(:payload AS JSONB), :key
                        )
                        """
                    ),
                    {
                        "id": task_id,
                        "tenant_id": principal.tenant_id,
                        "subject_id": DEMO_SUBJECT_ID,
                        "run_id": run_id,
                        "action_type": decision.proposed_action.action_type,
                        "title": decision.proposed_action.title,
                        "payload": json.dumps(decision.proposed_action.payload, sort_keys=True),
                        "key": f"task-{idempotency_key}",
                    },
                )
                for item in included:
                    connection.execute(
                        text(
                            """
                            INSERT INTO review_task_evidence (task_id, memory_id)
                            VALUES (:task_id, :memory_id)
                            """
                        ),
                        {"task_id": task_id, "memory_id": item.id},
                    )
            self._write_audit(
                connection,
                action="AGENT_RUN_COMMITTED",
                resource_type="agent_run",
                resource_id=str(run_id),
                request_id=idempotency_key,
                actor_type=(
                    principal.role.value if principal.role.value == "CLINICIAN" else "USER"
                ),
                actor_id=str(principal.user_id),
                metadata={
                    "vector_candidates": len(nearest),
                    "memory_dispositions": len(trace),
                    "review_task_created": task_id is not None,
                    "bedrock_validation_fallback": used_bedrock_fallback,
                },
            )
            return AgentRunResponse(
                id=run_id,
                subject_id=DEMO_SUBJECT_ID,
                status="SUCCEEDED",
                request_type=request_type,
                decision=decision,
                memory_trace=trace,
                review_task_id=task_id,
                created_at=now,
                persisted_review_applied=prior_review,
                processing_events=[
                    ProcessingEvent(
                        id="comparison-cockroach-retrieval",
                        service=self._database_service,
                        operation="Scoped trusted-memory retrieval",
                        status="COMPLETED",
                        detail=(
                            f"Retrieved and policy-filtered {len(trace)} memory candidates "
                            "for the authorized subject."
                        ),
                    ),
                    ProcessingEvent(
                        id="comparison-bedrock-decision",
                        service=(
                            "Amazon Bedrock" if self._bedrock is not None else "Local agent adapter"
                        ),
                        operation="Strict structured decision",
                        status=("SAFE_FALLBACK" if used_bedrock_fallback else "COMPLETED"),
                        detail=(
                            "Bedrock output did not pass strict schema/evidence validation; "
                            "application code used the authorized deterministic decision."
                            if used_bedrock_fallback
                            else (
                                "The decision passed schema, evidence-ID, action, "
                                "and safety validation."
                            )
                        ),
                    ),
                    ProcessingEvent(
                        id="comparison-cockroach-commit",
                        service=self._database_service,
                        operation="Agent run transaction",
                        status="COMPLETED",
                        detail=(
                            "Committed the run trace, memory dispositions, task state, "
                            "and audit event."
                        ),
                    ),
                ],
            )

        return self._transaction(operation)

    def _run_from_connection(self, connection: Connection, run_id: UUID) -> AgentRunResponse:
        row = (
            connection.execute(
                text(
                    """
                    SELECT id, subject_id, request_type, status, started_at,
                           decision_payload, persisted_review_applied
                    FROM agent_runs
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :run_id
                    """
                ),
                {
                    "tenant_id": DEMO_TENANT_ID,
                    "subject_id": DEMO_SUBJECT_ID,
                    "run_id": run_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["decision_payload"] is None:
            raise KeyError("Agent run not found")
        decision = AgentDecision.model_validate(self._json_object(row["decision_payload"]))
        trace_rows = (
            connection.execute(
                text(
                    """
                    SELECT m.id, m.title, m.content, m.source_type,
                           m.verification_status, m.confidence, m.metadata,
                           m.created_at, arm.trust_score, arm.disposition,
                           arm.disposition_reason
                    FROM agent_run_memories AS arm
                    JOIN memories AS m ON m.id = arm.memory_id
                    WHERE arm.agent_run_id = :run_id
                    ORDER BY arm.retrieval_rank
                    """
                ),
                {"run_id": run_id},
            )
            .mappings()
            .all()
        )
        trace: list[MemoryTraceItem] = []
        for item in trace_rows:
            metadata = item["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            source_label = (
                metadata.get("source_label") if isinstance(metadata, dict) else item["source_type"]
            )
            trace.append(
                MemoryTraceItem(
                    id=item["id"],
                    title=str(item["title"]),
                    content=str(item["content"]),
                    source_type=str(item["source_type"]),
                    source_label=str(source_label),
                    verification_status=str(item["verification_status"]),
                    confidence=float(item["confidence"]),
                    trust_score=float(item["trust_score"]),
                    disposition=item["disposition"],
                    disposition_reason=item["disposition_reason"],
                    created_at=item["created_at"],
                )
            )
        task_id = connection.execute(
            text(
                """
                SELECT id FROM review_tasks
                WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                  AND agent_run_id = :run_id
                """
            ),
            {
                "tenant_id": DEMO_TENANT_ID,
                "subject_id": DEMO_SUBJECT_ID,
                "run_id": run_id,
            },
        ).scalar_one_or_none()
        return AgentRunResponse(
            id=row["id"],
            subject_id=row["subject_id"],
            status=str(row["status"]),
            request_type=str(row["request_type"]),
            decision=decision,
            memory_trace=trace,
            review_task_id=task_id,
            created_at=row["started_at"],
            persisted_review_applied=bool(row["persisted_review_applied"]),
        )

    def get_run(self, run_id: UUID) -> AgentRunResponse:
        with self._engine.connect() as connection:
            return self._run_from_connection(connection, run_id)

    def _task_from_row(self, connection: Connection, row: RowMapping) -> ReviewTask:
        evidence_ids = list(
            connection.execute(
                text(
                    """
                    SELECT memory_id FROM review_task_evidence
                    WHERE task_id = :task_id ORDER BY memory_id
                    """
                ),
                {"task_id": row["id"]},
            ).scalars()
        )
        proposed = self._json_object(row["proposed_payload"])
        applied = (
            None if row["applied_payload"] is None else self._json_object(row["applied_payload"])
        )
        return ReviewTask(
            id=row["id"],
            agent_run_id=row["agent_run_id"],
            action_type=str(row["action_type"]),
            status=str(row["status"]),
            title=str(row["title"]),
            proposed_payload=proposed,
            applied_payload=applied,
            evidence_memory_ids=evidence_ids,
            requires_role=str(row["requires_role"]),
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
            resolution_note=row["resolution_note"],
        )

    def _list_tasks(self, connection: Connection) -> list[ReviewTask]:
        rows = (
            connection.execute(
                text(
                    """
                    SELECT id, agent_run_id, action_type, status, title,
                           proposed_payload, applied_payload, requires_role,
                           created_at, resolved_at, resolution_note
                    FROM review_tasks
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                    ORDER BY created_at DESC
                    """
                ),
                {"tenant_id": DEMO_TENANT_ID, "subject_id": DEMO_SUBJECT_ID},
            )
            .mappings()
            .all()
        )
        return [self._task_from_row(connection, row) for row in rows]

    def list_tasks(self) -> list[ReviewTask]:
        with self._engine.connect() as connection:
            return self._list_tasks(connection)

    def get_task(self, task_id: UUID) -> ReviewTask:
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        """
                        SELECT id, agent_run_id, action_type, status, title,
                               proposed_payload, applied_payload, requires_role,
                               created_at, resolved_at, resolution_note
                        FROM review_tasks
                        WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                          AND id = :task_id
                        """
                    ),
                    {
                        "tenant_id": DEMO_TENANT_ID,
                        "subject_id": DEMO_SUBJECT_ID,
                        "task_id": task_id,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise KeyError("Task not found")
            return self._task_from_row(connection, row)

    def resolve_task(
        self,
        task_id: UUID,
        *,
        decision: Literal["approve", "correct", "reject"],
        payload: ReviewDecisionRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> ReviewTask:
        with self._engine.connect() as connection:
            replay_task_id = connection.execute(
                text(
                    """
                    SELECT task_id FROM review_events
                    WHERE tenant_id = :tenant_id
                      AND decision_idempotency_key = :key
                    """
                ),
                {"tenant_id": principal.tenant_id, "key": idempotency_key},
            ).scalar_one_or_none()
            if replay_task_id is not None:
                if replay_task_id != task_id:
                    raise ValueError("idempotency key belongs to a different review task")
                return self.get_task(task_id)
            existing_task = self.get_task(task_id)
            if existing_task.status not in {"PROPOSED", "AWAITING_REVIEW"}:
                return existing_task
        if decision == "correct" and (not payload.corrected_title or not payload.corrected_content):
            raise ValueError("a correction requires corrected title and content")
        memory_title = (
            payload.corrected_title
            if decision == "correct"
            else (
                "Scanner comparison review approved"
                if decision == "approve"
                else "Scanner comparison proposal rejected"
            )
        ) or "Review decision"
        memory_content = (
            payload.corrected_content
            if decision == "correct"
            else (
                "A clinician approved using the documented hip comparison with its source "
                "and uncertainty notes."
                if decision == "approve"
                else "A clinician rejected the proposed scanner-comparison action."
            )
        ) or ""
        memory_embedding = self._embed(memory_content)

        def operation(connection: Connection) -> ReviewTask:
            replay_task_id = connection.execute(
                text(
                    """
                    SELECT task_id FROM review_events
                    WHERE tenant_id = :tenant_id
                      AND decision_idempotency_key = :key
                    """
                ),
                {"tenant_id": principal.tenant_id, "key": idempotency_key},
            ).scalar_one_or_none()
            if replay_task_id is not None:
                if replay_task_id != task_id:
                    raise ValueError("idempotency key belongs to a different review task")
                row = self._task_row_for_update(connection, task_id)
                return self._task_from_row(connection, row)

            row = self._task_row_for_update(connection, task_id)
            if row["status"] not in {"PROPOSED", "AWAITING_REVIEW"}:
                return self._task_from_row(connection, row)
            if decision == "correct" and (
                not payload.corrected_title or not payload.corrected_content
            ):
                raise ValueError("a correction requires corrected title and content")
            now = utc_now()
            new_status = "REJECTED" if decision == "reject" else "APPLIED"
            applied: dict[str, Any] = {"decision": decision.upper(), "note": payload.note}
            if decision == "correct":
                applied.update(
                    {
                        "corrected_title": payload.corrected_title,
                        "corrected_content": payload.corrected_content,
                    }
                )
            connection.execute(
                text(
                    """
                    UPDATE review_tasks
                    SET status = :status, applied_payload = CAST(:applied AS JSONB),
                        resolved_at = :resolved_at, resolved_by = :resolved_by,
                        resolution_note = :note
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :task_id
                    """
                ),
                {
                    "status": new_status,
                    "applied": json.dumps(applied, sort_keys=True),
                    "resolved_at": now,
                    "resolved_by": principal.user_id,
                    "note": payload.note,
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "task_id": task_id,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO review_events (
                        tenant_id, subject_id, task_id, actor_user_id, event_type,
                        previous_status, new_status, payload,
                        decision_idempotency_key
                    ) VALUES (
                        :tenant_id, :subject_id, :task_id, :actor_user_id,
                        :event_type, :previous_status, :new_status,
                        CAST(:payload AS JSONB), :key
                    )
                    """
                ),
                {
                    "tenant_id": principal.tenant_id,
                    "subject_id": DEMO_SUBJECT_ID,
                    "task_id": task_id,
                    "actor_user_id": principal.user_id,
                    "event_type": decision.upper(),
                    "previous_status": row["status"],
                    "new_status": new_status,
                    "payload": json.dumps(applied, sort_keys=True),
                    "key": idempotency_key,
                },
            )
            MemoryRepository().add(
                connection,
                self._scope(principal),
                title=memory_title,
                content=memory_content,
                embedding=memory_embedding,
                embedding_model=self._embedding_model_id,
                memory_type=MemoryType.TASK,
                source_type="REVIEWER_STATEMENT",
                source_id=task_id,
                verification_status=(
                    VerificationStatus.REJECTED
                    if decision == "reject"
                    else VerificationStatus.VERIFIED
                ),
                actor_type=ActorType.CLINICIAN,
                actor_id=principal.user_id,
                metadata={"source_label": f"Clinician review - {now:%b %d, %Y}"},
            )
            self._write_audit(
                connection,
                action=f"REVIEW_{decision.upper()}_COMMITTED",
                resource_type="review_task",
                resource_id=str(task_id),
                request_id=idempotency_key,
                actor_type="CLINICIAN",
                actor_id=str(principal.user_id),
                metadata={"new_status": new_status, "verified_memory_created": True},
            )
            updated = self._task_row_for_update(connection, task_id)
            return self._task_from_row(connection, updated)

        return self._transaction(operation)

    @staticmethod
    def _task_row_for_update(connection: Connection, task_id: UUID) -> RowMapping:
        row = (
            connection.execute(
                text(
                    """
                    SELECT id, agent_run_id, action_type, status, title,
                           proposed_payload, applied_payload, requires_role,
                           created_at, resolved_at, resolution_note
                    FROM review_tasks
                    WHERE tenant_id = :tenant_id AND subject_id = :subject_id
                      AND id = :task_id
                    FOR UPDATE
                    """
                ),
                {
                    "tenant_id": DEMO_TENANT_ID,
                    "subject_id": DEMO_SUBJECT_ID,
                    "task_id": task_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise KeyError("Task not found")
        return row

    def transparency(self) -> TransparencyResponse:
        with self._engine.connect() as connection:
            audit_count = int(
                connection.execute(
                    text("SELECT count(*) FROM audit_events WHERE tenant_id = :tenant_id"),
                    {"tenant_id": DEMO_TENANT_ID},
                ).scalar_one()
            )
        live_bedrock = self._bedrock is not None
        cloud_mcp = self._mcp is not None
        hosted = self._settings.app_env.strip().lower() == "hosted"
        document_pipeline = (
            [
                {
                    "step": "Storage",
                    "service": (
                        "Amazon S3 with AWS KMS encryption and short-lived presigned uploads"
                    ),
                },
                {
                    "step": "Extraction",
                    "service": "Application PDF extraction and validated demo parser on AWS Lambda",
                },
                {
                    "step": "Data boundary",
                    "service": "Application-enforced fabricated demo-document boundary",
                },
                {
                    "step": "Workflow",
                    "service": "AWS Lambda Function URL with transactional CockroachDB workflow",
                },
            ]
            if hosted
            else [
                {
                    "step": "Storage",
                    "service": (
                        "Amazon S3 (SigV4, SSE-KMS, short-lived raw object)"
                        if self._raw_documents.label == "s3-kms"
                        else "Temporary local filesystem -> Amazon S3 for hosted deployment"
                    ),
                },
                {"step": "Extraction", "service": "Local PDF extraction -> Amazon Textract"},
                {
                    "step": "PHI screening",
                    "service": "Synthetic-only guard -> Comprehend Medical",
                },
                {"step": "Workflow", "service": "Local transaction -> AWS Step Functions"},
            ]
        )
        return TransparencyResponse(
            mode=(
                "AWS"
                if hosted
                else (
                    "LOCAL_CLOUD_MCP"
                    if cloud_mcp
                    else ("LOCAL_BEDROCK" if live_bedrock else "LOCAL_MOCK")
                )
            ),
            database={
                "service": ("CockroachDB Cloud" if cloud_mcp else "CockroachDB local single-node"),
                "role": "Active system of record for reports, agent memory, tasks, and audits",
                "vector": "Live VECTOR(1024) subject-scoped cosine retrieval",
                "access": (
                    "Transactional SQL writes + LangChain MCP retrieval gate"
                    if cloud_mcp
                    else "Direct local SQL"
                ),
            },
            document_pipeline=document_pipeline,
            memory_engine=[
                {
                    "step": "Embedding",
                    "service": (
                        f"Amazon Bedrock {self._embedding_model_id}"
                        if live_bedrock
                        else "Deterministic 1,024-D offline test vector"
                    ),
                },
                {"step": "Retrieval", "service": "CockroachDB vector + trust filters"},
                {
                    "step": "MCP gate",
                    "service": (
                        "LangChain + CockroachDB Cloud managed MCP select_query"
                        if cloud_mcp
                        else "Disabled in this runtime"
                    ),
                },
                {"step": "Review", "service": "Transactional verified durable memory"},
            ],
            agent={
                "runtime": (
                    f"Amazon Bedrock Converse ({self._bedrock.chat_model_id})"
                    if self._bedrock is not None
                    else "Deterministic offline test adapter"
                ),
                "prompt": "system-v1",
                "output": "Strict AgentDecision schema persisted as validated JSON",
            },
            audit_event_count=audit_count,
            safety_boundary=SAFETY_NOTICE,
        )
