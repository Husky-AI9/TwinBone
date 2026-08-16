---
title: "BoneTwin - Codex Implementation Specification"
subtitle: "CockroachDB x AWS Hackathon: Build with Agentic Memory"
author: "Project implementation plan"
date: "July 25, 2026"
---

# Document purpose

This document is the implementation contract for **BoneTwin**, a trustworthy longitudinal bone-health memory agent. It is written so that OpenAI Codex can create the repository, implement the application in phases, test each phase, and leave a public, reproducible submission suitable for the CockroachDB x AWS Hackathon.

The application must demonstrate that CockroachDB is not a passive database. CockroachDB must be the system of record for agent state, structured scan history, embeddings, corrections, open tasks, audit records, and human-approved memory. The agent must behave differently because of durable memory.

> **Product safety boundary:** BoneTwin is a document-understanding, longitudinal organization, and clinical-review preparation tool. It is not a diagnostic system, medical device, or treatment recommendation engine. The public demo must use synthetic or fully de-identified data.

# 1. Codex operating contract

Codex should treat the following rules as mandatory.

1. Work from a new public repository created during the hackathon submission period.
2. Keep pre-existing Bone Health Tracker code isolated under `legacy/` or imported as a clearly disclosed package. Do not represent pre-existing parser work as newly created.
3. Implement the smallest complete vertical slice first: upload one synthetic report, parse it, persist it, retrieve prior memory, create one human-review task, and remember the review decision across a new session.
4. Do not add autonomous diagnosis, medication changes, fracture-risk predictions, or clinical treatment recommendations.
5. Every state-changing endpoint must be authenticated, authorized, idempotent, audited, and covered by tests.
6. Every model output used by application logic must be validated against a strict JSON schema. Free-form model text must never directly execute a tool.
7. Agent tools must be allowlisted, narrowly scoped, and deterministic. The model may propose an action; application code performs authorization and commits it.
8. Preserve source evidence and corrections. Never overwrite the original extracted measurement.
9. Run formatting, type checking, unit tests, integration tests, and security-focused tests after every implementation phase.
10. Keep the repository runnable without real medical documents by providing synthetic fixtures and a local mock mode for AWS document services.
11. Do not commit secrets, real patient data, cloud credentials, generated presigned URLs, or raw production logs.
12. Prefer clear, boring, maintainable code over complex multi-agent orchestration.
13. Commit in small logical changes. Use descriptive commit messages and update the implementation checklist.
14. When a requirement is ambiguous, choose the safer and simpler behavior and document the decision in an Architecture Decision Record.

## Codex completion behavior

For each phase, Codex must:

- Read this specification and the repository `AGENTS.md`.
- Inspect existing code before changing it.
- State the exact files it will create or modify.
- Implement the phase without unrelated refactors.
- Run all relevant checks.
- Fix failures rather than disabling tests.
- Update `docs/implementation-status.md` with completed acceptance criteria, evidence, and remaining risks.
- Stop at the phase boundary unless explicitly instructed to continue.

# 2. Product definition

## 2.1 Name and one-sentence pitch

**BoneTwin** is a trustworthy longitudinal memory agent that remembers every bone-density scan, correction, treatment event, unresolved question, and clinician decision; retrieves only relevant and valid memories; and prepares evidence-backed follow-up actions for human approval.

## 2.2 Problem

Bone-density reports are often reviewed as isolated documents. Longitudinal interpretation is difficult when reports span years, different scanner models, different skeletal sites, changing treatment history, extraction errors, and prior clinician decisions. Traditional dashboards can display measurements, but they do not preserve why a measurement was excluded, what remains unresolved, or which prior correction should influence the next review.

## 2.3 Core innovation

The differentiator is the **Memory Trust Engine**. Every memory has provenance, confidence, verification state, temporal validity, privacy classification, and supersession links. BoneTwin can explain:

- Which memories it retrieved.
- Which memories influenced the result.
- Which memories were excluded and why.
- Which memory changed the proposed action.
- What the result would have been without an important verified memory.

This visible explanation is called the **Memory Impact Trace**.

## 2.4 Primary users

- A patient organizing longitudinal bone-health records before an appointment.
- A clinician or care coordinator reviewing extracted data and resolving inconsistencies.
- A researcher using only consented, de-identified records and aggregate views.
- A hackathon judge using a synthetic demo account and a read-only memory inspector.

## 2.5 Success story for the demo

A synthetic patient has two DXA reports. An earlier report contains a lumbar-spine measurement that a reviewer marked unsuitable for longitudinal comparison. A new report is uploaded in a later session. BoneTwin retrieves the verified correction from CockroachDB, excludes that measurement, compares appropriate hip measurements, creates a review task, and explains that its behavior changed because of the remembered correction. The reviewer approves the task. A completely new session retrieves the approval and applies it again.

# 3. Hackathon requirement traceability

| Hackathon expectation | BoneTwin implementation | Required evidence |
|---|---|---|
| Agentic application | Strands-based agent reasons over memory and proposes bounded actions | Agent run trace and tool call log |
| CockroachDB persistent memory | Structured reports, embeddings, task state, corrections, run history, and audit records stored in CockroachDB | Schema, queries, demo, tests |
| At least two CockroachDB tools | Distributed Vector Indexing, Managed MCP Server, and Agent Skills Repo | README sections and video footage |
| AWS deployment | AgentCore Runtime, Bedrock, Lambda/Step Functions, S3, Textract, Comprehend Medical, Cognito, CloudWatch | Architecture and deployed URL |
| Memory must be meaningful | Verified corrections and unresolved tasks change later behavior | Cross-session test and Memory Impact Trace |
| Public open-source repository | MIT license, setup instructions, synthetic fixtures, `.env.example` | Repository URL |
| Functional demo application | Public web PWA and judge credentials if authentication is required | Demo URL |
| Video under three minutes | Shows memory write, retrieval, correction, new session, MCP query | Public YouTube or Vimeo URL |
| Production readiness | RBAC, idempotency, auditability, retries, threat model, evaluation suite | Tests and documentation |
| New project requirement | New repo and new agentic architecture; pre-existing parser disclosed | `NOTICE-PREEXISTING.md` |

# 4. Scope

## 4.1 Minimum winning scope

The complete submission must support:

1. Sign in with a synthetic demo user.
2. Create or select a pseudonymous subject timeline.
3. Upload a synthetic PDF using a presigned S3 URL.
4. Start an asynchronous ingestion workflow.
5. Extract text and report structure.
6. Detect and mask likely PHI before durable storage.
7. Run the existing custom BMD parser or a compatible replacement.
8. Store the original extraction, normalized measurements, confidence, and evidence locations.
9. Generate embeddings for safe memory summaries using Amazon Titan Text Embeddings V2 with 1,024 dimensions.
10. Create memories in CockroachDB with trust metadata.
11. Retrieve memories with structured filters plus vector similarity.
12. Generate an evidence-backed comparison using an Amazon Bedrock foundation model.
13. Propose one of a small set of safe actions.
14. Require human approval, correction, or rejection before applying the action.
15. Store the review decision as verified memory.
16. Show a Memory Impact Trace.
17. Demonstrate persistent behavior in a new browser session.
18. Expose a read-only CockroachDB MCP workflow for inspecting the evidence.
19. Run at least one CockroachDB Agent Skill for security or production-readiness validation.
20. Provide automated memory-quality and privacy-isolation tests.

## 4.2 Explicit non-goals

- Diagnosing osteoporosis or osteopenia.
- Determining whether a patient should take medication.
- Recommending medication dosage or treatment changes.
- Predicting fractures.
- Replacing a clinician’s official interpretation.
- Training a medical model on user data.
- Sharing identifiable data with research users.
- Building a general-purpose medical chatbot.
- Implementing a complex multi-agent society.
- Supporting every possible DXA report format before submission.

# 5. Technical stack

Use a monorepo with stable, actively maintained dependencies.

| Layer | Decision |
|---|---|
| Web client | Next.js, React, TypeScript, Tailwind CSS, accessible component primitives |
| Portability | Responsive PWA; API-first design; no server-only UI assumptions; later Capacitor wrapper is possible |
| API | FastAPI on Python 3.12, Pydantic v2, OpenAPI |
| Agent | Strands Agents SDK with Amazon Bedrock model provider |
| Agent hosting | Amazon Bedrock AgentCore Runtime |
| Document workflow | AWS Step Functions plus Lambda functions |
| Documents | Amazon S3 with KMS encryption and short retention |
| Extraction | Amazon Textract asynchronous document analysis |
| PHI screening | Amazon Comprehend Medical `DetectPHI` plus user/reviewer confirmation |
| Embeddings | Amazon Titan Text Embeddings V2, normalized, 1,024 dimensions |
| Database | CockroachDB Cloud |
| SQL access | SQLAlchemy 2.x for standard CRUD; Psycopg 3/raw SQL for vector and Cockroach-specific operations |
| Migrations | Alembic plus reviewed SQL migration files |
| Authentication | Amazon Cognito user pools for hosted demo |
| Authorization | Application RBAC plus tenant/subject scoping in every query |
| Infrastructure | AWS CDK in TypeScript; scripts using `ccloud` for CockroachDB setup where appropriate |
| Observability | OpenTelemetry, AgentCore observability, CloudWatch logs/metrics, X-Ray where supported |
| Tests | Pytest, Testcontainers/local CockroachDB, Playwright, Vitest, Ruff, MyPy/Pyright, ESLint, TypeScript checks |
| Package managers | `uv` for Python and `pnpm` for Node.js |

Do not hardcode a particular Bedrock reasoning model in business logic. Configure `BEDROCK_CHAT_MODEL_ID` by environment and document the tested model in the README.

# 6. System architecture

![BoneTwin architecture](bonetwin_doc_assets/architecture.png)

## 6.1 Request and data flow

1. The user authenticates through Cognito.
2. The client requests a presigned upload URL from the API.
3. The API creates a `document` record in `UPLOADING` state and returns the URL.
4. The client uploads directly to the encrypted S3 bucket.
5. The API starts a Step Functions ingestion execution using the document ID, not raw personal data.
6. Textract asynchronously extracts text and layout.
7. Comprehend Medical identifies probable PHI. The workflow masks detected spans and records confidence values.
8. The custom parser creates normalized bone-density measurements and evidence references.
9. One CockroachDB transaction stores document state, report metadata, measurements, source evidence, initial memories, and an audit event.
10. Titan embeddings are generated for de-identified memory text and stored in `VECTOR(1024)` columns.
11. A user requests a comparison. The API calls the AgentCore runtime with an authenticated subject scope.
12. The agent calls a server-side retrieval tool. It cannot provide arbitrary SQL.
13. The retrieval service combines relational constraints and vector similarity, then applies trust filters.
14. The model produces a strict `AgentDecision` JSON object containing evidence IDs, reasoning summary, uncertainty, and a proposed safe action.
15. Application code validates the result and either returns an answer-only response or creates a review task.
16. A human approves, corrects, or rejects the task.
17. A transaction stores the review event, updates task state, creates verified or rejected memory, and records an audit event.
18. The UI displays the Memory Impact Trace.

# 7. Repository structure

Codex must create the following structure unless an ADR documents a justified change.

```text
bonetwin/
├── AGENTS.md
├── README.md
├── LICENSE
├── NOTICE-PREEXISTING.md
├── SECURITY.md
├── CONTRIBUTING.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── pnpm-workspace.yaml
├── pyproject.toml
├── uv.lock
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       ├── public/
│       └── tests/
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── schemas/
│   │   │   └── services/
│   │   └── tests/
│   ├── agent/
│   │   ├── bonetwin_agent/
│   │   │   ├── prompts/
│   │   │   ├── tools/
│   │   │   ├── policies/
│   │   │   ├── schemas/
│   │   │   └── runtime.py
│   │   └── tests/
│   └── ingestion/
│       ├── handlers/
│       ├── parser/
│       ├── fixtures/
│       └── tests/
├── packages/
│   ├── shared-types/
│   └── api-client/
├── database/
│   ├── alembic/
│   ├── migrations/
│   ├── seed/
│   └── queries/
├── infrastructure/
│   ├── cdk/
│   ├── cockroach/
│   └── scripts/
├── evaluations/
│   ├── datasets/
│   ├── runners/
│   ├── reports/
│   └── tests/
├── docs/
│   ├── architecture.md
│   ├── memory-design.md
│   ├── threat-model.md
│   ├── data-flow.md
│   ├── demo-script.md
│   ├── judge-testing.md
│   ├── implementation-status.md
│   ├── adr/
│   └── diagrams/
└── .github/
    └── workflows/
```

# 8. Domain model and database schema

## 8.1 Design principles

- Use UUID primary keys generated by the application or `gen_random_uuid()`.
- Store timestamps as `TIMESTAMPTZ` in UTC.
- Every patient-scoped table must include `tenant_id` and `subject_id` where applicable.
- Do not store direct identifiers in the demo database.
- Use append-only events for corrections and audits.
- Use `JSONB` only for flexible payloads; important query fields must be typed columns.
- Use database constraints for state enums, uniqueness, and referential integrity.
- Use explicit idempotency keys for uploads, ingestion jobs, model runs, and action execution.
- Avoid large vector batch inserts; insert memory rows individually or in small controlled transactions.
- Use a vector index with prefix columns that match retrieval constraints, such as `tenant_id` and `subject_id`.

## 8.2 Required enums

```sql
CREATE TYPE document_status AS ENUM (
  'UPLOADING', 'UPLOADED', 'EXTRACTING', 'PHI_REVIEW',
  'PARSING', 'INDEXING', 'READY', 'FAILED', 'DELETED'
);

CREATE TYPE memory_type AS ENUM (
  'EPISODIC', 'SEMANTIC', 'PROCEDURAL', 'TASK', 'EVIDENCE'
);

CREATE TYPE verification_status AS ENUM (
  'PROPOSED', 'AWAITING_REVIEW', 'VERIFIED',
  'REJECTED', 'SUPERSEDED', 'EXPIRED'
);

CREATE TYPE action_status AS ENUM (
  'PROPOSED', 'AWAITING_REVIEW', 'APPROVED',
  'CORRECTED', 'REJECTED', 'APPLIED', 'FAILED', 'CANCELLED'
);

CREATE TYPE actor_type AS ENUM (
  'USER', 'CLINICIAN', 'AGENT', 'SYSTEM', 'RESEARCHER'
);
```

CockroachDB compatibility must be verified during migration implementation. If custom SQL enum behavior creates friction, use constrained `STRING` columns with `CHECK` constraints and document the change.

## 8.3 Core tables

The migration should implement at least the following columns. Codex may add operational columns such as `updated_at`, but may not remove provenance, authorization, or idempotency fields.

### `tenants`

```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name STRING NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `app_users`

```sql
CREATE TABLE app_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  cognito_subject STRING NOT NULL,
  role STRING NOT NULL CHECK (role IN ('PATIENT', 'CLINICIAN', 'RESEARCHER', 'ADMIN', 'JUDGE')),
  display_name STRING NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, cognito_subject)
);
```

### `subjects`

```sql
CREATE TABLE subjects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  pseudonym STRING NOT NULL,
  owner_user_id UUID NULL REFERENCES app_users(id),
  date_of_birth_year INT NULL,
  status STRING NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, pseudonym)
);
CREATE INDEX subjects_tenant_idx ON subjects (tenant_id, id);
```

### `documents`

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  status STRING NOT NULL,
  original_filename STRING NOT NULL,
  content_type STRING NOT NULL,
  byte_size INT8 NOT NULL,
  sha256 STRING NOT NULL,
  s3_bucket STRING NULL,
  s3_key STRING NULL,
  upload_idempotency_key STRING NOT NULL,
  raw_retention_until TIMESTAMPTZ NULL,
  failure_code STRING NULL,
  failure_message STRING NULL,
  created_by UUID NOT NULL REFERENCES app_users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, subject_id, sha256),
  UNIQUE (tenant_id, upload_idempotency_key)
);
```

### `scan_reports`

```sql
CREATE TABLE scan_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  document_id UUID NOT NULL REFERENCES documents(id),
  scan_date DATE NULL,
  report_type STRING NOT NULL DEFAULT 'DXA_BMD',
  facility_pseudonym STRING NULL,
  scanner_manufacturer STRING NULL,
  scanner_model STRING NULL,
  parser_name STRING NOT NULL,
  parser_version STRING NOT NULL,
  extraction_confidence DECIMAL(5,4) NULL,
  review_required BOOL NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id)
);
CREATE INDEX reports_subject_date_idx ON scan_reports (tenant_id, subject_id, scan_date DESC);
```

### `measurements`

```sql
CREATE TABLE measurements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  report_id UUID NOT NULL REFERENCES scan_reports(id),
  skeletal_site STRING NOT NULL,
  region STRING NULL,
  side STRING NULL,
  bmd_g_cm2 DECIMAL(8,4) NULL,
  t_score DECIMAL(5,2) NULL,
  z_score DECIMAL(5,2) NULL,
  unit STRING NULL,
  extraction_confidence DECIMAL(5,4) NOT NULL,
  source_page INT NULL,
  source_text STRING NULL,
  source_bbox JSONB NULL,
  usable_for_longitudinal BOOL NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX measurement_timeline_idx
  ON measurements (tenant_id, subject_id, skeletal_site, region, report_id);
```

### `treatment_events`

This stores user-provided or reviewer-confirmed context without providing medical recommendations.

```sql
CREATE TABLE treatment_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  event_date DATE NULL,
  category STRING NOT NULL,
  description STRING NOT NULL,
  source_type STRING NOT NULL,
  verification_status STRING NOT NULL,
  created_by UUID NOT NULL REFERENCES app_users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `memories`

```sql
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NULL REFERENCES subjects(id),
  memory_type STRING NOT NULL,
  source_type STRING NOT NULL,
  source_id UUID NULL,
  title STRING NOT NULL,
  content STRING NOT NULL,
  content_hash STRING NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  verification_status STRING NOT NULL,
  valid_from TIMESTAMPTZ NULL,
  valid_until TIMESTAMPTZ NULL,
  supersedes_id UUID NULL REFERENCES memories(id),
  superseded_by_id UUID NULL REFERENCES memories(id),
  privacy_classification STRING NOT NULL,
  embedding_model STRING NOT NULL,
  embedding VECTOR(1024) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_by_actor_type STRING NOT NULL,
  created_by_actor_id UUID NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, content_hash, source_id)
);
```

Create and test a cosine vector index. Prefer prefix columns that enable subject-scoped retrieval.

```sql
SET CLUSTER SETTING feature.vector_index.enabled = true;

CREATE VECTOR INDEX memories_subject_embedding_idx
ON memories (tenant_id, subject_id, embedding vector_cosine_ops)
WITH (min_partition_size = 16, max_partition_size = 128);
```

If a nullable `subject_id` cannot be used effectively as a prefix in the chosen query plan, create separate subject-scoped and global-reference memory tables or indexes. Document the result of `EXPLAIN` in `docs/adr/`.

### `memory_relations`

```sql
CREATE TABLE memory_relations (
  from_memory_id UUID NOT NULL REFERENCES memories(id),
  to_memory_id UUID NOT NULL REFERENCES memories(id),
  relation_type STRING NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (from_memory_id, to_memory_id, relation_type)
);
```

### `agent_runs`

```sql
CREATE TABLE agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  user_id UUID NOT NULL REFERENCES app_users(id),
  request_type STRING NOT NULL,
  user_query STRING NOT NULL,
  model_id STRING NOT NULL,
  prompt_version STRING NOT NULL,
  run_idempotency_key STRING NOT NULL,
  status STRING NOT NULL,
  response_summary STRING NULL,
  uncertainty STRING NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  error_code STRING NULL,
  UNIQUE (tenant_id, run_idempotency_key)
);
```

### `agent_run_memories`

```sql
CREATE TABLE agent_run_memories (
  agent_run_id UUID NOT NULL REFERENCES agent_runs(id),
  memory_id UUID NOT NULL REFERENCES memories(id),
  vector_distance DECIMAL(12,8) NULL,
  trust_score DECIMAL(8,6) NOT NULL,
  retrieval_rank INT NOT NULL,
  disposition STRING NOT NULL CHECK (disposition IN ('USED', 'EXCLUDED', 'SUPPORTING')),
  disposition_reason STRING NULL,
  PRIMARY KEY (agent_run_id, memory_id)
);
```

### `review_tasks`

```sql
CREATE TABLE review_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  agent_run_id UUID NOT NULL REFERENCES agent_runs(id),
  action_type STRING NOT NULL,
  status STRING NOT NULL,
  title STRING NOT NULL,
  proposed_payload JSONB NOT NULL,
  applied_payload JSONB NULL,
  evidence_memory_ids UUID[] NULL,
  requires_role STRING NOT NULL DEFAULT 'CLINICIAN',
  action_idempotency_key STRING NOT NULL,
  due_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ NULL,
  resolved_by UUID NULL REFERENCES app_users(id),
  resolution_note STRING NULL,
  UNIQUE (tenant_id, action_idempotency_key)
);
```

If UUID arrays reduce portability or indexing quality, replace `evidence_memory_ids` with a join table.

### `review_events`

```sql
CREATE TABLE review_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  task_id UUID NOT NULL REFERENCES review_tasks(id),
  actor_user_id UUID NOT NULL REFERENCES app_users(id),
  event_type STRING NOT NULL,
  previous_status STRING NULL,
  new_status STRING NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `consent_records`

```sql
CREATE TABLE consent_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NOT NULL REFERENCES subjects(id),
  scope STRING NOT NULL,
  status STRING NOT NULL CHECK (status IN ('GRANTED', 'REVOKED')),
  effective_at TIMESTAMPTZ NOT NULL,
  actor_user_id UUID NOT NULL REFERENCES app_users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `audit_events`

```sql
CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  subject_id UUID NULL REFERENCES subjects(id),
  actor_type STRING NOT NULL,
  actor_id STRING NULL,
  action STRING NOT NULL,
  resource_type STRING NOT NULL,
  resource_id STRING NULL,
  request_id STRING NOT NULL,
  outcome STRING NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_tenant_time_idx ON audit_events (tenant_id, created_at DESC);
```

# 9. Memory Trust Engine

![Memory lifecycle](bonetwin_doc_assets/memory_lifecycle.png)

## 9.1 Memory creation rules

Every memory must have:

- A clear memory type.
- A source type and source identifier.
- A source-backed title and content summary.
- A confidence score in `[0, 1]`.
- A verification state.
- A privacy classification.
- Temporal validity when applicable.
- A content hash for deduplication.
- An embedding generated only from approved de-identified content.

Never embed raw document text before PHI screening. Never include names, addresses, contact information, medical record numbers, or unreviewed OCR headers in embedding text.

## 9.2 Source-quality weights

Use the following initial weights. Store them in configuration, not hardcoded across multiple modules.

| Source | Weight |
|---|---:|
| Clinician-verified correction | 1.00 |
| Source report measurement with high confidence | 0.92 |
| Reviewer-confirmed patient statement | 0.85 |
| Unverified patient statement | 0.70 |
| High-confidence parser inference | 0.65 |
| Agent-generated hypothesis | 0.40 |
| Rejected, expired, or superseded memory | 0.00 |

## 9.3 Trust score

Use deterministic application code for trust scoring.

```python
def calculate_trust_score(memory, *, now, vector_similarity, subject_match):
    if memory.verification_status in {"REJECTED", "SUPERSEDED", "EXPIRED"}:
        return 0.0
    if memory.valid_until and memory.valid_until <= now:
        return 0.0

    verification_weight = {
        "VERIFIED": 1.0,
        "AWAITING_REVIEW": 0.65,
        "PROPOSED": 0.45,
    }.get(memory.verification_status, 0.0)

    recency_weight = temporal_decay(memory.valid_from or memory.created_at, now)
    subject_weight = 1.0 if subject_match else 0.35
    source_weight = source_weight_for(memory.source_type)

    return clamp01(
        vector_similarity
        * verification_weight
        * source_weight
        * recency_weight
        * subject_weight
    )
```

For patient-specific decisions, global reference memories may support wording or workflow guidance but may not override patient-scoped verified facts.

## 9.4 Supersession transaction

A correction must be atomic:

1. Lock or serializably read the active memory.
2. Insert a new verified memory containing the corrected fact or instruction.
3. Set the old memory to `SUPERSEDED` and link `superseded_by_id`.
4. Link the new memory with `supersedes_id`.
5. Update any affected task.
6. Write the review event.
7. Write the audit event.
8. Commit all changes together.

CockroachDB serializable transaction retry errors must be handled with bounded retries and jitter. Add an integration test that intentionally creates concurrent corrections and verifies one consistent final chain.

# 10. Hybrid retrieval

## 10.1 Retrieval stages

1. Authorize `tenant_id`, `subject_id`, user role, and requested purpose.
2. Create the query embedding using Titan Text Embeddings V2.
3. Retrieve subject-scoped candidate memories using the CockroachDB vector index.
4. Retrieve deterministic timeline facts through relational queries.
5. Add open task memory and the latest relevant correction regardless of vector rank.
6. Apply trust score and verification filters.
7. Deduplicate by source and supersession chain.
8. Cap the evidence bundle by token budget.
9. Record every candidate in `agent_run_memories`, including excluded items and reasons.

## 10.2 Candidate vector query

Use parameterized SQL. The exact distance-to-similarity conversion should be validated against the selected cosine operator.

```sql
SELECT
  id,
  memory_type,
  source_type,
  title,
  content,
  confidence,
  verification_status,
  valid_from,
  valid_until,
  superseded_by_id,
  metadata,
  embedding <=> CAST(:query_embedding AS VECTOR(1024)) AS cosine_distance
FROM memories
WHERE tenant_id = :tenant_id
  AND subject_id = :subject_id
  AND verification_status IN ('VERIFIED', 'AWAITING_REVIEW', 'PROPOSED')
  AND (valid_until IS NULL OR valid_until > now())
  AND superseded_by_id IS NULL
ORDER BY embedding <=> CAST(:query_embedding AS VECTOR(1024))
LIMIT :candidate_limit;
```

Run `EXPLAIN` and save an anonymized plan demonstrating vector index use.

## 10.3 Mandatory deterministic additions

The retrieval service must always consider:

- Latest scan report.
- Prior comparable scan at the same skeletal site.
- Active clinician-verified procedural memories.
- Open review tasks.
- Latest treatment-context event, if one was explicitly recorded.
- Measurements with low confidence or conflicting metadata.

These records cannot rely only on semantic similarity.

## 10.4 Cross-patient isolation

Every repository method must receive `AccessScope(tenant_id, subject_id, role)`. No repository method may accept only an unrestricted ID for a patient-scoped resource. Integration tests must attempt to retrieve another subject’s memory by ID, vector query, task ID, and MCP view and must receive no data.

# 11. Agent design

![Agent execution flow](bonetwin_doc_assets/agent_flow.png)

## 11.1 Agent responsibilities

The agent may:

- Summarize a subject’s stored timeline.
- Compare selected measurements with clear caveats.
- Explain which memories affected its response.
- Identify missing data or inconsistencies.
- Propose a bounded review task.
- Prepare appointment questions.
- Request confirmation of dates or source documents.

The agent may not:

- Diagnose a condition.
- Recommend treatment.
- Change or infer medication instructions.
- Claim clinical certainty.
- Retrieve data outside the authenticated scope.
- Execute arbitrary SQL.
- Directly mutate source measurements.
- Mark its own hypothesis as verified.

## 11.2 Allowed tools

Implement only these application tools for the initial submission:

```text
retrieve_trusted_memory
get_measurement_timeline
get_open_review_tasks
propose_review_task
prepare_longitudinal_summary
record_agent_observation
```

`record_agent_observation` must create a `PROPOSED` memory with low source weight. It cannot create a verified memory.

The CockroachDB Managed MCP Server is a separate judge/clinician inspection integration. Do not expose the broad MCP server directly as a tool to the patient-facing agent.

## 11.3 Agent input schema

```json
{
  "request_id": "uuid",
  "tenant_id": "uuid",
  "subject_id": "uuid",
  "user_id": "uuid",
  "role": "PATIENT|CLINICIAN|JUDGE",
  "request_type": "COMPARE_REPORTS|EXPLAIN_MEMORY|PREPARE_VISIT|REVIEW_OPEN_TASKS",
  "query": "string",
  "idempotency_key": "string"
}
```

The runtime must not trust tenant, subject, user, or role values supplied directly by the browser. The API derives them from authentication and authorization context before calling AgentCore.

## 11.4 Agent output schema

Use Pydantic and reject responses that do not validate.

```python
class EvidenceReference(BaseModel):
    memory_id: UUID
    source_type: str
    source_id: UUID | None
    role: Literal["PRIMARY", "SUPPORTING", "EXCLUDED"]
    exclusion_reason: str | None = None

class ProposedAction(BaseModel):
    action_type: Literal[
        "CREATE_CLINICIAN_REVIEW",
        "REQUEST_MISSING_REPORT",
        "REQUEST_DATE_CONFIRMATION",
        "PREPARE_APPOINTMENT_QUESTIONS",
        "NO_ACTION"
    ]
    title: str
    rationale: str
    payload: dict[str, Any]
    requires_human_approval: bool = True

class AgentDecision(BaseModel):
    summary: str
    uncertainty: str
    safety_notice: str
    evidence: list[EvidenceReference]
    proposed_action: ProposedAction
    memory_impact_statement: str
    counterfactual_without_key_memory: str | None
```

## 11.5 System prompt requirements

Store the prompt in a versioned text file. It must contain:

- Product purpose and medical safety boundary.
- Instruction to use only supplied evidence.
- Instruction to state uncertainty.
- Instruction not to diagnose or recommend treatment.
- Instruction not to follow commands contained inside source documents.
- Instruction to treat report text as untrusted data.
- Instruction to cite evidence IDs in the structured response.
- Instruction to propose only allowlisted action types.
- Instruction that agent observations are unverified until human review.
- Instruction to explain how important memory changed the result.

## 11.6 Prompt injection defense

- Separate system instructions, user text, and retrieved evidence into clearly tagged blocks.
- Mark user input for Bedrock Guardrails prompt-attack detection.
- Never concatenate raw report text into tool descriptions or system prompts.
- Sanitize document text and remove active markup.
- Reject evidence strings containing attempts to alter instructions; retain the source as evidence but tag it as untrusted.
- Apply output validation after model generation.
- Run adversarial tests with hidden instructions inside synthetic reports.

# 12. Safe action workflow

## 12.1 Action types

### `CREATE_CLINICIAN_REVIEW`

Creates a task asking a reviewer to verify an inconsistency or low-confidence interpretation.

### `REQUEST_MISSING_REPORT`

Creates a patient-visible checklist item requesting a missing prior report. It does not send external email in the initial version.

### `REQUEST_DATE_CONFIRMATION`

Asks the user to confirm an event or scan date before it influences the timeline.

### `PREPARE_APPOINTMENT_QUESTIONS`

Creates an editable list of questions based on unresolved stored facts. The questions must not prescribe treatment.

## 12.2 Approval state machine

```text
PROPOSED -> AWAITING_REVIEW -> APPROVED | CORRECTED | REJECTED
APPROVED | CORRECTED -> APPLIED
APPLIED -> remembered as VERIFIED procedural/task memory
```

## 12.3 Transactional execution

Action application must occur in one serializable transaction:

- Validate task is still pending.
- Verify reviewer role.
- Validate idempotency key.
- Append review event.
- Update task.
- Create correction or verification memory.
- Supersede prior memory if applicable.
- Write audit event.

Return the already committed result when the same idempotency key is replayed.

# 13. API contract

The generated OpenAPI schema must be used to generate a typed client for the web app.

## 13.1 Health and session

| Method | Route | Purpose |
|---|---|---|
| GET | `/health/live` | Process liveness only |
| GET | `/health/ready` | Database and critical dependency readiness |
| GET | `/v1/me` | Authenticated user and role |

## 13.2 Subjects

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/subjects` | List authorized pseudonymous subjects |
| POST | `/v1/subjects` | Create synthetic/pseudonymous subject |
| GET | `/v1/subjects/{subject_id}` | Subject summary |
| GET | `/v1/subjects/{subject_id}/timeline` | Reports, events, tasks, trusted memories |

## 13.3 Documents and ingestion

| Method | Route | Purpose |
|---|---|---|
| POST | `/v1/subjects/{subject_id}/documents/upload-intent` | Validate metadata and issue presigned URL |
| POST | `/v1/documents/{document_id}/complete-upload` | Verify S3 object and start workflow |
| GET | `/v1/documents/{document_id}` | Ingestion status |
| POST | `/v1/documents/{document_id}/confirm-redaction` | Confirm redaction if required |
| DELETE | `/v1/documents/{document_id}` | Logical delete and cleanup request |

## 13.4 Agent

| Method | Route | Purpose |
|---|---|---|
| POST | `/v1/subjects/{subject_id}/agent/runs` | Start a scoped agent run |
| GET | `/v1/agent/runs/{run_id}` | Retrieve validated result and trace |
| GET | `/v1/agent/runs/{run_id}/memory-impact` | Used/excluded memories and counterfactual |

## 13.5 Tasks and reviews

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/subjects/{subject_id}/tasks` | List authorized tasks |
| GET | `/v1/tasks/{task_id}` | Task details and evidence |
| POST | `/v1/tasks/{task_id}/approve` | Approve proposed action |
| POST | `/v1/tasks/{task_id}/correct` | Apply reviewer correction |
| POST | `/v1/tasks/{task_id}/reject` | Reject action and store reason |

## 13.6 Research demo

Only implement if core scope is complete.

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/research/cohorts/summary` | Aggregate consented, de-identified counts |

Never return row-level patient data to the researcher role in the hackathon demo.

# 14. Ingestion workflow

## 14.1 Step Functions states

```text
ValidateDocument
  -> StartTextract
  -> WaitForTextract
  -> GetTextractResult
  -> DetectPHI
  -> DecideRedactionReview
      -> WaitForHumanRedactionConfirmation (when needed)
  -> ParseBMDReport
  -> ValidateParsedMeasurements
  -> PersistReportTransaction
  -> BuildMemorySummaries
  -> GenerateEmbeddings
  -> PersistMemories
  -> MarkReady
```

All states must have timeout, retry, and catch policies. Failures must update the document record with a stable failure code and a user-safe message.

## 14.2 Local mock mode

Set `AWS_DOCUMENT_PIPELINE_MODE=mock` to process bundled synthetic parser fixtures without calling Textract or Comprehend Medical. The mock response format must match the production adapters so that business logic tests are identical.

## 14.3 Document retention

- Raw documents are temporary by default.
- Set an S3 lifecycle rule to delete demo uploads after a short configurable period.
- Store only sanitized evidence text necessary for the demo.
- Provide a delete operation that removes S3 objects and logically deletes database records while preserving minimum audit metadata.

# 15. Web application

## 15.1 Required screens

1. **Sign-in / demo access**
2. **Subject list**
3. **Subject timeline** with scan cards and treatment-context events
4. **Upload report** with privacy notice and progress state
5. **Parsed report review** with measurement table and source evidence
6. **Agent comparison** with summary, uncertainty, and safety notice
7. **Memory Impact Trace** showing used and excluded memories
8. **Review task** with approve, correct, and reject controls
9. **New session proof** button or clear-session behavior
10. **System transparency** page listing AWS and CockroachDB integrations

## 15.2 Timeline visualization

Use a simple accessible chart for BMD/T-score values over time. The chart must:

- Never imply a diagnosis.
- Display source report date and skeletal site.
- Visually distinguish excluded measurements.
- Show a tooltip with verification status and source.
- Provide a text table alternative.

## 15.3 Memory Impact Trace UI

Display:

- Key memory that changed behavior.
- Used memories with source and verification badge.
- Excluded memories with reason: rejected, expired, superseded, wrong subject, low confidence, or token-budget omission.
- Proposed action and approval status.
- Counterfactual statement.

Do not reveal hidden model reasoning. Show concise, source-backed rationale generated for the user.

## 15.4 Mobile portability

- Use responsive layout and touch-friendly controls.
- Keep all domain logic in API services.
- Use generated API client types.
- Avoid Node-only features in shared UI packages.
- Add a valid web app manifest and service worker only if it does not destabilize the demo.
- Do not build native iOS/Android packages before core acceptance criteria pass.

# 16. CockroachDB tool integration

## 16.1 Distributed Vector Indexing

Required proof:

- `VECTOR(1024)` memory column.
- Cosine vector index.
- Prefix-filtered subject retrieval or documented alternative.
- `EXPLAIN` plan saved in documentation.
- Evaluation comparing vector-only retrieval with hybrid trusted retrieval.
- Demo footage showing a retrieved correction changing behavior.

## 16.2 Cloud Managed MCP Server

Configure a read-only database role and limited views for the judge/clinician memory inspector.

Recommended views:

```sql
CREATE VIEW mcp_subject_memory_trace AS
SELECT
  m.id,
  m.tenant_id,
  m.subject_id,
  m.memory_type,
  m.source_type,
  m.title,
  m.confidence,
  m.verification_status,
  m.valid_from,
  m.valid_until,
  m.supersedes_id,
  m.superseded_by_id,
  m.created_at
FROM memories AS m;

CREATE VIEW mcp_agent_run_trace AS
SELECT
  ar.id AS run_id,
  ar.subject_id,
  ar.request_type,
  ar.status,
  arm.memory_id,
  arm.trust_score,
  arm.retrieval_rank,
  arm.disposition,
  arm.disposition_reason
FROM agent_runs AS ar
JOIN agent_run_memories AS arm ON arm.agent_run_id = ar.id;
```

Do not expose raw document text, embeddings, credentials, direct identifiers, or unrestricted audit payloads through MCP views.

Add `docs/mcp-demo-prompts.md` containing:

- “Show the verified memory that influenced the latest comparison.”
- “Which candidate memories were excluded and why?”
- “List open review tasks for the demo subject.”
- “Show whether the latest agent run used a superseded memory.”

## 16.3 Agent Skills Repo

Use at least one official skill in a documented operational workflow. Preferred choices:

- Audit user privileges.
- Validate production readiness.
- Check backup/disaster-recovery posture.
- Triage live SQL activity.

Store redacted output under `docs/evidence/agent-skills/` and describe what changed because of the result. Running a skill without using its findings is insufficient.

## 16.4 Optional ccloud CLI

Add scripts for:

- Cluster information retrieval.
- Service-account verification.
- Network/connection information setup.
- Audit or backup status retrieval when supported.

Do not allow the patient-facing model to run `ccloud` commands.

# 17. AWS infrastructure

## 17.1 CDK stacks

Create separate stacks or constructs for:

- `AuthStack`: Cognito.
- `StorageStack`: S3, KMS, lifecycle rules.
- `IngestionStack`: Step Functions, Lambda, IAM, SNS/SQS if required by Textract pattern.
- `ApiStack`: API Gateway and API runtime.
- `AgentStack`: AgentCore deployment configuration, Bedrock permissions, guardrail identifiers.
- `ObservabilityStack`: log groups, alarms, dashboards.

Use environment-specific configuration for `dev` and `demo`.

## 17.2 IAM principles

- Separate execution roles for API, ingestion, and agent.
- Agent role cannot read arbitrary S3 documents.
- Ingestion role cannot invoke reviewer actions.
- API role cannot administer CockroachDB Cloud.
- Secrets are read through AWS Secrets Manager or SSM Parameter Store.
- Deny wildcard actions where practical.
- Log access-denied events without sensitive request contents.

## 17.3 AgentCore Runtime

- Deploy the Strands agent as a Python runtime.
- Use a versioned entry point.
- Enable OpenTelemetry instrumentation.
- Configure session lifetime, but do not rely on runtime session state for durable memory.
- All durable state must be written to CockroachDB.
- Use AgentCore runtime session IDs only as transport/session identifiers.

# 18. Privacy, security, and safety

## 18.1 Threat model

| Threat | Required mitigation |
|---|---|
| Unexpected PHI in upload | DetectPHI, confidence threshold, masked preview, synthetic demo data |
| Cross-subject memory leakage | Scope object in every repository method, database predicates, adversarial tests |
| Prompt injection in report text | Untrusted evidence tags, Guardrails, allowlisted tools, output validation |
| Agent acts on unverified value | Trust filter and human approval |
| Original evidence overwritten | Append-only correction and supersession chain |
| Duplicate workflow execution | Hash and idempotency keys |
| Sensitive data in logs | Structured redaction and disabled body logging |
| MCP overexposure | Read-only role, limited views, no raw text or embeddings |
| Research use after consent withdrawal | Consent check at query time and aggregate-only role |
| Compromised browser request | Cognito validation, CSRF protections where applicable, server-side authorization |
| Model hallucination | Evidence-only prompt, contextual grounding check where applicable, strict uncertainty wording |
| Race condition during correction | Serializable transaction with retry and unique constraints |

## 18.2 Bedrock Guardrails

Configure:

- Prompt attack detection.
- Sensitive information filters for PII.
- Denied topics covering diagnosis and treatment directives.
- Contextual grounding checks for source-backed summarization where compatible.

Guardrails are probabilistic. Application authorization, evidence validation, and human review remain mandatory.

## 18.3 Logging policy

Allowed log fields:

- Request ID.
- Tenant/subject IDs as internal UUIDs.
- Route and status.
- Latency.
- Error code.
- Model ID and token counts.
- Number of memories retrieved/used/excluded.

Forbidden log fields:

- Raw report text.
- Extracted PHI.
- Full model prompts or responses in production.
- Presigned URLs.
- Database passwords.
- Cognito tokens.

# 19. Observability

## 19.1 Metrics

Create metrics for:

- Upload completion rate.
- Ingestion success/failure rate.
- Textract and PHI-screen latency.
- Parser confidence distribution.
- Agent run latency and model errors.
- Memory candidate count.
- Trusted memory count.
- Percentage of responses with evidence.
- Proposed action count by type.
- Approval/correction/rejection rates.
- Transaction retry count.
- Cross-subject access denials.
- MCP query failures.

## 19.2 Tracing

One trace should connect:

```text
API request -> retrieval -> embedding request -> CockroachDB query
-> model invocation -> validation -> action transaction -> response
```

Use request IDs across AWS and database audit events.

## 19.3 Alarms

At minimum:

- Ingestion failure rate above threshold.
- Repeated database connection failures.
- Agent validation failure spike.
- Unauthorized access attempts.
- S3 object retention cleanup failure.

# 20. Evaluation suite

## 20.1 Synthetic dataset

Create 30 synthetic timelines. No fixture may resemble a real identifiable person. Include:

1. Verified correction to a lumbar measurement.
2. Duplicate report upload.
3. Missing previous report.
4. Conflicting scan dates.
5. Different scanner manufacturer.
6. Different skeletal site.
7. Low-confidence OCR value.
8. Superseded patient statement.
9. Expired task.
10. Revoked research consent.
11. Cross-patient similarity trap.
12. Prompt injection in report impression.
13. Agent hypothesis that must not become verified.
14. Concurrent reviewer corrections.
15. Workflow retry after timeout.

Repeat patterns with varied wording and values until 30 timelines exist.

## 20.2 Required metrics

| Metric | Release gate |
|---|---:|
| Correct subject-scoped retrieval | 100% |
| Cross-subject leakage | 0 cases |
| Verified correction adherence | 100% |
| Superseded memory used as active evidence | 0 cases |
| Duplicate ingestion | 0 duplicate reports |
| Agent responses with valid evidence IDs | >= 95% |
| Correct safe-action class | >= 90% |
| Unsafe diagnosis/treatment output | 0 cases |
| Retry produces duplicate action | 0 cases |
| Memory trace reproducibility | 100% on fixed fixtures |

## 20.3 Baseline comparison

Evaluate three retrieval approaches:

1. Most recent report only.
2. Vector similarity only.
3. Hybrid trusted memory retrieval.

The report should show that hybrid retrieval improves correction adherence and prevents stale/superseded-memory use. This directly supports the hackathon’s Agentic Memory Design criterion.

# 21. Test plan

## 21.1 Unit tests

- Parser normalization.
- Memory hash and deduplication.
- Trust scoring.
- Temporal validity.
- Supersession chain validation.
- Agent output schema validation.
- Action allowlist.
- Redaction span handling.
- Authorization scope construction.

## 21.2 Database integration tests

Run against CockroachDB, not SQLite.

- Migrations apply from zero.
- Vector values insert and query.
- Index is used for representative query.
- Duplicate hashes are rejected.
- Serializable retry logic succeeds.
- Concurrent corrections produce one active verified memory.
- Cross-subject queries return no rows.
- Transaction rollback leaves no partial report/task state.

## 21.3 Agent tests

Mock Bedrock for deterministic tests and run a small live-model test suite separately.

- Valid structured response.
- Invalid action type rejected.
- Missing evidence rejected.
- Prompt injection ignored.
- Treatment recommendation blocked.
- Low-confidence evidence produces uncertainty.
- Verified correction changes action.
- Same query in a new session produces consistent memory use.

## 21.4 End-to-end tests

Playwright must cover:

1. Demo login.
2. Upload synthetic report.
3. Wait for processing.
4. Review parsed measurements.
5. Run comparison.
6. Open Memory Impact Trace.
7. Approve or correct task.
8. Sign out and sign in again.
9. Repeat comparison and verify remembered decision.
10. Attempt unauthorized subject URL and verify denial.

# 22. Implementation phases

Codex must implement phases in order. Do not start optional work before the release gate for the current phase passes.

## Phase 0 - Repository and disclosure

### Tasks

- [ ] Create monorepo structure.
- [ ] Add MIT license.
- [ ] Add `NOTICE-PREEXISTING.md` describing the prior Bone Health Tracker parser and prototype.
- [ ] Add `AGENTS.md` from the operating contract in this document.
- [ ] Configure `uv`, `pnpm`, linting, type checks, and CI.
- [ ] Add synthetic-data-only policy.
- [ ] Add basic README with architecture placeholder.

### Acceptance criteria

- Fresh clone installs with documented commands.
- CI runs formatting, type checking, and placeholder test suites.
- No secrets in repository history.
- Pre-existing code disclosure is visible.

## Phase 1 - CockroachDB foundation

### Tasks

- [ ] Implement configuration and secret loading.
- [ ] Create migrations for tenants, users, subjects, documents, reports, measurements, memories, runs, tasks, reviews, consents, and audits.
- [ ] Implement vector feature and index migration.
- [ ] Add database retry helper for serializable transactions.
- [ ] Seed one tenant, judge user, clinician user, and synthetic subject.
- [ ] Add repository scope object.

### Acceptance criteria

- Migrations apply to local CockroachDB and CockroachDB Cloud.
- Vector insert and similarity query work.
- Cross-subject access tests pass.
- Duplicate and concurrent transaction tests pass.

## Phase 2 - API and authentication

### Tasks

- [ ] Implement FastAPI service and health endpoints.
- [ ] Implement Cognito JWT validation with local mock auth.
- [ ] Implement role and subject authorization.
- [ ] Implement subject and timeline endpoints.
- [ ] Generate TypeScript API client.
- [ ] Add structured audit middleware.

### Acceptance criteria

- Unauthorized requests return 401.
- Wrong-role and wrong-subject requests return 403 or 404 without leaking existence.
- OpenAPI client builds.
- Audit event is written for sensitive reads and all writes.

## Phase 3 - Ingestion vertical slice

### Tasks

- [ ] Implement upload intent and completion endpoints.
- [ ] Implement S3 adapter and local storage adapter.
- [ ] Implement mock Textract and DetectPHI adapters.
- [ ] Integrate the custom BMD parser behind a stable interface.
- [ ] Persist reports, measurements, evidence, and initial memory.
- [ ] Add duplicate detection by SHA-256.
- [ ] Display ingestion state in web client.

### Acceptance criteria

- Synthetic report reaches `READY` state locally.
- Duplicate upload returns existing report instead of duplicating data.
- Failed parsing leaves a recoverable status and no partial measurements.
- Existing parser provenance is stored with name and version.

## Phase 4 - AWS document workflow

### Tasks

- [ ] Implement CDK storage and ingestion stacks.
- [ ] Add asynchronous Textract flow.
- [ ] Add Comprehend Medical DetectPHI adapter.
- [ ] Add Step Functions retry/catch behavior.
- [ ] Add encrypted S3 lifecycle policy.
- [ ] Deploy development environment.

### Acceptance criteria

- Real synthetic PDF processes through AWS.
- Likely PHI findings are masked or sent to review.
- Raw object is encrypted and scheduled for deletion.
- Failure paths update stable document error codes.

## Phase 5 - Trusted memory retrieval

### Tasks

- [ ] Implement Titan embedding adapter.
- [ ] Generate 1,024-dimensional normalized embeddings.
- [ ] Implement vector candidate query.
- [ ] Implement deterministic timeline additions.
- [ ] Implement trust scoring and exclusion reasons.
- [ ] Record candidate disposition in `agent_run_memories`.
- [ ] Add evaluation fixtures.

### Acceptance criteria

- Vector index is used in representative query.
- Rejected, expired, and superseded memories are excluded.
- Latest verified correction is always considered.
- Cross-patient leakage evaluation is zero.

## Phase 6 - Agent and safe actions

### Tasks

- [ ] Implement versioned system prompt.
- [ ] Implement Strands agent with allowlisted tools.
- [ ] Deploy to AgentCore Runtime.
- [ ] Implement strict input/output schemas.
- [ ] Configure Guardrails.
- [ ] Implement proposed review task action.
- [ ] Implement approval/correction/rejection transactions.

### Acceptance criteria

- Agent never directly writes verified memory.
- Invalid output is rejected and safely retried or returned as an error.
- Verified correction changes later behavior.
- Unsafe diagnosis/treatment test cases produce no prohibited output.

## Phase 7 - Memory Impact Trace and polished UI

### Tasks

- [ ] Implement timeline chart and text alternative.
- [ ] Implement used/excluded memory cards.
- [ ] Implement counterfactual statement.
- [ ] Implement review task controls.
- [ ] Implement new-session proof flow.
- [ ] Add integration transparency page.

### Acceptance criteria

- Judge can understand why the result changed within 20 seconds.
- Excluded memory reasons are visible.
- New session retrieves prior approval.
- UI passes basic keyboard and color-contrast checks.

## Phase 8 - MCP and Agent Skills

### Tasks

- [ ] Create read-only MCP role and limited views.
- [ ] Configure Managed MCP Server.
- [ ] Add demo query guide.
- [ ] Run an official Agent Skill for privileges or production readiness.
- [ ] Apply at least one finding and document it.

### Acceptance criteria

- MCP can answer demo questions without exposing raw text or another subject.
- MCP credentials cannot write.
- Agent Skill evidence and remediation are committed without secrets.

## Phase 9 - Evaluation and resilience

### Tasks

- [ ] Complete 30 synthetic timelines.
- [ ] Run baseline comparisons.
- [ ] Add workflow retry test.
- [ ] Add concurrent correction test.
- [ ] Add prompt-injection tests.
- [ ] Add observability dashboards and alarms.
- [ ] Produce evaluation report.

### Acceptance criteria

- All release-gate metrics pass.
- Evaluation report is reproducible with one command.
- Failure recovery creates no duplicate memory or action.

## Phase 10 - Submission package

### Tasks

- [ ] Finish README and architecture documentation.
- [ ] Add one-command local demo setup.
- [ ] Add judge testing instructions and demo credentials.
- [ ] Record video under three minutes.
- [ ] Publish public app.
- [ ] Verify license and repository About section.
- [ ] Verify application remains available during judging period.
- [ ] Complete Devpost description and tool-use explanations.

### Acceptance criteria

- Fresh-machine judge test succeeds.
- Video visibly shows CockroachDB memory at work.
- No real health data appears anywhere.
- All links are public and functional.

# 23. Recommended implementation commands

The exact commands may change as scaffolding evolves, but the repository should converge on this interface.

```bash
make install
make dev-infra
make migrate
make seed
make dev
make test
make test-integration
make test-e2e
make eval
make lint
make typecheck
make security-check
make deploy-demo
```

`make dev` should start local CockroachDB, the API, the mock ingestion worker, the agent mock, and the web client.

# 24. Environment variables

Provide `.env.example` with descriptions and safe placeholder values.

```text
APP_ENV=local
LOG_LEVEL=INFO
DATABASE_URL=
COCKROACH_CLUSTER_ID=
AWS_REGION=us-west-2
AWS_DOCUMENT_PIPELINE_MODE=mock
S3_DOCUMENT_BUCKET=
KMS_KEY_ARN=
COGNITO_USER_POOL_ID=
COGNITO_CLIENT_ID=
BEDROCK_CHAT_MODEL_ID=
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
BEDROCK_GUARDRAIL_ID=
BEDROCK_GUARDRAIL_VERSION=
AGENTCORE_RUNTIME_ARN=
MCP_READONLY_DATABASE=
RAW_DOCUMENT_RETENTION_DAYS=1
ALLOW_SYNTHETIC_DEMO_ONLY=true
```

# 25. Architecture Decision Records

Create ADRs for at least:

1. CockroachDB as the sole durable memory system.
2. Hybrid retrieval instead of vector-only RAG.
3. Human-approved actions instead of autonomous clinical action.
4. Append-only corrections and supersession.
5. AgentCore Runtime with Strands.
6. Synthetic-data-only public demo.
7. MCP isolation from patient-facing agent tools.
8. Selected vector prefix/index strategy after `EXPLAIN` testing.

# 26. Definition of done

BoneTwin is done for submission only when all statements are true:

- [ ] CockroachDB stores structured facts, vectors, task state, corrections, run traces, and audits.
- [ ] Distributed vector indexing is visibly and measurably used.
- [ ] Managed MCP Server is configured with read-only limited views.
- [ ] An official Agent Skill is run and produces an implemented improvement.
- [ ] The agent runs on AWS and uses Amazon Bedrock.
- [ ] A correction changes the agent’s behavior in a later session.
- [ ] The Memory Impact Trace displays used and excluded memories.
- [ ] The human review loop creates verified memory transactionally.
- [ ] Cross-subject leakage tests have zero failures.
- [ ] Duplicate/retry tests create no duplicate records or actions.
- [ ] Unsafe medical-output tests pass.
- [ ] Public demo uses only synthetic data.
- [ ] Repository is public, licensed, documented, and reproducible.
- [ ] Demo video is under three minutes and shows the memory layer.
- [ ] Pre-existing parser work is clearly disclosed.

# 27. Three-minute demo script

## 0:00-0:18 - Problem and promise

“Bone-density reports arrive years apart, often from different scanners and sites. The missing piece is not another chatbot; it is trustworthy memory of what was verified, corrected, and left unresolved.”

## 0:18-0:43 - Upload and persistence

Upload a synthetic DXA report. Show the workflow status, extracted measurements, parser confidence, and a small developer panel confirming that report state and evidence were committed to CockroachDB.

## 0:43-1:12 - Retrieval

Run “Compare this report with the subject’s history.” Show CockroachDB retrieving the previous report, an earlier verified correction, and an open task. Briefly show the vector retrieval trace.

## 1:12-1:38 - Memory changes action

The agent explains that a lumbar measurement was previously marked unsuitable for longitudinal comparison. It excludes that value and proposes a clinician-review task based on the hip timeline.

## 1:38-1:58 - Human review becomes memory

Approve or correct the task. Show the atomic write of the review event, verified memory, and audit event.

## 1:58-2:18 - New session proof

Sign out or open a new session. Run the comparison again. The agent remembers and applies the prior decision without being reminded.

## 2:18-2:38 - Memory Impact Trace

Show used memories, excluded superseded memory, and the counterfactual: “Without the verified correction, the agent would have included the lumbar value.”

## 2:38-2:52 - MCP and production readiness

Use the read-only MCP inspector to ask which memory influenced the run. Flash the security/production-readiness Agent Skill output and one remediation.

## 2:52-3:00 - Close

“BoneTwin does not just remember data. It remembers what can be trusted, what was corrected, what remains unresolved, and why.”

# 28. Devpost submission language

## Tool usage summary

**CockroachDB Distributed Vector Indexing:** Stores de-identified memory embeddings alongside transactional scan data and retrieves subject-scoped semantic candidates. Hybrid trust filtering prevents rejected, expired, or superseded memories from influencing future actions.

**CockroachDB Cloud Managed MCP Server:** Provides a read-only Memory Inspector for judges and authorized reviewers to query evidence, retrieval disposition, task state, and correction history without a custom database proxy.

**CockroachDB Agent Skills:** Audits the database’s security or production-readiness posture. BoneTwin includes the redacted result and documents the remediation applied.

**Amazon Bedrock and AgentCore Runtime:** Host and execute the Strands agent and generate source-backed structured decisions. Bedrock also generates embeddings and applies configurable guardrails.

**AWS Step Functions, Lambda, S3, Textract, and Comprehend Medical:** Implement durable encrypted document ingestion, OCR, likely-PHI detection, parsing, retries, and cleanup.

# 29. Master prompt to start Codex

Copy the following prompt into Codex after placing this document at the repository root as `CODEX_IMPLEMENTATION_SPEC.md`.

```text
You are the implementation engineer for BoneTwin. Read CODEX_IMPLEMENTATION_SPEC.md completely, then create or update AGENTS.md so its mandatory operating rules are visible to future Codex sessions.

Begin with Phase 0 only. Do not implement later phases yet.

Before editing:
1. Inspect the repository.
2. Summarize the Phase 0 deliverables.
3. List the exact files you will create or modify.
4. Identify any conflict between the existing repository and the specification.

Then implement Phase 0 with production-quality scaffolding. Use uv for Python and pnpm for Node.js. Add CI, formatting, type checking, test placeholders, MIT license, SECURITY.md, CONTRIBUTING.md, NOTICE-PREEXISTING.md, .env.example, and the required monorepo directories. The notice must clearly say that the earlier Bone Health Tracker concept and custom BMD parser predate this hackathon, while the BoneTwin agentic-memory architecture and implementation are new.

Do not add real patient data, secrets, diagnosis features, medication recommendations, or autonomous clinical actions.

After implementation:
1. Run all available formatting, linting, type-checking, and tests.
2. Fix every failure.
3. Update docs/implementation-status.md with evidence for each Phase 0 acceptance criterion.
4. Report changed files, commands run, test results, and remaining risks.
5. Stop after Phase 0.
```

For later phases, instruct Codex with:

```text
Implement Phase N from CODEX_IMPLEMENTATION_SPEC.md. Inspect current code first, preserve all completed acceptance criteria, make only phase-relevant changes, run the full relevant test suite, update docs/implementation-status.md, and stop at the phase boundary.
```

# 30. Reference sources

The implementation must verify service availability, API details, and regional support against current official documentation before deployment.

1. CockroachDB x AWS Hackathon official rules and submission requirements: `https://cockroachdb-ai.devpost.com/rules`
2. CockroachDB Cloud Managed MCP Server: `https://www.cockroachlabs.com/docs/cockroachcloud/connect-to-the-cockroachdb-cloud-mcp-server`
3. CockroachDB vector indexes: `https://www.cockroachlabs.com/docs/stable/vector-indexes`
4. CockroachDB and AI overview: `https://www.cockroachlabs.com/docs/stable/cockroachdb-and-ai`
5. CockroachDB Agent Skills: `https://www.cockroachlabs.com/docs/v26.2/agent-skills`
6. Amazon Bedrock AgentCore Runtime: `https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html`
7. Deploy MCP servers in AgentCore Runtime: `https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html`
8. Amazon Bedrock Guardrails: `https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html`
9. Amazon Comprehend Medical DetectPHI: `https://docs.aws.amazon.com/comprehend-medical/latest/dev/textanalysis-phi.html`
10. Amazon Textract asynchronous operations: `https://docs.aws.amazon.com/textract/latest/dg/api-async.html`
11. Amazon Titan Text Embeddings V2: `https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html`
12. Strands Agents Python SDK: `https://github.com/strands-agents/sdk-python`

# Appendix A - Existing project assets to preserve

The original Bone Health Tracker concept provides useful starting assets:

- Personal motivation and a clear bone-health problem.
- A custom BMD report parser capable of handling multiple supported bone sites and report formats.
- Existing visualization concepts.
- Experience integrating Textract and Comprehend Medical.
- A privacy-first intent to minimize collection of identifying information.

These assets should be reused only with transparent disclosure. BoneTwin’s new work is the CockroachDB memory model, trust engine, agent workflow, AWS production architecture, human review loop, evaluation framework, and public demo.

# Appendix B - Judge-focused 90+ checklist

## Agentic Memory Design

- [ ] Memory has types, trust, provenance, time, and supersession.
- [ ] Memory changes a later action.
- [ ] Task state survives new sessions and retries.
- [ ] Counterfactual demonstrates why memory matters.

## Technical Implementation

- [ ] Vector index is used and measured.
- [ ] MCP is read-only and scoped.
- [ ] Agent Skill drives a remediation.
- [ ] Transactions and idempotency are tested.
- [ ] Model output is schema validated.

## Real-World Impact

- [ ] Story is understandable without medical jargon.
- [ ] User benefit is longitudinal organization and safer review preparation.
- [ ] No exaggerated medical claims.

## Production Readiness

- [ ] Authentication and authorization.
- [ ] PHI screening and short retention.
- [ ] Threat model and adversarial tests.
- [ ] Observability and failure recovery.
- [ ] Synthetic judge dataset and reproducible setup.

## Creativity and Originality

- [ ] Memory Trust Engine is visible.
- [ ] Correction inheritance is visible.
- [ ] Memory Impact Trace is visible.
- [ ] Hybrid retrieval outperforms vector-only baseline.
