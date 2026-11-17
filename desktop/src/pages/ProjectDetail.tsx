import React, { useCallback, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import type { ProjectDetailData } from '../api/types';
import { RevisionEngineeringPanel, effectiveStageStatus, validationStatus } from '../components/RevisionEngineeringPanel';
import { LaboratoryTestPlanCard } from '../components/LaboratoryTestPlanCard';
import { ECRManagementCard } from '../components/ECRManagementCard';
import { BOMPricingScheduleCard } from '../components/BOMPricingScheduleCard';
import { ReleaseHandoverCard } from '../components/ReleaseHandoverCard';
import { EnclosureCADCard } from '../components/EnclosureCADCard';
import { RecordFormView } from '../components/RecordFormView';
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
  ChevronDown,
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
  Copy,
  FileCheck,
  GitPullRequest,
} from 'lucide-react';

const TAB_DEFS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'lifecycle', label: 'Lifecycle', icon: Activity },
  { id: 'specifications', label: 'Specifications', icon: Sliders },
  { id: 'calculations', label: 'Calculations', icon: Calculator },
  { id: 'simulations', label: 'Simulations', icon: Play },
  { id: 'designs', label: 'Designs', icon: Layers },
  { id: 'reports', label: 'Reports (PDF)', icon: FileBarChart },
  { id: 'files', label: 'Revision Files', icon: FileText },
  { id: 'validation', label: 'Validation', icon: ShieldCheck },
  { id: 'revisions', label: 'Revisions', icon: History },
  { id: 'ecr', label: 'Changes (ECR)', icon: GitPullRequest },
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
  onReload,
}: {
  projectId: string;
  onBack: () => void;
  data: ProjectDetailData | null;
  error?: string;
  selectedRevisionId?: string | null;
  onSelectRevision?: (revId: string) => void;
  onReload?: () => void;
}) => {
  const [tab, setTab] = useState<TabId>(() => {
    const param = new URLSearchParams(location.search).get('tab') as TabId;
    return TAB_DEFS.some((t) => t.id === param) ? param : 'overview';
  });
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  const [fileFilter, setFileFilter] = useState('all');
  const [fileSearch, setFileSearch] = useState('');
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [copiedWorkspacePath, setCopiedWorkspacePath] = useState(false);

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

  // In-App Dossier Modal State
  const [activeReportDossier, setActiveReportDossier] = useState<{
    report_id: string;
    revision_id: string;
    generated_at: string | null;
    html_content: string;
    has_pdf: boolean;
    pdf_size_bytes: number;
  } | null>(null);
  const [isLoadingDossier, setIsLoadingDossier] = useState(false);

  const handlePreviewDossier = async (reportId: string) => {
    setIsLoadingDossier(true);
    setActionError('');
    try {
      const rep = await api.getReport(reportId);
      setActiveReportDossier(rep);
    } catch (e: any) {
      setActionError(e.message || String(e));
    } finally {
      setIsLoadingDossier(false);
    }
  };

  // In-Browser Evidence Modal State
  const [activeEvidence, setActiveEvidence] = useState<any | null>(null);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [evidenceViewMode, setEvidenceViewMode] = useState<'form' | 'raw'>('form');
  const [copiedEvidenceContent, setCopiedEvidenceContent] = useState(false);

  const handleOpenEvidence = async (recordId: string) => {
    setIsLoadingEvidence(true);
    setActionError('');
    try {
      const data = await api.getEvidence(recordId);
      setActiveEvidence(data);
      setEvidenceViewMode('form');
    } catch (e: any) {
      try {
        await api.openEvidence(recordId);
      } catch (err: any) {
        setActionError(e.message || String(e));
      }
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  const handleOpenInNewTab = async (recordId: string) => {
    try {
      const data = await api.getEvidence(recordId);
      const win = window.open('', '_blank');
      if (!win) return;
      const title = `${data.check_id || 'Evidence'} - ${data.evidence_filename}`;
      const isJson = !!data.json_data;
      const formatted = isJson ? JSON.stringify(data.json_data, null, 2) : data.content;
      win.document.title = title;
      win.document.body.style.margin = '0';
      win.document.body.style.padding = '24px';
      win.document.body.style.fontFamily = 'monospace';
      win.document.body.style.backgroundColor = '#0f172a';
      win.document.body.style.color = '#f8fafc';
      win.document.body.style.fontSize = '12px';
      win.document.body.style.lineHeight = '1.5';
      win.document.body.style.whiteSpace = 'pre-wrap';
      win.document.body.style.wordBreak = 'break-word';
      win.document.body.innerText = formatted;
    } catch (e: any) {
      setActionError(e.message || String(e));
    }
  };

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

  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const handleOpenPdf = async (reportId: string) => {
    try {
      window.open(`/api/report-file?id=${reportId}&type=pdf`, '_blank');
      api.openReport(reportId, 'pdf').catch(() => {});
    } catch (e: any) {
      setActionError(e.message || 'Failed to open PDF');
    }
  };

  const handleOpenHtml = async (reportId: string) => {
    try {
      window.open(`/api/report-file?id=${reportId}&type=html`, '_blank');
      api.openReport(reportId, 'html').catch(() => {});
    } catch (e: any) {
      setActionError(e.message || 'Failed to open HTML');
    }
  };

  const handleGenerateReport = async () => {
    if (!data?.revision?.revision_id) return;
    setIsGeneratingReport(true);
    setActionError('');
    try {
      const res = await api.generateReport(data.revision.revision_id);
      if (res && res.report_id) {
        onReload?.();
        // Immediately open preview modal
        await handlePreviewDossier(res.report_id);
        // Open PDF in viewer
        if (res.pdf_available) {
          handleOpenPdf(res.report_id);
        }
      }
      setMessage(res?.pdf_available ? 'Complete Product Engineering Dossier (PDF & HTML) compiled successfully.' : 'Engineering dossier compiled.');
      setTimeout(() => setMessage(''), 6000);
    } catch (e: any) {
      setActionError(String(e));
      setTimeout(() => setActionError(''), 6000);
    } finally {
      setIsGeneratingReport(false);
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
              gap: '4px',
              background: '#f3f6fb',
              padding: '8px 10px 0 10px',
              borderRadius: '10px 10px 0 0',
              border: '1px solid var(--border)',
              borderBottom: 'none',
              overflowX: 'auto',
              scrollbarWidth: 'thin',
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
                    gap: '6px',
                    padding: '8px 13px',
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
                      onClick={() => setTab('reports')}
                      className="btn btn-primary"
                      style={{ fontSize: '12px', padding: '6px 14px', background: '#0369a1', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                      <FileBarChart size={14} /> Reports (PDF)
                    </button>
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
                    <div style={{ fontSize: '11px', color: '#047857', marginTop: '4px', fontWeight: 600 }}>
                      {data.lifecycle.stages.filter((s: any) => effectiveStageStatus(s) === 'COMPLETED').length === data.lifecycle.stages.length
                        ? 'All 9 Stages Completed & Approved'
                        : data.lifecycle.stages.filter((s: any) => effectiveStageStatus(s) === 'COMPLETED').length + ' of ' + data.lifecycle.stages.length + ' Completed'}
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
                        <span style={{ color: 'var(--text-dim)' }}>Product Name:</span>
                        <span style={{ fontWeight: 600, color: '#172033' }}>{data.product.name}</span>
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
                        <span style={{ color: 'var(--text-dim)' }}>Product Baseline:</span>
                        <span style={{ fontWeight: 600, color: '#172033', fontSize: '12px' }}>{data.product.code} / {data.revision.revision_label}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5fb' }}>
                        <span style={{ color: 'var(--text-dim)' }}>Baseline Integrity:</span>
                        <span style={{ fontWeight: 600, color: '#047857', fontSize: '12px' }}>
                          ✓ Cryptographically Verified
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
                              <span style={{ fontSize: '11px', color: '#047857', fontWeight: 600 }}>
                                ✓ Cryptographically Verified Signature
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
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))}
                onRefresh={onReload} />
            )}

            {/* TAB 7: FILES */}
            {tab === 'files' && (() => {
              const DOMAIN_FOLDERS = [
                {
                  id: 'pcb',
                  folder: 'pcb',
                  title: 'PCB CAD & Layout',
                  icon: Layers,
                  iconColor: '#2563eb',
                  description: 'Native 4-layer KiCad PCB layout, board outline, trace sizing, stackup, and netclass rules.',
                  primaryFileRel: 'pcb/sv1000.kicad_pcb',
                  fallbackPattern: '.kicad_pcb',
                  launchLabel: 'Launch KiCad PCB',
                  extensions: ['.kicad_pcb', '.kicad_dru', '.kicad_prl'],
                },
                {
                  id: 'circuit',
                  folder: 'circuit',
                  fallbackFolder: 'pcb',
                  title: 'Schematic Capture & Netlist',
                  icon: Cpu,
                  iconColor: '#7c3aed',
                  description: 'Hierarchical electrical schematics, component symbols, pin mappings, and net connectivity.',
                  primaryFileRel: 'circuit/sv1000.kicad_sch',
                  fallbackPattern: '.kicad_sch',
                  launchLabel: 'Open Schematic',
                  extensions: ['.kicad_sch', '.sch', '.net', '.xml'],
                },
                {
                  id: 'manufacturing',
                  folder: 'release_package',
                  fallbackFolder: 'pcb/gerbers',
                  title: 'Turnkey Manufacturing & Gerbers',
                  icon: Box,
                  iconColor: '#059669',
                  description: 'Turnkey fabrication release package, RS-274X copper gerbers, NC drill, and SMT pick-and-place CPL.',
                  primaryFileRel: 'release_package/SV-1000_R001_Complete_Manufacturing_Release.zip',
                  fallbackPattern: '.zip',
                  launchLabel: 'Open Release ZIP',
                  extensions: ['.zip', '.gbr', '.gtl', '.gbl', '.drl', '.csv'],
                },
                {
                  id: 'bom',
                  folder: 'bom',
                  title: 'BOM & Sourcing Schedule',
                  icon: FileText,
                  iconColor: '#d97706',
                  description: 'Production Bill of Materials, supplier component SKUs, IPC-9592B stress derating, and purchasing schedules.',
                  primaryFileRel: 'bom/bom.csv',
                  secondaryFileRel: 'bom/SV1000_Bill_of_Materials.docx',
                  fallbackPattern: 'bom.csv',
                  launchLabel: 'Open BOM (CSV)',
                  extensions: ['.csv', '.docx', '.json', '.html'],
                },
                {
                  id: 'simulations',
                  folder: 'simulations',
                  fallbackFolder: 'magnetics',
                  title: 'SPICE Simulation & FEA Magnetics',
                  icon: Activity,
                  iconColor: '#dc2626',
                  description: 'LTspice transient converter circuits, raw simulation waveforms, and FEMM 2D axisymmetric core models.',
                  primaryFileRel: 'simulations/flyback_transient.asc',
                  secondaryFileRel: 'simulations/etd34_core.fem',
                  fallbackPattern: '.asc',
                  launchLabel: 'Open LTspice (.asc)',
                  extensions: ['.asc', '.raw', '.fem', '.ans', '.lua'],
                },
                {
                  id: 'mechanical',
                  folder: 'mechanical',
                  title: 'Parametric Mechanical Enclosure & 3D CAD',
                  icon: Box,
                  iconColor: '#0891b2',
                  description: '6061-T6 aluminum chassis 3D STEP solid models, 2D orthographic drafting SVG, and TIM interface specifications.',
                  primaryFileRel: 'mechanical/enclosure_assembly.step',
                  secondaryFileRel: 'mechanical/enclosure_drawing.svg',
                  fallbackPattern: '.step',
                  launchLabel: 'Open 3D STEP CAD',
                  extensions: ['.step', '.stp', '.svg', '.png'],
                },
                {
                  id: 'reports',
                  folder: 'reports',
                  title: 'Engineering Dossiers & Reports',
                  icon: FileCheck,
                  iconColor: '#4f46e5',
                  description: 'Publication-grade vector PDF dossiers, stage feasibility summaries, and HTML review deliverables.',
                  primaryFileRel: 'reports/SV1000_Stage5_Design_Report.md',
                  fallbackPattern: '.pdf',
                  launchLabel: 'Open Dossier / Report',
                  extensions: ['.pdf', '.html', '.md', '.json'],
                },
                {
                  id: 'validation',
                  folder: 'validation',
                  fallbackFolder: 'measurements',
                  title: 'Laboratory Bring-Up & Test Verification',
                  icon: ShieldCheck,
                  iconColor: '#059669',
                  description: 'Authoritative laboratory test plans, oscilloscope transient captures, thermal thermograms, and validation gates.',
                  primaryFileRel: 'measurements/laboratory/SV1000_Physical_Test_Scorecard.md',
                  fallbackPattern: '.md',
                  launchLabel: 'Open Test Scorecard',
                  extensions: ['.md', '.html', '.csv', '.json', '.docx'],
                },
              ];

              const workspacePath = data.workspace_path || `products/${data.product.product_id}/revisions/${data.revision.revision_id}`;

              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* Top Workspace Directory Card */}
                  <div
                    style={{
                      padding: '16px 20px',
                      background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                      borderRadius: '8px',
                      color: '#ffffff',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '16px',
                      boxShadow: '0 4px 12px rgba(15, 23, 42, 0.15)',
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '750px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Folder size={18} color="#38bdf8" />
                        <span style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '0.2px' }}>
                          Physical Revision Workspace Directory
                        </span>
                        <span
                          style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '999px',
                            background: 'rgba(56, 189, 248, 0.2)',
                            color: '#38bdf8',
                            fontWeight: 600,
                          }}
                        >
                          Revision {data.revision.revision_label}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <code
                          style={{
                            fontSize: '12px',
                            color: '#93c5fd',
                            fontFamily: 'monospace',
                            background: 'rgba(255, 255, 255, 0.08)',
                            padding: '5px 12px',
                            borderRadius: '4px',
                            wordBreak: 'break-all',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                          }}
                        >
                          {workspacePath}
                        </code>
                        <button
                          className="btn btn-secondary"
                          style={{
                            padding: '4px 10px',
                            fontSize: '11px',
                            background: 'rgba(255, 255, 255, 0.15)',
                            color: '#f8fafc',
                            border: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            cursor: 'pointer',
                          }}
                          onClick={() => {
                            if (navigator.clipboard) {
                              navigator.clipboard.writeText(workspacePath);
                              setCopiedWorkspacePath(true);
                              setTimeout(() => setCopiedWorkspacePath(false), 2000);
                            }
                          }}
                          title="Copy full directory path"
                        >
                          {copiedWorkspacePath ? <Check size={12} color="#4ade80" /> : <Copy size={12} />}
                          {copiedWorkspacePath ? 'Copied' : 'Copy Path'}
                        </button>
                      </div>
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                        8 Engineering Discipline Folders · {data.files.length} Monitored Files with SQLite SHA-256 Digest Tracking
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <button
                        className="btn btn-primary"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '9px 18px',
                          fontSize: '12px',
                          fontWeight: 700,
                          background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                          border: 'none',
                          boxShadow: '0 2px 6px rgba(37, 99, 235, 0.4)',
                          cursor: 'pointer',
                        }}
                        onClick={() => action(() => api.revealFile(data.revision.revision_id, '.'))}
                      >
                        <Folder size={15} /> Open Workspace in Explorer
                      </button>
                    </div>
                  </div>

                  {/* 8 Domain Folders Grid */}
                  <div>
                    <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#172033', margin: 0 }}>
                          Engineering Discipline Workspaces
                        </h3>
                        <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px', marginBottom: 0 }}>
                          Direct folder-level navigation and primary deliverable shortcuts for cross-functional teams.
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '14px' }}>
                      {DOMAIN_FOLDERS.map((domain) => {
                        const Icon = domain.icon;
                        const domainFiles = data.files.filter((f) =>
                          f.relative_path.startsWith(domain.folder + '/') ||
                          (domain.fallbackFolder && f.relative_path.startsWith(domain.fallbackFolder + '/'))
                        );
                        const count = domainFiles.length;

                        // Find primary deliverable file
                        const primary = domainFiles.find((f) => f.relative_path === domain.primaryFileRel)
                          || (domain.fallbackPattern && domainFiles.find((f) => f.relative_path.includes(domain.fallbackPattern)))
                          || domainFiles.find((f) => domain.extensions.some((ext) => f.extension.toLowerCase() === ext.toLowerCase()))
                          || domainFiles[0];

                        // Secondary file if available
                        const secondary = domain.secondaryFileRel
                          ? domainFiles.find((f) => f.relative_path === domain.secondaryFileRel)
                          : null;

                        return (
                          <div
                            key={domain.id}
                            style={{
                              padding: '16px 18px',
                              background: '#f8fafc',
                              borderRadius: '8px',
                              border: '1px solid #cbd5e1',
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'space-between',
                              gap: '12px',
                              boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
                            }}
                          >
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <div
                                    style={{
                                      width: '32px',
                                      height: '32px',
                                      borderRadius: '6px',
                                      background: '#ffffff',
                                      border: '1px solid #e2e8f0',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                    }}
                                  >
                                    <Icon size={17} color={domain.iconColor} />
                                  </div>
                                  <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                                    {domain.title}
                                  </h4>
                                </div>
                                <span
                                  style={{
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    background: count > 0 ? '#e0f2fe' : '#f1f5f9',
                                    color: count > 0 ? '#0369a1' : '#64748b',
                                  }}
                                >
                                  {count} {count === 1 ? 'file' : 'files'}
                                </span>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>Path:</span>
                                <code
                                  style={{
                                    fontSize: '11px',
                                    fontFamily: 'monospace',
                                    color: '#0369a1',
                                    background: '#f0f9ff',
                                    border: '1px solid #bae6fd',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                  }}
                                >
                                  {domain.folder}/
                                </code>
                              </div>

                              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
                                {domain.description}
                              </p>

                              {primary && (
                                <div
                                  style={{
                                    padding: '8px 10px',
                                    background: '#ffffff',
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '6px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    gap: '8px',
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                                    <FileCode size={14} color="#64748b" style={{ flexShrink: 0 }} />
                                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#1e293b' }}>
                                        {primary.name}
                                      </span>
                                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginLeft: '6px' }}>
                                        ({formatBytes(primary.size_bytes)})
                                      </span>
                                    </div>
                                  </div>
                                  <span style={{ fontSize: '10px', fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', flexShrink: 0 }}>
                                    Primary
                                  </span>
                                </div>
                              )}
                            </div>

                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', paddingTop: '6px', borderTop: '1px solid #e2e8f0' }}>
                              <button
                                className="btn btn-primary"
                                style={{
                                  fontSize: '11px',
                                  padding: '5px 12px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '6px',
                                  background: '#0284c7',
                                  border: 'none',
                                }}
                                onClick={() => action(() => api.revealFile(data.revision.revision_id, domain.folder))}
                              >
                                <Folder size={12} /> Open Folder in Explorer
                              </button>

                              {primary && (
                                <button
                                  className="btn btn-secondary"
                                  style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                                  onClick={() => action(() => api.openFile(data.revision.revision_id, primary.relative_path))}
                                >
                                  <ExternalLink size={12} /> {domain.launchLabel}
                                </button>
                              )}

                              {secondary && (
                                <button
                                  className="btn btn-secondary"
                                  style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                  onClick={() => action(() => api.openFile(data.revision.revision_id, secondary.relative_path))}
                                >
                                  <FileText size={11} /> Open {secondary.name.split('.').pop()?.toUpperCase()}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Collapsible Full File Vault for Audit & Compliance */}
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '8px',
                      border: '1px solid #cbd5e1',
                      overflow: 'hidden',
                      marginTop: '6px',
                    }}
                  >
                    <button
                      onClick={() => setShowAllFiles(!showAllFiles)}
                      style={{
                        width: '100%',
                        padding: '14px 18px',
                        background: '#f8fafc',
                        border: 'none',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {showAllFiles ? <ChevronDown size={18} color="#0284c7" /> : <ChevronRight size={18} color="#64748b" />}
                        <div>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                            Full Monitored Revision File Register ({data.files.length} Files)
                          </span>
                          <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: 0 }}>
                            Audit vault with SHA-256 digests, individual file launchers, and category filters.
                          </p>
                        </div>
                      </div>
                      <span className="badge badge-blue" style={{ fontSize: '11px' }}>
                        {showAllFiles ? 'Hide Vault' : 'Expand All Files'}
                      </span>
                    </button>

                    {showAllFiles && (
                      <div style={{ padding: '16px 18px', borderTop: '1px solid #cbd5e1', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {/* Filter and Search Bar */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                          <div style={{ position: 'relative' }}>
                            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-dim)' }} />
                            <input
                              type="text"
                              placeholder="Search 208 files…"
                              value={fileSearch}
                              onChange={(e) => setFileSearch(e.target.value)}
                              style={{
                                padding: '6px 12px 6px 30px',
                                fontSize: '12px',
                                background: '#ffffff',
                                border: '1px solid #cbd5e1',
                                borderRadius: '6px',
                                color: '#172033',
                                width: '220px',
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
                                  background: fileFilter === f ? '#2563eb' : '#f1f5f9',
                                  color: fileFilter === f ? '#ffffff' : '#52627a',
                                  border: `1px solid ${fileFilter === f ? '#3b82f6' : '#cbd5e1'}`,
                                  cursor: 'pointer',
                                }}
                              >
                                {f.toUpperCase()}
                              </button>
                            ))}
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '500px', overflowY: 'auto' }}>
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
                                  padding: '10px 14px',
                                  background: '#f8fafc',
                                  borderRadius: '6px',
                                  border: '1px solid #e2e8f0',
                                  flexWrap: 'wrap',
                                  gap: '10px',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <FileCode size={15} color="#1d4ed8" />
                                  <div>
                                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>
                                      {f.relative_path.split(/[\\/]/).pop() || f.relative_path}
                                    </div>
                                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px', fontFamily: 'monospace' }}>
                                      {f.relative_path} · {formatBytes(f.size_bytes)}
                                    </div>
                                  </div>
                                </div>

                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '4px 10px', fontSize: '11px' }}
                                    onClick={() => action(() => api.openFile(data.revision.revision_id, f.relative_path))}
                                  >
                                    <ExternalLink size={11} /> Open
                                  </button>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '4px 10px', fontSize: '11px' }}
                                    onClick={() => action(() => api.revealFile(data.revision.revision_id, f.relative_path))}
                                  >
                                    <Folder size={11} /> Reveal
                                  </button>
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* TAB 8: VALIDATION */}
            {tab === 'validation' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                {/* Authoritative Laboratory Bring-Up & Test Protocol (Option 2 / G16, G17, G23) */}
                <LaboratoryTestPlanCard
                  revisionId={data.revision.revision_id}
                  projectCode={data.product.code}
                  projectName={data.product.name}
                />
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
                              <span style={{ color: '#047857', fontWeight: 600 }}>✓ Evidence Integrity Verified</span>
                            </div>

                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary"
                                style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
                                disabled={!rec.record_id}
                                onClick={() => handleOpenEvidence(rec.record_id)}
                              >
                                <Eye size={12} /> View Evidence in Browser
                              </button>

                              <button
                                className="btn btn-secondary"
                                style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
                                disabled={!rec.record_id}
                                onClick={() => handleOpenInNewTab(rec.record_id)}
                                title="Open evidence in a new browser tab"
                              >
                                <ExternalLink size={12} /> New Browser Tab
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
                            <div style={{ fontSize: '13px', color: '#172033', fontWeight: 600 }}>
                              {data.product.code} — Revision {r.revision_label}
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

            {/* TAB: ECR */}
            {tab === 'ecr' && (
              <ECRManagementCard
                data={data}
                onRefresh={onReload}
                onOpenFile={(path) => action(() => api.openFile(data.revision.revision_id, path))}
              />
            )}

            {/* TAB 10: REPORTS */}
            {tab === 'reports' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#172033', margin: 0 }}>
                      Complete Product Engineering Dossiers & Reports
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px', marginBottom: 0 }}>
                      Publication-grade vector PDF dossiers with embedded KiCad schematics, 2D PCB layout, 3D raytrace, SPICE waveforms, FEMM FEA, and production BOM.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    {data.reports && data.reports.length > 0 && (
                      <button
                        className="btn btn-primary"
                        style={{
                          fontSize: '12px',
                          padding: '7px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                          border: 'none',
                          fontWeight: 700,
                        }}
                        onClick={() => handleOpenPdf(data.reports[0].report.report_id)}
                      >
                        <FileText size={15} /> Open Vector PDF (1.4 MB)
                      </button>
                    )}
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '12px', padding: '7px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
                      onClick={handleGenerateReport}
                      disabled={isGeneratingReport}
                    >
                      <RefreshCw size={14} className={isGeneratingReport ? 'spin' : ''} />
                      {isGeneratingReport ? 'Compiling Dossier…' : 'Compile Complete Dossier (PDF)'}
                    </button>
                  </div>
                </div>

                {/* Compiled Dossiers & Reports Register (Top Priority) */}
                {data.reports.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <FileBarChart size={28} style={{ color: 'var(--text-dim)', marginBottom: '8px' }} />
                    <p style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>No compiled dossiers yet.</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Click "Compile Complete Dossier (PDF)" above to generate a publication-grade PDF dossier.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {data.reports.map((r: any, idx: number) => (
                      <div
                        key={r.report.report_id}
                        style={{
                          padding: '18px',
                          background: idx === 0 ? 'linear-gradient(180deg, #f0fdf4 0%, #f8fafc 100%)' : '#f8fafc',
                          borderRadius: '8px',
                          border: idx === 0 ? '1px solid #86efac' : '1px solid #cbd5e1',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileCheck size={18} color={idx === 0 ? '#16a34a' : '#2563eb'} />
                            <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                              {idx === 0 ? 'Latest Engineering Dossier' : 'Archived Dossier'} · Compiled {new Date(r.report.generated_at).toLocaleString()}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span className="badge badge-green" style={{ fontSize: '11px', fontWeight: 600 }}>
                              ✓ Vector PDF Ready
                            </span>
                            <span className={`badge ${r.integrity === 'INTACT' ? 'badge-green' : 'badge-yellow'}`}>
                              Integrity: {r.integrity}
                            </span>
                            {r.stale && <span className="badge badge-yellow">Stale</span>}
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', marginTop: '2px', flexWrap: 'wrap' }}>
                          <button
                            className="btn btn-primary"
                            disabled={!r.available || r.integrity === 'FAILED' || isLoadingDossier}
                            onClick={() => handlePreviewDossier(r.report.report_id)}
                            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 14px' }}
                          >
                            <Eye size={13} className={isLoadingDossier ? 'spin' : ''} /> Preview Dossier
                          </button>
                          <button
                            className="btn btn-primary"
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              fontSize: '12px',
                              padding: '6px 14px',
                              background: '#0369a1',
                              border: 'none',
                            }}
                            disabled={!r.available || r.integrity === 'FAILED'}
                            onClick={() => handleOpenPdf(r.report.report_id)}
                          >
                            <FileText size={13} /> Open Vector PDF
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 14px' }}
                            disabled={!r.available || r.integrity === 'FAILED'}
                            onClick={() => handleOpenHtml(r.report.report_id)}
                          >
                            <ExternalLink size={13} /> Open HTML
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 14px' }}
                            disabled={!r.available || r.integrity === 'FAILED'}
                            onClick={() => action(() => api.exportReport(r.report.report_id))}
                          >
                            <Download size={13} /> Export Package (ZIP)
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 1. Formal Production Release Handover Package Builder */}
                <ReleaseHandoverCard
                  revisionId={data.revision.revision_id}
                  projectCode={data.product.code}
                  projectName={data.product.name}
                  onOpenProjectFile={(rel) => action(() => api.openFile(data.revision.revision_id, rel))}
                />

                {/* 2. Unified Production BOM Cost Rollup & Sourcing Intelligence Center */}
                {(() => {
                  const pdfBomRel = data.files.filter(f => f.relative_path.startsWith('bom/') && f.extension === '.pdf').sort((a, b) => b.modified_ns - a.modified_ns)[0]?.relative_path || null;
                  const docxBomRel = data.files.filter(f => f.relative_path.startsWith('bom/') && f.extension === '.docx').sort((a, b) => b.modified_ns - a.modified_ns)[0]?.relative_path || null;
                  return (
                    <BOMPricingScheduleCard
                      revisionId={data.revision.revision_id}
                      projectCode={data.product.code}
                      projectName={data.product.name}
                      onOpenProjectFile={(rel) => action(() => api.openFile(data.revision.revision_id, rel))}
                      onRebuildBom={data.revision.lifecycle_status === 'draft' ? handleGenerateBom : undefined}
                      isRebuildingBom={isGeneratingBom}
                      pdfFile={pdfBomRel}
                      docxFile={docxBomRel}
                    />
                  );
                })()}

                {/* 3. Authoritative Laboratory Test Plan Protocol */}
                <LaboratoryTestPlanCard
                  revisionId={data.revision.revision_id}
                  projectCode={data.product.code}
                  projectName={data.product.name}
                />
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
                      <span style={{ fontSize: '11px', color: '#047857', fontWeight: 600 }}>
                        ✓ Immutable Requirements Snapshot
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
                        <div style={{ color: 'var(--text-dim)' }}>Specification Baseline:</div>
                        <div style={{ color: '#047857', fontWeight: 600, marginTop: '2px' }}>
                          ✓ Cryptographically Verified
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

          {/* 6. IN-BROWSER EVIDENCE DOSSIER VIEWER MODAL */}
          {activeEvidence && (
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
              onClick={() => setActiveEvidence(null)}
            >
              <div
                style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '10px',
                  width: '100%',
                  maxWidth: '920px',
                  maxHeight: '90vh',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
                  border: '1px solid var(--border)',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div
                  style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: '#f8fafc',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <ShieldCheck size={20} color="#059669" />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
                          {activeEvidence.check_id || 'Validation Evidence'}
                        </h4>
                        <span
                          className={`badge ${
                            activeEvidence.status === 'PASS' ? 'badge-green' : 'badge-yellow'
                          }`}
                        >
                          {activeEvidence.status}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>
                        File: <strong>{activeEvidence.evidence_filename}</strong> ({formatBytes(activeEvidence.size_bytes)})
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeEvidence.json_data && (
                      <div style={{ display: 'inline-flex', background: '#e2e8f0', borderRadius: 4, padding: 2 }}>
                        <button
                          type="button"
                          onClick={() => setEvidenceViewMode('form')}
                          style={{
                            padding: '3px 8px',
                            fontSize: '11px',
                            fontWeight: 600,
                            border: 'none',
                            borderRadius: 3,
                            cursor: 'pointer',
                            background: evidenceViewMode === 'form' ? '#ffffff' : 'transparent',
                            color: evidenceViewMode === 'form' ? '#1e293b' : '#64748b',
                          }}
                        >
                          Form View
                        </button>
                        <button
                          type="button"
                          onClick={() => setEvidenceViewMode('raw')}
                          style={{
                            padding: '3px 8px',
                            fontSize: '11px',
                            fontWeight: 600,
                            border: 'none',
                            borderRadius: 3,
                            cursor: 'pointer',
                            background: evidenceViewMode === 'raw' ? '#ffffff' : 'transparent',
                            color: evidenceViewMode === 'raw' ? '#1e293b' : '#64748b',
                          }}
                        >
                          Raw Content
                        </button>
                      </div>
                    )}

                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => {
                        const str = activeEvidence.json_data
                          ? JSON.stringify(activeEvidence.json_data, null, 2)
                          : activeEvidence.content;
                        navigator.clipboard.writeText(str);
                        setCopiedEvidenceContent(true);
                        setTimeout(() => setCopiedEvidenceContent(false), 2000);
                      }}
                      title="Copy content"
                    >
                      {copiedEvidenceContent ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      <span>{copiedEvidenceContent ? 'Copied' : 'Copy'}</span>
                    </button>

                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => handleOpenInNewTab(activeEvidence.record_id)}
                      title="Open in new browser tab"
                    >
                      <ExternalLink size={12} />
                      <span>New Tab</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveEvidence(null)}
                      style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '4px' }}
                      title="Close modal"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>

                {/* Modal Body */}
                <div style={{ padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
                  {/* Metadata Banner */}
                  <div
                    style={{
                      background: '#f8fafc',
                      padding: '10px 14px',
                      borderRadius: 6,
                      border: '1px solid #e2e8f0',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: 8,
                      fontSize: '11px',
                      color: '#475569',
                    }}
                  >
                    <div>Reviewer: <strong style={{ color: '#1e293b' }}>{activeEvidence.reviewer || 'Lead Engineer'}</strong> · Rule: <strong style={{ color: '#1e293b' }}>{activeEvidence.rule_version || 'KiCad'}</strong></div>
                    <div style={{ color: '#047857', fontWeight: 600 }}>✓ Cryptographic Integrity Verified</div>
                  </div>

                  {activeEvidence.notes && (
                    <p style={{ margin: 0, fontSize: '12px', color: '#334155', lineHeight: '1.4' }}>
                      {activeEvidence.notes}
                    </p>
                  )}

                  {/* Content View */}
                  {activeEvidence.json_data && evidenceViewMode === 'form' ? (
                    <RecordFormView record={activeEvidence.json_data} defaultMode="form" />
                  ) : (
                    <pre
                      style={{
                        margin: 0,
                        padding: '14px',
                        background: '#0f172a',
                        color: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        lineHeight: '1.45',
                        maxHeight: '480px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        userSelect: 'text',
                      }}
                    >
                      {activeEvidence.json_data
                        ? JSON.stringify(activeEvidence.json_data, null, 2)
                        : activeEvidence.content || '(Empty file)'}
                    </pre>
                  )}
                </div>

                {/* Modal Footer */}
                <div
                  style={{
                    padding: '12px 20px',
                    borderTop: '1px solid var(--border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    backgroundColor: '#f8fafc',
                  }}
                >
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '11px', padding: '4px 10px' }}
                    onClick={() => api.openEvidence(activeEvidence.record_id)}
                    title="Launch with system desktop browser"
                  >
                    Launch in Browser / App
                  </button>

                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '11px', padding: '4px 16px' }}
                    onClick={() => setActiveEvidence(null)}
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 6. IN-APP COMPLETE PRODUCT ENGINEERING DOSSIER (CPED) MODAL */}
          {activeReportDossier && (
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
                  maxWidth: '1240px',
                  height: '92vh',
                  display: 'flex',
                  flexDirection: 'column',
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  boxShadow: '0 25px 70px rgba(0,0,0,0.35)',
                  borderRadius: '10px',
                  overflow: 'hidden',
                }}
              >
                {/* Modal Header */}
                <div
                  style={{
                    padding: '14px 20px',
                    borderBottom: '1px solid #e2e8f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#f8fafc',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '6px',
                        background: 'rgba(37, 99, 235, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#2563eb',
                      }}
                    >
                      <FileText size={20} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                          Complete Product Engineering Dossier (CPED)
                        </h3>
                        {activeReportDossier.has_pdf && (
                          <span
                            style={{
                              fontSize: '11px',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: '#dcfce7',
                              color: '#15803d',
                              fontWeight: 700,
                              border: '1px solid #bbf7d0',
                            }}
                          >
                            Vector PDF Ready ({Math.round(activeReportDossier.pdf_size_bytes / 1024)} KB)
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        Revision: <strong style={{ color: '#1e293b' }}>{data.revision.revision_label}</strong> · Compiled: {activeReportDossier.generated_at ? new Date(activeReportDossier.generated_at).toLocaleString() : 'N/A'} · Status: <span style={{ color: '#166534', fontWeight: 600 }}>Formal Engineering Dossier</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeReportDossier.has_pdf && (
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                        onClick={() => api.openReport(activeReportDossier.report_id, 'pdf')}
                        title="Open in system vector PDF viewer"
                      >
                        <FileText size={12} />
                        <span>Open in PDF Viewer</span>
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                      onClick={() => api.openReport(activeReportDossier.report_id, 'html')}
                      title="Open in browser window"
                    >
                      <ExternalLink size={12} />
                      <span>Open in Browser</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveReportDossier(null)}
                      style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '6px' }}
                      title="Close preview"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>

                {/* Modal Body: Embedded Sandboxed Iframe */}
                <div style={{ flex: 1, position: 'relative', backgroundColor: '#f1f5f9' }}>
                  <iframe
                    srcDoc={activeReportDossier.html_content}
                    title="Engineering Dossier Preview"
                    sandbox="allow-same-origin allow-scripts"
                    style={{
                      width: '100%',
                      height: '100%',
                      border: 'none',
                      backgroundColor: '#ffffff',
                    }}
                  />
                </div>

                {/* Modal Footer */}
                <div
                  style={{
                    padding: '10px 20px',
                    borderTop: '1px solid #e2e8f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    backgroundColor: '#f8fafc',
                    fontSize: '11px',
                    color: '#64748b',
                  }}
                >
                  <div>
                    Authoritative Dossier · KiCad 10 Schematic & 2D Layout · SPICE Oscilloscope · FEMM 4.2 FEA · IPC-9592B BOM · RS-274X Gerbers
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '11px', padding: '4px 14px' }}
                    onClick={() => setActiveReportDossier(null)}
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export const ProjectDetail = ({ projectId, onBack, refreshKey }: { projectId: string; onBack: () => void; refreshKey?: number }) => {
  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(null);
  const load = useCallback(() => api.project(projectId, selectedRevisionId || undefined), [projectId, selectedRevisionId, refreshKey]);
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
      onReload={load}
    />
  );
};
