"""Bounded retry execution for CockroachDB SERIALIZABLE transactions."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import DBAPIError

SERIALIZATION_FAILURE_SQLSTATE = "40001"
T = TypeVar("T")


class TransactionRetriesExhausted(RuntimeError):
    """Raised after all configured CockroachDB transaction attempts fail."""


def sqlstate_for_exception(error: BaseException) -> str | None:
    """Extract the PostgreSQL-compatible SQLSTATE from driver-wrapped errors."""
    candidate: object = error.orig if isinstance(error, DBAPIError) else error
    sqlstate = getattr(candidate, "sqlstate", None)
    if isinstance(sqlstate, str):
        return sqlstate
    pgcode = getattr(candidate, "pgcode", None)
    return pgcode if isinstance(pgcode, str) else None


def retry_delay(
    attempt: int,
    *,
    base_delay_seconds: float,
    max_delay_seconds: float,
    random_value: float,
) -> float:
    """Return exponential backoff with full jitter."""
    ceiling = min(max_delay_seconds, base_delay_seconds * (2**attempt))
    return float(max(0.0, ceiling * min(max(random_value, 0.0), 1.0)))


def run_transaction(
    engine: Engine,
    operation: Callable[[Connection], T],
    *,
    max_retries: int = 5,
    base_delay_seconds: float = 0.025,
    max_delay_seconds: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    random_source: Callable[[], float] = random.random,
) -> T:
    """Run an operation atomically and retry only SQLSTATE 40001 failures."""
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")

    last_error: BaseException | None = None
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection, connection.begin():
                return operation(connection)
        except DBAPIError as error:
            if sqlstate_for_exception(error) != SERIALIZATION_FAILURE_SQLSTATE:
                raise
            last_error = error
            if attempt + 1 == max_retries:
                break
            sleep(
                retry_delay(
                    attempt,
                    base_delay_seconds=base_delay_seconds,
                    max_delay_seconds=max_delay_seconds,
                    random_value=random_source(),
                )
            )

    raise TransactionRetriesExhausted(
        f"transaction did not commit after {max_retries} attempts"
    ) from last_error
