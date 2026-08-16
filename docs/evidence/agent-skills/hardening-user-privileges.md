# CockroachDB Agent Skill evidence

## Skill

`hardening-user-privileges` version 1.0 from the official
`cockroachlabs/cockroachdb-skills` repository.

## Workflow used

The skill's audit sequence was applied to the local synthetic CockroachDB cluster:

1. Confirm administrative access for the audit.
2. Count admin role members.
3. inspect non-`USAGE` grants held by `PUBLIC`.
4. Inspect sensitive system privileges.
5. Create a purpose-specific role.
6. Verify the final grants and exercise both allowed reads and denied writes.

## Finding and remediation

Finding: the MCP inspector must not reuse the migration administrator or inherit broad
`PUBLIC` access.

Remediation: migration `0003_mcp_readonly_views` creates `bonetwin_mcp_reader`, grants
`SELECT` on three sanitized demo-only views, revokes `PUBLIC` access to those views, and
adds an integration test that connects as a member of the role and proves an `INSERT` is
denied.

The generated redacted result is stored beside this file as
`hardening-user-privileges.json`. It contains role/grant counts only—no connection string,
password, token, raw report text, embedding, or patient data.
