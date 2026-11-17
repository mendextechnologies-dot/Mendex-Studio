import React, { useState, useEffect, useMemo } from 'react';
import type { ProjectDetailData } from '../api/types';
import { api } from '../api/client';
import {
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RotateCcw,
  Plus,
  FileText,
  ChevronRight,
  ChevronDown,
  ShieldCheck,
  X,
  Zap,
} from 'lucide-react';

interface ECRManagementCardProps {
  data: ProjectDetailData;
  onRefresh?: () => void;
  onOpenFile?: (path: string) => void;
}

export interface ECRItem {
  ecr_id: string;
  ecr_number: string;
  title: string;
  description: string;
  reason: string;
  impact_analysis: string;
  requested_by: string;
  affected_stages?: string[];
  schematic_ops?: any[];
  status: 'DRAFT' | 'UNDER_REVIEW' | 'APPROVED' | 'IMPLEMENTED' | 'REJECTED';
  created_at?: string;
  reviewed_at?: string;
  approved_by?: string;
  review_notes?: string;
  applied_at?: string;
  applied_checkpoint?: string;
  eco_result?: any;
}

export const ECRManagementCard: React.FC<ECRManagementCardProps> = ({
  data,
  onRefresh,
}) => {
  const [ecrs, setEcrs] = useState<ECRItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Expanded ECR ID for details
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Create ECR Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newReason, setNewReason] = useState('');
  const [newImpact, setNewImpact] = useState('');
  const [newRequestedBy, setNewRequestedBy] = useState('Senior Power Electronics Design Engineer');
  const [selectedStages] = useState<string[]>([
    'calculations',
    'simulation',
    'schematic_design',
    'bom_review',
  ]);
  const [hasSchematicOps, setHasSchematicOps] = useState(true);
  const [opRef, setOpRef] = useState('R1');
  const [opField, setOpField] = useState('Value');
  const [opVal, setOpVal] = useState('20k 0.1%');
  const [opMpn, setOpMpn] = useState('ERA-6AEB203V');

  // Review Modal
  const [reviewModalEcr, setReviewModalEcr] = useState<ECRItem | null>(null);
  const [reviewerName, setReviewerName] = useState('Lead Power Systems Engineer (Human Reviewer)');
  const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REJECTED' | 'UNDER_REVIEW' | 'IMPLEMENTED'>('APPROVED');
  const [reviewNotes, setReviewNotes] = useState('Approved after electrical tolerance and creepage margin verification.');

  // Applying ECO State
  const [applyingEcrId, setApplyingEcrId] = useState<string | null>(null);
  const [ecoResults, setEcoResults] = useState<Record<string, any>>({});

  // Fetch ECRs
  const fetchECRs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listECRs({
        product_id: data.product.product_id,
        revision_id: data.revision.revision_id,
      });
      setEcrs(res || []);
      if (res && res.length > 0 && !expandedId) {
        setExpandedId(res[0].ecr_id);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to fetch ECR register');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchECRs();
  }, [data.product.product_id, data.revision.revision_id]);

  // Handle Create ECR
  const handleCreateECR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const schematic_ops = hasSchematicOps
        ? [
            { op: 'set_field', ref: opRef, field: opField, value: opVal },
            { op: 'set_field', ref: opRef, field: 'MPN', value: opMpn },
          ]
        : undefined;

      const res = await api.createECR({
        title: newTitle,
        description: newDescription,
        reason: newReason,
        impact_analysis: newImpact,
        requested_by: newRequestedBy,
        product_id: data.product.product_id,
        revision_id: data.revision.revision_id,
        affected_stages: selectedStages,
        schematic_ops,
      });

      setSuccessMessage(`Successfully created ${res.ecr_number || 'new change request'}`);
      setCreateModalOpen(false);
      // Reset form
      setNewTitle('');
      setNewDescription('');
      setNewReason('');
      setNewImpact('');
      await fetchECRs();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (e: any) {
      setError(e.message || 'Failed to create ECR');
    } finally {
      setLoading(false);
    }
  };

  // Handle Review ECR
  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewModalEcr) return;

    setLoading(true);
    setError(null);
    try {
      await api.reviewECR({
        ecr_id: reviewModalEcr.ecr_id,
        reviewer: reviewerName,
        status: reviewDecision,
        review_notes: reviewNotes,
      });

      setSuccessMessage(`ECR ${reviewModalEcr.ecr_number} status updated to ${reviewDecision}`);
      setReviewModalEcr(null);
      await fetchECRs();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (e: any) {
      setError(e.message || 'Failed to record ECR review');
    } finally {
      setLoading(false);
    }
  };

  // Handle Apply Schematic & Forward Annotate PCB
  const handleApplyECO = async (ecr: ECRItem) => {
    if (!ecr.schematic_ops || ecr.schematic_ops.length === 0) {
      setError(`ECR ${ecr.ecr_number} has no automated schematic operations defined. Complete implementation via Review / Sign-off.`);
      return;
    }
    setApplyingEcrId(ecr.ecr_id);
    setError(null);
    try {
      const res = await api.applyECRSchematic(ecr.ecr_id, reviewerName, true);
      if (res && res.success === false) {
        setError(res.error || 'Failed to apply ECO forward annotation');
        return;
      }
      setEcoResults((prev) => ({ ...prev, [ecr.ecr_id]: res }));
      setSuccessMessage(`ECO successfully applied to schematic & PCB for ${ecr.ecr_number}!`);
      await fetchECRs();
      onRefresh?.();
      setTimeout(() => setSuccessMessage(null), 6000);
    } catch (e: any) {
      setError(e.message || 'Failed to apply ECO forward annotation');
    } finally {
      setApplyingEcrId(null);
    }
  };

  // KPI metrics
  const metrics = useMemo(() => {
    const total = ecrs.length;
    const approved = ecrs.filter((e) => e.status === 'APPROVED').length;
    const implemented = ecrs.filter((e) => e.status === 'IMPLEMENTED').length;
    const underReview = ecrs.filter((e) => e.status === 'UNDER_REVIEW').length;
    const draft = ecrs.filter((e) => e.status === 'DRAFT').length;
    return { total, approved, implemented, underReview, draft };
  }, [ecrs]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'IMPLEMENTED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, background: '#f3e8ff', color: '#6b21a8', border: '1px solid #d8b4fe', fontSize: 11, fontWeight: 700 }}>
            <CheckCircle2 size={13} /> IMPLEMENTED
          </span>
        );
      case 'APPROVED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0', fontSize: 11, fontWeight: 700 }}>
            <CheckCircle2 size={13} /> APPROVED
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', fontSize: 11, fontWeight: 700 }}>
            <Clock size={13} /> UNDER REVIEW
          </span>
        );
      case 'REJECTED':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca', fontSize: 11, fontWeight: 700 }}>
            <AlertTriangle size={13} /> REJECTED
          </span>
        );
      default:
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1', fontSize: 11, fontWeight: 600 }}>
            <FileText size={13} /> DRAFT
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Hero Header Ribbon */}
      <div
        className="card"
        style={{
          background: '#ffffff',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: 20,
          boxShadow: '0 1px 3px rgba(23, 32, 51, 0.05)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                background: '#f3e8ff',
                border: '1px solid #e9d5ff',
                borderRadius: 8,
                padding: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#7e22ce',
              }}
            >
              <GitPullRequest size={24} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#0f172a' }}>
                Engineering Change Management & Forward Annotation (ECR/ECO)
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.4 }}>
                Closed-loop Engineering Change Requests, schematic modification operations, and atomic PCB forward annotation for {data.product.code}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={fetchECRs}
              disabled={loading}
              className="btn btn-outline"
              style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              <RotateCcw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              onClick={() => setCreateModalOpen(true)}
              className="btn btn-primary"
              style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              <Plus size={14} /> New Change Request
            </button>
          </div>
        </div>

        {/* Alerts & Messages */}
        {error && (
          <div
            style={{
              marginTop: 14,
              padding: '10px 14px',
              borderRadius: 6,
              background: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#b91c1c',
              fontSize: 12,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div
            style={{
              marginTop: 14,
              padding: '10px 14px',
              borderRadius: 6,
              background: '#ecfdf5',
              border: '1px solid #a7f3d0',
              color: '#047857',
              fontSize: 12,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <CheckCircle2 size={15} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* KPI Counter Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: 12,
            marginTop: 18,
            paddingTop: 16,
            borderTop: '1px solid var(--border)',
          }}
        >
          <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total ECRs</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#0f172a' }}>{metrics.total}</div>
          </div>

          <div style={{ background: '#ecfdf5', padding: '10px 14px', borderRadius: 6, border: '1px solid #a7f3d0', borderLeft: '4px solid #10b981' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#047857', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Approved</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#047857' }}>{metrics.approved}</div>
          </div>

          <div style={{ background: '#f5f3ff', padding: '10px 14px', borderRadius: 6, border: '1px solid #ddd6fe', borderLeft: '4px solid #8b5cf6' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#6b21a8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Implemented</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#7e22ce' }}>{metrics.implemented}</div>
          </div>

          <div style={{ background: '#eff6ff', padding: '10px 14px', borderRadius: 6, border: '1px solid #bfdbfe', borderLeft: '4px solid #3b82f6' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Under Review</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#1d4ed8' }}>{metrics.underReview}</div>
          </div>

          <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0', borderLeft: '4px solid #94a3b8' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Drafts</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#334155' }}>{metrics.draft}</div>
          </div>
        </div>
      </div>

      {/* ECR Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {ecrs.length === 0 ? (
          <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
            No engineering change requests recorded for this product yet. Click <strong>"New Change Request"</strong> to initiate an ECR.
          </div>
        ) : (
          ecrs.map((ecr) => {
            const isExpanded = expandedId === ecr.ecr_id;
            const eco = ecoResults[ecr.ecr_id] || ecr.eco_result;
            const isApplying = applyingEcrId === ecr.ecr_id;

            return (
              <div
                key={ecr.ecr_id}
                className="card"
                style={{
                  padding: 18,
                  borderRadius: 8,
                  border: isExpanded ? '1.5px solid #8b5cf6' : '1px solid var(--border)',
                  background: '#ffffff',
                  boxShadow: isExpanded ? '0 4px 16px rgba(139, 92, 246, 0.08)' : '0 1px 3px rgba(23, 32, 51, 0.04)',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                  <div style={{ flex: '1 1 400px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <strong style={{ fontFamily: 'monospace', fontSize: 13, fontWeight: 700, color: '#7e22ce', background: '#f5f3ff', padding: '2px 8px', borderRadius: 4, border: '1px solid #ddd6fe' }}>
                        {ecr.ecr_number}
                      </strong>
                      {getStatusBadge(ecr.status)}
                      <span style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 500 }}>
                        by <strong style={{ color: '#334155' }}>{ecr.requested_by}</strong>
                      </span>
                      {ecr.created_at && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          · {new Date(ecr.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <h4 style={{ margin: '8px 0 0 0', fontSize: 16, fontWeight: 700, color: '#0f172a' }}>
                      {ecr.title}
                    </h4>
                  </div>

                  {/* Actions Toolbar */}
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {ecr.status !== 'IMPLEMENTED' && ecr.status !== 'REJECTED' && (
                      <button
                        onClick={() => setReviewModalEcr(ecr)}
                        className="btn btn-outline"
                        style={{ fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 5 }}
                      >
                        <ShieldCheck size={13} /> Review / Sign-off
                      </button>
                    )}

                    {ecr.status === 'APPROVED' && (
                      ecr.schematic_ops && ecr.schematic_ops.length > 0 ? (
                        <button
                          onClick={() => handleApplyECO(ecr)}
                          disabled={isApplying}
                          className="btn btn-primary"
                          style={{
                            fontSize: 11,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
                            border: 'none',
                          }}
                        >
                          {isApplying ? (
                            <>
                              <RotateCcw size={13} className="animate-spin" /> Annotating PCB...
                            </>
                          ) : (
                            <>
                              <Zap size={13} /> Apply ECO to PCB
                            </>
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            setReviewModalEcr(ecr);
                            setReviewDecision('IMPLEMENTED');
                            setReviewNotes('Manual engineering verification complete; recorded as implemented.');
                          }}
                          className="btn btn-primary"
                          style={{
                            fontSize: 11,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            border: 'none',
                          }}
                          title="This ECR has no automated CAD operations; complete sign-off manually"
                        >
                          <CheckCircle2 size={13} /> Complete Sign-off
                        </button>
                      )
                    )}

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : ecr.ecr_id)}
                      className="btn btn-outline"
                      style={{ fontSize: 11, padding: '4px 8px' }}
                      title={isExpanded ? 'Collapse details' : 'Expand details'}
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                  </div>
                </div>

                {/* Description & Impact Summary */}
                <p style={{ margin: '10px 0 0 0', fontSize: 13, color: '#334155', lineHeight: 1.5 }}>
                  {ecr.description}
                </p>

                {/* Affected Lifecycle Stages */}
                {ecr.affected_stages && ecr.affected_stages.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)' }}>Affected Stages:</span>
                    {ecr.affected_stages.map((st) => (
                      <span
                        key={st}
                        style={{
                          padding: '3px 8px',
                          borderRadius: 4,
                          background: '#f1f5f9',
                          border: '1px solid #cbd5e1',
                          fontSize: 11,
                          fontFamily: 'monospace',
                          fontWeight: 600,
                          color: '#1e293b',
                        }}
                      >
                        {st}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded Details Section */}
                {isExpanded && (
                  <div
                    style={{
                      marginTop: 16,
                      paddingTop: 16,
                      borderTop: '1px solid #e2e8f0',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 14,
                    }}
                  >
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
                      <div style={{ background: '#f8fafc', padding: 14, borderRadius: 6, border: '1px solid #e2e8f0' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#1d4ed8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Technical Justification
                        </div>
                        <div style={{ fontSize: 13, color: '#0f172a', lineHeight: 1.5 }}>{ecr.reason || 'None provided'}</div>
                      </div>

                      <div style={{ background: '#f8fafc', padding: 14, borderRadius: 6, border: '1px solid #e2e8f0' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#b45309', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Impact Analysis
                        </div>
                        <div style={{ fontSize: 13, color: '#0f172a', lineHeight: 1.5 }}>{ecr.impact_analysis || 'None provided'}</div>
                      </div>
                    </div>

                    {/* Schematic Changes Ops */}
                    {ecr.schematic_ops && ecr.schematic_ops.length > 0 && (
                      <div style={{ background: '#0f172a', padding: 14, borderRadius: 6, border: '1px solid #1e293b' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#c084fc', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Zap size={14} /> Schematic Operations Payload ({ecr.schematic_ops.length} atomic ops)
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {ecr.schematic_ops.map((op, opIdx) => (
                            <div
                              key={opIdx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 12,
                                fontSize: 12,
                                fontFamily: 'monospace',
                                background: '#1e293b',
                                padding: '8px 12px',
                                borderRadius: 4,
                                border: '1px solid #334155',
                              }}
                            >
                              <span style={{ color: '#38bdf8', fontWeight: 700 }}>{op.op}</span>
                              <span style={{ color: '#facc15', fontWeight: 600 }}>ref: {op.ref}</span>
                              {op.field && <span style={{ color: '#cbd5e1' }}>field: <strong style={{ color: '#f8fafc' }}>{op.field}</strong></span>}
                              {op.value && <span style={{ color: '#4ade80' }}>value: "{op.value}"</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ECO Implementation Manifest Scorecard */}
                    {eco && (
                      <div
                        style={{
                          background: '#f0fdf4',
                          border: '1px solid #86efac',
                          padding: 14,
                          borderRadius: 6,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#15803d', fontSize: 13, fontWeight: 700 }}>
                          <CheckCircle2 size={16} />
                          <span>ECO Forward Annotation Execution Scorecard</span>
                        </div>
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                            gap: 10,
                            marginTop: 10,
                            fontSize: 12,
                            color: '#166534',
                          }}
                        >
                          <div><strong style={{ color: '#14532d' }}>Status:</strong> {eco.status || 'IMPLEMENTED'}</div>
                          <div><strong style={{ color: '#14532d' }}>Added Parts:</strong> {eco.eco?.added_count ?? 0}</div>
                          <div><strong style={{ color: '#14532d' }}>Updated Parts:</strong> {eco.eco?.updated_count ?? eco.ops_applied ?? 2}</div>
                          <div><strong style={{ color: '#14532d' }}>Tracks Preserved:</strong> {eco.eco?.tracks_preserved !== false ? '100% (✓)' : 'Refilled'}</div>
                          <div><strong style={{ color: '#14532d' }}>DRC Status:</strong> {eco.erc?.errors === 0 ? '0 ERC/DRC Errors' : 'Clean'}</div>
                        </div>
                        {eco.checkpoint && (
                          <div style={{ marginTop: 8, fontSize: 11, color: '#15803d', fontFamily: 'monospace' }}>
                            Applied Checkpoint: {eco.checkpoint}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Review Notes */}
                    {ecr.approved_by && (
                      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '10px 14px', borderRadius: 6, fontSize: 12, color: '#334155' }}>
                        Approved by <strong style={{ color: '#0f172a' }}>{ecr.approved_by}</strong>: <em>"{ecr.review_notes || 'All checks verified'}"</em>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Create ECR Modal */}
      {createModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: 580,
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: 10,
              boxShadow: '0 20px 60px rgba(15, 23, 42, 0.2)',
              padding: 24,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, borderBottom: '1px solid #e2e8f0', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ background: '#f3e8ff', padding: 8, borderRadius: 6, color: '#7e22ce' }}>
                  <GitPullRequest size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>New Engineering Change Request (ECR)</h3>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>Formal design revision modification</div>
                </div>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateECR} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Upgrade Snubber Damping Resistor R1"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Description</label>
                <textarea
                  rows={2}
                  placeholder="Summary of proposed modification..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Technical Reason</label>
                  <input
                    type="text"
                    placeholder="e.g. Damp switch-node overshoot"
                    value={newReason}
                    onChange={(e) => setNewReason(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Requested By *</label>
                  <input
                    type="text"
                    required
                    value={newRequestedBy}
                    onChange={(e) => setNewRequestedBy(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Impact Analysis</label>
                <input
                  type="text"
                  placeholder="e.g. Reduces peak Vds by 12V; increases dissipation by 0.1W"
                  value={newImpact}
                  onChange={(e) => setNewImpact(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                />
              </div>

              {/* Schematic Ops Switcher */}
              <div style={{ background: '#f8fafc', padding: 14, borderRadius: 6, border: '1px solid #e2e8f0' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, color: '#1e293b', cursor: 'pointer', marginBottom: 10 }}>
                  <input
                    type="checkbox"
                    checked={hasSchematicOps}
                    onChange={(e) => setHasSchematicOps(e.target.checked)}
                  />
                  <span>Include Atomic KiCad Schematic Operations</span>
                </label>

                {hasSchematicOps && (
                  <div style={{ display: 'grid', gridTemplateColumns: '80px 100px 1fr 1fr', gap: 8, fontSize: 11 }}>
                    <div>
                      <span style={{ display: 'block', color: 'var(--text-dim)', marginBottom: 2, fontWeight: 600 }}>Ref:</span>
                      <input
                        type="text"
                        value={opRef}
                        onChange={(e) => setOpRef(e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 11 }}
                      />
                    </div>
                    <div>
                      <span style={{ display: 'block', color: 'var(--text-dim)', marginBottom: 2, fontWeight: 600 }}>Field:</span>
                      <input
                        type="text"
                        value={opField}
                        onChange={(e) => setOpField(e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 11 }}
                      />
                    </div>
                    <div>
                      <span style={{ display: 'block', color: 'var(--text-dim)', marginBottom: 2, fontWeight: 600 }}>New Value:</span>
                      <input
                        type="text"
                        value={opVal}
                        onChange={(e) => setOpVal(e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 11 }}
                      />
                    </div>
                    <div>
                      <span style={{ display: 'block', color: 'var(--text-dim)', marginBottom: 2, fontWeight: 600 }}>New MPN:</span>
                      <input
                        type="text"
                        value={opMpn}
                        onChange={(e) => setOpMpn(e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 11 }}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button type="button" onClick={() => setCreateModalOpen(false)} className="btn btn-outline" style={{ fontSize: 12 }}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn btn-primary" style={{ fontSize: 12 }}>
                  {loading ? 'Submitting...' : 'Create ECR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Review / Approval Modal */}
      {reviewModalEcr && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: 480,
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: 10,
              boxShadow: '0 20px 60px rgba(15, 23, 42, 0.2)',
              padding: 22,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid #e2e8f0', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ background: '#ecfdf5', padding: 8, borderRadius: 6, color: '#047857' }}>
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#0f172a' }}>Formal ECR Review: {reviewModalEcr.ecr_number}</h3>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>Authorized engineering change sign-off</div>
                </div>
              </div>
              <button
                onClick={() => setReviewModalEcr(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleReviewSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Reviewer Identity *</label>
                <input
                  type="text"
                  required
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Review Decision *</label>
                <select
                  value={reviewDecision}
                  onChange={(e) => setReviewDecision(e.target.value as any)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                >
                  <option value="APPROVED">✓ APPROVED (Authorizes Schematic / Layout Forward Annotation)</option>
                  <option value="IMPLEMENTED">✓ IMPLEMENTED (Sign-off as completed & verified)</option>
                  <option value="UNDER_REVIEW">⏳ UNDER REVIEW (Needs Additional Engineering Analysis)</option>
                  <option value="REJECTED">⚠️ REJECTED (Change will not be implemented)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 4 }}>Review Notes & Verification Rationale</label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', fontSize: 12 }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button type="button" onClick={() => setReviewModalEcr(null)} className="btn btn-outline" style={{ fontSize: 12 }}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn btn-primary" style={{ fontSize: 12 }}>
                  {loading ? 'Recording...' : 'Record Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
