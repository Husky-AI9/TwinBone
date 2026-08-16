"""Create the subject-prefixed cosine vector index."""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0002_memory_vector_index"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def _execute_sql_file(filename: str) -> None:
    sql = (MIGRATIONS / filename).read_text(encoding="utf-8")
    for statement in sql.split(";\n"):
        if stripped := statement.strip():
            op.execute(sa.text(stripped))


def upgrade() -> None:
    _execute_sql_file("0002_memory_vector_index.sql")


def downgrade() -> None:
    _execute_sql_file("0002_memory_vector_index.down.sql")
