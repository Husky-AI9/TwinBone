"""Thread-safe synthetic workflow store used by the credential-free local demo.

The production adapters persist the same contracts in CockroachDB. This store intentionally
contains no direct identifiers or real health data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from io import BytesIO
from threading import RLock
from typing import Any, Literal
from uuid import UUID, uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from services.agent.bonetwin_agent.policies.safety import SAFETY_NOTICE, assert_safe_text
from services.agent.bonetwin_agent.schemas import (
    AgentDecision,
    EvidenceReference,
    ProposedAction,
)
from services.agent.bonetwin_agent.trust import calculate_trust_score, utc_now
from services.api.app.auth import DEMO_SUBJECT_ID, Principal
from services.api.app.schemas import (
    AgentRunResponse,
    DemoDataResetResponse,
    DocumentResponse,
    Measurement,
    MemoryTraceItem,
    Report,
    ReviewDecisionRequest,
    ReviewTask,
    SubjectSummary,
    TimelineResponse,
    TransparencyResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)
from services.ingestion.parser import parse_synthetic_dxa


@dataclass(slots=True)
class MemoryState:
    id: UUID
    title: str
    content: str
    source_type: str
    source_label: str
    verification_status: str
    confidence: float
    created_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    superseded_by_id: UUID | None = None


class DemoStore:
    """Atomic deterministic workflow state for the synthetic local experience."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.reset()

    def reset(self) -> None:
        """Restore deterministic fixture state between local tests."""
        with self._lock:
            self._reset_unlocked()

    def _reset_unlocked(self) -> None:
        self._documents: dict[UUID, DocumentResponse] = {}
        self._reports: list[Report] = self._baseline_reports()
        self._memories: list[MemoryState] = self._baseline_memories()
        self._tasks: dict[UUID, ReviewTask] = {}
        self._runs: dict[UUID, AgentRunResponse] = {}
        self._treatment_events: list[dict[str, str]] = [
            {
                "id": "61000000-0000-4000-8000-000000000001",
                "date": "2023-02-15",
                "category": "CONTEXT",
                "description": "Synthetic treatment-context date confirmed by reviewer.",
                "verification_status": "VERIFIED",
            }
        ]
        self._upload_keys: dict[str, UUID] = {}
        self._document_hashes: dict[str, UUID] = {}
        self._upload_blobs: dict[UUID, bytes] = {}
        self._run_keys: dict[str, UUID] = {}
        self._action_keys: dict[str, UUID] = {}
        self._audit_events: list[dict[str, Any]] = []

    def health(self) -> dict[str, str]:
        """Report the explicit non-durable unit-test adapter."""
        return {"status": "ready", "database": "in-memory-test-double"}

    @staticmethod
    def _baseline_reports() -> list[Report]:
        return [
            _report(
                "41000000-0000-4000-8000-000000000001",
                "42000000-0000-4000-8000-000000000001",
                date(2019, 5, 3),
                0.781,
                -1.3,
                "Baseline",
            ),
            _report(
                "41000000-0000-4000-8000-000000000002",
                "42000000-0000-4000-8000-000000000002",
                date(2022, 6, 8),
                0.756,
                -1.5,
                "Prior",
            ),
        ]

    @staticmethod
    def _baseline_memories() -> list[MemoryState]:
        created = datetime(2022, 6, 8, 16, 0, tzinfo=UTC)
        return [
            MemoryState(
                id=UUID("51000000-0000-4000-8000-000000000001"),
                title="Do not compare the lumbar measurement",
                content=(
                    "A clinician verified that the 2022 lumbar value is unsuitable for "
                    "longitudinal comparison; use comparable hip sites."
                ),
                source_type="CLINICIAN_CORRECTION",
                source_label="Clinician correction · Jun 8, 2022",
                verification_status="VERIFIED",
                confidence=1.0,
                created_at=created,
                valid_from=created,
            ),
            MemoryState(
                id=UUID("51000000-0000-4000-8000-000000000002"),
                title="2022 left total hip measurement",
                content="Left total hip BMD was 0.756 g/cm² with source-backed confidence.",
                source_type="SOURCE_REPORT",
                source_label="Synthetic report · Jun 8, 2022",
                verification_status="VERIFIED",
                confidence=0.98,
                created_at=created,
                valid_from=created,
            ),
            MemoryState(
                id=UUID("51000000-0000-4000-8000-000000000003"),
                title="Earlier lumbar comparison note",
                content="Include lumbar values in all comparisons.",
                source_type="AGENT_OBSERVATION",
                source_label="Superseded observation · Jun 8, 2022",
                verification_status="SUPERSEDED",
                confidence=0.42,
                created_at=created,
                superseded_by_id=UUID("51000000-0000-4000-8000-000000000001"),
            ),
            MemoryState(
                id=UUID("51000000-0000-4000-8000-000000000004"),
                title="Unverified scanner equivalence",
                content="Scanner models may be directly comparable.",
                source_type="PARSER_INFERENCE",
                source_label="Parser inference · Apr 12, 2026",
                verification_status="REJECTED",
                confidence=0.55,
                created_at=datetime(2026, 4, 12, 10, 0, tzinfo=UTC),
            ),
        ]

    def record_http_audit(
        self,
        *,
        method: str,
        path: str,
        request_id: str,
        outcome: str,
        actor: str,
    ) -> None:
        with self._lock:
            self._audit_events.append(
                {
                    "method": method,
                    "path": path,
                    "request_id": request_id,
                    "outcome": outcome,
                    "actor": actor,
                    "created_at": utc_now().isoformat(),
                }
            )

    def clear_demo_data(
        self,
        idempotency_key: str,
        principal: Principal,
    ) -> DemoDataResetResponse:
        """Clear the in-memory synthetic subject with replay-safe audit evidence."""
        with self._lock:
            replay = next(
                (
                    event
                    for event in self._audit_events
                    if event.get("action") == "DEMO_DATA_RESET"
                    and event.get("request_id") == idempotency_key
                ),
                None,
            )
            if replay is not None:
                return DemoDataResetResponse(
                    subject_id=DEMO_SUBJECT_ID,
                    status="CLEARED",
                    database="in-memory-test-double",
                    deleted_records=dict(replay["deleted_records"]),
                    replayed=True,
                    reset_at=datetime.fromisoformat(str(replay["reset_at"])),
                )

            reset_at = utc_now()
            deleted_records = {
                "documents": len(self._documents),
                "scan_reports": len(self._reports),
                "measurements": sum(len(report.measurements) for report in self._reports),
                "memories": len(self._memories),
                "agent_runs": len(self._runs),
                "review_tasks": len(self._tasks),
                "treatment_events": len(self._treatment_events),
                "audit_events": len(self._audit_events),
            }
            self._documents.clear()
            self._reports.clear()
            self._memories.clear()
            self._tasks.clear()
            self._runs.clear()
            self._treatment_events.clear()
            self._upload_keys.clear()
            self._document_hashes.clear()
            self._upload_blobs.clear()
            self._run_keys.clear()
            self._action_keys.clear()
            self._audit_events = [
                {
                    "action": "DEMO_DATA_RESET",
                    "request_id": idempotency_key,
                    "actor": str(principal.user_id),
                    "deleted_records": deleted_records,
                    "reset_at": reset_at.isoformat(),
                }
            ]
            return DemoDataResetResponse(
                subject_id=DEMO_SUBJECT_ID,
                status="CLEARED",
                database="in-memory-test-double",
                deleted_records=deleted_records,
                replayed=False,
                reset_at=reset_at,
            )

    def subject_summary(self) -> SubjectSummary:
        open_tasks = sum(
            task.status in {"PROPOSED", "AWAITING_REVIEW"} for task in self._tasks.values()
        )
        dates = [report.scan_date for report in self._reports]
        return SubjectSummary(
            id=DEMO_SUBJECT_ID,
            pseudonym="SYNTH-BONE-001",
            year_of_birth=1965,
            status="ACTIVE",
            report_count=len(self._reports),
            open_task_count=open_tasks,
            latest_scan_date=max(dates) if dates else None,
        )

    def timeline(self) -> TimelineResponse:
        with self._lock:
            return TimelineResponse(
                subject=self.subject_summary(),
                reports=sorted(self._reports, key=lambda report: report.scan_date, reverse=True),
                memories=self.memory_trace(),
                tasks=sorted(self._tasks.values(), key=lambda task: task.created_at, reverse=True),
                treatment_events=list(self._treatment_events),
            )

    def create_upload_intent(
        self,
        payload: UploadIntentRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> UploadIntentResponse:
        del principal
        with self._lock:
            existing_id = self._upload_keys.get(idempotency_key) or self._document_hashes.get(
                payload.sha256
            )
            if existing_id is not None:
                return UploadIntentResponse(
                    document_id=existing_id,
                    upload_url=f"/v1/local-uploads/{existing_id}",
                    upload_method="PUT",
                    upload_headers={"Content-Type": payload.content_type},
                    expires_in_seconds=900,
                    duplicate=True,
                )
            document_id = uuid4()
            document = DocumentResponse(
                id=document_id,
                subject_id=DEMO_SUBJECT_ID,
                status="UPLOADING",
                original_filename=payload.original_filename,
                content_type=payload.content_type,
                byte_size=payload.byte_size,
                sha256=payload.sha256,
                progress=8,
                status_message="Upload intent created",
                created_at=utc_now(),
            )
            self._documents[document_id] = document
            self._upload_keys[idempotency_key] = document_id
            self._document_hashes[payload.sha256] = document_id
            return UploadIntentResponse(
                document_id=document_id,
                upload_url=f"/v1/local-uploads/{document_id}",
                upload_method="PUT",
                upload_headers={"Content-Type": payload.content_type},
                expires_in_seconds=900,
                duplicate=False,
            )

    def accept_local_upload(
        self,
        document_id: UUID,
        content: bytes,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        del idempotency_key, principal
        with self._lock:
            document = self.get_document(document_id)
            if len(content) != document.byte_size:
                raise ValueError("uploaded byte count does not match upload intent")
            if sha256(content).hexdigest() != document.sha256:
                raise ValueError("uploaded SHA-256 does not match upload intent")
            if document.content_type == "application/pdf" and not content.startswith(b"%PDF-"):
                raise ValueError("uploaded content is not a PDF")
            if document.content_type == "text/plain":
                content.decode("utf-8")
            self._upload_blobs[document_id] = bytes(content)
            updated = document.model_copy(
                update={
                    "status": "UPLOADED",
                    "progress": 20,
                    "status_message": "Uploaded bytes verified by local storage adapter",
                }
            )
            self._documents[document_id] = updated
            return updated

    def complete_upload(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        del idempotency_key, principal
        with self._lock:
            document = self.get_document(document_id)
            if document.status == "READY":
                return document
            try:
                content = self._upload_blobs.get(document_id)
                if content is None:
                    raise ValueError("uploaded document bytes are unavailable")
                text = self._extract_text(document, content)
                parsed = parse_synthetic_dxa(text)
                total_hip = next(item for item in parsed.measurements if item.region == "TOTAL_HIP")
                report = Report(
                    id=uuid4(),
                    document_id=document_id,
                    scan_date=parsed.scan_date,
                    report_type=parsed.report_type,
                    facility_pseudonym=parsed.facility_pseudonym,
                    scanner_manufacturer=parsed.scanner_manufacturer,
                    scanner_model=parsed.scanner_model,
                    parser_name=parsed.parser_name,
                    parser_version=parsed.parser_version,
                    extraction_confidence=parsed.extraction_confidence,
                    review_required=parsed.review_required,
                    measurements=[
                        Measurement(
                            id=uuid4(),
                            report_id=UUID(int=0),
                            skeletal_site=value.skeletal_site,
                            region=value.region,
                            side=value.side,
                            bmd_g_cm2=value.bmd_g_cm2,
                            t_score=value.t_score,
                            z_score=value.z_score,
                            confidence=value.extraction_confidence,
                            source_page=value.source_page,
                            source_text=value.source_text,
                            usable_for_longitudinal=value.usable_for_longitudinal,
                            verification_status=(
                                "EXCLUDED"
                                if not value.usable_for_longitudinal
                                else "AWAITING_REVIEW"
                            ),
                        )
                        for value in parsed.measurements
                    ],
                )
                report = report.model_copy(
                    update={
                        "measurements": [
                            measurement.model_copy(update={"report_id": report.id})
                            for measurement in report.measurements
                        ]
                    }
                )
                self._reports = [
                    existing for existing in self._reports if existing.document_id != document_id
                ]
                self._reports.append(report)
                self._memories.append(
                    MemoryState(
                        id=uuid4(),
                        title=f"{parsed.scan_date.year} left total hip measurement",
                        content=(
                            "Left total hip BMD is "
                            f"{total_hip.bmd_g_cm2:.3f} "
                            f"g/cm2 in the synthetic {parsed.scan_date.year} report."
                        ),
                        source_type="SOURCE_REPORT",
                        source_label=f"Synthetic report - {parsed.scan_date:%b %d, %Y}",
                        verification_status="AWAITING_REVIEW",
                        confidence=0.98,
                        created_at=utc_now(),
                    )
                )
                updated = document.model_copy(
                    update={
                        "status": "READY",
                        "progress": 100,
                        "status_message": "Report parsed, screened, and indexed",
                        "report": report,
                    }
                )
            except (OSError, ValueError) as error:
                updated = document.model_copy(
                    update={
                        "status": "FAILED",
                        "progress": 100,
                        "status_message": "Parsing failed safely; retry is available",
                        "failure_code": "PARSER_VALIDATION_FAILED",
                        "failure_message": str(error),
                        "report": None,
                    }
                )
            self._documents[document_id] = updated
            self._upload_blobs.pop(document_id, None)
            return updated

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
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            raise ValueError("PDF contains no extractable text")
        return text

    def get_document(self, document_id: UUID) -> DocumentResponse:
        document = self._documents.get(document_id)
        if document is None:
            raise KeyError("Document not found")
        return document

    def delete_document(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse:
        del idempotency_key, principal
        with self._lock:
            document = self.get_document(document_id)
            updated = document.model_copy(
                update={
                    "status": "DELETED",
                    "progress": 100,
                    "status_message": "Logical deletion recorded; object cleanup requested",
                    "report": None,
                }
            )
            self._documents[document_id] = updated
            return updated

    def memory_trace(self) -> list[MemoryTraceItem]:
        now = utc_now()
        items: list[MemoryTraceItem] = []
        for memory in self._memories:
            trust = calculate_trust_score(
                memory, now=now, vector_similarity=0.96, subject_match=True
            )
            excluded = trust == 0.0
            reason = None
            if memory.verification_status == "SUPERSEDED":
                reason = "Superseded by a later clinician-verified correction"
            elif memory.verification_status == "REJECTED":
                reason = "Rejected evidence cannot influence a new run"
            elif memory.verification_status == "EXPIRED":
                reason = "Memory is outside its validity window"
            items.append(
                MemoryTraceItem(
                    id=memory.id,
                    title=memory.title,
                    content=memory.content,
                    source_type=memory.source_type,
                    source_label=memory.source_label,
                    verification_status=memory.verification_status,
                    confidence=memory.confidence,
                    trust_score=round(trust, 4),
                    disposition="EXCLUDED"
                    if excluded
                    else (
                        "USED"
                        if memory.source_type in {"CLINICIAN_CORRECTION", "REVIEWER_STATEMENT"}
                        else "SUPPORTING"
                    ),
                    disposition_reason=reason,
                    created_at=memory.created_at,
                )
            )
        return sorted(
            items,
            key=lambda item: (
                item.disposition == "EXCLUDED",
                -item.trust_score,
                item.title,
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
        with self._lock:
            existing_id = self._run_keys.get(idempotency_key)
            if existing_id is not None:
                return self._runs[existing_id]
            trace = self.memory_trace()
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
            prior_review = any(
                memory.source_type == "REVIEWER_STATEMENT"
                and memory.verification_status == "VERIFIED"
                for memory in self._memories
            )
            hip_series = []
            for report in sorted(self._reports, key=lambda item: item.scan_date):
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
            hip_summary = ", ".join(hip_series)
            decision = AgentDecision(
                summary=(
                    f"The comparable left total hip series is {hip_summary} g/cm2. "
                    "Lumbar values marked for review remain visible as source evidence "
                    "but are excluded from the longitudinal comparison."
                ),
                uncertainty=(
                    "Scanner metadata still needs human confirmation. Measurement "
                    "differences are presented without diagnostic interpretation."
                ),
                safety_notice=SAFETY_NOTICE,
                evidence=evidence,
                proposed_action=ProposedAction(
                    action_type=("NO_ACTION" if prior_review else "CREATE_CLINICIAN_REVIEW"),
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
                    payload={
                        "focus": "scanner metadata",
                        "site": "left total hip",
                    },
                    requires_human_approval=not prior_review,
                ),
                memory_impact_statement=(
                    "A verified prior review and the lumbar correction were retrieved "
                    "from durable memory and changed this comparison."
                    if prior_review
                    else (
                        "The verified lumbar correction changed which skeletal sites were compared."
                    )
                ),
                counterfactual_without_key_memory=(
                    "Without the verified correction, the lumbar value would have been "
                    "included even though it was previously marked unsuitable."
                ),
            )
            assert_safe_text(
                decision.summary,
                decision.uncertainty,
                decision.memory_impact_statement,
            )
            run_id = uuid4()
            task_id: UUID | None = None
            if decision.proposed_action.action_type != "NO_ACTION":
                task_id = uuid4()
                self._tasks[task_id] = ReviewTask(
                    id=task_id,
                    agent_run_id=run_id,
                    action_type=decision.proposed_action.action_type,
                    status="AWAITING_REVIEW",
                    title=decision.proposed_action.title,
                    proposed_payload=decision.proposed_action.payload,
                    evidence_memory_ids=[
                        item.id for item in trace if item.disposition != "EXCLUDED"
                    ],
                    requires_role="CLINICIAN",
                    created_at=utc_now(),
                )
            result = AgentRunResponse(
                id=run_id,
                subject_id=DEMO_SUBJECT_ID,
                status="SUCCEEDED",
                request_type=request_type,
                decision=decision,
                memory_trace=trace,
                review_task_id=task_id,
                created_at=utc_now(),
                persisted_review_applied=prior_review,
            )
            self._runs[run_id] = result
            self._run_keys[idempotency_key] = run_id
            return result

    def get_run(self, run_id: UUID) -> AgentRunResponse:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError("Agent run not found")
        return run

    def list_tasks(self) -> list[ReviewTask]:
        return sorted(self._tasks.values(), key=lambda task: task.created_at, reverse=True)

    def get_task(self, task_id: UUID) -> ReviewTask:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError("Task not found")
        return task

    def resolve_task(
        self,
        task_id: UUID,
        *,
        decision: Literal["approve", "correct", "reject"],
        payload: ReviewDecisionRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> ReviewTask:
        del principal
        with self._lock:
            replay_id = self._action_keys.get(idempotency_key)
            if replay_id is not None:
                return self.get_task(replay_id)
            task = self.get_task(task_id)
            if task.status not in {"PROPOSED", "AWAITING_REVIEW"}:
                return task
            now = utc_now()
            status = {
                "approve": "APPLIED",
                "correct": "APPLIED",
                "reject": "REJECTED",
            }[decision]
            applied: dict[str, Any] = {
                "decision": decision.upper(),
                "note": payload.note,
            }
            if decision == "correct":
                if not payload.corrected_title or not payload.corrected_content:
                    raise ValueError("a correction requires corrected title and content")
                applied.update(
                    {
                        "corrected_title": payload.corrected_title,
                        "corrected_content": payload.corrected_content,
                    }
                )
            updated = task.model_copy(
                update={
                    "status": status,
                    "applied_payload": applied,
                    "resolved_at": now,
                    "resolution_note": payload.note,
                }
            )
            self._tasks[task_id] = updated
            self._action_keys[idempotency_key] = task_id
            self._memories.append(
                MemoryState(
                    id=uuid4(),
                    title=(
                        payload.corrected_title
                        if decision == "correct"
                        else (
                            "Scanner comparison review approved"
                            if decision == "approve"
                            else "Scanner comparison proposal rejected"
                        )
                    )
                    or "Review decision",
                    content=(
                        payload.corrected_content
                        if decision == "correct"
                        else (
                            "A clinician approved using the documented hip comparison "
                            "with its source and uncertainty notes."
                            if decision == "approve"
                            else "A clinician rejected the proposed scanner-comparison action."
                        )
                    )
                    or "",
                    source_type="REVIEWER_STATEMENT",
                    source_label=f"Clinician review · {now:%b %d, %Y}",
                    verification_status="VERIFIED" if decision != "reject" else "REJECTED",
                    confidence=1.0,
                    created_at=now,
                    valid_from=now,
                )
            )
            return updated

    def transparency(self) -> TransparencyResponse:
        return TransparencyResponse(
            mode="LOCAL_MOCK",
            database={
                "service": "CockroachDB",
                "role": "System of record in production; Phase 1 integration verified locally",
                "vector": "VECTOR(1024) with subject-prefixed cosine index",
            },
            document_pipeline=[
                {"step": "Storage", "service": "Local synthetic adapter → Amazon S3"},
                {"step": "Extraction", "service": "Mock Textract → Amazon Textract"},
                {"step": "PHI screening", "service": "Mock DetectPHI → Comprehend Medical"},
                {"step": "Workflow", "service": "Local orchestration → AWS Step Functions"},
            ],
            memory_engine=[
                {"step": "Embedding", "service": "Deterministic 1,024-D local vector"},
                {"step": "Retrieval", "service": "Hybrid trust + timeline additions"},
                {"step": "Review", "service": "Idempotent human-approved action"},
            ],
            agent={
                "runtime": "Deterministic local adapter → Bedrock AgentCore",
                "prompt": "system-v1",
                "output": "Strict AgentDecision schema",
            },
            audit_event_count=len(self._audit_events),
            safety_boundary=SAFETY_NOTICE,
        )


def _report(
    report_id: str,
    document_id: str,
    scan_date: date,
    bmd: float,
    t_score: float,
    label: str,
) -> Report:
    report_uuid = UUID(report_id)
    return Report(
        id=report_uuid,
        document_id=UUID(document_id),
        scan_date=scan_date,
        report_type="DXA_BMD",
        facility_pseudonym=f"Synthetic Imaging Center · {label}",
        scanner_manufacturer="Hologic",
        scanner_model="Synthetic Discovery",
        parser_name="bonetwin-seed",
        parser_version="1.0.0",
        extraction_confidence=0.99,
        review_required=False,
        measurements=[
            Measurement(
                id=uuid4(),
                report_id=report_uuid,
                skeletal_site="HIP",
                region="TOTAL_HIP",
                side="LEFT",
                bmd_g_cm2=bmd,
                t_score=t_score,
                z_score=None,
                confidence=0.99,
                source_page=1,
                source_text=f"Left total hip BMD {bmd:.3f}; T-score {t_score:.1f}",
                usable_for_longitudinal=True,
                verification_status="VERIFIED",
            )
        ],
    )


demo_store = DemoStore()
