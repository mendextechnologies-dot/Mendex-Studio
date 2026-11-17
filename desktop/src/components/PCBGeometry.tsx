import React from 'react';

export const layerColor = (layer: string) => layer === 'F.Cu' ? '#f59e0b' : layer === 'B.Cu' ? '#3b82f6' : layer === 'Edge.Cuts' ? '#facc15' : layer.endsWith('.SilkS') ? '#e2e8f0' : layer.endsWith('.Mask') ? '#a78bfa' : layer.endsWith('.Paste') ? '#cbd5e1' : layer === 'In1.Cu' ? '#a855f7' : '#06b6d4';
const matches = (patterns: string[], layer: string) => patterns.some(p => p === layer || p === '*.' + layer.split('.').pop() || (p === 'F&B.Cu' && ['F.Cu','B.Cu'].includes(layer)));
const pointString = (points: number[][]) => points.map(p => p.join(',')).join(' ');

/** Only stored native geometry; no decorative planes or component bodies. */
export function PCBGeometry({ data, states, copperOnly = false, colorOverride }: { data: any; states?: Record<string,{visible:boolean;opacity:number}>; copperOnly?:boolean; colorOverride?: (layer:string)=>string }) {
  const layers: string[] = [...new Set<string>([...(data.copper_layers || []), ...(data.tracks || []).map((t:any)=>t.layer), ...(data.zones || []).flatMap((z:any)=>z.filled_polygons.map((p:any)=>p.layer)), ...(copperOnly ? [] : ['F.Mask','B.Mask','F.Paste','B.Paste','F.SilkS','B.SilkS','Edge.Cuts'])])];
  return <>{layers.filter(layer => !states || states[layer]?.visible).map(layer => {
    const color = colorOverride?.(layer) || layerColor(layer);
    const isCopper = layer.endsWith('.Cu');
    return <g key={layer} data-pcb-layer={layer} opacity={states?.[layer]?.opacity ?? 1}>
      {isCopper && (data.zones || []).map((z:any,i:number) => {
        const polys = (z.filled_polygons || []).filter((p:any)=>p.layer===layer && p.points.length>2);
        return <path key={`zone-${i}`} d={polys.map((p:any)=>'M'+p.points.map((v:number[])=>v.join(',')).join(' L')+' Z').join(' ')} fill={color} fillOpacity={0.22} fillRule="evenodd"/>;
      })}
      {isCopper && (data.tracks || []).filter((t:any)=>t.layer===layer).map((t:any,i:number)=>t.points ? <polyline key={`track-${i}`} data-track-index={i} points={pointString(t.points)} fill="none" stroke={color} strokeWidth={t.width} strokeLinecap="round" strokeLinejoin="round"/> : <line key={`track-${i}`} data-track-index={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke={color} strokeWidth={t.width || .4} strokeLinecap="round"/>)}
      {isCopper && (data.vias || []).filter((v:any)=>matches(v.layers,layer) || (v.layers.includes('F.Cu') && v.layers.includes('B.Cu'))).map((v:any,i:number)=><g key={`via-${i}`}><circle cx={v.x} cy={v.y} r={v.size/2} fill={color}/><circle cx={v.x} cy={v.y} r={v.diameter/2} fill="#071a18"/></g>)}
      {(data.footprints || []).map((f:any,i:number)=><g key={`fp-${i}`}>
        {(f.pads || []).filter((p:any)=>p.type!=='np_thru_hole' && matches(p.layers || [],layer)).map((p:any,j:number)=><g key={`pad-${j}`} transform={`rotate(${-(p.rot || 0)} ${p.x} ${p.y})`}><rect x={p.x-p.sx/2} y={p.y-p.sy/2} width={p.sx} height={p.sy} rx={p.shape==='circle' ? Math.min(p.sx,p.sy)/2 : p.shape==='roundrect' ? .2 : 0} fill={color}/>{p.drill && <circle cx={p.x} cy={p.y} r={p.drill/2} fill="#071a18"/>}</g>)}
        {!copperOnly && <g transform={`translate(${f.x} ${f.y}) rotate(${-(f.rot || 0)})`}>
          {(f.silks || []).filter((g:any)=>g.layer===layer).map((g:any,j:number)=>g.type==='circle' ? <circle key={j} cx={g.cx} cy={g.cy} r={g.r} fill="none" stroke={color} strokeWidth={.15}/> : g.type==='rect' ? <rect key={j} x={g.x1} y={g.y1} width={g.x2-g.x1} height={g.y2-g.y1} fill="none" stroke={color} strokeWidth={.15}/> : <line key={j} x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} stroke={color} strokeWidth={.15}/>)}
          {layer===(f.layer==='B.Cu' ? 'B.SilkS':'F.SilkS') && <text x={0} y={-2} fontSize={1.4} fill={color}>{f.ref}</text>}
        </g>}
      </g>)}
      {!copperOnly && (layer==='Edge.Cuts' ? data.edge_cuts || [] : data.graphics || []).filter((g:any)=>g.layer===layer).map((g:any,i:number)=>g.points ? <polyline key={i} points={pointString(g.points)} fill="none" stroke={color} strokeWidth={.25}/> : g.type==='rect' ? <rect key={i} x={g.x1} y={g.y1} width={g.x2-g.x1} height={g.y2-g.y1} fill="none" stroke={color} strokeWidth={.25}/> : <line key={i} x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} stroke={color} strokeWidth={.25}/>)}
    </g>;
  })}</>;
}
