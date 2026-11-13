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
  project_id?: string;
  project_name?: string;
  revision_id?: string;
  tool_id: string;
  operation: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  created_at: string;
  started_at?: string;
  ended_at?: string;
  exit_code?: number;
  progress: number;
  evidence_available: boolean;
  workspace_id: string;
  provenance: Record<string, any>;
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

export interface ComponentRecord {
  id: string;
  part_number: string;
  manufacturer: string;
  category: string;
  package_type: string;
  parameters: Record<string, any>;
}

export interface MaterialRecord {
  id: string;
  name: string;
  material_family: string;
  initial_permeability?: number;
  saturation_flux_density_t?: number;
  curie_temperature_c?: number;
}
