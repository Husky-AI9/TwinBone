"""Allowlisted agent tools; application services authorize and commit mutations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ALLOWED_TOOLS = frozenset(
    {
        "retrieve_trusted_memory",
        "get_measurement_timeline",
        "get_open_review_tasks",
        "propose_review_task",
        "prepare_longitudinal_summary",
        "record_agent_observation",
    }
)


def execute_allowlisted_tool(
    name: str,
    arguments: dict[str, Any],
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    """Execute only a registered deterministic handler."""
    if name not in ALLOWED_TOOLS or name not in handlers:
        raise ValueError("agent requested a tool outside the allowlist")
    return handlers[name](arguments)
