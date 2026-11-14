import React, { useEffect, useState, useMemo, useRef } from 'react';
import { api } from '../api/client';
import {
  Layers,
  Eye,
  EyeOff,
  Sliders,
  Download,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Crosshair,
  CheckCircle2,
  AlertTriangle,
  Folder,
  Hash,
  Activity,
  Layers2,
  FileCode,
  ShieldAlert,
  Ruler,
  Magnet,
  Trash2,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react';

export interface SnapPoint {
  x: number;
  y: number;
  type: 'pad' | 'drill' | 'track' | 'edge';
  label: string;
}

export interface MeasurementPoint {
  x: number;
  y: number;
  label?: string;
  type?: 'pad' | 'drill' | 'track' | 'edge' | 'free';
}

export interface ClearanceRule {
  minVoltage: number;
  maxVoltage: number;
  ipc2221_external_bare: number; // mm
  ipc2221_internal: number; // mm
  iec60664_basic: number; // mm (Material Group IIIa, PD2)
  iec60664_reinforced: number; // mm
}

export const CLEARANCE_RULES: ClearanceRule[] = [
  { minVoltage: 0, maxVoltage: 15, ipc2221_external_bare: 0.10, ipc2221_internal: 0.05, iec60664_basic: 0.80, iec60664_reinforced: 1.60 },
  { minVoltage: 16, maxVoltage: 30, ipc2221_external_bare: 0.10, ipc2221_internal: 0.05, iec60664_basic: 1.00, iec60664_reinforced: 2.00 },
  { minVoltage: 31, maxVoltage: 50, ipc2221_external_bare: 0.60, ipc2221_internal: 0.10, iec60664_basic: 1.20, iec60664_reinforced: 2.40 },
  { minVoltage: 51, maxVoltage: 100, ipc2221_external_bare: 0.60, ipc2221_internal: 0.10, iec60664_basic: 1.40, iec60664_reinforced: 2.80 },
  { minVoltage: 101, maxVoltage: 150, ipc2221_external_bare: 0.60, ipc2221_internal: 0.20, iec60664_basic: 1.60, iec60664_reinforced: 3.20 },
  { minVoltage: 151, maxVoltage: 250, ipc2221_external_bare: 1.25, ipc2221_internal: 0.20, iec60664_basic: 2.50, iec60664_reinforced: 5.00 },
  { minVoltage: 251, maxVoltage: 325, ipc2221_external_bare: 1.25, ipc2221_internal: 0.25, iec60664_basic: 3.20, iec60664_reinforced: 6.40 },
  { minVoltage: 326, maxVoltage: 500, ipc2221_external_bare: 2.50, ipc2221_internal: 0.25, iec60664_basic: 5.00, iec60664_reinforced: 10.00 },
  { minVoltage: 501, maxVoltage: 800, ipc2221_external_bare: 6.25, ipc2221_internal: 0.50, iec60664_basic: 8.00, iec60664_reinforced: 16.00 },
  { minVoltage: 801, maxVoltage: 1000, ipc2221_external_bare: 12.50, ipc2221_internal: 0.80, iec60664_basic: 10.00, iec60664_reinforced: 20.00 },
];

export interface ClearanceEvaluation {
  voltage: number;
  insulationType: 'basic' | 'reinforced';
  requiredIecMm: number;
  requiredIpcMm: number;
  actualDistanceMm: number;
  actualDistanceMils: number;
  marginMm: number;
  isIecCompliant: boolean;
  isIpcCompliant: boolean;
  verdict: 'COMPLIANT' | 'MARGINAL' | 'VIOLATION';
  notes: string;
}

export function evaluateClearance(
  distanceMm: number,
  voltage: number = 230,
  insulationType: 'basic' | 'reinforced' = 'basic'
): ClearanceEvaluation {
  const rule = CLEARANCE_RULES.find((r) => voltage >= r.minVoltage && voltage <= r.maxVoltage)
    || CLEARANCE_RULES[CLEARANCE_RULES.length - 1];

  const reqIec = insulationType === 'reinforced' ? rule.iec60664_reinforced : rule.iec60664_basic;
  const reqIpc = rule.ipc2221_external_bare;
  const distMils = distanceMm * 39.3701;
  const marginMm = distanceMm - reqIec;

  let verdict: 'COMPLIANT' | 'MARGINAL' | 'VIOLATION' = 'COMPLIANT';
  if (marginMm < 0) {
    verdict = 'VIOLATION';
  } else if (marginMm < 0.5) {
    verdict = 'MARGINAL';
  }

  const notes = verdict === 'COMPLIANT'
    ? `Meets IEC 60664-1 (${reqIec.toFixed(2)} mm) and IPC-2221B (${reqIpc.toFixed(2)} mm) at ${voltage}V with +${marginMm.toFixed(2)} mm margin.`
    : verdict === 'MARGINAL'
    ? `Compliant with tight safety margin (+${marginMm.toFixed(2)} mm) for ${voltage}V ${insulationType} insulation.`
    : `Creepage/clearance violation: Deficit of ${Math.abs(marginMm).toFixed(2)} mm below ${reqIec.toFixed(2)} mm limit for ${voltage}V.`;

  return {
    voltage,
    insulationType,
    requiredIecMm: reqIec,
    requiredIpcMm: reqIpc,
    actualDistanceMm: distanceMm,
    actualDistanceMils: distMils,
    marginMm,
    isIecCompliant: marginMm >= 0,
    isIpcCompliant: distanceMm >= reqIpc,
    verdict,
    notes,
  };
}

interface GerberLayerInspectorProps {
  revisionId: string;
}

interface LayerState {
  visible: boolean;
  opacity: number;
}

export const GerberLayerInspector: React.FC<GerberLayerInspectorProps> = ({ revisionId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Per-layer visibility and opacity state
  const [layerStates, setLayerStates] = useState<Record<string, LayerState>>({});

  // Mode: standard multilayer stack vs differential comparison
  const [mode, setMode] = useState<'stack' | 'differential'>('stack');
  const [diffLayerA, setDiffLayerA] = useState<string>('F.Cu');
  const [diffLayerB, setDiffLayerB] = useState<string>('B.Cu');

  // Pan and Zoom
  const [zoom, setZoom] = useState<number>(1.2);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Crosshair coordinates & Hover Tooltip
  const [mouseCoords, setMouseCoords] = useState<{ x: number; y: number } | null>(null);
  const [hoverItem, setHoverItem] = useState<any>(null);

  // Drill Schedule Drawer
  const [showDrillSchedule, setShowDrillSchedule] = useState<boolean>(true);

  // Caliper & Creepage Ruler Tool state
  const [toolMode, setToolMode] = useState<'pan' | 'measure'>('pan');
  const [measureStart, setMeasureStart] = useState<MeasurementPoint | null>(null);
  const [measureEnd, setMeasureEnd] = useState<MeasurementPoint | null>(null);
  const [measureHover, setMeasureHover] = useState<MeasurementPoint | null>(null);
  const [snappingEnabled, setSnappingEnabled] = useState<boolean>(true);
  const [targetVoltageV, setTargetVoltageV] = useState<number>(230);
  const [insulationType, setInsulationType] = useState<'basic' | 'reinforced'>('basic');
  const [activeHoverSnap, setActiveHoverSnap] = useState<SnapPoint | null>(null);

  // Export / Download states
  const [exporting, setExporting] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const inFlightRef = useRef<string | null>(null);

  const loadData = async (force: boolean = false) => {
    if (inFlightRef.current === revisionId && !force) return;
    inFlightRef.current = revisionId;
    setLoading(true);
    setError(null);
    try {
      const res = await api.inspectGerberLayers(revisionId, true);
      if (res.success) {
        setData(res);
        // Initialize layer states
        const initialStates: Record<string, LayerState> = {};
        (res.layers || []).forEach((l: any) => {
          initialStates[l.layer_id] = {
            visible: true,
            opacity: l.layer_id === 'Edge.Cuts' ? 1.0 : l.is_drill ? 0.95 : l.is_copper ? 0.85 : 0.6,
          };
        });
        // Default drill layer visible
        initialStates['Drill'] = { visible: true, opacity: 0.95 };
        setLayerStates(initialStates);

        // If 4-layer, set default diff B to In1.Cu
        if (res.is_4layer) {
          setDiffLayerB('In1.Cu');
        }

        // Set voltage preset matching design
        const bName = (res.board_name || '').toLowerCase();
        if (bName.includes('sv1000') || bName.includes('1000')) {
          setTargetVoltageV(1000);
        } else if (bName.includes('pcb') || bName.includes('emc')) {
          setTargetVoltageV(325);
        }
      } else {
        setError(res.error || 'Failed to inspect Gerber layers');
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      inFlightRef.current = null;
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [revisionId]);

  const toggleLayerVisibility = (layerId: string) => {
    setLayerStates((prev) => ({
      ...prev,
      [layerId]: {
        ...prev[layerId],
        visible: !prev[layerId]?.visible,
      },
    }));
  };

  const setLayerOpacity = (layerId: string, opacity: number) => {
    setLayerStates((prev) => ({
      ...prev,
      [layerId]: {
        ...prev[layerId],
        opacity,
      },
    }));
  };

  const soloLayer = (layerId: string) => {
    setLayerStates((prev) => {
      const next: Record<string, LayerState> = {};
      Object.keys(prev).forEach((k) => {
        next[k] = { ...prev[k], visible: k === layerId || k === 'Edge.Cuts' };
      });
      return next;
    });
  };

  const applyPreset = (preset: 'all' | 'none' | 'copper' | 'mask_copper' | 'drill') => {
    setLayerStates((prev) => {
      const next: Record<string, LayerState> = {};
      Object.keys(prev).forEach((k) => {
        let vis = false;
        if (preset === 'all') vis = true;
        else if (preset === 'none') vis = k === 'Edge.Cuts';
        else if (preset === 'copper') vis = ['F.Cu', 'B.Cu', 'In1.Cu', 'In2.Cu', 'Edge.Cuts'].includes(k);
        else if (preset === 'mask_copper') vis = ['F.Cu', 'B.Cu', 'F.Mask', 'B.Mask', 'Edge.Cuts'].includes(k);
        else if (preset === 'drill') vis = ['Drill', 'Edge.Cuts'].includes(k);
        next[k] = { ...prev[k], visible: vis };
      });
      return next;
    });
  };

  const handleDownload = async () => {
    setDownloading(true);
    setActionMessage(null);
    try {
      const res = await api.downloadGerbers(revisionId);
      if (res.success && res.data_uri) {
        const link = document.createElement('a');
        link.href = res.data_uri;
        link.download = res.filename || 'gerbers.zip';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setActionMessage(`Downloaded ${res.filename} (${(res.size_bytes / 1024).toFixed(1)} KB)`);
      } else {
        setActionMessage(`Download failed: ${res.error}`);
      }
    } catch (err: any) {
      setActionMessage(`Error: ${err.message || String(err)}`);
    } finally {
      setDownloading(false);
    }
  };

  const handleReExport = async () => {
    setExporting(true);
    setActionMessage(null);
    try {
      const res = await api.exportGerbers(revisionId, true);
      if (res.success) {
        setActionMessage(`Generated ${res.file_count} manufacturing files successfully.`);
        await loadData(true);
      } else {
        setActionMessage(`Export error: ${res.error}`);
      }
    } catch (err: any) {
      setActionMessage(`Error: ${err.message || String(err)}`);
    } finally {
      setExporting(false);
    }
  };



  // Exact screen-to-board coordinate transformation
  const screenToBoard = (clientX: number, clientY: number): { x: number; y: number } => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const svgX = clientX - rect.left;
    const svgY = clientY - rect.top;
    const originX = rect.width / 2 + pan.x;
    const originY = rect.height / 2 + pan.y;
    const scaleFactor = zoom * 4.5;
    const boardX = boardCenterX + (svgX - originX) / scaleFactor;
    const boardY = boardCenterY + (svgY - originY) / scaleFactor;
    return { x: boardX, y: boardY };
  };

  // Memoized snap targets across pads, drill holes, tracks, and edge cuts
  const snapTargets = useMemo<SnapPoint[]>(() => {
    if (!data) return [];
    const targets: SnapPoint[] = [];

    // 1. Footprint pads
    (data.footprints || []).forEach((fp: any) => {
      (fp.pads || []).forEach((p: any) => {
        if (typeof p.x === 'number' && typeof p.y === 'number') {
          targets.push({
            x: p.x,
            y: p.y,
            type: 'pad',
            label: `${fp.ref} pad ${p.number}`,
          });
        }
      });
    });

    // 2. Drill hits / vias
    (data.drill_hits || []).forEach((dh: any) => {
      if (typeof dh.x === 'number' && typeof dh.y === 'number') {
        targets.push({
          x: dh.x,
          y: dh.y,
          type: 'drill',
          label: `Drill ø${dh.diameter}mm (${dh.plated ? 'PTH' : 'NPTH'})`,
        });
      }
    });

    // 3. Track endpoints
    (data.tracks || []).forEach((t: any) => {
      if (typeof t.x1 === 'number' && typeof t.y1 === 'number') {
        targets.push({ x: t.x1, y: t.y1, type: 'track', label: `Track net ${t.net}` });
      }
      if (typeof t.x2 === 'number' && typeof t.y2 === 'number') {
        targets.push({ x: t.x2, y: t.y2, type: 'track', label: `Track net ${t.net}` });
      }
    });

    // 4. Edge cuts / slot vertices
    (data.edge_cuts || []).forEach((ec: any) => {
      if (ec.type === 'rect') {
        targets.push({ x: ec.x1, y: ec.y1, type: 'edge', label: 'Outline / Slot corner' });
        targets.push({ x: ec.x2, y: ec.y1, type: 'edge', label: 'Outline / Slot corner' });
        targets.push({ x: ec.x1, y: ec.y2, type: 'edge', label: 'Outline / Slot corner' });
        targets.push({ x: ec.x2, y: ec.y2, type: 'edge', label: 'Outline / Slot corner' });
      } else if (ec.type === 'line') {
        targets.push({ x: ec.x1, y: ec.y1, type: 'edge', label: 'Edge line' });
        targets.push({ x: ec.x2, y: ec.y2, type: 'edge', label: 'Edge line' });
      }
    });

    return targets;
  }, [data]);

  const findSnapPoint = (rawX: number, rawY: number, maxRadiusMm: number = 2.5): SnapPoint | null => {
    if (!snappingEnabled || snapTargets.length === 0) return null;
    let closest: SnapPoint | null = null;
    let minDist = maxRadiusMm;

    for (const target of snapTargets) {
      const d = Math.hypot(target.x - rawX, target.y - rawY);
      if (d < minDist) {
        minDist = d;
        closest = target;
      }
    }
    return closest;
  };

  // Live measurement calculation
  const currentMeasurement = useMemo(() => {
    if (!measureStart) return null;
    const p2 = measureEnd || measureHover;
    if (!p2) return null;
    const distMm = Math.hypot(p2.x - measureStart.x, p2.y - measureStart.y);
    return evaluateClearance(distMm, targetVoltageV, insulationType);
  }, [measureStart, measureEnd, measureHover, targetVoltageV, insulationType]);

  // Pan, drag & measurement handling
  const handleMouseDown = (e: React.MouseEvent) => {
    // If middle click, right click, shift click or pan mode -> drag
    if (e.button === 1 || e.button === 2 || e.shiftKey || toolMode === 'pan') {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      return;
    }

    // In measurement mode with left click
    if (toolMode === 'measure' && e.button === 0) {
      const boardCoords = screenToBoard(e.clientX, e.clientY);
      const snap = findSnapPoint(boardCoords.x, boardCoords.y, 2.5);
      const targetPt: MeasurementPoint = snap
        ? { x: snap.x, y: snap.y, label: snap.label, type: snap.type }
        : { x: boardCoords.x, y: boardCoords.y, type: 'free' };

      if (!measureStart || measureEnd) {
        setMeasureStart(targetPt);
        setMeasureEnd(null);
        setMeasureHover(null);
      } else {
        setMeasureEnd(targetPt);
        setMeasureHover(null);
      }
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }

    if (svgRef.current && data?.bbox) {
      const boardCoords = screenToBoard(e.clientX, e.clientY);
      const snap = findSnapPoint(boardCoords.x, boardCoords.y, 2.5);
      setActiveHoverSnap(snap);

      setMouseCoords({ x: snap ? snap.x : boardCoords.x, y: snap ? snap.y : boardCoords.y });

      if (toolMode === 'measure' && measureStart && !measureEnd) {
        setMeasureHover(
          snap
            ? { x: snap.x, y: snap.y, label: snap.label, type: snap.type }
            : { x: boardCoords.x, y: boardCoords.y, type: 'free' }
        );
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((z) => Math.max(0.4, Math.min(6.0, z * factor)));
  };

  // Dimensions & bounds
  const bbox = data?.bbox || { min_x: 0, min_y: 0, width: 100, height: 80, max_x: 100, max_y: 80 };
  const boardCenterX = bbox.min_x + bbox.width / 2;
  const boardCenterY = bbox.min_y + bbox.height / 2;

  // Differential mode metrics
  const diffMetrics = useMemo(() => {
    if (mode !== 'differential' || !data) return null;
    const tracksA = (data.tracks || []).filter((t: any) => t.layer === diffLayerA).length;
    const tracksB = (data.tracks || []).filter((t: any) => t.layer === diffLayerB).length;
    const coincidentDrills = (data.drill_hits || []).length;
    return { tracksA, tracksB, coincidentDrills };
  }, [mode, diffLayerA, diffLayerB, data]);

  if (loading && !data) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>
        <RefreshCw size={24} className="spin" style={{ marginBottom: 12 }} />
        <div>Inspecting RS-274X Gerber Layers & Excellon Drill schedule...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={{ padding: 30, background: '#1e1014', border: '1px solid #e11d48', borderRadius: 8, color: '#fecdd3' }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>Gerber Layer Inspector Error</div>
        <div>{error}</div>
        <button
          onClick={() => loadData(true)}
          style={{
            marginTop: 14,
            background: '#e11d48',
            color: '#fff',
            border: 'none',
            padding: '6px 14px',
            borderRadius: 6,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Retry Inspection
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 740, background: '#0a0f1d', color: '#f8fafc', borderRadius: 8, overflow: 'hidden', border: '1px solid #1e293b' }}>
      {/* Top Banner & Control Strip */}
      <div style={{ background: '#0f172a', borderBottom: '1px solid #1e293b', padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={18} style={{ color: '#38bdf8' }} />
            <span style={{ fontWeight: 700, fontSize: 14, color: '#f8fafc' }}>
              RS-274X Gerber & Drill Inspector
            </span>
            <span style={{ fontSize: 11, background: data?.is_4layer ? '#0e7490' : '#1e293b', color: '#38bdf8', padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
              {data?.is_4layer ? '4-Layer Multilayer FR4' : '2-Layer Standard FR4'}
            </span>
          </div>

          {data?.has_gerber_zip && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8', background: '#1e293b', padding: '3px 8px', borderRadius: 4 }}>
              <CheckCircle2 size={12} style={{ color: '#10b981' }} />
              <span>{data.gerber_zip_filename}</span>
              <span style={{ color: '#64748b' }}>({(data.gerber_zip_bytes / 1024).toFixed(1)} KB)</span>
              <span style={{ color: '#38bdf8', fontFamily: 'monospace' }}>
                SHA: {data.gerber_zip_sha256?.substring(0, 8)}...
              </span>
            </div>
          )}
        </div>

        {/* View Mode Toggle & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Mode Switcher */}
          <div style={{ display: 'flex', background: '#1e293b', padding: 2, borderRadius: 6 }}>
            <button
              onClick={() => setMode('stack')}
              style={{
                background: mode === 'stack' ? '#2563eb' : 'transparent',
                border: 'none',
                color: mode === 'stack' ? '#fff' : '#94a3b8',
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🥞 Multilayer Stack
            </button>
            <button
              onClick={() => setMode('differential')}
              style={{
                background: mode === 'differential' ? '#ec4899' : 'transparent',
                border: 'none',
                color: mode === 'differential' ? '#fff' : '#94a3b8',
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🔬 Differential Compare
            </button>
            <button
              onClick={() => {
                if (toolMode === 'measure') {
                  setToolMode('pan');
                } else {
                  setToolMode('measure');
                }
              }}
              style={{
                background: toolMode === 'measure' ? '#0d9488' : 'transparent',
                border: 'none',
                color: toolMode === 'measure' ? '#fff' : '#94a3b8',
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 5,
              }}
              title="Activate interactive point-to-point caliper & IPC-2221/IEC 60664-1 clearance meter"
            >
              <Ruler size={12} />
              📏 Caliper / Measure
            </button>
          </div>

          <button
            onClick={handleDownload}
            disabled={downloading}
            style={{
              background: '#047857',
              border: 'none',
              color: '#fff',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: downloading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              boxShadow: '0 2px 6px rgba(4, 120, 87, 0.4)',
            }}
          >
            <Download size={13} className={downloading ? 'spin' : ''} />
            {downloading ? 'Downloading...' : 'Download Gerber ZIP'}
          </button>

          <button
            onClick={handleReExport}
            disabled={exporting}
            style={{
              background: '#0284c7',
              border: 'none',
              color: '#fff',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: exporting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <RefreshCw size={13} className={exporting ? 'spin' : ''} />
            {exporting ? 'Exporting...' : 'Re-Export Gerbers'}
          </button>
        </div>
      </div>

      {actionMessage && (
        <div style={{ background: '#1e293b', borderBottom: '1px solid #334155', padding: '6px 16px', fontSize: 12, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={13} />
          {actionMessage}
        </div>
      )}

      {/* Main Workspace Body */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, position: 'relative' }}>
        {/* Left Side Panel: Layer Stack Controls */}
        <div style={{ width: 310, background: '#0b1329', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
          {/* Preset Buttons */}
          <div style={{ padding: '12px 14px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8, letterSpacing: '0.05em' }}>
              Layer Presets
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4 }}>
              <button
                onClick={() => applyPreset('all')}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', padding: '4px', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}
              >
                All On
              </button>
              <button
                onClick={() => applyPreset('copper')}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', padding: '4px', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}
              >
                Copper Only
              </button>
              <button
                onClick={() => applyPreset('drill')}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', padding: '4px', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}
              >
                Drill Only
              </button>
              <button
                onClick={() => applyPreset('mask_copper')}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', padding: '4px', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}
              >
                Mask & Cu
              </button>
              <button
                onClick={() => applyPreset('none')}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', padding: '4px', borderRadius: 4, fontSize: 10, cursor: 'pointer' }}
              >
                Clear
              </button>
            </div>
          </div>

          {/* Differential Comparison Selector (if in diff mode) */}
          {mode === 'differential' && (
            <div style={{ padding: '12px 14px', borderBottom: '1px solid #1e293b', background: '#131c38' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#ec4899', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Layers2 size={13} />
                Differential Layer Pair
              </div>
              <div style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 10, color: '#10b981', display: 'block', marginBottom: 2, fontWeight: 600 }}>
                  Layer A (Green Overlay):
                </label>
                <select
                  value={diffLayerA}
                  onChange={(e) => setDiffLayerA(e.target.value)}
                  style={{ width: '100%', background: '#0a0f1d', border: '1px solid #10b981', color: '#10b981', padding: '4px 8px', borderRadius: 4, fontSize: 11 }}
                >
                  {(data?.layers || []).filter((l: any) => l.is_copper).map((l: any) => (
                    <option key={l.layer_id} value={l.layer_id}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 10, color: '#ec4899', display: 'block', marginBottom: 2, fontWeight: 600 }}>
                  Layer B (Magenta Overlay):
                </label>
                <select
                  value={diffLayerB}
                  onChange={(e) => setDiffLayerB(e.target.value)}
                  style={{ width: '100%', background: '#0a0f1d', border: '1px solid #ec4899', color: '#ec4899', padding: '4px 8px', borderRadius: 4, fontSize: 11 }}
                >
                  {(data?.layers || []).filter((l: any) => l.is_copper).map((l: any) => (
                    <option key={l.layer_id} value={l.layer_id}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>

              {diffMetrics && (
                <div style={{ marginTop: 10, padding: 8, background: '#0a0f1d', borderRadius: 4, fontSize: 10, border: '1px solid #334155' }}>
                  <div style={{ color: '#10b981', marginBottom: 2 }}>{diffLayerA}: {diffMetrics.tracksA} tracks</div>
                  <div style={{ color: '#ec4899', marginBottom: 2 }}>{diffLayerB}: {diffMetrics.tracksB} tracks</div>
                  <div style={{ color: '#facc15' }}>Via / Through-Hole Hits: {diffMetrics.coincidentDrills}</div>
                </div>
              )}
            </div>
          )}

          {/* Layer List */}
          <div style={{ padding: '10px 14px', flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8, letterSpacing: '0.05em' }}>
              Layer Stack ({data?.layers?.length || 0} Layers)
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {(data?.layers || []).map((layer: any) => {
                const state = layerStates[layer.layer_id] || { visible: true, opacity: 0.8 };
                return (
                  <div
                    key={layer.layer_id}
                    style={{
                      background: state.visible ? '#131e38' : '#0c1326',
                      border: state.visible ? `1px solid ${layer.color_hex}44` : '1px solid #1e293b',
                      borderRadius: 6,
                      padding: '6px 10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                        <button
                          onClick={() => toggleLayerVisibility(layer.layer_id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: state.visible ? layer.color_hex : '#64748b',
                            cursor: 'pointer',
                            padding: 2,
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          title={state.visible ? 'Hide Layer' : 'Show Layer'}
                        >
                          {state.visible ? <Eye size={14} /> : <EyeOff size={14} />}
                        </button>

                        <div
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: layer.color_hex,
                            boxShadow: state.visible ? `0 0 6px ${layer.color_hex}` : 'none',
                            flexShrink: 0,
                          }}
                        />

                        <div style={{ fontSize: 11, fontWeight: 600, color: state.visible ? '#f8fafc' : '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {layer.layer_id}
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button
                          onClick={() => soloLayer(layer.layer_id)}
                          style={{
                            background: '#1e293b',
                            border: '1px solid #334155',
                            color: '#94a3b8',
                            fontSize: 9,
                            padding: '1px 5px',
                            borderRadius: 3,
                            cursor: 'pointer',
                            fontWeight: 700,
                          }}
                          title={`Solo ${layer.layer_id}`}
                        >
                          S
                        </button>
                        <span style={{ fontSize: 9, color: '#64748b', fontFamily: 'monospace' }}>
                          {(layer.file_size_bytes / 1024).toFixed(1)}K
                        </span>
                      </div>
                    </div>

                    {/* Opacity slider */}
                    {state.visible && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                        <Sliders size={10} style={{ color: '#64748b' }} />
                        <input
                          type="range"
                          min="0.1"
                          max="1.0"
                          step="0.05"
                          value={state.opacity}
                          onChange={(e) => setLayerOpacity(layer.layer_id, parseFloat(e.target.value))}
                          style={{ flex: 1, height: 3, accentColor: layer.color_hex, cursor: 'pointer' }}
                        />
                        <span style={{ fontSize: 9, color: '#94a3b8', minWidth: 26, textAlign: 'right' }}>
                          {Math.round(state.opacity * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Center: Interactive High-Contrast Gerber SVG Canvas */}
        <div
          style={{
            flex: 1,
            position: 'relative',
            background: '#070c18',
            overflow: 'hidden',
            cursor: isDragging ? 'grabbing' : toolMode === 'measure' ? 'crosshair' : 'default',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
        >
          {/* Floating Caliper & Creepage Meter HUD Bar */}
          {toolMode === 'measure' && (
            <div
              style={{
                position: 'absolute',
                top: 12,
                left: 12,
                right: 90,
                background: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid #0d9488',
                borderRadius: 8,
                padding: '8px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.6), 0 0 12px rgba(13, 148, 136, 0.25)',
                backdropFilter: 'blur(8px)',
                zIndex: 20,
                flexWrap: 'wrap',
              }}
            >
              {/* Left: Status & Points */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#0f766e', color: '#fff', padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
                  <Ruler size={13} />
                  CALIPER RULER
                </div>

                <div style={{ fontSize: 11, color: '#94a3b8' }}>
                  {!measureStart && (
                    <span style={{ color: '#38bdf8' }}>Click anywhere on PCB or pads to set Point A</span>
                  )}
                  {measureStart && !measureEnd && (
                    <span>
                      Point A: <b style={{ color: '#38bdf8' }}>({measureStart.x.toFixed(1)}, {measureStart.y.toFixed(1)})</b> {measureStart.label && <span style={{ color: '#64748b' }}>[{measureStart.label}]</span>} &rarr; <span style={{ color: '#f59e0b' }}>Click Point B to measure</span>
                    </span>
                  )}
                  {measureStart && measureEnd && (
                    <span>
                      A: <b style={{ color: '#38bdf8' }}>({measureStart.x.toFixed(1)}, {measureStart.y.toFixed(1)})</b> &rarr; B: <b style={{ color: '#38bdf8' }}>({measureEnd.x.toFixed(1)}, {measureEnd.y.toFixed(1)})</b>
                    </span>
                  )}
                </div>
              </div>

              {/* Center: Live Measurement & Compliance Scorecard */}
              {currentMeasurement && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#0b1329', padding: '4px 10px', borderRadius: 6, border: '1px solid #1e293b' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                    <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Clearance:</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', fontFamily: 'monospace' }}>
                      {currentMeasurement.actualDistanceMm.toFixed(3)} mm
                    </span>
                    <span style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>
                      ({currentMeasurement.actualDistanceMils.toFixed(1)} mil)
                    </span>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 5,
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 700,
                      background: currentMeasurement.verdict === 'COMPLIANT' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                      border: `1px solid ${currentMeasurement.verdict === 'COMPLIANT' ? '#10b981' : '#f43f5e'}`,
                      color: currentMeasurement.verdict === 'COMPLIANT' ? '#10b981' : '#f43f5e',
                    }}
                    title={currentMeasurement.notes}
                  >
                    {currentMeasurement.verdict === 'COMPLIANT' ? <ShieldCheck size={13} /> : <AlertTriangle size={13} />}
                    <span>
                      {currentMeasurement.verdict === 'COMPLIANT'
                        ? `PASS @ ${targetVoltageV}V (Req: ${currentMeasurement.requiredIecMm.toFixed(2)}mm, +${currentMeasurement.marginMm.toFixed(2)}mm)`
                        : `VIOLATION @ ${targetVoltageV}V: Req ${currentMeasurement.requiredIecMm.toFixed(2)}mm (${Math.abs(currentMeasurement.marginMm).toFixed(2)}mm deficit)`}
                    </span>
                  </div>
                </div>
              )}

              {/* Right: Controls & Presets */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Working Voltage Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#1e293b', padding: '2px 6px', borderRadius: 4 }}>
                  <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 600 }}>Voltage:</span>
                  <select
                    value={targetVoltageV}
                    onChange={(e) => setTargetVoltageV(Number(e.target.value))}
                    style={{
                      background: '#0f172a',
                      border: '1px solid #334155',
                      color: '#38bdf8',
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '2px 4px',
                      borderRadius: 3,
                      cursor: 'pointer',
                    }}
                  >
                    <option value={50}>50 V (SELV)</option>
                    <option value={230}>230 V (Mains AC)</option>
                    <option value={325}>325 V (Rectified Peak)</option>
                    <option value={500}>500 V (Intermediate)</option>
                    <option value={1000}>1000 V (HV SV-1000)</option>
                  </select>
                </div>

                {/* Insulation Class */}
                <button
                  onClick={() => setInsulationType(insulationType === 'basic' ? 'reinforced' : 'basic')}
                  style={{
                    background: insulationType === 'reinforced' ? '#7c3aed' : '#1e293b',
                    border: '1px solid #334155',
                    color: insulationType === 'reinforced' ? '#fff' : '#94a3b8',
                    fontSize: 10,
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Toggle between Basic and Reinforced (2x) insulation per IEC 60664-1"
                >
                  {insulationType === 'reinforced' ? 'Reinforced (2x)' : 'Basic Insulation'}
                </button>

                {/* Snapping Button */}
                <button
                  onClick={() => setSnappingEnabled(!snappingEnabled)}
                  style={{
                    background: snappingEnabled ? '#0e7490' : '#1e293b',
                    border: '1px solid #334155',
                    color: snappingEnabled ? '#fff' : '#64748b',
                    fontSize: 10,
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                  title="Toggle magnetic snapping to pad centers, drill holes, and track endpoints"
                >
                  <Magnet size={11} />
                  {snappingEnabled ? 'Snap ON' : 'Snap OFF'}
                </button>

                {/* Clear */}
                {(measureStart || measureEnd) && (
                  <button
                    onClick={() => { setMeasureStart(null); setMeasureEnd(null); setMeasureHover(null); }}
                    style={{
                      background: '#334155',
                      border: 'none',
                      color: '#f8fafc',
                      fontSize: 10,
                      fontWeight: 600,
                      padding: '3px 8px',
                      borderRadius: 4,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                    title="Clear current measurement (or press Esc)"
                  >
                    <Trash2 size={11} />
                    Clear
                  </button>
                )}

                {/* Exit Caliper Mode */}
                <button
                  onClick={() => { setToolMode('pan'); setMeasureStart(null); setMeasureEnd(null); setMeasureHover(null); }}
                  style={{
                    background: '#dc2626',
                    border: 'none',
                    color: '#fff',
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Exit measurement mode"
                >
                  ✕ Done
                </button>
              </div>
            </div>
          )}
          {/* Zoom & Fit HUD Controls */}
          <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 6, zIndex: 10, background: 'rgba(15, 23, 42, 0.85)', padding: 4, borderRadius: 6, border: '1px solid #1e293b', backdropFilter: 'blur(4px)' }}>
            <button
              onClick={() => setZoom((z) => Math.min(6.0, z * 1.2))}
              style={{ background: 'transparent', border: 'none', color: '#f8fafc', padding: 4, cursor: 'pointer' }}
              title="Zoom In"
            >
              <ZoomIn size={14} />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z * 0.83))}
              style={{ background: 'transparent', border: 'none', color: '#f8fafc', padding: 4, cursor: 'pointer' }}
              title="Zoom Out"
            >
              <ZoomOut size={14} />
            </button>
            <button
              onClick={() => { setZoom(1.2); setPan({ x: 0, y: 0 }); }}
              style={{ background: 'transparent', border: 'none', color: '#f8fafc', padding: 4, cursor: 'pointer' }}
              title="Reset View"
            >
              <Maximize2 size={14} />
            </button>
          </div>

          {/* SVG Viewport */}
          <svg
            ref={svgRef}
            style={{ width: '100%', height: '100%', display: 'block' }}
          >
            <g
              transform={`translate(${svgRef.current ? svgRef.current.clientWidth / 2 + pan.x : 400}, ${
                svgRef.current ? svgRef.current.clientHeight / 2 + pan.y : 350
              }) scale(${zoom * 4.5}) translate(${-boardCenterX}, ${-boardCenterY})`}
            >
              {/* Background PCB Substrate FR4 */}
              <rect
                x={bbox.min_x}
                y={bbox.min_y}
                width={bbox.width}
                height={bbox.height}
                fill="#0d1b1e"
                stroke="#164e63"
                strokeWidth={0.3}
                rx={1}
              />

              {/* Edge.Cuts Outline */}
              {layerStates['Edge.Cuts']?.visible && (
                <g opacity={layerStates['Edge.Cuts']?.opacity || 1.0}>
                  {(data?.edge_cuts || []).map((e: any, i: number) => {
                    if (e.type === 'rect') {
                      return (
                        <rect
                          key={`ec-${i}`}
                          x={e.x1}
                          y={e.y1}
                          width={e.x2 - e.x1}
                          height={e.y2 - e.y1}
                          fill="none"
                          stroke="#eab308"
                          strokeWidth={0.35}
                        />
                      );
                    }
                    return (
                      <line
                        key={`ec-${i}`}
                        x1={e.x1}
                        y1={e.y1}
                        x2={e.x2}
                        y2={e.y2}
                        stroke="#eab308"
                        strokeWidth={0.35}
                        strokeLinecap="round"
                      />
                    );
                  })}
                </g>
              )}

              {/* Bottom Copper Tracks & Fills (B.Cu) */}
              {(mode === 'stack' ? layerStates['B.Cu']?.visible : (diffLayerA === 'B.Cu' || diffLayerB === 'B.Cu')) && (
                <g
                  opacity={
                    mode === 'differential'
                      ? 0.9
                      : layerStates['B.Cu']?.opacity || 0.85
                  }
                >
                  {(data?.tracks || []).filter((t: any) => t.layer === 'B.Cu').map((t: any, i: number) => {
                    const strokeColor =
                      mode === 'differential'
                        ? diffLayerA === 'B.Cu' ? '#10b981' : '#ec4899'
                        : '#3b82f6';
                    return (
                      <line
                        key={`bcu-t-${i}`}
                        x1={t.x1}
                        y1={t.y1}
                        x2={t.x2}
                        y2={t.y2}
                        stroke={strokeColor}
                        strokeWidth={t.width || 0.4}
                        strokeLinecap="round"
                        onMouseEnter={() => setHoverItem({ type: 'track', layer: 'B.Cu', net: t.net, width: t.width })}
                        onMouseLeave={() => setHoverItem(null)}
                      />
                    );
                  })}
                </g>
              )}

              {/* Top Copper Tracks & Fills (F.Cu) */}
              {(mode === 'stack' ? layerStates['F.Cu']?.visible : (diffLayerA === 'F.Cu' || diffLayerB === 'F.Cu')) && (
                <g
                  opacity={
                    mode === 'differential'
                      ? 0.9
                      : layerStates['F.Cu']?.opacity || 0.85
                  }
                >
                  {(data?.tracks || []).filter((t: any) => t.layer === 'F.Cu').map((t: any, i: number) => {
                    const strokeColor =
                      mode === 'differential'
                        ? diffLayerA === 'F.Cu' ? '#10b981' : '#ec4899'
                        : '#ef4444';
                    return (
                      <line
                        key={`fcu-t-${i}`}
                        x1={t.x1}
                        y1={t.y1}
                        x2={t.x2}
                        y2={t.y2}
                        stroke={strokeColor}
                        strokeWidth={t.width || 0.4}
                        strokeLinecap="round"
                        onMouseEnter={() => setHoverItem({ type: 'track', layer: 'F.Cu', net: t.net, width: t.width })}
                        onMouseLeave={() => setHoverItem(null)}
                      />
                    );
                  })}
                </g>
              )}

              {/* Footprint Pads (Through-Hole & SMD) */}
              {(data?.footprints || []).map((fp: any, fpi: number) => (
                <g key={`fp-${fpi}`}>
                  {(fp.pads || []).map((p: any, pi: number) => {
                    const isThru = p.type === 'thru_hole' || p.type === 'np_thru_hole';
                    const padColor = isThru ? '#f59e0b' : '#ef4444';
                    const showPad =
                      mode === 'differential'
                        ? true
                        : isThru
                        ? layerStates['F.Cu']?.visible || layerStates['B.Cu']?.visible
                        : layerStates['F.Cu']?.visible;

                    if (!showPad) return null;

                    return (
                      <rect
                        key={`p-${pi}`}
                        x={p.x - p.sx / 2}
                        y={p.y - p.sy / 2}
                        width={p.sx}
                        height={p.sy}
                        rx={p.shape === 'circle' ? p.sx / 2 : 0.2}
                        fill={padColor}
                        opacity={0.9}
                        stroke="#fff"
                        strokeWidth={0.08}
                        onMouseEnter={() =>
                          setHoverItem({
                            type: 'pad',
                            ref: fp.ref,
                            pin: p.number,
                            shape: p.shape,
                            sx: p.sx,
                            sy: p.sy,
                            drill: p.drill,
                            isThru,
                          })
                        }
                        onMouseLeave={() => setHoverItem(null)}
                      />
                    );
                  })}
                </g>
              ))}

              {/* Silkscreen Layer (F.SilkS) */}
              {mode === 'stack' && layerStates['F.SilkS']?.visible && (
                <g opacity={layerStates['F.SilkS']?.opacity || 0.6}>
                  {(data?.footprints || []).map((fp: any, fpi: number) => (
                    <g key={`silk-${fpi}`}>
                      {(fp.silks || []).map((s: any, si: number) => {
                        if (s.type === 'rect') {
                          return (
                            <rect
                              key={`sr-${si}`}
                              x={s.x1}
                              y={s.y1}
                              width={s.x2 - s.x1}
                              height={s.y2 - s.y1}
                              fill="none"
                              stroke="#ffffff"
                              strokeWidth={0.12}
                            />
                          );
                        }
                        return (
                          <line
                            key={`sl-${si}`}
                            x1={s.x1}
                            y1={s.y1}
                            x2={s.x2}
                            y2={s.y2}
                            stroke="#ffffff"
                            strokeWidth={0.12}
                          />
                        );
                      })}
                      {/* Component Reference Label */}
                      <text
                        x={fp.x}
                        y={fp.y - 1.5}
                        fill="#ffffff"
                        fontSize={1.2}
                        textAnchor="middle"
                        fontWeight="bold"
                        opacity={0.85}
                      >
                        {fp.ref}
                      </text>
                    </g>
                  ))}
                </g>
              )}

              {/* Excellon Drill Layer (Drill Holes & Crosshairs) */}
              {(mode === 'stack' ? layerStates['Drill']?.visible : true) && (
                <g opacity={layerStates['Drill']?.opacity || 0.95}>
                  {(data?.drill_hits || []).map((h: any, hi: number) => {
                    const r = (h.diameter || 0.8) / 2;
                    return (
                      <g
                        key={`drl-${hi}`}
                        onMouseEnter={() =>
                          setHoverItem({
                            type: 'drill',
                            tool_id: h.tool_id,
                            diameter: h.diameter,
                            plated: h.plated,
                            x: h.x,
                            y: h.y,
                          })
                        }
                        onMouseLeave={() => setHoverItem(null)}
                      >
                        {/* Black drill hole clearance */}
                        <circle cx={h.x} cy={h.y} r={r} fill="#050a14" stroke="#06b6d4" strokeWidth={0.08} />
                        {/* Centered crosshair tick */}
                        <line x1={h.x - r * 0.7} y1={h.y} x2={h.x + r * 0.7} y2={h.y} stroke="#06b6d4" strokeWidth={0.06} />
                        <line x1={h.x} y1={h.y - r * 0.7} x2={h.x} y2={h.y + r * 0.7} stroke="#06b6d4" strokeWidth={0.06} />
                      </g>
                    );
                  })}
                </g>
              )}

              {/* Active Magnetic Snap Reticle on Hover */}
              {toolMode === 'measure' && activeHoverSnap && (
                <g pointerEvents="none">
                  <circle cx={activeHoverSnap.x} cy={activeHoverSnap.y} r={1.8} fill="none" stroke="#38bdf8" strokeWidth={0.35} strokeDasharray="1 0.6" />
                  <circle cx={activeHoverSnap.x} cy={activeHoverSnap.y} r={0.4} fill="#38bdf8" />
                </g>
              )}

              {/* Interactive Caliper & Creepage Measurement Overlay */}
              {measureStart && (() => {
                const p1 = measureStart;
                const p2 = measureEnd || measureHover;
                if (!p2) {
                  return (
                    <g pointerEvents="none">
                      <circle cx={p1.x} cy={p1.y} r={1.6} fill="none" stroke="#38bdf8" strokeWidth={0.4} />
                      <circle cx={p1.x} cy={p1.y} r={0.4} fill="#38bdf8" />
                    </g>
                  );
                }

                const dx = p2.x - p1.x;
                const dy = p2.y - p1.y;
                const distMm = Math.hypot(dx, dy);
                const distMils = distMm * 39.3701;
                const evalRes = evaluateClearance(distMm, targetVoltageV, insulationType);
                const strokeColor = evalRes.verdict === 'COMPLIANT' ? '#10b981' : evalRes.verdict === 'MARGINAL' ? '#f59e0b' : '#f43f5e';

                const angle = Math.atan2(dy, dx);
                const perp = angle + Math.PI / 2;
                const tineLen = 2.4;

                const ax1 = p1.x - Math.cos(perp) * tineLen;
                const ay1 = p1.y - Math.sin(perp) * tineLen;
                const ax2 = p1.x + Math.cos(perp) * tineLen;
                const ay2 = p1.y + Math.sin(perp) * tineLen;

                const bx1 = p2.x - Math.cos(perp) * tineLen;
                const by1 = p2.y - Math.sin(perp) * tineLen;
                const bx2 = p2.x + Math.cos(perp) * tineLen;
                const by2 = p2.y + Math.sin(perp) * tineLen;

                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;

                return (
                  <g pointerEvents="none" id="caliper-graphics">
                    {/* Bounding right-triangle guides */}
                    {Math.abs(dx) > 0.6 && Math.abs(dy) > 0.6 && (
                      <g opacity={0.3}>
                        <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p1.y} stroke="#94a3b8" strokeWidth={0.2} strokeDasharray="1 1" />
                        <line x1={p2.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#94a3b8" strokeWidth={0.2} strokeDasharray="1 1" />
                      </g>
                    )}

                    {/* Perpendicular Caliper Tines */}
                    <line x1={ax1} y1={ay1} x2={ax2} y2={ay2} stroke={strokeColor} strokeWidth={0.4} strokeLinecap="round" />
                    <line x1={bx1} y1={by1} x2={bx2} y2={by2} stroke={strokeColor} strokeWidth={0.4} strokeLinecap="round" />

                    {/* Main Dimension Line */}
                    <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={strokeColor} strokeWidth={0.45} strokeDasharray="2 1" />

                    {/* End Point Markers */}
                    <circle cx={p1.x} cy={p1.y} r={1.2} fill="none" stroke="#38bdf8" strokeWidth={0.3} />
                    <circle cx={p1.x} cy={p1.y} r={0.35} fill="#38bdf8" />

                    <circle cx={p2.x} cy={p2.y} r={1.2} fill="none" stroke={strokeColor} strokeWidth={0.3} />
                    <circle cx={p2.x} cy={p2.y} r={0.35} fill={strokeColor} />

                    {/* On-Board Dimension Pill */}
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x={-14}
                        y={-4.5}
                        width={28}
                        height={9}
                        rx={1.8}
                        fill="rgba(10, 15, 29, 0.95)"
                        stroke={strokeColor}
                        strokeWidth={0.3}
                      />
                      <text
                        x={0}
                        y={-0.8}
                        fill="#f8fafc"
                        fontSize={2.3}
                        fontWeight="700"
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        {distMm.toFixed(2)} mm
                      </text>
                      <text
                        x={0}
                        y={2.2}
                        fill={strokeColor}
                        fontSize={1.7}
                        fontWeight="600"
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        {distMils.toFixed(0)} mil {evalRes.verdict === 'COMPLIANT' ? '✓' : '⚠️'}
                      </text>
                    </g>
                  </g>
                );
              })()}
            </g>
          </svg>

          {/* Coordinate HUD Bottom Left */}
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              left: 12,
              background: 'rgba(15, 23, 42, 0.85)',
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'monospace',
              color: '#38bdf8',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              backdropFilter: 'blur(4px)',
            }}
          >
            <Crosshair size={12} />
            <span>
              X: {mouseCoords ? mouseCoords.x.toFixed(2) : '00.00'} mm
            </span>
            <span>
              Y: {mouseCoords ? mouseCoords.y.toFixed(2) : '00.00'} mm
            </span>
            <span style={{ color: '#64748b' }}>Zoom: {(zoom * 100).toFixed(0)}%</span>
            {activeHoverSnap && (
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                🧲 {activeHoverSnap.label}
              </span>
            )}
          </div>

          {/* Hover Tooltip Overlay */}
          {hoverItem && (
            <div
              style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: '#0f172a',
                border: '1px solid #38bdf8',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: 11,
                boxShadow: '0 4px 14px rgba(0,0,0,0.6)',
                zIndex: 20,
              }}
            >
              {hoverItem.type === 'pad' && (
                <div>
                  <div style={{ fontWeight: 700, color: '#f59e0b' }}>
                    Pad {hoverItem.ref}.{hoverItem.pin} ({hoverItem.isThru ? 'Through-Hole' : 'SMD'})
                  </div>
                  <div style={{ color: '#cbd5e1' }}>Size: {hoverItem.sx} × {hoverItem.sy} mm</div>
                  {hoverItem.drill && <div style={{ color: '#06b6d4' }}>Drill: ⌀{hoverItem.drill} mm</div>}
                </div>
              )}
              {hoverItem.type === 'track' && (
                <div>
                  <div style={{ fontWeight: 700, color: hoverItem.layer === 'F.Cu' ? '#ef4444' : '#3b82f6' }}>
                    {hoverItem.layer} Copper Segment
                  </div>
                  <div style={{ color: '#cbd5e1' }}>Width: {hoverItem.width} mm</div>
                  <div style={{ color: '#94a3b8' }}>Net: #{hoverItem.net}</div>
                </div>
              )}
              {hoverItem.type === 'drill' && (
                <div>
                  <div style={{ fontWeight: 700, color: '#06b6d4' }}>
                    Excellon Drill: Tool {hoverItem.tool_id}
                  </div>
                  <div style={{ color: '#cbd5e1' }}>Diameter: ⌀{hoverItem.diameter} mm ({(hoverItem.diameter * 39.37).toFixed(1)} mils)</div>
                  <div style={{ color: hoverItem.plated ? '#10b981' : '#f59e0b' }}>
                    {hoverItem.plated ? 'Plated Through Hole (PTH)' : 'Non-Plated (NPTH)'}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Collapsible Drawer: Excellon Drill Schedule */}
      <div style={{ background: '#0b1329', borderTop: '1px solid #1e293b' }}>
        <div
          onClick={() => setShowDrillSchedule(!showDrillSchedule)}
          style={{
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            background: '#0f172a',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
              Excellon Drill Schedule & Tooling Table
            </span>
            <span style={{ fontSize: 11, background: '#1e293b', color: '#06b6d4', padding: '1px 6px', borderRadius: 4 }}>
              {data?.drill_summary?.total_holes || 0} Total Holes
            </span>
            <span style={{ fontSize: 11, color: '#10b981' }}>
              PTH: {data?.drill_summary?.pth_count || 0}
            </span>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>
              NPTH: {data?.drill_summary?.npth_count || 0}
            </span>
            <span style={{ fontSize: 11, color: '#f59e0b' }}>
              Tools: {data?.drill_summary?.tool_count || 0}
            </span>
          </div>

          <div style={{ fontSize: 11, color: '#38bdf8', fontWeight: 600 }}>
            {showDrillSchedule ? '▼ Collapse Schedule' : '▲ Expand Schedule'}
          </div>
        </div>

        {showDrillSchedule && (
          <div style={{ padding: '10px 16px', maxHeight: 180, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b', color: '#94a3b8', textAlign: 'left' }}>
                  <th style={{ padding: '6px 8px' }}>Tool ID</th>
                  <th style={{ padding: '6px 8px' }}>Diameter (mm)</th>
                  <th style={{ padding: '6px 8px' }}>Diameter (mil)</th>
                  <th style={{ padding: '6px 8px' }}>Plating</th>
                  <th style={{ padding: '6px 8px' }}>Hit Count</th>
                  <th style={{ padding: '6px 8px' }}>Classification / Usage</th>
                </tr>
              </thead>
              <tbody>
                {(data?.drill_tools || []).map((t: any) => (
                  <tr key={t.tool_id} style={{ borderBottom: '1px solid #131e38' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 700, color: '#06b6d4', fontFamily: 'monospace' }}>
                      {t.tool_id}
                    </td>
                    <td style={{ padding: '6px 8px', color: '#f8fafc' }}>{t.diameter_mm.toFixed(2)} mm</td>
                    <td style={{ padding: '6px 8px', color: '#94a3b8' }}>{t.diameter_mils.toFixed(1)} mil</td>
                    <td style={{ padding: '6px 8px' }}>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 3,
                          background: t.plated ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                          color: t.plated ? '#10b981' : '#f59e0b',
                          fontWeight: 600,
                        }}
                      >
                        {t.plated ? 'Plated (PTH)' : 'Non-Plated (NPTH)'}
                      </span>
                    </td>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#f8fafc' }}>{t.count} hits</td>
                    <td style={{ padding: '6px 8px', color: '#cbd5e1' }}>{t.usage}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
