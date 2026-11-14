import React, { useEffect, useState, useMemo, useRef } from 'react';
import { api } from '../api/client';
import { Activity, Play, Eye, EyeOff, ZoomIn, RefreshCw, ExternalLink } from 'lucide-react';

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
}) => {
  const [data, setData] = useState<WaveformResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTraces, setActiveTraces] = useState<Record<string, boolean>>({});
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

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
  const width = 800;
  const height = 320;
  const padLeft = 70;
  const padRight = 30;
  const padTop = 20;
  const padBottom = 35;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  // Selected traces
  const visibleTraces = traces.filter((t) => activeTraces[t]);

  // Overall min/max across active traces for unified or normalized scaling
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
    return `${seconds.toFixed(3)} s`;
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

  // Handle cursor hover
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || !samples.length) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const relX = (mouseX / rect.width) * width;
    if (relX < padLeft || relX > width - padRight) {
      setHoverIndex(null);
      return;
    }
    const ratio = (relX - padLeft) / chartW;
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
    setHoverIndex(bestIdx);
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

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
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
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
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

      {/* Trace Toggles */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
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
            style={{ width: '100%', height: 'auto', background: '#070b14', borderRadius: 8, border: '1px solid #1e293b', cursor: 'crosshair' }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIndex(null)}
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

            {/* Crosshair Cursor on Hover */}
            {hoverSample && (
              <g>
                <line
                  x1={scaleX(hoverSample.time)}
                  y1={padTop}
                  x2={scaleX(hoverSample.time)}
                  y2={padTop + chartH}
                  stroke="#f8fafc"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                  opacity={0.6}
                />
                {visibleTraces.map((traceName) => {
                  const val = hoverSample[traceName];
                  if (val === undefined || isNaN(val)) return null;
                  const idx = traces.indexOf(traceName);
                  const color = TRACE_COLORS[idx % TRACE_COLORS.length];
                  const cx = scaleX(hoverSample.time);
                  const cy = scaleY(val);
                  return (
                    <circle
                      key={`dot-${traceName}`}
                      cx={cx}
                      cy={cy}
                      r="4"
                      fill={color}
                      stroke="#0b1120"
                      strokeWidth="1.5"
                    />
                  );
                })}
              </g>
            )}
          </svg>

          {/* Tooltip Overlay */}
          {hoverSample && (
            <div
              style={{
                position: 'absolute',
                top: 10,
                right: 15,
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(8px)',
                padding: '8px 14px',
                borderRadius: 6,
                border: '1px solid #334155',
                fontSize: 11,
                fontFamily: 'monospace',
                pointerEvents: 'none',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              <div style={{ color: '#94a3b8', borderBottom: '1px solid #334155', paddingBottom: 4, marginBottom: 6 }}>
                t = {formatTime(hoverSample.time)}
              </div>
              {visibleTraces.map((traceName) => {
                const val = hoverSample[traceName];
                const idx = traces.indexOf(traceName);
                const color = TRACE_COLORS[idx % TRACE_COLORS.length];
                return (
                  <div key={traceName} style={{ display: 'flex', justifyContent: 'space-between', gap: 14, color }}>
                    <span>{traceName}:</span>
                    <strong>{formatValue(val, traceName)}</strong>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Signal Statistics Table */}
      {!loading && !error && visibleTraces.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h5 style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', marginBottom: 8 }}>
            Signal Steady-State Statistics
          </h5>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
            {visibleTraces.map((t) => {
              const sm = data?.metrics?.[t];
              const st = sm ? { mean: sm.mean, p2p: sm.p2p, min: sm.min, max: sm.max, rms: sm.rms } : stats[t];
              const idx = traces.indexOf(t);
              const color = TRACE_COLORS[idx % TRACE_COLORS.length];
              if (!st) return null;
              return (
                <div
                  key={t}
                  style={{
                    background: '#070b14',
                    border: '1px solid #1e293b',
                    borderLeft: `3px solid ${color}`,
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 11,
                    fontFamily: 'monospace',
                  }}
                >
                  <div style={{ fontWeight: 700, color, marginBottom: 4 }}>{t}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                    <span>Mean:</span>
                    <strong style={{ color: '#f1f5f9' }}>{formatValue(st.mean, t)}</strong>
                  </div>
                  {'rms' in st && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                      <span>RMS:</span>
                      <strong style={{ color: '#f1f5f9' }}>{formatValue(st.rms, t)}</strong>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                    <span>Ripple (pk-pk):</span>
                    <strong style={{ color: '#f1f5f9' }}>{formatValue(st.p2p, t)}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
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
