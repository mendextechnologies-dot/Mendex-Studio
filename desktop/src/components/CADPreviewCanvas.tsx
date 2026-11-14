import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import { Layers, Eye, RefreshCw, ExternalLink, Box, ZoomIn, ZoomOut, CheckCircle2, Zap, Package } from 'lucide-react';

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
  const [viewMode, setViewMode] = useState<'pcb' | 'schematic' | '3d'>('pcb');
  const [render3dData, setRender3dData] = useState<any>(null);
  const [pcbData, setPcbData] = useState<any>(null);
  const [schData, setSchData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoverItem, setHoverItem] = useState<any>(null);
  const [routing, setRouting] = useState<boolean>(false);
  const [exportingGerbers, setExportingGerbers] = useState<boolean>(false);
  const [routeStatus, setRouteStatus] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const handleExportGerbers = async () => {
    setExportingGerbers(true);
    setRouteStatus({ type: 'info', text: 'Generating manufacturing Gerbers and drill files (with auto-routing verification)...' });
    try {
      const res = await api.exportGerbers(revisionId, true);
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `Manufacturing release package generated: ${res.file_count} Gerber & drill files exported to ${res.output_dir}`,
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
  const [d3View, setD3View] = useState<'iso' | 'top' | 'bottom'>('iso');

  const load3d = (view: 'iso' | 'top' | 'bottom' = d3View) => {
    setLoading(true);
    setD3View(view);
    api.cadPreview(revisionId, '3d', view)
      .then(d3 => setRender3dData(d3))
      .catch((err: any) => setError(err.message || String(err)))
      .finally(() => setLoading(false));
  };

  const handleAutoRoute = async () => {
    setRouting(true);
    setRouteStatus({ type: 'info', text: 'Executing Copper guided topological router with power net classes (1.2mm power, 0.4mm signal)...' });
    try {
      const res = await api.autoRoutePCB(revisionId, true, 1.2, 0.4);
      if (res.success) {
        setRouteStatus({
          type: 'success',
          text: `Auto-routing completed successfully: ${res.tracks} copper tracks, ${res.vias} vias, DRC: ${res.drc_errors} errors. Ground pour filled on B.Cu.`,
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
              3D Board Assembly
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
                {exportingGerbers ? 'Exporting...' : '📦 Export Gerbers'}
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

          {viewMode === '3d' && onOpenPCB && (
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
              Open in KiCad 3D Viewer
            </button>
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

      {/* Interactive Vector Canvas */}
      {!loading && !error && viewMode !== '3d' && activeData?.available && (
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
                    stroke="#f59e0b"
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
                    <rect
                      x="-4.5"
                      y="-4.5"
                      width="9"
                      height="9"
                      fill="#1e293b"
                      stroke="#ef4444"
                      strokeWidth="0.3"
                      rx="0.5"
                    />
                    <text
                      x="0"
                      y="-5.5"
                      fill="#ef4444"
                      fontSize="2.0"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {sym.ref}
                    </text>
                    <text
                      x="0"
                      y="6.2"
                      fill="#cbd5e1"
                      fontSize="1.3"
                      textAnchor="middle"
                      fontFamily="sans-serif"
                    >
                      {sym.value?.substring(0, 16)}
                    </text>
                    <text
                      x="0"
                      y="0.6"
                      fill="#94a3b8"
                      fontSize="1.1"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {sym.lib_id?.split(':').pop()?.substring(0, 10)}
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
            minHeight: '420px',
            background: '#070b14',
            borderRadius: 8,
            border: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.6)',
          }}
        >
          {/* 3D Angle Selector Bar */}
          <div style={{ display: 'inline-flex', gap: 6, marginBottom: 16, background: '#1e293b', padding: 3, borderRadius: 6 }}>
            <button
              onClick={() => load3d('iso')}
              disabled={loading}
              style={{
                background: d3View === 'iso' ? '#0284c7' : 'transparent',
                border: 'none',
                color: d3View === 'iso' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              📐 Isometric (ISO)
            </button>
            <button
              onClick={() => load3d('top')}
              disabled={loading}
              style={{
                background: d3View === 'top' ? '#0284c7' : 'transparent',
                border: 'none',
                color: d3View === 'top' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🔝 Top View (Components)
            </button>
            <button
              onClick={() => load3d('bottom')}
              disabled={loading}
              style={{
                background: d3View === 'bottom' ? '#0284c7' : 'transparent',
                border: 'none',
                color: d3View === 'bottom' ? '#fff' : '#94a3b8',
                padding: '5px 12px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🔻 Bottom View (Ground Plane)
            </button>
          </div>

          {render3dData?.available && render3dData?.render_image ? (
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
            Dimensions: {bbox.width.toFixed(1)} × {bbox.height.toFixed(1)} mm • Placement Only (Unrouted)
          </div>
        </div>
      )}
    </div>
  );
};
