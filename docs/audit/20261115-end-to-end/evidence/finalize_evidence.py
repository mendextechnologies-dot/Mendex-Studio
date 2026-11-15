"""Capture final assessment evidence without touching application data."""
import hashlib,json,shutil,sys,subprocess,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

E=Path(__file__).resolve().parent; R=E.parents[3]
sys.path.insert(0,str(R/'src'))
def save(n,v): (E/n).write_text(json.dumps(v,indent=2,default=str),encoding='utf-8')
from mendex_core.service import StudioService
from mendex_core.design.thermal_engine import PCBThermalEngine
s=StudioService(E/'final-probe-root')
p=s.create_product('AUDIT-FINAL','Empty audit framework fixture','dc_dc_converter','Audit only')
rev=s.get_revision(p.active_revision_id)
res={'empty_thermal_current':s.calculate_pcb_thermal_field(rev.revision_id)}
if hasattr(s,'generate_enclosure_model'):
    try: res['empty_enclosure_without_solver']=s.generate_enclosure_model(rev.revision_id,export_step=False)
    except Exception as ex: res['empty_enclosure_without_solver']={'error':str(ex)}
save('final-source-probes.json',res)
copies=['src/mendex_core/service.py','src/mendex_core/design/thermal_engine.py','src/mendex_core/design/wcca_engine.py','src/mendex_core/design/bom_pricing.py','src/mendex_core/design/release_packager.py','src/mendex_core/design/test_plan_generator.py','src/integrations/generators/enclosure_generator.py','desktop/src/components/RecordFormView.tsx','desktop/src/pages/ProjectDetail.tsx']
for rel in copies:
    src=R/rel
    if src.exists():
        dest=E/'source-at-close'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
save('source-at-close.json',{rel:hashlib.sha256((R/rel).read_bytes()).hexdigest() for rel in copies if (R/rel).exists()})
native={}
for pattern in ['test_kicad_schematic_erc_zero_*/kicad_buck/erc.json','test_kicad_pcb_drc_and_no_isol*/drc.json']:
    for path in (E/'pytest-temp').glob(pattern):
        data=json.loads(path.read_text(encoding='utf-8'))
        violations=data.get('violations',[])+[v for s in data.get('sheets',[]) for v in s.get('violations',[])]
        native[str(path.relative_to(E))]={'severity_counts':dict(Counter(v.get('severity') for v in violations)),
            'unconnected':len(data.get('unconnected',data.get('unconnected_items',[]))), 'keys':list(data)}
save('native-check-summary.json',native)
tests=ET.parse(E/'pytest.xml').getroot().find('testsuite')
groups=Counter(t.get('classname') for t in tests.findall('testcase'))
failed=[t.get('classname')+'::'+t.get('name') for t in tests.findall('testcase') if t.find('failure') is not None]
save('test-summary.json',{'total':tests.get('tests'),'failures':tests.get('failures'),'seconds':tests.get('time'),'groups':dict(groups),'failed':failed})
save('git-at-close.json',{'status':subprocess.run(['git','status','--short'],cwd=R,capture_output=True,text=True).stdout,'commit':subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True).stdout})
print('Captured final source probes, source copies, native and regression summaries')
