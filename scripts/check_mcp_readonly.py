"""Fail closed when the MCP role or curated-view boundary is too broad."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Connection, text

from services.api.app.db.engine import create_database_engine

MCP_ROLE = "bonetwin_mcp_reader"
MCP_VIEWS = {
    "mcp_subject_memory_trace",
    "mcp_agent_run_trace",
    "mcp_open_review_tasks",
}
FORBIDDEN_COLUMNS = {
    "content",
    "embedding",
    "metadata",
    "source_text",
    "source_bbox",
    "user_query",
    "proposed_payload",
    "applied_payload",
}
FORBIDDEN_PRIVILEGES = {
    "ALL",
    "CREATE",
    "DELETE",
    "DROP",
    "INSERT",
    "UPDATE",
    "ZONECONFIG",
}


def _strings(values: Iterable[object]) -> set[str]:
    return {str(value) for value in values}


def audit_mcp_boundary(connection: Connection) -> dict[str, object]:
    """Return a redaction-safe privilege summary or raise on overexposure."""
    columns = connection.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN (
                  'mcp_subject_memory_trace',
                  'mcp_agent_run_trace',
                  'mcp_open_review_tasks'
              )
            ORDER BY table_name, ordinal_position
            """
        )
    ).all()
    discovered_views = {str(row[0]) for row in columns}
    if discovered_views != MCP_VIEWS:
        raise RuntimeError("MCP view set is missing or unexpected")
    exposed_columns = _strings(row[1] for row in columns)
    forbidden_exposure = exposed_columns & FORBIDDEN_COLUMNS
    if forbidden_exposure:
        raise RuntimeError(f"MCP views expose forbidden columns: {sorted(forbidden_exposure)}")

    grants = connection.execute(
        text(
            """
            SELECT table_name, privilege_type
            FROM information_schema.table_privileges
            WHERE grantee = :role
            ORDER BY table_name, privilege_type
            """
        ),
        {"role": MCP_ROLE},
    ).all()
    granted_views = {str(row[0]) for row in grants}
    granted_privileges = _strings(row[1] for row in grants)
    if granted_views != MCP_VIEWS or granted_privileges != {"SELECT"}:
        raise RuntimeError("MCP role must have SELECT on exactly the curated views")
    if granted_privileges & FORBIDDEN_PRIVILEGES:
        raise RuntimeError("MCP role has a state-changing privilege")

    return {
        "role": MCP_ROLE,
        "views": sorted(discovered_views),
        "privileges": sorted(granted_privileges),
        "forbidden_columns_exposed": [],
    }


def main() -> int:
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            result = audit_mcp_boundary(connection)
    finally:
        engine.dispose()
    views = result["views"]
    if not isinstance(views, list):
        raise RuntimeError("MCP audit returned an invalid view summary")
    print(f"MCP boundary passed: role={result['role']}, views={len(views)}, privileges=SELECT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
