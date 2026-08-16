# ADR 0002: Read-only MCP boundary

- Status: accepted
- Date: 2026-07-27

## Context

CockroachDB's Managed MCP Server can expose database tools to an authenticated client. A
general application or migration credential would reveal raw report text and could mutate
durable health-memory state. The public demo has one fixed fabricated subject and must never
make another subject discoverable through MCP.

## Decision

Migration `0003_mcp_readonly_views` creates the non-login role
`bonetwin_mcp_reader`. It receives `USAGE` on `public` and `SELECT` on exactly three curated
views:

- `mcp_subject_memory_trace`
- `mcp_agent_run_trace`
- `mcp_open_review_tasks`

The views are hard-scoped to the fixed synthetic demo tenant and subject. They expose IDs,
provenance labels, trust/disposition data, timestamps, and review status, but omit raw
content, embeddings, query text, metadata, source bounding boxes, and review payloads.
`PUBLIC` access is revoked and no write privilege is granted.

Cloud activation uses a separate CockroachDB Cloud SQL user assigned only this role, the
single-cluster MCP header, and read-only OAuth permission. The migration administrator is
never used as an MCP identity.

## Consequences

MCP can explain synthetic memory behavior without becoming an alternate path to protected
content or writes. Adding a new field or subject to MCP now requires an explicit migration
and privilege-audit update. The fixed subject scope is intentionally demo-specific; a
multi-subject deployment needs a separate tenant-aware authorization design rather than a
broader view.
