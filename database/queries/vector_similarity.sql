SELECT
    id,
    title,
    verification_status,
    embedding <=> CAST(:query_embedding AS VECTOR(1024)) AS cosine_distance
FROM memories
WHERE tenant_id = :tenant_id
  AND subject_id = :subject_id
  AND verification_status IN ('VERIFIED', 'AWAITING_REVIEW', 'PROPOSED')
  AND superseded_by_id IS NULL
  AND (valid_until IS NULL OR valid_until > now())
ORDER BY embedding <=> CAST(:query_embedding AS VECTOR(1024))
LIMIT :candidate_limit;
