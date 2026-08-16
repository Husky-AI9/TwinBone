"""Narrow administrative helpers for local migration setup."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

DATABASE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def database_name_from_url(database_url: str) -> str:
    """Extract and validate the database name from a connection URL."""
    database_name = urlsplit(database_url).path.removeprefix("/")
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("DATABASE_URL must contain a simple lowercase database name")
    return database_name


def connection_url_for_database(database_url: str, database_name: str) -> str:
    """Return a Psycopg-compatible URL targeting a different database."""
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("database_name is not a safe SQL identifier")
    parsed = urlsplit(database_url)
    scheme = "postgresql" if parsed.scheme.startswith("cockroachdb") else parsed.scheme
    return urlunsplit((scheme, parsed.netloc, f"/{database_name}", parsed.query, parsed.fragment))


def ensure_database(database_url: str) -> str:
    """Create the configured application database if it does not already exist."""
    database_name = database_name_from_url(database_url)
    admin_url = connection_url_for_database(database_url, "defaultdb")
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE IF NOT EXISTS {}").format(sql.Identifier(database_name))
        )
    return database_name


def enable_vector_indexes(database_url: str) -> None:
    """Enable CockroachDB's cluster-wide vector index feature before migration."""
    admin_url = connection_url_for_database(database_url, "defaultdb")
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute("SET CLUSTER SETTING feature.vector_index.enabled = true")
