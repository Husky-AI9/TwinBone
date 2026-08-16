# MCP Memory Inspector demo

Use only the three curated `mcp_*` views. Always include the fixed synthetic demo subject
scope in visible queries, even though the views already enforce it.

## Judge prompts

1. **Show the verified memory that influenced the latest comparison.**

   Query `mcp_agent_run_trace` for the latest successful run, select `USED` memory IDs, then
   join those IDs to `mcp_subject_memory_trace`. Return title, source type, verification
   status, trust score, and retrieval rank.

2. **Which candidate memories were excluded and why?**

   Query `mcp_agent_run_trace` for `disposition = 'EXCLUDED'`. Return memory ID,
   `disposition_reason`, and verification status from `mcp_subject_memory_trace`.

3. **List open review tasks for the demo subject.**

   Query `mcp_open_review_tasks`. Return task ID, action type, status, title, required role,
   and creation time.

4. **Show whether the latest agent run used a superseded memory.**

   Join the latest run's `USED` rows to `mcp_subject_memory_trace` and count rows whose
   `verification_status = 'SUPERSEDED'` or `superseded_by_id IS NOT NULL`. The expected
   answer is zero.

## Safety checks

- Refuse prompts requesting raw document text, embeddings, audit payloads, identity fields,
  or a different subject.
- Do not query base tables.
- Do not invoke write tools.
- Do not infer a diagnosis or treatment recommendation from the trace.
