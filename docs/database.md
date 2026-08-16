# CockroachDB foundation

## Version and compatibility

Phase 1 was verified locally against CockroachDB CCL v26.2.4 using SQLAlchemy 2.0, Psycopg 3,
the CockroachDB SQLAlchemy adapter, and Alembic. Reviewed SQL uses CockroachDB-native
`STRING`, `JSONB`, `UUID`, `TIMESTAMPTZ`, and `VECTOR(1024)` types.

The schema uses constrained strings instead of custom enum types. This keeps migrations
portable across supported CockroachDB deployment types while preserving database-level
validation.

## Local setup

The recommended path is:

```bash
docker compose up -d --wait cockroach
uv run python -m scripts.migrate
uv run python -m scripts.seed
BONETWIN_RUN_DB_TESTS=1 uv run pytest -m integration
```

The Docker image is pinned to `cockroachdb/cockroach:v26.2.4`. The compose server is insecure
and intended only for local development.

Windows systems without Docker can use the checksum-pinned scripts documented in the root
README. Downloaded binaries and database storage are ignored by Git.

## Cloud validation

Use a dedicated migration administrator and obtain a connection string from the CockroachDB
Cloud Connect dialog. Keep TLS verification enabled:

```bash
export DATABASE_URL='postgresql://<user>:<password>@<host>:26257/bonetwin?sslmode=verify-full'
uv run python -m scripts.migrate
uv run python -m scripts.seed
BONETWIN_RUN_DB_TESTS=1 uv run pytest -m integration
```

The migration runner creates the configured database when absent, enables the vector-index
cluster feature through an administrative autocommit connection, then applies Alembic
revisions. If the migration principal cannot change cluster settings, an administrator must
enable `feature.vector_index.enabled` once before migration.

Do not paste a Cloud URL into logs, issues, screenshots, command history shared with others,
or committed files.

## Migration layout

- `0001_initial_schema`: tenant, user, subject, document, report, measurement, treatment
  context, memory, run, task, review, consent, and audit tables.
- `0002_memory_vector_index`: subject-prefixed cosine index over `VECTOR(1024)`.

The SQL files under `database/migrations` are authoritative and executed by their matching
Alembic revisions.

## Isolation rules

Patient-scoped repository methods require an immutable `AccessScope(tenant_id, subject_id,
role)`. Queries constrain both identifiers, while composite foreign keys prevent child rows
from binding a subject or actor in another tenant. Integration tests cover cross-tenant
subject lookup and cross-subject vector/memory access.

## Transaction retries

CockroachDB uses `SERIALIZABLE` isolation by default and reports retryable serialization
failures with SQLSTATE `40001`. `run_transaction` retries only that state, uses bounded
exponential backoff with full jitter, and creates a new transaction for each attempt.
