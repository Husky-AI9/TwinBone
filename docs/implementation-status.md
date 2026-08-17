# Implementation status

## Active boundary

Phases 2–9 now have a complete **local synthetic vertical slice**, implemented and verified
through August 2, 2026. CockroachDB is now the active local system of record for normalized
reports, vectors, validated agent runs, retrieval dispositions, review tasks and decisions,
verified review memory, and audits. Amazon Bedrock is now available as an explicit credentialed
local runtime. The credentialed local profile stores state in CockroachDB Cloud and gates trusted
retrieval through LangChain plus the managed Cloud MCP server. Live Cloud SQL, managed MCP, and
synthetic upload acceptance have been verified without printing credentials.
The workflow includes Memory Impact Trace, process-restart proof, read-only MCP inspection,
and reproducible resilience evaluation.

AWS deployment was authorized on August 16, 2026. The low-cost hosted API stack is deployed in
`us-west-2` as a Python 3.12 Lambda Function URL with reserved concurrency five, one-week logs,
Bedrock model access, an allowlisted Secrets Manager payload, a retained KMS key, and
prefix-scoped access to the existing private S3 bucket. Public liveness and readiness probes
passed against CockroachDB Cloud revision `0004`, LangChain managed-MCP retrieval, and S3-KMS
raw-document storage. Amplify SSR is deployed from the connected GitHub `main` branch at
`https://main.d1zm7v13x5ofdq.amplifyapp.com` with automatic builds enabled.

Repository-connected deployment preparation is complete: `amplify.yml` builds the pnpm Next.js
monorepo, and a reproducible Lambda packaging script produces a Linux x86_64 artifact below AWS
size limits. Hosted startup reads only four allowlisted Cockroach values from Secrets Manager.
The locked dependency set and 37 non-integration tests pass; lint, strict typing, 30 Vitest tests,
the Next.js production build, secret scan, evaluation, and both CDK synth paths also pass.
Destructive demo reset remains disabled when `APP_ENV=hosted`.

## Local run readiness

| Capability                          | Status | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Real browser-to-API upload contract | Pass   | The client computes SHA-256 and sends the selected PDF bytes. The API rejects byte-count or hash mismatches, extracts the uploaded PDF in memory, and discards raw bytes after processing.                                                                                                                                                                                                                                                                                                                                                                              |
| Generated demo documents            | Pass   | Three deterministic, one-page DXA PDFs are visibly marked `SYNTHETIC DEMO - NOT A MEDICAL RECORD`. All pages were rendered and visually inspected for clipping, overlap, and legibility.                                                                                                                                                                                                                                                                                                                                                                                |
| Local setup verifier                | Pass   | `scripts/verify_local_setup.ps1` starts CockroachDB, migrates and seeds it, runs Python/database tests, MCP/Agent Skill checks, evaluation, TypeScript checks, Vitest, and a production build. No API key is required.                                                                                                                                                                                                                                                                                                                                                  |
| Durable local workflow              | Pass   | A generated PDF reached `READY`, created structured report/vector rows and a review task, stored approval transactionally, then a fresh store instance returned `NO_ACTION` with prior memory applied.                                                                                                                                                                                                                                                                                                                                                                  |
| Live local Bedrock adapter          | Pass   | A real Titan v2 call returned a validated normalized 1,024-D vector; a real Nova Lite Converse call returned the forced proposal; and a full CockroachDB-backed run persisted `NO_ACTION` with six authorized evidence items after reusing verified review memory. The UI/API report `LOCAL_BEDROCK`.                                                                                                                                                                                                                                                                   |
| LangChain + Cloud MCP profile       | Pass   | Cloud SQL connected to database `husky` at revision `0004_durable_workflow_state`; managed MCP exposed 12 tools, BoneTwin allowed only `select_query`, and the scoped checker retrieved eight curated synthetic memory IDs.                                                                                                                                                                                                                                                                                                                                             |
| Interactive upload-to-result UI     | Pass   | Upload exists only inside the `/demo` Overview with a visible required PDF input and native form submit; the standalone upload view/nav entry was removed and legacy `/demo?view=upload` resolves to Overview. The local proxy forwards exact bytes through authenticated, authorized, idempotent, audited APIs. A real multipart submission redirected to its server-rendered `READY` parsed report. Static, client-fetched, server-fetched, and fallback-error display paths remove the requested word while preserving internal safety data; 19 frontend tests pass. |

The public landing page is available at `http://127.0.0.1:3000` and the working demo at
`http://127.0.0.1:3000/demo` after
`scripts/run_local.ps1 -SkipInstall`. Local mode remains explicitly synthetic and must not
receive real patient documents.

## Phase 8–9 evidence

| Capability             | Local status     | Evidence                                                                                                                                                                                                                                          |
| ---------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Read-only MCP boundary | Pass             | Migration `0003_mcp_readonly_views` creates `bonetwin_mcp_reader` with `SELECT` on exactly three sanitized, fixed-synthetic-subject views. Integration tests connect as a role member, read the views, and prove a base-table `INSERT` is denied. |
| Managed MCP setup      | Pass             | Single-cluster scoping, read-only authorization, and judge prompts are documented; the configured service-account credential connected to the managed endpoint and the application allowlist exposed only `select_query`.                         |
| LangChain MCP runtime  | Pass             | Managed MCP `select_query` authorized four curated synthetic memory IDs entering agent context while durable writes remained transactional Cloud SQL. Dependency import, formatting, strict typing, and the live readiness check passed.          |
| Official Agent Skill   | Pass             | The official CockroachDB `hardening-user-privileges` workflow produced redacted evidence, identified the need for a purpose-specific role and revoked `PUBLIC` access, and the migration applies that remediation.                                |
| Evaluation dataset     | Pass             | Thirty deterministic fabricated timelines cover 15 trust, isolation, concurrency, injection, and recovery scenarios.                                                                                                                              |
| Baseline comparison    | Pass             | Hybrid trusted memory achieved 100% key recall and safe-action accuracy with zero cross-subject leakage; latest-only achieved 0% key recall and 53.33% safe-action accuracy; unfiltered vector-only leaked in all 30 synthetic trap cases.        |
| Resilience and safety  | Pass             | Bounded workflow retries commit one idempotent result, retry exhaustion has a stable failure, prompt injection and active markup are screened before downstream context, and concurrent correction remains transaction-tested.                    |
| Observability          | Local synth pass | The CDK dashboard includes workflow/dependency and safety-boundary signals, with alarms for retry exhaustion, database connection, raw cleanup, validation, authorization, and cross-subject denial failures.                                     |

## Phase 2–7 local product evidence

| Capability              | Local status | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API and authentication  | Pass         | FastAPI exposes the required health, identity, subject, timeline, document, run, trace, task, and transparency routes. Missing/invalid tokens return 401; wrong-subject access returns a non-leaking 404; judge review writes return 403. Non-mock mode verifies Cognito JWT signature, issuer, audience, token type, and scoped claims.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Synthetic ingestion     | Pass         | Upload intent and completion are idempotent by key and SHA-256. The API processes the exact selected PDF rather than substituting a fixture, produces three normalized measurements, stores parser name/version, preserves source text, and safely returns a stable failure with no partial report.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| AWS workflow definition | Partial      | CDK defines Cognito, KMS-encrypted S3 with one-day raw retention, a retry/catch Step Functions workflow, API Gateway, an AgentCore execution role, log groups, dashboard, and alarms. `cdk synth` passes; no AWS deployment was attempted.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Trusted retrieval       | Local pass   | Normalized 1,024-dimensional vectors are queried through subject-scoped CockroachDB `VECTOR(1024)` retrieval and trust filters. Offline mode is deterministic; live local mode invokes Titan Text Embeddings v2. The live path awaits credentialed acceptance and CockroachDB Cloud remains a deployment step.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Agent and safe actions  | Local pass   | A versioned safety prompt, strict schemas, medical-output policy, forced allowlisted Bedrock tool, bounded task proposal, role enforcement, idempotent review behavior, and verified memory are implemented. Live local Bedrock acceptance and hosted AgentCore execution are pending credentials.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Polished UI             | Pass         | A responsive editorial landing page uses BoneTwin's forest/teal palette, oversized linked-memory typography, an anatomical hero card, explicit safety language, honest sign-in/sign-up entry points, and a direct demo CTA. The working product is isolated at `/demo`, including its server-rendered upload redirects and view navigation. Product navigation covers a detailed anterior skeletal SVG with inward-angling shaped femurs, patellae, larger medial tibiae, slender lateral fibulae, articulated feet, and aligned DXA markers, plus an accessible chart/table, native upload, parsed evidence, memory impact, clinician review, new-session proof, and transparency. The left-hip timeline uses immutable measurement UUID keys, filters laterality, and has regression coverage for multiple records sharing a scan date. |

The database integration workflow processed the report to `READY`, parsed three measurements,
created `CREATE_CLINICIAN_REVIEW`, atomically applied clinician approval and verified memory,
created a fresh store instance, and returned `NO_ACTION` with
`persisted_review_applied=true`.

## Phase 0 evidence

| Acceptance criterion                                     | Status | Evidence                                                                                                                          |
| -------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Fresh clone installs with documented commands            | Pass   | `README.md` documents uv/pnpm prerequisites and both direct and Make-based setup. Both locked installs pass.                      |
| CI runs formatting, type checking, and placeholder tests | Pass   | `.github/workflows/ci.yml` runs the Python, Node, build, database integration, and secret-scan gates.                             |
| No secrets in repository history                         | Pass   | The repository began with zero commits. The working-tree secret signature scan passes and secret-bearing local files are ignored. |
| Pre-existing code disclosure is visible                  | Pass   | `NOTICE-PREEXISTING.md` distinguishes the earlier Bone Health Tracker assets from new BoneTwin work.                              |

## Phase 1 acceptance evidence

| Acceptance criterion                                        | Status | Evidence                                                                                                                                                                                    |
| ----------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Migrations apply to local CockroachDB and CockroachDB Cloud | Pass   | All four Alembic revisions applied locally and to the configured CockroachDB Cloud `husky` database; a secret-safe audit confirmed revision `0004_durable_workflow_state`.                  |
| Vector insert and similarity query work                     | Pass   | A real `VECTOR(1024)` insert and cosine query returned the identical subject-scoped vector at distance `0.0`; the cosine vector index exists in `information_schema.statistics`.            |
| Cross-subject access tests pass                             | Pass   | Cross-tenant subject lookup and cross-subject memory/vector retrieval returned no protected record.                                                                                         |
| Duplicate and concurrent transaction tests pass             | Pass   | A duplicate report SHA-256 was rejected, seed replay remained idempotent, and two concurrent verified corrections produced a valid three-memory chain with exactly one active verified tip. |

## Phase 1 deliverables

- Environment-backed Pydantic configuration keeps database URLs redacted and enforces the
  synthetic-only public-demo boundary.
- CockroachDB is accessed with SQLAlchemy 2, the CockroachDB dialect, and Psycopg 3.
- Reviewed Alembic/SQL migrations create all required tables, constraints, indexes,
  idempotency keys, audit storage, and a `VECTOR(1024)` memory column.
- `memories_subject_embedding_idx` uses tenant/subject prefix columns and cosine distance.
- The migration runner creates the configured database, enables vector indexing, and upgrades
  to the Alembic head without printing credentials.
- Deterministic seed data creates one synthetic tenant, judge, clinician, patient role,
  pseudonymous subject, structured timeline, and trust memories and can be replayed safely.
- Every patient-facing repository operation implemented in this phase requires an immutable
  `AccessScope`.
- The transaction helper retries only SQLSTATE `40001`, with bounded exponential backoff and
  full jitter.
- Docker Compose and checksum-verified Windows scripts provide local CockroachDB v26.2.4.
- GitHub CI now runs CockroachDB migrations, synthetic seed loading, and integration tests.

## Verification results

- CockroachDB CCL v26.2.4 migration from an empty test database: passed.
- CockroachDB integration tests: 9 passed, including durable workflow restart and live-runtime
  wiring/replay proof.
- Python Phase 2–7 focused workflow/security tests: 10 passed.
- Full Python non-integration suite: 29 passed, including strict Bedrock request/output tests.
- Seed replay: passed twice with stable counts.
- Ruff formatting/lint and strict MyPy: passed, including the Bedrock runtime and access checker.
- ESLint, TypeScript, four Vitest UI tests, Next.js production build, and CDK type checking:
  passed.
- Six-stack AWS CDK synthesis: passed.
- Local authenticated CockroachDB-backed end-to-end HTTP workflow: passed.
- Live AWS readiness probe: Titan Text Embeddings v2 returned 1,024 validated dimensions and
  Nova Lite returned a schema-valid forced tool proposal.
- Live local Bedrock/CockroachDB workflow: passed with strict evidence authorization and a
  durable validated decision.
- Live authenticated 2022 synthetic PDF upload: reached `READY` and returned three parsed,
  source-backed measurements through the same intent, byte-upload, and completion contract used
  by the browser.
- Local S3 implementation checks: three storage-adapter tests validate signed checksum/KMS
  headers, exact-byte retrieval, and deletion; two browser/server tests prove app bearer tokens
  and idempotency headers are not sent to S3; the three-test CockroachDB integration workflow
  passes, including direct-upload verification from `UPLOADING` to `READY`, persisted S3
  references/audit evidence, and post-commit raw-object deletion.
- Hosted Lambda acceptance: the Linux x86_64 Python 3.12 artifact is 47.8 MiB compressed and
  139.7 MiB uncompressed with no Windows extensions. CloudFormation deployment completed, and
  public `/health/live` plus `/health/ready` returned healthy CockroachDB Cloud, LangChain MCP,
  and S3-KMS adapters.
- Hosted browser acceptance: Amplify release 4 deployed the exact Git commit recorded in `main`.
  Landing, sign-in, sign-up, and demo routes returned 200. A fabricated 2026 PDF posted through
  the public SSR upload route, persisted as `READY`, rendered its evidence page, and left zero raw
  objects under the hosted S3 prefix after the transactional cleanup. Browser API preflight and
  authenticated timeline calls return one exact-origin CORS header from FastAPI; Lambda Function
  URL CORS is intentionally disabled to prevent duplicate headers.
- Hosted browser repair: an allowlisted same-origin Amplify route now forwards only `/v1/*` and
  the three approved demo PDFs to the configured backend. It preserves authentication,
  idempotency, request IDs, JSON/PDF bytes, and safe response headers while excluding cookies and
  upstream CORS headers. Hosted runtime transparency reports `AWS` and only active services;
  an unreachable API reports `STATUS UNAVAILABLE` instead of inferring local mock mode.
- Hosted throttle repair: fresh-Chrome network capture proved the bearer header reached the API,
  while one of three concurrent startup requests received Lambda 429 throttling under the former
  concurrency cap of two. The initial repair serialized dashboard reads and added bounded
  transient retries; the demo concurrency cap remains five. State-changing calls remain
  single-attempt, authenticated, authorized, and idempotent.
- On-demand dashboard optimization: opening `/demo` now performs no API or Lambda request. An
  explicit **Load record** action retrieves timeline, review tasks, and runtime transparency from
  one authenticated `/dashboard` snapshot endpoint and stores the result in browser-session
  storage. Review Tasks and System can also be loaded independently with one request and reuse
  the session cache on later client-side navigation. Upload, comparison, and review actions no
  longer trigger an automatic three-read refresh. Logout clears the browser-session cache and
  returns to the public landing page.
- Upload and comparison observability repair: the former longitudinal chart slot now renders a
  terminal-style trace built from real client transport events and backend-completed operation
  contracts. Hosted uploads explicitly show AWS Lambda, encrypted Amazon S3 verification,
  Amazon Bedrock Titan embedding, the CockroachDB Cloud serializable commit, and raw-object
  cleanup. A successful upload refreshes the combined dashboard once and immediately selects the
  new left-total-hip source measurement in the anatomical preview.
- Bedrock comparison resilience: CloudWatch identified the generic comparison 500 as a correctly
  rejected Bedrock citation outside the authorized CockroachDB evidence set. Evidence validation
  remains strict. The runtime now retries one invalid structured proposal with a narrower citation
  instruction; if it still fails, application code returns the bounded deterministic decision
  over the already-authorized evidence and marks the operation `SAFE_FALLBACK` in the visible
  trace instead of returning an opaque 500.
- Current-date demo fixture: `bonetwin-demo-dxa-2026-08-16.pdf` is unique generated content with
  three parser-valid measurements and new scanner metadata. Poppler rendering, extracted-text
  inspection, parser replay, and SHA-256 comparison against the three earlier reports passed.

## Phase status

- Phase 0: complete locally.
- Phase 1: implementation complete; local and CockroachDB Cloud migration gates passed.
- Phase 2: local implementation and acceptance tests passed; production Cognito deployment pending.
- Phase 3: local synthetic vertical slice passed.
- Phase 4: the low-cost Lambda Function URL hosting stack is deployed and publicly healthy.
- Phase 5: trust engine, CockroachDB Cloud persistence, and hosted Bedrock IAM wiring passed.
- Phase 6: local validated safe-action adapter and live Nova Converse execution passed;
  AgentCore hosting remains pending.
- Phase 7: polished local UI and new-session flow passed.
- Phase 8: local privilege acceptance and live Cloud Managed MCP activation passed.
- Phase 8 extension: LangChain managed-MCP retrieval and the CockroachDB Cloud local profile are
  implemented and live-validated with scoped synthetic memory retrieval.
- Phase 9: complete locally; all reproducible release gates passed.
- Phase 10: local setup, demo documents, Lambda backend, and Amplify frontend acceptance passed;
  submission video and form remain pending.

## Remaining risks

- Real S3 raw-document storage is active with short-lived SigV4 PUT URLs, SHA-256 checksums,
  SSE-KMS headers, scoped object keys, post-transaction deletion, and one-day lifecycle expiry.
  Hosted API calls use the same Amplify origin; only direct presigned S3 PUTs depend on browser
  CORS. The bucket remains private with public-access blocking enabled.

- The detailed anatomical SVG passed structural, accessibility, live-render, type, lint, and
  production-build checks. The embedded browser surface was unavailable, so final cross-browser
  visual inspection of proportions and marker placement remains a manual acceptance step.

- The Windows CockroachDB binary is officially marked experimental and is used only for
  local verification. Docker or CockroachDB Cloud is recommended for regular development.
- The public hackathon slice still uses authenticated static demo identities rather than Cognito.
  State changes remain bearer-authenticated, role-authorized, idempotent, audited, and restricted
  to the fixed fabricated subject; production use must replace mock auth with Cognito.
- AWS Textract, Comprehend Medical, Cognito, Step Functions, and AgentCore have not been called
  in this environment. Titan Embeddings and Bedrock Converse were called only with fixed
  synthetic/de-identified demo context.
- The managed MCP service-account credential may have broader Cloud capabilities than the single
  tool BoneTwin invokes. Use a dedicated demo-cluster account, keep the key out of logs and source,
  and rotate it after the hackathon.
- The repository still has zero commits, so GitHub-hosted CI has not run.
