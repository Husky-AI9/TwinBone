"""Application-level medical safety checks independent of model guardrails."""

from __future__ import annotations

PROHIBITED_DIRECTIVES = (
    "you have osteoporosis",
    "you have osteopenia",
    "start medication",
    "stop medication",
    "increase your dose",
    "decrease your dose",
    "fracture risk is",
)

SAFETY_NOTICE = (
    "BoneTwin organizes source-backed records for human review. "
    "It does not diagnose, predict fractures, or recommend treatment."
)


def assert_safe_text(*values: str) -> None:
    """Reject known diagnostic and treatment directives after model validation."""
    combined = " ".join(values).casefold()
    if any(phrase in combined for phrase in PROHIBITED_DIRECTIVES):
        raise ValueError("agent output crossed the medical safety boundary")
