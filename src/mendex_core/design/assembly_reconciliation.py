"""Assembly Readiness & Multi-Discipline BOM-CPL-PCB Reconciliation Engine.

Performs semantic cross-validation across:
1. Bill of Materials (BOM) - designators, quantities, MPNs, and explicit DNP flags
2. Component Placement List (CPL / Centroid / POS) - RefDes, package, coordinates, rotation, layer side
3. PCB Layout Footprints - physical footprints placed on the board

Identifies unplaced parts, unlisted SMT parts, package conflicts, side distribution,
and synthesizes assembly verification scorecards for contract manufacturing handover.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


def _parse_bom_designators(raw_items: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Set[str]]:
    """Extracts designators, attributes, and DNP sets from BOM records."""
    bom_map: Dict[str, Dict[str, Any]] = {}
    dnp_set: Set[str] = set()

    for item in raw_items:
        des_str = str(item.get("designator") or item.get("reference") or item.get("ref") or "").strip()
        if not des_str:
            continue

        desc = str(item.get("description") or "").lower()
        val = str(item.get("value") or "").lower()
        mpn = str(item.get("mpn") or "").lower()
        is_dnp = bool(
            item.get("dnp")
            or "dnp" in desc
            or "do not place" in desc
            or "not fitted" in desc
            or "dnp" in val
            or "dnp" in mpn
        )

        # Split comma/space separated designators (e.g. "R1, R2, R3" or "C1 C2")
        designators = [d.strip().upper() for d in re.split(r"[\s,;]+", des_str) if d.strip()]
        for d in designators:
            if is_dnp:
                dnp_set.add(d)
            bom_map[d] = {
                "designator": d,
                "description": item.get("description", ""),
                "mpn": item.get("mpn", ""),
                "manufacturer": item.get("manufacturer", ""),
                "package": item.get("package") or item.get("footprint", ""),
                "dnp": is_dnp,
            }

    return bom_map, dnp_set


def _parse_cpl_rows(cpl_content_or_path: Union[str, Path, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Extracts pick-and-place rows from CPL CSV text, file, or parsed list."""
    cpl_map: Dict[str, Dict[str, Any]] = {}

    if isinstance(cpl_content_or_path, list):
        for row in cpl_content_or_path:
            ref = str(row.get("Ref") or row.get("Designator") or row.get("ref") or "").strip().upper()
            if ref:
                cpl_map[ref] = {
                    "ref": ref,
                    "val": row.get("Val") or row.get("Value") or row.get("val") or "",
                    "package": row.get("Package") or row.get("Footprint") or row.get("package") or row.get("footprint") or "",
                    "pos_x": float(row.get("PosX") or row.get("Mid X") or row.get("pos_x") or row.get("x") or 0.0),
                    "pos_y": float(row.get("PosY") or row.get("Mid Y") or row.get("pos_y") or row.get("y") or 0.0),
                    "rotation": float(row.get("Rot") or row.get("Rotation") or row.get("rotation") or row.get("rot") or 0.0),
                    "side": str(row.get("Side") or row.get("Layer") or row.get("side") or "top").strip().lower(),
                }
        return cpl_map

    content = ""
    if isinstance(cpl_content_or_path, Path):
        if cpl_content_or_path.is_file():
            content = cpl_content_or_path.read_text(encoding="utf-8", errors="replace")
    elif isinstance(cpl_content_or_path, str):
        if Path(cpl_content_or_path).is_file():
            content = Path(cpl_content_or_path).read_text(encoding="utf-8", errors="replace")
        else:
            content = cpl_content_or_path

    if not content.strip():
        return cpl_map

    # Parse CSV
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        return cpl_map

    reader = csv.DictReader(lines)
    for row in reader:
        # Standard KiCad CPL headers: Ref, Val, Package, PosX, PosY, Rot, Side
        # Or alternative headers: Designator, Mid X, Mid Y, Layer, Rotation
        ref = (
            row.get("Ref")
            or row.get("Designator")
            or row.get("ref")
            or row.get("REFERENCE")
            or ""
        ).strip().upper()
        if not ref:
            continue

        cpl_map[ref] = {
            "ref": ref,
            "val": row.get("Val") or row.get("Value") or "",
            "package": row.get("Package") or row.get("Footprint") or "",
            "pos_x": float(row.get("PosX") or row.get("Mid X") or 0.0),
            "pos_y": float(row.get("PosY") or row.get("Mid Y") or 0.0),
            "rotation": float(row.get("Rot") or row.get("Rotation") or 0.0),
            "side": (row.get("Side") or row.get("Layer") or "top").strip().lower(),
        }

    return cpl_map


def reconcile_assembly(
    bom_input: Union[List[Dict[str, Any]], Path, str],
    cpl_input: Optional[Union[List[Dict[str, Any]], Path, str]] = None,
    pcb_footprints: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Reconciles BOM line items with CPL placement data and physical PCB footprints."""
    # 1. Parse BOM
    raw_bom: List[Dict[str, Any]] = []
    if isinstance(bom_input, list):
        raw_bom = bom_input
    elif isinstance(bom_input, (str, Path)):
        p = Path(bom_input)
        if p.is_file():
            try:
                raw_bom = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass

    if not raw_bom:
        return {
            "reconciliation_status": "NOT_EVALUATED",
            "is_matched": False,
            "error": "BOM data missing or empty",
            "placed_parts_count": 0,
            "unplaced_bom_parts": [],
            "unlisted_cpl_parts": [],
            "dnp_parts": [],
            "package_mismatches": [],
        }

    bom_map, dnp_set = _parse_bom_designators(raw_bom)

    # 2. Parse CPL
    cpl_map: Dict[str, Dict[str, Any]] = {}
    if cpl_input:
        cpl_map = _parse_cpl_rows(cpl_input)

    # 3. Incorporate PCB footprints if provided and CPL was absent
    pcb_refs: Set[str] = set()
    if pcb_footprints:
        for fp in pcb_footprints:
            r = str(fp.get("ref", "")).strip().upper()
            if r and r != "?":
                pcb_refs.add(r)
                if r not in cpl_map and not cpl_input:
                    cpl_map[r] = {
                        "ref": r,
                        "val": fp.get("value", ""),
                        "package": fp.get("name", ""),
                        "pos_x": fp.get("x", 0.0),
                        "pos_y": fp.get("y", 0.0),
                        "rotation": fp.get("rot", 0.0),
                        "side": "top",
                    }

    if not cpl_map:
        return {
            "reconciliation_status": "NOT_EVALUATED",
            "is_matched": False,
            "error": "CPL placement data missing or empty",
            "bom_items_count": len(bom_map),
            "placed_parts_count": 0,
            "unplaced_bom_parts": [k for k in bom_map if k not in dnp_set],
            "unlisted_cpl_parts": [],
            "dnp_parts": sorted(list(dnp_set)),
            "package_mismatches": [],
        }

    # 4. Cross-Reference Evaluation
    bom_active_refs = {ref for ref, itm in bom_map.items() if not itm["dnp"]}
    cpl_refs = set(cpl_map.keys())

    unplaced_bom = sorted(list(bom_active_refs - cpl_refs))
    unlisted_cpl = sorted(list(cpl_refs - set(bom_map.keys())))
    erroneous_dnp_placed = sorted(list(cpl_refs.intersection(dnp_set)))

    # Package checks
    package_mismatches: List[Dict[str, Any]] = []
    for ref in bom_active_refs.intersection(cpl_refs):
        bom_pkg = str(bom_map[ref].get("package") or "").strip().lower()
        cpl_pkg = str(cpl_map[ref].get("package") or "").strip().lower()
        if bom_pkg and cpl_pkg:
            # Check basic package compatibility
            clean_b = re.sub(r"[^a-z0-9]", "", bom_pkg)
            clean_c = re.sub(r"[^a-z0-9]", "", cpl_pkg)
            if clean_b not in clean_c and clean_c not in clean_b and len(clean_b) >= 3 and len(clean_c) >= 3:
                package_mismatches.append({
                    "ref": ref,
                    "bom_package": bom_map[ref]["package"],
                    "cpl_package": cpl_map[ref]["package"],
                })

    # Side distribution
    top_count = sum(1 for p in cpl_map.values() if p.get("side", "top") in ("top", "f.cu", "front"))
    bottom_count = sum(1 for p in cpl_map.values() if p.get("side") in ("bottom", "b.cu", "back"))

    is_matched = len(unplaced_bom) == 0 and len(unlisted_cpl) == 0 and len(erroneous_dnp_placed) == 0

    reconciliation_status = "MATCHED" if is_matched else "DISCREPANCIES_FOUND"

    return {
        "reconciliation_status": reconciliation_status,
        "is_matched": is_matched,
        "bom_items_count": len(bom_map),
        "bom_active_parts_count": len(bom_active_refs),
        "placed_parts_count": len(cpl_refs),
        "dnp_parts_count": len(dnp_set),
        "side_distribution": {
            "top_side_count": top_count,
            "bottom_side_count": bottom_count,
            "double_sided_assembly": bottom_count > 0,
        },
        "unplaced_bom_parts": unplaced_bom,
        "unlisted_cpl_parts": unlisted_cpl,
        "erroneous_dnp_in_cpl": erroneous_dnp_placed,
        "dnp_parts": sorted(list(dnp_set)),
        "package_mismatches": package_mismatches,
        "assembly_guidelines": {
            "stencil_recommended_thickness_um": 127,  # 5 mil standard
            "reflow_profile": "J-STD-020E Lead-Free (SAC305 peak 245-250°C)",
            "msl_sensitive_parts": [
                itm["designator"] for itm in bom_map.values()
                if any(k in str(itm.get("description", "")).lower() for k in ["ic", "driver", "mcu", "qfn", "soic"])
            ],
            "polarity_critical_parts": [
                itm["designator"] for itm in bom_map.values()
                if any(k in str(itm.get("description", "")).lower() for k in ["diode", "tantalum", "electrolytic", "led", "sic"])
            ],
        },
        "governance_note": "Draft assembly reconciliation only. SMT line setup and component feeder verification require production engineer review per AGENTS.md.",
    }
