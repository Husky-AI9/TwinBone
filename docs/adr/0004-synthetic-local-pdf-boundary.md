# ADR 0004: Synthetic local PDF boundary

- Status: accepted
- Date: 2026-08-01

## Context

Local development must exercise a real browser-to-API PDF upload instead of substituting a
server fixture. At the same time, the repository contract prohibits real patient data and
the credential-free local mode does not run AWS DetectPHI.

## Decision

The browser sends the exact selected PDF bytes. The API checks the declared byte count and
SHA-256, reads extractable PDF text in memory, validates the explicit BoneTwin synthetic
markers, parses structured source evidence, and discards the raw bytes after success or
failure.

Three deterministic PDFs are generated from code and visibly state `SYNTHETIC DEMO - NOT A
MEDICAL RECORD`. Local mode refuses unlabeled documents even if their layout resembles a
supported report. Real or identifiable documents must wait for the deployed encrypted S3,
Textract, and PHI-review workflow.

## Consequences

The local demo proves real file selection, transport, hashing, parsing, and review UI without
claiming that AWS services ran. It intentionally supports only the generated report format;
broader real-world parsing and PHI handling remain deployment work.
