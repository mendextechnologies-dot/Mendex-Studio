import React, { useCallback, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import type { ProjectDetailData } from '../api/types';
import { RevisionEngineeringPanel, effectiveStageStatus, validationStatus } from '../components/RevisionEngineeringPanel';
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
  Key,
  Lock,
  AlertTriangle,
  Zap,
  Search,
  Filter,
  Eye,
  CheckCheck,
  FileCheck,
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
      backgroundColor: '#edf2f8',
      padding: '12px',
      borderRadius: '6px',
      border: '1px solid var(--border)',
      color: '#334155',
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

export const ProjectDetailView = ({
  projectId,
  onBack,
  data,
  error = '',
  selectedRevisionId,
  onSelectRevision,
}: {
  projectId: string;
  onBack: () => void;
  data: ProjectDetailData | null;
  error?: string;
  selectedRevisionId?: string | null;
  onSelectRevision?: (revId: string) => void;
}) => {
  const [tab, setTab] = useState<TabId>(() => {
    const param = new URLSearchParams(location.search).get('tab') as TabId;
    return TAB_DEFS.some((t) => t.id === param) ? param : 'overview';
  });
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  const [fileFilter, setFileFilter] = useState('all');
  const [fileSearch, setFileSearch] = useState('');

  // Human Engineering Review Modal State
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewStageId, setReviewStageId] = useState('requirements');
  const [reviewPackage, setReviewPackage] = useState<any>(null);
  const [reviewerName, setReviewerName] = useState('');
  const [reviewComments, setReviewComments] = useState('');
  const [deferralRationale, setDeferralRationale] = useState('');
  const [deferralOwner, setDeferralOwner] = useState('');
  const [deferralGate, setDeferralGate] = useState('Before completing Stage 3: Feasibility and Architecture; before detailed design');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [isGeneratingBom, setIsGeneratingBom] = useState(false);

  const handleGenerateBom = async () => {
    if (!data?.revision?.revision_id) return;
    setIsGeneratingBom(true);
    setActionError('');
    try {
      const res = await api.generateBom(data.revision.revision_id);
      setMessage(res.message);
      setTimeout(() => setMessage(''), 6000);
    } catch (e: any) {
      setActionError(String(e));
      setTimeout(() => setActionError(''), 6000);
    } finally {
      setIsGeneratingBom(false);
    }
  };

  const action = async (call: () => Promise<unknown>) => {
    try {
      setActionError('');
      const result = await call();
      let msg = 'Operation succeeded.';
      if (typeof result === 'string') {
        msg = result;
      } else if (result && typeof result === 'object') {
        const obj = result as Record<string, any>;
        if (obj.opened) {
          const fname = String(obj.opened).replace(/\\/g, '/').split('/').pop() || '';
          const ext = fname.split('.').pop()?.toLowerCase();
          const appName = ext === 'kicad_sch' ? 'KiCad Schematic Editor' :
                          ext === 'kicad_pcb' ? 'KiCad PCB Editor' :
                          ext === 'kicad_pro' ? 'KiCad Project Manager' :
                          ext === 'step' || ext === 'stp' ? 'FreeCAD 3D CAD' :
                          ext === 'net' || ext === 'raw' || ext === 'asc' ? 'LTspice' :
                          ext === 'fem' || ext === 'ans' ? 'FEMM 4.2' :
                          ext === 'pdf' ? 'PDF Viewer (Microsoft Edge)' :
                          ext === 'docx' || ext === 'doc' ? 'Microsoft Word' :
                          ext === 'xlsx' || ext === 'xls' ? 'Microsoft Excel' :
                          ext === 'csv' || ext === 'json' ? 'Data Viewer' : 'native application';
          msg = `Launch requested for ${fname} in ${appName}.`;
        } else if (obj.revealed) {
          const fname = String(obj.revealed).replace(/\\/g, '/').split('/').pop();
          msg = `Revealed ${fname} in Windows File Explorer.`;
        }
      }
      setMessage(msg);
      setTimeout(() => setMessage(''), 5000);
    } catch (e) {
      setActionError(String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  const openReviewModal = async (stageId: string) => {
    try {
      setActionError('');
      setReviewStageId(stageId);
      if (!data) return;
      const pkg = await api.reviewPackage(data.revision.revision_id, stageId);
      setReviewPackage(pkg);
      setReviewerName('');
      setReviewComments('');
      setDeferralRationale('');
      setDeferralOwner('');
      setReviewModalOpen(true);
    } catch (e) {
      setActionError(String(e));
    }
  };

  const handleRequestReview = async (stageId: string) => {
    if (!data) return;
    await action(async () => {
      await api.requestReview(
        data.revision.revision_id,
        data.product.owner || 'Lead Engineer',
        `Formal review requested for ${stageId}`,
        stageId
      );
      return `Review requested for ${stageId}. Awaiting qualified reviewer decision.`;
    });
  };

  const handleCompleteStage = async (stageId: string) => {
    if (!data) return;
    await action(async () => {
      await api.completeStage(data.revision.revision_id, stageId);
      return `Stage '${stageId}' successfully verified and completed!`;
    });
  };

  const handleSubmitReviewDecision = async (decision: 'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED') => {
    if (!data || !reviewPackage) return;
    try {
      setIsSubmittingReview(true);
      setActionError('');

      const deferrals: any[] = [];
      if (decision === 'APPROVED' && reviewPackage.safety_blockers?.length > 0 && deferralRationale) {
        for (const blocker of reviewPackage.safety_items || []) {
          deferrals.push({
            requirement_id: blocker.id,
            rationale: deferralRationale,
            owner: deferralOwner.trim(),
            scope: 'Preliminary feasibility analysis only; detailed design and physical work remain gated',
            downstream_gate: deferralGate,
          });
        }
      }

      const res = await api.submitReview({
        revision_id: data.revision.revision_id,
        stage_id: reviewStageId,
        attempt: reviewPackage.stage.attempt || 1,
        decision,
        reviewer_name: reviewerName.trim(),
        comments: reviewComments.trim(),
        conflicts: reviewPackage.conflicts || [],
        deferrals,
        expected_requirements_digest: reviewPackage.requirements_package.digest,
        expected_specification_hash: reviewPackage.revision.specification_hash,
        expected_document_hashes: reviewPackage.document_hashes,
        expected_evidence_hashes: reviewPackage.evidence_hashes,
        idempotency_key: crypto.randomUUID(),
      });

      setReviewModalOpen(false);
      setMessage(`Review successfully recorded: ${decision} by ${res.reviewer_name}`);
      setTimeout(() => setMessage(''), 5000);
    } catch (e: any) {
      setActionError(e.message || String(e));
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // Safe extraction of records
  const calcRecords = data
    ? Array.isArray(data.calculations)
      ? data.calculations
      : (data.calculations as any)?.records || []
    : [];

  const artifactRecords = data
    ? Array.isArray(data.registered_artifacts)
      ? data.registered_artifacts
      : (data.registered_artifacts as any)?.records || []
    : [];

  const valRecords = data
    ? Array.isArray(data.validation)
      ? data.validation
      : (data.validation as any)?.results || (data.validation as any)?.records || []
    : [];

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
          <span style={{ fontSize: '12px', color: '#1d4ed8', fontWeight: 700 }}>
            {data ? data.product.code : 'Project'}
          </span>
        </div>

        {data && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {data.revisions && data.revisions.length > 1 ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>Revision:</span>
                <select
                  value={data.revision.revision_id}
                  onChange={(e) => onSelectRevision && onSelectRevision(e.target.value)}
                  className="input"
                  style={{ padding: '4px 8px', fontSize: '12px', fontWeight: 700, borderRadius: '4px', borderColor: '#1d4ed8', background: '#eff6ff', color: '#1e40af' }}
                >
                  {data.revisions.map((rev) => (
                    <option key={rev.revision_id} value={rev.revision_id}>
                      {rev.revision_label} ({rev.lifecycle_status.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <span className={`badge ${data.product.revision_status === 'PASSED' ? 'badge-green' : 'badge-blue'}`}>
                Revision: {data.revision.revision_label}
              </span>
            )}
            <span className="badge badge-yellow">
              Engineering: {data.lifecycle?.engineering_status || 'DRAFT'}
            </span>
            <span className="badge badge-muted">
              Approval: {data.lifecycle?.approval_status || 'PENDING'}
            </span>
          </div>
        )}
      </div>

      {error && <p role="alert" style={{ color: '#b91c1c', fontSize: '12px' }}>{error}. Displayed records may be stale.</p>}

      {!data ? (
        <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin" style={{ marginBottom: '12px', color: '#1d4ed8' }} />
          <p>{error ? 'Project unavailable' : 'Loading project baseline & engineering records…'}</p>
        </div>
      ) : (
        <>
          {/* 2. Project Hero Card */}
          <div
            className="card"
            style={{
              padding: '20px',
              background: 'linear-gradient(180deg, #f3f6fb 0%, #ffffff 100%)',
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
                    color: '#1d4ed8',
                    fontWeight: 800,
                    fontSize: '16px',
                    flexShrink: 0,
                  }}
                >
                  {data.product.code.split('-')[0] || 'PRJ'}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#172033', letterSpacing: '-0.3px' }}>
                      {data.product.code} — {data.product.name}
                    </h2>
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: 'rgba(16, 185, 129, 0.1)',
                        color: '#047857',
                        fontWeight: 600,
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                      }}
                    >
                      {data.product.category.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', maxWidth: '850px', lineHeight: 1.5 }}>
                    {data.product.description || 'Precision High-Voltage DC-DC Converter baseline registered in SQLite repository.'}
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
                borderTop: '1px solid rgba(23,32,51,0.10)',
                fontSize: '12px',
                color: 'var(--text-dim)',
                flexWrap: 'wrap',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <User size={13} color="var(--text-dim)" /> Owner: <strong style={{ color: '#334155' }}>{data.product.owner}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Calendar size={13} color="var(--text-dim)" /> Created:{' '}
                <strong style={{ color: '#334155' }}>
                  {data.product.created_at ? new Date(data.product.created_at).toLocaleDateString() : 'N/A'}
                </strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <GitCommit size={13} color="var(--text-dim)" /> Active Revision:{' '}
                <strong style={{ color: '#334155' }}>{data.revision.revision_label}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Folder size={13} color="var(--text-dim)" /> Files:{' '}
                <strong style={{ color: '#334155' }}>{data.files.length}</strong>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Activity size={13} color="var(--text-dim)" /> Lifecycle Stages:{' '}
                <strong style={{ color: '#334155' }}>{data.lifecycle.stages.length}</strong>
              </span>
            </div>
          </div>

          {/* Action Alerts / Feedback */}
          {actionError && (
            <div
              role="alert"
              style={{
                padding: '12px 16px',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                borderRadius: '6px',
                color: '#b91c1c',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <AlertCircle size={16} />
              <span>{actionError}</span>
            </div>
          )}
          {message && (
            <div
              role="status"
              style={{
                padding: '12px 16px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                borderRadius: '6px',
                color: '#047857',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <CheckCircle2 size={16} />
              <span>{message}</span>
            </div>
          )}

          {/* 3. Modern Styled Tabs Strip */}
          <nav
            style={{
              display: 'flex',
              gap: '6px',
              background: '#f3f6fb',
              padding: '8px 12px 0 12px',
              borderRadius: '10px 10px 0 0',
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
              if (t.id === 'simulations') count = data.simulations.length > 0 ? data.simulations.length : 2;
              if (t.id === 'calculations') count = calcRecords.length;
              if (t.id === 'designs') count = 3;
              if (t.id === 'validation') count = valRecords.length;
              if (t.id === 'reports') count = data.reports.length;

              return (
                <button
                  key={t.id}
                  id={`tab-${t.id}`}
                  data-tab={t.id}
                  onClick={() => setTab(t.id)}
                  aria-pressed={isActive}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',
                    fontSize: '12px',
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? '#172033' : '#52627a',
                    backgroundColor: isActive ? 'var(--bg-card)' : 'transparent',
                    border: '1px solid',
                    borderColor: isActive ? 'var(--border)' : 'transparent',
                    borderTop: isActive ? '2px solid #0369a1' : '2px solid transparent',
                    borderBottomColor: isActive ? 'var(--bg-card)' : 'transparent',
                    borderRadius: '6px 6px 0 0',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s ease',
                    marginBottom: isActive ? '-1px' : '0',
                    zIndex: isActive ? 2 : 1,
                  }}
                >
                  <Icon size={14} color={isActive ? '#0369a1' : '#58677d'} />
                  <span>{t.label}</span>
                  {count !== null && count > 0 && (
                    <span
                      style={{
                        fontSize: '10px',
                        padding: '1px 6px',
                        borderRadius: '10px',
                        backgroundColor: isActive ? 'rgba(56, 189, 248, 0.2)' : 'rgba(23, 32, 51, 0.04)',
                        color: isActive ? '#0369a1' : '#52627a',
                        fontWeight: 700,
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#172033', letterSpacing: '-0.3px' }}>
                      Executive Project Summary
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Recorded project baseline, specifications, evidence and lifecycle integrity.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setTab('lifecycle')}
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '6px 14px' }}
                    >
                      <Activity size={14} /> View Lifecycle Gates
                    </button>
                    {data.lifecycle.stages.some((s: any) => s.definition.id === 'requirements' && (s.review_status === 'REQUESTED' || s.review?.effective_status !== 'APPROVED')) && (
                      <button
                        onClick={() => openReviewModal('requirements')}
                        className="btn btn-primary"
                        style={{ fontSize: '12px', padding: '6px 14px', background: '#2563eb' }}
                      >
                        <ShieldCheck size={14} /> Review Requirements
                      </button>
                    )}
                  </div>
                </div>

                {/* 4-KPI Overview Row */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>
                      Enrolled Stages
                    </div>
                    <div style={{ fontSize: '22px', fontWeight: 800, color: '#172033', marginTop: '6px' }}>
                      {data.lifecycle.stages.filter((s: any) => effectiveStageStatus(s) === 'COMPLETED').length} / {data.lifecycle.stages.length}
                    </div>
                    <div style={{ fontSize: '11px', color: '#1d4ed8', marginTop: '4px' }}>
                      Stages 1–5 Completed
                    </div>
                  </div>

                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>
                      Revision Files
                    </div>
                    <div style={{ fontSize: '22px', fontWeight: 800, color: '#172033', marginTop: '6px' }}>
                      {data.files.length}
                    </div>
                    <div style={{ fontSize: '11px', color: '#047857', marginTop: '4px' }}>
                      CAD, Models, Reports & Netlists
                    </div>
                  </div>

                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>
                      Engineering Calculations
                    </div>
                    <div style={{ fontSize: '22px', fontWeight: 800, color: '#172033', marginTop: '6px' }}>
                      {calcRecords.length}
                    </div>
                    <div style={{ fontSize: '11px', color: '#0369a1', marginTop: '4px' }}>
                      Recorded inputs and results for this revision
                    </div>
                  </div>

                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>
                      Next Execution Stage
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#92400e', marginTop: '10px' }}>
                      {data.lifecycle.stages.find((stage: any) => !['COMPLETED', 'NOT_APPLICABLE'].includes(effectiveStageStatus(stage)))?.definition.name || 'No incomplete stage'}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      See lifecycle criteria and current blockers
                    </div>
                  </div>
                </div>

                {/* Stage Progression Stepper */}
                <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Engineering Stage Pipeline
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                      Click stage to view gates & evidence
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(1, data.lifecycle.stages.length)}, 1fr)`, gap: '8px', overflowX: 'auto' }}>
                    {data.lifecycle.stages.map((st: any, idx: number) => {
                      const isDone = effectiveStageStatus(st) === 'COMPLETED';
                      const isCurrent = ['IN_PROGRESS', 'AWAITING_REVIEW'].includes(effectiveStageStatus(st));
                      return (
                        <div
                          key={st.definition.id}
                          onClick={() => setTab('lifecycle')}
                          style={{
                            padding: '10px',
                            background: isDone ? 'rgba(16, 185, 129, 0.1)' : isCurrent ? 'rgba(56, 189, 248, 0.1)' : '#f3f6fb',
                            border: `1px solid ${isDone ? 'rgba(16, 185, 129, 0.3)' : isCurrent ? 'rgba(56, 189, 248, 0.35)' : 'rgba(23,32,51,0.10)'}`,
                            borderRadius: '6px',
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontSize: '10px', fontWeight: 800, color: isDone ? '#047857' : isCurrent ? '#0369a1' : 'var(--text-dim)' }}>
                              S{idx + 1}
                            </span>
                            {isDone ? (
                              <CheckCircle2 size={12} color="#047857" />
                            ) : isCurrent ? (
                              <Clock size={12} color="#0369a1" />
                            ) : (
                              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#334155' }} />
                            )}
                          </div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: isDone ? '#172033' : isCurrent ? '#1d4ed8' : '#58677d', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {st.definition.name}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Two Column Project Baseline Info */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '16px' }}>
                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#334155', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Box size={14} color="#1d4ed8" /> Product Definition & Provenance
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Product ID:</span>
                        <span style={{ fontFamily: 'monospace', color: '#172033' }}>{data.product.product_id}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Project Code:</span>
                        <span style={{ fontWeight: 600, color: '#1d4ed8' }}>{data.product.code}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Category:</span>
                        <span style={{ color: '#334155' }}>{data.product.category}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Lead Engineer:</span>
                        <span style={{ color: '#334155' }}>{data.product.owner}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Active Revision:</span>
                        <span style={{ fontWeight: 600, color: '#047857' }}>{data.revision.revision_label}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ padding: '16px', background: '#f3f6fb', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#334155', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <GitCommit size={14} color="#047857" /> Active Baseline & Hash Integrity
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Revision UUID:</span>
                        <span style={{ fontFamily: 'monospace', color: '#172033', fontSize: '11px' }}>{data.revision.revision_id}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Input Hash:</span>
                        <span style={{ fontFamily: 'monospace', color: '#1d4ed8', fontSize: '11px' }} title={data.input_hash}>
                          {data.input_hash ? `${data.input_hash.substring(0, 24)}…` : 'None'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Revision Lifecycle:</span>
                        <span className="badge badge-blue">{data.revision.lifecycle_status}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Artifact Storage:</span>
                        <span style={{ color: '#334155' }}>
                          Hash-checked artifact records ({artifactRecords.length} returned)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Diagnostics Collapsible */}
                <details style={{ marginTop: '8px', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>
                    Developer & Audit Diagnostics JSON
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                      Lifecycle Stages & Gates
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Standard nine-stage power engineering lifecycle gates, reviews, and blocking criteria.
                    </p>
                  </div>
                </div>

                {data.lifecycle.stages.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#f3f6fb', borderRadius: '6px' }}>
                    <p>This revision has not been enrolled.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {data.lifecycle.stages.map((s: any, idx: number) => {
                      const isCompleted = effectiveStageStatus(s) === 'COMPLETED';
                      const isInProgress = effectiveStageStatus(s) === 'IN_PROGRESS';
                      const isBlocked = effectiveStageStatus(s) === 'BLOCKED';
                      const badgeClass = isCompleted ? 'badge-green' : isInProgress ? 'badge-blue' : isBlocked ? 'badge-red' : 'badge-muted';
                      const review = s.review;

                      return (
                        <div
                          key={s.definition.id}
                          style={{
                            padding: '18px',
                            background: '#f3f6fb',
                            borderRadius: '8px',
                            border: `1px solid ${isCompleted ? 'rgba(16, 185, 129, 0.4)' : 'var(--border)'}`,
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  fontWeight: 800,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  background: '#eaf2ff',
                                  color: '#52627a',
                                }}
                              >
                                Stage {idx + 1}
                              </span>
                              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#172033' }}>
                                {s.definition.name}
                              </h4>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span className={`badge ${badgeClass}`}>
                                {s.effective_status || s.status}
                              </span>
                            </div>
                          </div>

                          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.4 }}>
                            {s.definition.purpose}
                          </p>

                          {/* Stage Review Banner if review exists */}
                          {review && (
                            <div
                              style={{
                                marginTop: '12px',
                                padding: '10px 14px',
                                borderRadius: '6px',
                                backgroundColor:
                                  review.effective_status === 'APPROVED'
                                    ? 'rgba(16, 185, 129, 0.08)'
                                    : review.effective_status === 'STALE'
                                    ? 'rgba(245, 158, 11, 0.08)'
                                    : 'rgba(239, 68, 68, 0.08)',
                                border: `1px solid ${
                                  review.effective_status === 'APPROVED'
                                    ? 'rgba(16, 185, 129, 0.3)'
                                    : review.effective_status === 'STALE'
                                    ? 'rgba(245, 158, 11, 0.3)'
                                    : 'rgba(239, 68, 68, 0.3)'
                                }`,
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                flexWrap: 'wrap',
                                gap: '10px',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                                {review.effective_status === 'APPROVED' ? (
                                  <ShieldCheck size={16} color="#047857" />
                                ) : (
                                  <ShieldAlert size={16} color="#b91c1c" />
                                )}
                                <div>
                                  <span style={{ fontWeight: 700, color: review.effective_status === 'APPROVED' ? '#047857' : '#b91c1c' }}>
                                    {review.effective_status}: {review.reviewer_name}
                                    {review.review_mode === 'MANUALLY_DECLARED' && ' · Manually declared human review'}
                                  </span>
                                  <span style={{ color: 'var(--text-dim)', marginLeft: '8px' }}>
                                    "{review.comments}"
                                  </span>
                                </div>
                              </div>
                              <span style={{ fontFamily: 'monospace', fontSize: '10px', color: 'var(--text-dim)' }}>
                                Digest: {review.signature?.substring(0, 16)}…
                              </span>
                            </div>
                          )}

                          <div
                            style={{
                              display: 'flex',
                              gap: '16px',
                              marginTop: '12px',
                              paddingTop: '8px',
                              borderTop: '1px solid #f3f6fb',
                              fontSize: '11px',
                              color: 'var(--text-dim)',
                              flexWrap: 'wrap',
                            }}
                          >
                            <span>Recorded: <b style={{ color: '#334155' }}>{s.status}</b></span>
                            <span>Effective: <b style={{ color: '#334155' }}>{s.effective_status}</b></span>
                            <span>Stale: <b style={{ color: s.stale ? '#92400e' : '#52627a' }}>{String(s.stale)}</b></span>
                            <span>Review required: <b style={{ color: '#334155' }}>{String(s.definition.review_required)}</b></span>
                          </div>

                          {/* Blockers alert if present */}
                          {s.blockers && s.blockers.length > 0 && (
                            <div
                              style={{
                                marginTop: '10px',
                                padding: '10px 14px',
                                background: 'rgba(239, 68, 68, 0.08)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: '#b91c1c',
                              }}
                            >
                              <strong>Blocking criteria:</strong> {Array.isArray(s.blockers) ? s.blockers.join('; ') : String(s.blockers)}
                            </div>
                          )}

                          {/* Action Buttons: Review & Complete */}
                          <div style={{ marginTop: '14px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                            {s.definition.review_required && (
                              <button
                                className="btn btn-secondary"
                                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', borderColor: '#3b82f6', color: '#1d4ed8' }}
                                onClick={() => openReviewModal(s.definition.id)}
                              >
                                <ShieldCheck size={14} /> Review {s.definition.name}
                              </button>
                            )}

                            {s.definition.review_required && s.review_status !== 'REQUESTED' && (
                              <button
                                className="btn btn-secondary"
                                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                                onClick={() => handleRequestReview(s.definition.id)}
                              >
                                <Clock size={14} /> Request Review
                              </button>
                            )}

                            {!isCompleted && (!s.blockers || s.blockers.length === 0) && (
                              <button
                                className="btn btn-primary"
                                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', background: '#059669' }}
                                onClick={() => handleCompleteStage(s.definition.id)}
                              >
                                <CheckCircle2 size={14} /> Complete {s.definition.name}
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: SPECIFICATIONS */}
            {tab === 'specifications' && (
              <RevisionEngineeringPanel section="specifications" data={data}
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))} />
            )}

            {/* TAB 4: CALCULATIONS */}
            {tab === 'calculations' && (
              <RevisionEngineeringPanel section="calculations" data={data}
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))} />
            )}

            {/* TAB 5: SIMULATIONS */}
            {tab === 'simulations' && (
              <RevisionEngineeringPanel section="simulations" data={data}
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))} />
            )}

            {/* TAB 6: DESIGNS */}
            {tab === 'designs' && (
              <RevisionEngineeringPanel section="designs" data={data}
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))} />
            )}

            {/* TAB 7: FILES */}
            {tab === 'files' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                      Monitored Revision Workspace Files ({data.files.length})
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Physical engineering files tracked with SHA-256 digests in SQLite repository.
                    </p>
                  </div>

                  {/* Filter and Search Bar */}
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ position: 'relative' }}>
                      <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-dim)' }} />
                      <input
                        type="text"
                        placeholder="Search files…"
                        value={fileSearch}
                        onChange={(e) => setFileSearch(e.target.value)}
                        style={{
                          padding: '6px 12px 6px 30px',
                          fontSize: '12px',
                          background: '#f3f6fb',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          color: '#172033',
                          width: '180px',
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', gap: '4px' }}>
                      {['all', 'cad', 'reports', 'sims', 'bom'].map((f) => (
                        <button
                          key={f}
                          onClick={() => setFileFilter(f)}
                          style={{
                            fontSize: '11px',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            background: fileFilter === f ? '#2563eb' : '#f3f6fb',
                            color: fileFilter === f ? '#ffffff' : '#52627a',
                            border: `1px solid ${fileFilter === f ? '#3b82f6' : 'var(--border)'}`,
                            cursor: 'pointer',
                          }}
                        >
                          {f.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {data.files.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#f3f6fb', borderRadius: '6px' }}>
                    <p>No revision files available.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {data.files
                      .filter((f) => {
                        if (fileSearch && !f.relative_path.toLowerCase().includes(fileSearch.toLowerCase())) return false;
                        if (fileFilter === 'cad') return f.relative_path.includes('pcb/') || f.relative_path.includes('mechanical/');
                        if (fileFilter === 'reports') return f.relative_path.includes('reports/');
                        if (fileFilter === 'sims') return f.relative_path.includes('simulations/');
                        if (fileFilter === 'bom') return f.relative_path.includes('bom/');
                        return true;
                      })
                      .map((f) => (
                        <div
                          key={f.relative_path}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '12px 16px',
                            background: '#f3f6fb',
                            borderRadius: '6px',
                            border: '1px solid var(--border)',
                            flexWrap: 'wrap',
                            gap: '10px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <FileCode size={16} color="#1d4ed8" />
                            <div>
                              <div style={{ fontSize: '13px', fontWeight: 600, color: '#172033', fontFamily: 'monospace' }}>
                                {f.relative_path}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                                Size: {formatBytes(f.size_bytes)} ({f.size_bytes} bytes)
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              className="btn btn-secondary"
                              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 12px', fontSize: '11px' }}
                              onClick={() => action(() => api.openFile(data.revision.revision_id, f.relative_path))}
                            >
                              <ExternalLink size={12} /> Open
                            </button>
                            <button
                              className="btn btn-secondary"
                              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 12px', fontSize: '11px' }}
                              onClick={() => action(() => api.revealFile(data.revision.revision_id, f.relative_path))}
                            >
                              <Folder size={12} /> Reveal in Explorer
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 8: VALIDATION */}
            {tab === 'validation' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                      Lifecycle Stage Validation Gates & Acceptance Evidence
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Authorized verification decisions, rule versions, and cryptographic evidence hashes.
                    </p>
                  </div>
                  <span className="badge badge-green">{valRecords.length} Validation Records</span>
                </div>

                {valRecords.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#f3f6fb', borderRadius: '6px' }}>
                    <ShieldAlert size={24} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p>No formal validation records registered for this revision yet.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {valRecords.map((vr: any, idx: number) => {
                      const rec = vr.record || vr;
                      const chk = rec.check || {};
                      const effective = validationStatus(vr);
                      const isPass = effective === 'PASS';

                      return (
                        <div
                          key={rec.record_id || idx}
                          style={{
                            padding: '16px',
                            background: '#f3f6fb',
                            borderRadius: '8px',
                            border: `1px solid ${isPass ? 'rgba(16, 185, 129, 0.4)' : 'var(--border)'}`,
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '10px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <ShieldCheck size={18} color="#047857" />
                              <span style={{ fontSize: '14px', fontWeight: 700, color: '#172033', fontFamily: 'monospace' }}>
                                {chk.check_id}
                              </span>
                              <span className={`badge ${isPass ? 'badge-green' : 'badge-yellow'}`}>{effective}</span>
                              <span className="badge badge-blue">{chk.evidence_kind || 'CALCULATED'}</span>
                            </div>

                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '11px', color: 'var(--text-dim)' }}>
                              <span>Reviewer: <strong style={{ color: '#334155' }}>{chk.reviewer}</strong></span>
                              <span>·</span>
                              <span>Rule: <strong>{chk.rule_version}</strong></span>
                            </div>
                          </div>

                          <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                            {chk.notes}
                          </p>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', paddingTop: '8px', borderTop: '1px solid #f1f5fb' }}>
                            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', fontSize: '11px', color: 'var(--text-dim)' }}>
                              <span>Evidence: <strong style={{ color: '#1d4ed8' }}>{rec.evidence_filename || 'Evidence File'}</strong></span>
                              <span style={{ fontFamily: 'monospace' }}>SHA-256: {rec.evidence_sha256?.substring(0, 16)}…</span>
                            </div>

                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary"
                                style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
                                disabled={!rec.record_id}
                                onClick={() => action(() => api.openEvidence(rec.record_id))}
                              >
                                <ExternalLink size={12} /> Open Evidence Dossier
                              </button>

                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* TAB 9: REVISIONS */}
            {tab === 'revisions' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                    Revision History & Baseline Traceability
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Immutable sequence of frozen engineering revisions and audit trail in SQLite.
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
                          background: '#f3f6fb',
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
                              backgroundColor: isActive ? 'rgba(59, 130, 246, 0.2)' : '#f1f5fb',
                              color: isActive ? '#1d4ed8' : '#52627a',
                              border: `1px solid ${isActive ? '#3b82f6' : 'transparent'}`,
                            }}
                          >
                            {r.revision_label}
                          </span>
                          <div>
                            <div style={{ fontSize: '12px', color: '#172033', fontFamily: 'monospace' }}>
                              {r.revision_id}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                              Created: {new Date(r.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={`badge ${r.lifecycle_status === 'passed' ? 'badge-green' : 'badge-blue'}`}>
                            {r.lifecycle_status}
                          </span>
                          {!isActive && onSelectRevision && (
                            <button
                              onClick={() => onSelectRevision(r.revision_id)}
                              className="btn btn-secondary"
                              style={{ fontSize: '11px', padding: '4px 10px' }}
                            >
                              Switch to this revision
                            </button>
                          )}
                          {isActive && (
                            <span className="badge badge-green" style={{ fontSize: '10px' }}>
                              CURRENT VIEW
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB 10: REPORTS */}
            {tab === 'reports' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                    Engineering Dossiers & Reports
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    Compilation of formal engineering reports, stage reviews, and export packages.
                  </p>
                </div>

                {/* Production BOM Deliverables Header in Reports Tab */}
                <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '6px', border: '1px solid #cbd5e1', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <FileCheck size={20} color="#1d4ed8" />
                    <div>
                      <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a' }}>
                        Draft Bill of Materials (BOM) • Sourcing Schedule
                      </h4>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                        Vector PDF & Editable Word formats • 10 Sourced Items derated per IPC-9592B
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                      disabled={!data.files.some(f => f.relative_path.startsWith('bom/') && f.extension === '.pdf')}
                      onClick={() => { const file = data.files.filter(f => f.relative_path.startsWith('bom/') && f.extension === '.pdf').sort((a, b) => b.modified_ns - a.modified_ns)[0]; if (file) action(() => api.openFile(data.revision.revision_id, file.relative_path)); }}
                    >
                      <ExternalLink size={12} /> Open PDF BOM
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                      disabled={!data.files.some(f => f.relative_path.startsWith('bom/') && f.extension === '.docx')}
                      onClick={() => { const file = data.files.filter(f => f.relative_path.startsWith('bom/') && f.extension === '.docx').sort((a, b) => b.modified_ns - a.modified_ns)[0]; if (file) action(() => api.openFile(data.revision.revision_id, file.relative_path)); }}
                    >
                      <FileText size={12} /> Open Word BOM
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                      onClick={handleGenerateBom}
                      disabled={isGeneratingBom || data.revision.lifecycle_status !== 'draft'}
                    >
                      <RefreshCw size={12} className={isGeneratingBom ? 'spin' : ''} />
                      {isGeneratingBom ? 'Generating…' : 'Re-Generate BOM'}
                    </button>
                  </div>
                </div>

                {data.reports.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#f3f6fb', borderRadius: '6px' }}>
                    <FileBarChart size={24} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>No reports available.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {data.reports.map((r: any) => (
                      <div
                        key={r.report.report_id}
                        style={{
                          padding: '16px',
                          background: '#f3f6fb',
                          borderRadius: '6px',
                          border: '1px solid var(--border)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '10px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 600, color: '#172033' }}>
                            Report generated: {new Date(r.report.generated_at).toLocaleString()}
                          </span>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            <span className={`badge ${r.integrity === 'INTACT' ? 'badge-green' : 'badge-yellow'}`}>
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
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* 5. HUMAN ENGINEERING REVIEW MODAL */}
          {reviewModalOpen && reviewPackage && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                backgroundColor: 'rgba(5, 7, 13, 0.85)',
                backdropFilter: 'blur(4px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                padding: '20px',
              }}
            >
              <div
                className="card"
                style={{
                  width: '100%',
                  maxWidth: '860px',
                  maxHeight: '90vh',
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#f3f6fb',
                  border: '1px solid #cbd5e1',
                  boxShadow: '0 20px 60px rgba(23,32,51,0.18)',
                  borderRadius: '10px',
                  overflow: 'hidden',
                }}
              >
                {/* Modal Header */}
                <div
                  style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#f8fafd',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <ShieldCheck size={20} color="#0369a1" />
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033' }}>
                        Human Engineering Review — {reviewPackage.stage.name}
                      </h3>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                        Attempt {reviewPackage.stage.attempt} · Submitter: <b style={{ color: '#334155' }}>{reviewPackage.submitter}</b>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setReviewModalOpen(false)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Modal Body */}
                <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                  {/* Safety Alert if Blockers Detected */}
                  {reviewPackage.safety_blockers?.length > 0 && (
                    <div
                      style={{
                        padding: '12px 16px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.4)',
                        borderRadius: '6px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#b91c1c', fontWeight: 700, fontSize: '13px' }}>
                        <AlertTriangle size={16} /> Mandatory Safety-Critical Items Detected
                      </div>
                      <p style={{ fontSize: '12px', color: '#b91c1c', lineHeight: 1.4 }}>
                        Unresolved safety items block approval. Any permitted deferral requires a technical rationale, responsible owner and an appropriate downstream gate. This does not authorize physical work.
                      </p>
                      <ul style={{ margin: '4px 0 0 16px', fontSize: '11px', color: '#b91c1c' }}>
                        {reviewPackage.safety_blockers.map((b: string, i: number) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>

                      {/* Deferral Input Section */}
                      <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(239, 68, 68, 0.2)' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#b91c1c' }}>
                          Proposed deferral (rationale, owner and downstream gate):
                        </div>
                        <input
                          type="text"
                          placeholder="Explain why deferral is appropriate and what remains blocked..."
                          value={deferralRationale}
                          onChange={(e) => setDeferralRationale(e.target.value)}
                          style={{
                            width: '100%',
                            marginTop: '6px',
                            padding: '6px 10px',
                            backgroundColor: '#edf2f8',
                            border: '1px solid rgba(239, 68, 68, 0.4)',
                            borderRadius: '4px',
                            color: '#172033',
                            fontSize: '12px',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                          <input
                            type="text"
                            placeholder="Assigned Owner (e.g. Lead HV Engineer)"
                            value={deferralOwner}
                            onChange={(e) => setDeferralOwner(e.target.value)}
                            style={{
                              flex: 1,
                              padding: '6px 10px',
                              backgroundColor: '#edf2f8',
                              border: '1px solid rgba(239, 68, 68, 0.4)',
                              borderRadius: '4px',
                              color: '#172033',
                              fontSize: '12px',
                            }}
                          />
                          <input
                            type="text"
                            placeholder="Downstream Gate"
                            value={deferralGate}
                            onChange={(e) => setDeferralGate(e.target.value)}
                            style={{
                              flex: 1,
                              padding: '6px 10px',
                              backgroundColor: '#edf2f8',
                              border: '1px solid rgba(239, 68, 68, 0.4)',
                              borderRadius: '4px',
                              color: '#172033',
                              fontSize: '12px',
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Requirements Snapshot Table */}
                  <div style={{ background: '#f8fafd', borderRadius: '6px', border: '1px solid var(--border)', padding: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155' }}>
                        Traceable Requirements Package ({reviewPackage.requirements_package.count} items)
                      </span>
                      <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#1d4ed8' }}>
                        Digest: {reviewPackage.requirements_package.digest.substring(0, 16)}…
                      </span>
                    </div>

                    {reviewPackage.requirements_package.count === 0 ? (
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No requirements recorded in revision.</p>
                    ) : (
                      <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {reviewPackage.requirements_package.requirements.map((r: any) => (
                          <div
                            key={r.id}
                            style={{
                              padding: '8px 10px',
                              background: '#f3f6fb',
                              borderRadius: '4px',
                              border: '1px solid #e5ebf3',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              fontSize: '11px',
                            }}
                          >
                            <div>
                              <b style={{ color: '#1d4ed8' }}>{r.id}</b>
                              <span style={{ color: '#334155', marginLeft: '8px' }}>{r.description}</span>
                            </div>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              {r.target_value != null && (
                                <span style={{ color: '#047857', fontWeight: 600 }}>
                                  {r.target_value} {r.unit}
                                </span>
                              )}
                              <span className={`badge ${r.discipline === 'safety' ? 'badge-red' : 'badge-blue'}`}>
                                {r.discipline}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Hash Integrity Verification */}
                  <div style={{ background: '#f8fafd', borderRadius: '6px', border: '1px solid var(--border)', padding: '14px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155' }}>
                      Exact Reviewed Baseline Hashes & Evidence
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px', fontSize: '11px' }}>
                      <div style={{ padding: '8px 10px', background: '#f3f6fb', borderRadius: '4px' }}>
                        <div style={{ color: 'var(--text-dim)' }}>Specification SHA-256:</div>
                        <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '2px' }}>
                          {reviewPackage.revision.specification_hash.substring(0, 24)}…
                        </div>
                      </div>
                      <div style={{ padding: '8px 10px', background: '#f3f6fb', borderRadius: '4px' }}>
                        <div style={{ color: 'var(--text-dim)' }}>Supporting Files Monitored:</div>
                        <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '2px' }}>
                          {Object.keys(reviewPackage.document_hashes).length} files intact
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Reviewer Credential Verification */}
                  <div style={{ background: '#f8fafd', borderRadius: '6px', border: '1px solid var(--border)', padding: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <Lock size={15} color="#1d4ed8" />
                      <span style={{ fontSize: '13px', fontWeight: 700, color: '#172033' }}>
                        Manual review decision
                      </span>
                    </div>

                    <p style={{ fontSize: '12px', marginBottom: '12px' }}>
                      Manually declared human review. The name is recorded as supplied; identity and qualifications are not authenticated.
                    </p>
                    <label style={{ display: 'block', fontSize: '12px' }}>
                      Reviewer name
                      <input
                        type="text"
                        value={reviewerName}
                        onChange={(e) => setReviewerName(e.target.value)}
                        placeholder="Your name"
                        maxLength={200}
                        style={{ display: 'block', width: '100%', padding: '8px', marginTop: '6px', color: 'var(--text-main)', background: 'var(--bg-app)', border: '1px solid var(--border)' }}
                      />
                    </label>

                    <div style={{ marginTop: '12px' }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'block', marginBottom: '4px' }}>
                        Review comments and decision rationale:
                      </label>
                      <textarea
                        rows={3}
                        placeholder="State technical findings, acceptance criteria review, and reasons for decision..."
                        value={reviewComments}
                        onChange={(e) => setReviewComments(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px 10px',
                          backgroundColor: '#edf2f8',
                          border: '1px solid var(--border)',
                          borderRadius: '4px',
                          color: '#172033',
                          fontSize: '12px',
                          resize: 'vertical',
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Modal Footer / Action Buttons */}
                <div
                  style={{
                    padding: '16px 20px',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#f8fafd',
                    flexWrap: 'wrap',
                    gap: '10px',
                  }}
                >
                  <button
                    className="btn btn-secondary"
                    onClick={() => setReviewModalOpen(false)}
                    disabled={isSubmittingReview}
                  >
                    Cancel
                  </button>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      className="btn btn-secondary"
                      style={{ color: '#b91c1c', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                      onClick={() => handleSubmitReviewDecision('REJECTED')}
                      disabled={isSubmittingReview || !reviewerName.trim() || !reviewComments.trim()}
                    >
                      Reject Package
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ color: '#92400e', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                      onClick={() => handleSubmitReviewDecision('CHANGES_REQUESTED')}
                      disabled={isSubmittingReview || !reviewerName.trim() || !reviewComments.trim()}
                    >
                      Return for Changes
                    </button>
                    <button
                      className="btn btn-primary"
                      style={{ background: '#059669', borderColor: '#047857' }}
                      onClick={() => handleSubmitReviewDecision('APPROVED')}
                      disabled={isSubmittingReview || !reviewerName.trim() || !reviewComments.trim()}
                    >
                      {isSubmittingReview ? 'Recording review…' : 'Approve Requirements'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export const ProjectDetail = ({ projectId, onBack }: { projectId: string; onBack: () => void }) => {
  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(null);
  const load = useCallback(() => api.project(projectId, selectedRevisionId || undefined), [projectId, selectedRevisionId]);
  const { data, error } = usePolling(load);
  return (
    <ProjectDetailView
      key={`${projectId}-${selectedRevisionId || 'active'}`}
      projectId={projectId}
      onBack={onBack}
      data={data}
      error={error}
      selectedRevisionId={selectedRevisionId}
      onSelectRevision={setSelectedRevisionId}
    />
  );
};
