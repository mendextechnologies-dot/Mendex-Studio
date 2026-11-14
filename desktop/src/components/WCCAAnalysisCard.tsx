import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { WccaAnalysisReport } from '../api/types';
import {
  Activity,
  Play,
  RotateCcw,
  BarChart3,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Layers,
  ShieldCheck,
  ChevronRight,
  TrendingUp,
  Percent,
} from 'lucide-react';

interface WCCAAnalysisCardProps {
  revisionId: string;
  projectCode?: string;
}

export const WCCAAnalysisCard: React.FC<WCCAAnalysisCardProps> = ({ revisionId, projectCode }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<WccaAnalysisReport | null>(null);

  // Sweep controls
  const [numIterations, setNumIterations] = useState<number>(50);
  const [distribution, setDistribution] = useState<'gaussian' | 'uniform'>('gaussian');
  const [activeTab, setActiveTab] = useState<'histogram' | 'corners' | 'sensitivities' | 'runs'>('histogram');

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWccaAnalysis(revisionId);
      if (data && data.success) {
        setReport(data);
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRunSweep = async () => {
    setRunning(true);
    setError(null);
    try {
      const data = await api.runWccaAnalysis({
        revisionId,
        numIterations,
        distribution,
      });
      if (data && data.success) {
        setReport(data);
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [revisionId]);

  const stats = report?.statistics;
  const spec = report?.specification_limits;
  const bins = report?.histogram_bins || [];
  const corners = report?.eva_corners || [];
  const sensitivities = report?.sensitivities || [];

  // SVG Histogram calculations
  const maxBinCount = Math.max(...bins.map((b) => b.count), 1);
  const svgW = 740;
  const svgH = 220;
  const padL = 50;
  const padR = 30;
  const padT = 25;
  const padB = 40;
  const plotW = svgW - padL - padR;
  const plotH = svgH - padT - padB;

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderRadius: 8,
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        marginTop: 16,
      }}
    >
      {/* 1. Header Bar */}
      <div
        style={{
          padding: '14px 18px',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
          borderBottom: '1px solid #cbd5e1',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: '#0284c7',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <BarChart3 size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h4 style={{ margin: 0, fontSize: 14, fontWeight: 800, color: '#0f172a' }}>
                Worst-Case & Monte Carlo Tolerance Analysis (WCCA)
              </h4>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: 4,
                  background: report?.overall_readiness === 'PRODUCTION_READY' ? '#dcfce7' : '#fef3c7',
                  color: report?.overall_readiness === 'PRODUCTION_READY' ? '#15803d' : '#b45309',
                  border: `1px solid ${report?.overall_readiness === 'PRODUCTION_READY' ? '#86efac' : '#fde68a'}`,
                }}
              >
                {report?.overall_readiness === 'PRODUCTION_READY'
                  ? '✓ 3-SIGMA PRODUCTION READY'
                  : '⚠ MARGINAL (REQUIRES TRIMMING)'}
              </span>
            </div>
            <p style={{ margin: '2px 0 0 0', fontSize: 11, color: '#64748b' }}>
              Parametric sensitivity sweeps across component aging, thermal drift (-40°C to +85°C), and input voltage sag
            </p>
          </div>
        </div>

        {/* Sweep Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#475569' }}>
            <span>Runs:</span>
            <select
              value={numIterations}
              onChange={(e) => setNumIterations(Number(e.target.value))}
              style={{
                background: '#fff',
                border: '1px solid #cbd5e1',
                borderRadius: 4,
                padding: '3px 6px',
                fontSize: 11,
              }}
            >
              <option value={20}>20 Runs</option>
              <option value={50}>50 Runs</option>
              <option value={100}>100 Runs</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#475569' }}>
            <span>Distribution:</span>
            <select
              value={distribution}
              onChange={(e) => setDistribution(e.target.value as any)}
              style={{
                background: '#fff',
                border: '1px solid #cbd5e1',
                borderRadius: 4,
                padding: '3px 6px',
                fontSize: 11,
              }}
            >
              <option value="gaussian">Gaussian Normal (3σ)</option>
              <option value="uniform">Uniform (Worst Corner)</option>
            </select>
          </div>

          <button
            onClick={handleRunSweep}
            disabled={running}
            style={{
              background: '#0284c7',
              border: 'none',
              color: '#fff',
              padding: '5px 12px',
              borderRadius: 5,
              fontSize: 11.5,
              fontWeight: 700,
              cursor: running ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <RefreshCw size={12} className={running ? 'animate-spin' : ''} />
            {running ? 'Running Sweep...' : 'Re-Run Sweep'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 30, textAlign: 'center', color: '#64748b' }}>
          <RefreshCw size={20} className="animate-spin" style={{ display: 'inline', marginRight: 6 }} />
          Computing tolerance matrix & statistical yields...
        </div>
      ) : error ? (
        <div style={{ padding: 16, color: '#b91c1c', fontSize: 12 }}>{error}</div>
      ) : !report ? (
        <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>No WCCA data available.</div>
      ) : (
        <div style={{ padding: 18 }}>
          {/* 2. Executive Statistical Telemetry Ribbon */}
          {stats && spec && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                gap: 10,
                marginBottom: 16,
              }}
            >
              <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                  Statistical Yield
                </span>
                <div style={{ fontSize: 16, fontWeight: 800, color: stats.statistical_yield_percent >= 99 ? '#15803d' : '#b45309', marginTop: 2 }}>
                  {stats.statistical_yield_percent.toFixed(1)}%
                </div>
                <span style={{ fontSize: 10, color: '#64748b' }}>Within ±{spec.tolerance_percent}% limit</span>
              </div>

              <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                  Process Capability
                </span>
                <div style={{ fontSize: 16, fontWeight: 800, color: stats.cpk >= 1.33 ? '#15803d' : '#0284c7', marginTop: 2 }}>
                  Cpk = {stats.cpk.toFixed(2)}
                </div>
                <span style={{ fontSize: 10, color: '#64748b' }}>Cp = {stats.cp.toFixed(2)}</span>
              </div>

              <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                  Mean Output (μ)
                </span>
                <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginTop: 2 }}>
                  {stats.mean_v.toFixed(2)} V
                </div>
                <span style={{ fontSize: 10, color: '#64748b' }}>Nominal: {spec.vout_nominal_v.toFixed(1)} V</span>
              </div>

              <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                  Standard Dev (σ)
                </span>
                <div style={{ fontSize: 16, fontWeight: 800, color: '#0284c7', marginTop: 2 }}>
                  {stats.std_dev_v.toFixed(3)} V
                </div>
                <span style={{ fontSize: 10, color: '#64748b' }}>
                  ±3σ: [{stats.three_sigma_lower_v.toFixed(1)}, {stats.three_sigma_upper_v.toFixed(1)}] V
                </span>
              </div>

              <div style={{ padding: '10px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
                  Spec Tolerance Band
                </span>
                <div style={{ fontSize: 16, fontWeight: 800, color: '#475569', marginTop: 2 }}>
                  [{spec.lsl_vout_v.toFixed(1)}, {spec.usl_vout_v.toFixed(1)}] V
                </div>
                <span style={{ fontSize: 10, color: '#64748b' }}>LSL to USL (±{spec.tolerance_percent}%)</span>
              </div>
            </div>
          )}

          {/* 3. Sub-Tab Navigation Strip */}
          <div style={{ display: 'flex', gap: 6, borderBottom: '1px solid #e2e8f0', paddingBottom: 8, marginBottom: 14 }}>
            <button
              onClick={() => setActiveTab('histogram')}
              style={{
                background: activeTab === 'histogram' ? '#0284c7' : '#f1f5f9',
                color: activeTab === 'histogram' ? '#fff' : '#475569',
                border: 'none',
                borderRadius: 5,
                padding: '4px 12px',
                fontSize: 11.5,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Output Spread Histogram ({bins.length} bins)
            </button>
            <button
              onClick={() => setActiveTab('corners')}
              style={{
                background: activeTab === 'corners' ? '#0284c7' : '#f1f5f9',
                color: activeTab === 'corners' ? '#fff' : '#475569',
                border: 'none',
                borderRadius: 5,
                padding: '4px 12px',
                fontSize: 11.5,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Extreme Value Corners ({corners.length})
            </button>
            <button
              onClick={() => setActiveTab('sensitivities')}
              style={{
                background: activeTab === 'sensitivities' ? '#0284c7' : '#f1f5f9',
                color: activeTab === 'sensitivities' ? '#fff' : '#475569',
                border: 'none',
                borderRadius: 5,
                padding: '4px 12px',
                fontSize: 11.5,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Component Sensitivity Pareto
            </button>
          </div>

          {/* 4. Sub-Tab 1: Histogram View */}
          {activeTab === 'histogram' && (
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: '#334155' }}>
                  Monte Carlo Output Voltage (Vout) Distribution Histogram ({report.num_iterations} sweeps)
                </span>
                <div style={{ display: 'flex', gap: 12, fontSize: 10.5, color: '#64748b' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, background: '#0284c7', borderRadius: 2 }} />
                    Frequency Count
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 12, height: 2, background: '#dc2626' }} />
                    LSL / USL Specification Limit
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 12, height: 2, background: '#16a34a', borderTop: '1px dashed' }} />
                    Nominal Target (1000V)
                  </span>
                </div>
              </div>

              <svg viewBox={`0 0 ${svgW} ${svgH}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
                {/* Horizontal Grid */}
                {[0, 0.5, 1.0].map((frac) => {
                  const y = padT + plotH * (1 - frac);
                  const countVal = Math.round(frac * maxBinCount);
                  return (
                    <g key={frac}>
                      <line x1={padL} y1={y} x2={padL + plotW} y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                      <text x={padL - 6} y={y + 4} fontSize="9" fill="#94a3b8" textAnchor="end" fontFamily="monospace">
                        {countVal}
                      </text>
                    </g>
                  );
                })}

                {/* Bars */}
                {bins.map((b, idx) => {
                  const barW = (plotW / bins.length) * 0.75;
                  const barX = padL + idx * (plotW / bins.length) + (plotW / bins.length - barW) / 2;
                  const barH = (b.count / maxBinCount) * plotH;
                  const barY = padT + plotH - barH;
                  return (
                    <g key={idx}>
                      <rect
                        x={barX}
                        y={barY}
                        width={barW}
                        height={barH}
                        fill="#0284c7"
                        opacity={0.85}
                        rx="2"
                      />
                      <text
                        x={barX + barW / 2}
                        y={barY - 4}
                        fontSize="9"
                        fontWeight="bold"
                        fill="#0284c7"
                        textAnchor="middle"
                      >
                        {b.count > 0 ? b.count : ''}
                      </text>
                      <text
                        x={barX + barW / 2}
                        y={padT + plotH + 16}
                        fontSize="9"
                        fill="#64748b"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {b.bin_center.toFixed(1)}
                      </text>
                    </g>
                  );
                })}

                {/* Base axis */}
                <line x1={padL} y1={padT + plotH} x2={padL + plotW} y2={padT + plotH} stroke="#94a3b8" strokeWidth="1" />
              </svg>
            </div>
          )}

          {/* 5. Sub-Tab 2: EVA Corners Table */}
          {activeTab === 'corners' && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 11.5, borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', color: '#475569' }}>
                    <th style={{ padding: '8px 10px' }}>Corner ID</th>
                    <th style={{ padding: '8px 10px' }}>Test Conditions</th>
                    <th style={{ padding: '8px 10px' }}>Output Voltage (Vout)</th>
                    <th style={{ padding: '8px 10px' }}>Max Switch Stress (Vsw)</th>
                    <th style={{ padding: '8px 10px' }}>Ripple (pk-pk)</th>
                    <th style={{ padding: '8px 10px' }}>Margin Status</th>
                  </tr>
                </thead>
                <tbody>
                  {corners.map((c, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 700, color: '#0284c7' }}>{c.corner_name}</td>
                      <td style={{ padding: '8px 10px', color: '#475569', fontSize: 11 }}>{c.condition}</td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontWeight: 700, color: '#0f172a' }}>
                        {c.vout_v.toFixed(2)} V
                      </td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', color: '#0284c7' }}>
                        {c.vsw_peak_v.toFixed(1)} V
                      </td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', color: '#475569' }}>
                        {c.ripple_mv.toFixed(1)} mV
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: 3,
                            background: c.margin_status === 'PASS' ? '#dcfce7' : '#fef3c7',
                            color: c.margin_status === 'PASS' ? '#15803d' : '#b45309',
                          }}
                        >
                          {c.margin_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 6. Sub-Tab 3: Sensitivity Pareto Chart */}
          {activeTab === 'sensitivities' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 11.5, color: '#475569', marginBottom: 4 }}>
                Relative contribution to output voltage variance: d(Vout) / d(param). Components with high sensitivity require precision tolerance selection or active laser trimming.
              </div>
              {sensitivities.map((s, idx) => (
                <div key={idx} style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#0f172a' }}>{s.component}</span>
                    <span style={{ fontSize: 12, fontWeight: 800, color: '#0284c7' }}>
                      {s.sensitivity_pct.toFixed(1)}% of variance
                    </span>
                  </div>
                  <div style={{ width: '100%', height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${s.sensitivity_pct}%`,
                        height: '100%',
                        background: idx === 0 ? '#0284c7' : idx === 1 ? '#0ea5e9' : '#38bdf8',
                        borderRadius: 3,
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: '#64748b', marginTop: 4 }}>
                    <span>Parameter: {s.parameter}</span>
                    <span>Component Tolerance: ±{s.tolerance_pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
