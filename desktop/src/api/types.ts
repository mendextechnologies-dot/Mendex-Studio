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

export interface ReleaseDeliverableItem {
  file: string;
  category: 'cad' | 'fabrication' | 'assembly' | 'bom' | 'testing_qa' | 'other';
  size_bytes: number;
  sha256: string;
}

export interface ReleasePackageData {
  status: 'READY' | 'PENDING_GENERATION';
  package_exists: boolean;
  product_code: string;
  product_name: string;
  revision_label: string;
  revision_id: string;
  package_filename: string | null;
  package_relative_path: string | null;
  package_size_bytes: number;
  package_sha256: string | null;
  generated_at: string | null;
  generator: string | null;
  contents: ReleaseDeliverableItem[];
  categories: Record<string, ReleaseDeliverableItem[]>;
  available_candidates_count: number;
  available_candidates?: Array<{
    name: string;
    relative_path: string;
    category: string;
    size_bytes: number;
  }>;
  governance_notice: string;
}


// ============================================================================
// OSCILLOSCOPE CSV INGESTION & REAL-VS-SIMULATED CORRELATION (OPTION 2)
// ============================================================================

export interface ScopeChannelMetrics {
  mean: number;
  rms: number;
  min: number;
  max: number;
  pk_pk: number;
  est_freq_hz: number;
  rise_time_s: number;
}

export interface ScopeMeasurementSummary {
  measurement_id: string;
  revision_id: string;
  original_filename: string;
  saved_filename?: string;
  relative_path: string;
  sha256: string;
  vendor: string;
  operator: string;
  test_name: string;
  procedure_reference: string;
  instrument_name: string;
  instrument_serial: string;
  calibration_reference: string;
  notes: string;
  timestamp: string;
  sample_rate_hz: number;
  duration_s: number;
  total_points: number;
  channels: string[];
  channel_metrics: Record<string, ScopeChannelMetrics>;
  channel_mapping?: Record<string, string>;
}

export interface ScopeWaveformData {
  measurement_id: string;
  filename: string;
  sha256: string;
  vendor: string;
  samples: Array<{ time: number; [key: string]: number }>;
  traces: string[];
  total_points: number;
  returned_points: number;
  sample_rate_hz: number;
  duration_s: number;
  channel_metrics: Record<string, ScopeChannelMetrics>;
  operator: string;
  timestamp: string;
  error?: string;
}

export interface ChannelCorrelation {
  channel: string;
  scope_channel: string;
  sim_trace: string;
  status: 'CORRELATED_PASS' | 'WARNING_DEVIATION' | 'EXCEEDED_TOLERANCE' | 'UNAVAILABLE';
  status_description: string;
  dc_simulated: number;
  dc_measured: number;
  dc_delta_abs: number;
  dc_error_percent: number;
  ripple_simulated_pk_pk: number;
  ripple_measured_pk_pk: number;
  ripple_delta_abs: number;
  peak_simulated: number;
  peak_measured: number;
  peak_delta_abs: number;
  frequency_simulated_hz: number | null;
  frequency_measured_hz: number | null;
  frequency_delta_hz: number | null;
  pearson_r: number;
  r_squared: number;
}

export interface ScopeCorrelationReport {
  status: 'CORRELATED_PASS' | 'WARNING_DEVIATION' | 'EXCEEDED_TOLERANCE' | 'NOT_EVALUATED' | 'UNAVAILABLE';
  measurement_id: string;
  original_filename: string;
  sim_relative_path: string;
  operator: string;
  channel_mapping: Record<string, string>;
  channels_evaluated: number;
  average_r_squared: number;
  average_dc_error_percent: number;
  channel_correlations: ChannelCorrelation[];
  measurement_sha256: string;
  vendor: string;
  total_measured_points: number;
  sampling_rate_hz: number;
  reason?: string;
}

// ============================================================================
// WORST-CASE & MONTE CARLO TOLERANCE ANALYSIS (OPTION 3)
// ============================================================================

export interface WccaStatistics {
  mean_v: number;
  std_dev_v: number;
  median_v: number;
  min_v: number;
  max_v: number;
  three_sigma_lower_v: number;
  three_sigma_upper_v: number;
  cp: number;
  cpk: number;
  statistical_yield_percent: number;
}

export interface WccaHistogramBin {
  bin_start: number;
  bin_end: number;
  bin_center: number;
  count: number;
  frequency: number;
}

export interface WccaEvaCorner {
  corner_name: string;
  condition: string;
  vout_v: number;
  vsw_peak_v: number;
  ripple_mv: number;
  margin_status: string;
}

export interface WccaSensitivity {
  component: string;
  parameter: string;
  tolerance_pct: number;
  sensitivity_pct: number;
}

export interface WccaMonteCarloRun {
  iteration: number;
  vout_v: number;
  ripple_mv: number;
  vsw_peak_v: number;
  temperature_c: number;
  vin_v: number;
}

export interface WccaAnalysisReport {
  success: boolean;
  revision_id: string;
  distribution: string;
  num_iterations: number;
  overall_readiness: 'PRODUCTION_READY' | 'MARGINAL_REQUIRES_TRIMMING';
  specification_limits: {
    vout_nominal_v: number;
    lsl_vout_v: number;
    usl_vout_v: number;
    tolerance_percent: number;
    ripple_limit_mv: number;
  };
  statistics: WccaStatistics;
  histogram_bins: WccaHistogramBin[];
  eva_corners: WccaEvaCorner[];
  sensitivities: WccaSensitivity[];
  monte_carlo_runs: WccaMonteCarloRun[];
  report_sha256?: string;
}
