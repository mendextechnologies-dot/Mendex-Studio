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
  cadPreview: (revisionId: string, kind: 'pcb' | 'schematic' | '3d' = 'pcb') =>
    rpcCall<any>('cad_preview', { revision_id: revisionId, kind }),
  autoRoutePCB: (
    revisionId: string,
    pourGround: boolean = true,
    powerTrack: number = 1.2,
    defaultTrack: number = 0.4
  ) =>
    rpcCall<any>('auto_route_pcb', {
      revision_id: revisionId,
      pour_ground: pourGround,
      power_track: powerTrack,
      default_track: defaultTrack,
    }),
  openEvidence: (recordId: string) => rpcCall<any>('open_evidence', { record_id: recordId }),
  openReport: (reportId: string) => rpcCall<any>('open_report', { report_id: reportId }),
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
};
