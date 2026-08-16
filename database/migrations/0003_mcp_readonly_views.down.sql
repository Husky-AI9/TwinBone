REVOKE SELECT ON TABLE
    mcp_subject_memory_trace,
    mcp_agent_run_trace,
    mcp_open_review_tasks
FROM bonetwin_mcp_reader;

REVOKE USAGE ON SCHEMA public FROM bonetwin_mcp_reader;

DROP VIEW IF EXISTS mcp_open_review_tasks;
DROP VIEW IF EXISTS mcp_agent_run_trace;
DROP VIEW IF EXISTS mcp_subject_memory_trace;

DROP ROLE IF EXISTS bonetwin_mcp_reader;
