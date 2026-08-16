"""Shared contract for in-memory tests and CockroachDB-backed local runtime."""

from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

from services.api.app.auth import Principal
from services.api.app.schemas import (
    AgentRunResponse,
    DemoDataResetResponse,
    DocumentResponse,
    ReviewDecisionRequest,
    ReviewTask,
    SubjectSummary,
    TimelineResponse,
    TransparencyResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)


class WorkflowStore(Protocol):
    """Application-facing durable workflow operations."""

    def health(self) -> dict[str, str]: ...

    def record_http_audit(
        self,
        *,
        method: str,
        path: str,
        request_id: str,
        outcome: str,
        actor: str,
    ) -> None: ...

    def subject_summary(self) -> SubjectSummary: ...

    def timeline(self) -> TimelineResponse: ...

    def clear_demo_data(
        self,
        idempotency_key: str,
        principal: Principal,
    ) -> DemoDataResetResponse: ...

    def create_upload_intent(
        self,
        payload: UploadIntentRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> UploadIntentResponse: ...

    def accept_local_upload(
        self,
        document_id: UUID,
        content: bytes,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse: ...

    def complete_upload(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse: ...

    def get_document(self, document_id: UUID) -> DocumentResponse: ...

    def delete_document(
        self,
        document_id: UUID,
        idempotency_key: str,
        principal: Principal,
    ) -> DocumentResponse: ...

    def run_agent(
        self,
        *,
        principal: Principal,
        request_type: str,
        query: str,
        idempotency_key: str,
    ) -> AgentRunResponse: ...

    def get_run(self, run_id: UUID) -> AgentRunResponse: ...

    def list_tasks(self) -> list[ReviewTask]: ...

    def get_task(self, task_id: UUID) -> ReviewTask: ...

    def resolve_task(
        self,
        task_id: UUID,
        *,
        decision: Literal["approve", "correct", "reject"],
        payload: ReviewDecisionRequest,
        idempotency_key: str,
        principal: Principal,
    ) -> ReviewTask: ...

    def transparency(self) -> TransparencyResponse: ...
