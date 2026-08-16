"""Authorization scope required by every patient-scoped repository operation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from services.api.app.models import UserRole


@dataclass(frozen=True, slots=True)
class AccessScope:
    """Immutable tenant, subject, and role boundary derived by trusted code."""

    tenant_id: UUID
    subject_id: UUID
    role: UserRole

    def __post_init__(self) -> None:
        if self.tenant_id.int == 0 or self.subject_id.int == 0:
            raise ValueError("tenant_id and subject_id must be non-zero UUIDs")
