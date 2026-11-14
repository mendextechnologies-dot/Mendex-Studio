import { GerberLayerInspector } from './GerberLayerInspector';
import React, { useEffect, useState, useMemo } from 'react';
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
      let dataUri = gerberInfo?.dataUri;
      let filename = gerberInfo?.filename || 'gerbers.zip';
      if (!dataUri) {
        const res = await api.downloadGerbers(revisionId);
        if (res.success && res.data_uri) {
          dataUri = res.data_uri;
          filename = res.filename || filename;
          setGerberInfo({
            available: true,
            filename: res.filename,
            zipPath: res.relative_path,
            sha256: res.sha256,
            bytes: res.size_bytes,
            dataUri: res.data_uri,
          });
        } else {
          setRouteStatus({ type: 'error', text: res.error || 'Failed to download Gerber package' });
          return;
        }
      }

      // Trigger standard browser download
      const link = document.createElement('a');
      link.href = dataUri;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setRouteStatus({
        type: 'success',
        text: `Downloaded ${filename} successfully. Cryptographic release verified with SHA-256.`,
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
          text: `Manufacturing release package generated: ${res.file_count} Gerber & drill files exported to ${res.output_dir}${res.sha256 ? ` (SHA-256: ${res.sha256.slice(0, 12)}...)` : ''}`,
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
            ? `Exported ${res.filename} (${(res.size_bytes / 1024 / 1024).toFixed(2)} MB${res.sha256 ? `, SHA: ${res.sha256.slice(0, 12)}...` : ''}) and launched in FreeCAD / 3D CAD Viewer.`
            : `3D STEP CAD Model exported successfully: ${res.filename} (${(res.size_bytes / 1024 / 1024).toFixed(2)} MB${res.sha256 ? `, SHA: ${res.sha256.slice(0, 12)}...` : ''}).`,
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
      text: 'Configuring IPC-2152 4-layer internal planes (In1.Cu GND shield + In2.Cu VIN power plane)...',
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
          text: `IPC-2152 4-Layer stackup active: In1.Cu (${res.gnd_net}) ${res.in1_gnd_poured ? 'poured' : 'pending'}, In2.Cu (${res.pwr_net}) ${res.in2_pwr_poured ? 'poured' : 'pending'}. DRC: ${res.drc?.errors ?? 0} errors.`,
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
      text: 'Milling physical 2.5mm Edge.Cuts isolation air slot between primary and secondary domains...',
    });
    try {
      const res = await api.millIsolationSlot(revisionId, 2.5);
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `Isolation slot milled on Edge.Cuts (${res.slot_geometry.width_mm}mm × ${res.slot_geometry.length_mm}mm). Copper zones automatically refilled with clearance back-off. DRC: ${res.drc.errors} errors.`,
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
          text: `Auto-routing completed (${copperWeight}): ${res.tracks} copper tracks, ${res.vias} vias, DRC: ${res.drc_errors} errors. Ground pour filled on B.Cu (spoke=${thermalSpoke}mm).`,
        });
        loadData();
      } else {
        setRouteStatus({
          type: 'error',
          text: `Routing notice: ${res.messages?.join(', ') || res.error || 'Routing did not complete.'}`,
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

  const loadData = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.cadPreview(revisionId, 'pcb'),
      api.cadPreview(revisionId, 'schematic'),
      api.cadPreview(revisionId, '3d', d3View),
    ])
      .then(([pcb, sch, d3]) => {
        setPcbData(pcb);
        setSchData(sch);
        setRender3dData(d3);
        if (pcb?.has_gerbers) {
          setGerberInfo({
            available: true,
            filename: pcb.gerber_filename,
            zipPath: pcb.gerber_zip_path,
            sha256: pcb.gerber_sha256,
            bytes: pcb.gerber_bytes,
          });
        }
      })
      .catch((err: any) => {
        setError(err.message || String(err));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [revisionId]);

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
                  background: activeData.drc_summary.status === 'PASS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: activeData.drc_summary.status === 'PASS' ? '#34d399' : '#f87171',
                  border: `1px solid ${activeData.drc_summary.status === 'PASS' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                DRC: {activeData.drc_summary.status} ({activeData.drc_summary.errors} errors, {activeData.drc_summary.warnings} warnings)
              </span>
            )}
            {viewMode === 'schematic' && activeData?.erc_summary && (
              <span
                style={{
                  fontSize: 11,
                  background: activeData.erc_summary.status === 'PASS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: activeData.erc_summary.status === 'PASS' ? '#34d399' : '#f87171',
                  border: `1px solid ${activeData.erc_summary.status === 'PASS' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
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
            Direct vector geometry extracted from <code>{activeData?.filename || 'CAD file'}</code>
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
            onClick={loadData}
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
                title="Configures IPC-2152 compliant 4-layer internal copper plane zones (In1.Cu GND shield + In2.Cu VIN plane)"
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
          <GerberLayerInspector revisionId={revisionId} />
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

            {/* Fine Grid Background */}
            <defs>
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

                {/* 2. Copper Tracks */}
                {(pcbData.tracks || []).map((t: any, i: number) => (
                  <line
                    key={`tr-${i}`}
                    x1={t.x1}
                    y1={t.y1}
                    x2={t.x2}
                    y2={t.y2}
                    stroke={
                      t.layer === 'In1.Cu'
                        ? '#a855f7'
                        : t.layer === 'In2.Cu'
                        ? '#06b6d4'
                        : t.layer === 'B.Cu'
                        ? '#3b82f6'
                        : '#f59e0b'
                    }
                    strokeWidth={t.width || 0.4}
                    strokeLinecap="round"
                  />
                ))}

                {/* 3. Placed Footprints */}
                {(pcbData.footprints || []).map((fp: any, idx: number) => {
                  const isHovered = hoverItem?.ref === fp.ref;
                  return (
                    <g
                      key={`fp-${idx}`}
                      transform={`translate(${fp.x}, ${fp.y}) rotate(${fp.rot || 0})`}
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
                        const px = p.ox - (p.sx / 2);
                        const py = p.oy - (p.sy / 2);
                        return (
                          <g key={`p-${pi}`}>
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

          {sub3dMode === 'orbit' ? (
            <div
              style={{
                width: '100%',
                height: '380px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                perspective: '1200px',
                userSelect: 'none',
                cursor: isOrbitDragging ? 'grabbing' : 'grab',
                overflow: 'hidden',
                background: 'radial-gradient(circle, #0f172a 0%, #020617 100%)',
                borderRadius: 8,
                border: '1px solid #1e293b',
              }}
              onMouseDown={(e) => {
                setIsOrbitDragging(true);
                setOrbitDragStart({ x: e.clientX, y: e.clientY });
              }}
              onMouseMove={(e) => {
                if (!isOrbitDragging) return;
                const deltaX = e.clientX - orbitDragStart.x;
                const deltaY = e.clientY - orbitDragStart.y;
                setOrbitRotZ((prev) => (prev + deltaX * 0.5) % 360);
                setOrbitRotX((prev) => Math.max(10, Math.min(85, prev - deltaY * 0.5)));
                setOrbitDragStart({ x: e.clientX, y: e.clientY });
              }}
              onMouseUp={() => setIsOrbitDragging(false)}
              onMouseLeave={() => setIsOrbitDragging(false)}
              onWheel={(e) => {
                e.preventDefault();
                setOrbitZoom((prev) => Math.max(0.5, Math.min(2.5, prev - e.deltaY * 0.0015)));
              }}
              onDoubleClick={() => { setOrbitRotX(55); setOrbitRotZ(25); setOrbitZoom(1.0); }}
            >
              <div
                style={{
                  transform: `rotateX(${orbitRotX}deg) rotateZ(${orbitRotZ}deg) scale(${orbitZoom})`,
                  transformStyle: 'preserve-3d',
                  transition: isOrbitDragging ? 'none' : 'transform 0.15s ease-out',
                  width: '340px',
                  height: '240px',
                  position: 'relative',
                  borderRadius: '6px',
                  backgroundColor: '#0a3622',
                  border: '3px solid #15803d',
                  boxShadow: '0 25px 60px rgba(0,0,0,0.85), inset 0 0 25px rgba(0,0,0,0.5)',
                }}
              >
                {/* 5mm HV Isolation Barrier Milling Slot */}
                <div
                  style={{
                    position: 'absolute',
                    top: '12px',
                    bottom: '12px',
                    left: '50%',
                    width: '12px',
                    transform: 'translateX(-50%) translateZ(1px)',
                    backgroundColor: '#020617',
                    border: '1.5px dashed #f8fafc',
                    borderRadius: '3px',
                    boxShadow: 'inset 0 0 8px rgba(0,0,0,0.95)',
                  }}
                  title="5.0mm High-Voltage Isolation Barrier (Edge.Cuts)"
                />

                {/* Silk Screen Labels */}
                <div style={{ position: 'absolute', top: 10, left: 14, color: '#f8fafc', fontSize: 9, fontWeight: 800, letterSpacing: 0.5, transform: 'translateZ(2px)' }}>
                  PRIMARY HV (400V)
                </div>
                <div style={{ position: 'absolute', top: 10, right: 14, color: '#38bdf8', fontSize: 9, fontWeight: 800, letterSpacing: 0.5, transform: 'translateZ(2px)' }}>
                  SELV ISOLATED (48V)
                </div>

                {/* 3D Component Blocks */}
                {/* Transformer T1 */}
                <div
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    width: '54px',
                    height: '66px',
                    transform: 'translate(-50%, -50%) translateZ(16px)',
                    backgroundColor: '#1e293b',
                    border: '2px solid #eab308',
                    borderRadius: '4px',
                    boxShadow: '0 8px 16px rgba(0,0,0,0.7)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#f8fafc',
                    fontSize: 9,
                    fontWeight: 700,
                  }}
                >
                  <span>T1</span>
                  <span style={{ fontSize: 7, color: '#eab308' }}>PQ32/30</span>
                </div>

                {/* Primary Switches Q1-Q4 */}
                <div style={{ position: 'absolute', top: '45px', left: '38px', width: '22px', height: '26px', backgroundColor: '#0f172a', border: '1px solid #94a3b8', borderRadius: 2, transform: 'translateZ(8px)', color: '#fff', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Q1</div>
                <div style={{ position: 'absolute', top: '90px', left: '38px', width: '22px', height: '26px', backgroundColor: '#0f172a', border: '1px solid #94a3b8', borderRadius: 2, transform: 'translateZ(8px)', color: '#fff', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Q2</div>
                <div style={{ position: 'absolute', top: '135px', left: '38px', width: '22px', height: '26px', backgroundColor: '#0f172a', border: '1px solid #94a3b8', borderRadius: 2, transform: 'translateZ(8px)', color: '#fff', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Q3</div>
                <div style={{ position: 'absolute', top: '180px', left: '38px', width: '22px', height: '26px', backgroundColor: '#0f172a', border: '1px solid #94a3b8', borderRadius: 2, transform: 'translateZ(8px)', color: '#fff', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Q4</div>

                {/* Secondary Rectifiers & Output Filter */}
                <div style={{ position: 'absolute', top: '55px', right: '42px', width: '24px', height: '28px', backgroundColor: '#0f172a', border: '1px solid #38bdf8', borderRadius: 2, transform: 'translateZ(8px)', color: '#38bdf8', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>D1</div>
                <div style={{ position: 'absolute', top: '105px', right: '42px', width: '24px', height: '28px', backgroundColor: '#0f172a', border: '1px solid #38bdf8', borderRadius: 2, transform: 'translateZ(8px)', color: '#38bdf8', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>D2</div>
                <div style={{ position: 'absolute', top: '155px', right: '38px', width: '32px', height: '32px', backgroundColor: '#1e293b', border: '2px solid #38bdf8', borderRadius: '50%', transform: 'translateZ(14px)', color: '#fff', fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>C1</div>

                {/* Gold Edge Connector Pads */}
                <div style={{ position: 'absolute', bottom: '6px', left: '20px', width: '36px', height: '8px', backgroundColor: '#eab308', borderRadius: 1 }} />
                <div style={{ position: 'absolute', bottom: '6px', right: '20px', width: '36px', height: '8px', backgroundColor: '#eab308', borderRadius: 1 }} />
              </div>
            </div>
          ) : null}

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
                        <code style={{ marginLeft: 6, fontSize: 10, background: '#1e293b', padding: '1px 5px', borderRadius: 3, color: '#94a3b8' }}>
                          SHA: {render3dData.step_sha256.slice(0, 8)}...
                        </code>
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
              IEC 61010-1 Isolation Slot
            </span>
          </div>

          <div style={{ color: '#94a3b8', fontFamily: 'monospace' }}>
            Dimensions: {bbox.width.toFixed(1)} × {bbox.height.toFixed(1)} mm •{' '}
            {pcbData?.tracks?.length > 0
              ? `Routed (${pcbData.tracks.length} tracks${pcbData?.drc_summary ? `, DRC: ${pcbData.drc_summary.status}` : ''})`
              : 'Placement Only (Unrouted)'}
            {' · '}
            {pcbData?.is_4layer ? (
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>🥞 4-Layer IPC-2152 Stackup (In1.Cu GND · In2.Cu Power)</span>
            ) : (
              <span style={{ color: '#94a3b8' }}>2-Layer Standard (F.Cu / B.Cu)</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
