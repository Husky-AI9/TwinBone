# Security policy

## Supported versions

BoneTwin is pre-release software. Security fixes are applied to the latest revision on the
default branch.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed credential. Contact the
repository owner privately and include the affected component, impact, reproduction steps,
and any safe remediation guidance. Do not include patient data, access tokens, presigned
URLs, raw medical documents, or production logs.

## Data handling

- Public demos and tests use synthetic or fully de-identified data only.
- Secrets belong in local environment variables or an approved secret manager.
- `.env`, credentials, raw uploads, extracted PHI, and production logs are git-ignored.
- Raw document text must not be logged or embedded before PHI screening.
- Security reports must use fabricated examples.

## Scope

The current Phase 0 repository is scaffolding only. Authentication, authorization,
idempotency, auditing, and dependency-specific controls will be threat-modeled and tested in
the phases that introduce those capabilities.
