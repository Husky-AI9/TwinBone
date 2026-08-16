ALTER TABLE review_events
    DROP CONSTRAINT review_events_tenant_idempotency_key;

ALTER TABLE review_events
    DROP COLUMN decision_idempotency_key;

ALTER TABLE agent_runs
    DROP COLUMN persisted_review_applied;

ALTER TABLE agent_runs
    DROP COLUMN decision_payload;
