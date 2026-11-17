import json
from pathlib import Path
from src.mendex_core.service import StudioService
from src.mendex_core.engineering_reviews.service import is_ephemeral_workspace_file
from src.mendex_core.engineering_lifecycle.storage import file_hash

studio = StudioService(Path.cwd())
rid = '9b7c1396-64da-41f8-8649-77dc0f24e103'
with studio.connection() as conn:
    row = conn.execute(
        "SELECT sequence, payload FROM engineering_reviews WHERE revision_id=? AND stage_id=? ORDER BY sequence DESC LIMIT 1",
        (rid, "verification")
    ).fetchone()

if row:
    record = json.loads(row[1])
    print("Verification review found:", record["decision"], record["reviewer_name"], "attempt:", record["attempt"])
    revision = studio.get_revision(rid)
    ws_path = studio.workspace_path(revision)
    for rel, exp_h in record.get("document_hashes", {}).items():
        if is_ephemeral_workspace_file(rel):
            continue
        fp = ws_path / rel
        if not fp.is_file():
            print("Missing file:", rel)
        else:
            cur_h = file_hash(fp)
            if cur_h != exp_h:
                print(f"Hash mismatch: {rel}\n  exp: {exp_h}\n  got: {cur_h}")
else:
    print("No review found for verification")
