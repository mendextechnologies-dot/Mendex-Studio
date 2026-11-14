import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  ShieldAlert,
  Zap,
  Printer,
  FileText,
  Copy,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Layers,
  CheckSquare,
  Square,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Sliders,
  X,
} from 'lucide-react';

interface LaboratoryTestPlanCardProps {
  revisionId: string;
  projectCode: string;
  projectName: string;
}

export const LaboratoryTestPlanCard: React.FC<LaboratoryTestPlanCardProps> = ({
  revisionId,
  projectCode,
  projectName,
}) => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [planData, setPlanData] = useState<any | null>(null);

  // Active view tab: 'procedure' | 'probes' | 'equipment' | 'scorecard'
  const [activeSubTab, setActiveSubTab] = useState<'procedure' | 'probes' | 'equipment' | 'scorecard'>('procedure');

  // Expanded phases map
  const [expandedPhases, setExpandedPhases] = useState<Record<number, boolean>>({
    1: true,
    2: true,
    3: true,
    4: true,
  });

  // Checked PPE items (local interactive state)
  const [checkedPpe, setCheckedPpe] = useState<Record<number, boolean>>({});

  // Modal preview for print-ready HTML
  const [previewModalOpen, setPreviewModalOpen] = useState(false);

  // Markdown copy confirmation
  const [copiedMd, setCopiedMd] = useState(false);

  const fetchPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getTestPlan(revisionId);
      if (res && res.success) {
        setPlanData(res);
      }
    } catch (err: any) {
      // If not yet generated, attempt to generate
      try {
        const genRes = await api.generateTestPlan(revisionId);
        if (genRes && genRes.success) {
          setPlanData(genRes);
        }
      } catch (genErr: any) {
        setError(genErr.message || String(genErr));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await api.generateTestPlan(revisionId);
      if (res && res.success) {
        setPlanData(res);
        setSuccessMsg(`Test plan ${res.protocol_id} generated successfully.`);
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    fetchPlan();
  }, [revisionId]);

  const togglePhase = (phaseNum: number) => {
    setExpandedPhases((prev) => ({ ...prev, [phaseNum]: !prev[phaseNum] }));
  };

  const togglePpe = (idx: number) => {
    setCheckedPpe((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleCopyMarkdown = () => {
    if (planData?.markdown_content) {
      navigator.clipboard.writeText(planData.markdown_content);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 3000);
    }
  };

  const handleOpenPrintView = () => {
    if (planData?.html_content) {
      const win = window.open('', '_blank');
      if (win) {
        win.document.write(planData.html_content);
        win.document.close();
      }
    }
  };

  const plan = planData?.test_plan;
  const isExtremeHv = planData?.is_high_voltage && plan?.operating_envelope?.vin_max_v >= 500;

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      {/* 1. Header Bar */}
      <div
        style={{
          padding: '16px 20px',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
          borderBottom: '1px solid #cbd5e1',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: isExtremeHv ? '#fee2e2' : '#e0f2fe',
              color: isExtremeHv ? '#b91c1c' : '#0369a1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                High-Voltage Laboratory Test Plan & Bring-Up Protocol
              </h3>
              {planData?.protocol_id && (
                <span
                  style={{
                    fontSize: '11px',
                    fontFamily: 'monospace',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: '#e2e8f0',
                    color: '#334155',
                    fontWeight: 600,
                  }}
                >
                  {planData.protocol_id}
                </span>
              )}
            </div>
            <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
              Staged power-up protocol, oscilloscope probe acquisition schedule, PPE limits, and attributable sign-off scorecard (G16 / G17 / G23).
            </p>
          </div>
        </div>

        {/* Header Action Badges & Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {planData?.safety_category && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                padding: '4px 10px',
                borderRadius: '5px',
                background: isExtremeHv ? '#ffe4e6' : '#fef9c3',
                color: isExtremeHv ? '#be123c' : '#854d0e',
                border: `1px solid ${isExtremeHv ? '#f43f5e' : '#facc15'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <AlertTriangle size={13} />
              {planData.safety_category}
            </span>
          )}

          <button
            onClick={handleRegenerate}
            disabled={generating || loading}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Re-generate protocol from latest specification"
          >
            <RefreshCw size={12} className={generating ? 'spin' : ''} />
            <span>{generating ? 'Compiling…' : 'Re-Generate'}</span>
          </button>

          <button
            onClick={() => setPreviewModalOpen(true)}
            disabled={!planData}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Preview print-ready protocol document"
          >
            <FileText size={12} />
            <span>View Doc</span>
          </button>

          <button
            onClick={handleOpenPrintView}
            disabled={!planData}
            className="btn btn-primary"
            style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Print or export as PDF"
          >
            <Printer size={12} />
            <span>Print / PDF</span>
          </button>

          <button
            onClick={handleCopyMarkdown}
            disabled={!planData}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Copy Markdown protocol"
          >
            {copiedMd ? <CheckCircle2 size={12} color="#15803d" /> : <Copy size={12} />}
            <span>{copiedMd ? 'Copied' : 'Copy MD'}</span>
          </button>
        </div>
      </div>

      {/* 2. Messages & Alerts */}
      {error && (
        <div style={{ padding: '10px 16px', background: '#fef2f2', borderBottom: '1px solid #fecaca', color: '#b91c1c', fontSize: '12px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {successMsg && (
        <div style={{ padding: '10px 16px', background: '#f0fdf4', borderBottom: '1px solid #bbf7d0', color: '#15803d', fontSize: '12px' }}>
          {successMsg}
        </div>
      )}

      {/* 3. Safety Notice Bar */}
      <div
        style={{
          padding: '10px 20px',
          background: '#fffbeb',
          borderBottom: '1px solid #fef3c7',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '11.5px',
          color: '#92400e',
        }}
      >
        <ShieldAlert size={16} style={{ flexShrink: 0 }} />
        <span>
          <strong>Engineering Notice (Gate G16/G17/G23):</strong> This protocol governs high-voltage bench execution. Generating this document does <strong>not</strong> assert that physical bring-up has succeeded. Human laboratory sign-off with calibrated instruments is required.
        </span>
      </div>

      {/* 4. Sub-Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid #e2e8f0',
          background: '#f8fafc',
          padding: '0 16px',
        }}
      >
        {[
          { id: 'procedure', label: '4-Phase Bring-Up Procedure', icon: Activity },
          { id: 'probes', label: 'Oscilloscope Probe Points Map', icon: Sliders },
          { id: 'equipment', label: 'Lab Instruments & PPE Checklist', icon: CheckSquare },
          { id: 'scorecard', label: 'Attributable Sign-Off Scorecard', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 14px',
                fontSize: '12px',
                fontWeight: active ? 700 : 500,
                color: active ? '#1d4ed8' : '#64748b',
                background: 'transparent',
                border: 'none',
                borderBottom: active ? '2px solid #1d4ed8' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* 5. Tab Content Area */}
      <div style={{ padding: '20px' }}>
        {loading && !plan && (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
            <RefreshCw size={24} className="spin" style={{ margin: '0 auto 10px auto' }} />
            <p style={{ fontSize: '13px', margin: 0 }}>Loading authoritative laboratory test plan…</p>
          </div>
        )}

        {plan && (
          <>
            {/* SUB-TAB 1: PROCEDURE */}
            {activeSubTab === 'procedure' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Operating Design Envelope Summary Cards */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
                    gap: '10px',
                    marginBottom: '8px',
                  }}
                >
                  <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Nominal Input</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
                      {plan.operating_envelope?.vin_nom_v} V
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>Max: {plan.operating_envelope?.vin_max_v} V</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Target Output</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
                      {plan.operating_envelope?.vout_v} V
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>Power: {plan.operating_envelope?.pout_w?.toFixed(1)} W</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Switching Freq</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
                      {(plan.operating_envelope?.fsw_hz / 1000).toFixed(1)} kHz
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>{plan.operating_envelope?.topology}</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Galvanic Barrier</div>
                    <div style={{ fontSize: '14px', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                      {plan.operating_envelope?.isolation || '5000 Vrms'}
                    </div>
                    <div style={{ fontSize: '10.5px', color: '#94a3b8' }}>Primary to Secondary</div>
                  </div>
                </div>

                {/* Staged Phases Accordion */}
                {plan.phases?.map((phase: any) => {
                  const isExpanded = expandedPhases[phase.phase_num];
                  return (
                    <div
                      key={phase.phase_num}
                      style={{
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        overflow: 'hidden',
                        background: '#ffffff',
                      }}
                    >
                      <button
                        onClick={() => togglePhase(phase.phase_num)}
                        style={{
                          width: '100%',
                          padding: '12px 16px',
                          background: '#f8fafc',
                          border: 'none',
                          borderBottom: isExpanded ? '1px solid #cbd5e1' : 'none',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          cursor: 'pointer',
                          textAlign: 'left',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span
                            style={{
                              width: '24px',
                              height: '24px',
                              borderRadius: '50%',
                              background: '#1d4ed8',
                              color: '#fff',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '11px',
                              fontWeight: 700,
                            }}
                          >
                            {phase.phase_num}
                          </span>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                            Phase {phase.phase_num}: {phase.title}
                          </span>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>
                            ({phase.steps.length} verified steps)
                          </span>
                        </div>
                        {isExpanded ? <ChevronDown size={16} color="#64748b" /> : <ChevronRight size={16} color="#64748b" />}
                      </button>

                      {isExpanded && (
                        <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {phase.steps.map((st: any) => (
                            <div
                              key={st.step}
                              style={{
                                padding: '12px 14px',
                                background: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                                <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>
                                  <span style={{ color: '#1d4ed8', marginRight: '6px' }}>Step {st.step}</span>
                                  {st.action}
                                </div>
                                <span
                                  style={{
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    background: '#f1f5f9',
                                    color: '#475569',
                                  }}
                                >
                                  BENCH VERIFICATION
                                </span>
                              </div>
                              <p style={{ fontSize: '11.5px', color: '#475569', margin: '6px 0 8px 0', lineHeight: 1.4 }}>
                                {st.detail}
                              </p>
                              <div
                                style={{
                                  padding: '8px 10px',
                                  background: '#ffffff',
                                  border: '1px dashed #cbd5e1',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  flexWrap: 'wrap',
                                  gap: '8px',
                                }}
                              >
                                <div>
                                  <strong style={{ color: '#15803d' }}>Acceptance Criteria:</strong> {st.criteria}
                                </div>
                                <div style={{ display: 'flex', gap: '6px', fontFamily: 'monospace', fontSize: '10.5px' }}>
                                  <span style={{ border: '1px solid #cbd5e1', padding: '2px 6px', borderRadius: '3px' }}>[ ] PASS</span>
                                  <span style={{ border: '1px solid #cbd5e1', padding: '2px 6px', borderRadius: '3px' }}>[ ] FAIL</span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Immediate Abort Limits Callout */}
                <div
                  style={{
                    padding: '14px 18px',
                    background: '#fef2f2',
                    border: '1px solid #fecaca',
                    borderLeft: '4px solid #ef4444',
                    borderRadius: '6px',
                    marginTop: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <ShieldAlert size={18} color="#b91c1c" />
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#991b1b', margin: 0 }}>
                      Non-Negotiable Immediate Abort & Hazard Shutdown Limits
                    </h4>
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '11.5px', color: '#b91c1c', lineHeight: 1.5 }}>
                    {plan.abort_criteria?.map((crit: string, i: number) => (
                      <li key={i}>{crit}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* SUB-TAB 2: PROBE POINTS MAP */}
            {activeSubTab === 'probes' && (
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
                  Simultaneous 4-Channel Oscilloscope Acquisition Schedule
                </h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '11.5px', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', color: '#475569' }}>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>Channel</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>Signal Name</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>PCB Test Point</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>Reference Ground</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>Probe Type</th>
                        <th style={{ padding: '10px 12px', textAlign: 'left' }}>Expected Waveform</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.test_points?.map((tp: any, i: number) => {
                        const channelColor =
                          tp.channel.includes('CH1') ? '#ca8a04' :
                          tp.channel.includes('CH2') ? '#2563eb' :
                          tp.channel.includes('CH3') ? '#c026d3' : '#0891b2';
                        return (
                          <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={{ padding: '10px 12px' }}>
                              <span
                                style={{
                                  display: 'inline-block',
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  fontWeight: 700,
                                  fontSize: '11px',
                                  background: `${channelColor}20`,
                                  color: channelColor,
                                  border: `1px solid ${channelColor}50`,
                                }}
                              >
                                {tp.channel}
                              </span>
                            </td>
                            <td style={{ padding: '10px 12px', fontWeight: 700, color: '#0f172a' }}>{tp.signal}</td>
                            <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#1d4ed8' }}>`{tp.test_point}`</td>
                            <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#64748b' }}>`{tp.reference}`</td>
                            <td style={{ padding: '10px 12px', color: '#475569' }}>{tp.probe_type}</td>
                            <td style={{ padding: '10px 12px', color: '#334155' }}>{tp.expected}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SUB-TAB 3: EQUIPMENT & PPE */}
            {activeSubTab === 'equipment' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* PPE Checklist */}
                <div>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                    Personal Protective Equipment (PPE) & Bench Safety Gate
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {plan.ppe_checklist?.map((item: string, idx: number) => {
                      const isChecked = checkedPpe[idx];
                      return (
                        <div
                          key={idx}
                          onClick={() => togglePpe(idx)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '8px 12px',
                            background: isChecked ? '#f0fdf4' : '#f8fafc',
                            border: `1px solid ${isChecked ? '#bbf7d0' : '#e2e8f0'}`,
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '12px',
                            color: isChecked ? '#15803d' : '#334155',
                          }}
                        >
                          {isChecked ? <CheckSquare size={16} color="#15803d" /> : <Square size={16} color="#94a3b8" />}
                          <span>{item}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Calibrated Instruments Table */}
                <div>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                    Required Calibrated Laboratory Instruments
                  </h4>
                  <table style={{ width: '100%', fontSize: '11.5px', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', color: '#475569' }}>
                        <th style={{ padding: '8px 10px', textAlign: 'left' }}>Category</th>
                        <th style={{ padding: '8px 10px', textAlign: 'left' }}>Instrument</th>
                        <th style={{ padding: '8px 10px', textAlign: 'left' }}>Minimum Specification</th>
                        <th style={{ padding: '8px 10px', textAlign: 'left' }}>Measurement Purpose</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.equipment_checklist?.map((eq: any, i: number) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '8px 10px', fontWeight: 600, color: '#1d4ed8' }}>{eq.category}</td>
                          <td style={{ padding: '8px 10px', fontWeight: 600, color: '#0f172a' }}>{eq.name}</td>
                          <td style={{ padding: '8px 10px', color: '#475569' }}>{eq.min_spec}</td>
                          <td style={{ padding: '8px 10px', color: '#64748b' }}>{eq.purpose}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SUB-TAB 4: SCORECARD */}
            {activeSubTab === 'scorecard' && (
              <div
                style={{
                  border: '2px solid #0f766e',
                  borderRadius: '8px',
                  padding: '20px',
                  background: '#f0fdfa',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#0f766e', margin: 0 }}>
                      Attributable Physical Laboratory Sign-Off Scorecard
                    </h4>
                    <span style={{ fontSize: '11px', color: '#134e4a' }}>
                      Official record format for ingesting authentic test measurements into StudioService.measurements
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: '4px',
                      background: '#ccfbf1',
                      color: '#0f766e',
                      border: '1px solid #99f6e4',
                    }}
                  >
                    STATUS: PENDING PHYSICAL EXECUTION
                  </span>
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                    gap: '12px',
                    fontSize: '12px',
                    color: '#0f766e',
                  }}
                >
                  <div style={{ background: '#fff', padding: '10px 12px', borderRadius: '6px', border: '1px solid #99f6e4' }}>
                    <strong>Test Station ID:</strong>
                    <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '4px' }}>LAB-BENCH-HV-01</div>
                  </div>
                  <div style={{ background: '#fff', padding: '10px 12px', borderRadius: '6px', border: '1px solid #99f6e4' }}>
                    <strong>Lead Test Engineer:</strong>
                    <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '4px' }}>__________________________</div>
                  </div>
                  <div style={{ background: '#fff', padding: '10px 12px', borderRadius: '6px', border: '1px solid #99f6e4' }}>
                    <strong>Attributable Signature:</strong>
                    <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '4px' }}>__________________________</div>
                  </div>
                  <div style={{ background: '#fff', padding: '10px 12px', borderRadius: '6px', border: '1px solid #99f6e4' }}>
                    <strong>Physical Test Date:</strong>
                    <div style={{ fontFamily: 'monospace', color: '#334155', marginTop: '4px' }}>____ / ____ / ________</div>
                  </div>
                </div>

                <div
                  style={{
                    marginTop: '16px',
                    padding: '12px',
                    background: '#fff',
                    borderRadius: '6px',
                    border: '1px solid #99f6e4',
                    fontSize: '11.5px',
                    color: '#334155',
                  }}
                >
                  <strong style={{ color: '#0f766e' }}>Evidence Retention Note:</strong> Raw oscilloscope waveform CSV exports and thermal FLIR imagery must be recorded with cryptographic SHA-256 hashes. Generating this protocol provides the authoritative framework; physical measurement records remain distinct from automated predictions.
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* 6. Document Preview Modal */}
      {previewModalOpen && planData?.html_content && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(5, 7, 13, 0.75)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '1000px',
              height: '90vh',
              background: '#ffffff',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
            }}
          >
            <div
              style={{
                padding: '12px 18px',
                background: '#f8fafc',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={18} color="#0f766e" />
                <strong style={{ fontSize: '13px', color: '#0f172a' }}>{planData.protocol_id} - Print View</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={handleOpenPrintView}
                  className="btn btn-primary"
                  style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Printer size={12} /> Print / Save as PDF
                </button>
                <button
                  onClick={() => setPreviewModalOpen(false)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
                >
                  <X size={18} color="#64748b" />
                </button>
              </div>
            </div>
            <iframe
              srcDoc={planData.html_content}
              title="Test Plan Protocol Preview"
              style={{ width: '100%', flex: 1, border: 'none' }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
