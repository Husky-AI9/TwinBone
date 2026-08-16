"""Safe serialization for fixed-dimension CockroachDB VECTOR parameters."""

from __future__ import annotations

import math
from collections.abc import Sequence

EMBEDDING_DIMENSIONS = 1024


def vector_literal(values: Sequence[float]) -> str:
    """Validate and serialize a vector for an explicit SQL VECTOR cast."""
    if len(values) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"embedding must contain exactly {EMBEDDING_DIMENSIONS} values")

    serialized: list[str] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("embedding values must be finite")
        serialized.append(format(number, ".9g"))
    return f"[{','.join(serialized)}]"
