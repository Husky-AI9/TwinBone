"""LangChain adapter for allowlisted CockroachDB Cloud MCP retrieval."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from typing import cast
from uuid import UUID

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection

from services.api.app.auth import DEMO_SUBJECT_ID, DEMO_TENANT_ID
from services.api.app.config import Settings

SERVER_NAME = "cockroachdb-cloud"
SELECT_TOOL_NAME = "select_query"
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)


class CockroachMcpError(RuntimeError):
    """Raised when the managed MCP boundary is unavailable or incompatible."""


def _text_fragments(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        fragments: list[str] = []
        for key, item in value.items():
            if key in {"text", "content", "structured_content"}:
                fragments.extend(_text_fragments(item))
        return fragments
    if isinstance(value, list | tuple):
        fragments = []
        for item in value:
            fragments.extend(_text_fragments(item))
        return fragments
    return []


class LangChainCockroachMcpRetriever:
    """Retrieve only fixed synthetic memory IDs through one allowlisted MCP tool."""

    def __init__(self, settings: Settings) -> None:
        connection: StreamableHttpConnection = {
            "transport": "streamable_http",
            "url": settings.cockroach_mcp_url,
            "headers": {
                "mcp-cluster-id": settings.cockroach_cluster_id,
                "Authorization": f"Bearer {settings.reveal_cockroach_mcp_api_key()}",
            },
            "timeout": float(settings.cockroach_mcp_timeout_seconds),
            "sse_read_timeout": float(settings.cockroach_mcp_timeout_seconds),
        }
        self._client = MultiServerMCPClient({SERVER_NAME: connection})
        self._database = settings.mcp_readonly_database

    async def _select_tool(self) -> BaseTool:
        tools = await self._client.get_tools(server_name=SERVER_NAME)
        matches = [tool for tool in tools if tool.name == SELECT_TOOL_NAME]
        if len(matches) != 1:
            names = sorted(tool.name for tool in tools)
            raise CockroachMcpError(
                f"Expected exactly one {SELECT_TOOL_NAME} MCP tool; received {names}"
            )
        return matches[0]

    @staticmethod
    def _arguments(tool: BaseTool, query: str, database: str) -> dict[str, str]:
        properties = tool.args
        arguments: dict[str, str] = {}
        if "query" in properties:
            arguments["query"] = query
        elif "sql" in properties:
            arguments["sql"] = query
        elif "statement" in properties:
            arguments["statement"] = query
        else:
            raise CockroachMcpError("CockroachDB select_query has no recognized SQL argument")
        if "database" in properties:
            arguments["database"] = database
        elif "database_name" in properties:
            arguments["database_name"] = database
        return arguments

    async def _available_tool_names(self) -> tuple[str, ...]:
        tools = await self._client.get_tools(server_name=SERVER_NAME)
        return tuple(sorted(tool.name for tool in tools))

    def available_tool_names(self) -> tuple[str, ...]:
        """Return server tool names for the manual readiness checker."""
        return asyncio.run(self._available_tool_names())

    async def _allowed_memory_ids(self) -> set[UUID]:
        tool = await self._select_tool()
        query = f"""
            SELECT memory_id::STRING AS memory_id
            FROM public.mcp_subject_memory_trace
            WHERE tenant_id = '{DEMO_TENANT_ID}'
              AND subject_id = '{DEMO_SUBJECT_ID}'
            ORDER BY memory_id
            LIMIT 100
        """.strip()
        result = cast(
            object,
            await tool.ainvoke(self._arguments(tool, query, self._database)),
        )
        identifiers = {
            UUID(match) for text in _text_fragments(result) for match in UUID_PATTERN.findall(text)
        }
        if not identifiers:
            raise CockroachMcpError("MCP retrieval returned no authorized synthetic memory IDs")
        return identifiers

    def allowed_memory_ids(self) -> set[UUID]:
        """Fail closed when MCP cannot return the curated memory ID set."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._allowed_memory_ids())
        raise CockroachMcpError("Synchronous MCP retrieval cannot run inside an event loop")
