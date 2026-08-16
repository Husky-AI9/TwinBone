# Memory design

The CockroachDB schema stores provenance, confidence, verification state, temporal validity,
privacy classification, 1,024-dimensional vectors, and bidirectional supersession links.
Corrections append a verified memory, supersede the current chain tip, and record an audit
event in one retryable transaction.

Phase 1 implements subject-scoped cosine similarity as a database foundation. The complete
hybrid trust scoring, deterministic timeline additions, and candidate-disposition trace
remain Phase 5 work.
