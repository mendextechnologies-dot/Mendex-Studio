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
          Real open-source solver executions (LTspice transient, FEMM 4.2 magnetics, KiCad ERC/DRC).
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
                  {job.project_name || 'Generic Workspace'}
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
