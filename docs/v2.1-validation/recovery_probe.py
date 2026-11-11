"""Controlled database/job concurrency probes on separate SOFTWARE FIXTURE data."""
from pathlib import Path
import json, os, sqlite3, sys, time, traceback
E=Path(__file__).parent.resolve()/'evidence';R=E.parents[2];sys.path.insert(0,str(R/'src'))
from mendex_core.service import StudioService
from mendex_core.integration_contracts import JobRequest
out={};root=E/'recovery-data-2';s=StudioService(root);ws=s.integrations.create_workspace('Synthetic recovery audit only')
try:
    req=JobRequest(workspace_id=ws['workspace_id'],tool_id='studio-demo',operation='synthetic-echo',parameters={'steps':100,'delay_s':.05},timeout_s=20,provenance='SYNTHETIC SOFTWARE FIXTURE; engineering NOT_EVALUATED')
    job=s.integrations.submit(req)
    time.sleep(.2)
    out['before_second_client']=s.integrations.job(job.request.job_id).model_dump(mode='json')
    second=StudioService(root)
    out['after_second_client']=second.integrations.job(job.request.job_id).model_dump(mode='json')
    out['executor_still_running']=not s.integrations._futures[job.request.job_id].done() if job.request.job_id in s.integrations._futures else 'key format differs'
    out['eventual_state']=s.integrations.wait(job.request.job_id,timeout=25).model_dump(mode='json')
except Exception:out['exception']=traceback.format_exc()
finally:
    try:s.integrations.shutdown()
    except Exception:pass
    (E/'recovery.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
