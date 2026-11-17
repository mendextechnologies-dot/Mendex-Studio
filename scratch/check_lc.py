from pathlib import Path
from src.mendex_core.service import StudioService
from src.mendex_core.desktop.service import DesktopService
from src.mendex_core.desktop.models import ProjectQuery

studio = StudioService(Path.cwd())
ds = DesktopService(studio)
proj = ds.project(ProjectQuery(project_id='8f697275-3a8d-456c-ae20-138a7698df61'))
lc = proj.get('lifecycle')
if lc:
    for st in lc.get('stages', []):
        sid = st.get('definition', {}).get('id')
        name = st.get('definition', {}).get('name')
        eff = st.get('effective_status')
        bl = st.get('blockers')
        rv = st.get('review', {})
        rv_status = rv.get('effective_status') if rv else None
        print(f"Stage '{sid}' ({name}): effective={eff}, review_eff={rv_status}, blockers={bl}")
