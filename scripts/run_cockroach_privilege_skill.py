"""Run the official CockroachDB hardening-user-privileges audit workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from services.api.app.db.engine import create_database_engine

OFFICIAL_SKILL = (
    "cockroachlabs/cockroachdb-skills/"
    "cockroachdb-security-and-governance/hardening-user-privileges@1.0"
)
SENSITIVE_SYSTEM_PRIVILEGES = {
    "CANCELQUERY",
    "CANCELSESSION",
    "CREATELOGIN",
    "CREATEDB",
    "MODIFYCLUSTERSETTING",
    "VIEWACTIVITY",
}
WRITE_PRIVILEGES = {"ALL", "DELETE", "INSERT", "UPDATE"}


def run_privilege_audit(connection: Connection) -> dict[str, Any]:
    """Execute the skill's audit and verification queries without changing grants."""
    current_user = str(connection.execute(text("SELECT current_user()")).scalar_one())
    admin_count = int(
        connection.execute(
            text("SELECT count(*) FROM [SHOW GRANTS ON ROLE admin] WHERE is_admin = true")
        ).scalar_one()
    )
    public_grants = connection.execute(
        text(
            """
            SELECT database_name, schema_name, object_name, privilege_type
            FROM [SHOW GRANTS FOR public]
            WHERE privilege_type != 'USAGE'
            ORDER BY database_name, schema_name, object_name, privilege_type
            """
        )
    ).all()
    system_grants = connection.execute(
        text(
            """
            SELECT grantee, privilege_type
            FROM [SHOW SYSTEM GRANTS]
            ORDER BY grantee, privilege_type
            """
        )
    ).all()
    mcp_grants = connection.execute(
        text(
            """
            SELECT table_name, privilege_type
            FROM information_schema.table_privileges
            WHERE grantee = 'bonetwin_mcp_reader'
            ORDER BY table_name, privilege_type
            """
        )
    ).all()

    sensitive_system_grants = [
        {"role": str(row[0]), "privilege": str(row[1])}
        for row in system_grants
        if str(row[1]) in SENSITIVE_SYSTEM_PRIVILEGES
    ]
    mcp_write_grants = [
        {"view": str(row[0]), "privilege": str(row[1])}
        for row in mcp_grants
        if str(row[1]) in WRITE_PRIVILEGES
    ]
    public_mcp_grants = [
        {
            "database": str(row[0]),
            "schema": str(row[1]),
            "object": str(row[2]),
            "privilege": str(row[3]),
        }
        for row in public_grants
        if str(row[2]).startswith("mcp_")
    ]
    return {
        "skill": OFFICIAL_SKILL,
        "environment": "local synthetic CockroachDB",
        "current_user_is_admin": current_user == "root",
        "admin_member_count": admin_count,
        "sensitive_system_grants": sensitive_system_grants,
        "public_mcp_grants": public_mcp_grants,
        "mcp_write_grants": mcp_write_grants,
        "mcp_select_view_count": sum(str(row[1]) == "SELECT" for row in mcp_grants),
        "finding": (
            "Use a purpose-specific role and revoke PUBLIC access from MCP views; "
            "do not reuse the migration administrator."
        ),
        "remediation": (
            "Migration 0003 creates bonetwin_mcp_reader, grants SELECT on three "
            "curated views only, and revokes PUBLIC access."
        ),
        "passed": (
            len(public_mcp_grants) == 0
            and len(mcp_write_grants) == 0
            and sum(str(row[1]) == "SELECT" for row in mcp_grants) == 3
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional redacted JSON evidence path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            result = run_privilege_audit(connection)
    finally:
        engine.dispose()

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote redacted Agent Skill evidence to {args.output}")
    else:
        print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
