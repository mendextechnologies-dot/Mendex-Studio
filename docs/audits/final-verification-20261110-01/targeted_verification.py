"""Safe negative and generic UI/native verification; never alters application code."""
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Timer
from time import monotonic
import ast, hashlib, json, os, platform, shutil, subprocess, sys, tempfile
from uuid import uuid4

from mendex_core.service import StudioService
from mendex_core.models import Specification
from mendex_core.evidence import ManualCheck
from mendex_core.integration_contracts import JobRequest, ToolConfiguration, ExecutionContext
from integrations.v15_connector import LTspiceV15Connector, PythonV15Connector, DatasetV15Connector
from integrations.runners.safe_runner import SafeRunner
from integrations.parsers.kicad_parser import parse_kicad_drc_json
from integrations.datasets.magnet_dataset import MagNetDataset
from integrations.datasets.switchloss_db import SwitchLossDB

E=Path(__file__).resolve().parent
root=Path(tempfile.mkdtemp(prefix='fvp-'))
data={'snapshot':sys.argv[1],'probe_root':str(root),'environment':{'python':sys.version,'platform':platform.platform(),'git':subprocess.check_output(['git','--version'],text=True).strip()}}
def save():
    (E/('PROBES-'+sys.argv[1]+'.json')).write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')
fake=root/'fake.exe';fake.write_bytes(b'NONEXECUTABLE verification sentinel; NEVER EXECUTED')
service=StudioService(root/'studio');engine=service.integrations
connector=LTspiceV15Connector(str(fake))
engine.register_reviewed_adapter(connector)
engine.configure('ltspice',ToolConfiguration(executable_path=str(fake)))
data['fake_binary_application_verify']=engine.verify('ltspice').model_dump(mode='json')
data['missing_python_verify']=PythonV15Connector().verify(ToolConfiguration(executable_path=str(root/'missing-python.exe'))).model_dump(mode='json')
dataset=DatasetV15Connector('magnet-dataset','MagNet Dataset','dataset','https://example.org/negative-fixture')
engine.register_reviewed_adapter(dataset)
data['dataset_no_resource_health']=engine.verify('magnet-dataset').model_dump(mode='json')
ws=engine.create_workspace('Verification software fixtures')
req=JobRequest(workspace_id=ws['workspace_id'],tool_id='magnet-dataset',operation='verify_checksum',provenance='Negative software test: no input')
job=engine.submit(req);done=engine.wait(job.request.job_id)
data['dataset_no_input_job']={'status':done.status.value,'outputs':done.result.outputs,'evidence_paths':done.result.evidence_paths,'integrity':engine.evidence_integrity(job.request.job_id)}
runner=SafeRunner(allowlist_patterns=['definitely-not-python'])
try:data['non_allowlisted_binary_accepted']=str(runner.validate_command([sys.executable,'--version']))
except Exception as exc:data['non_allowlisted_binary_accepted']={'rejected':repr(exc)}
outside=root/'outside-workdir.log';outside.write_text('AUDIT SENTINEL')
out=runner.run([sys.executable,'-c','print("benign audit output")'],root/'runner',timeout_s=5,log_file=outside)
data['runner_log_boundary']={'status':str(out.status),'outside_workdir_written':outside.exists(),'sentinel_overwritten':outside.read_text()!='AUDIT SENTINEL'}
bad=root/'malformed-drc.txt';bad.write_text('THIS IS NOT A KICAD REPORT')
data['malformed_kicad']=parse_kicad_drc_json(bad)
mag=root/'missing-fields.json';mag.write_text('{"measurements":[{}]}')
loader=MagNetDataset();loader.load_json(mag)
data['missing_magnet_measurements']=[x.model_dump() for x in loader._records]
csv=root/'unrelated.csv';csv.write_text('unrelated_column\nplaceholder\n')
loader2=SwitchLossDB();loader2.load_csv(csv)
data['unrelated_switchloss_csv']=[x.model_dump() for x in loader2._records]

# Reproduce old report/spec interleaving using an audit-only instance hook.
product=service.create_product('SNAPSHOT','Software fixture','pcb','Verifier')
revision=product.active_revision_id
evidence=root/'software.txt';evidence.write_text('SOFTWARE fixture, no engineering meaning')
check=ManualCheck(check_id='fixture',reviewer='Verifier',notes='Software fixture only',status='pass',measured_value=1,unit='1',minimum=0)
original=service.get_product;flag={'fired':False}
def interleave(pid):
    if not flag['fired']:
        flag['fired']=True
        service.update_specification(revision,Specification(vout_v=24,source='Synthetic fixture'))
        service.record_validation(revision,check,evidence)
    return original(pid)
service.get_product=interleave
report=service.generate_report(revision)
snapshot=json.loads((service.root/report.report_path).with_name('snapshot.json').read_text())
data['report_interleaving']={'hook_fired':flag['fired'],'report_hash':report.input_hash,'report_vout':snapshot['revision']['specification']['vout_v'],'validation':[(x['effective_status'],x['record']['input_hash'],x['record']['specification']['vout_v']) for x in snapshot['validation']]}
service.get_product=original
collision=engine.workspace_path(ws['workspace_id'])/'REQUEST.JSON';collision.write_text('RAW fixture must remain unchanged')
request=JobRequest(workspace_id=ws['workspace_id'],tool_id='studio-demo',operation='synthetic-echo',input_paths=['REQUEST.JSON'],parameters={'steps':1,'delay_s':0},provenance='Windows reserved-name regression')
try:
    j=engine.submit(request);d=engine.wait(j.request.job_id)
    data['windows_reserved_collision']={'status':d.status.value,'integrity':engine.evidence_integrity(j.request.job_id),'staged_input_preserved':(engine.job_path(j.request.job_id)/'REQUEST.JSON').read_text()=='RAW fixture must remain unchanged'}
except Exception as exc:data['windows_reserved_collision']={'rejected':repr(exc)}
engine.shutdown();save()

if sys.argv[1]=='main':
    from PySide6.QtWidgets import QApplication, QPushButton
    from mendex_ui.window import StudioWindow
    app=QApplication.instance() or QApplication([])
    ui_service=StudioService(root/'ui');window=StudioWindow(ui_service);window.show();app.processEvents()
    eng=ui_service.integrations
    data['ui']={'navigation':[window.navigation.item(i).text() for i in range(window.navigation.count())],'default_cli_adapters':list(StudioService(root/'cli').integrations.adapters),'ui_adapters':list(eng.adapters),'buttons':[x.text() for x in window.jobs_panel.findChildren(QPushButton)],'menus':[x.text() for x in window.menuBar().actions()],'catalog_count':len(eng.list_tools())}
    data['tool_health']={}
    for tool in eng.list_tools():
        try:data['tool_health'][tool.tool_id]={'detect':eng.detect(tool.tool_id).model_dump(mode='json'),'verify':eng.verify(tool.tool_id).model_dump(mode='json')}
        except Exception as exc:data['tool_health'][tool.tool_id]={'error':repr(exc)}
    window.navigation.setCurrentRow(12);app.processEvents()
    window.grab().save(str(E/'main-jobs.png'))
    # Use the exact existing native-test fixture, not a product design/model.
    tree=ast.parse((Path.cwd()/'tests/integration/test_v15_integration_hook.py').read_text())
    fixture=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='netlist_text' for t in n.targets))
    source=root/'existing-test-fixture.net';source.write_text(fixture)
    workspace=eng.create_workspace('Existing RC software test fixture')
    rel=eng.attach_input(workspace['workspace_id'],source)
    j=eng.submit(JobRequest(workspace_id=workspace['workspace_id'],tool_id='ltspice',operation='batch_simulate',input_paths=[rel],timeout_s=15,provenance='Existing generic RC software test fixture; no engineering qualification'))
    result=eng.wait(j.request.job_id,timeout=30)
    manifest=eng.evidence(j.request.job_id)
    dest=E/'native-rc';dest.mkdir()
    retained=[]
    for artifact in manifest.artifacts:
        src=eng.job_path(j.request.job_id)/artifact.relative_path
        name=str(len(retained))+'-'+src.name;shutil.copyfile(src,dest/name)
        retained.append({'path':artifact.relative_path,'saved':name,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'bytes':src.stat().st_size})
    data['native_rc']={'status':result.status.value,'result':result.result.model_dump(mode='json'),'integrity':eng.evidence_integrity(j.request.job_id),'manifest':manifest.model_dump(mode='json'),'artifacts':retained,'actual_files':[x.relative_to(eng.job_path(j.request.job_id)).as_posix() for x in eng.job_path(j.request.job_id).rglob('*') if x.is_file()]}
    # Bounded benign Python workload tests actual connector cancellation latency.
    script=root/'sleep.py';script.write_text('import time\ntime.sleep(1.2)\n')
    event=Event();context=ExecutionContext(root,event,monotonic()+5,lambda _:None,lambda _:None)
    timer=Timer(.15,event.set);timer.start();start=monotonic()
    try:
        PythonV15Connector().execute(JobRequest(workspace_id=uuid4(),tool_id='python',operation='run_script',input_paths=['sleep.py'],timeout_s=5,provenance='Benign cancellation test'),context)
        outcome='returned'
    except Exception as exc:outcome=type(exc).__name__
    timer.join();data['python_cancel']={'event_after_s':.15,'returned_after_s':round(monotonic()-start,3),'outcome':outcome}
    window.close();app.processEvents();save()
print(json.dumps(data,indent=2,default=str))
