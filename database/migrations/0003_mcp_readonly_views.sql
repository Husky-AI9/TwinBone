CREATE VIEW mcp_subject_memory_trace AS
SELECT
    m.id AS memory_id,
    m.tenant_id,
    m.subject_id,
    m.memory_type,
    m.source_type,
    m.source_id,
    m.title,
    m.confidence,
    m.verification_status,
    m.valid_from,
    m.valid_until,
    m.supersedes_id,
    m.superseded_by_id,
    m.created_at
FROM memories AS m
WHERE m.tenant_id = '10000000-0000-4000-8000-000000000001'
  AND m.subject_id = '30000000-0000-4000-8000-000000000001';

CREATE VIEW mcp_agent_run_trace AS
SELECT
    ar.id AS run_id,
    ar.tenant_id,
    ar.subject_id,
    ar.request_type,
    ar.status AS run_status,
    ar.started_at,
    ar.completed_at,
    arm.memory_id,
    arm.vector_distance,
    arm.trust_score,
    arm.retrieval_rank,
    arm.disposition,
    arm.disposition_reason
FROM agent_runs AS ar
JOIN agent_run_memories AS arm ON arm.agent_run_id = ar.id
WHERE ar.tenant_id = '10000000-0000-4000-8000-000000000001'
  AND ar.subject_id = '30000000-0000-4000-8000-000000000001';

CREATE VIEW mcp_open_review_tasks AS
SELECT
    rt.id AS task_id,
    rt.tenant_id,
    rt.subject_id,
    rt.agent_run_id,
    rt.action_type,
    rt.status,
    rt.title,
    rt.requires_role,
    rt.due_at,
    rt.created_at
FROM review_tasks AS rt
WHERE rt.status IN ('PROPOSED', 'AWAITING_REVIEW')
  AND rt.tenant_id = '10000000-0000-4000-8000-000000000001'
  AND rt.subject_id = '30000000-0000-4000-8000-000000000001';

CREATE ROLE IF NOT EXISTS bonetwin_mcp_reader;

GRANT USAGE ON SCHEMA public TO bonetwin_mcp_reader;

GRANT SELECT ON TABLE
    mcp_subject_memory_trace,
    mcp_agent_run_trace,
    mcp_open_review_tasks
TO bonetwin_mcp_reader;

REVOKE ALL ON TABLE
    mcp_subject_memory_trace,
    mcp_agent_run_trace,
    mcp_open_review_tasks
FROM public;

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM public;
