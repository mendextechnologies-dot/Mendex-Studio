import { PCBGeometry } from './PCBGeometry';
import { downloadCandidate } from '../downloadCandidate';
import { GerberLayerInspector } from './GerberLayerInspector';
import React, { useEffect, useState, useMemo, useRef } from 'react';
import { api } from '../api/client';
import { Layers, Eye, RefreshCw, ExternalLink, Box, ZoomIn, ZoomOut, CheckCircle2, Zap, Package, Camera, Download, Folder, Scissors } from 'lucide-react';

interface CADPreviewProps {
  revisionId: string;
  onOpenPCB?: () => void;
  onOpenSchematic?: () => void;
}

export const CADPreviewCanvas: React.FC<CADPreviewProps> = ({
  revisionId,
  onOpenPCB,
  onOpenSchematic,
}) => {
  const requestGeneration = useRef(0);
  const activeRevision = useRef(revisionId); activeRevision.current = revisionId;
  const sourceIdentity = useRef<string | null>(null);
  const [previewEpoch, setPreviewEpoch] = useState(0);
  const busy = useRef(false);
  const [viewMode, setViewMode] = useState<'pcb' | 'schematic' | '3d' | 'gerber'>('pcb');
  const [render3dData, setRender3dData] = useState<any>(null);
  const [sub3dMode, setSub3dMode] = useState<'raytrace' | 'orbit'>('raytrace');
  const [orbitRotX, setOrbitRotX] = useState<number>(55);
  const [orbitRotZ, setOrbitRotZ] = useState<number>(25);
  const [orbitZoom, setOrbitZoom] = useState<number>(1.0);
  const [isOrbitDragging, setIsOrbitDragging] = useState<boolean>(false);
  const [orbitDragStart, setOrbitDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [pcbData, setPcbData] = useState<any>(null);
  const [schData, setSchData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoverItem, setHoverItem] = useState<any>(null);
  const [schViewMode, setSchViewMode] = useState<'kicad_vector' | 'interactive'>('kicad_vector');
  const [schZoom, setSchZoom] = useState<number>(1.0);
  const [routing, setRouting] = useState<boolean>(false);
  const [exportingGerbers, setExportingGerbers] = useState<boolean>(false);
  const [routeStatus, setRouteStatus] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // 2D PCB Thermal Heatmap Overlay State (Option 4)
  const [showThermalOverlay, setShowThermalOverlay] = useState<boolean>(false);
  const [thermalData, setThermalData] = useState<any>(null);
  const [loadingThermal, setLoadingThermal] = useState<boolean>(false);
  const [thermalHoverSpot, setThermalHoverSpot] = useState<any>(null);
  const [chassisCooling, setChassisCooling] = useState<boolean>(true);

  const toggleChassisCooling = async () => {
    const nextCooling = !chassisCooling;
    setChassisCooling(nextCooling);
    setLoadingThermal(true);
    try {
      const data = await api.calculatePcbThermalField({
        revisionId,
        chassisCooling: nextCooling,
        copperWeightOz: copperWeight === '2oz' ? 2.0 : 1.0,
      });
      if (data && data.success) {
        setThermalData(data);
      }
    } catch (err) {
      setRouteStatus({type:'error',text:String(err)});
    } finally {
      setLoadingThermal(false);
    }
  };

  const toggleThermalHeatmap = async () => {
    const next = !showThermalOverlay;
    setShowThermalOverlay(next);
    if (next && !thermalData) {
      setLoadingThermal(true);
      try {
        const data = await api.calculatePcbThermalField({
          revisionId,
          chassisCooling,
          copperWeightOz: copperWeight === '2oz' ? 2.0 : 1.0,
        });
        if (data && data.success) {
          setThermalData(data);
        }
      } catch (err) {
        setRouteStatus({type:'error',text:String(err)});
      } finally {
        setLoadingThermal(false);
      }
    }
  };

  const [gerberInfo, setGerberInfo] = useState<{
    available: boolean;
    filename?: string;
    zipPath?: string;
    sha256?: string;
    bytes?: number;
    dataUri?: string;
  } | null>(null);
  const [downloadingGerbers, setDownloadingGerbers] = useState<boolean>(false);

  const handleDownloadGerbers = async () => {
    setDownloadingGerbers(true);
    try {
      const res = await api.downloadGerbers(revisionId);
      if (!res.success) throw new Error(res.error || 'No current package. Re-export Gerbers.');
      await downloadCandidate(res);
      const filename=res.filename;
      setRouteStatus({
        type: 'success',
        text: `Save requested for ${filename}; payload SHA-256 matches. Browser save completion is not observed.`,
      });
    } catch (err: any) {
      setRouteStatus({ type: 'error', text: `Download failed: ${err.message || String(err)}` });
    } finally {
      setDownloadingGerbers(false);
    }
  };

  const handleRevealGerbers = async () => {
    try {
      const targetPath = gerberInfo?.zipPath || 'pcb/gerbers';
      const res = await api.revealFile(revisionId, targetPath);
      setRouteStatus({
        type: 'info',
        text: `Revealed ${res.revealed ? res.revealed.split(/[\\/]/).pop() : 'Gerber folder'} in Windows File Explorer.`,
      });
    } catch (err: any) {
      setRouteStatus({ type: 'error', text: `Could not reveal in Explorer: ${err.message || String(err)}` });
    }
  };

  const handleExportGerbers = async () => {
    setExportingGerbers(true);
    setRouteStatus({ type: 'info', text: 'Generating manufacturing Gerbers and drill files (with auto-routing verification)...' });
    try {
      const res = await api.exportGerbers(revisionId, true);
      if (res.success) {
        setGerberInfo({
          available: true,
          filename: res.zip_filename || (res.zip_path ? res.zip_path.split('/').pop() : 'gerbers.zip'),
          zipPath: res.zip_path,
          sha256: res.sha256,
          bytes: res.zip_bytes,
          dataUri: res.data_uri,
        });
        setRouteStatus({
          type: 'success',
          text: `Candidate fabrication files generated: ${res.file_count} Gerber & drill files exported to ${res.output_dir}${res.sha256 ? ` (SHA-256: ${res.sha256.slice(0, 12)}...)` : ''}`,
        });
        loadData();
      } else {
        setRouteStatus({
          type: 'error',
          text: `Gerber export notice: ${res.error || 'Check logs'}`,
        });
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `Gerber export failed: ${err.message || String(err)}`,
      });
    } finally {
      setExportingGerbers(false);
    }
  };

  const [exportingStep, setExportingStep] = useState<boolean>(false);

  const handleExportStep = async (openNative: boolean = false) => {
    setExportingStep(true);
    setRouteStatus({
      type: 'info',
      text: openNative
        ? 'Exporting 3D STEP solid model and launching CAD viewer (FreeCAD)...'
        : 'Exporting 3D STEP solid model from PCB layout...',
    });
    try {
      const res = await api.exportCADStep(revisionId, openNative);
      if (res?.available) {
        setRouteStatus({
          type: 'success',
          text: openNative && res?.opened
            ? `Exported ${res.filename} (${(res.size_bytes / 1024 / 1024).toFixed(2)} MB) and launched in FreeCAD. (Tip: Press 'V' then 'F' in FreeCAD to fit the model to screen)`
            : `3D STEP CAD Model exported successfully: ${res.filename} (${(res.size_bytes / 1024 / 1024).toFixed(2)} MB).`,
        });
        load3d(d3View);
      } else {
        setRouteStatus({
          type: 'error',
          text: `STEP export notice: ${res?.error || 'Unknown error'}`,
        });
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `STEP export failed: ${err.message || String(err)}`,
      });
    } finally {
      setExportingStep(false);
    }
  };
  const [d3View, setD3View] = useState<'iso' | 'top' | 'bottom' | 'iso_bottom'>('iso');
  const [raytracing, setRaytracing] = useState<boolean>(false);

  const load3d = (view: 'iso' | 'top' | 'bottom' | 'iso_bottom' = d3View) => {
    setLoading(true);
    setD3View(view);
    api.cadPreview(revisionId, '3d', view)
      .then(d3 => setRender3dData(d3))
      .catch((err: any) => setError(err.message || String(err)))
      .finally(() => setLoading(false));
  };

  const handleTriggerRaytrace = async () => {
    setRaytracing(true);
    setRouteStatus({
      type: 'info',
      text: `Executing KiCad 10 raytracer for ${d3View.toUpperCase()} 3D view (1400×1050)...`,
    });
    try {
      const res = await api.render3D(revisionId, d3View, 1400, 1050);
      if (res?.success && res?.render_image) {
        setRender3dData(res);
        setRouteStatus({
          type: 'success',
          text: `Photorealistic 3D render generated: ${res.filename} (${(res.render_bytes / 1024).toFixed(1)} KB, ${res.width}×${res.height}, SHA: ${(res.sha256 || '').slice(0, 10)}...)`,
        });
      } else {
        setRouteStatus({
          type: 'error',
          text: `3D Raytracing notice: ${res?.error || 'Rendering did not produce an image'}`,
        });
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `3D Raytracing failed: ${err.message || String(err)}`,
      });
    } finally {
      setRaytracing(false);
    }
  };

  const [copperWeight, setCopperWeight] = useState<'1oz' | '2oz'>('1oz');
  const [millingSlot, setMillingSlot] = useState<boolean>(false);
  const [configuringPlanes, setConfiguringPlanes] = useState<boolean>(false);

  const handleSetup4LayerPlanes = async () => {
    setConfiguringPlanes(true);
    setRouteStatus({
      type: 'info',
      text: 'Configuring native four-layer copper planes...',
    });
    try {
      const res = await api.setup4LayerPlanes({
        revision_id: revisionId,
        gnd_net: 'PRI_GND',
        pwr_net: 'VIN',
        zone_clearance: 0.5,
        thermal_spoke: copperWeight === '2oz' ? 0.8 : 0.5,
        pad_connection: 'tht_thermal',
      });
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `4-Layer configuration: In1.Cu (${res.gnd_net}) ${res.in1_gnd_poured ? 'poured' : 'pending'}, In2.Cu (${res.pwr_net}) ${res.in2_pwr_poured ? 'poured' : 'pending'}. DRC: ${res.drc?.errors ?? 'unavailable'} errors, ${res.drc?.warnings ?? 'unavailable'} warnings. No standards qualification implied.`,
        });
        loadData();
      } else {
        setRouteStatus({
          type: 'error',
          text: `4-Layer configuration notice: ${res.messages?.join('; ') || 'Failed to configure 4-layer planes.'}`,
        });
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `4-Layer configuration failed: ${err.message || String(err)}`,
      });
    } finally {
      setConfiguringPlanes(false);
    }
  };

  const handleMillIsolationSlot = async () => {
    setMillingSlot(true);
    setRouteStatus({
      type: 'info',
      text: 'Adding 2.5mm Edge.Cuts slot geometry between primary and secondary domains...',
    });
    try {
      const res = await api.millIsolationSlot(revisionId, 2.5);
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `Slot geometry added on Edge.Cuts (${res.slot_geometry.width_mm}mm × ${res.slot_geometry.length_mm}mm). Copper zones automatically refilled with clearance back-off. DRC: ${res.drc?.errors ?? 'unavailable'} errors, ${res.drc?.warnings ?? 'unavailable'} warnings.`,
        });
        loadData();
      } else {
        setRouteStatus({
          type: 'error',
          text: `Slot milling notice: ${res.error || 'Failed to mill isolation slot.'}`,
        });
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `Slot milling failed: ${err.message || String(err)}`,
      });
    } finally {
      setMillingSlot(false);
    }
  };

  const handleAutoRoute = async () => {
    setRouting(true);
    const isHeavy = copperWeight === '2oz';
    const powerTrack = isHeavy ? 2.0 : 1.2;
    const thermalSpoke = isHeavy ? 0.8 : 0.5;
    const thermalGap = isHeavy ? 0.6 : 0.5;
    setRouteStatus({
      type: 'info',
      text: `Executing Copper guided topological router (${copperWeight}: ${powerTrack}mm power track, ${thermalSpoke}mm thermal spoke)...`,
    });
    try {
      const res = await api.autoRoutePCB(revisionId, true, powerTrack, 0.4, thermalSpoke, thermalGap, 'tht_thermal', false, 5.0, 0.5);
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `Auto-routing completed (${copperWeight}): ${res.tracks} copper tracks, ${res.vias} vias, DRC: ${res.drc_errors} errors. Unconnected: ${res.unrouted_after ?? 'unavailable'}, warnings: ${res.drc_warnings ?? 'unavailable'}. Ground fill: ${res.pour_completed ? 'completed' : 'not completed'}. `,
        });
        loadData();
      } else {
        setRouteStatus({
          type: 'error',
          text: `Routing incomplete or unverified: ${res.unrouted_after ?? 'unknown'} unconnected; DRC: ${res.drc_errors ?? 'unavailable'} errors. ${res.messages?.join(', ') || res.error || ''}`,
        });
        loadData();
      }
    } catch (err: any) {
      setRouteStatus({
        type: 'error',
        text: `Routing failed: ${err.message || String(err)}`,
      });
    } finally {
      setRouting(false);
    }
  };

  busy.current = routing || exportingGerbers || millingSlot || configuringPlanes;
  const loadData = async (silent = false) => {
    if (silent && busy.current) return;
    const generation=++requestGeneration.current;
    const revision=revisionId;
    if (!silent) setLoading(true);
    setError(null);
    const result=await Promise.allSettled([api.cadPreview(revision,'pcb'),api.cadPreview(revision,'schematic')]);
    if (activeRevision.current!==revision || generation!==requestGeneration.current) return;
    const pcb=result[0].status==='fulfilled' ? result[0].value : {available:false,error:String(result[0].reason)};
    const sch=result[1].status==='fulfilled' ? result[1].value : {available:false,error:String(result[1].reason)};
    if (sourceIdentity.current !== pcb.source_hash) {
      sourceIdentity.current=pcb.source_hash || null;
      setThermalData(null);setShowThermalOverlay(false);setRender3dData(null);
    }
    setPcbData(pcb);setSchData(sch);
    setGerberInfo(pcb.has_gerbers ? {available:true,filename:pcb.gerber_filename,zipPath:pcb.gerber_zip_path,sha256:pcb.gerber_sha256,bytes:pcb.gerber_bytes} : null);
    if (!silent) setPreviewEpoch(e=>e+1);
    setLoading(false);
  };
  useEffect(() => {
    ++requestGeneration.current;sourceIdentity.current=null;
    setPcbData(null);setSchData(null);setRender3dData(null);setGerberInfo(null);setThermalData(null);setShowThermalOverlay(false);setRouteStatus(null);
    loadData();
    const timer=setInterval(()=>{ if (!document.hidden) loadData(true); },4000);
    return ()=>{clearInterval(timer);++requestGeneration.current;};
  }, [revisionId]);
  useEffect(()=>{setThermalData(null);setShowThermalOverlay(false);},[copperWeight]);
  useEffect(()=>{if(viewMode==='3d') load3d(d3View);},[viewMode,pcbData?.source_hash]);

  const activeData = viewMode === 'pcb' ? pcbData : schData;
  const bbox = activeData?.bbox || { min_x: 0, min_y: 0, max_x: 200, max_y: 150, width: 200, height: 150 };

  // Calculate viewBox with padding
  const pad = 10;
  const vbX = bbox.min_x - pad;
  const vbY = bbox.min_y - pad;
  const vbW = Math.max(50, bbox.width + pad * 2);
  const vbH = Math.max(40, bbox.height + pad * 2);

  const renderInteractiveSymbol = (sym: any) => {
    const ref = (sym.ref || '').toUpperCase();
    const lib = (sym.lib_id || '').toUpperCase();
    const val = (sym.value || '').toUpperCase();

    // Resistor
    if (ref.startsWith('R') || lib.includes('RESISTOR')) {
      return (
        <g stroke="#f87171" strokeWidth="0.45" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <line x1="-5" y1="0" x2="-3.2" y2="0" />
          <path d="M -3.2 0 L -2.4 -1.8 L -0.8 1.8 L 0.8 -1.8 L 2.4 1.8 L 3.2 0" />
          <line x1="3.2" y1="0" x2="5" y2="0" />
        </g>
      );
    }
    // Capacitor
    if (ref.startsWith('C') || lib.includes('CAPACITOR')) {
      const isPolar = lib.includes('POLAR') || val.includes('CP');
      return (
        <g strokeLinecap="round" strokeLinejoin="round">
          <line x1="-5" y1="0" x2="-1.2" y2="0" stroke="#38bdf8" strokeWidth="0.45" />
          <line x1="-1.2" y1="-3.2" x2="-1.2" y2="3.2" stroke="#38bdf8" strokeWidth="0.6" />
          {isPolar ? (
            <path d="M 1.2 -3.2 A 4 4 0 0 0 1.2 3.2" stroke="#38bdf8" strokeWidth="0.6" fill="none" />
          ) : (
            <line x1="1.2" y1="-3.2" x2="1.2" y2="3.2" stroke="#38bdf8" strokeWidth="0.6" />
          )}
          <line x1="1.2" y1="0" x2="5" y2="0" stroke="#38bdf8" strokeWidth="0.45" />
          {isPolar && <text x="-3" y="-2" fontSize="2" fill="#ef4444" fontWeight="bold">+</text>}
        </g>
      );
    }
    // Diode & Bridge
    if (lib.includes('BRIDGE') || val.includes('BRIDGE')) {
      return (
        <g strokeLinecap="round" strokeLinejoin="round">
          <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#1e293b" stroke="#f59e0b" strokeWidth="0.5" />
          <text x="0" y="-1" fontSize="1.8" fill="#ef4444" textAnchor="middle" fontWeight="bold">+</text>
          <text x="0" y="3.5" fontSize="1.8" fill="#94a3b8" textAnchor="middle" fontWeight="bold">-</text>
          <text x="-2.5" y="1" fontSize="1.5" fill="#38bdf8" textAnchor="middle">~</text>
          <text x="2.5" y="1" fontSize="1.5" fill="#38bdf8" textAnchor="middle">~</text>
        </g>
      );
    }
    if (ref.startsWith('D') || lib.includes('DIODE')) {
      return (
        <g strokeLinecap="round" strokeLinejoin="round">
          <line x1="-5" y1="0" x2="-2" y2="0" stroke="#f59e0b" strokeWidth="0.45" />
          <polygon points="-2,-2.5 1.8,0 -2,2.5" fill="#f59e0b" stroke="#f59e0b" strokeWidth="0.45" />
          <line x1="1.8" y1="-2.8" x2="1.8" y2="2.8" stroke="#f59e0b" strokeWidth="0.6" />
          <line x1="1.8" y1="0" x2="5" y2="0" stroke="#f59e0b" strokeWidth="0.45" />
        </g>
      );
    }
    // Inductor
    if (ref.startsWith('L') || lib.includes('INDUCTOR')) {
      return (
        <g stroke="#a855f7" strokeWidth="0.45" fill="none" strokeLinecap="round">
          <line x1="-5" y1="0" x2="-3.5" y2="0" />
          <path d="M -3.5 0 A 1.2 1.2 0 0 1 -1.1 0 A 1.2 1.2 0 0 1 1.1 0 A 1.2 1.2 0 0 1 3.5 0" />
          <line x1="3.5" y1="0" x2="5" y2="0" />
        </g>
      );
    }
    // Transformer
    if (ref.startsWith('T') || lib.includes('TRANSFORMER')) {
      return (
        <g strokeLinecap="round">
          <path d="M -2 -4 A 1.3 1.3 0 0 0 -2 -1.4 A 1.3 1.3 0 0 0 -2 1.4 A 1.3 1.3 0 0 0 -2 4" stroke="#a855f7" strokeWidth="0.45" fill="none" />
          <line x1="-0.6" y1="-4.5" x2="-0.6" y2="4.5" stroke="#94a3b8" strokeWidth="0.35" />
          <line x1="0.6" y1="-4.5" x2="0.6" y2="4.5" stroke="#94a3b8" strokeWidth="0.35" />
          <path d="M 2 -4 A 1.3 1.3 0 0 1 2 -1.4 A 1.3 1.3 0 0 1 2 1.4 A 1.3 1.3 0 0 1 2 4" stroke="#38bdf8" strokeWidth="0.45" fill="none" />
        </g>
      );
    }
    // Transistor / MOSFET
    if (ref.startsWith('Q') || lib.includes('MOSFET') || lib.includes('TRANSISTOR')) {
      return (
        <g stroke="#10b981" strokeWidth="0.45" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <line x1="-4" y1="0" x2="-1.5" y2="0" />
          <line x1="-1.5" y1="-3" x2="-1.5" y2="3" strokeWidth="0.7" />
          <line x1="0" y1="-3.2" x2="0" y2="-1.5" strokeWidth="0.6" />
          <line x1="0" y1="-0.8" x2="0" y2="0.8" strokeWidth="0.6" />
          <line x1="0" y1="1.5" x2="0" y2="3.2" strokeWidth="0.6" />
          <line x1="0" y1="-2.4" x2="3" y2="-2.4" />
          <line x1="3" y1="-2.4" x2="3" y2="-4.5" />
          <line x1="0" y1="2.4" x2="3" y2="2.4" />
          <line x1="3" y1="2.4" x2="3" y2="4.5" />
        </g>
      );
    }
    // Connector
    if (ref.startsWith('J') || lib.includes('CONN')) {
      return (
        <g strokeLinecap="round" strokeLinejoin="round">
          <rect x="-4.5" y="-4.5" width="9" height="9" rx="1.5" fill="#1e293b" stroke="#0284c7" strokeWidth="0.45" />
          <circle cx="0" cy="-2" r="1.1" fill="#0f172a" stroke="#38bdf8" strokeWidth="0.4" />
          <circle cx="0" cy="2" r="1.1" fill="#0f172a" stroke="#38bdf8" strokeWidth="0.4" />
        </g>
      );
    }
    // IC / Generic
    return (
      <g strokeLinecap="round" strokeLinejoin="round">
        <rect x="-6" y="-7.5" width="12" height="15" rx="1" fill="#1e293b" stroke="#e2e8f0" strokeWidth="0.45" />
        <path d="M -2 -7.5 A 2 2 0 0 0 2 -7.5" fill="none" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="-8" y1="-4" x2="-6" y2="-4" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="-8" y1="0" x2="-6" y2="0" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="-8" y1="4" x2="-6" y2="4" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="6" y1="-4" x2="8" y2="-4" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="6" y1="0" x2="8" y2="0" stroke="#e2e8f0" strokeWidth="0.4" />
        <line x1="6" y1="4" x2="8" y2="4" stroke="#e2e8f0" strokeWidth="0.4" />
      </g>
    );
  };

  return (
    <div style={{ background: '#0b1120', borderRadius: 10, padding: 20, color: '#f8fafc', border: '1px solid #1e293b' }}>
      {/* Header & Mode Selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={18} color="#38bdf8" />
            <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
              Native 2D CAD & Circuit Preview Canvas
            </h4>
            <span style={{ fontSize: 11, background: '#1e293b', color: '#10b981', padding: '2px 8px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
              <CheckCircle2 size={12} />
              Native KiCad 10 Parser Active
            </span>
            {viewMode === 'pcb' && activeData?.drc_summary && (
              <span
                style={{
                  fontSize: 11,
                  background: activeData.drc_summary.status === 'CLEAR' ? 'rgba(16, 185, 129, 0.15)' : activeData.drc_summary.status === 'WARNINGS' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: activeData.drc_summary.status === 'CLEAR' ? '#34d399' : activeData.drc_summary.status === 'WARNINGS' ? '#fbbf24' : '#f87171',
                  border: `1px solid ${activeData.drc_summary.status === 'CLEAR' ? 'rgba(16, 185, 129, 0.4)' : activeData.drc_summary.status === 'WARNINGS' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                DRC: {activeData.drc_summary.status} ({activeData.drc_summary.errors ?? 'unknown'} errors, {activeData.drc_summary.warnings ?? 'unknown'} warnings, {activeData.drc_summary.unconnected ?? 'unknown'} unconnected)
              </span>
            )}
            {viewMode === 'schematic' && activeData?.erc_summary && (
              <span
                style={{
                  fontSize: 11,
                  background: activeData.erc_summary.status === 'CLEAR' ? 'rgba(16, 185, 129, 0.15)' : activeData.erc_summary.status === 'WARNINGS' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: activeData.erc_summary.status === 'CLEAR' ? '#34d399' : activeData.erc_summary.status === 'WARNINGS' ? '#fbbf24' : '#f87171',
                  border: `1px solid ${activeData.erc_summary.status === 'CLEAR' ? 'rgba(16, 185, 129, 0.4)' : activeData.erc_summary.status === 'WARNINGS' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                ERC: {activeData.erc_summary.status} ({activeData.erc_summary.errors} errors, {activeData.erc_summary.warnings} warnings)
              </span>
            )}
          </div>
          <span style={{ fontSize: 11, color: '#64748b', display: 'block', marginTop: 4 }}>
            {viewMode === 'gerber' ? (
              <>RS-274X Gerber & Excellon Drill Layer Stack with Precision Clearance Ruler</>
            ) : viewMode === '3d' ? (
              <>High-resolution 3D raytraced photorealistic preview</>
            ) : viewMode === 'pcb' ? (
              <>Direct vector geometry extracted from <code>{pcbData?.filename || 'pcb.kicad_pcb'}</code></>
            ) : (
              <>Direct vector geometry extracted from <code>{schData?.filename || 'schematic.kicad_sch'}</code></>
            )}
          </span>
        </div>

        {/* View Switcher & Actions */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: '#1e293b', borderRadius: 6, padding: 2 }}>
            <button
              onClick={() => setViewMode('pcb')}
              style={{
                background: viewMode === 'pcb' ? '#0284c7' : 'transparent',
                border: 'none',
                color: viewMode === 'pcb' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              2D PCB Layout
            </button>
            <button
              onClick={() => setViewMode('schematic')}
              style={{
                background: viewMode === 'schematic' ? '#0284c7' : 'transparent',
                border: 'none',
                color: viewMode === 'schematic' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Schematic Diagram
            </button>
            <button
              onClick={() => setViewMode('3d')}
              style={{
                background: viewMode === '3d' ? '#0284c7' : 'transparent',
                border: 'none',
                color: viewMode === '3d' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              📷 Raytraced 3D View
            </button>
            <button
              onClick={() => setViewMode('gerber')}
              style={{
                background: viewMode === 'gerber' ? '#4338ca' : 'transparent',
                border: 'none',
                color: viewMode === 'gerber' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🎛️ Gerber & Drill Inspector
            </button>
          </div>

          <button
            onClick={() => loadData()}
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

          {viewMode === 'pcb' && (
            <>
              {/* Thermal Heatmap Toggle (Option 4) */}
              <button
                type="button"
                onClick={toggleThermalHeatmap}
                style={{
                  background: showThermalOverlay ? '#dc2626' : '#1e293b',
                  border: `1px solid ${showThermalOverlay ? '#ef4444' : '#334155'}`,
                  color: '#fff',
                  padding: '5px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: showThermalOverlay ? '0 0 12px rgba(239, 68, 68, 0.45)' : 'none',
                }}
                title="Toggle 2D PCB Thermal Loss & Heatmap Diffusion Overlay"
              >
                <span>🔥</span> Thermal Heatmap
              </button>

              {/* Copper Weight Toggle */}
              <div style={{ display: 'inline-flex', background: '#0f172a', borderRadius: 6, border: '1px solid #334155', padding: 2 }}>
                <button
                  type="button"
                  onClick={() => setCopperWeight('1oz')}
                  style={{
                    background: copperWeight === '1oz' ? '#2563eb' : 'transparent',
                    border: 'none',
                    color: '#fff',
                    fontSize: 11,
                    padding: '4px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontWeight: copperWeight === '1oz' ? 700 : 400,
                  }}
                  title="Standard 1 oz copper weight (35 µm)"
                >
                  1 oz
                </button>
                <button
                  type="button"
                  onClick={() => setCopperWeight('2oz')}
                  style={{
                    background: copperWeight === '2oz' ? '#ea580c' : 'transparent',
                    border: 'none',
                    color: '#fff',
                    fontSize: 11,
                    padding: '4px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontWeight: copperWeight === '2oz' ? 700 : 400,
                  }}
                  title="Heavy 2 oz copper weight (70 µm) with widened power traces & thermal relief"
                >
                  2 oz Heavy
                </button>
              </div>

              {/* 4-Layer Power Plane Wizard Button */}
              <button
                type="button"
                onClick={handleSetup4LayerPlanes}
                disabled={configuringPlanes || routing || loading}
                style={{
                  background: configuringPlanes ? '#0891b2' : pcbData?.is_4layer ? '#0e7490' : '#0284c7',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: configuringPlanes ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: '0 2px 8px rgba(2, 132, 199, 0.4)',
                }}
                title="Configure native internal copper planes; this does not qualify a standard or safety requirement"
              >
                <Layers size={13} className={configuringPlanes ? 'spin' : ''} />
                {configuringPlanes ? 'Configuring Planes...' : pcbData?.is_4layer ? '🥞 4-Layer Active' : '🥞 4-Layer Planes'}
              </button>

              {/* Isolation Slot Milling Button */}
              <button
                type="button"
                onClick={handleMillIsolationSlot}
                disabled={millingSlot || routing || loading}
                style={{
                  background: millingSlot ? '#b45309' : '#d97706',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: millingSlot ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: '0 2px 8px rgba(217, 119, 6, 0.4)',
                }}
                title="Mill physical Edge.Cuts isolation air slot between primary and secondary domains"
              >
                <Scissors size={13} className={millingSlot ? 'spin' : ''} />
                {millingSlot ? 'Milling Slot...' : '✂️ Mill Isolation Slot'}
              </button>

              <button
                onClick={handleAutoRoute}
                disabled={routing || exportingGerbers || loading}
                style={{
                  background: routing ? '#4c1d95' : '#7c3aed',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: routing ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: '0 2px 8px rgba(124, 58, 237, 0.4)',
                }}
              >
                <Zap size={13} className={routing ? 'spin' : ''} />
                {routing ? 'Routing Board...' : '⚡ Auto-Route Board'}
              </button>

              {gerberInfo?.available && (
                <button
                  onClick={() => setViewMode('gerber')}
                  style={{
                    background: '#4338ca',
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
                    boxShadow: '0 2px 8px rgba(67, 56, 202, 0.4)',
                  }}
                  title="Inspect RS-274X Gerber layers and Excellon drill schedule"
                >
                  <Eye size={13} />
                  👁️ Inspect Layers
                </button>
              )}

              {gerberInfo?.available && (
                <button
                  onClick={handleDownloadGerbers}
                  disabled={downloadingGerbers}
                  style={{
                    background: '#047857',
                    border: 'none',
                    color: '#fff',
                    padding: '6px 12px',
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: downloadingGerbers ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    boxShadow: '0 2px 8px rgba(4, 120, 87, 0.4)',
                  }}
                  title="Directly download manufacturing Gerber & drill ZIP"
                >
                  <Download size={13} className={downloadingGerbers ? 'spin' : ''} />
                  {downloadingGerbers ? 'Downloading...' : '⬇️ Download Gerbers'}
                </button>
              )}

              {gerberInfo?.available && (
                <button
                  onClick={handleRevealGerbers}
                  style={{
                    background: '#334155',
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
                  title="Reveal Gerber ZIP in Windows File Explorer"
                >
                  <Folder size={13} />
                  In Explorer
                </button>
              )}

              <button
                onClick={handleExportGerbers}
                disabled={exportingGerbers || routing || loading}
                style={{
                  background: exportingGerbers ? '#115e59' : '#0d9488',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: exportingGerbers ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: '0 2px 8px rgba(13, 148, 136, 0.4)',
                }}
              >
                <Package size={13} className={exportingGerbers ? 'spin' : ''} />
                {exportingGerbers ? 'Exporting...' : gerberInfo?.available ? '📦 Re-Export Gerbers' : '📦 Export Gerbers'}
              </button>
            </>
          )}

          {viewMode === 'pcb' && onOpenPCB && (
            <button
              onClick={onOpenPCB}
              style={{
                background: '#047857',
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
              Open in KiCad PCB
            </button>
          )}

          {viewMode === 'schematic' && onOpenSchematic && (
            <button
              onClick={onOpenSchematic}
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
              Open in KiCad Schematic
            </button>
          )}

          {viewMode === 'gerber' && (
        <div style={{ marginTop: 6 }}>
          <GerberLayerInspector key={`${revisionId}:${pcbData?.source_hash}:${previewEpoch}`} revisionId={revisionId} />
        </div>
      )}

      {viewMode === '3d' && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={handleTriggerRaytrace}
                disabled={raytracing || loading}
                title="Execute high-resolution raytraced 3D rendering with KiCad 10 raytracer"
                style={{
                  background: raytracing ? '#1e3a8a' : '#2563eb',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: raytracing ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: '0 2px 8px rgba(37, 99, 235, 0.4)',
                }}
              >
                <Camera size={13} className={raytracing ? 'spin' : ''} />
                {raytracing ? 'Raytracing...' : '📸 Re-Render 3D'}
              </button>

              <button
                onClick={() => handleExportStep(false)}
                disabled={exportingStep || loading}
                title="Generate 3D STEP mechanical solid model of the board"
                style={{
                  background: '#1e293b',
                  border: '1px solid #475569',
                  color: '#f8fafc',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: exportingStep ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <Package size={13} />
                {exportingStep ? 'Exporting STEP...' : 'Export 3D STEP CAD'}
              </button>

              <button
                onClick={() => handleExportStep(true)}
                disabled={exportingStep || loading}
                title="Export STEP and open in FreeCAD 1.1"
                style={{
                  background: '#0284c7',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: exportingStep ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <ExternalLink size={13} />
                Open in FreeCAD
              </button>

              {onOpenPCB && (
                <button
                  onClick={onOpenPCB}
                  title="Open native KiCad 3D Viewer"
                  style={{
                    background: '#047857',
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
                  Open in KiCad 3D Viewer
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Route Status Banner */}
      {routeStatus && (
        <div
          style={{
            marginBottom: 14,
            padding: '8px 14px',
            borderRadius: 6,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background:
              routeStatus.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : routeStatus.type === 'error'
                ? 'rgba(239, 68, 68, 0.15)'
                : 'rgba(56, 189, 248, 0.15)',
            border: `1px solid ${
              routeStatus.type === 'success'
                ? '#059669'
                : routeStatus.type === 'error'
                ? '#dc2626'
                : '#0284c7'
            }`,
            color:
              routeStatus.type === 'success'
                ? '#34d399'
                : routeStatus.type === 'error'
                ? '#f87171'
                : '#38bdf8',
          }}
        >
          <span>{routeStatus.text}</span>
          <button
            onClick={() => setRouteStatus(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              fontWeight: 'bold',
              padding: '0 4px',
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Loading & Error */}
      {loading && (
        <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
          <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginRight: 10 }} />
          Parsing native KiCad vector geometry...
        </div>
      )}

      {error && !loading && (
        <div style={{ padding: 24, background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: 8, color: '#fca5a5', fontSize: 13 }}>
          <strong>CAD Preview Error:</strong> {error}
        </div>
      )}

      {/* Schematic KiCad Vector Viewer */}
      {!loading && !error && viewMode === 'schematic' && schViewMode === 'kicad_vector' && schData?.svg_content && (
        <div
          style={{
            position: 'relative',
            background: '#ffffff',
            borderRadius: 8,
            border: '1px solid #cbd5e1',
            padding: '16px',
            overflow: 'auto',
            maxHeight: '620px',
            boxShadow: 'inset 0 1px 4px rgba(0,0,0,0.05)',
          }}
        >
          {/* Zoom controls */}
          <div
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              display: 'flex',
              gap: 4,
              background: 'rgba(15, 23, 42, 0.85)',
              backdropFilter: 'blur(4px)',
              padding: 4,
              borderRadius: 6,
              zIndex: 10,
            }}
          >
            <button
              onClick={() => setSchZoom((z) => Math.min(z + 0.25, 3.0))}
              style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', padding: 4 }}
              title="Zoom In"
            >
              <ZoomIn size={14} />
            </button>
            <span style={{ color: '#94a3b8', fontSize: 11, alignSelf: 'center', minWidth: 38, textAlign: 'center' }}>
              {Math.round(schZoom * 100)}%
            </span>
            <button
              onClick={() => setSchZoom((z) => Math.max(z - 0.25, 0.5))}
              style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', padding: 4 }}
              title="Zoom Out"
            >
              <ZoomOut size={14} />
            </button>
            <button
              onClick={() => setSchZoom(1.0)}
              style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', padding: '0 4px', fontSize: 10, fontWeight: 700 }}
              title="Reset Zoom"
            >
              1:1
            </button>
            <button
              onClick={() => setSchViewMode('interactive')}
              style={{ background: '#0284c7', border: 'none', color: '#fff', cursor: 'pointer', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, marginLeft: 4 }}
              title="Switch to Net Inspector"
            >
              Net Inspector
            </button>
          </div>
          <div
            style={{
              transform: `scale(${schZoom})`,
              transformOrigin: 'top left',
              transition: 'transform 0.15s ease-out',
              width: `${100 / schZoom}%`,
            }}
            dangerouslySetInnerHTML={{ __html: schData.svg_content }}
          />
        </div>
      )}

      {/* Interactive Vector Canvas */}
      {!loading && !error && viewMode !== '3d' && viewMode !== 'gerber' && activeData?.available && !(viewMode === 'schematic' && schViewMode === 'kicad_vector' && schData?.svg_content) && (
        <div style={{ position: 'relative' }}>
          <svg
            viewBox={`${vbX} ${vbY} ${vbW} ${vbH}`}
            style={{
              width: '100%',
              height: '420px',
              background: viewMode === 'pcb' ? '#071811' : '#070b14', // Dark green soldermask for PCB, dark blue for Schematic
              borderRadius: 8,
              border: '1px solid #1e293b',
              boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.6)',
            }}
          >
            {/* Toggle back to KiCad Vector View */}
            {viewMode === 'schematic' && schData?.svg_content && (
              <g
                style={{ cursor: 'pointer' }}
                onClick={() => setSchViewMode('kicad_vector')}
                transform={`translate(${vbX + 10}, ${vbY + 10})`}
              >
                <rect x="0" y="0" width="38" height="7" rx="2" fill="#0284c7" />
                <text x="19" y="4.5" fill="#ffffff" fontSize="2.8" fontWeight="bold" textAnchor="middle" fontFamily="sans-serif">
                  ← KiCad Sheet
                </text>
              </g>
            )}

            {/* Fine Grid Background & Thermal Hotspot Gradients */}
            <defs>
              {showThermalOverlay && viewMode === 'pcb' && (thermalData?.hotspots || []).map((h: any) => {
                const isWarning = h.status === 'WARNING';
                return (
                  <radialGradient key={`t-grad-${h.ref}`} id={`t-grad-${h.ref}`} cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor={isWarning ? "#ef4444" : "#f97316"} stopOpacity="0.80" />
                    <stop offset="35%" stopColor={isWarning ? "#f97316" : "#eab308"} stopOpacity="0.60" />
                    <stop offset="70%" stopColor="#06b6d4" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#0f172a" stopOpacity="0.0" />
                  </radialGradient>
                );
              })}
              <pattern id="cadGrid" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#ffffff" strokeWidth="0.08" opacity={0.12} />
              </pattern>
            </defs>
            <rect x={vbX} y={vbY} width={vbW} height={vbH} fill="url(#cadGrid)" />

            {/* === PCB MODE RENDERING === */}
            {viewMode === 'pcb' && (
              <g>
                {/* 1. Edge.Cuts Outlines and Isolation Slots */}
                {(pcbData.edge_cuts || []).map((e: any, i: number) => {
                  if (e.points) return <polyline key={`ec-${i}`} points={e.points.map((p:number[])=>p.join(',')).join(' ')} fill="none" stroke="#facc15" strokeWidth={.6}/>;
                  if (e.type === 'rect') {
                    const isSlot = (e.x2 - e.x1) <= 6.0 && (e.y2 - e.y1) > 20.0;
                    return (
                      <g key={`ec-${i}`}>
                        <rect
                          x={e.x1}
                          y={e.y1}
                          width={e.x2 - e.x1}
                          height={e.y2 - e.y1}
                          fill={isSlot ? '#070b14' : 'none'}
                          stroke={isSlot ? '#38bdf8' : '#facc15'}
                          strokeWidth={isSlot ? 0.35 : 0.6}
                          strokeDasharray={isSlot ? '1.5 1.0' : undefined}
                        />
                        {isSlot && (
                          <text
                            x={(e.x1 + e.x2) / 2}
                            y={(e.y1 + e.y2) / 2}
                            fill="#38bdf8"
                            fontSize="2.2"
                            textAnchor="middle"
                            transform={`rotate(-90 ${(e.x1 + e.x2) / 2} ${(e.y1 + e.y2) / 2})`}
                            fontFamily="sans-serif"
                            fontWeight="bold"
                          >
                            5.0mm HV Isolation Slot (IEC 61010-1)
                          </text>
                        )}
                      </g>
                    );
                  }
                  return (
                    <line
                      key={`ec-${i}`}
                      x1={e.x1}
                      y1={e.y1}
                      x2={e.x2}
                      y2={e.y2}
                      stroke="#facc15"
                      strokeWidth="0.6"
                    />
                  );
                })}

                <PCBGeometry data={pcbData} copperOnly />

                {/* 3. Placed Footprints */}
                {(pcbData.footprints || []).map((fp: any, idx: number) => {
                  const isHovered = hoverItem?.ref === fp.ref;
                  return (
                    <g
                      key={`fp-${idx}`}
                      transform={`translate(${fp.x}, ${fp.y}) rotate(${-(fp.rot || 0)})`}
                      onMouseEnter={() => setHoverItem(fp)}
                      onMouseLeave={() => setHoverItem(null)}
                      style={{ cursor: 'pointer' }}
                    >
                      {/* Silkscreen Lines */}
                      {(fp.silks || []).map((s: any, si: number) => {
                        if (s.type === 'rect') {
                          return (
                            <rect
                              key={`s-${si}`}
                              x={s.x1}
                              y={s.y1}
                              width={s.x2 - s.x1}
                              height={s.y2 - s.y1}
                              fill="none"
                              stroke="#f8fafc"
                              strokeWidth="0.2"
                              opacity={0.8}
                            />
                          );
                        }
                        if (s.type === 'circle') {
                          return (
                            <circle
                              key={`s-${si}`}
                              cx={s.cx}
                              cy={s.cy}
                              r={s.r}
                              fill="none"
                              stroke="#f8fafc"
                              strokeWidth="0.2"
                              opacity={0.8}
                            />
                          );
                        }
                        return (
                          <line
                            key={`s-${si}`}
                            x1={s.x1}
                            y1={s.y1}
                            x2={s.x2}
                            y2={s.y2}
                            stroke="#f8fafc"
                            strokeWidth="0.2"
                            opacity={0.8}
                          />
                        );
                      })}

                      {/* Default Footprint Boundary if no silks */}
                      {(!fp.silks || fp.silks.length === 0) && (
                        <rect
                          x="-3.5"
                          y="-3.5"
                          width="7"
                          height="7"
                          fill={isHovered ? 'rgba(56, 189, 248, 0.25)' : 'none'}
                          stroke={isHovered ? '#38bdf8' : '#f8fafc'}
                          strokeWidth="0.2"
                          strokeDasharray="0.8 0.5"
                        />
                      )}

                      {/* Copper Pads */}
                      {(fp.pads || []).map((p: any, pi: number) => {
                        const isThru = p.type === 'thru_hole';
                        const padRot = (p.rot || 0) - (fp.rot || 0);
                        const px = p.ox - (p.sx / 2);
                        const py = p.oy - (p.sy / 2);
                        return (
                          <g key={`p-${pi}`} transform={padRot ? `rotate(${-padRot} ${p.ox} ${p.oy})` : undefined}>
                            <rect
                              x={px}
                              y={py}
                              width={p.sx}
                              height={p.sy}
                              rx={isThru ? p.sx / 2 : 0.2}
                              fill={isThru ? '#10b981' : '#fbbf24'}
                              stroke="#b45309"
                              strokeWidth="0.08"
                            />
                            {isThru && (
                              <circle
                                cx={p.ox}
                                cy={p.oy}
                                r={Math.min(p.sx, p.sy) * 0.28}
                                fill="#070b14"
                              />
                            )}
                          </g>
                        );
                      })}

                      {/* Reference Designator on Silkscreen */}
                      <text
                        x="0"
                        y="-4.2"
                        fill="#f8fafc"
                        fontSize="1.8"
                        fontWeight="bold"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {fp.ref}
                      </text>

                      {/* Value / MPN Label */}
                      <text
                        x="0"
                        y="4.8"
                        fill="#94a3b8"
                        fontSize="1.2"
                        textAnchor="middle"
                        fontFamily="monospace"
                      >
                        {fp.value?.substring(0, 14)}
                      </text>

                      {/* 3D Model Badge Indicator */}
                      {fp.has_3d_model && (
                        <circle cx="2.6" cy="-2.6" r="0.6" fill="#10b981" />
                      )}
                    </g>
                  );
                })}

                {/* 2D PCB Thermal Heatmap Overlay (Option 4) */}
                {showThermalOverlay && viewMode === 'pcb' && thermalData?.hotspots && (
                  <g className="thermal-overlay-layer">
                    {/* 1. Thermal Radial Heat Spreading Circles */}
                    {thermalData.hotspots.map((h: any) => {
                      const r = h.spreading_radius_mm || 14;
                      return (
                        <circle
                          key={`t-circ-${h.ref}`}
                          cx={h.x}
                          cy={h.y}
                          r={r}
                          fill={`url(#t-grad-${h.ref})`}
                          style={{ mixBlendMode: 'screen', pointerEvents: 'none' }}
                        />
                      );
                    })}

                    {/* 2. Interactive Hotspot Markers and Labels */}
                    {thermalData.hotspots.map((h: any) => (
                      <g
                        key={`t-lbl-${h.ref}`}
                        transform={`translate(${h.x}, ${h.y})`}
                        onMouseEnter={() => setThermalHoverSpot(h)}
                        onMouseLeave={() => setThermalHoverSpot(null)}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle cx="0" cy="0" r="2.2" fill="#ffffff" stroke={h.status === 'WARNING' ? "#ef4444" : "#22c55e"} strokeWidth="1" />
                        <rect
                          x="-16"
                          y="-15"
                          width="32"
                          height="10"
                          rx="2.5"
                          fill="rgba(15, 23, 42, 0.90)"
                          stroke={h.status === 'WARNING' ? "#ef4444" : "#22c55e"}
                          strokeWidth="0.8"
                        />
                        <text
                          x="0"
                          y="-8"
                          fontSize="6.5"
                          fontWeight="bold"
                          fill="#ffffff"
                          textAnchor="middle"
                          fontFamily="monospace"
                        >
                          {h.ref}: {Math.round(h.t_junction_c)}°C
                        </text>
                      </g>
                    ))}
                  </g>
                )}
              </g>
            )}

            {/* === SCHEMATIC MODE RENDERING === */}
            {viewMode === 'schematic' && (
              <g>
                {/* Wires */}
                {(schData.wires || []).map((w: any, i: number) => (
                  <line
                    key={`w-${i}`}
                    x1={w.x1}
                    y1={w.y1}
                    x2={w.x2}
                    y2={w.y2}
                    stroke="#22c55e"
                    strokeWidth="0.45"
                    strokeLinecap="round"
                  />
                ))}

                {/* Symbols */}
                {(schData.symbols || []).map((sym: any, idx: number) => (
                  <g
                    key={`s-${idx}`}
                    transform={`translate(${sym.x}, ${sym.y})`}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoverItem(sym)}
                    onMouseLeave={() => setHoverItem(null)}
                  >
                    {renderInteractiveSymbol(sym)}
                    <text
                      x="0"
                      y="-5.5"
                      fill="#f8fafc"
                      fontSize="1.8"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {sym.ref}
                    </text>
                    <text
                      x="0"
                      y="6.2"
                      fill="#38bdf8"
                      fontSize="1.3"
                      fontWeight="600"
                      textAnchor="middle"
                      fontFamily="sans-serif"
                    >
                      {sym.value?.substring(0, 16)}
                    </text>
                  </g>
                ))}

                {/* Labels */}
                {(schData.labels || []).map((l: any, i: number) => (
                  <g key={`l-${i}`} transform={`translate(${l.x}, ${l.y})`}>
                    <circle cx="0" cy="0" r="0.6" fill="#22c55e" />
                    <text
                      x="1.5"
                      y="0.5"
                      fill="#38bdf8"
                      fontSize="1.5"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      {l.name}
                    </text>
                  </g>
                ))}
              </g>
            )}
          </svg>

          {/* Hover Tooltip Overlay */}
          {hoverItem && (
            <div
              style={{
                position: 'absolute',
                top: 12,
                right: 12,
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(8px)',
                padding: '10px 16px',
                borderRadius: 6,
                border: '1px solid #38bdf8',
                fontSize: 12,
                fontFamily: 'monospace',
                pointerEvents: 'none',
                boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
              }}
            >
              <div style={{ color: '#38bdf8', fontWeight: 800, fontSize: 13, borderBottom: '1px solid #334155', paddingBottom: 4, marginBottom: 6 }}>
                Component: {hoverItem.ref}
              </div>
              <div style={{ color: '#f8fafc', marginBottom: 2 }}>
                <strong>Value:</strong> {hoverItem.value || 'N/A'}
              </div>
              {hoverItem.name && (
                <div style={{ color: '#94a3b8', marginBottom: 2 }}>
                  <strong>Footprint:</strong> {hoverItem.name}
                </div>
              )}
              {hoverItem.lib_id && (
                <div style={{ color: '#94a3b8', marginBottom: 2 }}>
                  <strong>Symbol:</strong> {hoverItem.lib_id}
                </div>
              )}
              {hoverItem.pads && (
                <div style={{ color: '#94a3b8', marginBottom: 2 }}>
                  <strong>Pads:</strong> {hoverItem.pads.length} terminals
                </div>
              )}
              {hoverItem.has_3d_model !== undefined && (
                <div style={{ color: hoverItem.has_3d_model ? '#10b981' : '#f59e0b', marginTop: 4 }}>
                  {hoverItem.has_3d_model ? '✓ 3D STEP Model Linked' : '⚠ No 3D Model Attached'}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Thermal Heatmap HUD Telemetry Banner (Option 4) */}
      {showThermalOverlay && viewMode === 'pcb' && thermalData && (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
            border: '1px solid #334155',
            borderRadius: 8,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
            color: '#f8fafc',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 16 }}>🔥</span>
              <div>
                <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
                  Peak PCB Hotspot (Tj,max)
                </div>
                <div style={{ fontSize: 15, fontWeight: 800, color: thermalData.overall_status === 'CLEAR' ? '#22c55e' : '#f59e0b' }}>
                  {thermalData.max_temperature_c.toFixed(1)}°C on {thermalData.max_component}
                </div>
              </div>
            </div>

            <div style={{ borderLeft: '1px solid #334155', paddingLeft: 14 }}>
              <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
                Total Board Dissipation
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                {thermalData.total_board_loss_w.toFixed(2)} W
              </div>
            </div>

            <div style={{ borderLeft: '1px solid #334155', paddingLeft: 14 }}>
              <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
                Copper Spreading
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#38bdf8' }}>
                {thermalData.copper_weight_oz.toFixed(1)} oz Top/Bottom Pour
              </div>
            </div>

            {/* Chassis Cooling & TIM Toggle Button */}
            <div style={{ borderLeft: '1px solid #334155', paddingLeft: 14, display: 'flex', alignItems: 'center' }}>
              <button
                onClick={toggleChassisCooling}
                disabled={loadingThermal}
                style={{
                  padding: '5px 12px',
                  background: chassisCooling ? '#065f46' : '#7f1d1d',
                  border: `1px solid ${chassisCooling ? '#10b981' : '#ef4444'}`,
                  borderRadius: 6,
                  color: '#ffffff',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: loadingThermal ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  boxShadow: chassisCooling ? '0 0 8px rgba(16, 185, 129, 0.35)' : 'none',
                }}
                title={chassisCooling ? 'Click to simulate bare PCB in still air (143.6°C)' : 'Click to enable Bergquist TIM Gap Pad & 6061 Aluminum Chassis cooling (55.8°C)'}
              >
                <span>{chassisCooling ? '📦 Chassis TIM Pad: ACTIVE' : '🌬️ Bare PCB (Still Air)'}</span>
              </button>
            </div>
          </div>

          {/* Color Gradient Legend Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10.5, color: '#94a3b8' }}>
            <span>25°C</span>
            <div
              style={{
                width: 140,
                height: 10,
                borderRadius: 5,
                background: 'linear-gradient(90deg, #06b6d4 0%, #84cc16 35%, #f97316 70%, #ef4444 100%)',
              }}
            />
            <span>120°C+</span>
          </div>
        </div>
      )}

      {/* Thermal Component Hover Tooltip Card */}
      {thermalHoverSpot && (
        <div
          style={{
            marginTop: 8,
            padding: '10px 14px',
            background: '#070b14',
            border: `1px solid ${thermalHoverSpot.status === 'WARNING' ? '#ef4444' : '#22c55e'}`,
            borderRadius: 6,
            fontSize: 11.5,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            color: '#f8fafc',
          }}
        >
          <div>
            <strong style={{ color: '#38bdf8' }}>{thermalHoverSpot.ref}</strong> ({thermalHoverSpot.name}) — {thermalHoverSpot.package}
            <div style={{ fontSize: 10.5, color: '#94a3b8', marginTop: 2 }}>
              Loss: <strong>{thermalHoverSpot.loss_w.toFixed(2)} W</strong> ({thermalHoverSpot.loss_breakdown}) • RθJA: {thermalHoverSpot.r_th_ja_c_w}°C/W
            </div>
          </div>
          <div style={{ textAlign: 'right', fontFamily: 'monospace' }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: thermalHoverSpot.status === 'WARNING' ? '#ef4444' : '#22c55e' }}>
              Tj = {thermalHoverSpot.t_junction_c.toFixed(1)}°C
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>
              Derated Margin: {thermalHoverSpot.thermal_margin_c > 0 ? `+${thermalHoverSpot.thermal_margin_c.toFixed(1)}` : thermalHoverSpot.thermal_margin_c.toFixed(1)}°C
            </div>
          </div>
        </div>
      )}

      {/* 3D Photorealistic Assembly View */}
      {!loading && !error && viewMode === '3d' && (
        <div
          style={{
            position: 'relative',
            width: '100%',
            minHeight: '440px',
            background: '#070b14',
            borderRadius: 8,
            border: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
            boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.6)',
          }}
        >
          {/* 3D Mode Selector: Raytrace Photo vs Interactive 3D Orbit */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
            <div style={{ display: 'inline-flex', gap: 4, background: '#0f172a', padding: 3, borderRadius: 6, border: '1px solid #334155' }}>
              <button
                type="button"
                onClick={() => setSub3dMode('raytrace')}
                style={{
                  background: sub3dMode === 'raytrace' ? '#2563eb' : 'transparent',
                  border: 'none',
                  color: sub3dMode === 'raytrace' ? '#fff' : '#94a3b8',
                  padding: '5px 12px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                <Camera size={12} />
                <span>📸 Raytraced Photo</span>
              </button>
              <button
                type="button"
                onClick={() => setSub3dMode('orbit')}
                style={{
                  background: sub3dMode === 'orbit' ? '#059669' : 'transparent',
                  border: 'none',
                  color: sub3dMode === 'orbit' ? '#fff' : '#94a3b8',
                  padding: '5px 12px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                <Box size={12} />
                <span>🌐 Interactive 3D Orbit</span>
              </button>
            </div>

            {sub3dMode === 'raytrace' ? (
              <div style={{ display: 'inline-flex', gap: 4, background: '#1e293b', padding: 3, borderRadius: 6 }}>
                <button
                  onClick={() => load3d('iso')}
                  disabled={loading}
                  style={{
                    background: d3View === 'iso' ? '#0284c7' : 'transparent',
                    border: 'none',
                    color: d3View === 'iso' ? '#fff' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  📐 Isometric
                </button>
                <button
                  onClick={() => load3d('top')}
                  disabled={loading}
                  style={{
                    background: d3View === 'top' ? '#0284c7' : 'transparent',
                    border: 'none',
                    color: d3View === 'top' ? '#fff' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  🔝 Top
                </button>
                <button
                  onClick={() => load3d('bottom')}
                  disabled={loading || raytracing}
                  style={{
                    background: d3View === 'bottom' ? '#0284c7' : 'transparent',
                    border: 'none',
                    color: d3View === 'bottom' ? '#fff' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  🔻 Bottom
                </button>
                <button
                  onClick={() => load3d('iso_bottom')}
                  disabled={loading || raytracing}
                  style={{
                    background: d3View === 'iso_bottom' ? '#0284c7' : 'transparent',
                    border: 'none',
                    color: d3View === 'iso_bottom' ? '#fff' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  🔄 Underside
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: '#94a3b8' }}>
                  Pitch: <strong style={{ color: '#f8fafc' }}>{orbitRotX}°</strong> · Yaw: <strong style={{ color: '#f8fafc' }}>{orbitRotZ}°</strong> · Zoom: <strong style={{ color: '#f8fafc' }}>{Math.round(orbitZoom * 100)}%</strong>
                </span>
                <button
                  type="button"
                  onClick={() => { setOrbitRotX(55); setOrbitRotZ(25); setOrbitZoom(1.0); }}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#f8fafc',
                    padding: '4px 10px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Reset View
                </button>
              </div>
            )}
          </div>

          {sub3dMode === 'orbit' && pcbData?.available && (
            <div style={{width:'100%',height:380,perspective:1000,display:'grid',placeItems:'center'}} onWheel={e=>setOrbitZoom(z=>Math.max(.4,Math.min(3,z+(e.deltaY<0?.1:-.1))))} onMouseDown={e=>{setIsOrbitDragging(true);setOrbitDragStart({x:e.clientX,y:e.clientY});}} onMouseUp={()=>setIsOrbitDragging(false)} onMouseLeave={()=>setIsOrbitDragging(false)} onMouseMove={e=>{if(isOrbitDragging){setOrbitRotZ(z=>z+(e.clientX-orbitDragStart.x)*.3);setOrbitRotX(x=>Math.max(0,Math.min(85,x+(e.clientY-orbitDragStart.y)*.3)));setOrbitDragStart({x:e.clientX,y:e.clientY});}}}>
              <svg width="75%" height="80%" viewBox={`${pcbData.bbox.min_x-4} ${pcbData.bbox.min_y-4} ${pcbData.bbox.width+8} ${pcbData.bbox.height+8}`} style={{background:'#071a18',transform:`rotateX(${orbitRotX}deg) rotateZ(${orbitRotZ}deg) scale(${orbitZoom})`}}><PCBGeometry data={pcbData}/></svg>
              <small>Projection of actual PCB geometry; use STEP for solid mechanical models.</small>
            </div>
          )}

          {sub3dMode === 'raytrace' && (
            render3dData?.available && render3dData?.render_image ? (
              <div style={{ textAlign: 'center', width: '100%' }}>
                <img
                  src={render3dData.render_image}
                  alt={render3dData.title || 'KiCad 3D Raytraced PCB Assembly'}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '420px',
                    borderRadius: 6,
                    border: '1px solid #334155',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.7)',
                    objectFit: 'contain',
                  }}
                />
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    gap: 16,
                    marginTop: 14,
                    fontSize: 12,
                    color: '#94a3b8',
                    flexWrap: 'wrap',
                  }}
                >
                  <span>
                    <strong style={{ color: '#f8fafc' }}>Source:</strong> {render3dData.filename}
                  </span>
                  <span>
                    <strong style={{ color: '#f8fafc' }}>Format:</strong> Photorealistic Raytraced ISO
                  </span>
                  <span>
                    <strong style={{ color: '#f8fafc' }}>Size:</strong>{' '}
                    {render3dData.render_bytes ? `${(render3dData.render_bytes / 1024).toFixed(1)} KB` : 'Rendered'}
                  </span>
                  <span style={{ color: '#10b981' }}>
                    ✓ KiCad 10 Raytracer Engine (Copper Integration)
                  </span>
                  {render3dData.has_step && (
                    <span style={{ color: '#38bdf8', fontWeight: 500 }}>
                      📦 STEP Solid: {render3dData.step_filename} ({(render3dData.step_bytes / 1024 / 1024).toFixed(2)} MB)
                      {render3dData.step_sha256 && (
                        <span style={{ marginLeft: 6, fontSize: 11, color: '#34d399', fontWeight: 600 }}>
                          ✓ Cryptographically Verified Solid
                        </span>
                      )}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>
                <Box size={48} color="#475569" style={{ margin: '0 auto 12px' }} />
                <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', marginBottom: 6 }}>
                  3D Raytraced Model Not Yet Generated
                </div>
                <p style={{ fontSize: 12, maxWidth: 450, margin: '0 auto 16px', lineHeight: 1.5 }}>
                  {render3dData?.error || 'A 3D assembly snapshot can be generated automatically from the PCB design using KiCad 10 CLI raytracer.'}
                </p>
                {onOpenPCB && (
                  <button
                    onClick={onOpenPCB}
                    style={{
                      background: '#047857',
                      border: 'none',
                      color: '#fff',
                      padding: '8px 16px',
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    <ExternalLink size={14} />
                    Launch KiCad 3D Viewer (Alt+3 in PCB)
                  </button>
                )}
              </div>
            )
          )}
        </div>
      )}

      {/* PCB Status & Layer Legend */}
      {!loading && !error && viewMode === 'pcb' && activeData?.available && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, flexWrap: 'wrap', gap: 10, fontSize: 11 }}>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: '#facc15' }} />
              Board Outline (Edge.Cuts)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: '#fbbf24' }} />
              SMD Copper Pads
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: '#10b981' }} />
              THT Through-Hole Pads
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: '#38bdf8' }} />
              Edge.Cuts Slot
            </span>
          </div>

          <div style={{ color: '#94a3b8', fontFamily: 'monospace' }}>
            Dimensions: {bbox.width.toFixed(1)} × {bbox.height.toFixed(1)} mm •{' '}
            {pcbData?.tracks?.length > 0
              ? `Copper: ${pcbData.tracks.length} displayed / ${pcbData.native_track_count} native tracks, ${pcbData.vias?.length || 0} vias; connectivity: ${pcbData.connectivity_status}`
              : 'No copper tracks found; connectivity NOT_EVALUATED'}
            {' · '}
            {pcbData?.is_4layer ? (
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>🥞 4-Layer Copper Stackup</span>
            ) : (
              <span style={{ color: '#94a3b8' }}>{pcbData.layer_count} enabled copper layers</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
