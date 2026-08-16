# BoneTwin Phase 9 evaluation

- Dataset: `bonetwin-phase9-synthetic-timelines` v1.0.0
- Synthetic timelines: 30
- Overall result: **PASS**

## Retrieval comparison

| Approach                | Subject scoped | Cross-subject leaks | Key recall | Correction adherence | Superseded used | Safe action |
| ----------------------- | -------------: | ------------------: | ---------: | -------------------: | --------------: | ----------: |
| most recent report only |         100.0% |                   0 |       0.0% |                 0.0% |               0 |      53.33% |
| vector similarity only  |           0.0% |                  30 |       0.0% |                 0.0% |               0 |      53.33% |
| hybrid trusted memory   |         100.0% |                   0 |     100.0% |               100.0% |               0 |      100.0% |

## Release metrics

- `correct_subject_scoped_retrieval_percent`: 100.0
- `cross_subject_leakage_cases`: 0
- `verified_correction_adherence_percent`: 100.0
- `superseded_memory_used_cases`: 0
- `duplicate_ingestion_reports`: 0
- `agent_responses_with_valid_evidence_ids_percent`: 100.0
- `correct_safe_action_class_percent`: 100.0
- `unsafe_diagnosis_or_treatment_outputs`: 0
- `retry_duplicate_actions`: 0
- `memory_trace_reproducibility_percent`: 100.0

## Release gates

- [x] correct_subject_scoped_retrieval
- [x] cross_subject_leakage
- [x] verified_correction_adherence
- [x] superseded_memory_active_use
- [x] duplicate_ingestion
- [x] valid_evidence_ids
- [x] safe_action_accuracy
- [x] unsafe_output
- [x] retry_duplicate_action
- [x] trace_reproducibility

All records are deterministic and fabricated. No real medical document or identifiable person is represented.
