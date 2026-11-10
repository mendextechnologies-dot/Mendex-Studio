"""Revision-aware KiCad workspace operations shared by desktop and CLI."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

from .evidence import specification_hash
from .models import Lifecycle, now
from .service import StudioError


DESIGN_EXTENSIONS = {".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_dru"}
CONTEXT_EXTENSIONS = DESIGN_EXTENSIONS | {".kicad_sym", ".kicad_mod", ".kicad_wks"}
MAX_FILE_BYTES = 50 * 1024 * 1024


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_structure(path):
    """Inspect native S-expressions; ignore quoted text and library definitions.

    This guards empty files, not engineering correctness. KiCad performs ERC/DRC.
    """
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("KiCad file exceeds the 50 MiB inspection limit")
    text = path.read_text(encoding="utf-8-sig")
    tokens = re.finditer(r'"(?:\\.|[^"\\])*"|;[^\n]*|[()]|[^\s();"]+', text)
    stack, roots = [], []
    for match in tokens:
        token = match.group()
        if token.startswith(";"):
            continue
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unbalanced KiCad document")
            stack.pop()
        elif stack:
            stack[-1].append(token)
        else:
            raise ValueError("Unexpected content outside KiCad document")
    expected = "kicad_sch" if path.suffix == ".kicad_sch" else "kicad_pcb"
    if stack or len(roots) != 1 or not roots[0] or roots[0][0] != expected:
        raise ValueError("Invalid or incomplete native KiCad document")
    children = [x for x in roots[0][1:] if isinstance(x, list) and x]
    counts = {name: sum(x[0] == name for x in children)
              for name in ("symbol", "wire", "sheet", "footprint", "segment", "arc", "zone")}
    pads = sum(sum(isinstance(p, list) and bool(p) and p[0] == "pad" for p in x[1:])
               for x in children if x[0] == "footprint")
    if expected == "kicad_sch":
        populated = counts["symbol"] > 0
        reason = "" if populated else "No placed symbols. An empty or hierarchy-only sheet cannot establish circuit validation."
    else:
        populated = counts["footprint"] > 0 and pads > 0
        reason = "" if populated else "No populated footprints/pads. Board outline alone is not a circuit layout."
    return {**counts, "pads": pads, "populated": populated, "reason": reason}


class PCBWorkspaceService:
    def __init__(self, studio):
        self.studio = studio

    def _revision(self, revision_id):
        revision = self.studio.get_revision(revision_id)
        workspace = self.studio.workspace_path(revision)
        pcb = workspace / "pcb"
        if not pcb.resolve().is_relative_to(workspace):
            raise StudioError("INVALID_INPUT", "PCB workspace points outside this revision")
        return revision, workspace, pcb

    def _design(self, revision_id, relative_path):
        revision, workspace, pcb = self._revision(revision_id)
        relative = Path(relative_path)
        path = (workspace / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(pcb) or not path.is_file():
            raise StudioError("INVALID_INPUT", "Select a file inside this revision's pcb folder")
        if path.suffix not in DESIGN_EXTENSIONS:
            raise StudioError("INVALID_INPUT", "Select a native KiCad design file")
        return revision, workspace, path

    def overview(self, revision_id):
        revision, workspace, pcb = self._revision(revision_id)
        files = []
        for path in sorted(pcb.rglob("*")) if pcb.is_dir() else []:
            if not path.is_file() or not path.resolve().is_relative_to(pcb) or path.suffix not in DESIGN_EXTENSIONS:
                continue
            entry = {"path": path.relative_to(workspace).as_posix(), "bytes": path.stat().st_size,
                     "kind": path.suffix.removeprefix(".kicad_")}
            if path.suffix in {".kicad_sch", ".kicad_pcb"}:
                try:
                    entry["structure"] = native_structure(path)
                except (OSError, ValueError, UnicodeError) as exc:
                    entry["structure"] = {"populated": False, "reason": str(exc)}
            files.append(entry)
        tool = self.studio.lifecycle.kicad
        return {"revision_id": str(revision.revision_id), "label": revision.revision_label,
                "workspace": str(pcb), "editable": revision.lifecycle_status == Lifecycle.DRAFT,
                "tool_available": tool.is_available(), "tool_path": str(tool.kicad_cli or ""),
                "files": files, "checks": self.list_checks(revision_id),
                "product_evaluation": "NOT_EVALUATED",
                "notice": "ERC/DRC evaluates configured rules only. HV isolation and prototype review remain separate."}

    def import_file(self, revision_id, source):
        revision, workspace, pcb = self._revision(revision_id)
        if revision.lifecycle_status != Lifecycle.DRAFT:
            raise StudioError("IMMUTABLE", "Only a draft revision can import design files")
        source = Path(source).resolve()
        if source.suffix not in DESIGN_EXTENSIONS or not source.is_file():
            raise StudioError("INVALID_INPUT", "Import a KiCad schematic, board, project or rules file")
        if source.stat().st_size > MAX_FILE_BYTES:
            raise StudioError("INVALID_INPUT", "Import exceeds the 50 MiB file limit")
        pcb.mkdir(parents=True, exist_ok=True)
        destination = pcb / source.name
        try:
            with source.open("rb") as src, destination.open("xb") as dest:
                shutil.copyfileobj(src, dest)
        except FileExistsError as exc:
            raise StudioError("CONFLICT", "This filename already exists. Existing design/evidence files are never overwritten.") from exc
        return destination.relative_to(workspace).as_posix()

    def open_file(self, revision_id, relative_path):
        revision, _, _ = self._design(revision_id, relative_path)
        if revision.lifecycle_status != Lifecycle.DRAFT:
            raise StudioError("IMMUTABLE", "Archived/review designs cannot be opened for editing; use a draft revision")
        return self.studio.open_project_file(revision_id, relative_path)

    def _context(self, pcb):
        result = {}
        for path in sorted(pcb.rglob("*")):
            if path.is_symlink():
                raise StudioError("INVALID_INPUT", "PCB dependencies must be local files, not links")
            if path.is_file() and (path.suffix in CONTEXT_EXTENSIONS or path.name in {"sym-lib-table", "fp-lib-table"}
                                   or path.name.startswith("pcb-review-")):
                if not path.resolve().is_relative_to(pcb) or path.stat().st_size > MAX_FILE_BYTES:
                    raise StudioError("INVALID_INPUT", "PCB input is outside the workspace or exceeds 50 MiB")
                result[path.relative_to(pcb).as_posix()] = file_hash(path)
        return result

    def _runs(self, revision):
        path = (self.studio.root / ".mendex" / "pcb-checks" / str(revision.revision_id)).resolve()
        if not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "Check storage escapes the data root")
        return path

    def review_notes(self, revision_id):
        _, _, pcb = self._revision(revision_id)
        paths = list(pcb.glob("pcb-review-*.json"))
        if not paths:
            return ""
        records = []
        for path in paths:
            if not path.resolve().is_relative_to(pcb):
                raise StudioError("INVALID_INPUT", "Review notes escape this revision")
            records.append(json.loads(path.read_text(encoding="utf-8")))
        return max(records, key=lambda item:item["recorded_at"])["notes"]

    def save_review_notes(self, revision_id, notes):
        revision, workspace, pcb = self._revision(revision_id)
        if revision.lifecycle_status != Lifecycle.DRAFT:
            raise StudioError("IMMUTABLE", "Only draft revision notes can be changed")
        if not isinstance(notes, str) or len(notes) > 20000:
            raise StudioError("INVALID_INPUT", "Review notes must be at most 20,000 characters")
        pcb.mkdir(parents=True, exist_ok=True)
        path = pcb / f"pcb-review-{uuid4().hex[:12]}.json"
        with path.open("x", encoding="utf-8") as handle:
            json.dump({"notes":notes, "recorded_at":now().isoformat(),
                       "status":"NOT_EVALUATED", "notice":"Planning notes, not engineering sign-off"}, handle, indent=2)
        return path.relative_to(workspace).as_posix()

    def run_check(self, revision_id, relative_path, operation):
        if operation not in {"erc", "drc"}:
            raise StudioError("INVALID_INPUT", "Choose erc or drc")
        revision, workspace, source = self._design(revision_id, relative_path)
        if source.suffix != (".kicad_sch" if operation == "erc" else ".kicad_pcb"):
            raise StudioError("INVALID_INPUT", "Check type does not match the selected design file")
        pcb = workspace / "pcb"
        run_id = str(uuid4())
        folder = self._runs(revision) / run_id
        inputs = folder / "inputs"
        inputs.mkdir(parents=True, exist_ok=False)
        result = {"run_id": run_id, "revision_id": str(revision.revision_id), "operation": operation,
                  "source": Path(relative_path).as_posix(), "started_at": now().isoformat(),
                  "specification_hash": specification_hash(revision.specification),
                  "status": "NOT_EVALUATED", "diagnostic": "", "tool_version": None,
                  "product_evaluation": "NOT_EVALUATED", "context": {}}
        try:
            context = self._context(pcb)
            for name, sha in context.items():
                destination = inputs / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pcb / name, destination)
                if file_hash(destination) != sha:
                    raise StudioError("CONFLICT", "Design changed while input snapshot was copied")
            result["context"] = context
            staged = inputs / source.relative_to(pcb)
            structure = native_structure(staged)
            result["structure"] = structure
            tool = self.studio.lifecycle.kicad
            if not structure["populated"]:
                result["diagnostic"] = structure["reason"]
            elif not tool.is_available():
                result["diagnostic"] = "KiCad CLI unavailable. Configure/install KiCad before checking."
            else:
                version = subprocess.run([str(tool.kicad_cli), "--version"], capture_output=True,
                                         text=True, timeout=10, shell=False)
                (folder / "version.log").write_text(version.stdout + "\n" + version.stderr, encoding="utf-8")
                result["tool_version"] = version.stdout.strip() if version.returncode == 0 else None
                runner = tool.run_erc if operation == "erc" else tool.run_drc
                checked = runner(staged, folder / f"{operation}.json")
                result.update({key: checked.get(key) for key in ("exit_code", "parsed", "command")})
                (folder / "stdout.log").write_text(checked.get("stdout", ""), encoding="utf-8")
                (folder / "stderr.log").write_text(checked.get("stderr", ""), encoding="utf-8")
                parsed = checked.get("parsed", {})
                if not parsed:
                    result["diagnostic"] = checked.get("diagnostic") or "No evaluable check report"
                elif checked["exit_code"] != 0:
                    result.update(status="ERROR", diagnostic="KiCad process failed; inspect logs")
                elif parsed["total_issues"]:
                    result.update(status="ISSUES_FOUND", diagnostic=f"{parsed['total_issues']} rule-check issues reported")
                else:
                    result.update(status="CLEAR", diagnostic="No issues reported by configured rules; not product or HV approval")
                if any(not (inputs / name).is_file() or file_hash(inputs / name) != sha for name, sha in context.items()):
                    result.update(status="NOT_EVALUATED", diagnostic="KiCad changed input snapshots; check is not accepted")
        except subprocess.TimeoutExpired as exc:
            for name, content in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="replace")
                (folder / f"{name}.log").write_text(content or "", encoding="utf-8")
            result.update(status="ERROR", diagnostic="KiCad check timed out")
        except (OSError, ValueError, StudioError) as exc:
            result.update(status="NOT_EVALUATED", diagnostic=str(exc))
        result["ended_at"] = now().isoformat()
        (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        artifacts = {str(p.relative_to(folder).as_posix()): file_hash(p)
                     for p in folder.rglob("*") if p.is_file()}
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
        (folder / "manifest.sha256").write_text(file_hash(manifest), encoding="ascii")
        return self.read_check(revision_id, run_id)

    def read_check(self, revision_id, run_id):
        revision, _, pcb = self._revision(revision_id)
        try:
            run_id = str(UUID(str(run_id)))
        except ValueError as exc:
            raise StudioError("INVALID_INPUT", "Invalid check identifier") from exc
        folder = self._runs(revision) / run_id
        if not folder.is_dir():
            raise StudioError("NOT_FOUND", "PCB check not found")
        invalid = {"run_id":run_id, "status":"NOT_EVALUATED", "effective_status":"NOT_EVALUATED",
                   "integrity":False, "stale":True, "diagnostic":"Check evidence missing or modified"}
        try:
            manifest = folder / "manifest.json"
            if manifest.is_symlink() or file_hash(manifest) != (folder / "manifest.sha256").read_text().strip():
                return invalid
            artifacts = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(artifacts, dict) or "result.json" not in artifacts:
                return invalid
            for name, sha in artifacts.items():
                path = (folder / name).resolve()
                if not path.is_relative_to(folder) or not path.is_file() or file_hash(path) != sha:
                    return invalid
            result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            stale = result["specification_hash"] != specification_hash(revision.specification)
            stale = stale or self._context(pcb) != result["context"]
            return {**result, "integrity":True, "stale":stale,
                    "effective_status":"NOT_EVALUATED" if stale else result["status"],
                    "evidence_folder":str(folder), "notice":"Rule checks are not HV isolation review or prototype approval"}
        except (OSError, ValueError, KeyError, TypeError, StudioError):
            return invalid

    def list_checks(self, revision_id):
        revision, _, _ = self._revision(revision_id)
        folder = self._runs(revision)
        if not folder.is_dir():
            return []
        return [self.read_check(revision_id, p.name) for p in sorted(folder.iterdir(), reverse=True)
                if p.is_dir() and re.fullmatch(r"[0-9a-f-]{36}", p.name)]

    def open_check_evidence(self, revision_id, run_id):
        from .launch import open_native
        revision, _, _ = self._revision(revision_id)
        self.read_check(revision_id, run_id)  # validates identifier and existence
        folder = (self._runs(revision) / str(UUID(str(run_id)))).resolve()
        if not folder.is_relative_to(self._runs(revision)):
            raise StudioError("INVALID_INPUT", "Evidence folder escapes check storage")
        try:
            open_native(folder)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", str(exc)) from exc
        return str(folder)
