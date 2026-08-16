"""BoneTwin FastAPI application for local demo and cloud adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from services.api.app import PRODUCT_NAME, SAFETY_BOUNDARY
from services.api.app.auth import (
    DEMO_SUBJECT_ID,
    Principal,
    get_current_principal,
    require_role,
    require_subject,
)
from services.api.app.config import get_settings
from services.api.app.models import UserRole
from services.api.app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    CompleteUploadRequest,
    CreateSubjectRequest,
    DashboardResponse,
    DemoDataResetResponse,
    DocumentResponse,
    MemoryTraceItem,
    MeResponse,
    ReviewDecisionRequest,
    ReviewTask,
    SubjectSummary,
    TimelineResponse,
    TransparencyResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)
from services.api.app.services import workflow_store

settings = get_settings()
DEMO_DOCUMENT_DIRECTORY = Path(__file__).resolve().parents[3] / "output" / "pdf"
DEMO_DOCUMENTS = {
    "bonetwin-demo-dxa-2019.pdf",
    "bonetwin-demo-dxa-2022.pdf",
    "bonetwin-demo-dxa-2026.pdf",
}
app = FastAPI(
    title=PRODUCT_NAME,
    version="0.7.0",
    description=(
        "Synthetic-only API for source-backed longitudinal record organization and review."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)

PrincipalDependency = Annotated[Principal, Depends(get_current_principal)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        description="Stable key for replay-safe state changes",
    ),
]


@app.middleware("http")
async def audit_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach a request ID and record metadata without request/response bodies."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    actor = "authenticated" if request.headers.get("Authorization") else "anonymous"
    try:
        response = await call_next(request)
    except Exception:
        workflow_store.record_http_audit(
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            outcome="FAILED",
            actor=actor,
        )
        raise
    if request.url.path.startswith("/v1/"):
        workflow_store.record_http_audit(
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            outcome=(
                "SUCCESS"
                if response.status_code < 400
                else ("DENIED" if response.status_code in {401, 403, 404} else "FAILED")
            ),
            actor=actor,
        )
    response.headers["X-Request-ID"] = request_id
    return response


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live", "service": "bonetwin-api"}


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    return workflow_store.health() | {
        "document_pipeline": settings.aws_document_pipeline_mode,
        "auth": settings.auth_mode,
    }


@app.get("/demo-documents/{filename}", response_class=FileResponse)
def demo_document(filename: str) -> FileResponse:
    """Serve only the three checked-in, plainly synthetic local demo reports."""
    if filename not in DEMO_DOCUMENTS:
        raise not_found("Demo document not found")
    path = DEMO_DOCUMENT_DIRECTORY / filename
    if not path.is_file():
        raise not_found("Demo document not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.get("/v1/me", response_model=MeResponse)
def me(principal: PrincipalDependency) -> MeResponse:
    return MeResponse(
        id=principal.user_id,
        tenant_id=principal.tenant_id,
        role=principal.role.value,
        display_name=principal.display_name,
        demo_mode=settings.auth_mode == "mock",
    )


@app.get("/v1/subjects", response_model=list[SubjectSummary])
def list_subjects(principal: PrincipalDependency) -> list[SubjectSummary]:
    if DEMO_SUBJECT_ID not in principal.allowed_subject_ids:
        return []
    return [workflow_store.subject_summary()]


@app.post(
    "/v1/subjects",
    response_model=SubjectSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: CreateSubjectRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> SubjectSummary:
    require_role(principal, UserRole.CLINICIAN, UserRole.ADMIN)
    del idempotency_key
    if payload.pseudonym != "SYNTH-BONE-001":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The local demo is intentionally limited to one synthetic subject",
        )
    return workflow_store.subject_summary()


@app.get("/v1/subjects/{subject_id}", response_model=SubjectSummary)
def get_subject(subject_id: UUID, principal: PrincipalDependency) -> SubjectSummary:
    require_subject(principal, subject_id)
    return workflow_store.subject_summary()


@app.get("/v1/subjects/{subject_id}/timeline", response_model=TimelineResponse)
def get_timeline(subject_id: UUID, principal: PrincipalDependency) -> TimelineResponse:
    require_subject(principal, subject_id)
    return workflow_store.timeline()


@app.get("/v1/subjects/{subject_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(subject_id: UUID, principal: PrincipalDependency) -> DashboardResponse:
    """Return the on-demand dashboard snapshot in one Lambda invocation."""
    require_subject(principal, subject_id)
    return DashboardResponse(
        timeline=workflow_store.timeline(),
        tasks=workflow_store.list_tasks(),
        transparency=workflow_store.transparency(),
    )


@app.delete(
    "/v1/subjects/{subject_id}/demo-data",
    response_model=DemoDataResetResponse,
)
def clear_demo_data(
    subject_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DemoDataResetResponse:
    """Clear only the authorized synthetic demo subject from the active store."""
    require_subject(principal, subject_id)
    require_role(principal, UserRole.CLINICIAN, UserRole.ADMIN)
    if (
        settings.app_env != "local"
        or settings.auth_mode != "mock"
        or principal.cognito_subject != "demo-clinician"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo data reset is available only to the local demo clinician",
        )
    return workflow_store.clear_demo_data(idempotency_key, principal)


@app.post(
    "/v1/subjects/{subject_id}/documents/upload-intent",
    response_model=UploadIntentResponse,
)
def upload_intent(
    subject_id: UUID,
    payload: UploadIntentRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> UploadIntentResponse:
    require_subject(principal, subject_id)
    try:
        return workflow_store.create_upload_intent(payload, idempotency_key, principal)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.put("/v1/local-uploads/{document_id}", response_model=DocumentResponse)
def local_upload(
    document_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    content: Annotated[bytes, Body(media_type="application/octet-stream")],
) -> DocumentResponse:
    try:
        document = workflow_store.get_document(document_id)
        require_subject(principal, document.subject_id)
        return workflow_store.accept_local_upload(document_id, content, idempotency_key, principal)
    except KeyError as error:
        raise not_found("Document not found") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@app.post("/v1/documents/{document_id}/complete-upload", response_model=DocumentResponse)
def complete_upload(
    document_id: UUID,
    payload: CompleteUploadRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DocumentResponse:
    del payload
    try:
        document = workflow_store.get_document(document_id)
        require_subject(principal, document.subject_id)
        if document.status == "UPLOADING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload bytes must be accepted before processing",
            )
        return workflow_store.complete_upload(document_id, idempotency_key, principal)
    except KeyError as error:
        raise not_found("Document not found") from error


@app.get("/v1/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, principal: PrincipalDependency) -> DocumentResponse:
    try:
        document = workflow_store.get_document(document_id)
        require_subject(principal, document.subject_id)
        return document
    except KeyError as error:
        raise not_found("Document not found") from error


@app.post("/v1/documents/{document_id}/confirm-redaction", response_model=DocumentResponse)
def confirm_redaction(
    document_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DocumentResponse:
    require_role(principal, UserRole.CLINICIAN, UserRole.ADMIN)
    return get_document(document_id, principal)


@app.delete("/v1/documents/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> DocumentResponse:
    try:
        document = workflow_store.get_document(document_id)
        require_subject(principal, document.subject_id)
        return workflow_store.delete_document(document_id, idempotency_key, principal)
    except KeyError as error:
        raise not_found("Document not found") from error


@app.post("/v1/subjects/{subject_id}/agent/runs", response_model=AgentRunResponse)
def create_agent_run(
    subject_id: UUID,
    payload: AgentRunRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> AgentRunResponse:
    require_subject(principal, subject_id)
    if principal.role not in {UserRole.PATIENT, UserRole.CLINICIAN, UserRole.JUDGE}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return workflow_store.run_agent(
        principal=principal,
        request_type=payload.request_type,
        query=payload.query,
        idempotency_key=idempotency_key,
    )


@app.get("/v1/agent/runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(run_id: UUID, principal: PrincipalDependency) -> AgentRunResponse:
    try:
        run = workflow_store.get_run(run_id)
        require_subject(principal, run.subject_id)
        return run
    except KeyError as error:
        raise not_found("Agent run not found") from error


@app.get(
    "/v1/agent/runs/{run_id}/memory-impact",
    response_model=list[MemoryTraceItem],
)
def get_memory_impact(run_id: UUID, principal: PrincipalDependency) -> list[MemoryTraceItem]:
    return get_agent_run(run_id, principal).memory_trace


@app.get("/v1/subjects/{subject_id}/tasks", response_model=list[ReviewTask])
def list_tasks(subject_id: UUID, principal: PrincipalDependency) -> list[ReviewTask]:
    require_subject(principal, subject_id)
    return workflow_store.list_tasks()


@app.get("/v1/tasks/{task_id}", response_model=ReviewTask)
def get_task(task_id: UUID, principal: PrincipalDependency) -> ReviewTask:
    try:
        task = workflow_store.get_task(task_id)
        require_subject(principal, DEMO_SUBJECT_ID)
        return task
    except KeyError as error:
        raise not_found("Task not found") from error


def resolve_task(
    *,
    task_id: UUID,
    action: Literal["approve", "correct", "reject"],
    payload: ReviewDecisionRequest,
    principal: Principal,
    idempotency_key: str,
) -> ReviewTask:
    require_role(principal, UserRole.CLINICIAN, UserRole.ADMIN)
    get_task(task_id, principal)
    try:
        return workflow_store.resolve_task(
            task_id,
            decision=action,
            payload=payload,
            idempotency_key=idempotency_key,
            principal=principal,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


@app.post("/v1/tasks/{task_id}/approve", response_model=ReviewTask)
def approve_task(
    task_id: UUID,
    payload: ReviewDecisionRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReviewTask:
    return resolve_task(
        task_id=task_id,
        action="approve",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
    )


@app.post("/v1/tasks/{task_id}/correct", response_model=ReviewTask)
def correct_task(
    task_id: UUID,
    payload: ReviewDecisionRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReviewTask:
    return resolve_task(
        task_id=task_id,
        action="correct",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
    )


@app.post("/v1/tasks/{task_id}/reject", response_model=ReviewTask)
def reject_task(
    task_id: UUID,
    payload: ReviewDecisionRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ReviewTask:
    return resolve_task(
        task_id=task_id,
        action="reject",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
    )


@app.get("/v1/transparency", response_model=TransparencyResponse)
def transparency(principal: PrincipalDependency) -> TransparencyResponse:
    del principal
    return workflow_store.transparency()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": PRODUCT_NAME,
        "status": "API ready",
        "safety_boundary": SAFETY_BOUNDARY,
        "docs": "/docs",
    }
