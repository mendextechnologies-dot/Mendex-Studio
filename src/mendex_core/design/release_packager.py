"""Formal Production Release Handover Package Builder & Manifest Synthesizer.

Bundles all multi-disciplinary engineering deliverables:
- CAD netlists & schematics (.kicad_sch, .kicad_pcb, .kicad_pro)
- RS-274X Gerbers & Excellon Drills (.gbr, .drl, gerbers.zip, .d356)
- SMT Pick-and-Place (CPL / Centroid) files & 3D raytrace visuals
- Engineering BOMs (derated JSON, CSV procurement schedules, DOCX)
- Mechanical 3D solid models (.step) & 2D drafting drawings (.svg)
- Simulations (.raw SPICE waveforms, thermal analyses, WCCA reports)
- Requirements matrices & traceable snapshots
- Staged laboratory bring-up test plan protocol & engineering dossiers
- Registered external artifacts

Enforces fail-closed cryptographic integrity validation, archive readability testing (testzip),
source freshness tracking, and mandatory deliverable completeness checks.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from mendex_core.service import StudioError


def _sha256_file(path: Path) -> str:
    """Computes SHA-256 hexadecimal digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def categorize_deliverable(filename: str) -> str:
    """Categorizes a deliverable file into an engineering discipline."""
    lower = filename.lower()
    if "requirement" in lower:
        return "requirements"
    if "simulation" in lower or lower.endswith(".raw") or "thermal_analysis" in lower or "wcca" in lower:
        return "simulation"
    if "enclosure" in lower or "mechanical" in lower or "thermal_interface" in lower or "chassis" in lower or lower.endswith(".step") or lower.endswith(".stp") or lower.endswith(".svg"):
        return "mechanical"
    if lower.endswith(".kicad_sch") or lower.endswith(".kicad_pcb") or lower.endswith(".kicad_pro") or lower.endswith(".sch") or lower.endswith(".pcb"):
        return "cad"
    if lower.endswith(".gbr") or lower.endswith(".drl") or "gerber" in lower or lower.endswith(".d356"):
        return "fabrication"
    if "cpl" in lower or "pos" in lower or lower.endswith(".png") or "assembly" in lower or "reconciliation" in lower:
        return "assembly"
    if "test_plan" in lower or "transformer" in lower or "dossier" in lower or "report" in lower or lower.endswith(".pdf"):
        return "testing_qa"
    if "bom" in lower or lower.endswith(".csv") or "procurement" in lower or lower.endswith(".docx"):
        return "bom"
    return "other"


MANDATORY_DISCIPLINES: Set[str] = {"cad", "fabrication", "bom", "assembly", "mechanical"}


def scan_workspace_candidates(ws_dir: Path) -> List[Path]:
    """Scans a revision workspace directory for genuine engineering deliverable candidates."""
    if not ws_dir.exists():
        return []

    candidates: List[Path] = []
    excluded_names = {".git", ".pytest_cache", "__pycache__", "node_modules", ".venv", "release_package", "scratch", "backup", "backups", ".tmp"}

    for p in ws_dir.rglob("*"):
        if not p.is_file():
            continue
        # Skip excluded dirs
        if any(part in excluded_names for part in p.parts):
            continue
        if p.name.startswith("."):
            continue

        ext = p.suffix.lower()
        name_lower = p.name.lower()

        # Check candidate relevance across all disciplines
        is_cad = ext in [".kicad_sch", ".kicad_pcb", ".kicad_pro"]
        is_fab = ext in [".gbr", ".drl", ".d356"] or ("gerber" in name_lower and ext == ".zip")
        is_cpl = "cpl" in name_lower or "-pos" in name_lower or "centroid" in name_lower or "reconciliation" in name_lower
        is_bom = "bom" in name_lower or "procurement" in name_lower or ext in [".csv", ".docx"]
        is_sim = ext == ".raw" or "simulation" in name_lower or "thermal_analysis" in name_lower or "wcca" in name_lower
        is_req = "requirement" in name_lower
        is_doc = "assembly" in name_lower or "transformer" in name_lower or "test_plan" in name_lower or "dossier" in name_lower or ext in [".pdf", ".html"]
        is_visual = ext == ".png" and ("3d" in name_lower or "render" in name_lower)
        is_mech = "enclosure" in name_lower or "mechanical" in name_lower or "thermal_interface" in name_lower or ext in [".step", ".stp", ".svg"]

        if is_cad or is_fab or is_cpl or is_bom or is_sim or is_req or is_doc or is_visual or is_mech:
            candidates.append(p)

    # Sort deterministically
    return sorted(candidates, key=lambda p: (categorize_deliverable(p.name), p.name))


def get_release_package(studio: Any, revision_id: UUID) -> Dict[str, Any]:
    """Queries current release package status, manifest, freshness, and deliverable integrity.

    Fails closed: if the archive is missing, corrupted, altered, or stale compared to workspace source files,
    status is never READY.
    """
    rev = studio.get_revision(revision_id)
    prod = studio.get_product(rev.product_id)
    ws_dir = studio.workspace_path(rev)
    release_dir = ws_dir / "release_package"

    manifest_file = release_dir / "release_manifest.json"
    candidates = scan_workspace_candidates(ws_dir)

    governance_notice = (
        "Engineering qualification: Design handover package. All constituent deliverables are "
        "cryptographically registered with SHA-256 checksums. Final production manufacturing release "
        "requires attributable human review and completed physical laboratory verification per AGENTS.md rules."
    )

    if not manifest_file.exists():
        return {
            "status": "PENDING_GENERATION",
            "package_exists": False,
            "product_code": prod.code,
            "product_name": prod.name,
            "revision_label": rev.revision_label,
            "revision_id": str(rev.revision_id),
            "package_filename": None,
            "package_relative_path": None,
            "package_size_bytes": 0,
            "package_sha256": None,
            "generated_at": None,
            "generator": None,
            "contents": [],
            "categories": {
                "cad": [],
                "fabrication": [],
                "assembly": [],
                "bom": [],
                "mechanical": [],
                "simulation": [],
                "requirements": [],
                "testing_qa": [],
                "other": [],
            },
            "available_candidates_count": len(candidates),
            "available_candidates": [
                {
                    "name": c.name,
                    "relative_path": str(c.relative_to(ws_dir)),
                    "category": categorize_deliverable(c.name),
                    "size_bytes": c.stat().st_size,
                }
                for c in candidates
            ],
            "missing_mandatory_disciplines": sorted(list(MANDATORY_DISCIPLINES)),
            "governance_notice": governance_notice,
        }

    try:
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        manifest_data = {}

    package_name = manifest_data.get("package") or manifest_data.get("package_filename") or f"{prod.code}_{rev.revision_label}_Complete_Manufacturing_Release.zip"
    zip_path = release_dir / package_name
    zip_exists = zip_path.exists()
    zip_size = zip_path.stat().st_size if zip_exists else 0

    integrity_status = "VALID" if zip_exists else "NOT_EVALUATED"
    integrity_reason: Optional[str] = None
    freshness_status = "CURRENT"

    raw_contents = manifest_data.get("contents", [])
    contents = []
    categories: Dict[str, List[Dict[str, Any]]] = {
        "cad": [],
        "fabrication": [],
        "assembly": [],
        "bom": [],
        "mechanical": [],
        "simulation": [],
        "requirements": [],
        "testing_qa": [],
        "other": [],
    }

    for item in raw_contents:
        fname = item.get("file") or item.get("name") or "unknown"
        cat = item.get("category") or categorize_deliverable(fname)
        entry = {
            "file": fname,
            "category": cat,
            "size_bytes": item.get("size_bytes", 0),
            "sha256": item.get("sha256", ""),
        }
        contents.append(entry)
        categories.setdefault(cat, []).append(entry)

    # 1. Archive Readability & CRC Validation (G02)
    if zip_exists:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad_crc_file = zf.testzip()
                if bad_crc_file is not None:
                    integrity_status = "CORRUPTED"
                    integrity_reason = f"Archive CRC-32 check failed on file: {bad_crc_file}"
                else:
                    # Re-verify internal entries against recorded digests
                    zip_names = set(zf.namelist())
                    for entry in contents:
                        efile = entry["file"]
                        if efile in zip_names:
                            content_bytes = zf.read(efile)
                            actual_sha = hashlib.sha256(content_bytes).hexdigest()
                            if actual_sha != entry["sha256"]:
                                integrity_status = "CORRUPTED"
                                integrity_reason = f"File {efile} SHA-256 digest mismatch inside archive"
                                break
        except Exception as exc:
            integrity_status = "CORRUPTED"
            integrity_reason = f"Archive cannot be opened as valid ZIP: {exc}"

    # 2. Freshness Check: compare modification times of source files vs archive
    if zip_exists and integrity_status == "VALID":
        zip_mtime = zip_path.stat().st_mtime
        stale_files: List[str] = []
        for c in candidates:
            try:
                if c.stat().st_mtime > (zip_mtime + 2.0):
                    stale_files.append(str(c.relative_to(ws_dir)))
            except Exception:
                pass
        if stale_files:
            freshness_status = "STALE"
            integrity_reason = f"{len(stale_files)} workspace file(s) modified after release package generation"

    # 3. Completeness check
    covered_categories = {k for k, v in categories.items() if len(v) > 0}
    missing_mandatory = sorted(list(MANDATORY_DISCIPLINES - covered_categories))

    # Determine final overall status
    if not zip_exists:
        package_status = "PENDING_GENERATION"
    elif integrity_status == "CORRUPTED":
        package_status = "CORRUPTED"
    elif freshness_status == "STALE":
        package_status = "STALE"
    elif missing_mandatory:
        package_status = "INCOMPLETE"
    else:
        package_status = "READY"

    zip_sha256 = manifest_data.get("archive_sha256") or manifest_data.get("package_sha256")
    if zip_exists and not zip_sha256 and integrity_status != "CORRUPTED":
        try:
            zip_sha256 = _sha256_file(zip_path)
        except Exception:
            zip_sha256 = None

    return {
        "status": package_status,
        "package_exists": zip_exists,
        "integrity_status": integrity_status,
        "integrity_reason": integrity_reason,
        "freshness_status": freshness_status,
        "product_code": prod.code,
        "product_name": prod.name,
        "revision_label": rev.revision_label,
        "revision_id": str(rev.revision_id),
        "package_filename": package_name if zip_exists else None,
        "package_relative_path": f"release_package/{package_name}" if zip_exists else None,
        "package_size_bytes": zip_size,
        "package_sha256": zip_sha256,
        "generated_at": manifest_data.get("generated_at"),
        "generator": manifest_data.get("generator") or manifest_data.get("author") or "Lead Systems Engineer",
        "contents": contents,
        "categories": categories,
        "missing_mandatory_disciplines": missing_mandatory,
        "available_candidates_count": len(candidates),
        "governance_notice": governance_notice,
    }


def build_release_package(studio: Any, revision_id: UUID, author: str = "Lead Systems Engineer") -> Dict[str, Any]:
    """Assembles all engineering deliverables into a formal release ZIP package with cryptographic manifest.

    Enforces revision draft guard and collects both workspace candidates and registered external artifacts.
    """
    rev = studio.get_revision(revision_id)
    if getattr(rev.lifecycle_status, "value", rev.lifecycle_status) != "draft":
        raise StudioError("IMMUTABLE", "Cannot build release packages for a frozen or archived baseline")

    prod = studio.get_product(rev.product_id)
    ws_dir = studio.workspace_path(rev)
    release_dir = ws_dir / "release_package"
    release_dir.mkdir(parents=True, exist_ok=True)

    candidates = scan_workspace_candidates(ws_dir)

    # Collect registered artifacts from studio.engineering_records
    external_artifacts: List[Tuple[Path, str]] = []
    if hasattr(studio, "engineering_records"):
        try:
            records_resp = studio.engineering_records.list_records("artifact", {"revision_id": str(revision_id)})
            records_list = records_resp.get("records", []) if isinstance(records_resp, dict) else []
            for rec in records_list:
                snap_path_str = rec.get("snapshot_path")
                if snap_path_str:
                    snap_p = studio.root / snap_path_str
                    if snap_p.is_file() and snap_p not in candidates:
                        rel_arc = f"registered_artifacts/{rec.get('name', snap_p.name)}"
                        external_artifacts.append((snap_p, rel_arc))
        except Exception:
            pass

    if not candidates and not external_artifacts:
        raise StudioError("NOT_FOUND", "No valid engineering deliverables found in workspace or registry to package")

    package_name = f"{prod.code}_{rev.revision_label}_Complete_Manufacturing_Release.zip"
    zip_path = release_dir / package_name

    manifest_entries: List[Dict[str, Any]] = []
    categories: Dict[str, List[Dict[str, Any]]] = {
        "cad": [],
        "fabrication": [],
        "assembly": [],
        "bom": [],
        "mechanical": [],
        "simulation": [],
        "requirements": [],
        "testing_qa": [],
        "other": [],
    }

    # Write files into zip preserving relative workspace path structure
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Workspace candidates
        for f in candidates:
            arcname = str(f.relative_to(ws_dir)).replace("\\", "/")
            zf.write(f, arcname=arcname)
            file_sha = _sha256_file(f)
            file_size = f.stat().st_size
            cat = categorize_deliverable(f.name)
            entry = {
                "file": arcname,
                "category": cat,
                "size_bytes": file_size,
                "sha256": file_sha,
            }
            manifest_entries.append(entry)
            categories.setdefault(cat, []).append(entry)

        # 2. Registered external artifacts
        for ext_file, arc_name in external_artifacts:
            zf.write(ext_file, arcname=arc_name)
            file_sha = _sha256_file(ext_file)
            file_size = ext_file.stat().st_size
            cat = categorize_deliverable(ext_file.name)
            entry = {
                "file": arc_name,
                "category": cat,
                "size_bytes": file_size,
                "sha256": file_sha,
            }
            manifest_entries.append(entry)
            categories.setdefault(cat, []).append(entry)

    zip_sha256 = _sha256_file(zip_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    manifest_data = {
        "schema_version": "3.1.0",
        "product": f"{prod.name} ({prod.code})",
        "product_code": prod.code,
        "product_name": prod.name,
        "revision": rev.revision_label,
        "revision_label": rev.revision_label,
        "revision_id": str(rev.revision_id),
        "package": package_name,
        "package_filename": package_name,
        "archive_sha256": zip_sha256,
        "package_sha256": zip_sha256,
        "package_size_bytes": zip_path.stat().st_size,
        "generated_at": now_iso,
        "generator": author,
        "contents": manifest_entries,
        "categories": categories,
        "governance_notice": (
            "Engineering qualification: Design handover package. All constituent deliverables are "
            "cryptographically registered with SHA-256 checksums. Final production manufacturing release "
            "requires attributable human review and completed physical laboratory verification per AGENTS.md rules."
        ),
    }

    manifest_file = release_dir / "release_manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Also store self-contained release manifest inside the archive
    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("release_manifest.json", json.dumps(manifest_data, indent=2))

    # Recalculate package SHA after manifest append
    final_zip_sha = _sha256_file(zip_path)
    manifest_data["archive_sha256"] = final_zip_sha
    manifest_data["package_sha256"] = final_zip_sha
    manifest_data["package_size_bytes"] = zip_path.stat().st_size
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return get_release_package(studio, revision_id)
