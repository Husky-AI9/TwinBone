# BoneTwin operating contract

These rules apply to every change in this repository.

1. Work from the new public hackathon repository.
2. Keep pre-existing Bone Health Tracker code isolated under `legacy/` or in a clearly
   disclosed package. Never present the earlier parser or prototype as new work.
3. Build the smallest complete vertical slice first: upload one synthetic report, parse it,
   persist it, retrieve prior memory, create one human-review task, and remember the review
   decision across a new session.
4. Do not add autonomous diagnosis, medication changes, fracture-risk predictions, or
   clinical treatment recommendations.
5. Every state-changing endpoint must be authenticated, authorized, idempotent, audited,
   and covered by tests.
6. Validate every model output used by application logic against a strict JSON schema.
   Free-form model text must never execute a tool directly.
7. Agent tools must be allowlisted, narrowly scoped, and deterministic. The model may
   propose an action; application code authorizes and commits it.
8. Preserve source evidence and corrections. Never overwrite an original extracted
   measurement.
9. Run formatting, type checking, unit tests, integration tests, and security-focused tests
   after every implementation phase.
10. Keep the repository runnable without real medical documents by providing synthetic
    fixtures and a local mock mode for AWS document services.
11. Never commit secrets, real patient data, cloud credentials, generated presigned URLs,
    or raw production logs.
12. Prefer clear, maintainable code over complex multi-agent orchestration.
13. Keep changes small and logical, use descriptive commit messages, and update
    `docs/implementation-status.md`.
14. When a requirement is ambiguous, choose the safer and simpler behavior and record the
    decision in an Architecture Decision Record.

## Phase workflow

Before changing a phase:

1. Read `CODEX_IMPLEMENTATION_SPEC.md` and this file completely.
2. Inspect the existing code and working tree.
3. State the exact files to create or modify.
4. Implement only the active phase without unrelated refactors.
5. Run every relevant check and fix failures rather than disabling tests.
6. Update `docs/implementation-status.md` with acceptance evidence and remaining risks.
7. Stop at the phase boundary unless the user explicitly requests the next phase.

## Data and safety boundary

BoneTwin is a document-understanding, longitudinal organization, and clinical-review
preparation tool. It is not a diagnostic system, medical device, or treatment recommendation
engine. Public and local demo data must be synthetic or fully de-identified. Do not add real
patient data to fixtures, tests, screenshots, examples, prompts, logs, or commits.
