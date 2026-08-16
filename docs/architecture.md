# Architecture

BoneTwin uses a Next.js client boundary and CockroachDB as the sole durable memory system. It
will add FastAPI, an AWS document workflow, and a Strands agent hosted on AgentCore with
Bedrock models in later phases.

Phase 1 implements typed configuration, Alembic migrations, reviewed SQL, deterministic
synthetic seed data, scope-enforcing repositories, vector similarity, and serializable
transaction retries. Detailed API, deployment, and agent sequence diagrams will be added
with the phases that can verify them.
