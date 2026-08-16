ALTER TABLE agent_runs
    ADD COLUMN decision_payload JSONB NULL;

ALTER TABLE agent_runs
    ADD COLUMN persisted_review_applied BOOL NOT NULL DEFAULT false;

ALTER TABLE review_events
    ADD COLUMN decision_idempotency_key STRING NULL;

ALTER TABLE review_events
    ADD CONSTRAINT review_events_tenant_idempotency_key
    UNIQUE (tenant_id, decision_idempotency_key);
