"""Independent audit probes. Only mutate newly created audit data, never production data."""
from pathlib import Path
import hashlib, json, os, sqlite3, subprocess, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
E = Path(__file__).parent / 'evidence'
E.mkdir(exist_ok=True)
ROOT = E / 'audit-data'
ROOT.mkdir(exist_ok=True)
os.environ['PYTHONPATH'] = str(REPO / 'src')
sys.path.insert(0, str(REPO / 'src'))
out = {}
def save():
    (E/'probes.json').write_text(json.dumps(out, indent=2, default=str), encoding='utf-8')
def probe(name, fn):
    start = time.monotonic()
    try: out[name] = {'returned': fn()}
    except Exception as exc: out[name] = {'exception': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    out[name]['duration_s'] = round(time.monotonic()-start, 3)
    save()
    print(name, flush=True)
def cli(*args):
    cmd = [sys.executable, '-m','mendex_core.cli','--root',str(ROOT), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
    return {'command':cmd, 'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def run(cmd, timeout=40):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    return {'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def inventory():
    files={}
    for dirname in ['products','workspaces','engineering_designs','reports']:
        for p in (REPO/dirname).rglob('*'):
            if p.is_file(): files[str(p.relative_to(REPO))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in (REPO/'.mendex').glob('*'):
        if p.is_file(): files[str(p.relative_to(REPO))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return files
probe('existing_data_before',inventory)
probe('git_before',lambda:run(['git','status','--short']))
probe('runtime',lambda:run([sys.executable,'-m','pip','list','--format=json']))
from mendex_core.controller import MendexEngineeringController
from mendex_core.models import Category, Specification, Lifecycle
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.service import StudioService
c=MendexEngineeringController(ROOT)
probe('cli_help',lambda:cli('--help'))
probe('cli_create_workspace',lambda:cli('workspace','create','Independent CLI reference'))
ws=json.loads(out['cli_create_workspace']['returned']['stdout'])['workspace_id']
probe('core_create_workspace',lambda:c.create_workspace('Independent MCP reference'))
ws2=out['core_create_workspace']['returned']['workspace_id']
spec={'vin_min_v':18,'vin_nom_v':24,'vin_max_v':32,'vout_v':5,'iout_a':4,'switching_frequency_hz':100000,'source':'Generic independent software audit reference; unapproved'}
product=c.service.create_product('AUDIT-REF','Generic independent reference',Category.DC_DC,'Independent audit')
rev=str(product.active_revision_id)
out['context']={'root':str(ROOT),'workspace_cli':ws,'workspace_mcp':ws2,'product_id':str(product.product_id),'revision_id':rev}
save()
for name,args in {
 'workspace_list':['workspace','list'], 'workspace_status':['workspace','status',ws],
 'workspace_invalid':['workspace','status','invalid-id'], 'workspace_empty':['workspace','create',' '],
 'spec_valid':['specification','validate',json.dumps(spec)], 'spec_invalid':['specification','validate','{"vout_v":-5}'],
 'spec_order_invalid':['specification','validate','{"vin_min_v":30,"vin_nom_v":10}'],
 'spec_save':['specification','save',rev,json.dumps(spec)], 'spec_save_invalid':['specification','save','invalid-id','{}'],
 'design_generate':['design','generate','--workspace',ws,'--title','Independent buck reference','--vin-nom','24','--vout','5','--iout','4','--product-id',str(product.product_id)],
 'design_invalid':['design','show','invalid-id'],
 'calculate_dowell':['calculate','dowell'], 'calculate_losses':['calculate','losses'],
 'calculate_steinmetz':['calculate','steinmetz'], 'calculate_flyback':['calculate','flyback'],
 'calculate_invalid':['calculate','dowell','--freq','-1'],
 'artifact_list':['artifact','list','--workspace',ws], 'artifact_invalid':['artifact','open','--workspace',ws,'--file','missing.asc'],
 'tool_list':['tool','list'], 'tool_check':['tool','check','ltspice'], 'tool_invalid':['tool','check','invalid-tool'],
 'tool_open_invalid':['tool','open','ltspice','missing.asc'],
 'simulation_list':['simulation','list','--workspace',ws], 'simulation_ltspice':['simulation','run','--workspace',ws],
 'simulation_missing':['simulation','run','--workspace','invalid-id'],
 'simulation_unsupported':['simulation','run','--workspace',ws,'--tool','arbitrary-shell'],
 'validation':['validation','--revision',rev], 'validation_invalid':['validation','--revision','bad-id'],
 'report':['report','--revision',rev], 'report_invalid':['report','--revision','bad-id'],
 'products':['products'],'plugins':['plugins'],'rules':['rules'], 'doctor':['doctor'],
}.items(): probe('cli_'+name,lambda args=args:cli(*args))
design_id=json.loads(out['cli_design_generate']['returned']['stdout'])['design_id']
out['context']['design_id']=design_id;save()
probe('cli_design_show',lambda:cli('design','show',design_id))
probe('cli_design_candidates',lambda:cli('design','candidates',design_id))
probe('cache_existing_controller_after_cli',lambda:c.get_design(design_id))
fresh=MendexEngineeringController(ROOT)
probe('cache_new_controller_after_cli',lambda:fresh.get_design(design_id))
server=MendexMCPServer(ROOT)
def rpc(name,args):
    return server.handle_request({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}})
probe('mcp_tool_schemas',lambda:server.tools_schema)
for name,tool,args in [
 ('workspace_list','list_workspaces',{}), ('workspace_create','create_workspace',{'name':'MCP transport reference'}),
 ('workspace_status_invalid','get_workspace_status',{'workspace_id':'invalid-id'}),
 ('spec_valid','validate_specification',{'spec_data':spec}), ('spec_invalid','validate_specification',{'spec_data':{'vout_v':-1}}),
 ('unknown_argument','create_workspace',{'name':'Unknown argument reference','unexpected':True}),
 ('missing_argument','create_workspace',{}), ('wrong_type','create_workspace',{'name':37}),
 ('design_get','get_design',{'design_id':design_id}), ('design_candidates','list_design_candidates',{'design_id':design_id}),
 ('calculation','run_engineering_calculations',{'calc_type':'losses','params':{}}),
 ('calculation_invalid','run_engineering_calculations',{'calc_type':'shell','params':{'command':'echo SHOULD_NOT_EXECUTE'}}),
 ('artifacts','list_design_artifacts',{'workspace_id':ws}), ('tool_check','check_tool',{'tool_id':'ltspice'}),
 ('simulation','run_simulation',{'workspace_id':ws}), ('simulations','list_simulations',{'workspace_id':ws}),
 ('revisions','list_revisions',{'product_id':str(product.product_id)}),
 ('validation','get_validation_summary',{'revision_id':rev}), ('report','generate_engineering_report',{'revision_id':rev}),
 ('unknown_destructive','delete_workspace',{'workspace_id':ws}),
]: probe('mcp_'+name,lambda tool=tool,args=args:rpc(tool,args))
# Harmless outside-root canary: prove disclosure without opening or executing any file.
outside=E/'outside-root-canary';outside.mkdir(exist_ok=True)
(outside/'canary.txt').write_text('Independent harmless traversal canary',encoding='utf-8')
probe('mcp_outside_root_read',lambda:rpc('list_design_artifacts',{'workspace_id':str(outside.resolve())}))
probe('mcp_traversal_read',lambda:rpc('list_design_artifacts',{'workspace_id':'../../outside-root-canary'}))
probe('mcp_outside_root_status',lambda:rpc('get_workspace_status',{'workspace_id':str(outside.resolve())}))
probe('mcp_invalid_design_workspace',lambda:rpc('generate_design',{'workspace_id':'nonexistent-workspace','title':'Invalid workspace reference','vin_nom':24,'vout':5,'iout':4,'generate_artifacts':False,'category':'UNSUPPORTED_CATEGORY'}))
# Actual stdio, each malformed envelope in its own process to retain crash evidence.
base=[sys.executable,'-m','mendex_core.mcp','--root',str(ROOT)]
for name,payload in {'handshake': '\n'.join(json.dumps(x) for x in [
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'independent-audit','version':'1'}}},
 {'jsonrpc':'2.0','method':'notifications/initialized'}, {'jsonrpc':'2.0','id':2,'method':'tools/list'},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'list_workspaces','arguments':{}}}])+'\n',
 'parse_error':'{invalid\n','invalid_envelope':'[]\n','invalid_params':'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":[]}\n'}.items():
    def transport(payload=payload):
        p=subprocess.run(base,input=payload,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        return {'command':base,'stdin':payload,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    probe('stdio_'+name,transport)
probe('revision_create',lambda:rpc('create_revision',{'product_id':str(product.product_id),'label':'R2'}))
probe('archived_revision_mutation',lambda:rpc('save_specification',{'revision_id':rev,'spec_data':spec}))
probe('approval_rejection',lambda:c.service.set_revision_status(product.active_revision_id,Lifecycle.APPROVED))
probe('revision_history',lambda:rpc('list_revisions',{'product_id':str(product.product_id)}))
def db_summary():
    with sqlite3.connect(f'file:{ROOT / ".mendex/studio.sqlite3"}?mode=ro',uri=True) as db:
        tables=[x[0] for x in db.execute("select name from sqlite_master where type='table'")]
        return {'integrity':db.execute('pragma integrity_check').fetchone()[0], 'schema_version':db.execute('pragma user_version').fetchone()[0], 'counts':{t:db.execute('select count(*) from "'+t+'"').fetchone()[0] for t in tables}}
probe('database_summary',db_summary)
def concurrency():
    def create(i): return MendexEngineeringController(ROOT).create_workspace(f'Concurrent reference {i}')
    with ThreadPoolExecutor(max_workers=4) as pool: return list(pool.map(create,range(8)))
probe('concurrent_workspace_creation',concurrency)
probe('restart',lambda:MendexEngineeringController(ROOT).list_workspaces())
# Lower-level real solver test, expressly distinct from broken CLI/MCP dispatch.
design=fresh.design_service.get_design(design_id)
ws_dir=ROOT/'workspaces'/ws
probe('real_ltspice_lower_core',lambda:fresh.design_service.run_ltspice_simulation(design_id,ws_dir).model_dump(mode='json'))
probe('simulations_after_real_lower_core',lambda:MendexEngineeringController(ROOT).list_simulations(ws))
probe('femm_api_contract',lambda:{'run_script_exists':hasattr(__import__('mendex_core.design.femm_runner',fromlist=['FEMMRunner']).FEMMRunner,'run_script')})
# Native KiCad checks on generated files, never use empty-board results as readiness.
from integrations.adapters.kicad import KiCadAdapter
from integrations.adapters.femm import FEMMAdapter
from integrations.contracts import JobRequest
probe('kicad_detection',lambda:KiCadAdapter().descriptor.model_dump(mode='json'))
for operation,ext in [('erc','.kicad_sch'),('drc','.kicad_pcb')]:
    files=list(ws_dir.rglob('*'+ext))
    if files: probe('real_kicad_'+operation,lambda operation=operation,files=files:KiCadAdapter().execute(JobRequest(job_id=str(uuid4()),workspace_id=ws,tool_id='kicad',operation=operation,input_paths=[str(files[0])],timeout_s=40),E/('native-kicad-'+operation)).model_dump(mode='json'))
probe('femm_detection',lambda:FEMMAdapter().descriptor.model_dump(mode='json'))
probe('real_femm_adapter',lambda:FEMMAdapter().execute(JobRequest(job_id=str(uuid4()),workspace_id=ws,tool_id='femm',operation='solve_2d_magnetic',parameters={'primary_turns':24,'secondary_turns':12,'primary_current_a':1,'frequency_hz':1000},timeout_s=35),E/'native-femm').model_dump(mode='json'))
probe('existing_data_after',inventory)
before=out['existing_data_before']['returned'];after=out['existing_data_after']['returned']
out['original_data_comparison']={'removed':[k for k in before if k not in after],'modified':[k for k in before if k in after and before[k]!=after[k]],'added':[k for k in after if k not in before]}
save()
