path = 'src/mendex_core/engineering_reviews/service.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update is_ephemeral_workspace_file to include .kicad_prl and backup extensions
old_ephemeral = """    fname = parts[-1].lower()
    if (
        fname.endswith((".lck", ".tmp", ".log", ".raw", ".ans", ".db", ".png", ".jpg", ".svg", ".step", ".drl", ".gbr", ".gbrjob", ".zip", ".rpt"))
        or fname.startswith("~")
    ):
        return True"""

new_ephemeral = """    fname = parts[-1].lower()
    if (
        fname.endswith((".lck", ".tmp", ".log", ".raw", ".ans", ".db", ".png", ".jpg", ".svg", ".step", ".drl", ".gbr", ".gbrjob", ".zip", ".rpt", ".kicad_prl", ".bak", "-bak"))
        or fname.startswith("~")
    ):
        return True"""

if old_ephemeral in text:
    text = text.replace(old_ephemeral, new_ephemeral, 1)
    print("Updated is_ephemeral_workspace_file with .kicad_prl")
else:
    print("Could not find old_ephemeral in text")

# 2. Add STAGE_DOCUMENT_SCOPES and is_stage_document
scoped_docs_def = """STAGE_DOCUMENT_SCOPES = {
    "project_initialization": set(),
    "requirements": {"requirements", "specs", "specification", "architecture"},
    "feasibility": {"feasibility", "architecture", "requirements", "magnetics"},
    "calculations": {"calculations", "magnetics", "circuit", "requirements"},
    "design_development": {"pcb", "circuit", "mechanical", "magnetics", "assembly"},
    "simulation": {"simulations", "pcb", "circuit", "magnetics"},
    "verification": {"verification", "validation", "simulations", "measurements", "pcb", "circuit"},
    "prototype_testing": {"measurements", "laboratory", "validation"},
    "documentation": {"bom", "assembly", "mechanical", "documentation", "pcb"},
}


def is_stage_document(rel: str, stage_id: str) -> bool:
    \"\"\"Returns True if the document path is within the scope of the given lifecycle stage.\"\"\"
    if not stage_id or stage_id not in STAGE_DOCUMENT_SCOPES:
        return True
    allowed_scopes = STAGE_DOCUMENT_SCOPES[stage_id]
    parts = rel.replace("\\\\", "/").split("/")
    top_dir = parts[0].lower() if len(parts) > 1 else ""
    fname = parts[-1].lower()

    if top_dir:
        return any(s in top_dir for s in allowed_scopes)

    return fname.endswith((".txt", ".md", ".json", ".csv", ".pdf", ".docx"))
"""

if "def is_stage_document" not in text:
    target_pos = text.find("class EngineeringReviewService:")
    if target_pos != -1:
        text = text[:target_pos] + scoped_docs_def + "\n\n" + text[target_pos:]
        print("Added is_stage_document definition")

# 3. Update prepare_package to filter doc_hashes by stage
old_prep_docs = """        # 4. Workspace document hashes
        ws_path = self.studio.workspace_path(revision)
        doc_hashes = {}
        if ws_path.exists():
            for f in sorted(ws_path.glob("**/*")):
                if f.is_file() and f.stat().st_size <= MAX_FILE:
                    rel = f.relative_to(ws_path).as_posix()
                    if not is_ephemeral_workspace_file(rel):
                        doc_hashes[rel] = file_hash(f)"""

new_prep_docs = """        # 4. Workspace document hashes scoped to this stage
        ws_path = self.studio.workspace_path(revision)
        doc_hashes = {}
        if ws_path.exists():
            for f in sorted(ws_path.glob("**/*")):
                if f.is_file() and f.stat().st_size <= MAX_FILE:
                    rel = f.relative_to(ws_path).as_posix()
                    if not is_ephemeral_workspace_file(rel) and is_stage_document(rel, stage_id):
                        doc_hashes[rel] = file_hash(f)"""

if old_prep_docs in text:
    text = text.replace(old_prep_docs, new_prep_docs, 1)
    print("Updated prepare_package with scoped doc_hashes")
else:
    print("Could not find old_prep_docs in text")

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Saved service.py")
