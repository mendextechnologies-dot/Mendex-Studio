import json
from pathlib import Path
from src.mendex_core.service import StudioService
from src.mendex_core.desktop.service import DesktopService
from src.mendex_core.desktop.models import ProjectQuery

studio = StudioService(Path.cwd())
ds = DesktopService(studio)
proj = ds.project(ProjectQuery(project_id='8f697275-3a8d-456c-ae20-138a7698df61'))

print("Project Name:", proj['product']['name'])
print("Revision:", proj['revision']['revision_label'])
lc = proj['lifecycle']
print("Lifecycle Definition ID:", lc['definition_id'])
print("Engineering Status:", lc['engineering_status'])
print("Approval Status:", lc['approval_status'])

all_completed = True
for st in lc['stages']:
    sid = st['definition']['id']
    sname = st['definition']['name']
    eff = st['effective_status']
    blk = st['blockers']
    rev = st.get('review')
    rev_dec = rev.get('decision') if rev else 'N/A'
    print(f"  [{eff}] {sid:25} (Review: {rev_dec}) - Blockers: {blk}")
    if eff != 'COMPLETED':
        all_completed = False

print("\nALL 9 STAGES COMPLETED:", all_completed)
assert all_completed, "Not all stages are completed!"
