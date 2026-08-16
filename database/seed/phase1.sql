INSERT INTO tenants (id, name)
VALUES ('10000000-0000-4000-8000-000000000001', 'BoneTwin Synthetic Demo')
ON CONFLICT (id) DO UPDATE SET name = excluded.name;

INSERT INTO app_users (id, tenant_id, cognito_subject, role, display_name)
VALUES
    (
        '20000000-0000-4000-8000-000000000001',
        '10000000-0000-4000-8000-000000000001',
        'demo-judge',
        'JUDGE',
        'Synthetic Judge'
    ),
    (
        '20000000-0000-4000-8000-000000000002',
        '10000000-0000-4000-8000-000000000001',
        'demo-clinician',
        'CLINICIAN',
        'Synthetic Clinician'
    )
ON CONFLICT (id) DO UPDATE SET
    role = excluded.role,
    display_name = excluded.display_name;

INSERT INTO subjects (
    id,
    tenant_id,
    pseudonym,
    owner_user_id,
    date_of_birth_year,
    status
)
VALUES (
    '30000000-0000-4000-8000-000000000001',
    '10000000-0000-4000-8000-000000000001',
    'SYNTH-BONE-001',
    '20000000-0000-4000-8000-000000000002',
    1965,
    'ACTIVE'
)
ON CONFLICT (id) DO UPDATE SET
    pseudonym = excluded.pseudonym,
    owner_user_id = excluded.owner_user_id,
    status = excluded.status;
