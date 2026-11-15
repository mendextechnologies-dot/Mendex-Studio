"""Read-only repository audit; execution probes write only to this evidence folder."""
import hashlib, json, os, shutil, sqlite3, subprocess, sys
from pathlib import Path
from collections import Counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['MENDEX_DATA_ROOT'] = str(OUT / 'isolated')
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def snapshot():
    return {str(p.relative_to(ROOT)).replace('\\','/'): sha(p)
            for folder in ['src','desktop/src','contracts','config','products','engineering_designs','workspaces','.mendex','reports']
            for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}

if sys.argv[-1] == 'after':
    before=json.loads((OUT/'snapshot-before.json').read_text())
    after=snapshot(); save('snapshot-after.json',after)
    save('preservation.json', {'changed':[p for p in before if p in after and before[p]!=after[p]],
         'removed':sorted(set(before)-set(after)), 'added':sorted(set(after)-set(before))})
    raise SystemExit

if not (OUT/'snapshot-before.json').exists(): save('snapshot-before.json', snapshot())
save('git-before.json', {k:subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True).stdout
    for k,args in {'commit':['rev-parse','HEAD'],'status':['status','--short']}.items()})
inventory=[]
for folder in ['products','engineering_designs','workspaces','reports','docs/audit/evidence/20261114-readiness']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.kicad_sch','.kicad_pcb','.kicad_pro','.asc','.net','.cir','.raw','.log','.gbr','.gtl','.gbl','.drl','.step','.stp','.csv','.pdf','.docx','.zip','.json','.md'}:
            inventory.append({'path':str(p.relative_to(ROOT)), 'size':p.stat().st_size, 'sha256':sha(p)})
save('artifact-inventory.json', inventory)
db=ROOT/'.mendex/studio.sqlite3'
with sqlite3.connect(db.as_uri()+'?mode=ro', uri=True) as c:
    tables=[r[0] for r in c.execute("select name from sqlite_master where type='table'")]
    save('database-readonly.json', {'user_version':c.execute('pragma user_version').fetchone()[0],
         'integrity':c.execute('pragma integrity_check').fetchall(),
         'tables':{t:c.execute('select count(*) from "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}})
from integrations.adapters.registry import ToolRegistry
registry=ToolRegistry()
save('tool-discovery.json',[d.model_dump(mode='json') for d in registry.list_descriptors()])
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
kc=KiCadLifecycleService()
native={}
if kc.kicad_cli:
    r=subprocess.run([str(kc.kicad_cli),'--version'],capture_output=True,text=True,timeout=30)
    native['kicad']={'command':[str(kc.kicad_cli),'--version'],'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
from mendex_core.design.ltspice_runner import LTspiceRunner
native['ltspice_discovery']=str(LTspiceRunner().ltspice_exe) if hasattr(LTspiceRunner(),'ltspice_exe') else str(LTspiceRunner().__dict__)
save('native-tools.json',native)
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
studio=StudioService(OUT/'isolated')
p=next((p for p in studio.list_products() if p.code=='AUDIT-ONLY'),None)
if p is None: p=studio.create_product('AUDIT-ONLY','Disposable framework audit','dc_dc_converter','Audit fixture')
rev=studio.get_revision(p.active_revision_id); ws=studio.workspace_path(rev); ws.mkdir(parents=True,exist_ok=True)
results={}
results['empty_wcca']=studio.run_wcca_analysis(rev.revision_id, num_iterations=20)
results['empty_thermal']=studio.calculate_pcb_thermal_field(rev.revision_id)
try: results['empty_laboratory_plan']=studio.generate_laboratory_test_plan(rev.revision_id)
except Exception as e: results['empty_laboratory_plan']={'error_type':type(e).__name__,'error':str(e)}
(ws/'simulation').mkdir(exist_ok=True)
for n in ['design.asc','design.net','design.raw','design.log','model.step','requirements.json']:
    (ws/'simulation'/n).write_text('AUDIT PLACEHOLDER - not engineering evidence',encoding='utf-8')
(ws/'only_report.html').write_text('<p>AUDIT PLACEHOLDER</p>',encoding='utf-8')
results['package_incomplete']=studio.generate_release_package(rev.revision_id, author='Audit fixture')
zip_path=ws/results['package_incomplete']['package_relative_path']
import zipfile
with zipfile.ZipFile(zip_path) as z: results['package_members']=z.namelist(); results['package_zip_crc']=z.testzip()
zip_path.write_bytes(b'CORRUPTED AUDIT ARCHIVE')
results['package_after_corruption']=studio.get_release_package(rev.revision_id)
(ws/'bom').mkdir(exist_ok=True)
(ws/'bom/bom.json').write_text(json.dumps([{'designator':'R1','description':'resistor','quantity':1,'mpn':'AUDIT-NONEXISTENT-PART'}]),encoding='utf-8')
results['pricing_unknown_part']=studio.generate_bom_pricing_schedule(rev.revision_id)
studio.create_revision(p.product_id,'AUDIT-NEXT-'+uuid4().hex[:8])
results['archived_revision_status']=studio.get_revision(rev.revision_id).lifecycle_status
try: results['archived_wcca']=studio.run_wcca_analysis(rev.revision_id,num_iterations=20)['success']
except Exception as e: results['archived_wcca']=str(e)
try: results['archived_package']=studio.generate_release_package(rev.revision_id)['status']
except Exception as e: results['archived_package']=str(e)
save('probe-results.json',results)
save('summary.json',{'inventory_count':len(inventory),'extensions':dict(Counter(Path(r['path']).suffix for r in inventory)),
     'disposable_revision':str(rev.revision_id),'note':'All synthetic inputs are audit-only; no physical measurement or product design.'})
print('Audit probe complete:',OUT)
