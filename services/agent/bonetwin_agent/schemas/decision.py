"""Strict schemas for validated agent input and output."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentInput(StrictModel):
    request_id: UUID
    tenant_id: UUID
    subject_id: UUID
    user_id: UUID
    role: Literal["PATIENT", "CLINICIAN", "JUDGE"]
    request_type: Literal["COMPARE_REPORTS", "EXPLAIN_MEMORY", "PREPARE_VISIT", "REVIEW_OPEN_TASKS"]
    query: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class EvidenceReference(StrictModel):
    memory_id: UUID
    source_type: str = Field(min_length=1, max_length=80)
    source_id: UUID | None = None
    role: Literal["PRIMARY", "SUPPORTING", "EXCLUDED"]
    exclusion_reason: str | None = Field(
        default=None,
        max_length=240,
        description=(
            "Required text when role is EXCLUDED; otherwise JSON null or omitted. "
            "Never use the string 'null'."
        ),
    )

    @model_validator(mode="after")
    def validate_exclusion(self) -> EvidenceReference:
        if self.role == "EXCLUDED" and not self.exclusion_reason:
            raise ValueError("excluded evidence requires an exclusion reason")
        if self.role != "EXCLUDED" and self.exclusion_reason:
            raise ValueError("included evidence cannot have an exclusion reason")
        return self


class ProposedAction(StrictModel):
    action_type: Literal[
        "CREATE_CLINICIAN_REVIEW",
        "REQUEST_MISSING_REPORT",
        "REQUEST_DATE_CONFIRMATION",
        "PREPARE_APPOINTMENT_QUESTIONS",
        "NO_ACTION",
    ]
    title: str = Field(min_length=1, max_length=160)
    rationale: str = Field(min_length=1, max_length=500)
    payload: dict[str, Any]
    requires_human_approval: bool = True


class AgentDecision(StrictModel):
    summary: str = Field(min_length=1, max_length=1200)
    uncertainty: str = Field(min_length=1, max_length=500)
    safety_notice: str = Field(min_length=1, max_length=300)
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=30)
    proposed_action: ProposedAction
    memory_impact_statement: str = Field(min_length=1, max_length=500)
    counterfactual_without_key_memory: str | None = Field(default=None, max_length=500)
