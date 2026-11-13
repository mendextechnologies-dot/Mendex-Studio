import React from 'react';
import { OverviewData } from '../api/types';
import { FolderGit2, Activity, ShieldCheck, Clock, ArrowRight } from 'lucide-react';

interface DashboardProps {
  data: OverviewData | null;
  onSelectProject: (projectId: string) => void;
  onNavigateToSimulations: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  data,
  onSelectProject,
  onNavigateToSimulations,
}) => {
  if (!data) {
    return <div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading engineering dashboard...</div>;
  }

  const { metrics, projects, jobs, activity } = data;

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {/* 1. Metric Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <span>AUTHORITATIVE PROJECTS</span>
            <FolderGit2 size={16} color="#60a5fa" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '8px', color: '#f8fafc' }}>
            {metrics.projects}
          </div>
          <div style={{ fontSize: '11px', color: '#38bdf8', marginTop: '4px' }}>
            {metrics.revisions} total recorded revisions
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <span>COMPLETED SIMULATIONS</span>
            <Activity size={16} color="#34d399" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '8px', color: '#34d399' }}>
            {metrics.completed_simulations}
          </div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            LTspice & FEMM headless batch jobs
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <span>FAILED RUNS</span>
            <Activity size={16} color="#f87171" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '8px', color: metrics.failed_simulations > 0 ? '#f87171' : '#94a3b8' }}>
            {metrics.failed_simulations}
          </div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            Recorded failed execution statuses
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <span>PENDING REVIEWS</span>
            <Clock size={16} color="#fbbf24" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '8px', color: '#fbbf24' }}>
            {metrics.review_requests}
          </div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
            Human-in-the-loop gate decisions
          </div>
        </div>
      </div>

      {/* 2. Main Content Split: Projects Table & Recent Simulations */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* Left: Active Projects */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
              Authoritative Engineering Projects ({projects.length})
            </h2>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              Source: Local SQLite
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                  <th style={{ padding: '8px 12px' }}>Code</th>
                  <th style={{ padding: '8px 12px' }}>Project Name</th>
                  <th style={{ padding: '8px 12px' }}>Active Rev</th>
                  <th style={{ padding: '8px 12px' }}>Status</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((proj) => (
                  <tr
                    key={proj.product_id}
                    style={{ borderBottom: '1px solid #1f2436', cursor: 'pointer' }}
                    onClick={() => onSelectProject(proj.product_id)}
                  >
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: '#60a5fa' }}>
                      {proj.code}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>
                      {proj.name}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                      {proj.revision_label}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className={`badge ${proj.revision_status === 'PASSED' ? 'badge-green' : 'badge-blue'}`}>
                        {proj.revision_status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }}>
                        <span>Open</span>
                        <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Recent Simulation Jobs */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
              Recent Simulations
            </h2>
            <button
              onClick={onNavigateToSimulations}
              style={{ background: 'none', border: 'none', color: '#60a5fa', fontSize: '11px', fontWeight: 600, cursor: 'pointer' }}
            >
              View All
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {jobs.slice(0, 6).map((job) => (
              <div
                key={job.job_id}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#121522',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '12px', color: '#e2e8f0' }}>
                    {job.tool_id.toUpperCase()} · {job.operation}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                    {job.project_name || 'Generic Workspace'}
                  </div>
                </div>
                <div>
                  <span className={`badge ${job.status === 'SUCCEEDED' ? 'badge-green' : job.status === 'FAILED' ? 'badge-red' : 'badge-yellow'}`}>
                    {job.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
