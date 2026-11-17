"""Verify real copper creation from a deliberately unrouted disposable copy."""
from pathlib import Path
import hashlib,json,shutil,sys,time
H=Path(__file__).resolve().parent;R=H.parents[2];E=H/'evidence';sys.path.insert(0,str(R/'src'))
from copper_kicad.sexpr import loads,dumps
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
s=StudioService(H/'isolated');p=s.create_product('ROUTE-ZERO','Unrouted disposable board copy','dc_dc_converter','Audit fixture');rev=s.get_revision(p.active_revision_id)
folder=s.workspace_path(rev)/'pcb';folder.mkdir(exist_ok=True)
source=R/'products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb'
for f in source.iterdir():
 if f.suffix in {'.kicad_sch','.kicad_pro','.kicad_pcb'}:shutil.copyfile(f,folder/f.name)
board=folder/'sv1000.kicad_pcb';tree=loads(board.read_text(encoding='utf-8'));tree=[tree[0]]+[n for n in tree[1:] if not (isinstance(n,list) and n[0] in {'segment','arc','via'})];board.write_text(dumps(tree)+'\n',encoding='utf-8')
def counts():
 t=loads(board.read_text(encoding='utf-8'));return {key:sum(isinstance(n,list) and n[0]==key for n in t[1:]) for key in ['segment','via','zone','footprint']}
out={'revision_id':str(rev.revision_id),'before':counts(),'note':'Only isolated copy deliberately stripped of tracks/vias. Not a live design change.'}
print('START routing from zero',flush=True);start=time.monotonic()
out['route_result']=DesktopService(s).dispatch('auto_route_pcb',{'revision_id':str(rev.revision_id),'pour_ground':True})
out['seconds']=round(time.monotonic()-start,3);out['after']=counts();out['board_sha256']=hashlib.sha256(board.read_bytes()).hexdigest()
try:out['native_drc']=KiCadLifecycleService().run_drc(board,output_json=E/'route-from-zero-drc.json')
except Exception as ex:out['native_drc_error']=str(ex)
(E/'route-from-zero.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8');print(json.dumps(out,default=str),flush=True)
