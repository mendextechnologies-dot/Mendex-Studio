"""Reproduce current gaps on disposable data; no native solvers or live writes."""
import hashlib,json,tempfile,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.models import ProjectQuery
from mendex_core.desktop.service import DesktopService
from mendex_core.integration_contracts import JobRecord,JobRequest
from mendex_core.mcp.server import MendexMCPServer

out=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix="mendex-audit-20261114-") as td:
 root=Path(td); ctrl=MendexEngineeringController(root)
 a=ctrl.create_project("Audit A",code="AUDIT-A",auto_enroll=True)
 b=ctrl.create_project("Audit B",code="AUDIT-B",auto_enroll=True)
 pid=a["project_id"];rid=ctrl.service.get_product(pid).active_revision_id
 args=dict(workspace_id=pid,product_id=pid,title="Disposable design",vin_min=18,vin_nom=24,vin_max=30,vout=5,iout=2,fsw_hz=100000,ripple_v=.1)
 first=ctrl.generate_design(**args)
 originals={x["path"]:x["sha256"] for x in first["generated_artifacts"]}
 second=ctrl.generate_design(**args)
 overwritten=[p for p,h in originals.items() if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h]
 try:
  ctrl.generate_design(**{**args,"vout":8})
  conflict_rejected=False
 except Exception as e:
  conflict_rejected=True;conflict_error=str(e)
 missing=MendexMCPServer(root).handle_request({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"generate_design","arguments":{"workspace_id":pid,"title":"Missing inputs","generate_artifacts":False}}})
 job=JobRecord(request=JobRequest(workspace_id=b["project_id"],tool_id="audit-software-fixture",operation="inspect",parameters={"revision_id":str(ctrl.service.get_product(b["project_id"]).active_revision_id)},provenance="Audit fixture; not a simulation"))
 ctrl.service.integrations.list_jobs=lambda:[job]
 desktop=DesktopService(ctrl.service).project(ProjectQuery(project_id=pid))
 startup_root=root/'concurrent-first-start'
 code="from pathlib import Path; from mendex_core.service import StudioService; import sys; StudioService(Path(sys.argv[1]))"
 def start(_):
  p=subprocess.run([sys.executable,'-c',code,str(startup_root)],capture_output=True,text=True,timeout=30)
  return {"exit_code":p.returncode,"stderr":p.stderr[-1000:]}
 with ThreadPoolExecutor(max_workers=4) as pool:starts=list(pool.map(start,range(4)))
 result={"overwritten_registered_artifacts":overwritten,"saved_spec_conflict_rejected":conflict_rejected,"missing_mcp_inputs_rejected":missing['result']['isError'],"desktop_project_A_includes_project_B_job":any(str(x['request']['job_id'])==str(job.request.job_id) for x in desktop['simulations']),"created_designs":len(ctrl.design_service.list_designs(pid)),"desktop_visible_designs":len(desktop['designs']),"concurrent_initialization":starts}
 (out/'probe-results-after.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
