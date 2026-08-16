export type ImplementationPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;
export type DemoRole = "PATIENT" | "CLINICIAN" | "JUDGE";
export type Disposition = "USED" | "SUPPORTING" | "EXCLUDED";

export interface Me {
  id: string;
  tenant_id: string;
  role: DemoRole;
  display_name: string;
  demo_mode: boolean;
}

export interface SubjectSummary {
  id: string;
  pseudonym: string;
  year_of_birth: number | null;
  status: string;
  report_count: number;
  open_task_count: number;
  latest_scan_date: string | null;
}

export interface Measurement {
  id: string;
  report_id: string;
  skeletal_site: string;
  region: string;
  side: string | null;
  bmd_g_cm2: number;
  t_score: number;
  z_score: number | null;
  confidence: number;
  source_page: number;
  source_text: string;
  usable_for_longitudinal: boolean;
  verification_status: string;
}

export interface Report {
  id: string;
  document_id: string;
  scan_date: string;
  report_type: string;
  facility_pseudonym: string;
  scanner_manufacturer: string;
  scanner_model: string;
  parser_name: string;
  parser_version: string;
  extraction_confidence: number;
  review_required: boolean;
  measurements: Measurement[];
}

export interface MemoryTraceItem {
  id: string;
  title: string;
  content: string;
  source_type: string;
  source_label: string;
  verification_status: string;
  confidence: number;
  trust_score: number;
  disposition: Disposition;
  disposition_reason: string | null;
  created_at: string;
}

export interface ReviewTask {
  id: string;
  agent_run_id: string;
  action_type: string;
  status: string;
  title: string;
  proposed_payload: Record<string, unknown>;
  applied_payload: Record<string, unknown> | null;
  evidence_memory_ids: string[];
  requires_role: string;
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface Timeline {
  subject: SubjectSummary;
  reports: Report[];
  memories: MemoryTraceItem[];
  tasks: ReviewTask[];
  treatment_events: Array<Record<string, unknown>>;
}

export interface DocumentStatus {
  id: string;
  subject_id: string;
  status: string;
  original_filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  progress: number;
  status_message: string;
  report: Report | null;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
}

export interface DemoDataReset {
  subject_id: string;
  status: "CLEARED";
  database: string;
  deleted_records: Record<string, number>;
  replayed: boolean;
  reset_at: string;
}

export interface EvidenceReference {
  memory_id: string;
  source_type: string;
  source_id: string | null;
  role: "PRIMARY" | "SUPPORTING" | "EXCLUDED";
  exclusion_reason: string | null;
}

export interface AgentDecision {
  summary: string;
  uncertainty: string;
  safety_notice: string;
  evidence: EvidenceReference[];
  proposed_action: {
    action_type: string;
    title: string;
    rationale: string;
    payload: Record<string, unknown>;
    requires_human_approval: boolean;
  };
  memory_impact_statement: string;
  counterfactual_without_key_memory: string | null;
}

export interface AgentRun {
  id: string;
  subject_id: string;
  status: string;
  request_type: string;
  decision: AgentDecision;
  memory_trace: MemoryTraceItem[];
  review_task_id: string | null;
  created_at: string;
  persisted_review_applied: boolean;
}

export interface Transparency {
  mode: "LOCAL_MOCK" | "LOCAL_BEDROCK" | "LOCAL_CLOUD_MCP" | "AWS";
  database: Record<string, string>;
  document_pipeline: Array<Record<string, string>>;
  memory_engine: Array<Record<string, string>>;
  agent: Record<string, string>;
  audit_event_count: number;
  safety_boundary: string;
}

export interface DashboardSnapshot {
  timeline: Timeline;
  tasks: ReviewTask[];
  transparency: Transparency;
}
