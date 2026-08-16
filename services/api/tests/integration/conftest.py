from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import Engine

from scripts.seed import execute_sql_file
from services.api.app.config import get_settings
from services.api.app.db.admin import (
    connection_url_for_database,
    enable_vector_indexes,
    ensure_database,
)
from services.api.app.db.engine import create_database_engine

TEST_DATABASE_NAME = "bonetwin_test"
SEED_FILE = Path(__file__).resolve().parents[4] / "database" / "seed" / "phase1.sql"


def _integration_enabled() -> bool:
    return os.getenv("BONETWIN_RUN_DB_TESTS") == "1"


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    if not _integration_enabled():
        pytest.skip("set BONETWIN_RUN_DB_TESTS=1 to run CockroachDB integration tests")

    base_url = get_settings().reveal_database_url()
    test_url = connection_url_for_database(base_url, TEST_DATABASE_NAME)
    admin_url = connection_url_for_database(base_url, "defaultdb")
    if TEST_DATABASE_NAME != "bonetwin_test":
        raise RuntimeError("integration cleanup is restricted to bonetwin_test")

    try:
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} CASCADE").format(
                    sql.Identifier(TEST_DATABASE_NAME)
                )
            )
    except psycopg.Error:
        raise RuntimeError(
            "CockroachDB test setup could not connect; verify credentials and TLS settings"
        ) from None

    ensure_database(test_url)
    enable_vector_indexes(test_url)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_database_engine()
    with engine.begin() as connection:
        execute_sql_file(connection, SEED_FILE)

    yield engine
    engine.dispose()
    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url
    get_settings.cache_clear()
