from pathlib import Path
from src.mendex_core.service import StudioService
studio = StudioService(Path.cwd())
rid = '9b7c1396-64da-41f8-8649-77dc0f24e103'
ws = studio.workspace_path(studio.get_revision(rid))
prl = ws / 'pcb' / 'sv1000.kicad_prl'
if prl.exists():
    with open(prl, 'a') as f:
        f.write(' ')
    print('Modified sv1000.kicad_prl')

lc = studio.engineering_lifecycle.get(rid)
all_comp = all(s['effective_status'] == 'COMPLETED' for s in lc['stages'])
print('Stages still all COMPLETED after touching kicad_prl?:', all_comp)
for s in lc['stages']:
    sid = s['definition']['id']
    eff = s['effective_status']
    print(f'  {sid}: {eff}')
