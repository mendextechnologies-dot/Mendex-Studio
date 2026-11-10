"""Audit-only probes of the concurrently committed UI delta."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,tempfile
from PySide6.QtWidgets import QApplication,QLabel
from mendex_core.models import Specification
from mendex_core.service import StudioService
from mendex_ui.workspace_panels import TransformerWorkspacePanel

E=Path(__file__).resolve().parent
root=Path(tempfile.mkdtemp(prefix='fvw-'))
app=QApplication.instance() or QApplication([])
service=StudioService(root)
p=TransformerWorkspacePanel(service,lambda fn:fn(),QLabel('SOFTWARE VERIFICATION ONLY'))
p._suppress_dialogs=True
p.set_revision(SimpleNamespace(specification=Specification(vin_min_v=36,vout_v=400,iout_a=.5,switching_frequency_hz=150000)))
before={x:getattr(p,x).text() for x in ('vin_min','vout','iout','freq_khz')}
p.set_revision(SimpleNamespace(specification=Specification()))
after={x:getattr(p,x).text() for x in before}
one,_=p.calculate();f1=root/'one.lua';p.export_femm_script(target_path=f1)
p.vout.setText('200');two,_=p.calculate();f2=root/'two.lua';p.export_femm_script(target_path=f2)
data={'scope':'Synthetic UI/software probes only; no engineering design/approval','revision_reset':{'previous':before,'after_unspecified_revision':after,'stale_fields_retained':before==after},'no_product_calculation':{'products':len(service.list_products()),'numeric_result_returned':one is not None},'femm_export':{'calculated_turns_changed':one.secondary_turns!=two.secondary_turns,'script_bytes_identical':f1.read_bytes()==f2.read_bytes(),'first_sha256':hashlib.sha256(f1.read_bytes()).hexdigest(),'second_sha256':hashlib.sha256(f2.read_bytes()).hexdigest()},'traceability':{'jobs':len(service.integrations.list_jobs()),'products':len(service.list_products()),'notes':'UI calls math and writes scripts directly; no service-calculation run/hash/source metadata is persisted'}}
with (E/'LATEST_UI_PROBES.json').open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
print(json.dumps(data,indent=2))
service.integrations.shutdown()
