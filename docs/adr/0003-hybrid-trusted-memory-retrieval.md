# ADR 0003: Hybrid trusted-memory retrieval

- Status: accepted
- Date: 2026-07-27

## Context

Most-recent-only retrieval misses older verified corrections. Vector-only retrieval can
select a highly similar record from the wrong subject, a superseded statement, low-confidence
OCR, duplicate evidence, or hostile instructions embedded in a report.

## Decision

BoneTwin combines subject scoping, verification and validity filters, source trust,
deduplication, mandatory durable corrections, temporal context, and semantic similarity.
Every candidate is recorded as used or excluded with a stable reason. Untrusted report text
is sanitized before it is eligible for model context or embedding.

The checked-in Phase 9 evaluation compares this approach with most-recent-report-only and
unfiltered vector-similarity baselines across 30 deterministic fabricated timelines.

## Consequences

Retrieval is explainable and safer, and verified corrections survive new sessions. It is
more deliberate than a single nearest-neighbor query and needs regression tests for each
filter. The evaluation is synthetic and validates decision logic, not clinical performance.
