"""Create the configured database and apply all Alembic migrations."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from services.api.app.config import get_settings
from services.api.app.db.admin import enable_vector_indexes, ensure_database


def main() -> int:
    settings = get_settings()
    database_url = settings.reveal_database_url()
    database_name = ensure_database(database_url)
    enable_vector_indexes(database_url)
    command.upgrade(Config("alembic.ini"), "head")
    print(f"CockroachDB database '{database_name}' is at the latest revision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
