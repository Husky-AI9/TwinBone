"""Deterministic trust scoring and local embedding behavior."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime
from typing import Protocol

SOURCE_WEIGHTS = {
    "CLINICIAN_CORRECTION": 1.0,
    "SOURCE_REPORT": 0.92,
    "REVIEWER_STATEMENT": 0.85,
    "PATIENT_STATEMENT": 0.70,
    "PARSER_INFERENCE": 0.65,
    "AGENT_OBSERVATION": 0.40,
}


class TrustMemory(Protocol):
    source_type: str
    verification_status: str
    valid_from: datetime | None
    valid_until: datetime | None
    created_at: datetime


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def temporal_decay(origin: datetime, now: datetime) -> float:
    """Use a slow ten-year half-life suitable for longitudinal records."""
    years = max(0.0, (now - origin).total_seconds() / (365.25 * 24 * 60 * 60))
    return float(0.5 ** (years / 10.0))


def calculate_trust_score(
    memory: TrustMemory,
    *,
    now: datetime,
    vector_similarity: float,
    subject_match: bool,
) -> float:
    if memory.verification_status in {"REJECTED", "SUPERSEDED", "EXPIRED"}:
        return 0.0
    if memory.valid_until and memory.valid_until <= now:
        return 0.0
    verification_weight = {
        "VERIFIED": 1.0,
        "AWAITING_REVIEW": 0.65,
        "PROPOSED": 0.45,
    }.get(memory.verification_status, 0.0)
    return clamp01(
        vector_similarity
        * verification_weight
        * SOURCE_WEIGHTS.get(memory.source_type, 0.4)
        * temporal_decay(memory.valid_from or memory.created_at, now)
        * (1.0 if subject_match else 0.35)
    )


def deterministic_embedding(text: str, dimensions: int = 1024) -> list[float]:
    """Create a normalized local vector without sending content to a model service."""
    if dimensions != 1024:
        raise ValueError("BoneTwin embeddings must contain 1,024 dimensions")
    digest = hashlib.shake_256(text.encode("utf-8")).digest(dimensions * 2)
    values = [
        (int.from_bytes(digest[index : index + 2], "big") / 32767.5) - 1.0
        for index in range(0, len(digest), 2)
    ]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
