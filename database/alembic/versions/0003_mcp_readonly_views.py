"""Create limited MCP views and a purpose-specific read-only role."""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0003_mcp_readonly_views"
down_revision = "0002_memory_vector_index"
branch_labels = None
depends_on = None

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def _execute_sql_file(filename: str) -> None:
    sql = (MIGRATIONS / filename).read_text(encoding="utf-8")
    for statement in sql.split(";\n"):
        if stripped := statement.strip():
            op.execute(sa.text(stripped))


def upgrade() -> None:
    _execute_sql_file("0003_mcp_readonly_views.sql")


def downgrade() -> None:
    _execute_sql_file("0003_mcp_readonly_views.down.sql")
