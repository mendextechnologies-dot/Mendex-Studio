"""PCB Layout Geometry & Vector Feature Extraction.

Extracts Edge.Cuts outlines, component footprints, pads, silkscreen geometries,
and bounding boxes from native KiCad 8/9/10 .kicad_pcb layout files.
Shared across Core services (thermal, enclosure) and Desktop presentation.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def extract_pcb_geometry(pcb_path: Optional[Path]) -> Dict[str, Any]:
    """Parses a native .kicad_pcb file into structured vector geometry and bounding box.

    Returns:
        dict containing:
        - "footprints": List of footprint dictionaries with ref, value, x, y, rot, pads, silks, model
        - "edge_cuts": List of Edge.Cuts lines and rects
        - "tracks": List of routed copper track segments
        - "bbox": Dict with min_x, max_x, min_y, max_y, width, height
        - "has_pcb": bool
        - "is_valid": bool
    """
    empty_result: Dict[str, Any] = {
        "footprints": [],
        "edge_cuts": [],
        "tracks": [],
        "bbox": {"min_x": 0.0, "max_x": 0.0, "min_y": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0},
        "has_pcb": False,
        "is_valid": False,
    }

    if not pcb_path or not isinstance(pcb_path, Path) or not pcb_path.is_file():
        return empty_result

    try:
        content = pcb_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return empty_result

    if not content or "(kicad_pcb" not in content:
        return empty_result

    # 1. Edge.Cuts (Board Outline)
    edge_cuts: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)',
        content,
        re.DOTALL,
    ):
        x1, y1, x2, y2 = map(float, m.groups())
        edge_cuts.append({
            "type": "rect",
            "x1": min(x1, x2),
            "y1": min(y1, y2),
            "x2": max(x1, x2),
            "y2": max(y1, y2),
        })

    for m in re.finditer(
        r'\(gr_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)',
        content,
        re.DOTALL,
    ):
        x1, y1, x2, y2 = map(float, m.groups())
        edge_cuts.append({"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    # 2. Copper Tracks
    tracks: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'\(segment\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(width\s+([\d\.\-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
        content,
    ):
        x1, y1, x2, y2, w, layer, net = m.groups()
        tracks.append({
            "x1": float(x1),
            "y1": float(y1),
            "x2": float(x2),
            "y2": float(y2),
            "width": float(w),
            "layer": layer,
            "net": int(net),
        })

    # 3. Footprints
    footprints: List[Dict[str, Any]] = []
    fp_blocks = content.split("(footprint ")
    for block in fp_blocks[1:]:
        header_end = block.find("\n")
        fp_name = block[:header_end].strip().strip('"')

        at_match = re.search(r"\(at\s+([\d\.\-]+)\s+([\d\.\-]+)(?:\s+([\d\.\-]+))?\)", block)
        fx = float(at_match.group(1)) if at_match else 0.0
        fy = float(at_match.group(2)) if at_match else 0.0
        rot = float(at_match.group(3)) if at_match and at_match.group(3) else 0.0

        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        ref = ref_match.group(1) if ref_match else "?"

        val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
        val = val_match.group(1) if val_match else ""

        model_match = re.search(r'\(model\s+"([^"]+)"', block)
        model_path = model_match.group(1) if model_match else None

        # Pads
        pads: List[Dict[str, Any]] = []
        for pm in re.finditer(
            r'\(pad\s+"([^"]+)"\s+(smd|thru_hole)\s+(\w+)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(size\s+([\d\.\-]+)\s+([\d\.\-]+)\)',
            block,
        ):
            pnum, ptype, pshape, px, py, sx, sy = pm.groups()
            pads.append({
                "number": pnum,
                "type": ptype,
                "shape": pshape,
                "ox": float(px),
                "oy": float(py),
                "sx": float(sx),
                "sy": float(sy),
            })

        # Silkscreen inside footprint
        silks: List[Dict[str, Any]] = []
        for sm in re.finditer(r'\(fp_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
            sx1, sy1, sx2, sy2 = map(float, sm.groups())
            silks.append({"type": "line", "x1": sx1, "y1": sy1, "x2": sx2, "y2": sy2})
        for sm in re.finditer(r'\(fp_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
            sx1, sy1, sx2, sy2 = map(float, sm.groups())
            silks.append({"type": "rect", "x1": min(sx1, sx2), "y1": min(sy1, sy2), "x2": max(sx1, sx2), "y2": max(sy1, sy2)})
        for sm in re.finditer(r'\(fp_circle\s+\(center\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
            cx, cy, ex, ey = map(float, sm.groups())
            r = math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2)
            silks.append({"type": "circle", "cx": cx, "cy": cy, "r": r})

        footprints.append({
            "name": fp_name,
            "ref": ref,
            "value": val,
            "x": fx,
            "y": fy,
            "rot": rot,
            "pads": pads,
            "silks": silks,
            "has_3d_model": model_path is not None,
            "model": model_path,
        })

    # 4. Bounding Box
    all_xs: List[float] = [fp["x"] for fp in footprints]
    all_ys: List[float] = [fp["y"] for fp in footprints]
    for e in edge_cuts:
        if e["type"] == "rect":
            all_xs.extend([e["x1"], e["x2"]])
            all_ys.extend([e["y1"], e["y2"]])
        elif e["type"] == "line":
            all_xs.extend([e["x1"], e["x2"]])
            all_ys.extend([e["y1"], e["y2"]])

    if all_xs and all_ys:
        min_x = round(min(all_xs), 2)
        max_x = round(max(all_xs), 2)
        min_y = round(min(all_ys), 2)
        max_y = round(max(all_ys), 2)
        width = round(max(0.0, max_x - min_x), 2)
        height = round(max(0.0, max_y - min_y), 2)
    else:
        min_x = 0.0
        max_x = 0.0
        min_y = 0.0
        max_y = 0.0
        width = 0.0
        height = 0.0

    return {
        "footprints": footprints,
        "edge_cuts": edge_cuts,
        "tracks": tracks,
        "bbox": {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "width": width,
            "height": height,
        },
        "has_pcb": True,
        "is_valid": len(footprints) > 0 or len(edge_cuts) > 0,
    }
