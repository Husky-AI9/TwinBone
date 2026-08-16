"""Tenant- and subject-scoped subject reads."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Connection, text

from services.api.app.auth import AccessScope


@dataclass(frozen=True, slots=True)
class SubjectRecord:
    id: UUID
    tenant_id: UUID
    pseudonym: str
    status: str


class SubjectRepository:
    """Read subjects only through a complete authorization scope."""

    def get(self, connection: Connection, scope: AccessScope) -> SubjectRecord | None:
        row = (
            connection.execute(
                text(
                    """
                    SELECT id, tenant_id, pseudonym, status
                    FROM subjects
                    WHERE tenant_id = :tenant_id AND id = :subject_id
                    """
                ),
                {
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return SubjectRecord(
            id=row["id"],
            tenant_id=row["tenant_id"],
            pseudonym=row["pseudonym"],
            status=row["status"],
        )
