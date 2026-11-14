"""Formal Production Release Handover Package Builder & Manifest Synthesizer.

Bundles all multi-disciplinary engineering deliverables:
- CAD netlists & schematics (.kicad_sch, .kicad_pcb, .kicad_pro)
- RS-274X Gerbers & Excellon Drills (.gbr, .drl, gerbers.zip)
- SMT Pick-and-Place (CPL / Centroid) files & 3D raytrace visuals
- Engineering BOMs (derated JSON & CSV procurement schedules)
- Staged laboratory bring-up test plan protocol
- High-voltage magnetics / transformer drawings
- Engineering dossiers & reports
Generates cryptographic SHA-256 manifest per delivery file and complete release zip.
"""
from __future__ import annotations
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
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
    if lower.endswith(".kicad_sch") or lower.endswith(".kicad_pcb") or lower.endswith(".kicad_pro") or lower.endswith(".sch") or lower.endswith(".pcb"):
        return "cad"
    if lower.endswith(".gbr") or lower.endswith(".drl") or "gerber" in lower:
        return "fabrication"
    if "cpl" in lower or "pos" in lower or lower.endswith(".png") or "assembly" in lower or lower.endswith(".step") or lower.endswith(".stp"):
        return "assembly"
    if "bom" in lower or lower.endswith(".csv") and "cpl" not in lower and "pos" not in lower:
        return "bom"
    if "test_plan" in lower or "transformer" in lower or "dossier" in lower or "report" in lower or lower.endswith(".pdf"):
        return "testing_qa"
    return "other"


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

        # Check candidate relevance
        is_cad = ext in [".kicad_sch", ".kicad_pcb", ".kicad_pro"]
        is_fab = ext in [".gbr", ".drl"] or ("gerber" in name_lower and ext == ".zip")
        is_cpl = "cpl" in name_lower or "-pos" in name_lower or "centroid" in name_lower
        is_bom = name_lower in ["bom.json", "bom.csv"] or "bom_pricing" in name_lower
        is_doc = "assembly" in name_lower or "transformer" in name_lower or "test_plan" in name_lower or ext in [".pdf", ".html"]
        is_visual = ext == ".png" and ("3d" in name_lower or "render" in name_lower)

        if is_cad or is_fab or is_cpl or is_bom or is_doc or is_visual:
            candidates.append(p)

    # Sort deterministically
    return sorted(candidates, key=lambda p: (categorize_deliverable(p.name), p.name))


def get_release_package(studio: Any, revision_id: UUID) -> Dict[str, Any]:
    """Queries current release package status, manifest, and deliverable inventory."""
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
    zip_sha256 = manifest_data.get("archive_sha256") or manifest_data.get("package_sha256")
    if zip_exists and not zip_sha256:
        zip_sha256 = _sha256_file(zip_path)

    raw_contents = manifest_data.get("contents", [])
    contents = []
    categories: Dict[str, List[Dict[str, Any]]] = {
        "cad": [],
        "fabrication": [],
        "assembly": [],
        "bom": [],
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

    return {
        "status": "READY" if zip_exists else "PENDING_GENERATION",
        "package_exists": zip_exists,
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
        "available_candidates_count": len(candidates),
        "governance_notice": governance_notice,
    }


def build_release_package(studio: Any, revision_id: UUID, author: str = "Lead Systems Engineer") -> Dict[str, Any]:
    """Assembles all engineering deliverables into a formal release ZIP package with cryptographic manifest."""
    rev = studio.get_revision(revision_id)
    prod = studio.get_product(rev.product_id)
    ws_dir = studio.workspace_path(rev)
    release_dir = ws_dir / "release_package"
    release_dir.mkdir(parents=True, exist_ok=True)

    candidates = scan_workspace_candidates(ws_dir)
    if not candidates:
        raise StudioError("NOT_FOUND", "No valid engineering deliverables found in workspace to package")

    package_name = f"{prod.code}_{rev.revision_label}_Complete_Manufacturing_Release.zip"
    zip_path = release_dir / package_name

    manifest_entries: List[Dict[str, Any]] = []
    categories: Dict[str, List[Dict[str, Any]]] = {
        "cad": [],
        "fabrication": [],
        "assembly": [],
        "bom": [],
        "testing_qa": [],
        "other": [],
    }

    # Write files into zip preserving relative workspace path structure
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
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

    return get_release_package(studio, revision_id)
