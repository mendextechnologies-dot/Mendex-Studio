import React, { useEffect, useState, useMemo, useRef } from 'react';
import { api } from '../api/client';
import type {
  ScopeMeasurementSummary,
  ScopeWaveformData,
  ScopeCorrelationReport,
} from '../api/types';
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
  Upload,
  FileText,
  Copy,
  Check,
  ChevronDown,
  Layers,
  Cpu,
  ShieldCheck,
  Radio,
  X,
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

const SCOPE_TRACE_COLORS = [
  '#22c55e', // Neon Green
  '#f43f5e', // Rose
  '#a855f7', // Vivid Purple
  '#eab308', // Vivid Yellow
];

export const WaveformChart: React.FC<WaveformChartProps> = ({
  revisionId,
  relativePath,
  title = 'LTspice Transient Waveform Analysis',
  onOpenNative,
  targetRippleMaxMv,
}) => {
  // --- View Mode ---
  const [viewMode, setViewMode] = useState<'sim' | 'scope' | 'overlay'>('sim');

  // --- Simulation Waveform State ---
  const [data, setData] = useState<WaveformResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTraces, setActiveTraces] = useState<Record<string, boolean>>({});
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // --- Oscilloscope Physical Measurements State ---
  const [scopeList, setScopeList] = useState<ScopeMeasurementSummary[]>([]);
  const [selectedScopeId, setSelectedScopeId] = useState<string | null>(null);
  const [scopeData, setScopeData] = useState<ScopeWaveformData | null>(null);
  const [activeScopeTraces, setActiveScopeTraces] = useState<Record<string, boolean>>({});
  const [correlationReport, setCorrelationReport] = useState<ScopeCorrelationReport | null>(null);
  const [correlating, setCorrelating] = useState<boolean>(false);

  // --- Ingestion Modal State ---
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadText, setUploadText] = useState<string>('');
  const [uploadOperator, setUploadOperator] = useState<string>('Lead Hardware Engineer');
  const [uploadNotes, setUploadNotes] = useState<string>('Bench oscilloscope verification capture');
  const [channelMapCh1, setChannelMapCh1] = useState<string>('V(vout)');
  const [channelMapCh2, setChannelMapCh2] = useState<string>('V(pri_drain)');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState<boolean>(false);

  // --- Dual-Cursor Measurement Calipers ---
  const [cursorMode, setCursorMode] = useState<boolean>(true);
  const [activeCursor, setActiveCursor] = useState<'A' | 'B'>('A');
  const [cursorAIndex, setCursorAIndex] = useState<number | null>(null);
  const [cursorBIndex, setCursorBIndex] = useState<number | null>(null);
  const [isDraggingCursor, setIsDraggingCursor] = useState<'A' | 'B' | null>(null);

  // --- Load Simulation Data ---
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

  // --- Load Scope Measurements List ---
  const loadScopeList = async () => {
    try {
      const list = await api.listScopeMeasurements(revisionId);
      setScopeList(list || []);
      if (list && list.length > 0 && !selectedScopeId) {
        setSelectedScopeId(list[0].measurement_id);
      }
    } catch (err) {
      console.warn('Could not load scope measurements:', err);
    }
  };

  // --- Load Specific Scope Waveform ---
  const loadScopeWaveform = async (measId: string) => {
    try {
      const res = await api.getScopeWaveform({
        revisionId,
        measurementId: measId,
        limit: 2000,
        decimate: true,
      });
      if (res && res.samples) {
        setScopeData(res);
        const active: Record<string, boolean> = {};
        (res.traces || []).forEach((tr) => {
          active[tr] = true;
        });
        setActiveScopeTraces(active);
      }
    } catch (err) {
      console.warn('Failed to load scope waveform:', err);
    }
  };

  // --- Run Real-vs-Simulated Correlation ---
  const runCorrelation = async (measId: string) => {
    setCorrelating(true);
    try {
      const mapping: Record<string, string> = {
        CH1: channelMapCh1 || 'V(vout)',
        CH2: channelMapCh2 || 'V(pri_drain)',
      };
      const report = await api.correlateScopeWaveform({
        revisionId,
        measurementId: measId,
        simRelativePath: relativePath,
        channelMapping: mapping,
        targetTolerancePct: 5.0,
      });
      setCorrelationReport(report);
    } catch (err) {
      console.warn('Correlation failed:', err);
    } finally {
      setCorrelating(false);
    }
  };

  useEffect(() => {
    loadWaveform();
    loadScopeList();
  }, [revisionId, relativePath]);

  useEffect(() => {
    if (selectedScopeId) {
      loadScopeWaveform(selectedScopeId);
      if (viewMode === 'overlay') {
        runCorrelation(selectedScopeId);
      }
    }
  }, [selectedScopeId, viewMode]);

  // Handle File Upload Change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadFile(file);
    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadText((event.target?.result as string) || '');
    };
    reader.readAsText(file);
  };

  // Submit Scope CSV Ingestion
  const handleIngestSubmit = async () => {
    if (!uploadText || !uploadFile) {
      setUploadError('Please select a valid oscilloscope CSV file.');
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      const res = await api.ingestScopeCsv({
        revisionId,
        filename: uploadFile.name,
        content: uploadText,
        channelMapping: {
          CH1: channelMapCh1,
          CH2: channelMapCh2,
        },
        operator: uploadOperator,
        notes: uploadNotes,
      });
      if (res.success) {
        setIsModalOpen(false);
        setUploadFile(null);
        setUploadText('');
        await loadScopeList();
        setSelectedScopeId(res.measurement_id);
        setViewMode('overlay');
      } else {
        setUploadError('Ingestion failed. Ensure the CSV contains valid numerical waveform columns.');
      }
    } catch (err: any) {
      setUploadError(err.message || String(err));
    } finally {
      setIsUploading(false);
    }
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2500);
  };

  // --- Active Samples and Bounds ---
  const simSamples = data?.samples || [];
  const simTraces = data?.traces || [];
  const scopeSamples = scopeData?.samples || [];
  const scopeTraces = scopeData?.traces || [];

  const activeSampleSet = viewMode === 'scope' ? scopeSamples : simSamples;

  const { minT, maxT, traceBounds, stats } = useMemo(() => {
    if (!activeSampleSet.length) {
      return { minT: 0, maxT: 1, traceBounds: {}, stats: {} };
    }
    const minT = activeSampleSet[0].time;
    const maxT = activeSampleSet[activeSampleSet.length - 1].time;

    const bounds: Record<string, { min: number; max: number }> = {};
    const st: Record<string, { min: number; max: number; mean: number; p2p: number }> = {};

    const targetTraces = viewMode === 'scope' ? scopeTraces : simTraces;

    targetTraces.forEach((t) => {
      let min = Infinity;
      let max = -Infinity;
      let sum = 0;
      let count = 0;
      for (let i = 0; i < activeSampleSet.length; i++) {
        const val = activeSampleSet[i][t];
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
  }, [activeSampleSet, simTraces, scopeTraces, viewMode]);

  const toggleTrace = (t: string) => {
    setActiveTraces((prev) => ({ ...prev, [t]: !prev[t] }));
  };

  const toggleScopeTrace = (t: string) => {
    setActiveScopeTraces((prev) => ({ ...prev, [t]: !prev[t] }));
  };

  // Dimensions for SVG
  const width = 860;
  const height = 360;
  const padLeft = 70;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 45;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const visibleTraces = useMemo(() => {
    return simTraces.filter((t) => activeTraces[t]);
  }, [simTraces, activeTraces]);

  const visibleScopeTraces = useMemo(() => {
    return scopeTraces.filter((t) => activeScopeTraces[t]);
  }, [scopeTraces, activeScopeTraces]);

  // Overall Y-Bounds across visible traces
  const { globalMinY, globalMaxY } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    if (viewMode === 'sim' || viewMode === 'overlay') {
      visibleTraces.forEach((t) => {
        const b = traceBounds[t];
        if (b) {
          if (b.min < min) min = b.min;
          if (b.max > max) max = b.max;
        }
      });
    }

    if (viewMode === 'scope' || viewMode === 'overlay') {
      visibleScopeTraces.forEach((t) => {
        const smp = scopeSamples;
        for (let i = 0; i < smp.length; i++) {
          const v = smp[i][t];
          if (v !== undefined && !isNaN(v)) {
            if (v < min) min = v;
            if (v > max) max = v;
          }
        }
      });
    }

    if (min === Infinity || max === -Infinity) {
      return { globalMinY: 0, globalMaxY: 10 };
    }
    const span = max - min || 1;
    return {
      globalMinY: min - span * 0.08,
      globalMaxY: max + span * 0.08,
    };
  }, [visibleTraces, visibleScopeTraces, traceBounds, scopeSamples, viewMode]);

  // Scaling helpers
  const scaleX = (t: number) => {
    if (maxT === minT) return padLeft;
    return padLeft + ((t - minT) / (maxT - minT)) * chartW;
  };

  const scaleY = (v: number) => {
    if (globalMaxY === globalMinY) return padTop + chartH / 2;
    return padTop + chartH - ((v - globalMinY) / (globalMaxY - globalMinY)) * chartH;
  };

  const invScaleX = (x: number) => {
    const clampedX = Math.max(padLeft, Math.min(x, padLeft + chartW));
    return minT + ((clampedX - padLeft) / chartW) * (maxT - minT);
  };

  const findClosestIndex = (timeVal: number, smp: WaveformPoint[]) => {
    if (!smp.length) return 0;
    let low = 0;
    let high = smp.length - 1;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      if (smp[mid].time < timeVal) low = mid + 1;
      else high = mid - 1;
    }
    const idx1 = Math.max(0, Math.min(low, smp.length - 1));
    const idx2 = Math.max(0, Math.min(high, smp.length - 1));
    return Math.abs(smp[idx1].time - timeVal) < Math.abs(smp[idx2].time - timeVal) ? idx1 : idx2;
  };

  // Format Helpers
  const formatTime = (t: number) => {
    const absT = Math.abs(t);
    if (absT === 0) return '0 s';
    if (absT >= 1) return `${t.toFixed(3)} s`;
    if (absT >= 1e-3) return `${(t * 1e3).toFixed(2)} ms`;
    if (absT >= 1e-6) return `${(t * 1e6).toFixed(2)} µs`;
    return `${(t * 1e9).toFixed(1)} ns`;
  };

  const formatFreq = (hz: number) => {
    if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`;
    if (hz >= 1e3) return `${(hz / 1e3).toFixed(2)} kHz`;
    return `${hz.toFixed(1)} Hz`;
  };

  const formatValue = (v: number, traceName = '') => {
    const isCurrent = traceName.startsWith('I(');
    const unit = isCurrent ? 'A' : 'V';
    const absV = Math.abs(v);
    if (absV === 0) return `0 ${unit}`;
    if (absV >= 1000) return `${(v / 1e3).toFixed(2)} k${unit}`;
    if (absV >= 1) return `${v.toFixed(3)} ${unit}`;
    if (absV >= 1e-3) return `${(v * 1e3).toFixed(2)} m${unit}`;
    return `${(v * 1e6).toFixed(1)} µ${unit}`;
  };

  // SVG Export
  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const svgEl = svgRef.current;
    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgEl);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `waveform_${viewMode}_${new Date().toISOString().slice(0, 10)}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Calipers
  const sampleA = cursorAIndex !== null && activeSampleSet[cursorAIndex] ? activeSampleSet[cursorAIndex] : null;
  const sampleB = cursorBIndex !== null && activeSampleSet[cursorBIndex] ? activeSampleSet[cursorBIndex] : null;

  const caliperMetrics = useMemo(() => {
    if (!sampleA || !sampleB) return null;
    const dt = Math.abs(sampleB.time - sampleA.time);
    const freq = dt > 0 ? 1 / dt : 0;
    const deltas: Record<string, { va: number; vb: number; dv: number }> = {};

    const targetTraces = viewMode === 'scope' ? visibleScopeTraces : visibleTraces;
    targetTraces.forEach((t) => {
      const va = sampleA[t] ?? 0;
      const vb = sampleB[t] ?? 0;
      deltas[t] = { va, vb, dv: vb - va };
    });

    return { dt, freq, deltas };
  }, [sampleA, sampleB, visibleTraces, visibleScopeTraces, viewMode]);

  // Handle Chart Interaction
  const handleSvgPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!cursorMode || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const timeVal = invScaleX(mouseX);
    const idx = findClosestIndex(timeVal, activeSampleSet);

    if (activeCursor === 'A') {
      setCursorAIndex(idx);
      setIsDraggingCursor('A');
    } else {
      setCursorBIndex(idx);
      setIsDraggingCursor('B');
    }
  };

  const handleSvgPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const timeVal = invScaleX(mouseX);
    const idx = findClosestIndex(timeVal, activeSampleSet);

    if (isDraggingCursor) {
      if (isDraggingCursor === 'A') setCursorAIndex(idx);
      if (isDraggingCursor === 'B') setCursorBIndex(idx);
    } else {
      setHoverIndex(idx);
    }
  };

  const handleSvgPointerUp = () => {
    setIsDraggingCursor(null);
  };

  const hoverSample = hoverIndex !== null && activeSampleSet[hoverIndex] ? activeSampleSet[hoverIndex] : null;

  return (
    <div
      style={{
        background: '#0b1120',
        borderRadius: 8,
        border: '1px solid #1e293b',
        padding: 16,
        color: '#f8fafc',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      }}
    >
      {/* 1. Header Bar with Segmented View Control */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          borderBottom: '1px solid #1e293b',
          paddingBottom: 14,
          marginBottom: 14,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid #06b6d4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
            }}
          >
            <Activity size={18} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>{title}</h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
              <span style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>{relativePath}</span>
              <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#1e293b', color: '#94a3b8' }}>
                {viewMode === 'overlay' ? 'Sim vs Measured Overlay' : viewMode === 'scope' ? 'Lab Oscilloscope' : 'LTspice Transient'}
              </span>
            </div>
          </div>
        </div>

        {/* View Mode Segmented Controls */}
        <div style={{ display: 'flex', background: '#070b14', padding: 3, borderRadius: 6, border: '1px solid #1e293b' }}>
          <button
            onClick={() => setViewMode('sim')}
            style={{
              background: viewMode === 'sim' ? '#1e293b' : 'transparent',
              color: viewMode === 'sim' ? '#38bdf8' : '#64748b',
              fontWeight: 700,
              fontSize: 11.5,
              padding: '5px 12px',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Zap size={13} /> Simulation
          </button>
          <button
            onClick={() => setViewMode('scope')}
            style={{
              background: viewMode === 'scope' ? '#1e293b' : 'transparent',
              color: viewMode === 'scope' ? '#22c55e' : '#64748b',
              fontWeight: 700,
              fontSize: 11.5,
              padding: '5px 12px',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Radio size={13} /> Scope Capture
          </button>
          <button
            onClick={() => setViewMode('overlay')}
            style={{
              background: viewMode === 'overlay' ? '#1e293b' : 'transparent',
              color: viewMode === 'overlay' ? '#ec4899' : '#64748b',
              fontWeight: 700,
              fontSize: 11.5,
              padding: '5px 12px',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Layers size={13} /> Overlay (Sim vs Real)
          </button>
        </div>

        {/* Scope Actions & Upload Button */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Scope Selector dropdown if captures exist */}
          {scopeList.length > 0 && (
            <select
              value={selectedScopeId || ''}
              onChange={(e) => setSelectedScopeId(e.target.value)}
              style={{
                background: '#0f172a',
                border: '1px solid #334155',
                color: '#e2e8f0',
                fontSize: 11.5,
                padding: '5px 8px',
                borderRadius: 6,
                cursor: 'pointer',
              }}
            >
              {scopeList.map((sc) => (
                <option key={sc.measurement_id} value={sc.measurement_id}>
                  {sc.original_filename} ({sc.vendor})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              background: 'linear-gradient(180deg, #16a34a 0%, #15803d 100%)',
              border: 'none',
              color: '#fff',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }}
          >
            <Upload size={13} /> Ingest Scope CSV
          </button>

          <button
            onClick={() => setCursorMode(!cursorMode)}
            style={{
              background: cursorMode ? 'rgba(6, 182, 212, 0.2)' : '#1e293b',
              border: `1px solid ${cursorMode ? '#06b6d4' : '#334155'}`,
              color: cursorMode ? '#06b6d4' : '#94a3b8',
              padding: '6px 10px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            title="Toggle Dual-Cursor Calipers"
          >
            <Ruler size={13} /> Calipers
          </button>

          <button
            onClick={handleExportSvg}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#cbd5e1',
              padding: '6px 10px',
              borderRadius: 6,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            title="Export high-resolution SVG capture"
          >
            <Download size={13} /> SVG
          </button>

          <button
            onClick={loadWaveform}
            disabled={loading}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              color: '#e2e8f0',
              padding: '6px 10px',
              borderRadius: 6,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* 2. Trace Toggles Bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12, alignItems: 'center' }}>
        {/* Simulation Traces */}
        {(viewMode === 'sim' || viewMode === 'overlay') &&
          simTraces.map((traceName, idx) => {
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
                  padding: '3px 10px',
                  borderRadius: 20,
                  fontSize: 11.5,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {active ? <Eye size={12} /> : <EyeOff size={12} />}
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                <span>Sim: {traceName}</span>
              </button>
            );
          })}

        {/* Physical Scope Traces */}
        {(viewMode === 'scope' || viewMode === 'overlay') &&
          scopeTraces.map((traceName, idx) => {
            const color = SCOPE_TRACE_COLORS[idx % SCOPE_TRACE_COLORS.length];
            const active = activeScopeTraces[traceName];
            return (
              <button
                key={traceName}
                onClick={() => toggleScopeTrace(traceName)}
                style={{
                  background: active ? `${color}25` : '#1e293b',
                  border: `1px solid ${active ? color : '#334155'}`,
                  color: active ? color : '#64748b',
                  padding: '3px 10px',
                  borderRadius: 20,
                  fontSize: 11.5,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {active ? <Eye size={12} /> : <EyeOff size={12} />}
                <span style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
                <span>Real: {traceName}</span>
              </button>
            );
          })}
      </div>

      {/* 3. Dual Caliper Controls & Live HUD */}
      {cursorMode && caliperMetrics && sampleA && sampleB && (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 12,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Active Caliper:
            </span>
            <div style={{ display: 'flex', borderRadius: 4, overflow: 'hidden', border: '1px solid #334155' }}>
              <button
                onClick={() => setActiveCursor('A')}
                style={{
                  background: activeCursor === 'A' ? '#06b6d4' : '#1e293b',
                  color: activeCursor === 'A' ? '#0f172a' : '#06b6d4',
                  fontWeight: 700,
                  fontSize: 11,
                  padding: '3px 10px',
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
                  padding: '3px 10px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Cursor B ({formatTime(sampleB.time)})
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontFamily: 'monospace', fontSize: 11.5 }}>
            <div>
              <span style={{ color: '#64748b' }}>ΔT: </span>
              <strong style={{ color: '#38bdf8' }}>{formatTime(caliperMetrics.dt)}</strong>
            </div>
            <div>
              <span style={{ color: '#64748b' }}>Frequency: </span>
              <strong style={{ color: '#34d399' }}>{formatFreq(caliperMetrics.freq)}</strong>
            </div>
          </div>
        </div>
      )}

      {/* 4. Main SVG Waveform Canvas */}
      {loading ? (
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
          <RefreshCw size={24} className="animate-spin" />
          <span style={{ marginLeft: 8 }}>Loading waveforms...</span>
        </div>
      ) : error ? (
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f43f5e' }}>
          <AlertTriangle size={24} />
          <span style={{ marginLeft: 8 }}>{error}</span>
        </div>
      ) : (
        <div style={{ position: 'relative', overflow: 'hidden', borderRadius: 6, background: '#070b14' }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${width} ${height}`}
            style={{ width: '100%', height: 'auto', display: 'block', cursor: cursorMode ? 'crosshair' : 'default' }}
            onPointerDown={handleSvgPointerDown}
            onPointerMove={handleSvgPointerMove}
            onPointerUp={handleSvgPointerUp}
          >
            {/* Grid Lines */}
            {[0, 0.25, 0.5, 0.75, 1.0].map((frac) => {
              const y = padTop + chartH * frac;
              const val = globalMaxY - frac * (globalMaxY - globalMinY);
              return (
                <g key={`y-grid-${frac}`}>
                  <line x1={padLeft} y1={y} x2={padLeft + chartW} y2={y} stroke="#1e293b" strokeWidth="1" strokeDasharray="3 3" />
                  <text x={padLeft - 8} y={y + 4} fill="#64748b" fontSize="10" textAnchor="end" fontFamily="monospace">
                    {formatValue(val)}
                  </text>
                </g>
              );
            })}

            {[0, 0.25, 0.5, 0.75, 1.0].map((frac) => {
              const x = padLeft + chartW * frac;
              const t = minT + frac * (maxT - minT);
              return (
                <g key={`x-grid-${frac}`}>
                  <line x1={x} y1={padTop} x2={x} y2={padTop + chartH} stroke="#1e293b" strokeWidth="1" strokeDasharray="3 3" />
                  <text x={x} y={padTop + chartH + 16} fill="#64748b" fontSize="10" textAnchor="middle" fontFamily="monospace">
                    {formatTime(t)}
                  </text>
                </g>
              );
            })}

            {/* Axes Border */}
            <rect x={padLeft} y={padTop} width={chartW} height={chartH} fill="none" stroke="#334155" strokeWidth="1" />

            {/* 1. Simulation Waveform Traces (Dashed if in overlay mode) */}
            {(viewMode === 'sim' || viewMode === 'overlay') &&
              visibleTraces.map((t) => {
                const idx = simTraces.indexOf(t);
                const color = TRACE_COLORS[idx % TRACE_COLORS.length];
                const smp = simSamples;
                let pathD = '';
                for (let i = 0; i < smp.length; i++) {
                  const val = smp[i][t];
                  if (val !== undefined && !isNaN(val)) {
                    const x = scaleX(smp[i].time);
                    const y = scaleY(val);
                    pathD += `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)} `;
                  }
                }
                return (
                  <path
                    key={`sim-${t}`}
                    d={pathD}
                    fill="none"
                    stroke={color}
                    strokeWidth={viewMode === 'overlay' ? '1.8' : '2'}
                    strokeDasharray={viewMode === 'overlay' ? '4 2' : 'none'}
                    opacity={viewMode === 'overlay' ? 0.75 : 1}
                  />
                );
              })}

            {/* 2. Physical Oscilloscope Waveform Traces (Solid vivid lines) */}
            {(viewMode === 'scope' || viewMode === 'overlay') &&
              visibleScopeTraces.map((t) => {
                const idx = scopeTraces.indexOf(t);
                const color = SCOPE_TRACE_COLORS[idx % SCOPE_TRACE_COLORS.length];
                const smp = scopeSamples;
                let pathD = '';
                for (let i = 0; i < smp.length; i++) {
                  const val = smp[i][t];
                  if (val !== undefined && !isNaN(val)) {
                    const x = scaleX(smp[i].time);
                    const y = scaleY(val);
                    pathD += `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)} `;
                  }
                }
                return (
                  <path
                    key={`scope-${t}`}
                    d={pathD}
                    fill="none"
                    stroke={color}
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                );
              })}

            {/* Calipers Vertical Lines */}
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
                <rect x={scaleX(sampleA.time) - 12} y={padTop - 18} width="24" height="16" rx="3" fill="#06b6d4" />
                <text x={scaleX(sampleA.time)} y={padTop - 6} fill="#0f172a" fontSize="10" fontWeight="bold" textAnchor="middle">
                  A
                </text>
              </g>
            )}

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
                <rect x={scaleX(sampleB.time) - 12} y={padTop - 18} width="24" height="16" rx="3" fill="#f59e0b" />
                <text x={scaleX(sampleB.time)} y={padTop - 6} fill="#0f172a" fontSize="10" fontWeight="bold" textAnchor="middle">
                  B
                </text>
              </g>
            )}

            {/* Hover Indicator */}
            {hoverSample && (
              <line
                x1={scaleX(hoverSample.time)}
                y1={padTop}
                x2={scaleX(hoverSample.time)}
                y2={padTop + chartH}
                stroke="#fff"
                strokeWidth="1"
                strokeDasharray="2 2"
                opacity={0.5}
              />
            )}
          </svg>
        </div>
      )}

      {/* 5. Real-vs-Simulated Correlation Telemetry Card (When Overlay Active) */}
      {viewMode === 'overlay' && (
        <div
          style={{
            marginTop: 14,
            padding: 14,
            background: '#070b14',
            border: '1px solid #1e293b',
            borderRadius: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: 4,
                  background:
                    correlationReport?.status === 'CORRELATED_PASS'
                      ? 'rgba(34, 197, 94, 0.2)'
                      : correlationReport?.status === 'WARNING_DEVIATION'
                      ? 'rgba(245, 158, 11, 0.2)'
                      : 'rgba(244, 63, 94, 0.2)',
                  color:
                    correlationReport?.status === 'CORRELATED_PASS'
                      ? '#22c55e'
                      : correlationReport?.status === 'WARNING_DEVIATION'
                      ? '#f59e0b'
                      : '#f43f5e',
                  border: `1px solid ${
                    correlationReport?.status === 'CORRELATED_PASS'
                      ? '#22c55e'
                      : correlationReport?.status === 'WARNING_DEVIATION'
                      ? '#f59e0b'
                      : '#f43f5e'
                  }`,
                }}
              >
                {correlationReport?.status || 'CORRELATING...'}
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                Physical Instrument Correlation Analysis
              </span>
            </div>

            {correlationReport?.measurement_sha256 && (
              <button
                onClick={() => handleCopySha(correlationReport.measurement_sha256)}
                style={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 10.5,
                  fontFamily: 'monospace',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
                title="Copy SHA-256 Digest of raw oscilloscope capture"
              >
                {copiedSha ? <Check size={11} color="#22c55e" /> : <Copy size={11} />}
                <span>SHA-256: {correlationReport.measurement_sha256.slice(0, 16)}...</span>
              </button>
            )}
          </div>

          {correlating ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
              <RefreshCw size={16} className="animate-spin" style={{ display: 'inline', marginRight: 6 }} />
              Correlating physical measurements against LTspice vectors...
            </div>
          ) : correlationReport?.channel_correlations?.length ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #1e293b', color: '#64748b' }}>
                    <th style={{ padding: '6px 8px' }}>Channel Mapping</th>
                    <th style={{ padding: '6px 8px' }}>Simulated DC</th>
                    <th style={{ padding: '6px 8px' }}>Measured DC</th>
                    <th style={{ padding: '6px 8px' }}>Δ DC Error</th>
                    <th style={{ padding: '6px 8px' }}>Ripple Match</th>
                    <th style={{ padding: '6px 8px' }}>Pearson R²</th>
                    <th style={{ padding: '6px 8px' }}>Grade</th>
                  </tr>
                </thead>
                <tbody>
                  {correlationReport.channel_correlations.map((ch, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #0f172a' }}>
                      <td style={{ padding: '6px 8px', fontWeight: 700, color: '#38bdf8' }}>{ch.channel}</td>
                      <td style={{ padding: '6px 8px', fontFamily: 'monospace' }}>{ch.dc_simulated.toFixed(3)} V</td>
                      <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: '#22c55e' }}>
                        {ch.dc_measured.toFixed(3)} V
                      </td>
                      <td style={{ padding: '6px 8px', fontFamily: 'monospace' }}>
                        {ch.dc_error_percent.toFixed(2)}% ({ch.dc_delta_abs.toFixed(3)} V)
                      </td>
                      <td style={{ padding: '6px 8px', fontFamily: 'monospace' }}>
                        Sim: {ch.ripple_simulated_pk_pk.toFixed(3)}V / Meas: {ch.ripple_measured_pk_pk.toFixed(3)}V
                      </td>
                      <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontWeight: 700 }}>
                        {(ch.r_squared * 100).toFixed(1)}%
                      </td>
                      <td style={{ padding: '6px 8px' }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: 3,
                            background:
                              ch.status === 'CORRELATED_PASS'
                                ? 'rgba(34, 197, 94, 0.2)'
                                : ch.status === 'WARNING_DEVIATION'
                                ? 'rgba(245, 158, 11, 0.2)'
                                : 'rgba(244, 63, 94, 0.2)',
                            color:
                              ch.status === 'CORRELATED_PASS'
                                ? '#22c55e'
                                : ch.status === 'WARNING_DEVIATION'
                                ? '#f59e0b'
                                : '#f43f5e',
                          }}
                        >
                          {ch.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ fontSize: 11.5, color: '#64748b' }}>
              No correlation records computed. Ingest an oscilloscope capture to verify hardware against simulation.
            </div>
          )}
        </div>
      )}

      {/* 6. Ingestion Modal Drawer */}
      {isModalOpen && (
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
            padding: 20,
          }}
        >
          <div
            style={{
              background: '#0b1120',
              border: '1px solid #334155',
              borderRadius: 10,
              width: '100%',
              maxWidth: 580,
              padding: 24,
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 6,
                    background: 'rgba(34, 197, 94, 0.15)',
                    border: '1px solid #22c55e',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#22c55e',
                  }}
                >
                  <Upload size={16} />
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                    Ingest Oscilloscope Waveform Capture
                  </h4>
                  <span style={{ fontSize: 11, color: '#64748b' }}>
                    Tektronix, Keysight, Rigol, Siglent, or Standard CSV format
                  </span>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {uploadError && (
              <div
                style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid #f43f5e',
                  borderRadius: 6,
                  padding: '8px 12px',
                  marginBottom: 14,
                  fontSize: 12,
                  color: '#f43f5e',
                }}
              >
                {uploadError}
              </div>
            )}

            {/* Dropzone File Input */}
            <div
              style={{
                border: '2px dashed #334155',
                borderRadius: 8,
                padding: '24px 16px',
                textAlign: 'center',
                background: '#070b14',
                marginBottom: 16,
                cursor: 'pointer',
              }}
              onClick={() => document.getElementById('scope-csv-file-input')?.click()}
            >
              <input
                id="scope-csv-file-input"
                type="file"
                accept=".csv,.txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <FileText size={32} color={uploadFile ? '#22c55e' : '#64748b'} style={{ margin: '0 auto 8px auto' }} />
              {uploadFile ? (
                <div>
                  <strong style={{ color: '#22c55e', fontSize: 13 }}>{uploadFile.name}</strong>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                    {(uploadFile.size / 1024).toFixed(1)} KB • Ready for Ingestion & Hash Signing
                  </div>
                </div>
              ) : (
                <div>
                  <span style={{ fontSize: 13, color: '#f8fafc', fontWeight: 600 }}>
                    Click or Drag & Drop Oscilloscope CSV File
                  </span>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    Supports multi-column time/voltage vectors up to 50 MB
                  </div>
                </div>
              )}
            </div>

            {/* Ingestion Parameters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
              <div>
                <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                  Lead Test Engineer:
                </label>
                <input
                  type="text"
                  value={uploadOperator}
                  onChange={(e) => setUploadOperator(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#070b14',
                    border: '1px solid #334155',
                    borderRadius: 4,
                    padding: '6px 8px',
                    fontSize: 11.5,
                    color: '#fff',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                  CH1 Target Trace:
                </label>
                <select
                  value={channelMapCh1}
                  onChange={(e) => setChannelMapCh1(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#070b14',
                    border: '1px solid #334155',
                    borderRadius: 4,
                    padding: '6px 8px',
                    fontSize: 11.5,
                    color: '#fff',
                  }}
                >
                  {simTraces.map((tr) => (
                    <option key={tr} value={tr}>
                      {tr}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Verification Protocol Notes:
              </label>
              <input
                type="text"
                value={uploadNotes}
                onChange={(e) => setUploadNotes(e.target.value)}
                style={{
                  width: '100%',
                  background: '#070b14',
                  border: '1px solid #334155',
                  borderRadius: 4,
                  padding: '6px 8px',
                  fontSize: 11.5,
                  color: '#fff',
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{
                  background: '#1e293b',
                  border: '1px solid #334155',
                  color: '#cbd5e1',
                  padding: '6px 14px',
                  borderRadius: 6,
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleIngestSubmit}
                disabled={isUploading || !uploadFile}
                style={{
                  background: isUploading ? '#334155' : 'linear-gradient(180deg, #16a34a 0%, #15803d 100%)',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 16px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {isUploading ? (
                  <>
                    <RefreshCw size={13} className="animate-spin" /> Ingesting & Signing...
                  </>
                ) : (
                  <>
                    <ShieldCheck size={14} /> Ingest & Cryptographically Register
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
