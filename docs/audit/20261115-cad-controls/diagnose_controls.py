"""Additional read/projection and fault-injection checks. No live CAD writes."""
import hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
H=Path(__file__).resolve().parent;R=H.parents[2];E=H/'evidence'
sys.path.insert(0,str(R/'src'))
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from copper_kicad.sexpr import loads
import integrations.adapters.copper_kicad_adapter as module

d=json.loads((E/'results.json').read_text());s=StudioService(H/'isolated');desktop=DesktopService(s)
rid=d['auto_route']['params']['revision_id'];rev=s.get_revision(rid);ws=s.workspace_path(rev);board=ws/'pcb/sv1000.kicad_pcb'
out={'utc':datetime.now(timezone.utc).isoformat()}
for rel in ['src/mendex_core/desktop/service.py','src/mendex_core/design/geometry.py','src/integrations/adapters/copper_kicad_adapter.py','desktop/src/components/CADPreviewCanvas.tsx','desktop/src/components/GerberLayerInspector.tsx','desktop/src/components/Header.tsx','desktop/src/api/client.ts']:
 p=R/rel;dest=E/'source-snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
 out.setdefault('source_sha256',{})[rel]=hashlib.sha256(p.read_bytes()).hexdigest()

for method,params in [('cad_preview',{'revision_id':rid,'kind':'pcb'}),('render_3d_pcb',{'revision_id':rid,'view':'iso','width':640,'height':480})]:
 try:
  v=desktop.dispatch(method,params)
  if method=='render_3d_pcb' and v.get('render_image'):
   import base64
   (E/'native-render.png').write_bytes(base64.b64decode(v['render_image'].split(',',1)[1]))
  out[method]={k:('<image omitted>' if k=='render_image' else v[k]) for k in v}
 except Exception as ex:out[method]={'error':str(ex),'error_type':type(ex).__name__}

adapter=module.CopperKiCadAdapter()
def injected(name,params):
 if name=='pcb_route_guided':return {'structuredContent':{'unrouted':0}}
 if name=='pcb_read':return {'structuredContent':{'tracks':145,'vias':24,'unrouted':0}}
 return {'isError':True,'content':[{'type':'text','text':'AUDIT INJECTED FAILURE: no native evidence'}]}
with patch.object(module.P,'resolve',return_value=object()),patch.object(module.rules,'set_netclasses',return_value={}),patch.object(module,'call_tool',side_effect=injected):
 out['fault_injection_route_failed_drc_and_pour']=adapter.route_pcb(board)
with patch.object(module,'call_tool',return_value={'isError':True,'content':[{'type':'text','text':'AUDIT INJECTED POUR FAILURE'}]}),patch.object(adapter,'run_drc',return_value={'error':'AUDIT INJECTED DRC FAILURE'}):
 out['fault_injection_planes_failed_pours']=adapter.setup_four_layer_power_planes(board)

exp=d.get('reexport_gerbers',{}).get('result',{})
rel=exp.get('zip_path')
out['explorer_export_path']={'returned_zip_path':rel,'exists_as_workspace_relative':(ws/rel).exists() if rel else None,'exists_as_data_root_relative':(s.root/rel).exists() if rel else None}

tree=loads(board.read_text(encoding='utf-8'));nodes=[n for n in tree[1:] if isinstance(n,list)]
def value(node,key):return next((n[1:] for n in node if isinstance(n,list) and n[0]==key),None)
segments=[n for n in nodes if n[0]=='segment'];fps=[n for n in nodes if n[0]=='footprint'];vias=[n for n in nodes if n[0]=='via']
out['canonical_counts']={'segments':len(segments),'vias':len(vias),'footprints':len(fps),'pads':sum(1 for f in fps for n in f[1:] if isinstance(n,list) and n[0]=='pad')}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="85 85 115 95"><rect x="85" y="85" width="115" height="95" fill="#071a18"/>']
for seg in segments:
 a=value(seg,'start');b=value(seg,'end');width=value(seg,'width');layer=value(seg,'layer')
 color='#e8aa30' if layer and layer[0]=='F.Cu' else '#3980ff'
 if a and b:svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{color}" stroke-width="{width[0] if width else .4}" stroke-linecap="round"/>')
for f in fps:
 at=value(f,'at');ref=next((n[2] for n in f if isinstance(n,list) and n[:2]==['property','Reference']),'?')
 if at:svg.append(f'<circle cx="{at[0]}" cy="{at[1]}" r=".6" fill="#21bc94"/><text x="{float(at[0])+1}" y="{at[1]}" fill="white" font-size="1.6">{ref}</text>')
svg.append('</svg>');(E/'actual-routed-tracks.svg').write_text(''.join(svg),encoding='utf-8')
(E/'diagnostics.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in {'cad_preview','render_3d_pcb'}},default=str))
