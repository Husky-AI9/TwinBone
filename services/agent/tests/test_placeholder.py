from services.agent.bonetwin_agent import VERIFIED_MEMORY_WRITES_ENABLED
from services.agent.bonetwin_agent.runtime import runtime_status


def test_agent_runtime_cannot_write_verified_memory() -> None:
    assert VERIFIED_MEMORY_WRITES_ENABLED is False
    assert runtime_status() == "phase-6-local-adapter-ready"
