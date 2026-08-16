# ADR 0007: LangChain MCP retrieval with transactional Cloud SQL storage

- Status: accepted; manual Cloud verification pending
- Date: 2026-08-01

## Context

The local application should use CockroachDB Cloud for durable state and the managed CockroachDB
Cloud MCP server through LangChain. The managed MCP service advertises both read and write tools.
BoneTwin state changes, however, span reports, measurements, memories, tasks, review events, and
audits and must remain authorized, idempotent, and atomic. A model or generic `insert_rows` tool
cannot enforce those invariants.

## Decision

In `COCKROACH_MCP_MODE=langchain`:

- SQLAlchemy connects to the TLS CockroachDB Cloud `DATABASE_URL` and remains the only durable
  write path.
- `langchain-mcp-adapters` connects to `https://cockroachlabs.cloud/mcp` using Streamable HTTP,
  a single-cluster header, and a dedicated service-account bearer token.
- The application discovers and invokes only `select_query`. It never loads an MCP write tool
  into model context.
- The query is fixed application code against `mcp_subject_memory_trace`; no user or model text
  can become SQL.
- MCP returns the authorized synthetic memory-ID set. Subject-scoped vector ranking and trust
  filtering then run against the same CockroachDB Cloud database, and only MCP-authorized IDs can
  enter the agent context.
- MCP failure or an empty/invalid result fails closed instead of falling back silently.

## Consequences

CockroachDB Cloud is the system of record and MCP is materially present in retrieval without
becoming an alternate mutation path. The local runtime needs two separate secrets: a Cloud SQL
credential and an MCP service-account API key. The service-account key can be powerful even
though application code allowlists one read tool, so it must be scoped to the demo cluster,
stored outside the repository, and rotated after the event. A live Cloud/MCP test remains a
manual acceptance step because no CockroachDB Cloud credentials were supplied.
