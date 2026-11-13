import {
  HandshakeData,
  OverviewData,
  ProjectRecord,
  ProjectDetailData,
  SimulationJob,
  ToolRecord,
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
  components: () => rpcCall<any>('components'),
  tools: () => rpcCall<ToolRecord[]>('tools'),
  reports: () => rpcCall<any[]>('reports'),
  settings: () => rpcCall<any>('settings'),
  waveform: (revisionId: string, relativePath: string, traces?: string[]) =>
    rpcCall<any>('waveform', { revision_id: revisionId, relative_path: relativePath, traces }),
  openFile: (revisionId: string, relativePath: string) =>
    rpcCall<any>('open_file', { revision_id: revisionId, relative_path: relativePath }),
  openReport: (reportId: string) => rpcCall<any>('open_report', { report_id: reportId }),
  exportReport: (reportId: string) => rpcCall<any>('export_report', {
    report_id: reportId, idempotency_key: crypto.randomUUID(),
  }),
};
