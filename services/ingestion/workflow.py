"""Bounded idempotent execution for local document-workflow stages."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


class WorkflowStageFailed(RuntimeError):
    """Stable user-safe failure after a retryable stage exhausts attempts."""

    def __init__(self, failure_code: str, attempts: int) -> None:
        self.failure_code = failure_code
        self.attempts = attempts
        super().__init__(f"{failure_code} after {attempts} attempts")


@dataclass(slots=True)
class IdempotentStageStore(Generic[T]):
    """Keep one committed result per workflow key."""

    _results: dict[str, T] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def execute(
        self,
        idempotency_key: str,
        operation: Callable[[], T],
        *,
        max_attempts: int = 3,
        failure_code: str = "DOCUMENT_STAGE_TIMEOUT",
    ) -> T:
        if not idempotency_key or max_attempts < 1:
            raise ValueError("a key and at least one attempt are required")
        with self._lock:
            if idempotency_key in self._results:
                return self._results[idempotency_key]

        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            try:
                result = operation()
                with self._lock:
                    return self._results.setdefault(idempotency_key, result)
            except TimeoutError as error:
                if attempts == max_attempts:
                    raise WorkflowStageFailed(failure_code, attempts) from error
        raise AssertionError("unreachable")

    def committed_count(self) -> int:
        with self._lock:
            return len(self._results)
