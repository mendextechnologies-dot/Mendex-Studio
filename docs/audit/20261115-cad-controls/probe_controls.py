"""CAD-control assessment. All mutating operations target isolated board copies."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import base64,hashlib,json,os,shutil,sqlite3,sys,time,zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
os.environ['MENDEX_DATA_ROOT']=str(HERE/'isolated')
from copper_kicad.sexpr import loads,dumps
from mendex_core.service import StudioService
from mendex_core.models import Specification
from mendex_core.desktop.service import DesktopService

SOURCE=ROOT/'products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb'
RESULT={};OUT=HERE/'evidence';OUT.mkdir(exist_ok=True)
def save(): (OUT/'results.json').write_text(json.dumps(RESULT,indent=2,default=str),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def structure(p):
    tree=loads(p.read_text(encoding='utf-8'))
    nodes=[n for n in tree[1:] if isinstance(n,list)]
    segments=[n for n in nodes if n[0]=='segment']
    return {'sha256':sha(p),'segments':len(segments),'vias':sum(n[0]=='via' for n in nodes),
        'zones':sum(n[0]=='zone' for n in nodes),'segment_layers':dict(Counter(next((x[1] for x in n[1:] if isinstance(x,list) and x[0]=='layer'),'unknown') for n in segments)),
        'sample_segment':segments[0] if segments else None}
def compact(value):
    if isinstance(value,dict):return {k:(f'<{len(v)} characters omitted>' if isinstance(v,str) and (len(v)>6000 or k in {'data_uri','render_image','svg_content'}) else compact(v)) for k,v in value.items()}
    if isinstance(value,list):return [compact(v) for v in value]
    return value
def call(label,method,params):
    print('START',label,flush=True);start=time.monotonic()
    try:
        data=desktop.dispatch(method,params)
        RESULT[label]={'method':method,'params':params,'seconds':round(time.monotonic()-start,3),'result':compact(data)}
        save(); print('END',label, 'success=',data.get('success',data.get('available')),flush=True)
        return data
    except Exception as ex:
        RESULT[label]={'method':method,'params':params,'error':str(ex),'error_type':type(ex).__name__,'seconds':round(time.monotonic()-start,3)}
        save();print('ERROR',label,str(ex),flush=True);return {}
def fixture(code):
    p=studio.create_product(code+'-'+__import__('uuid').uuid4().hex[:6],'Isolated copy for CAD control verification','dc_dc_converter','Audit fixture')
    rev=studio.get_revision(p.active_revision_id)
    studio.update_specification(rev.revision_id,Specification.model_validate(spec))
    rev=studio.get_revision(rev.revision_id);folder=studio.workspace_path(rev)/'pcb';folder.mkdir(parents=True,exist_ok=True)
    for src in SOURCE.iterdir():
        if src.suffix in {'.kicad_pcb','.kicad_pro','.kicad_sch'}:shutil.copyfile(src,folder/src.name)
    return str(rev.revision_id),folder/'sv1000.kicad_pcb'

RESULT['start_utc']=datetime.now(timezone.utc).isoformat()
RESULT['source_files_before']={str(p.relative_to(ROOT)):sha(p) for p in SOURCE.iterdir() if p.is_file()}
RESULT['source_structure']=structure(SOURCE/'sv1000.kicad_pcb')
RESULT['working_tree_before']=__import__('subprocess').run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True).stdout
save()
with sqlite3.connect((ROOT/'.mendex/studio.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    payload=json.loads(db.execute('select payload from revisions where id=?',('9b7c1396-64da-41f8-8649-77dc0f24e103',)).fetchone()[0]);spec=payload['specification']
studio=StudioService(HERE/'isolated');desktop=DesktopService(studio)
rid,board=fixture('CHECK-PREVIEW')
pcb=call('initial_2d_preview','cad_preview',{'revision_id':rid,'kind':'pcb'})
RESULT['initial_preview_summary']={'native':structure(board),'preview_tracks':len(pcb.get('tracks',[])),'preview_footprints':len(pcb.get('footprints',[])),'preview_pad_count':sum(len(f.get('pads',[])) for f in pcb.get('footprints',[]))};save()
call('schematic_preview','cad_preview',{'revision_id':rid,'kind':'schematic'})
call('gerber_inspector_without_export','inspect_gerber_layers',{'revision_id':rid,'auto_export':False})
call('thermal_heatmap_1oz','calculate_pcb_thermal_field',{'revision_id':rid,'copper_weight_oz':1.0})
call('thermal_heatmap_2oz','calculate_pcb_thermal_field',{'revision_id':rid,'copper_weight_oz':2.0})

# Main concern: execute actual auto-route RPC on a disposable copy, then compare
# native topology with the exact preview payload used by the UI.
rid,board=fixture('CHECK-ROUTE')
RESULT['route_before']=structure(board);save()
route=call('auto_route','auto_route_pcb',{'revision_id':rid,'pour_ground':True,'power_track':1.2,'default_track':0.4,'thermal_spoke':0.5,'thermal_gap':0.5,'pad_connection':'tht_thermal','stitch_ground':False,'stitch_pitch':5.0,'zone_clearance':0.5})
RESULT['route_after']=structure(board)
pcb=call('refresh_after_route','cad_preview',{'revision_id':rid,'kind':'pcb'})
RESULT['route_preview_tracks']=len(pcb.get('tracks',[]));save()
call('raytraced_3d_preview','cad_preview',{'revision_id':rid,'kind':'3d','view':'iso'})
call('rerender_3d','render_3d',{'revision_id':rid,'view':'iso','width':640,'height':480})
call('export_step','export_cad_step',{'revision_id':rid,'open_native':False})
exp=call('reexport_gerbers','export_gerbers',{'revision_id':rid,'auto_route':True,'check_drc':True})
call('gerber_inspector_after_export','inspect_gerber_layers',{'revision_id':rid,'auto_export':False})
for typ in ['gerber','turnkey']:
    data=call('download_'+typ,'download_gerbers',{'revision_id':rid,'package_type':typ})
    if data.get('data_uri'):
        binary=base64.b64decode(data['data_uri'].split(',',1)[1]);target=OUT/('download-'+typ+'.zip');target.write_bytes(binary)
        with zipfile.ZipFile(target) as z:info={'bytes':len(binary),'sha256_matches':sha(target)==data.get('sha256'),'crc_error':z.testzip(),'members':z.namelist()}
        RESULT['download_'+typ]['archive_validation']=info;save()

rid,board=fixture('CHECK-PLANES')
RESULT['planes_before']=structure(board)
call('four_layer_planes','setup_4layer_planes',{'revision_id':rid,'gnd_net':'PRI_GND','pwr_net':'VIN','zone_clearance':0.5,'thermal_spoke':0.5,'pad_connection':'tht_thermal'})
RESULT['planes_after']=structure(board);save()

rid,board=fixture('CHECK-SLOT')
RESULT['slot_before']=structure(board)
call('mill_slot','mill_isolation_slot',{'revision_id':rid,'slot_width':2.5})
RESULT['slot_after']=structure(board);save()

RESULT['source_files_after']={str(p.relative_to(ROOT)):sha(p) for p in SOURCE.iterdir() if p.is_file()}
RESULT['source_changes_during_check']=[k for k,v in RESULT['source_files_before'].items() if RESULT['source_files_after'].get(k)!=v]
RESULT['finish_utc']=datetime.now(timezone.utc).isoformat();save()
print('COMPLETE',flush=True)
