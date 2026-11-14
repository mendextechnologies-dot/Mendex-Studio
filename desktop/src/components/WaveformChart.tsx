import React, { useEffect, useState, useMemo, useRef } from 'react';
import { api } from '../api/client';
import {
  Activity,
  Play,
  Eye,
  EyeOff,
  ZoomIn,
  RefreshCw,
  ExternalLink,
  Sliders,
  Ruler,
  Download,
  CheckCircle2,
  AlertTriangle,
  MoveHorizontal,
  Zap,
} from 'lucide-react';

interface WaveformPoint {
  time: number;
  [key: string]: number;
}

interface WaveformResponse {
  samples: WaveformPoint[];
  traces: string[];
  total_points?: number;
  metrics?: Record<string, { rms: number; p2p: number; mean: number; min: number; max: number }>;
  error?: string;
}

interface WaveformChartProps {
  revisionId: string;
  relativePath: string;
  title?: string;
  onOpenNative?: () => void;
  targetRippleMaxMv?: number | null;
}

const TRACE_COLORS = [
  '#06b6d4', // Cyan
  '#f59e0b', // Amber
  '#10b981', // Emerald
  '#ec4899', // Pink
  '#8b5cf6', // Purple
  '#3b82f6', // Blue
  '#f97316', // Orange
];

export const WaveformChart: React.FC<WaveformChartProps> = ({
  revisionId,
  relativePath,
  title = 'LTspice Transient Waveform Analysis',
  onOpenNative,
  targetRippleMaxMv,
}) => {
  const [data, setData] = useState<WaveformResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTraces, setActiveTraces] = useState<Record<string, boolean>>({});
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Dual-Cursor Measurement Calipers Mode
  const [cursorMode, setCursorMode] = useState<boolean>(true);
  const [activeCursor, setActiveCursor] = useState<'A' | 'B'>('A');
  const [cursorAIndex, setCursorAIndex] = useState<number | null>(null);
  const [cursorBIndex, setCursorBIndex] = useState<number | null>(null);
  const [isDraggingCursor, setIsDraggingCursor] = useState<'A' | 'B' | null>(null);

  const loadWaveform = () => {
    setLoading(true);
    setError(null);
    api.waveform(revisionId, relativePath)
      .then((res: WaveformResponse) => {
        if (res.error) {
          setError(res.error);
        } else {
          setData(res);
          const initialActive: Record<string, boolean> = {};
          (res.traces || []).forEach((t, i) => {
            initialActive[t] = i < 3; // Enable first 3 by default
          });
          setActiveTraces(initialActive);

          // Auto-initialize Cursors A and B around steady-state
          const smp = res.samples || [];
          if (smp.length > 10) {
            const idxA = Math.floor(smp.length * 0.75);
            const idxB = Math.min(idxA + Math.floor(smp.length * 0.12), smp.length - 1);
            setCursorAIndex(idxA);
            setCursorBIndex(idxB);
          }
        }
      })
      .catch((err: any) => {
        setError(err.message || String(err));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadWaveform();
  }, [revisionId, relativePath]);

  const samples = data?.samples || [];
  const traces = data?.traces || [];

  // Compute stats and bounds
  const { minT, maxT, traceBounds, stats } = useMemo(() => {
    if (!samples.length) {
      return { minT: 0, maxT: 1, traceBounds: {}, stats: {} };
    }
    const minT = samples[0].time;
    const maxT = samples[samples.length - 1].time;

    const bounds: Record<string, { min: number; max: number }> = {};
    const st: Record<string, { min: number; max: number; mean: number; p2p: number }> = {};

    traces.forEach((t) => {
      let min = Infinity;
      let max = -Infinity;
      let sum = 0;
      let count = 0;
      for (let i = 0; i < samples.length; i++) {
        const val = samples[i][t];
        if (val !== undefined && !isNaN(val)) {
          if (val < min) min = val;
          if (val > max) max = val;
          sum += val;
          count++;
        }
      }
      if (count > 0) {
        bounds[t] = { min, max };
        const mean = sum / count;
        st[t] = { min, max, mean, p2p: max - min };
      }
    });

    return { minT, maxT, traceBounds: bounds, stats: st };
  }, [samples, traces]);

  const toggleTrace = (t: string) => {
    setActiveTraces((prev) => ({ ...prev, [t]: !prev[t] }));
  };

  // Dimensions for SVG
  const width = 860;
  const height = 340;
  const padLeft = 70;
  const padRight = 30;
  const padTop = 24;
  const padBottom = 35;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  // Selected traces
  const visibleTraces = traces.filter((t) => activeTraces[t]);

  // Overall min/max across active traces
  const { yMin, yMax } = useMemo(() => {
    let yMin = Infinity;
    let yMax = -Infinity;
    visibleTraces.forEach((t) => {
      const b = traceBounds[t];
      if (b) {
        if (b.min < yMin) yMin = b.min;
        if (b.max > yMax) yMax = b.max;
      }
    });
    if (yMin === Infinity || yMax === -Infinity) {
      return { yMin: 0, yMax: 1 };
    }
    if (Math.abs(yMax - yMin) < 1e-9) {
      yMin -= 1;
      yMax += 1;
    } else {
      const margin = (yMax - yMin) * 0.08;
      yMin -= margin;
      yMax += margin;
    }
    return { yMin, yMax };
  }, [visibleTraces, traceBounds]);

  const scaleX = (t: number) => {
    if (maxT === minT) return padLeft;
    return padLeft + ((t - minT) / (maxT - minT)) * chartW;
  };

  const scaleY = (v: number) => {
    if (yMax === yMin) return padTop + chartH / 2;
    return padTop + chartH - ((v - yMin) / (yMax - yMin)) * chartH;
  };

  const formatTime = (seconds: number) => {
    if (Math.abs(seconds) < 1e-6) return `${(seconds * 1e9).toFixed(1)} ns`;
    if (Math.abs(seconds) < 1e-3) return `${(seconds * 1e6).toFixed(1)} µs`;
    if (Math.abs(seconds) < 1) return `${(seconds * 1e3).toFixed(2)} ms`;
    return `${seconds.toFixed(4)} s`;
  };

  const formatFrequency = (hz: number) => {
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(2)} MHz`;
    if (hz >= 1e3) return `${(hz / 1e3).toFixed(2)} kHz`;
    return `${hz.toFixed(1)} Hz`;
  };

  const formatValue = (v: number, traceName: string) => {
    const isCurrent = traceName.startsWith('I(');
    const unit = isCurrent ? 'A' : 'V';
    if (Math.abs(v) < 1e-3) return `${(v * 1e3).toFixed(2)} m${unit}`;
    return `${v.toFixed(3)} ${unit}`;
  };

  // Build SVG paths for each trace
  const tracePaths = useMemo(() => {
    const paths: Record<string, string> = {};
    visibleTraces.forEach((t) => {
      let d = '';
      for (let i = 0; i < samples.length; i++) {
        const pt = samples[i];
        const val = pt[t];
        if (val !== undefined && !isNaN(val)) {
          const x = scaleX(pt.time);
          const y = scaleY(val);
          d += i === 0 ? `M ${x.toFixed(2)} ${y.toFixed(2)}` : ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
        }
      }
      paths[t] = d;
    });
    return paths;
  }, [visibleTraces, samples, yMin, yMax, minT, maxT]);

  // Cursor Sample points
  const sampleA = cursorAIndex !== null && samples[cursorAIndex] ? samples[cursorAIndex] : null;
  const sampleB = cursorBIndex !== null && samples[cursorBIndex] ? samples[cursorBIndex] : null;

  // Measurement Calipers Math
  const caliperMetrics = useMemo(() => {
    if (!sampleA || !sampleB) return null;
    const dt = Math.abs(sampleB.time - sampleA.time);
    const freq = dt > 1e-12 ? 1 / dt : 0;

    // Delta across visible traces
    const traceDeltas: Record<string, { valA: number; valB: number; dv: number; slewRate: number }> = {};
    visibleTraces.forEach((t) => {
      const vA = sampleA[t] ?? 0;
      const vB = sampleB[t] ?? 0;
      const dv = vB - vA;
      const slewRate = dt > 1e-12 ? Math.abs(dv / dt) : 0; // V/s
      traceDeltas[t] = { valA: vA, valB: vB, dv, slewRate };
    });

    return { dt, freq, traceDeltas };
  }, [sampleA, sampleB, visibleTraces]);

  // Handle Mouse Events for Cursors
  const getIndexFromX = (clientX: number) => {
    if (!svgRef.current || !samples.length) return 0;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = clientX - rect.left;
    const relX = (mouseX / rect.width) * width;
    const clampedX = Math.max(padLeft, Math.min(width - padRight, relX));
    const ratio = (clampedX - padLeft) / chartW;
    const targetTime = minT + ratio * (maxT - minT);

    let bestIdx = 0;
    let minDiff = Infinity;
    for (let i = 0; i < samples.length; i++) {
      const diff = Math.abs(samples[i].time - targetTime);
      if (diff < minDiff) {
        minDiff = diff;
        bestIdx = i;
      }
    }
    return bestIdx;
  };

  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!cursorMode) return;
    const idx = getIndexFromX(e.clientX);
    if (activeCursor === 'A') {
      setCursorAIndex(idx);
      setIsDraggingCursor('A');
    } else {
      setCursorBIndex(idx);
      setIsDraggingCursor('B');
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isDraggingCursor === 'A') {
      setCursorAIndex(getIndexFromX(e.clientX));
      return;
    }
    if (isDraggingCursor === 'B') {
      setCursorBIndex(getIndexFromX(e.clientX));
      return;
    }

    // Normal Hover
    const idx = getIndexFromX(e.clientX);
    setHoverIndex(idx);
  };

  const handleMouseUp = () => {
    setIsDraggingCursor(null);
  };

  // Export SVG Capture
  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const svgStr = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `waveform_${relativePath.replace(/[\/\\]/g, '_')}_capture.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const hoverSample = hoverIndex !== null && samples[hoverIndex] ? samples[hoverIndex] : null;

  return (
    <div style={{ background: '#0b1120', borderRadius: 10, padding: 20, color: '#f8fafc', border: '1px solid #1e293b' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={18} color="#38bdf8" />
            <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>{title}</h4>
            {data?.total_points && (
              <span style={{ fontSize: 11, background: '#1e293b', color: '#94a3b8', padding: '2px 8px', borderRadius: 4 }}>
                {data.total_points.toLocaleString()} solver steps
              </span>
            )}
          </div>
          <span style={{ fontSize: 11, color: '#64748b', display: 'block', marginTop: 4 }}>
            File: <code>{relativePath}</code> • Downsampled to {samples.length} display vectors
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Cursor Toggle Button */}
          <button
            onClick={() => setCursorMode(!cursorMode)}
            style={{
              background: cursorMode ? 'rgba(59, 130, 246, 0.2)' : '#1e293b',
              border: `1px solid ${cursorMode ? '#3b82f6' : '#334155'}`,
              color: cursorMode ? '#60a5fa' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <Ruler size={13} />
            Dual Calipers {cursorMode ? '(ON)' : '(OFF)'}
          </button>

          <button
            onClick={handleExportSvg}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#e2e8f0',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            title="Export high-resolution SVG capture"
          >
            <Download size={13} /> SVG Capture
          </button>

          <button
            onClick={loadWaveform}
            disabled={loading}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#e2e8f0',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          {onOpenNative && (
            <button
              onClick={onOpenNative}
              style={{
                background: '#0284c7',
                border: 'none',
                color: '#fff',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <ExternalLink size={13} />
              Open in LTspice GUI
            </button>
          )}
        </div>
      </div>

      {/* Trace Toggles Bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        {traces.map((traceName, idx) => {
          const color = TRACE_COLORS[idx % TRACE_COLORS.length];
          const active = activeTraces[traceName];
          return (
            <button
              key={traceName}
              onClick={() => toggleTrace(traceName)}
              style={{
                background: active ? `${color}22` : '#1e293b',
                border: `1px solid ${active ? color : '#334155'}`,
                color: active ? color : '#64748b',
                padding: '4px 10px',
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.15s ease',
              }}
            >
              {active ? <Eye size={13} /> : <EyeOff size={13} />}
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
              {traceName}
            </button>
          );
        })}
      </div>

      {/* Dual Caliper Controls & Live HUD */}
      {cursorMode && caliperMetrics && sampleA && sampleB && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: 8,
            padding: '12px 16px',
            marginBottom: 14,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 14,
          }}
        >
          {/* Caliper Selector Radio */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Active Caliper:</span>
            <div style={{ display: 'flex', borderRadius: 4, overflow: 'hidden', border: '1px solid #334155' }}>
              <button
                onClick={() => setActiveCursor('A')}
                style={{
                  background: activeCursor === 'A' ? '#06b6d4' : '#1e293b',
                  color: activeCursor === 'A' ? '#0f172a' : '#06b6d4',
                  fontWeight: 700,
                  fontSize: 11,
                  padding: '4px 12px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Cursor A ({formatTime(sampleA.time)})
              </button>
              <button
                onClick={() => setActiveCursor('B')}
                style={{
                  background: activeCursor === 'B' ? '#f59e0b' : '#1e293b',
                  color: activeCursor === 'B' ? '#0f172a' : '#f59e0b',
                  fontWeight: 700,
                  fontSize: 11,
                  padding: '4px 12px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Cursor B ({formatTime(sampleB.time)})
              </button>
            </div>
            <span style={{ fontSize: 11, color: '#64748b' }}>(Click or drag on chart)</span>
          </div>

          {/* Mathematical Caliper Readout Ribbon */}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', fontFamily: 'monospace' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#94a3b8', fontSize: 11 }}>ΔT:</span>
              <strong style={{ color: '#38bdf8', fontSize: 13 }}>{formatTime(caliperMetrics.dt)}</strong>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#94a3b8', fontSize: 11 }}>1/ΔT (f):</span>
              <strong style={{ color: '#10b981', fontSize: 13 }}>{formatFrequency(caliperMetrics.freq)}</strong>
            </div>

            {visibleTraces.slice(0, 2).map((t) => {
              const d = caliperMetrics.traceDeltas[t];
              if (!d) return null;
              const idx = traces.indexOf(t);
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              return (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color: '#94a3b8', fontSize: 11 }}>Δ{t}:</span>
                  <strong style={{ color, fontSize: 13 }}>{formatValue(d.dv, t)}</strong>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Loading & Error States */}
      {loading && (
        <div style={{ height: height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
          <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginRight: 10 }} />
          Parsing high-resolution simulation vectors...
        </div>
      )}

      {error && !loading && (
        <div style={{ padding: 24, background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: 8, color: '#fca5a5', fontSize: 13 }}>
          <strong>Waveform Ingestion Error:</strong> {error}
        </div>
      )}

      {/* SVG Canvas Oscilloscope */}
      {!loading && !error && samples.length > 0 && (
        <div style={{ position: 'relative' }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${width} ${height}`}
            style={{ width: '100%', height: 'auto', background: '#070b14', borderRadius: 8, border: '1px solid #1e293b', cursor: cursorMode ? 'col-resize' : 'crosshair' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              setHoverIndex(null);
              setIsDraggingCursor(null);
            }}
          >
            {/* Horizontal Grid lines (5 ticks) */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((ratio) => {
              const y = padTop + ratio * chartH;
              const val = yMax - ratio * (yMax - yMin);
              return (
                <g key={`y-${ratio}`}>
                  <line x1={padLeft} y1={y} x2={width - padRight} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                  <text x={padLeft - 8} y={y + 4} textAnchor="end" fill="#64748b" fontSize="10" fontFamily="monospace">
                    {val >= 100 ? val.toFixed(0) : val >= 1 ? val.toFixed(1) : val.toFixed(3)}
                  </text>
                </g>
              );
            })}

            {/* Vertical Grid lines (5 ticks) */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((ratio) => {
              const x = padLeft + ratio * chartW;
              const t = minT + ratio * (maxT - minT);
              return (
                <g key={`x-${ratio}`}>
                  <line x1={x} y1={padTop} x2={x} y2={padTop + chartH} stroke="#1e293b" strokeDasharray="3 3" />
                  <text x={x} y={padTop + chartH + 18} textAnchor="middle" fill="#64748b" fontSize="10" fontFamily="monospace">
                    {formatTime(t)}
                  </text>
                </g>
              );
            })}

            {/* Axis borders */}
            <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + chartH} stroke="#334155" strokeWidth="1.5" />
            <line x1={padLeft} y1={padTop + chartH} x2={width - padRight} y2={padTop + chartH} stroke="#334155" strokeWidth="1.5" />

            {/* Signal Paths */}
            {visibleTraces.map((traceName) => {
              const idx = traces.indexOf(traceName);
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              return (
                <path
                  key={traceName}
                  d={tracePaths[traceName] || ''}
                  fill="none"
                  stroke={color}
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={0.92}
                />
              );
            })}

            {/* Caliper Cursor A */}
            {cursorMode && sampleA && (
              <g>
                <line
                  x1={scaleX(sampleA.time)}
                  y1={padTop}
                  x2={scaleX(sampleA.time)}
                  y2={padTop + chartH}
                  stroke="#06b6d4"
                  strokeWidth="2"
                  strokeDasharray="5 3"
                />
                <rect
                  x={scaleX(sampleA.time) - 14}
                  y={padTop - 18}
                  width="28"
                  height="16"
                  rx="3"
                  fill="#06b6d4"
                />
                <text
                  x={scaleX(sampleA.time)}
                  y={padTop - 6}
                  textAnchor="middle"
                  fill="#0f172a"
                  fontSize="10"
                  fontWeight="800"
                >
                  CA
                </text>
              </g>
            )}

            {/* Caliper Cursor B */}
            {cursorMode && sampleB && (
              <g>
                <line
                  x1={scaleX(sampleB.time)}
                  y1={padTop}
                  x2={scaleX(sampleB.time)}
                  y2={padTop + chartH}
                  stroke="#f59e0b"
                  strokeWidth="2"
                  strokeDasharray="5 3"
                />
                <rect
                  x={scaleX(sampleB.time) - 14}
                  y={padTop - 18}
                  width="28"
                  height="16"
                  rx="3"
                  fill="#f59e0b"
                />
                <text
                  x={scaleX(sampleB.time)}
                  y={padTop - 6}
                  textAnchor="middle"
                  fill="#0f172a"
                  fontSize="10"
                  fontWeight="800"
                >
                  CB
                </text>
              </g>
            )}

            {/* Measurement Tine / Interval Box between A and B */}
            {cursorMode && sampleA && sampleB && (
              <g>
                <rect
                  x={Math.min(scaleX(sampleA.time), scaleX(sampleB.time))}
                  y={padTop}
                  width={Math.abs(scaleX(sampleB.time) - scaleX(sampleA.time))}
                  height={chartH}
                  fill="rgba(59, 130, 246, 0.08)"
                />
              </g>
            )}

            {/* Hover Crosshair (when not dragging) */}
            {hoverSample && !isDraggingCursor && (
              <g>
                <line
                  x1={scaleX(hoverSample.time)}
                  y1={padTop}
                  x2={scaleX(hoverSample.time)}
                  y2={padTop + chartH}
                  stroke="#f8fafc"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                  opacity={0.4}
                />
              </g>
            )}
          </svg>
        </div>
      )}

      {/* Signal Statistics & Ripple Verification Table */}
      {!loading && !error && visibleTraces.length > 0 && (
        <div style={{ marginTop: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h5 style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', margin: 0 }}>
              Signal Steady-State Statistics & Numerical Ripple Verification
            </h5>
            {targetRippleMaxMv && (
              <span style={{ fontSize: 11, color: '#93c5fd' }}>
                Target Max Ripple Limit: <strong>{targetRippleMaxMv} mV</strong>
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10 }}>
            {visibleTraces.map((t) => {
              const sm = data?.metrics?.[t];
              const st = sm ? { mean: sm.mean, p2p: sm.p2p, min: sm.min, max: sm.max, rms: sm.rms } : stats[t];
              const idx = traces.indexOf(t);
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              if (!st) return null;

              // Ripple Percentage relative to mean
              const ripplePct = st.mean !== 0 ? Math.abs((st.p2p / st.mean) * 100) : 0;
              const isVout = t.toLowerCase().includes('vout') || t.toLowerCase().includes('hv');

              return (
                <div
                  key={t}
                  style={{
                    background: '#070b14',
                    border: '1px solid #1e293b',
                    borderLeft: `3px solid ${color}`,
                    borderRadius: 6,
                    padding: '10px 14px',
                    fontSize: 11,
                    fontFamily: 'monospace',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, color }}>{t}</span>
                    {isVout && ripplePct < 2.0 && (
                      <span style={{ fontSize: 9, padding: '2px 5px', borderRadius: 3, background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 700 }}>
                        ✓ CLEAN RIPPLE
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                    <span>Mean:</span>
                    <strong style={{ color: '#f1f5f9' }}>{formatValue(st.mean, t)}</strong>
                  </div>
                  {'rms' in st && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginTop: 2 }}>
                      <span>RMS:</span>
                      <strong style={{ color: '#f1f5f9' }}>{formatValue(st.rms, t)}</strong>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginTop: 2 }}>
                    <span>Ripple (pk-pk):</span>
                    <strong style={{ color: '#38bdf8' }}>{formatValue(st.p2p, t)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginTop: 2 }}>
                    <span>Ripple (%):</span>
                    <strong style={{ color: ripplePct < 2 ? '#10b981' : '#f59e0b' }}>{ripplePct.toFixed(2)}%</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginTop: 2 }}>
                    <span>Min / Max:</span>
                    <span style={{ color: '#cbd5e1' }}>
                      {formatValue(st.min, t)} / {formatValue(st.max, t)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
