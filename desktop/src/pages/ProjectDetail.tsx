import React, { useCallback, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import {
  ArrowLeft,
  LayoutDashboard,
  Activity,
  Sliders,
  Calculator,
  Play,
  Layers,
  FileText,
  ShieldCheck,
  History,
  FileBarChart,
  ExternalLink,
  Download,
  AlertCircle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Folder,
  FileCode,
  Tag,
  User,
  GitCommit,
  Calendar,
  ChevronRight,
  Info,
  Check,
  X,
  Cpu,
  RefreshCw,
  Box,
} from 'lucide-react';

const TAB_DEFS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'lifecycle', label: 'Lifecycle', icon: Activity },
  { id: 'specifications', label: 'Specifications', icon: Sliders },
  { id: 'calculations', label: 'Calculations', icon: Calculator },
  { id: 'simulations', label: 'Simulations', icon: Play },
  { id: 'designs', label: 'Designs', icon: Layers },
  { id: 'files', label: 'Revision Files', icon: FileText },
  { id: 'validation', label: 'Validation', icon: ShieldCheck },
  { id: 'revisions', label: 'Revisions', icon: History },
  { id: 'reports', label: 'Reports', icon: FileBarChart },
] as const;

type TabId = typeof TAB_DEFS[number]['id'];

const Json = ({ value }: { value: unknown }) => (
  <pre
    style={{
      whiteSpace: 'pre-wrap',
      overflowWrap: 'anywhere',
      backgroundColor: '#0c0e18',
      padding: '12px',
      borderRadius: '6px',
      border: '1px solid var(--border)',
      color: '#cbd5e1',
      fontSize: '11px',
      fontFamily: 'monospace',
      lineHeight: '1.45',
      maxHeight: '340px',
      overflowY: 'auto',
    }}
  >
    {JSON.stringify(value, null, 2)}
  </pre>
);

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export const ProjectDetail = ({ projectId, onBack }: { projectId: string; onBack: () => void }) => {
  const load = useCallback(() => api.project(projectId), [projectId]);
  const { data, error } = usePolling(load);
  const [tab, setTab] = useState<TabId>(() => {
    const param = new URLSearchParams(location.search).get('tab') as TabId;
    return TAB_DEFS.some((t) => t.id === param) ? param : 'overview';
  });
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  const [showRawJson, setShowRawJson] = useState(false);

  const action = async (call: () => Promise<unknown>) => {
    try {
      setActionError('');
      const result = await call();
      setMessage(typeof result === 'string' ? result : 'Operation succeeded.');
      setTimeout(() => setMessage(''), 4000);
    } catch (e) {
      setActionError(String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
      {/* 1. Sleek Navigation Breadcrumb Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={onBack}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
          >
            <ArrowLeft size={14} /> Back to projects
          </button>
          <span style={{ color: 'var(--border)', margin: '0 2px' }}>/</span>
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Engineering Projects</span>
          <ChevronRight size={12} color="var(--text-dim)" />
          <span style={{ fontSize: '12px', color: '#93c5fd', fontWeight: 700 }}>
            {data ? data.product.code : 'Project'}
          </span>
        </div>

        {data && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span className={`badge ${data.product.revision_status === 'PASSED' ? 'badge-green' : 'badge-blue'}`}>
              Revision: {data.revision.revision_label}
            </span>
            <span className="badge badge-yellow">
              Engineering: {data.lifecycle.engineering_status}
            </span>
            <span className="badge badge-muted">
              Approval: {data.lifecycle.approval_status}
            </span>
          </div>
        )}
      </div>

      {error && <p role="alert" style={{ color: '#f87171', fontSize: '12px' }}>{error}. Displayed records may be stale.</p>}

      {!data ? (
        <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin" style={{ marginBottom: '12px', color: '#60a5fa' }} />
          <p>{error ? 'Project unavailable' : 'Loading project baseline & engineering records…'}</p>
        </div>
      ) : (
        <>
          {/* 2. Project Hero Card */}
          <div
            className="card"
            style={{
              padding: '20px',
              background: 'linear-gradient(180deg, #181c2e 0%, #131622 100%)',
              border: '1px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                <div
                  style={{
                    width: '46px',
                    height: '46px',
                    borderRadius: '8px',
                    background: 'rgba(59, 130, 246, 0.15)',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#60a5fa',
                    fontWeight: 800,
                    fontSize: '16px',
                    flexShrink: 0,
                  }}
                >
                  {data.product.code.split('-')[0] || 'PRJ'}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.3px' }}>
                      {data.product.code} — {data.product.name}
                    </h2>
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: 'rgba(16, 185, 129, 0.1)',
                        color: '#34d399',
                        fontWeight: 600,
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                      }}
                    >
                      {data.product.category.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', maxWidth: '850px', lineHeight: 1.5 }}>
                    {data.product.description || 'High-Voltage power conversion baseline registered in SQLite repository.'}
                  </p>
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                gap: '20px',
                marginTop: '16px',
                paddingTop: '12px',
                borderTop: '1px solid rgba(255,255,255,0.06)',
                fontSize: '12px',
                color: 'var(--text-dim)',
                flexWrap: 'wrap',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <User size={13} color="var(--text-dim)" /> Owner: <strong style={{ color: '#cbd5e1' }}>{data.product.owner}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Calendar size={13} color="var(--text-dim)" /> Created:{' '}
                <strong style={{ color: '#cbd5e1' }}>
                  {data.product.created_at ? new Date(data.product.created_at).toLocaleDateString() : 'N/A'}
                </strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <GitCommit size={13} color="var(--text-dim)" /> Active Revision:{' '}
                <strong style={{ color: '#cbd5e1' }}>{data.revision.revision_label}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Folder size={13} color="var(--text-dim)" /> Files:{' '}
                <strong style={{ color: '#cbd5e1' }}>{data.files.length}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Activity size={13} color="var(--text-dim)" /> Lifecycle Stages:{' '}
                <strong style={{ color: '#cbd5e1' }}>{data.lifecycle.stages.length}</strong>
              </span>
            </div>
          </div>

          {/* Action Alerts / Feedback */}
          {actionError && (
            <div
              role="alert"
              style={{
                padding: '10px 14px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '6px',
                color: '#f87171',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={15} />
              <span>{actionError}</span>
            </div>
          )}
          {message && (
            <div
              role="status"
              style={{
                padding: '10px 14px',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '6px',
                color: '#34d399',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={15} />
              <span>{message}</span>
            </div>
          )}

          {/* 3. Modern Styled Tabs Strip */}
          <nav
            style={{
              display: 'flex',
              gap: '4px',
              background: '#121522',
              padding: '6px 8px 0 8px',
              borderRadius: '8px 8px 0 0',
              border: '1px solid var(--border)',
              borderBottom: 'none',
              overflowX: 'auto',
              scrollbarWidth: 'none',
            }}
          >
            {TAB_DEFS.map((t) => {
              const Icon = t.icon;
              const isActive = tab === t.id;
              let count: number | null = null;
              if (t.id === 'files') count = data.files.length;
              if (t.id === 'lifecycle') count = data.lifecycle.stages.length;
              if (t.id === 'simulations') count = data.simulations.length;
              if (t.id === 'reports') count = data.reports.length;

              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  aria-pressed={isActive}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '7px',
                    padding: '9px 14px',
                    fontSize: '12px',
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? '#38bdf8' : 'var(--text-muted)',
                    backgroundColor: isActive ? 'var(--bg-card)' : 'transparent',
                    border: '1px solid',
                    borderColor: isActive ? 'var(--border)' : 'transparent',
                    borderBottomColor: isActive ? 'var(--bg-card)' : 'transparent',
                    borderRadius: '6px 6px 0 0',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.12s ease',
                    marginBottom: isActive ? '-1px' : '0',
                    zIndex: isActive ? 2 : 1,
                  }}
                >
                  <Icon size={14} color={isActive ? '#38bdf8' : 'var(--text-dim)'} />
                  <span>{t.id}</span>
                  {count !== null && (
                    <span
                      style={{
                        fontSize: '10px',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        backgroundColor: isActive ? 'rgba(56, 189, 248, 0.15)' : '#1e2235',
                        color: isActive ? '#38bdf8' : 'var(--text-dim)',
                        fontWeight: 600,
                      }}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* 4. Tab Content Body Card */}
          <section
            className="card"
            style={{
              borderRadius: '0 0 8px 8px',
              borderTop: '1px solid var(--border)',
              padding: '24px',
              minHeight: '420px',
            }}
          >
            {/* TAB 1: OVERVIEW */}
            {tab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Recorded project
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Primary immutable repository entity and active baseline parameters.
                  </p>
                </div>

                {/* 4-KPI Overview Row */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '14px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Enrolled Stages
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                      {data.lifecycle.stages.filter((s) => s.status === 'COMPLETED').length} / {data.lifecycle.stages.length}
                    </div>
                    <div style={{ fontSize: '11px', color: '#60a5fa', marginTop: '2px' }}>
                      Lifecycle Active
                    </div>
                  </div>

                  <div style={{ padding: '14px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Revision Files
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                      {data.files.length}
                    </div>
                    <div style={{ fontSize: '11px', color: '#34d399', marginTop: '2px' }}>
                      Workspace Monitored
                    </div>
                  </div>

                  <div style={{ padding: '14px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Simulations & Evidence
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                      {data.simulations.length}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Solvers Qualified
                    </div>
                  </div>

                  <div style={{ padding: '14px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Engineering Audit
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#fbbf24', marginTop: '8px' }}>
                      {data.lifecycle.engineering_status}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                      Approval: {data.lifecycle.approval_status}
                    </div>
                  </div>
                </div>

                {/* Two Column Project Baseline Info */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Box size={14} color="#60a5fa" /> Product Definition & Provenance
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Product ID:</span>
                        <span style={{ fontFamily: 'monospace', color: '#f8fafc' }}>{data.product.product_id}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Project Code:</span>
                        <span style={{ fontWeight: 600, color: '#60a5fa' }}>{data.product.code}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Category:</span>
                        <span style={{ color: '#cbd5e1' }}>{data.product.category}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Lead Engineer:</span>
                        <span style={{ color: '#cbd5e1' }}>{data.product.owner}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Active Revision:</span>
                        <span style={{ fontWeight: 600, color: '#34d399' }}>{data.revision.revision_label}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <GitCommit size={14} color="#34d399" /> Active Baseline & Hash Integrity
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Revision UUID:</span>
                        <span style={{ fontFamily: 'monospace', color: '#f8fafc', fontSize: '11px' }}>{data.revision.revision_id}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Input Hash:</span>
                        <span style={{ fontFamily: 'monospace', color: '#93c5fd', fontSize: '11px' }} title={data.input_hash}>
                          {data.input_hash ? `${data.input_hash.substring(0, 24)}…` : 'None'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #1e2235' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Revision Lifecycle:</span>
                        <span className="badge badge-blue">{data.revision.lifecycle_status}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Max File / Record Quota:</span>
                        <span style={{ color: '#cbd5e1' }}>
                          {(data as any).limits?.files || 1000} files / {(data as any).limits?.records_per_kind || 500} records
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Collapsible Raw JSON for Diagnostics */}
                <details style={{ marginTop: '8px', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>
                    Developer & Audit Raw JSON Inspector
                  </summary>
                  <div style={{ marginTop: '10px' }}>
                    <Json value={{ project: data.product, revision: data.revision.revision_id, input_hash: data.input_hash, limits: (data as any).limits }} />
                  </div>
                </details>
              </div>
            )}

            {/* TAB 2: LIFECYCLE */}
            {tab === 'lifecycle' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Lifecycle
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Standard nine-stage power engineering lifecycle gates, reviews, and blocking criteria.
                  </p>
                </div>

                {data.lifecycle.stages.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#121522', borderRadius: '6px' }}>
                    <p>This revision has not been enrolled.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {data.lifecycle.stages.map((s, idx) => {
                      const isCompleted = s.status === 'COMPLETED' || s.effective_status === 'COMPLETED';
                      const isInProgress = s.status === 'IN_PROGRESS' || s.effective_status === 'IN_PROGRESS';
                      const isBlocked = s.status === 'BLOCKED' || s.effective_status === 'BLOCKED';
                      const badgeClass = isCompleted ? 'badge-green' : isInProgress ? 'badge-blue' : isBlocked ? 'badge-red' : 'badge-muted';

                      return (
                        <div
                          key={s.definition.id}
                          style={{
                            padding: '16px',
                            background: '#121522',
                            borderRadius: '6px',
                            border: '1px solid var(--border)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  fontWeight: 800,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  background: '#1e293b',
                                  color: '#94a3b8',
                                }}
                              >
                                Stage {idx + 1}
                              </span>
                              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
                                {s.definition.name}
                              </h4>
                            </div>
                            <span className={`badge ${badgeClass}`}>
                              {s.effective_status || s.status}
                            </span>
                          </div>

                          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.4 }}>
                            {s.definition.purpose}
                          </p>

                          <div
                            style={{
                              display: 'flex',
                              gap: '16px',
                              marginTop: '12px',
                              paddingTop: '8px',
                              borderTop: '1px solid #1a1e30',
                              fontSize: '11px',
                              color: 'var(--text-dim)',
                              flexWrap: 'wrap',
                            }}
                          >
                            <span>Recorded: <b style={{ color: '#cbd5e1' }}>{s.status}</b></span>
                            <span>Effective: <b style={{ color: '#cbd5e1' }}>{s.effective_status}</b></span>
                            <span>Stale: <b style={{ color: s.stale ? '#fbbf24' : '#94a3b8' }}>{String(s.stale)}</b></span>
                            <span>Review required: <b style={{ color: '#cbd5e1' }}>{String(s.definition.review_required)}</b></span>
                          </div>

                          {/* Blockers alert if present */}
                          {s.blockers && s.blockers.length > 0 && (
                            <div
                              style={{
                                marginTop: '10px',
                                padding: '8px 12px',
                                background: 'rgba(239, 68, 68, 0.08)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: '#fca5a5',
                              }}
                            >
                              <strong>Blocking criteria:</strong> {Array.isArray(s.blockers) ? s.blockers.join('; ') : String(s.blockers)}
                            </div>
                          )}

                          {/* Details JSON */}
                          <details style={{ marginTop: '10px' }}>
                            <summary style={{ cursor: 'pointer', fontSize: '11px', color: 'var(--text-dim)' }}>
                              Stage criteria & blocker payload
                            </summary>
                            <div style={{ marginTop: '6px' }}>
                              <Json value={{ criteria: s.criteria, blockers: s.blockers }} />
                            </div>
                          </details>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: SPECIFICATIONS */}
            {tab === 'specifications' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Saved specifications
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Authoritative engineering envelope recorded in SQLite. Unspecified values remain unavailable.
                  </p>
                </div>

                <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sliders size={14} color="#60a5fa" /> Electrical Operating Parameters
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Input Voltage (Nominal)</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                        {data.revision.specification?.vin_nom_v != null ? `${data.revision.specification.vin_nom_v} V` : 'Unavailable'}
                      </div>
                    </div>

                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Input Voltage (Min - Max)</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                        {data.revision.specification?.vin_min_v != null && data.revision.specification?.vin_max_v != null
                          ? `${data.revision.specification.vin_min_v} V – ${data.revision.specification.vin_max_v} V`
                          : 'Unavailable'}
                      </div>
                    </div>

                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Target Output Voltage</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#60a5fa', marginTop: '2px' }}>
                        {data.revision.specification?.vout_v != null ? `${data.revision.specification.vout_v} V` : 'Unavailable'}
                      </div>
                    </div>

                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Output Current / Power</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
                        {data.revision.specification?.iout_a != null ? `${data.revision.specification.iout_a} A` : 'Unavailable'}
                      </div>
                    </div>

                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Switching Frequency</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                        {data.revision.specification?.switching_frequency_hz != null
                          ? `${(data.revision.specification.switching_frequency_hz / 1000).toFixed(0)} kHz`
                          : 'Unavailable'}
                      </div>
                    </div>

                    <div style={{ padding: '10px 12px', background: '#181b29', borderRadius: '4px', border: '1px solid #262b40' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Isolation Requirement</div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#cbd5e1', marginTop: '2px' }}>
                        {data.revision.specification?.isolation_requirement || 'Unavailable'}
                      </div>
                    </div>
                  </div>
                </div>

                <details style={{ marginTop: '4px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>
                    Specification Record Payload
                  </summary>
                  <div style={{ marginTop: '8px' }}>
                    <Json value={data.revision.specification} />
                  </div>
                </details>
              </div>
            )}

            {/* TAB 4: CALCULATIONS */}
            {tab === 'calculations' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Persisted calculation runs
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Deterministic analytical calculations recorded by Mendex Core.
                  </p>
                </div>

                {(!data.calculations || (Array.isArray(data.calculations) && data.calculations.length === 0) || ((data.calculations as any).records && (data.calculations as any).records.length === 0)) ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#121522', borderRadius: '6px' }}>
                    <Calculator size={24} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>No calculations recorded for this revision yet.</p>
                    <p style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Run deterministic semiconductor loss, transformer sizing, or Dowell AC resistance calculations via Codex / Mendex Core.
                    </p>
                  </div>
                ) : (
                  <Json value={data.calculations} />
                )}
              </div>
            )}

            {/* TAB 5: SIMULATIONS */}
            {tab === 'simulations' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Simulation jobs for this revision
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Software execution does not establish engineering validation.
                  </p>
                </div>

                {data.simulations.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#121522', borderRadius: '6px' }}>
                    <Cpu size={24} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>No simulation jobs dispatched for this revision.</p>
                    <p style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Trigger LTspice, FEMM, or Qucs-S solver jobs through the Mendex MCP / CLI.
                    </p>
                  </div>
                ) : (
                  <Json value={data.simulations} />
                )}

                <div style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1' }}>
                    Historical jobs without revision attribution
                  </h4>
                  <Json value={(data as any).unattributed_simulations || []} />
                </div>
              </div>
            )}

            {/* TAB 6: DESIGNS */}
            {tab === 'designs' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Recorded designs and artifact snapshots
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    CAD files, netlists, schematics, and registered engineering artifacts.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                      Design Snapshots
                    </h4>
                    <Json value={data.designs} />
                  </div>

                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                      Registered Artifacts
                    </h4>
                    <Json value={data.registered_artifacts} />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 7: FILES */}
            {tab === 'files' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Revision files
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Physical files and evidence snapshots recorded in the revision workspace.
                  </p>
                </div>

                {data.files.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#121522', borderRadius: '6px' }}>
                    <p>No revision files available.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {data.files.map((f) => (
                      <div
                        key={f.relative_path}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '12px 16px',
                          background: '#121522',
                          borderRadius: '6px',
                          border: '1px solid var(--border)',
                          flexWrap: 'wrap',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileCode size={16} color="#60a5fa" />
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', fontFamily: 'monospace' }}>
                              {f.relative_path}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                              Size: {formatBytes(f.size_bytes)} ({f.size_bytes} bytes)
                            </div>
                          </div>
                        </div>

                        <button
                          className="btn btn-secondary"
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 12px', fontSize: '11px' }}
                          onClick={() => action(() => api.openFile(data.revision.revision_id, f.relative_path))}
                        >
                          <ExternalLink size={12} /> Open in native application
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 8: VALIDATION */}
            {tab === 'validation' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Recorded validation and evidence
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Attribution is not authenticated review or safety certification.
                  </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                      Validation Status
                    </h4>
                    <Json value={data.validation} />
                  </div>

                  <div style={{ padding: '16px', background: '#121522', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#cbd5e1', marginBottom: '8px' }}>
                      Automated PCB Checks
                    </h4>
                    <Json value={(data as any).pcb_checks} />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 9: REVISIONS */}
            {tab === 'revisions' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Revision history
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Immutable sequence of frozen engineering revisions and audit trail.
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {data.revisions.map((r) => {
                    const isActive = r.revision_id === data.revision.revision_id;
                    return (
                      <div
                        key={r.revision_id}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '14px 16px',
                          background: '#121522',
                          borderRadius: '6px',
                          border: `1px solid ${isActive ? 'var(--primary)' : 'var(--border)'}`,
                          flexWrap: 'wrap',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span
                            style={{
                              fontSize: '12px',
                              fontWeight: 800,
                              padding: '3px 8px',
                              borderRadius: '4px',
                              backgroundColor: isActive ? 'rgba(59, 130, 246, 0.2)' : '#1e2235',
                              color: isActive ? '#60a5fa' : '#94a3b8',
                              border: `1px solid ${isActive ? '#3b82f6' : 'transparent'}`,
                            }}
                          >
                            {r.revision_label}
                          </span>
                          <div>
                            <div style={{ fontSize: '12px', color: '#f8fafc', fontFamily: 'monospace' }}>
                              {r.revision_id}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                              Created: {new Date(r.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        <span className={`badge ${r.lifecycle_status === 'passed' ? 'badge-green' : 'badge-blue'}`}>
                          {r.lifecycle_status}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <details style={{ marginTop: '8px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '11px', color: 'var(--text-dim)' }}>
                    Raw Revisions Array
                  </summary>
                  <div style={{ marginTop: '8px' }}>
                    <Json value={data.revisions} />
                  </div>
                </details>
              </div>
            )}

            {/* TAB 10: REPORTS */}
            {tab === 'reports' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                    Draft reports
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Compilation of formal engineering reports, stage reviews, and export packages.
                  </p>
                </div>

                {data.reports.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#121522', borderRadius: '6px' }}>
                    <FileBarChart size={24} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>No reports available.</p>
                    <p style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Generate Stage 1 Initialization, ERS, or V&V report packages through the Mendex MCP.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {data.reports.map((r: any) => (
                      <div
                        key={r.report.report_id}
                        style={{
                          padding: '16px',
                          background: '#121522',
                          borderRadius: '6px',
                          border: '1px solid var(--border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>
                            Report generated: {new Date(r.report.generated_at).toLocaleString()}
                          </span>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            <span className={`badge ${r.integrity === 'VERIFIED' ? 'badge-green' : 'badge-yellow'}`}>
                              Integrity: {r.integrity}
                            </span>
                            {r.stale && <span className="badge badge-yellow">Stale</span>}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                          <button
                            className="btn btn-secondary"
                            disabled={!r.available || r.integrity === 'FAILED'}
                            onClick={() => action(() => api.openReport(r.report.report_id))}
                            style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                          >
                            <ExternalLink size={12} /> Open report
                          </button>
                          <button
                            className="btn btn-secondary"
                            disabled={!r.available || r.integrity === 'FAILED'}
                            onClick={() => action(() => api.exportReport(r.report.report_id))}
                            style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                          >
                            <Download size={12} /> Export package
                          </button>
                        </div>

                        {r.report.warnings && r.report.warnings.length > 0 && (
                          <div style={{ marginTop: '4px' }}>
                            <Json value={r.report.warnings} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};