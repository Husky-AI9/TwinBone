# Phase 9 evaluation and resilience

Run the complete deterministic release gate:

```bash
uv run python -m evaluations.runners.memory_quality --check
```

Regenerate the committed evidence report:

```bash
uv run python -m evaluations.runners.memory_quality
```

The dataset contains 30 fabricated timelines: two variants each of 15 scenarios covering
verified and concurrent corrections, duplicates, missing reports, date conflicts, scanner
changes, low-confidence OCR, supersession, expiration, revoked consent, cross-subject traps,
prompt injection, unverified agent hypotheses, and workflow retry.

Three approaches receive the same timelines:

1. Most recent report only.
2. Unfiltered vector similarity only.
3. BoneTwin hybrid trusted memory.

Release gates require perfect subject scoping, zero cross-subject leaks, perfect verified
correction adherence, no active superseded memory, no duplicate ingestion, valid evidence
IDs, at least 90% safe-action accuracy, no diagnostic or treatment output, no retry-created
duplicate action, and a reproducible Memory Impact Trace.

This is a software safety evaluation over synthetic fixtures. It is not a clinical
validation and makes no claim about diagnosis, treatment, or patient outcomes.
