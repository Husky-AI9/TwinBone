"""CockroachDB SQLAlchemy engine construction."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from services.api.app.config import Settings, get_settings


def normalize_database_url(database_url: str) -> str:
    """Select CockroachDB's SQLAlchemy dialect with the Psycopg 3 driver."""
    prefixes = (
        "postgres://",
        "postgresql://",
        "cockroachdb://",
        "cockroachdb+psycopg://",
    )
    if not database_url.startswith(prefixes):
        raise ValueError("DATABASE_URL must use a PostgreSQL or CockroachDB URL")
    for prefix in prefixes[:-1]:
        if database_url.startswith(prefix):
            return database_url.replace(prefix, "cockroachdb+psycopg://", 1)
    return database_url


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create a pooled engine without logging credential-bearing connection details."""
    active_settings = settings or get_settings()
    return create_engine(
        normalize_database_url(active_settings.reveal_database_url()),
        pool_pre_ping=True,
        future=True,
    )
