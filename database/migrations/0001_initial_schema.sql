CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    cognito_subject STRING NOT NULL,
    role STRING NOT NULL CHECK (
        role IN ('PATIENT', 'CLINICIAN', 'RESEARCHER', 'ADMIN', 'JUDGE')
    ),
    display_name STRING NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, cognito_subject),
    UNIQUE (tenant_id, id)
);

CREATE TABLE subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    pseudonym STRING NOT NULL,
    owner_user_id UUID NULL,
    date_of_birth_year INT NULL CHECK (
        date_of_birth_year IS NULL OR date_of_birth_year BETWEEN 1900 AND 2100
    ),
    status STRING NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, pseudonym),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, owner_user_id) REFERENCES app_users (tenant_id, id)
);

CREATE INDEX subjects_tenant_idx ON subjects (tenant_id, id);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    status STRING NOT NULL CHECK (
        status IN (
            'UPLOADING', 'UPLOADED', 'EXTRACTING', 'PHI_REVIEW', 'PARSING',
            'INDEXING', 'READY', 'FAILED', 'DELETED'
        )
    ),
    original_filename STRING NOT NULL,
    content_type STRING NOT NULL,
    byte_size INT8 NOT NULL CHECK (byte_size >= 0),
    sha256 STRING NOT NULL CHECK (length(sha256) = 64),
    s3_bucket STRING NULL,
    s3_key STRING NULL,
    upload_idempotency_key STRING NOT NULL,
    raw_retention_until TIMESTAMPTZ NULL,
    failure_code STRING NULL,
    failure_message STRING NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, subject_id, sha256),
    UNIQUE (tenant_id, upload_idempotency_key),
    UNIQUE (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES app_users (tenant_id, id)
);

CREATE TABLE scan_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    document_id UUID NOT NULL,
    scan_date DATE NULL,
    report_type STRING NOT NULL DEFAULT 'DXA_BMD',
    facility_pseudonym STRING NULL,
    scanner_manufacturer STRING NULL,
    scanner_model STRING NULL,
    parser_name STRING NOT NULL,
    parser_version STRING NOT NULL,
    extraction_confidence DECIMAL(5, 4) NULL CHECK (
        extraction_confidence IS NULL
        OR extraction_confidence BETWEEN 0 AND 1
    ),
    review_required BOOL NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id),
    UNIQUE (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, subject_id, document_id)
        REFERENCES documents (tenant_id, subject_id, id)
);

CREATE INDEX reports_subject_date_idx
    ON scan_reports (tenant_id, subject_id, scan_date DESC);

CREATE TABLE measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    report_id UUID NOT NULL,
    skeletal_site STRING NOT NULL,
    region STRING NULL,
    side STRING NULL,
    bmd_g_cm2 DECIMAL(8, 4) NULL,
    t_score DECIMAL(5, 2) NULL,
    z_score DECIMAL(5, 2) NULL,
    unit STRING NULL,
    extraction_confidence DECIMAL(5, 4) NOT NULL CHECK (
        extraction_confidence BETWEEN 0 AND 1
    ),
    source_page INT NULL CHECK (source_page IS NULL OR source_page > 0),
    source_text STRING NULL,
    source_bbox JSONB NULL,
    usable_for_longitudinal BOOL NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, subject_id, report_id)
        REFERENCES scan_reports (tenant_id, subject_id, id)
);

CREATE INDEX measurement_timeline_idx
    ON measurements (tenant_id, subject_id, skeletal_site, region, report_id);

CREATE TABLE treatment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    event_date DATE NULL,
    category STRING NOT NULL,
    description STRING NOT NULL,
    source_type STRING NOT NULL,
    verification_status STRING NOT NULL CHECK (
        verification_status IN (
            'PROPOSED', 'AWAITING_REVIEW', 'VERIFIED',
            'REJECTED', 'SUPERSEDED', 'EXPIRED'
        )
    ),
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id),
    FOREIGN KEY (tenant_id, created_by) REFERENCES app_users (tenant_id, id)
);

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    subject_id UUID NULL,
    memory_type STRING NOT NULL CHECK (
        memory_type IN ('EPISODIC', 'SEMANTIC', 'PROCEDURAL', 'TASK', 'EVIDENCE')
    ),
    source_type STRING NOT NULL,
    source_id UUID NULL,
    title STRING NOT NULL,
    content STRING NOT NULL,
    content_hash STRING NOT NULL CHECK (length(content_hash) = 64),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    verification_status STRING NOT NULL CHECK (
        verification_status IN (
            'PROPOSED', 'AWAITING_REVIEW', 'VERIFIED',
            'REJECTED', 'SUPERSEDED', 'EXPIRED'
        )
    ),
    valid_from TIMESTAMPTZ NULL,
    valid_until TIMESTAMPTZ NULL CHECK (
        valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from
    ),
    supersedes_id UUID NULL REFERENCES memories (id),
    superseded_by_id UUID NULL REFERENCES memories (id),
    privacy_classification STRING NOT NULL CHECK (
        privacy_classification IN ('DEIDENTIFIED', 'SENSITIVE', 'RESTRICTED')
    ),
    embedding_model STRING NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_by_actor_type STRING NOT NULL CHECK (
        created_by_actor_type IN ('USER', 'CLINICIAN', 'AGENT', 'SYSTEM', 'RESEARCHER')
    ),
    created_by_actor_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, content_hash, source_id),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id),
    CHECK (supersedes_id IS NULL OR supersedes_id != id),
    CHECK (superseded_by_id IS NULL OR superseded_by_id != id)
);

CREATE INDEX memories_subject_status_idx
    ON memories (tenant_id, subject_id, verification_status, created_at DESC);

CREATE TABLE memory_relations (
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    from_memory_id UUID NOT NULL,
    to_memory_id UUID NOT NULL,
    relation_type STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (from_memory_id, to_memory_id, relation_type),
    FOREIGN KEY (tenant_id, from_memory_id) REFERENCES memories (tenant_id, id),
    FOREIGN KEY (tenant_id, to_memory_id) REFERENCES memories (tenant_id, id),
    CHECK (from_memory_id != to_memory_id)
);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    user_id UUID NOT NULL,
    request_type STRING NOT NULL CHECK (
        request_type IN (
            'COMPARE_REPORTS', 'EXPLAIN_MEMORY',
            'PREPARE_VISIT', 'REVIEW_OPEN_TASKS'
        )
    ),
    user_query STRING NOT NULL,
    model_id STRING NOT NULL,
    prompt_version STRING NOT NULL,
    run_idempotency_key STRING NOT NULL,
    status STRING NOT NULL CHECK (
        status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')
    ),
    response_summary STRING NULL,
    uncertainty STRING NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    error_code STRING NULL,
    UNIQUE (tenant_id, run_idempotency_key),
    UNIQUE (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES app_users (tenant_id, id)
);

CREATE TABLE agent_run_memories (
    agent_run_id UUID NOT NULL REFERENCES agent_runs (id),
    memory_id UUID NOT NULL REFERENCES memories (id),
    vector_distance DECIMAL(12, 8) NULL,
    trust_score DECIMAL(8, 6) NOT NULL CHECK (trust_score BETWEEN 0 AND 1),
    retrieval_rank INT NOT NULL CHECK (retrieval_rank > 0),
    disposition STRING NOT NULL CHECK (
        disposition IN ('USED', 'EXCLUDED', 'SUPPORTING')
    ),
    disposition_reason STRING NULL,
    PRIMARY KEY (agent_run_id, memory_id)
);

CREATE TABLE review_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    agent_run_id UUID NOT NULL,
    action_type STRING NOT NULL CHECK (
        action_type IN (
            'CREATE_CLINICIAN_REVIEW', 'REQUEST_MISSING_REPORT',
            'REQUEST_DATE_CONFIRMATION', 'PREPARE_APPOINTMENT_QUESTIONS'
        )
    ),
    status STRING NOT NULL CHECK (
        status IN (
            'PROPOSED', 'AWAITING_REVIEW', 'APPROVED', 'CORRECTED',
            'REJECTED', 'APPLIED', 'FAILED', 'CANCELLED'
        )
    ),
    title STRING NOT NULL,
    proposed_payload JSONB NOT NULL,
    applied_payload JSONB NULL,
    requires_role STRING NOT NULL DEFAULT 'CLINICIAN' CHECK (
        requires_role IN ('CLINICIAN', 'ADMIN')
    ),
    action_idempotency_key STRING NOT NULL,
    due_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ NULL,
    resolved_by UUID NULL,
    resolution_note STRING NULL,
    UNIQUE (tenant_id, action_idempotency_key),
    UNIQUE (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, subject_id, agent_run_id)
        REFERENCES agent_runs (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, resolved_by) REFERENCES app_users (tenant_id, id)
);

CREATE TABLE review_task_evidence (
    task_id UUID NOT NULL REFERENCES review_tasks (id),
    memory_id UUID NOT NULL REFERENCES memories (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (task_id, memory_id)
);

CREATE TABLE review_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    task_id UUID NOT NULL,
    actor_user_id UUID NOT NULL,
    event_type STRING NOT NULL,
    previous_status STRING NULL,
    new_status STRING NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, subject_id, task_id)
        REFERENCES review_tasks (tenant_id, subject_id, id),
    FOREIGN KEY (tenant_id, actor_user_id) REFERENCES app_users (tenant_id, id)
);

CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subject_id UUID NOT NULL,
    scope STRING NOT NULL,
    status STRING NOT NULL CHECK (status IN ('GRANTED', 'REVOKED')),
    effective_at TIMESTAMPTZ NOT NULL,
    actor_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id),
    FOREIGN KEY (tenant_id, actor_user_id) REFERENCES app_users (tenant_id, id)
);

CREATE INDEX consent_subject_scope_idx
    ON consent_records (tenant_id, subject_id, scope, effective_at DESC);

CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id),
    subject_id UUID NULL,
    actor_type STRING NOT NULL CHECK (
        actor_type IN ('USER', 'CLINICIAN', 'AGENT', 'SYSTEM', 'RESEARCHER')
    ),
    actor_id STRING NULL,
    action STRING NOT NULL,
    resource_type STRING NOT NULL,
    resource_id STRING NULL,
    request_id STRING NOT NULL,
    outcome STRING NOT NULL CHECK (outcome IN ('SUCCESS', 'DENIED', 'FAILED')),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects (tenant_id, id)
);

CREATE INDEX audit_tenant_time_idx
    ON audit_events (tenant_id, created_at DESC);
