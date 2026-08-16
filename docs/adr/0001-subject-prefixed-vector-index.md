# ADR 0001: Subject-prefixed cosine vector index

- Status: Accepted for Phase 1; representative-plan validation remains a Phase 5 gate
- Date: 2026-07-26

## Context

Every patient-specific retrieval must constrain both tenant and subject before similarity
ranking. CockroachDB v26.2 supports prefix columns on vector indexes and uses a vector index
only when every prefix is constrained to specific values. BoneTwin uses normalized
1,024-dimensional Titan embeddings and cosine distance.

`subject_id` remains nullable so later global workflow guidance can be stored, but global
memory must never override subject-scoped verified facts.

## Decision

Create `memories_subject_embedding_idx` on:

```sql
(tenant_id, subject_id, embedding vector_cosine_ops)
```

Subject memory queries require equality predicates for both prefix columns. Global memories
will use a separate deterministic retrieval path in Phase 5 instead of weakening the
patient-specific predicate.

The migration runner enables `feature.vector_index.enabled` through an autocommit
administrative connection before Alembic creates the index. Downgrade removes the index but
does not disable the cluster-wide setting because the cluster may host other vector users.

## Consequences

- Patient similarity candidates are pre-filtered by the authorization scope.
- Nullable global memories are intentionally outside the subject vector path.
- The 1,024 dimensions and cosine operator match the planned Titan embedding adapter.
- `EXPLAIN` proof on a representative dataset, index tuning, and the final prefix strategy
  remain required in Phase 5.
