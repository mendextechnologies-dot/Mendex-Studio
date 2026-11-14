import {
  HandshakeData,
  OverviewData,
  ProjectRecord,
  ProjectDetailData,
  SimulationJob,
  ToolRecord,
  LibraryCatalog,
  BOMGenerationResult,
} from './types';

let requestId = 0;

export async function rpcCall<T = any>(method: string, params: Record<string, any> = {}): Promise<T> {
  const id = `req-${++requestId}-${Date.now()}`;
  const payload = {
    protocol_version: '3.1.0',
    id,
    method,
    params,
  };

  let data: any;
  const native = (window as any).__TAURI__?.core?.invoke;
  if (native) {
    data = JSON.parse(await native('rpc_dispatch', { request: JSON.stringify(payload) }));
  } else {
    if (!['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
      throw new Error('Desktop bridge is unavailable');
    }
    const response = await fetch('/api/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`RPC transport error (${response.status}): ${errorText}`);
    }

    data = await response.json();
  }
  if (data.id !== id || data.protocol_version !== '3.1.0') {
    throw new Error('Desktop bridge response identity or protocol mismatch');
  }
  if (data.error) {
    throw new Error(`RPC error [${data.error.code}]: ${data.error.message}`);
  }

  return data.result as T;
}

export const api = {
  handshake: () => rpcCall<HandshakeData>('handshake'),
  overview: () => rpcCall<OverviewData>('overview'),
  projects: () => rpcCall<ProjectRecord[]>('projects'),
  project: (projectId: string, revisionId?: string) =>
    rpcCall<ProjectDetailData>('project', { project_id: projectId, revision_id: revisionId }),
  simulations: () => rpcCall<SimulationJob[]>('simulations'),
  components: () => rpcCall<LibraryCatalog>('components'),
  tools: () => rpcCall<ToolRecord[]>('tools'),
  reports: () => rpcCall<any[]>('reports'),
  settings: () => rpcCall<any>('settings'),
  waveform: (revisionId: string, relativePath: string, traces?: string[]) =>
    rpcCall<any>('waveform', { revision_id: revisionId, relative_path: relativePath, traces }),
  openFile: (revisionId: string, relativePath: string) =>
    rpcCall<any>('open_file', { revision_id: revisionId, relative_path: relativePath }),
  revealFile: (revisionId: string, relativePath: string) =>
    rpcCall<any>('reveal_file', { revision_id: revisionId, relative_path: relativePath }),
  generateBom: (revisionId: string) =>
    rpcCall<BOMGenerationResult>('generate_bom', { revision_id: revisionId }),
  cadPreview: (
    revisionId: string,
    kind: 'pcb' | 'schematic' | '3d' = 'pcb',
    view: 'iso' | 'top' | 'bottom' | 'iso_bottom' = 'iso'
  ) =>
    rpcCall<any>('cad_preview', { revision_id: revisionId, kind, view }),
  autoRoutePCB: (
    revisionId: string,
    pourGround: boolean = true,
    powerTrack: number = 1.2,
    defaultTrack: number = 0.4,
    thermalSpoke: number = 0.5,
    thermalGap: number = 0.5,
    padConnection: 'tht_thermal' | 'thermal' | 'solid' | 'none' = 'tht_thermal',
    stitchGround: boolean = false,
    stitchPitch: number = 5.0,
    zoneClearance: number = 0.5
  ) =>
    rpcCall<any>('auto_route_pcb', {
      revision_id: revisionId,
      pour_ground: pourGround,
      power_track: powerTrack,
      default_track: defaultTrack,
      thermal_spoke: thermalSpoke,
      thermal_gap: thermalGap,
      pad_connection: padConnection,
      stitch_ground: stitchGround,
      stitch_pitch: stitchPitch,
      zone_clearance: zoneClearance,
    }),
  millIsolationSlot: (
    revisionId: string,
    slotWidth: number = 2.5,
    slotLength?: number
  ) =>
    rpcCall<any>('mill_isolation_slot', {
      revision_id: revisionId,
      slot_width: slotWidth,
      slot_length: slotLength,
    }),
  setup4LayerPlanes: (params: {
    revision_id: string;
    gnd_net?: string;
    pwr_net?: string;
    zone_clearance?: number;
    thermal_spoke?: number;
    pad_connection?: string;
  }) =>
    rpcCall<{
      success: boolean;
      pcb_path: string;
      in1_gnd_poured: boolean;
      in2_pwr_poured: boolean;
      gnd_net: string;
      pwr_net: string;
      layers: string[];
      messages: string[];
      drc?: any;
      error?: string;
    }>('setup_4layer_planes', params),
  exportGerbers: (revisionId: string, autoRoute: boolean = true) =>
    rpcCall<any>('export_gerbers', { revision_id: revisionId, auto_route: autoRoute }),
  downloadGerbers: (revisionId: string) =>
    rpcCall<{
      success: boolean;
      filename: string;
      relative_path: string;
      sha256: string;
      size_bytes: number;
      data_uri: string;
      error?: string;
    }>('download_gerbers', { revision_id: revisionId }),
  inspectGerberLayers: (revisionId: string, autoExport: boolean = true) =>
    rpcCall<{
      success: boolean;
      board_name: string;
      filename: string;
      layer_count: number;
      is_4layer: boolean;
      bbox: { min_x: number; min_y: number; max_x: number; max_y: number; width: number; height: number };
      layers: Array<{
        layer_id: string;
        name: string;
        filename: string;
        file_size_bytes: number;
        sha256: string;
        color_hex: string;
        is_copper: boolean;
        is_drill: boolean;
        available: boolean;
      }>;
      drill_tools: Array<{
        tool_id: string;
        diameter_mm: number;
        diameter_mils: number;
        count: number;
        pth_count: number;
        npth_count: number;
        plated: boolean;
        usage: string;
      }>;
      drill_summary: {
        total_holes: number;
        pth_count: number;
        npth_count: number;
        tool_count: number;
      };
      drill_hits: Array<{
        x: number;
        y: number;
        tool_id: string;
        diameter: number;
        plated: boolean;
        pad_number?: string;
        ref?: string;
        type?: string;
      }>;
      edge_cuts: any[];
      tracks: any[];
      footprints: any[];
      zones: any[];
      has_gerber_zip: boolean;
      gerber_zip_filename?: string;
      gerber_zip_bytes?: number;
      gerber_zip_sha256?: string;
      gerber_zip_path?: string;
      error?: string;
    }>('inspect_gerber_layers', { revision_id: revisionId, auto_export: autoExport }),
  exportCADStep: (revisionId: string, openNative: boolean = false) =>
    rpcCall<any>('export_cad_step', { revision_id: revisionId, open_native: openNative }),
  render3D: (
    revisionId: string,
    view: 'iso' | 'top' | 'bottom' | 'iso_bottom' = 'iso',
    width: number = 1400,
    height: number = 1050
  ) =>
    rpcCall<any>('render_3d_pcb', {
      revision_id: revisionId,
      view,
      width,
      height,
    }),
  applySchematic: (revisionId: string, ops: any[], verify: boolean = true) =>
    rpcCall<any>('apply_schematic', { revision_id: revisionId, ops, verify }),
  openEvidence: (recordId: string) => rpcCall<any>('open_evidence', { record_id: recordId }),
  getEvidence: (recordId: string) => rpcCall<any>('get_evidence', { record_id: recordId }),
  generateReport: (revisionId: string) => rpcCall<any>('generate_report', { revision_id: revisionId }),
  openReport: (reportId: string, format: 'html' | 'pdf' = 'html') =>
    rpcCall<any>('open_report', { report_id: reportId, format }),
  getReport: (reportId: string) => rpcCall<any>('get_report', { report_id: reportId }),
  exportReport: (reportId: string) => rpcCall<any>('export_report', {
    report_id: reportId, idempotency_key: crypto.randomUUID(),
  }),
  listReviewers: () => rpcCall<any[]>('list_reviewers'),
  reviewPackage: (revisionId: string, stageId: string = 'requirements') =>
    rpcCall<any>('review_package', { revision_id: revisionId, stage_id: stageId }),
  requestReview: (revisionId: string, submitter: string, reason: string, stageId: string = 'requirements') =>
    rpcCall<any>('request_review', {
      revision_id: revisionId,
      stage_id: stageId,
      submitter,
      reason,
      idempotency_key: crypto.randomUUID(),
    }),
  submitReview: (params: {
    revision_id: string;
    stage_id: string;
    attempt: number;
    decision: 'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED';
    reviewer_name: string;
    expected_document_hashes: Record<string, string>;
    expected_evidence_hashes: Record<string, string>;
    comments: string;
    conflicts?: any[];
    deferrals?: any[];
    expected_requirements_digest: string;
    expected_specification_hash: string;
    idempotency_key: string;
  }) => rpcCall<any>('submit_review', params),
  completeStage: (revisionId: string, stageId: string) =>
    rpcCall<any>('complete_stage', { revision_id: revisionId, stage_id: stageId }),
  listECRs: (params?: { workspace_id?: string; product_id?: string; revision_id?: string }) =>
    rpcCall<any[]>('list_ecrs', params || {}),
  createECR: (params: {
    title: string;
    description: string;
    reason: string;
    impact_analysis: string;
    requested_by: string;
    affected_stages?: string[];
    workspace_id?: string;
    product_id?: string;
    revision_id?: string;
    schematic_ops?: any[];
  }) => rpcCall<any>('create_ecr', params),
  reviewECR: (params: {
    ecr_id: string;
    reviewer: string;
    status: 'APPROVED' | 'REJECTED' | 'UNDER_REVIEW' | 'DRAFT';
    review_notes?: string;
  }) => rpcCall<any>('review_ecr', params),
  applyECRSchematic: (ecrId: string, implementedBy?: string, forwardAnnotate: boolean = true) =>
    rpcCall<any>('apply_ecr_schematic', { ecr_id: ecrId, implemented_by: implementedBy, forward_annotate: forwardAnnotate }),
  forwardAnnotatePcb: (params: {
    revision_id: string;
    ecr_id?: string;
    remove_extra?: boolean;
    auto_place_new?: boolean;
    refill_zones?: boolean;
  }) => rpcCall<any>('forward_annotate_pcb', params),
  synthesizeTopologies: (revisionId: string) =>
    rpcCall<{
      success: boolean;
      design_id: string;
      revision_id: string;
      candidates: any[];
      count: number;
    }>('synthesize_topologies', { revision_id: revisionId }),
  selectCandidate: (
    revisionId: string,
    candidateId: string,
    autoExportKiCad: boolean = true
  ) =>
    rpcCall<{
      success: boolean;
      selected_candidate_id: string;
      selected_topology: string;
      name: string;
      kicad_exported: boolean;
      kicad_details?: any;
    }>('select_candidate', {
      revision_id: revisionId,
      candidate_id: candidateId,
      auto_export_kicad: autoExportKiCad,
    }),
  calculateThermalSizing: (params: {
    revision_id: string;
    ambient_temp_c?: number;
    p_switch_loss_w?: number;
    r_th_jc_c_w?: number;
    r_th_cs_c_w?: number;
    r_th_sa_c_w?: number;
    t_j_max_c?: number;
    derating_factor?: number;
    transformer_surface_area_cm2?: number;
    trace_current_a?: number;
    target_trace_delta_t_c?: number;
    copper_thickness_oz?: number;
    is_internal_trace?: boolean;
    record_evidence?: boolean;
  }) =>
    rpcCall<{
      success: boolean;
      revision_id: string;
      topology: string;
      ambient_temp_c: number;
      total_converter_loss_w: number;
      semiconductor: any;
      secondary_diode: any;
      magnetics: any;
      ipc2152_trace: any;
      summary: {
        max_temperature_c: number;
        min_thermal_margin_c: number;
        cooling_strategy: string;
        compliance_status: string;
        heatsink_rth_sa_required_c_w: number;
        pcb_copper_area_req_cm2: number;
        thermal_vias_count: number;
      };
      record_id?: string | null;
    }>('calculate_thermal_sizing', params),
  getOperationReceipt: (params: {
    operation_id?: string;
    idempotency_key?: string;
    revision_id?: string;
  }) =>
    rpcCall<{
      found: boolean;
      receipt?: {
        operation_id: string;
        operation_type: string;
        revision_id?: string;
        status: string;
        idempotency_key?: string;
        created_at: string;
      };
      cached_response?: any;
      error?: string;
    }>('get_operation_receipt', params),
  generateTestPlan: (revisionId: string) =>
    rpcCall<{
      success: boolean;
      protocol_id: string;
      revision_id: string;
      safety_category: string;
      is_high_voltage: boolean;
      json_path: string;
      markdown_path: string;
      html_path: string;
      sha256: string;
      markdown_content: string;
      html_content: string;
      test_plan: any;
    }>('generate_test_plan', { revision_id: revisionId }),
  getTestPlan: (revisionId: string) =>
    rpcCall<{
      success: boolean;
      protocol_id: string;
      revision_id: string;
      safety_category: string;
      is_high_voltage: boolean;
      json_path: string;
      markdown_path: string;
      html_path: string;
      sha256: string;
      markdown_content: string;
      html_content: string;
      test_plan: any;
    }>('get_test_plan', { revision_id: revisionId }),
  generateBOMPricing: (revisionId: string, currency: string = 'USD') =>
    rpcCall<{
      success: boolean;
      revision_id: string;
      product_code: string;
      product_name: string;
      currency: string;
      total_line_items: number;
      total_components: number;
      summary: {
        board_cost_1: number;
        board_cost_25: number;
        board_cost_100: number;
        board_cost_1000: number;
        volume_savings_pct: number;
        batch_cost_1: number;
        batch_cost_25: number;
        batch_cost_100: number;
        batch_cost_1000: number;
      };
      top_cost_drivers: Array<{
        rank: number;
        designator: string;
        mpn: string;
        description: string;
        category: string;
        cost_1000: number;
        share_pct: number;
        cumulative_share_pct: number;
      }>;
      category_breakdown: Array<{
        category: string;
        item_count: number;
        total_cost_1: number;
        total_cost_1000: number;
        pct_of_total: number;
      }>;
      items: Array<any>;
      csv_path: string;
      json_path: string;
      markdown_path: string;
      html_path: string;
      sha256: string;
      disclaimer: string;
    }>('generate_bom_pricing', { revision_id: revisionId, currency }),
  getBOMPricing: (revisionId: string) =>
    rpcCall<{
      success: boolean;
      revision_id: string;
      product_code: string;
      product_name: string;
      currency: string;
      total_line_items: number;
      total_components: number;
      summary: {
        board_cost_1: number;
        board_cost_25: number;
        board_cost_100: number;
        board_cost_1000: number;
        volume_savings_pct: number;
        batch_cost_1: number;
        batch_cost_25: number;
        batch_cost_100: number;
        batch_cost_1000: number;
      };
      top_cost_drivers: Array<{
        rank: number;
        designator: string;
        mpn: string;
        description: string;
        category: string;
        cost_1000: number;
        share_pct: number;
        cumulative_share_pct: number;
      }>;
      category_breakdown: Array<{
        category: string;
        item_count: number;
        total_cost_1: number;
        total_cost_1000: number;
        pct_of_total: number;
      }>;
      items: Array<any>;
      csv_path: string;
      json_path: string;
      markdown_path: string;
      html_path: string;
      sha256: string;
      disclaimer: string;
    }>('get_bom_pricing', { revision_id: revisionId }),
};
