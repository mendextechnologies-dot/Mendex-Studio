"""Audit-only disposable low-voltage fixture. Does not modify application source."""
from pathlib import Path
import json,hashlib,subprocess,time,traceback,shutil,sys
from uuid import uuid4
from mendex_core.controller import MendexEngineeringController
from mendex_core.evidence import specification_hash
from mendex_core.mcp.server import MendexMCPServer
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

out=Path(__file__).resolve().parent
root=out/'disposable-project'; root.mkdir(exist_ok=False)
events=[]
def save():
 (out/'e2e-transcript.json').write_text(json.dumps(events,indent=2,default=str)+'\n',encoding='utf-8')
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
server=MendexMCPServer(root);ctrl=server.controller;studio=ctrl.service
inventory=step('MCP tool discovery',lambda:server.handle_request({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}}))
(out/'tool-names.json').write_text(json.dumps([t['name'] for t in inventory['result']['tools']],indent=2),encoding='utf-8')
project=step('Disposable project and default lifecycle',lambda:ctrl.create_project('Readiness audit buck fixture',code='AUDIT-BUCK',owner='Software evaluation fixture',auto_enroll=True))
pid=project['project_id'];rid=str(studio.get_product(pid).active_revision_id)
step('Explicit fixture specification',lambda:ctrl.save_project_specification(pid,{'vin_min_v':12,'vin_nom_v':12,'vin_max_v':12,'vout_v':5,'iout_a':1,'switching_frequency_hz':100000,'topology':'buck','source':'Disposable software audit; not a commercial product','assumptions':['Idealized 12 V to 5 V / 1 A, 100 kHz, 0.1 V peak-to-peak limit; 2 ms transient requested; simulation is not physical validation.']}))
def life(action,stage,key):
 return studio.engineering_lifecycle.apply({'revision_id':rid,'stage_id':stage,'action':action,'source':'Audit fixture','reason':'Software evaluation only','idempotency_key':key})
step('Initialization start',lambda:life('start','project_initialization','init-start'))
step('Initialization completion',lambda:life('complete','project_initialization','init-complete'))
step('Requirements start',lambda:life('start','requirements','req-start'))
context={'revision_id':rid,'stage_id':'requirements','expected_input_hash':specification_hash(studio.get_revision(rid).specification),'source':'Explicit audit assumptions','reason':'Traceability fixture, no approval','idempotency_key':'requirements'}
step('Persist measurable requirements',lambda:studio.engineering_records.save_requirements({**context,'requirements':[{'id':'audit_vout','discipline':'electrical','description':'Nominal output 5 V','source':'Software audit fixture','specification_field':'vout_v','target_value':5,'unit':'V','acceptance_criterion':'Steady-state mean 4.75 to 5.25 V in this illustrative fixture'},{'id':'audit_ripple','discipline':'performance','description':'Peak-to-peak ripple limit','source':'Software audit fixture','target_value':.1,'unit':'V','acceptance_criterion':'Steady-state peak-to-peak <=0.1 V; settling and measurement window must be justified'}]}))
step('Attempt stage handoff without review',lambda:life('start','calculations','calc-start'))
request={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'generate_design','arguments':{'workspace_id':pid,'product_id':pid,'title':'Audit ideal buck','vin_min':12,'vin_nom':12,'vin_max':12,'vout':5,'iout':1,'fsw_hz':100000,'ripple_v':.1,'generate_artifacts':True}}}
reply=step('MCP design generation',lambda:server.handle_request(request))
if reply['result'].get('isError'):raise RuntimeError('Design MCP invocation failed; see transcript')
design=json.loads(reply['result']['content'][0]['text']);did=design['design_id']
model=studio.design.get_design(did);ir=model.get_active_revision().ir
step('Topology and sizing inspection',lambda:{'topology':ir.topology,'candidate_metrics':[{'topology':c.topology,'metrics':c.calculated_metrics} for c in model.candidates],'components':[c.model_dump(mode='json') for c in ir.components]})
step('Representative sourced part lookup',lambda:studio.components.get_component('BSC026N08NS5'))
ws=studio.workspace_path(studio.get_revision(rid));artifacts=design['generated_artifacts']
paths={Path(a['path']).suffix:root/a['path'] for a in artifacts}
sch,pcb=paths.get('.kicad_sch'),paths.get('.kicad_pcb')
step('Native converter execution and extraction',lambda:studio.design.run_ltspice_simulation(did,ws))
# The actual design service result is saved; no new simulator implementation is substituted.
exe=Path(r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
command('kicad-version',[exe,'--version'])
if sch:
 command('schematic-erc',[exe,'sch','erc','--format','json','--output',out/'erc.json',sch])
 command('schematic-svg',[exe,'sch','export','svg','--output',out/'schematic-svg',sch])
if pcb:
 command('pcb-drc-before',[exe,'pcb','drc','--format','json','--output',out/'drc-before.json',pcb])
 adapter=CopperKiCadAdapter()
 step('Copper availability',lambda:{'available':adapter.is_available()})
 step('Copper routing actual board',lambda:adapter.route_pcb(pcb,pour_ground=True))
 command('pcb-drc-after',[exe,'pcb','drc','--format','json','--output',out/'drc-after.json',pcb])
 step('Copper native PCB 3D render',lambda:str(adapter.render_3d(pcb,output_png=out/'board-3d.png',width=480,height=320,quality='basic')))
 command('pcb-step',[exe,'pcb','export','step','--output',out/'board.step',pcb])
 command('gerbers',[exe,'pcb','export','gerbers','--output',out/'gerbers',pcb])
 command('drill',[exe,'pcb','export','drill','--output',out/'drill',pcb])
 command('pick-place',[exe,'pcb','export','pos','--format','csv','--output',out/'positions.csv',pcb])
# Explicit source-only BOM: references derived from IR, no manufactured MPN qualification.
rows=[{'designator':c.designator,'quantity':1,'description':str(c.component_type)+' '+str(c.value),'manufacturer':c.manufacturer or '', 'mpn':c.mpn or '', 'source':'Generated fixture IR; exact physical selection unqualified'} for c in ir.components]
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
