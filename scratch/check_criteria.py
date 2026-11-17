from pathlib import Path
from src.mendex_core.service import StudioService
from src.mendex_core.desktop.service import DesktopService
from src.mendex_core.desktop.models import ProjectQuery

studio = StudioService(Path.cwd())
ds = DesktopService(studio)
proj = ds.project(ProjectQuery(project_id='8f697275-3a8d-456c-ae20-138a7698df61'))
lc = proj.get('lifecycle')
for st in lc.get('stages', []):
    sid = st['definition']['id']
    if sid in ('verification', 'prototype_testing', 'documentation'):
        print(f"=== Stage: {sid} ===")
        print("Status:", st.get('status'))
        print("Effective:", st.get('effective_status'))
        print("Attempt:", st.get('attempt'))
        print("Criteria:", st.get('criteria'))
        print("Blockers:", st.get('blockers'))
        print("Review req:", st['definition']['review_required'])
        print("Definition criteria:", st['definition']['criteria'])
