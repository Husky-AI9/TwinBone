from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from services.agent.bonetwin_agent.runtime import validate_agent_decision
from services.agent.bonetwin_agent.tools import execute_allowlisted_tool
from services.agent.bonetwin_agent.trust import (
    calculate_trust_score,
    deterministic_embedding,
)


def valid_decision() -> dict[str, object]:
    return {
        "summary": "The source-backed hip measurements are listed for review.",
        "uncertainty": "Scanner context requires confirmation.",
        "safety_notice": "This is not a diagnosis or treatment recommendation.",
        "evidence": [
            {
                "memory_id": str(uuid4()),
                "source_type": "SOURCE_REPORT",
                "source_id": None,
                "role": "PRIMARY",
                "exclusion_reason": None,
            }
        ],
        "proposed_action": {
            "action_type": "CREATE_CLINICIAN_REVIEW",
            "title": "Confirm scanner context",
            "rationale": "The reports contain different metadata.",
            "payload": {},
            "requires_human_approval": True,
        },
        "memory_impact_statement": "A verified correction excluded the lumbar value.",
        "counterfactual_without_key_memory": "The lumbar value would otherwise appear.",
    }


def test_agent_output_is_strict_and_medically_bounded() -> None:
    assert validate_agent_decision(valid_decision()).evidence
    invalid = valid_decision()
    invalid["proposed_action"] = {
        "action_type": "START_MEDICATION",
        "title": "Unsafe",
        "rationale": "Unsafe",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        validate_agent_decision(invalid)
    unsafe = valid_decision()
    unsafe["summary"] = "You have osteoporosis."
    with pytest.raises(ValueError, match="medical safety boundary"):
        validate_agent_decision(unsafe)


def test_embedding_and_trust_filters_are_deterministic() -> None:
    embedding = deterministic_embedding("de-identified synthetic evidence")
    assert len(embedding) == 1024
    assert sum(value * value for value in embedding) == pytest.approx(1.0)
    rejected = SimpleNamespace(
        source_type="SOURCE_REPORT",
        verification_status="REJECTED",
        valid_from=None,
        valid_until=None,
        created_at=datetime.now(tz=UTC),
    )
    assert (
        calculate_trust_score(
            rejected,
            now=datetime.now(tz=UTC),
            vector_similarity=1.0,
            subject_match=True,
        )
        == 0
    )


def test_tool_registry_rejects_arbitrary_execution() -> None:
    with pytest.raises(ValueError, match="outside the allowlist"):
        execute_allowlisted_tool("run_sql", {}, {})
