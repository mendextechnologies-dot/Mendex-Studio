"""Scoped UI control edits; keeps existing unrelated panel changes."""
from pathlib import Path
p=Path('desktop/src/components/CADPreviewCanvas.tsx');s=p.read_text(encoding='utf-8')
s=s.replace('useMemo }','useMemo, useRef }')
s="import { PCBGeometry } from './PCBGeometry';\nimport { downloadCandidate } from '../downloadCandidate';\n"+s
s=s.replace('  const [viewMode,','  const requestGeneration = useRef(0);\n  const activeRevision = useRef(revisionId); activeRevision.current = revisionId;\n  const sourceIdentity = useRef<string | null>(null);\n  const [previewEpoch, setPreviewEpoch] = useState(0);\n  const busy = useRef(false);\n  const [viewMode,',1)
s=s.replace('copperWeightOz: 2.0,',"copperWeightOz: copperWeight === '2oz' ? 2.0 : 1.0,")
s=s.replace('chassisCooling: true,','chassisCooling,')
s=s.replace("console.warn('Could not recalculate thermal field with chassis cooling:', err);","setRouteStatus({type:'error',text:String(err)});")
s=s.replace("console.warn('Could not load PCB thermal field:', err);","setRouteStatus({type:'error',text:String(err)});")
# Always fetch a fresh validated bundle rather than caching base64 from an older export.
a=s.index('      let dataUri =');b=s.index('      setRouteStatus({',s.index('      // Trigger standard browser download',a))
s=s[:a]+'''      const res = await api.downloadGerbers(revisionId);
      if (!res.success) throw new Error(res.error || 'No current package. Re-export Gerbers.');
      await downloadCandidate(res);
      const filename=res.filename;
'''+s[b:]
s=s.replace('Downloaded ${filename} successfully. Cryptographic release verified with SHA-256.','Save requested for ${filename}; payload SHA-256 matches. Browser save completion is not observed.')
s=s.replace('Manufacturing release package generated:', 'Candidate fabrication files generated:')
s=s.replace('IPC-2152 4-Layer stackup active:', '4-Layer configuration:')
s=s.replace("text: 'Configuring IPC-2152 4-layer internal planes (In1.Cu GND shield + In2.Cu VIN power plane)...',","text: 'Configuring native four-layer copper planes...',")
s=s.replace('${res.drc?.errors ?? 0} errors.',"${res.drc?.errors ?? 'unavailable'} errors, ${res.drc?.warnings ?? 'unavailable'} warnings. No standards qualification implied.")
s=s.replace('Milling physical 2.5mm Edge.Cuts isolation air slot','Adding 2.5mm Edge.Cuts slot geometry')
s=s.replace('Isolation slot milled on Edge.Cuts','Slot geometry added on Edge.Cuts')
s=s.replace('${res.drc.errors} errors.',"${res.drc?.errors ?? 'unavailable'} errors, ${res.drc?.warnings ?? 'unavailable'} warnings.")
s=s.replace('Ground pour filled on B.Cu (spoke=${thermalSpoke}mm).',"Unconnected: ${res.unrouted_after ?? 'unavailable'}, warnings: ${res.drc_warnings ?? 'unavailable'}. Ground fill: ${res.pour_completed ? 'completed' : 'not completed'}. ")
s=s.replace("text: `Routing notice: ${res.messages?.join(', ') || res.error || 'Routing did not complete.'}`","text: `Routing incomplete or unverified: ${res.unrouted_after ?? 'unknown'} unconnected; DRC: ${res.drc_errors ?? 'unavailable'} errors. ${res.messages?.join(', ') || res.error || ''}`")
a=s.index('  const loadData = () =>');b=s.index('  const activeData =',a)
s=s[:a]+'''  busy.current = routing || exportingGerbers || millingSlot || configuringPlanes;
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

'''+s[b:]
# React onClick supplies an event, not the silent flag.
s=s.replace('onClick={loadData}','onClick={() => loadData()}')
s=s.replace('<GerberLayerInspector revisionId={revisionId} />','<GerberLayerInspector key={`${revisionId}:${pcbData?.source_hash}:${previewEpoch}`} revisionId={revisionId} />')
# Supplied sample had invented orbit bodies. Render actual PCB geometry in projection.
a=s.index("          {sub3dMode === 'orbit' ? (");b=s.index("          {sub3dMode === 'raytrace' && (",a)
s=s[:a]+'''          {sub3dMode === 'orbit' && pcbData?.available && (
            <div style={{width:'100%',height:380,perspective:1000,display:'grid',placeItems:'center'}} onWheel={e=>setOrbitZoom(z=>Math.max(.4,Math.min(3,z+(e.deltaY<0?.1:-.1))))} onMouseDown={e=>{setIsOrbitDragging(true);setOrbitDragStart({x:e.clientX,y:e.clientY});}} onMouseUp={()=>setIsOrbitDragging(false)} onMouseLeave={()=>setIsOrbitDragging(false)} onMouseMove={e=>{if(isOrbitDragging){setOrbitRotZ(z=>z+(e.clientX-orbitDragStart.x)*.3);setOrbitRotX(x=>Math.max(0,Math.min(85,x+(e.clientY-orbitDragStart.y)*.3)));setOrbitDragStart({x:e.clientX,y:e.clientY});}}}>
              <svg width="75%" height="80%" viewBox={`${pcbData.bbox.min_x-4} ${pcbData.bbox.min_y-4} ${pcbData.bbox.width+8} ${pcbData.bbox.height+8}`} style={{background:'#071a18',transform:`rotateX(${orbitRotX}deg) rotateZ(${orbitRotZ}deg) scale(${orbitZoom})`}}><PCBGeometry data={pcbData}/></svg>
              <small>Projection of actual PCB geometry; use STEP for solid mechanical models.</small>
            </div>
          )}

'''+s[b:]
# Replace straight-line-only track rendering with common actual copper/via/fill geometry.
a=s.index('                {/* 2. Copper Tracks */}');b=s.index('                {/* 3. Placed Footprints */}',a)
s=s[:a]+'''                <PCBGeometry data={pcbData} copperOnly />

'''+s[b:]
# Arc/poly outlines also need their real geometry rather than undefined line coordinates.
s=s.replace("                  if (e.type === 'rect') {", "                  if (e.points) return <polyline key={`ec-${i}`} points={e.points.map((p:number[])=>p.join(',')).join(' ')} fill=\"none\" stroke=\"#facc15\" strokeWidth={.6}/>;\n                  if (e.type === 'rect') {",1)
s=s.replace("status === 'PASS'", "status === 'CLEAR'")
s=s.replace('{activeData.drc_summary.errors} errors, {activeData.drc_summary.warnings} warnings',"{activeData.drc_summary.errors ?? 'unknown'} errors, {activeData.drc_summary.warnings ?? 'unknown'} warnings, {activeData.drc_summary.unconnected ?? 'unknown'} unconnected")
s=s.replace('title="Configures IPC-2152 compliant 4-layer internal copper plane zones (In1.Cu GND shield + In2.Cu VIN plane)"','title="Configure native internal copper planes; this does not qualify a standard or safety requirement"')
s=s.replace('IEC 61010-1 Isolation Slot','Edge.Cuts Slot')
s=s.replace('4-Layer IPC-2152 Stackup (In1.Cu GND · In2.Cu Power)','4-Layer Copper Stackup')
s=s.replace("? `Routed (${pcbData.tracks.length} tracks${pcbData?.drc_summary ? `, DRC: ${pcbData.drc_summary.status}` : ''})`", "? `Copper: ${pcbData.tracks.length} displayed / ${pcbData.native_track_count} native tracks, ${pcbData.vias?.length || 0} vias; connectivity: ${pcbData.connectivity_status}`")
s=s.replace("'Placement Only (Unrouted)'", "'No copper tracks found; connectivity NOT_EVALUATED'")
s=s.replace("<span style={{ color: '#94a3b8' }}>2-Layer Standard (F.Cu / B.Cu)</span>","<span style={{ color: '#94a3b8' }}>{pcbData.layer_count} enabled copper layers</span>")
# Clear local panel state on revision change via parent key as well as effect.
p.write_text(s,encoding='utf-8')
p=Path('desktop/src/components/RevisionEngineeringPanel.tsx');s=p.read_text(encoding='utf-8');s=s.replace('<CADPreviewCanvas\n','<CADPreviewCanvas\n              key={data.revision.revision_id}\n');p.write_text(s,encoding='utf-8')

p=Path('desktop/src/components/GerberLayerInspector.tsx');s=p.read_text(encoding='utf-8');s="import { PCBGeometry } from './PCBGeometry';\nimport { downloadCandidate } from '../downloadCandidate';\n"+s
# Keep measurement distance, remove unqualified standard rules/verdicts entirely.
a=s.index('export interface ClearanceRule');b=s.index('interface GerberLayerInspectorProps',a)
s=s[:a]+'''export function evaluateClearance(distanceMm: number, voltage = 0, insulationType: 'basic'|'reinforced' = 'basic') {
  return {actualDistanceMm:distanceMm,actualDistanceMils:distanceMm*39.3701,voltage,insulationType,
    requiredIecMm:0,requiredIpcMm:0,marginMm:0,isIecCompliant:false,isIpcCompliant:false,
    verdict:'NOT_EVALUATED',notes:'Geometric measurement only. No qualified standards rule or safety acceptance supplied.'};
}

'''+s[b:]
a=s.index('        // Set voltage preset matching design');b=s.index('      } else {',a);s=s[:a]+s[b:]
for filename in ["res.filename || 'gerbers.zip'","res.filename || 'turnkey_manufacturing.zip'"]:
 a=s.index("        const link = document.createElement('a');");b=s.index('        setActionMessage(',a)
 s=s[:a]+"        await downloadCandidate(res);\n"+s[b:]
s=s.replace('Downloaded ${res.filename}', 'Save requested for ${res.filename}').replace('Downloaded turnkey manufacturing package','Save requested for assembly candidate')
s=s.replace('opacity ||','opacity ??')
# Render every actual enabled layer through one geometry renderer.
a=s.index('              {/* Edge.Cuts Outline */}');b=s.index('              {/*',s.index('              {/* Silkscreen Layer (F.SilkS) */}',a)+30)
# Use the next drill overlay as end marker, preserving drill schedules and measurements.
b=s.index('              {/*',s.index('              {/* Silkscreen Layer (F.SilkS) */}',a)+len('              {/* Silkscreen Layer (F.SilkS) */}'))
s=s[:a]+'''              <PCBGeometry data={data} states={mode==='stack' ? layerStates : Object.fromEntries(Object.keys(layerStates).map(k=>[k,{visible:[diffLayerA,diffLayerB,'Edge.Cuts'].includes(k),opacity:.9}]))} colorOverride={mode==='differential' ? layer => layer===diffLayerA ? '#10b981' : layer===diffLayerB ? '#ec4899' : '#facc15' : undefined}/>

'''+s[b:]
# Replace the measurement acceptance badge and explanatory standard thresholds.
a=s.index('              {/* Center: Live Measurement & Compliance Scorecard */}');b=s.index('              {/*',a+20)
s=s[:a]+'''              {currentMeasurement && <div style={{color:'#e2e8f0',padding:8}}>Distance {currentMeasurement.actualDistanceMm.toFixed(3)} mm · Safety NOT_EVALUATED</div>}

'''+s[b:]
s=s.replace('Gerber Layer Inspector','Native PCB Layer Inspector').replace('RS-274X Gerber','Native PCB layer geometry; exported RS-274X file inventory')
s=s.replace('Turnkey Manufacturing','Assembly Candidate').replace('Download Turnkey','Download Assembly Candidate')
p.write_text(s,encoding='utf-8')
