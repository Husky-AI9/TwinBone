"""OpenAPI-visible contracts for the local and hosted BoneTwin API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from services.agent.bonetwin_agent.schemas import AgentDecision


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MeResponse(ApiModel):
    id: UUID
    tenant_id: UUID
    role: str
    display_name: str
    demo_mode: bool


class SubjectSummary(ApiModel):
    id: UUID
    pseudonym: str
    year_of_birth: int | None
    status: str
    report_count: int
    open_task_count: int
    latest_scan_date: date | None


class CreateSubjectRequest(ApiModel):
    pseudonym: str = Field(pattern=r"^SYNTH-[A-Z0-9-]{3,40}$")
    year_of_birth: int | None = Field(default=None, ge=1900, le=2100)


class Measurement(ApiModel):
    id: UUID
    report_id: UUID
    skeletal_site: str
    region: str
    side: str | None
    bmd_g_cm2: float
    t_score: float
    z_score: float | None
    confidence: float
    source_page: int
    source_text: str
    usable_for_longitudinal: bool
    verification_status: str


class Report(ApiModel):
    id: UUID
    document_id: UUID
    scan_date: date
    report_type: str
    facility_pseudonym: str
    scanner_manufacturer: str
    scanner_model: str
    parser_name: str
    parser_version: str
    extraction_confidence: float
    review_required: bool
    measurements: list[Measurement]


class MemoryTraceItem(ApiModel):
    id: UUID
    title: str
    content: str
    source_type: str
    source_label: str
    verification_status: str
    confidence: float
    trust_score: float
    disposition: Literal["USED", "SUPPORTING", "EXCLUDED"]
    disposition_reason: str | None = None
    created_at: datetime


class ReviewTask(ApiModel):
    id: UUID
    agent_run_id: UUID
    action_type: str
    status: str
    title: str
    proposed_payload: dict[str, Any]
    applied_payload: dict[str, Any] | None = None
    evidence_memory_ids: list[UUID]
    requires_role: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None


class TimelineResponse(ApiModel):
    subject: SubjectSummary
    reports: list[Report]
    memories: list[MemoryTraceItem]
    tasks: list[ReviewTask]
    treatment_events: list[dict[str, Any]]


class UploadIntentRequest(ApiModel):
    original_filename: str = Field(min_length=1, max_length=160)
    content_type: Literal["application/pdf", "text/plain"]
    byte_size: int = Field(ge=1, le=10_000_000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class UploadIntentResponse(ApiModel):
    document_id: UUID
    upload_url: str
    upload_method: Literal["PUT"]
    upload_headers: dict[str, str] = Field(default_factory=dict)
    expires_in_seconds: int
    duplicate: bool


class ProcessingEvent(ApiModel):
    id: str
    service: str
    operation: str
    status: Literal["RUNNING", "COMPLETED", "SAFE_FALLBACK", "FAILED"]
    detail: str


class DocumentResponse(ApiModel):
    id: UUID
    subject_id: UUID
    status: str
    original_filename: str
    content_type: str
    byte_size: int
    sha256: str
    progress: int
    status_message: str
    report: Report | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    processing_events: list[ProcessingEvent] = Field(default_factory=list)
    created_at: datetime


class DemoDataResetResponse(ApiModel):
    subject_id: UUID
    status: Literal["CLEARED"]
    database: str
    deleted_records: dict[str, int]
    replayed: bool
    reset_at: datetime


class DemoRecordDeleteResponse(ApiModel):
    subject_id: UUID
    document_id: UUID
    report_id: UUID | None
    scan_date: date | None
    status: Literal["DELETED"]
    database: str
    deleted_records: dict[str, int]
    replayed: bool
    deleted_at: datetime
    timeline: TimelineResponse


class CompleteUploadRequest(ApiModel):
    acknowledge_synthetic_only: Literal[True]


class AgentRunRequest(ApiModel):
    request_type: Literal[
        "COMPARE_REPORTS", "EXPLAIN_MEMORY", "PREPARE_VISIT", "REVIEW_OPEN_TASKS"
    ] = "COMPARE_REPORTS"
    query: str = Field(min_length=1, max_length=1000)


class AgentRunResponse(ApiModel):
    id: UUID
    subject_id: UUID
    status: str
    request_type: str
    decision: AgentDecision
    memory_trace: list[MemoryTraceItem]
    review_task_id: UUID | None
    created_at: datetime
    persisted_review_applied: bool
    processing_events: list[ProcessingEvent] = Field(default_factory=list)


class ReviewDecisionRequest(ApiModel):
    note: str = Field(default="", max_length=500)
    corrected_title: str | None = Field(default=None, max_length=160)
    corrected_content: str | None = Field(default=None, max_length=800)


class TransparencyResponse(ApiModel):
    mode: Literal["LOCAL_MOCK", "LOCAL_BEDROCK", "LOCAL_CLOUD_MCP", "AWS"]
    database: dict[str, str]
    document_pipeline: list[dict[str, str]]
    memory_engine: list[dict[str, str]]
    agent: dict[str, str]
    audit_event_count: int
    safety_boundary: str


class DashboardResponse(ApiModel):
    """One authenticated snapshot for the explicitly loaded dashboard."""

    timeline: TimelineResponse
    tasks: list[ReviewTask]
    transparency: TransparencyResponse
