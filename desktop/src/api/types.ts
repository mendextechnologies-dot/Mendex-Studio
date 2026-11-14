export interface ProjectRecord {
  product_id: string;
  code: string;
  name: string;
  category: string;
  owner: string;
  description: string;
  active_revision_id: string;
  revision_label: string;
  revision_status: string;
  input_hash: string;
  created_at: string;
}

export interface SimulationJob {
  job_id: string;
  project_id?: string | null;
  project_name?: string | null;
  revision_id?: string | null;
  tool_id: string;
  operation: string;
  status: 'QUEUED' | 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED' | 'TIMED_OUT' | 'NOT_SUPPORTED';
  stale?: boolean | null;
  created_at: string;
  started_at?: string | null;
  ended_at?: string | null;
  exit_code?: number | null;
  progress: number;
  evidence_available: boolean;
  workspace_id: string;
  provenance: Record<string, any> | string;
  engineering_status: string;
}

export interface OverviewMetrics {
  projects: number;
  revisions: number;
  completed_simulations: number;
  failed_simulations: number;
  review_requests: number;
}

export interface OverviewData {
  projects: ProjectRecord[];
  jobs: SimulationJob[];
  activity: Array<{
    id: string;
    kind: string;
    title: string;
    detail: string;
    timestamp: string;
  }>;
  metrics: OverviewMetrics;
  timestamp: string;
}

export interface HandshakeData {
  protocol_version: string;
  status: string;
  data_root: string;
  python_version: string;
  application: string;
  desktop_version: string;
  engineering_status: string;
  timestamp: string;
}

export interface StageDefinition {
  id: string;
  name: string;
  purpose: string;
  dependencies: string[];
  review_required: boolean;
  optional: boolean;
}

export interface LifecycleStageView {
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'AWAITING_REVIEW' | 'NOT_APPLICABLE';
  attempt: number;
  input_hash: string;
  evidence_record_ids: string[];
  last_activity: string;
  reason: string;
  review_status: string;
  definition: StageDefinition;
  effective_status: string;
  stale: boolean;
  criteria: Array<{
    id: string;
    description: string;
    status: string;
    satisfied: boolean;
  }>;
  blockers: string[];
  review?: any;
}

export interface ProjectDetailData {
  product: ProjectRecord;
  revision: {
    revision_id: string;
    product_id: string;
    revision_label: string;
    lifecycle_status: string;
    created_at: string;
    specification: Record<string, any>;
    specification_hash?: string;
  };
  revisions: Array<{
    revision_id: string;
    revision_label: string;
    lifecycle_status: string;
    created_at: string;
  }>;
  input_hash: string;
  lifecycle: {
    stages: LifecycleStageView[];
    engineering_status: string;
    approval_status: string;
  };
  designs: any[];
  calculations: any[];
  requirements: any[];
  registered_artifacts: any[];
  files: Array<{
    relative_path: string;
    name: string;
    extension: string;
    size_bytes: number;
    modified_ns: number;
  }>;
  simulations: SimulationJob[];
  validation: any[];
  reports: any[];
  measurements: any[];
}

export interface ToolRecord {
  descriptor: {
    tool_id: string;
    name: string;
    category: string;
    description: string;
  };
  health: {
    state: string;
    installed_path?: string;
    executable_path?: string;
    version?: string;
    diagnostic?: string;
  };
  configured: boolean;
  qualification: string;
}

export interface LibraryReference {
  id: string;
  datasheet_url: string | null;
  source_checked_on: string | null;
  verification_status: string;
  provenance: string;
  conditions: string;
  lifecycle_status: string;
}

export interface ComponentRecord extends LibraryReference {
  mpn: string;
  manufacturer: string;
  category: string;
  description: string;
  package: string | null;
  record_kind: 'PART' | 'FAMILY';
  voltage_rating_v: number | null;
  current_rating_a: number | null;
  power_rating_w: number | null;
  rds_on_ohm: number | null;
  esr_ohm: number | null;
  kicad_footprint: string | null;
  kicad_symbol: string | null;
  spice_model_name: string | null;
}

export interface MaterialRecord extends LibraryReference {
  name: string;
  manufacturer: string;
  material_type: string;
  initial_permeability_ui: number | null;
  saturation_flux_t: number | null;
  curie_temp_c: number | null;
  curie_temp_qualifier: string;
  freq_min_hz: number | null;
  freq_max_hz: number | null;
}

export interface MagneticCoreRecord extends LibraryReference {
  name: string;
  geometry_type: string;
  manufacturer: string;
  ae_mm2: number | null;
  le_mm: number | null;
  ve_mm3: number | null;
}

export interface LibraryCatalog {
  categories: Array<{id: string; label: string}>;
  components: ComponentRecord[];
  materials: MaterialRecord[];
  cores: MagneticCoreRecord[];
  provenance_note: string;
}


export interface BOMGenerationResult {
  success: boolean;
  docx_path: string;
  pdf_path: string;
  csv_path: string;
  json_path: string;
  pdf_available: boolean;
  items_count: number;
  docx_size_bytes: number;
  pdf_size_bytes: number;
  message: string;
}
