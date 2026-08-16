# ADR 0005: CockroachDB-backed local runtime

## Status

Accepted on August 1, 2026.

## Context

The credential-free UI originally used a process-local workflow store. That was useful for
component tests, but it did not exercise the hackathon's defining requirement: CockroachDB
must be the persistent memory layer and later behavior must change because of durable state.
Local AWS document and model services still need deterministic adapters so contributors can
run the synthetic demo without cloud credentials.

## Decision

Local application mode uses CockroachDB by default. Reports, measurements, embeddings,
validated agent decisions, retrieval dispositions, tasks, review events, verified review
memory, and audit events are committed to the same structured tables intended for hosting.
The in-memory store is retained only as an explicitly selected unit-test double through
`WORKFLOW_STORE_MODE=memory`.

Raw synthetic upload bytes use an ignored UUID-named temporary directory. They are validated
against the declared size and SHA-256, parsed before the database transaction, and deleted
after either a committed result or a stable parsing failure. Raw bytes are not stored in
CockroachDB.

AWS extraction, embedding, authentication, and agent hosting remain deterministic local
adapters. Their UI labels identify the production AWS service they replace.

## Consequences

- A normal local run requires CockroachDB, migrations, and the structured synthetic seed.
- Review memory survives API and browser restarts and is visible through the limited MCP
  views.
- Local runs use real distributed-vector SQL and transactional idempotency without an API key.
- Cloud deployment and Managed MCP activation remain separate credentialed acceptance steps.
