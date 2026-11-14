import React, { useState } from 'react';
import { api } from '../api/client';

export interface TopologySynthesizerCardProps {
  revisionId: string;
  specification: Record<string, any>;
  designs?: any[];
  onRefresh?: () => void;
  onOpenFile?: (path: string) => void;
}

export const TopologySynthesizerCard: React.FC<TopologySynthesizerCardProps> = ({
  revisionId,
  specification,
  designs = [],
  onRefresh,
  onOpenFile,
}) => {
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [selectingCandidateId, setSelectingCandidateId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Extract candidates from linked designs
  const activeDesign = designs && designs.length > 0 ? designs[0] : null;
  const candidates: any[] = activeDesign?.candidates || [];
  const selectedCandidate = candidates.find((c) => c.status === 'SELECTED') || candidates[0] || null;

  const handleSynthesize = async () => {
    setIsSynthesizing(true);
    setNotification(null);
    try {
      const res = await api.synthesizeTopologies(revisionId);
      setNotification({
        type: 'success',
        message: `Successfully synthesized ${res.count} topology candidates based on specifications!`,
      });
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        message: err.message || 'Failed to synthesize topology candidates',
      });
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleSelectCandidate = async (candidateId: string) => {
    setSelectingCandidateId(candidateId);
    setNotification(null);
    try {
      const res = await api.selectCandidate(revisionId, candidateId, true);
      setNotification({
        type: 'success',
        message: `Topology "${res.name || res.selected_topology}" selected and promoted! KiCad 10 schematic captured and PCB layout auto-placed.`,
      });
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setNotification({
        type: 'error',
        message: err.message || 'Failed to select and promote candidate',
      });
    } finally {
      setSelectingCandidateId(null);
    }
  };

  const vinNom = specification?.vin_nom_v || 24;
  const vinMin = specification?.vin_min_v || vinNom;
  const vinMax = specification?.vin_max_v || vinNom;
  const vout = specification?.vout_v || 12;
  const iout = specification?.iout_a || 5;
  const pout = (vout * iout).toFixed(0);
  const fswKhz = ((specification?.switching_frequency_hz || 200000) / 1000).toFixed(0);
  const isolationReq = specification?.isolation_requirement || 'Non-Isolated';

  return (
    <div
      style={{
        padding: 20,
        background: '#ffffff',
        borderRadius: 8,
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        marginBottom: 20,
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 20 }}>⚡</span>
            <h4 style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', margin: 0 }}>
              Power Electronics Topology Synthesizer & Candidate Switcher
            </h4>
          </div>
          <span style={{ fontSize: 11, color: '#64748b', marginTop: 4, display: 'inline-block' }}>
            Deterministic Multi-Topology Synthesis & KiCad 10 Schematic Promotion per IEC 60664-1 & IPC Standards
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {selectedCandidate && (
            <span
              className="badge badge-green"
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', fontSize: 11 }}
            >
              🎯 Active: {selectedCandidate.name || selectedCandidate.topology}
            </span>
          )}
          <span className="badge badge-blue">{candidates.length} Evaluated</span>
          <button
            className="btn btn-secondary"
            onClick={handleSynthesize}
            disabled={isSynthesizing}
            style={{
              fontSize: 12,
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontWeight: 600,
            }}
          >
            {isSynthesizing ? '⚡ Synthesizing Candidates…' : '⚡ Re-Synthesize Topologies'}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            fontSize: 12,
            lineHeight: 1.4,
            background: notification.type === 'success' ? '#ecfdf5' : '#fef2f2',
            border: `1px solid ${notification.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
            color: notification.type === 'success' ? '#065f46' : '#991b1b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              color: 'inherit',
              padding: '0 4px',
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Electrical Specification HUD */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: 10,
          background: '#f8fafc',
          padding: 12,
          borderRadius: 6,
          border: '1px solid #e2e8f0',
        }}
      >
        <div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Input Voltage (Vin)
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>
            {vinNom} V <span style={{ fontSize: 10, color: '#94a3b8' }}>({vinMin}–{vinMax}V)</span>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Output Voltage (Vout)
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>{vout} V</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Load Current / Power
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>
            {iout} A <span style={{ fontSize: 10, color: '#94a3b8' }}>({pout} W)</span>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Switching Freq
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>{fswKhz} kHz</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
            Isolation Boundary
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>{isolationReq}</div>
        </div>
      </div>

      {/* Candidate Scorecard Grid */}
      {candidates.length === 0 ? (
        <div
          style={{
            padding: 30,
            textAlign: 'center',
            background: '#f8fafc',
            borderRadius: 6,
            border: '1px dashed #cbd5e1',
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>📐</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>
            No Topologies Synthesized Yet
          </div>
          <p style={{ fontSize: 12, color: '#64748b', maxWidth: 480, margin: '6px auto 16px' }}>
            Click below to execute deterministic multi-topology power synthesis, score feasibility across all candidates (PSFB, LLC, Flyback, Buck, Boost), and capture KiCad 10 schematics.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleSynthesize}
            disabled={isSynthesizing}
            style={{ padding: '8px 20px', fontWeight: 600 }}
          >
            {isSynthesizing ? '⚡ Synthesizing Topologies…' : '⚡ Synthesize Candidates Now'}
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: 14,
          }}
        >
          {candidates.map((cand) => {
            const isSelected = cand.status === 'SELECTED';
            const metrics = cand.calculated_metrics || {};
            const params = cand.parameters || {};
            const effPct = metrics.estimated_efficiency ? (metrics.estimated_efficiency * 100).toFixed(1) : null;
            const scorePct = Math.round((cand.feasibility_score || 0) * 100);
            const isPendingThis = selectingCandidateId === cand.id;

            return (
              <div
                key={cand.id}
                style={{
                  borderRadius: 8,
                  padding: 14,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  border: isSelected ? '2px solid #10b981' : '1px solid #e2e8f0',
                  background: isSelected ? '#f0fdf4' : '#ffffff',
                  boxShadow: isSelected ? '0 4px 12px rgba(16, 185, 129, 0.12)' : '0 1px 2px rgba(0,0,0,0.03)',
                  position: 'relative',
                  transition: 'all 0.2s ease',
                }}
              >
                <div>
                  {/* Top line: Name & Status badge */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                    <div>
                      <h5 style={{ fontSize: 13, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                        {cand.name}
                      </h5>
                      <span style={{ fontSize: 10, color: '#64748b' }}>{cand.topology}</span>
                    </div>
                    {isSelected ? (
                      <span
                        className="badge badge-green"
                        style={{ fontSize: 10, padding: '2px 8px', fontWeight: 700 }}
                      >
                        ✓ Active Baseline
                      </span>
                    ) : (
                      <span
                        className="badge badge-muted"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                      >
                        Proposed
                      </span>
                    )}
                  </div>

                  {/* Feasibility Score Bar */}
                  <div style={{ marginTop: 10, marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 3 }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>Feasibility Score</span>
                      <span style={{ fontWeight: 700, color: isSelected ? '#047857' : '#1e293b' }}>
                        {scorePct}%
                      </span>
                    </div>
                    <div
                      style={{
                        width: '100%',
                        height: 6,
                        borderRadius: 3,
                        background: '#e2e8f0',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${scorePct}%`,
                          height: '100%',
                          background: scorePct >= 90 ? '#10b981' : scorePct >= 80 ? '#3b82f6' : '#f59e0b',
                          borderRadius: 3,
                        }}
                      />
                    </div>
                  </div>

                  {/* Calculated Metrics Badges */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                    {effPct && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          background: '#ecfdf5',
                          color: '#065f46',
                          border: '1px solid #a7f3d0',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}
                      >
                        η: {effPct}%
                      </span>
                    )}
                    {metrics.switch_voltage_stress_v !== undefined && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          background: '#f1f5f9',
                          color: '#334155',
                          border: '1px solid #cbd5e1',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}
                      >
                        V_stress: {metrics.switch_voltage_stress_v.toFixed(0)} V
                      </span>
                    )}
                    {metrics.component_count !== undefined && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          background: '#f8fafc',
                          color: '#475569',
                          border: '1px solid #e2e8f0',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}
                      >
                        {metrics.component_count} Parts
                      </span>
                    )}
                  </div>

                  {/* Key Design Parameters */}
                  <div
                    style={{
                      fontSize: 10,
                      color: '#475569',
                      background: isSelected ? '#ffffff' : '#f8fafc',
                      padding: 8,
                      borderRadius: 4,
                      border: '1px solid #e2e8f0',
                      marginBottom: 10,
                      lineHeight: 1.4,
                    }}
                  >
                    {cand.topology.includes('Phase-Shifted') && (
                      <>
                        <strong>PSFB Metrics:</strong> D_eff: {params.d_eff ?? 0.7} • Np/Ns: {params.turns_ratio_np_ns?.toFixed(2) ?? '—'} • L_shim: {params.l_shim_uh?.toFixed(1) ?? '15.0'} µH • 4-Switch ZVS Bridge
                      </>
                    )}
                    {cand.topology.includes('LLC') && (
                      <>
                        <strong>LLC Metrics:</strong> Lr: {params.lr_uh?.toFixed(1) ?? '—'} µH • Cr: {params.cr_nf?.toFixed(1) ?? '—'} nF • Lm: {params.lm_uh?.toFixed(1) ?? '—'} µH • ZVS Resonant Tank
                      </>
                    )}
                    {cand.topology.includes('Flyback') && (
                      <>
                        <strong>Flyback Metrics:</strong> Lm: {params.lm_uh?.toFixed(1) ?? '—'} µH • Np/Ns: {params.turns_ratio_np_ns?.toFixed(2) ?? '—'} • Discontinuous / QR Operation
                      </>
                    )}
                    {cand.topology.includes('Buck') && (
                      <>
                        <strong>Buck Metrics:</strong> L: {params.l_uh?.toFixed(1) ?? '—'} µH • C: {params.c_uf?.toFixed(1) ?? '—'} µF • D: {params.d_nom?.toFixed(2) ?? '—'} • Synchronous MOSFET
                      </>
                    )}
                    {cand.topology.includes('Boost') && (
                      <>
                        <strong>Boost Metrics:</strong> L: {params.l_uh?.toFixed(1) ?? '—'} µH • C: {params.c_uf?.toFixed(1) ?? '—'} µF • D: {params.d_nom?.toFixed(2) ?? '—'} • Step-Up
                      </>
                    )}
                    {cand.topology.includes('Push-Pull') && (
                      <>
                        <strong>Push-Pull Metrics:</strong> Center-tapped Primary • Dual Low-Side Ground-Referenced Switches
                      </>
                    )}
                  </div>

                  {/* Description / Rationale */}
                  <p style={{ fontSize: 11, color: '#475569', lineHeight: 1.4, margin: '0 0 12px' }}>
                    {cand.description || cand.rationale}
                  </p>
                </div>

                {/* Card Action Button */}
                <div>
                  {isSelected ? (
                    <button
                      className="btn"
                      disabled
                      style={{
                        width: '100%',
                        fontSize: 11,
                        padding: '7px 12px',
                        background: '#dcfce7',
                        color: '#166534',
                        borderColor: '#86efac',
                        fontWeight: 700,
                        cursor: 'default',
                      }}
                    >
                      ✓ Currently Active KiCad Baseline
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      onClick={() => handleSelectCandidate(cand.id)}
                      disabled={isPendingThis || selectingCandidateId !== null}
                      style={{
                        width: '100%',
                        fontSize: 11,
                        padding: '7px 12px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                      }}
                    >
                      {isPendingThis ? '⚡ Capturing Schematic & PCB…' : '🔄 Switch & Promote to KiCad'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
