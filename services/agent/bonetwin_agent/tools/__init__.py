"""Narrow agent tool registry."""

from services.agent.bonetwin_agent.tools.registry import (
    ALLOWED_TOOLS,
    execute_allowlisted_tool,
)

__all__ = ["ALLOWED_TOOLS", "execute_allowlisted_tool"]
