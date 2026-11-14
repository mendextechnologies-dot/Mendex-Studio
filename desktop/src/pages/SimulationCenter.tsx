import React from 'react';
import { SimulationJob } from '../api/types';
import { Activity, CheckCircle, XCircle, Clock } from 'lucide-react';

interface SimulationCenterProps {
  jobs: SimulationJob[];
}

export const SimulationCenter: React.FC<SimulationCenterProps> = ({ jobs }) => {
  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#172033' }}>
          Simulation Center & Batch Solver Jobs
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Recorded solver jobs. Execution status does not establish engineering validation; unattributed jobs are not revision evidence.
        </p>
      </div>

      <div className="card">
        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
              <th style={{ padding: '10px 12px' }}>Job ID</th>
              <th style={{ padding: '10px 12px' }}>Tool</th>
              <th style={{ padding: '10px 12px' }}>Operation</th>
              <th style={{ padding: '10px 12px' }}>Project</th>
              <th style={{ padding: '10px 12px' }}>Status</th>
              <th style={{ padding: '10px 12px' }}>Created At</th>
              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Exit Code</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '36px', marginBottom: '12px' }}>⚙️</div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#172033', marginBottom: '6px' }}>
                    No Headless Batch Solver Jobs Queued
                  </div>
                  <p style={{ fontSize: '12px', color: '#64748b', maxWidth: '480px', margin: '0 auto', lineHeight: '1.5' }}>
                    Simulation design files (such as <code>etd34_core.fem</code> for FEMM and <code>flyback_circuit.net</code> for LTspice) are currently edited and verified directly in their native engineering tools.
                  </p>
                  <p style={{ fontSize: '11px', color: '#94a3b8', maxWidth: '480px', margin: '8px auto 0' }}>
                    When headless background solver workflows or parametric sweeps are dispatched through the integration runner, their execution status, progress, stdout logs, and SHA-256 evidence digests will be tracked in this table.
                  </p>
                </td>
              </tr>
            )}
            {jobs.map((job) => (
              <tr key={job.job_id} style={{ borderBottom: '1px solid #f3f6fb' }}>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#1d4ed8' }}>
                  {job.job_id.substring(0, 8)}...
                </td>
                <td style={{ padding: '10px 12px', fontWeight: 700, color: '#172033' }}>
                  {job.tool_id.toUpperCase()}
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                  {job.operation}
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                  {job.project_name || 'Unattributed workspace'}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <span className={`badge ${job.status === 'SUCCEEDED' ? 'badge-green' : job.status === 'FAILED' ? 'badge-red' : 'badge-yellow'}`}>
                    {job.status}
                  </span>
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>
                  {new Date(job.created_at).toLocaleString()}
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, color: job.exit_code === 0 ? '#047857' : '#b91c1c' }}>
                  {job.exit_code ?? 'Unavailable'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
