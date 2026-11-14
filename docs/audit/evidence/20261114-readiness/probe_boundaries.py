from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,hashlib
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
out=Path(__file__).resolve().parent
root=out/'boundary-fixture';studio=StudioService(root)
p=studio.create_product('BOUNDARY','Disposable mutation-permission probe','pcb','Software fixture')
r=studio.get_revision(p.active_revision_id);board=studio.workspace_path(r)/'pcb/fixture.kicad_pcb';board.write_text('(kicad_pcb)',encoding='utf-8')
studio.create_revision(p.product_id,'R002');before=hashlib.sha256(board.read_bytes()).hexdigest();calls=[]
def route(*args,**kwargs):
 calls.append(str(kwargs['pcb_path']));return {'routing_completed':False,'tracks':1,'unrouted_after':7,'drc_errors':3}
with patch.object(CopperKiCadAdapter,'route_pcb',route),patch.object(CopperKiCadAdapter,'render_3d',lambda *a,**k:None):
 response=DesktopService(studio).auto_route_pcb(SimpleNamespace(revision_id=r.revision_id))
results={'archived_revision_status':studio.get_revision(r.revision_id).lifecycle_status,'archived_route_adapter_called':bool(calls),'routing_response_with_seven_unrouted_and_three_drc_errors':response,'fixture_board_bytes_unchanged_by_spy':hashlib.sha256(board.read_bytes()).hexdigest()==before,'duplicate_creepage_material_probes':{g:CopperKiCadAdapter.calculate_iec60664_creepage(230,2,g,'reinforced') for g in ('I','II','IIIa','IIIb')},'duplicate_creepage_accepts_negative_voltage':CopperKiCadAdapter.calculate_iec60664_creepage(-230)}
(out/'boundary-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8');print(json.dumps(results,indent=2))
