"""Subject-scoped memory persistence and vector similarity reads."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, text

from services.api.app.auth import AccessScope
from services.api.app.config import Settings, get_settings
from services.api.app.db.retry import run_transaction
from services.api.app.db.vector import vector_literal
from services.api.app.models import ActorType, MemoryType, VerificationStatus


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: UUID
    tenant_id: UUID
    subject_id: UUID
    title: str
    content: str
    verification_status: VerificationStatus
    supersedes_id: UUID | None
    superseded_by_id: UUID | None


@dataclass(frozen=True, slots=True)
class SimilarMemory:
    memory: MemoryRecord
    cosine_distance: float


class MemoryNotFoundError(LookupError):
    """Raised when a memory is absent from the authorized subject scope."""


def content_hash(content: str) -> str:
    """Return the canonical SHA-256 digest used for memory deduplication."""
    normalized = " ".join(content.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _memory_from_mapping(row: object) -> MemoryRecord:
    mapping = row
    return MemoryRecord(
        id=mapping["id"],  # type: ignore[index]
        tenant_id=mapping["tenant_id"],  # type: ignore[index]
        subject_id=mapping["subject_id"],  # type: ignore[index]
        title=mapping["title"],  # type: ignore[index]
        content=mapping["content"],  # type: ignore[index]
        verification_status=VerificationStatus(mapping["verification_status"]),  # type: ignore[index]
        supersedes_id=mapping["supersedes_id"],  # type: ignore[index]
        superseded_by_id=mapping["superseded_by_id"],  # type: ignore[index]
    )


class MemoryRepository:
    """Persist and retrieve memory without permitting unscoped patient access."""

    _record_columns = """
        id, tenant_id, subject_id, title, content, verification_status,
        supersedes_id, superseded_by_id
    """

    def add(
        self,
        connection: Connection,
        scope: AccessScope,
        *,
        title: str,
        content: str,
        embedding: Sequence[float],
        memory_type: MemoryType = MemoryType.SEMANTIC,
        source_type: str = "SYNTHETIC_FIXTURE",
        source_id: UUID | None = None,
        confidence: Decimal = Decimal("1.0"),
        verification_status: VerificationStatus = VerificationStatus.VERIFIED,
        privacy_classification: str = "DEIDENTIFIED",
        embedding_model: str = "synthetic-test-vector-v1",
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: UUID | None = None,
        metadata: dict[str, object] | None = None,
        supersedes_id: UUID | None = None,
    ) -> MemoryRecord:
        memory_id = uuid4()
        row = (
            connection.execute(
                text(
                    f"""
                    INSERT INTO memories (
                        id, tenant_id, subject_id, memory_type, source_type, source_id,
                        title, content, content_hash, confidence, verification_status,
                        supersedes_id, privacy_classification, embedding_model, embedding,
                        metadata, created_by_actor_type, created_by_actor_id
                    ) VALUES (
                        :id, :tenant_id, :subject_id, :memory_type, :source_type, :source_id,
                        :title, :content, :content_hash, :confidence, :verification_status,
                        :supersedes_id, :privacy_classification, :embedding_model,
                        CAST(:embedding AS VECTOR(1024)), CAST(:metadata AS JSONB),
                        :actor_type, :actor_id
                    )
                    RETURNING {self._record_columns}
                    """
                ),
                {
                    "id": memory_id,
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "memory_type": memory_type.value,
                    "source_type": source_type,
                    "source_id": source_id,
                    "title": title,
                    "content": content,
                    "content_hash": content_hash(content),
                    "confidence": confidence,
                    "verification_status": verification_status.value,
                    "supersedes_id": supersedes_id,
                    "privacy_classification": privacy_classification,
                    "embedding_model": embedding_model,
                    "embedding": vector_literal(embedding),
                    "metadata": json.dumps(metadata or {}, sort_keys=True),
                    "actor_type": actor_type.value,
                    "actor_id": actor_id,
                },
            )
            .mappings()
            .one()
        )
        return _memory_from_mapping(row)

    def get(
        self,
        connection: Connection,
        scope: AccessScope,
        memory_id: UUID,
    ) -> MemoryRecord | None:
        row = (
            connection.execute(
                text(
                    f"""
                    SELECT {self._record_columns}
                    FROM memories
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND id = :memory_id
                    """
                ),
                {
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "memory_id": memory_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _memory_from_mapping(row)

    def nearest(
        self,
        connection: Connection,
        scope: AccessScope,
        embedding: Sequence[float],
        *,
        limit: int = 10,
    ) -> list[SimilarMemory]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        rows = (
            connection.execute(
                text(
                    f"""
                    SELECT {self._record_columns},
                           embedding <=> CAST(:embedding AS VECTOR(1024)) AS cosine_distance
                    FROM memories
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND verification_status IN (
                          'VERIFIED', 'AWAITING_REVIEW', 'PROPOSED'
                      )
                      AND superseded_by_id IS NULL
                      AND (valid_until IS NULL OR valid_until > now())
                    ORDER BY embedding <=> CAST(:embedding AS VECTOR(1024))
                    LIMIT :limit
                    """
                ),
                {
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "embedding": vector_literal(embedding),
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )
        return [
            SimilarMemory(
                memory=_memory_from_mapping(row),
                cosine_distance=float(row["cosine_distance"]),
            )
            for row in rows
        ]

    def correct(
        self,
        engine: Engine,
        scope: AccessScope,
        memory_id: UUID,
        *,
        corrected_title: str,
        corrected_content: str,
        embedding: Sequence[float],
        reviewer_user_id: UUID,
        request_id: UUID,
        settings: Settings | None = None,
    ) -> MemoryRecord:
        """Append a verified correction and atomically supersede the active chain tip."""
        active_settings = settings or get_settings()

        def operation(connection: Connection) -> MemoryRecord:
            current_id = memory_id
            for _depth in range(100):
                row = (
                    connection.execute(
                        text(
                            f"""
                            SELECT {self._record_columns}, memory_type, source_type, source_id,
                                   confidence, privacy_classification, embedding_model, metadata
                            FROM memories
                            WHERE tenant_id = :tenant_id
                              AND subject_id = :subject_id
                              AND id = :memory_id
                            FOR UPDATE
                            """
                        ),
                        {
                            "tenant_id": scope.tenant_id,
                            "subject_id": scope.subject_id,
                            "memory_id": current_id,
                        },
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    raise MemoryNotFoundError("memory is not available in this subject scope")
                if row["superseded_by_id"] is None:
                    break
                current_id = row["superseded_by_id"]
            else:
                raise RuntimeError("memory supersession chain exceeds the safety limit")

            corrected = self.add(
                connection,
                scope,
                title=corrected_title,
                content=corrected_content,
                embedding=embedding,
                memory_type=MemoryType(row["memory_type"]),
                source_type=row["source_type"],
                source_id=row["source_id"],
                confidence=Decimal("1.0"),
                verification_status=VerificationStatus.VERIFIED,
                privacy_classification=row["privacy_classification"],
                embedding_model=row["embedding_model"],
                actor_type=ActorType.CLINICIAN,
                actor_id=reviewer_user_id,
                metadata=dict(row["metadata"]),
                supersedes_id=row["id"],
            )
            update = connection.execute(
                text(
                    """
                    UPDATE memories
                    SET verification_status = 'SUPERSEDED',
                        superseded_by_id = :corrected_id
                    WHERE tenant_id = :tenant_id
                      AND subject_id = :subject_id
                      AND id = :current_id
                      AND superseded_by_id IS NULL
                    """
                ),
                {
                    "corrected_id": corrected.id,
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "current_id": row["id"],
                },
            )
            if update.rowcount != 1:
                raise RuntimeError("active memory changed without a serialization retry")

            connection.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        tenant_id, subject_id, actor_type, actor_id, action,
                        resource_type, resource_id, request_id, outcome, metadata
                    ) VALUES (
                        :tenant_id, :subject_id, 'CLINICIAN', :actor_id,
                        'MEMORY_CORRECTED', 'memory', :resource_id, :request_id,
                        'SUCCESS', '{}'::JSONB
                    )
                    """
                ),
                {
                    "tenant_id": scope.tenant_id,
                    "subject_id": scope.subject_id,
                    "actor_id": str(reviewer_user_id),
                    "resource_id": str(corrected.id),
                    "request_id": str(request_id),
                },
            )
            return corrected

        return run_transaction(
            engine,
            operation,
            max_retries=active_settings.db_transaction_max_retries,
            base_delay_seconds=active_settings.db_transaction_base_delay_seconds,
            max_delay_seconds=active_settings.db_transaction_max_delay_seconds,
        )
