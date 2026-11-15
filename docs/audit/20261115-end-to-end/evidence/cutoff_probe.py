"""Final isolated check of concurrent packaging edits."""
from pathlib import Path
import hashlib,json,sys
from datetime import datetime,timezone
E=Path(__file__).resolve().parent;R=E.parents[3];sys.path.insert(0,str(R/'src'))
from mendex_core.service import StudioService
s=StudioService(E/'cutoff-root');p=s.create_product('AUDIT-CUTOFF','Packaging fixture','dc_dc_converter','Audit only')
r=s.get_revision(p.active_revision_id);w=s.workspace_path(r);w.mkdir(parents=True,exist_ok=True)
for name in ['only_report.html','model.step','simulation.raw','simulation.net','requirements.json']:
    (w/name).write_text('AUDIT PLACEHOLDER - no engineering evidence',encoding='utf-8')
result=s.generate_release_package(r.revision_id)
archive=w/result['package_relative_path'];archive.write_bytes(b'CORRUPTED AUDIT ARCHIVE')
data={'utc':datetime.now(timezone.utc).isoformat(),'members':[x['file'] for x in result['contents']],
      'status_incomplete':result['status'],'status_corrupted':s.get_release_package(r.revision_id)['status']}
for rel in ['src/mendex_core/design/release_packager.py','src/mendex_core/desktop/service.py','src/mendex_core/desktop/models.py','desktop/src/api/client.ts','desktop/src/api/types.ts']:
    src=R/rel;dest=E/'source-at-final-cutoff'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
    data.setdefault('source_sha256',{})[rel]=hashlib.sha256(src.read_bytes()).hexdigest()
(E/'final-cutoff-probe.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data))
