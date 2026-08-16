"""Manual readiness check for LangChain and CockroachDB Cloud managed MCP."""

from __future__ import annotations

from services.api.app.config import get_settings
from services.api.app.services.cockroach_mcp import (
    SELECT_TOOL_NAME,
    LangChainCockroachMcpRetriever,
)


def main() -> int:
    settings = get_settings()
    if settings.cockroach_mcp_mode != "langchain":
        raise RuntimeError("Set COCKROACH_MCP_MODE=langchain before running this check")
    retriever = LangChainCockroachMcpRetriever(settings)
    tool_names = retriever.available_tool_names()
    if SELECT_TOOL_NAME not in tool_names:
        raise RuntimeError("CockroachDB Cloud MCP did not expose select_query")
    memory_ids = retriever.allowed_memory_ids()
    print(f"CockroachDB Cloud MCP connected; server exposed {len(tool_names)} tools.")
    print("BoneTwin allowlist: select_query only.")
    print(f"Curated synthetic memory IDs retrieved: {len(memory_ids)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
