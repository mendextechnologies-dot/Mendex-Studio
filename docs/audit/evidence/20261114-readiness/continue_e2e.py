"""Audit-only disposable low-voltage fixture. Does not modify application source."""
from pathlib import Path
import json,hashlib,subprocess,time,traceback,shutil,sys
from uuid import uuid4
from mendex_core.controller import MendexEngineeringController
from mendex_core.evidence import specification_hash
from mendex_core.mcp.server import MendexMCPServer
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

out=Path(__file__).resolve().parent
root=out/'disposable-project'; root.mkdir(exist_ok=True)
events=[]
def save():
 (out/'e2e-continuation-transcript.json').write_text(json.dumps(events,indent=2,default=str)+'\n',encoding='utf-8')
def step(name,fn):
 start=time.monotonic()
 try:
  result=fn()
  if hasattr(result,'model_dump'):result=result.model_dump(mode='json')
  events.append({'step':name,'status':'EXECUTED','elapsed_s':round(time.monotonic()-start,3),'result':result})
 except Exception as e:
  result=None; events.append({'step':name,'status':'FAILED_OR_BLOCKED','error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc()})
 save();print(name,events[-1]['status'],flush=True);return result

def command(name,args,timeout=60):
 def invoke():
  p=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  (out/(name+'.stdout.txt')).write_text(p.stdout,encoding='utf-8');(out/(name+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
  return {'argv':[str(x) for x in args],'exit_code':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-2000:]}
 return step(name,invoke)
server=MendexMCPServer(root); ctrl=server.controller; studio=ctrl.service
product=studio.list_products()[0];pid=str(product.product_id);rid=str(product.active_revision_id)
model=studio.design.list_designs()[0];ir=model.get_active_revision().ir
ws=studio.workspace_path(studio.get_revision(rid));artifacts=[a.model_dump(mode='json') for a in model.get_active_revision().artifacts]
context={'revision_id':rid,'stage_id':'requirements','expected_input_hash':specification_hash(studio.get_revision(rid).specification),'source':'Explicit audit assumptions','reason':'Traceability fixture, no approval','idempotency_key':'continuation'}
rows=[{'designator':c.designator,'quantity':1,'description':str(c.type)+' '+str(c.value),'manufacturer':c.manufacturer or '', 'mpn':c.mpn or '', 'source':'Generated fixture IR; exact physical selection unqualified'} for c in ir.components]
(ws/'bom').mkdir(exist_ok=True);(ws/'bom/bom.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
from mendex_core.bom_generator import generate_bom_deliverables
step('Draft BOM export from supplied fixture IR',lambda:generate_bom_deliverables(studio,rid))
# Register actual native outputs as explicitly unapproved audit artifacts in the open stage.
for index,a in enumerate(artifacts):
 dest=ws/'requirements'/('audit-'+str(index)+Path(a['path']).suffix)
 shutil.copy2(root/a['path'],dest)
 step('Register artifact '+str(index),lambda dest=dest,index=index:studio.engineering_records.register_artifact({**context,'idempotency_key':'artifact-'+str(index),'relative_path':dest.relative_to(ws).as_posix(),'expected_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'classification':'other'}))
step('Draft engineering report',lambda:studio.engineering_records.generate_report({**context,'idempotency_key':'report'}))
plan=ws/'requirements/audit-prototype-test-plan.md'
plan.write_text('# Manual audit fixture test plan ? NOT EXECUTED\nUse a qualified engineer, current-limited isolated bench supply and appropriately rated instruments. Record instrument ID/calibration, operator, revision, load, output, ripple bandwidth, temperatures, faults and evidence hashes. Fixture targets: 4.75?5.25 V mean and <=0.1 V pk-pk after demonstrated settling. No prototype was built; no hardware test or procurement is authorized by this fixture.\n',encoding='utf-8')
step('Manual prototype plan saved',lambda:{'path':str(plan),'classification':'audit-authored, not automatically generated','physical_status':'NOT_EVALUATED'})
command('cli-projects',[sys.executable,'-m','mendex_core.cli','--root',root,'projects'])
step('Final lifecycle read',lambda:studio.engineering_lifecycle.get(rid))
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.suffix not in ('.sqlite3','-wal','-shm')}
(out/'fixture-file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
