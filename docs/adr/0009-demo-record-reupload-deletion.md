# ADR 0009: Audited demo-record deletion for re-upload

## Status

Accepted

## Context

The shared demo needs to repeat an upload on camera. Upload identity is based on the PDF SHA-256,
so merely hiding a report or marking its document deleted does not permit the same bytes to be
uploaded again. The normal product boundary preserves original source evidence and corrections.

## Decision

Provide a separate record-deletion operation only when mock authentication is active, the subject
is the fixed fabricated demo subject, and the caller is the fixed demo clinician with the clinician
role. The operation is authenticated, subject-scoped, idempotent, transactional, and audited.

It deletes the selected document, scan report, measurements, direct `SOURCE_REPORT` memories, and
links to those direct memories. It does not delete other reports or clinician corrections. Before
commit, it writes an audit tombstone containing the original fingerprint and deletion counts. The
normal document deletion contract remains a logical deletion and is unchanged.

The System UI does not load records automatically. The operator explicitly loads records, chooses
one report, and confirms deletion. The response includes the updated timeline, avoiding a second
Lambda request.

## Consequences

- The same generated PDF can be uploaded again with a new document identity.
- Record deletion cannot be enabled with non-mock authentication or used for another subject.
- The public hosted demo clinician is intentionally shared, so any demo user can operate this
  control. It must never be used for real or production patient data.
- Historical agent-run rows can remain, but links to deleted direct evidence are removed so future
  retrieval cannot use it.
