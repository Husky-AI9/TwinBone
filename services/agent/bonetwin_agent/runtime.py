"""AgentCore-compatible validated runtime boundary."""

from services.agent.bonetwin_agent import IMPLEMENTATION_PHASE
from services.agent.bonetwin_agent.policies.safety import assert_safe_text
from services.agent.bonetwin_agent.schemas import AgentDecision


def runtime_status() -> str:
    """Describe the credential-free adapter without claiming cloud deployment."""
    return f"phase-{IMPLEMENTATION_PHASE}-local-adapter-ready"


def validate_agent_decision(payload: str | bytes | dict[str, object]) -> AgentDecision:
    """Reject malformed or unsafe model output before application logic uses it."""
    if isinstance(payload, dict):
        decision = AgentDecision.model_validate(payload)
    else:
        decision = AgentDecision.model_validate_json(payload)
    assert_safe_text(
        decision.summary,
        decision.uncertainty,
        decision.memory_impact_statement,
        decision.proposed_action.title,
        decision.proposed_action.rationale,
    )
    return decision
