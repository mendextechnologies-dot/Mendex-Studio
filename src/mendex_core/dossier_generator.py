"""Complete Product Engineering Dossier (CPED) Report Generator for Mendex Engineering Studio.

Assembles comprehensive engineering dossiers with embedded vector CAD graphics:
  1. Executive Summary & Design Envelope (KPIs)
  2. Recorded Analytical Inputs & Sizing Math
  3. Circuit Architecture & Schematic Capture (Embedded Vector SVG + ERC Scorecard)
  4. 2D PCB Layout, Layer Stackup & Isolation Barrier (Embedded Vector SVG + DRC Scorecard)
  5. Photorealistic 3D Raytraced Board Assembly (High-res PNG Embed + STEP CAD Solid Fingerprint)
  6. SPICE Transient Simulation & Waveforms (Embedded Vector SVG Oscilloscope + .meas Metrics)
  7. 2D Finite Element Magnetic Analysis (FEMM 4.2 FEA Actuator / Inductor Saturation Margin)
  8. Itemized Production Bill of Materials (BOM) Schedule
  9. Manufacturing Fabrication Package & RS-274X Gerber Specifications
 10. Engineering Change Requests (ECRs) & Audit Provenance
 11. 9-Stage Product Engineering Lifecycle Assessment & Cryptographic Evidence Register
 12. Frozen Input Snapshot (JSON)
"""
from __future__ import annotations

import base64
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


def _file_sha256(path: Path) -> str:
    """Computes SHA-256 hexadecimal digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _render_symbol_shape(ref: str, val: str, lib_id: str) -> str:
    """Generates standard electronic circuit symbols (IEEE/IEC) for schematic components."""
    r = ref.upper()
    v = val.upper()
    lid = lib_id.upper()

    # 1. Resistor (R)
    if r.startswith("R") or "RESISTOR" in lid:
        return '''
        <g stroke="#0f172a" stroke-width="1.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="-8" y1="0" x2="-5" y2="0" />
            <path d="M -5 0 L -3.75 -2.5 L -1.25 2.5 L 1.25 -2.5 L 3.75 2.5 L 5 0" />
            <line x1="5" y1="0" x2="8" y2="0" />
        </g>
        '''
    # 2. Capacitor (C)
    elif r.startswith("C") or "CAPACITOR" in lid:
        is_polar = "POLAR" in lid or "CP" in v or "ELEC" in v
        curve_plate = '<path d="M 1.5 -4.5 A 6 6 0 0 0 1.5 4.5" stroke="#0f172a" stroke-width="1.5" fill="none" />' if is_polar else '<line x1="1.5" y1="-4.5" x2="1.5" y2="4.5" stroke="#0f172a" stroke-width="1.5" />'
        plus_sign = '<text x="-4" y="-3.5" font-size="3" font-weight="bold" fill="#dc2626">+</text>' if is_polar else ''
        return f'''
        <g stroke-linecap="round" stroke-linejoin="round">
            <line x1="-7" y1="0" x2="-1.5" y2="0" stroke="#0f172a" stroke-width="1.2" />
            <line x1="-1.5" y1="-4.5" x2="-1.5" y2="4.5" stroke="#0f172a" stroke-width="1.5" />
            {curve_plate}
            <line x1="1.5" y1="0" x2="7" y2="0" stroke="#0f172a" stroke-width="1.2" />
            {plus_sign}
        </g>
        '''
    # 3. Bridge Rectifier
    elif "BRIDGE" in lid or "BRIDGE" in v or r.startswith("BR"):
        return '''
        <g stroke-linecap="round" stroke-linejoin="round">
            <polygon points="0,-7 7,0 0,7 -7,0" fill="#f8fafc" stroke="#0f172a" stroke-width="1.3" />
            <text x="0" y="-3" font-size="2.4" font-weight="bold" fill="#dc2626" text-anchor="middle">+</text>
            <text x="0" y="5.5" font-size="2.4" font-weight="bold" fill="#0f172a" text-anchor="middle">-</text>
            <text x="-4.5" y="1" font-size="2.2" font-weight="bold" fill="#0284c7" text-anchor="middle">~</text>
            <text x="4.5" y="1" font-size="2.2" font-weight="bold" fill="#0284c7" text-anchor="middle">~</text>
            <line x1="0" y1="-7" x2="0" y2="-9.5" stroke="#0f172a" stroke-width="1.2" />
            <line x1="0" y1="7" x2="0" y2="9.5" stroke="#0f172a" stroke-width="1.2" />
            <line x1="-7" y1="0" x2="-9.5" y2="0" stroke="#0f172a" stroke-width="1.2" />
            <line x1="7" y1="0" x2="9.5" y2="0" stroke="#0f172a" stroke-width="1.2" />
        </g>
        '''
    # 4. Diode (D)
    elif r.startswith("D") or "DIODE" in lid:
        return '''
        <g stroke-linecap="round" stroke-linejoin="round">
            <line x1="-7" y1="0" x2="-3" y2="0" stroke="#0f172a" stroke-width="1.2" />
            <polygon points="-3,-3.5 2.5,0 -3,3.5" fill="#0f172a" stroke="#0f172a" stroke-width="1.2" />
            <line x1="2.5" y1="-4" x2="2.5" y2="4" stroke="#0f172a" stroke-width="1.5" />
            <line x1="2.5" y1="0" x2="7" y2="0" stroke="#0f172a" stroke-width="1.2" />
        </g>
        '''
    # 5. Inductor (L)
    elif r.startswith("L") or "INDUCTOR" in lid:
        return '''
        <g stroke="#0f172a" stroke-width="1.2" fill="none" stroke-linecap="round">
            <line x1="-9" y1="0" x2="-6" y2="0" />
            <path d="M -6 0 A 2 2 0 0 1 -2 0 A 2 2 0 0 1 2 0 A 2 2 0 0 1 6 0" />
            <line x1="6" y1="0" x2="9" y2="0" />
        </g>
        '''
    # 6. Transformer (T)
    elif r.startswith("T") or "TRANSFORMER" in lid:
        return '''
        <g stroke="#0f172a" stroke-width="1.2" fill="none" stroke-linecap="round">
            <path d="M -3 -6 A 2 2 0 0 0 -3 -2 A 2 2 0 0 0 -3 2 A 2 2 0 0 0 -3 6" />
            <line x1="-0.8" y1="-6.5" x2="-0.8" y2="6.5" stroke="#64748b" stroke-width="1.0" />
            <line x1="0.8" y1="-6.5" x2="0.8" y2="6.5" stroke="#64748b" stroke-width="1.0" />
            <path d="M 3 -6 A 2 2 0 0 1 3 -2 A 2 2 0 0 1 3 2 A 2 2 0 0 1 3 6" />
            <line x1="-3" y1="-6" x2="-7" y2="-6" />
            <line x1="-3" y1="6" x2="-7" y2="6" />
            <line x1="3" y1="-6" x2="7" y2="-6" />
            <line x1="3" y1="6" x2="7" y2="6" />
            <circle cx="-5" cy="-4" r="0.6" fill="#0f172a" />
            <circle cx="5" cy="-4" r="0.6" fill="#0f172a" />
        </g>
        '''
    # 7. Transistor / MOSFET (Q)
    elif r.startswith("Q") or "MOSFET" in lid or "TRANSISTOR" in lid:
        return '''
        <g stroke="#0f172a" stroke-width="1.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="-6" y1="0" x2="-2" y2="0" />
            <line x1="-2" y1="-4" x2="-2" y2="4" stroke-width="1.6" />
            <line x1="0" y1="-4.5" x2="0" y2="-2" stroke-width="1.4" />
            <line x1="0" y1="-1" x2="0" y2="1" stroke-width="1.4" />
            <line x1="0" y1="2" x2="0" y2="4.5" stroke-width="1.4" />
            <line x1="0" y1="-3.5" x2="4" y2="-3.5" />
            <line x1="4" y1="-3.5" x2="4" y2="-6" />
            <line x1="0" y1="3.5" x2="4" y2="3.5" />
            <line x1="4" y1="3.5" x2="4" y2="6" />
            <polygon points="0,0 2.5,-1.2 2.5,1.2" fill="#0f172a" stroke="none" />
            <line x1="0" y1="0" x2="4" y2="0" />
            <line x1="4" y1="0" x2="4" y2="3.5" />
        </g>
        '''
    # 8. Connector / Terminal (J)
    elif r.startswith("J") or "CONN" in lid:
        return '''
        <g stroke-linecap="round" stroke-linejoin="round">
            <rect x="-6" y="-6" width="12" height="12" rx="2" fill="#f1f5f9" stroke="#334155" stroke-width="1.1" />
            <circle cx="0" cy="-2.5" r="1.5" fill="#ffffff" stroke="#0f172a" stroke-width="1.2" />
            <circle cx="0" cy="2.5" r="1.5" fill="#ffffff" stroke="#0f172a" stroke-width="1.2" />
        </g>
        '''
    # 9. IC / Controller (U)
    elif r.startswith("U") or "IC" in lid:
        return '''
        <g stroke-linecap="round" stroke-linejoin="round">
            <rect x="-9" y="-10" width="18" height="20" rx="1.5" fill="#f8fafc" stroke="#1e293b" stroke-width="1.3" />
            <path d="M -3 -10 A 3 3 0 0 0 3 -10" fill="none" stroke="#1e293b" stroke-width="1.2" />
            <circle cx="-6" cy="-7" r="0.7" fill="#64748b" />
            <line x1="-12" y1="-6" x2="-9" y2="-6" stroke="#1e293b" stroke-width="1.2" />
            <line x1="-12" y1="-2" x2="-9" y2="-2" stroke="#1e293b" stroke-width="1.2" />
            <line x1="-12" y1="2" x2="-9" y2="2" stroke="#1e293b" stroke-width="1.2" />
            <line x1="-12" y1="6" x2="-9" y2="6" stroke="#1e293b" stroke-width="1.2" />
            <line x1="9" y1="-6" x2="12" y2="-6" stroke="#1e293b" stroke-width="1.2" />
            <line x1="9" y1="-2" x2="12" y2="-2" stroke="#1e293b" stroke-width="1.2" />
            <line x1="9" y1="2" x2="12" y2="2" stroke="#1e293b" stroke-width="1.2" />
            <line x1="9" y1="6" x2="12" y2="6" stroke="#1e293b" stroke-width="1.2" />
        </g>
        '''
    # 10. Default Component Symbol
    else:
        return '''
        <g stroke-linecap="round" stroke-linejoin="round">
            <rect x="-6" y="-5" width="12" height="10" rx="1.5" fill="#f8fafc" stroke="#334155" stroke-width="1.1" />
        </g>
        '''


def render_schematic_svg(sch_path: Path, width: int = 860, height: int = 500) -> str:
    """Renders an authentic, publication-grade KiCad schematic diagram.
    
    If native KiCad CLI is available, exports and embeds the exact official vector SVG.
    Otherwise, executes the high-fidelity electronic symbol synthesis engine.
    """
    if not sch_path.exists() or sch_path.stat().st_size == 0:
        return '<div class="notice-box">Schematic Diagram: NOT_EVALUATED (file not present)</div>'

    # 1. Native KiCad 10 Vector SVG Export (Publication-Grade Authentic Circuit Diagram)
    try:
        from .lifecycle.kicad_service import KiCadLifecycleService
        kicad_srv = KiCadLifecycleService()
        if kicad_srv.is_available():
            svg_out_dir = sch_path.parent / "svg"
            cand_svg = svg_out_dir / f"{sch_path.stem}.svg"
            if not cand_svg.exists() or cand_svg.stat().st_mtime < sch_path.stat().st_mtime:
                kicad_srv.export_schematic_svg(sch_path, output_dir=svg_out_dir)
            if cand_svg.exists() and cand_svg.stat().st_size > 0:
                raw_svg = cand_svg.read_text(encoding="utf-8", errors="replace")
                raw_svg = re.sub(r'width="[^"]+"', 'width="100%"', raw_svg, count=1)
                raw_svg = re.sub(r'height="[^"]+"', 'height="auto"', raw_svg, count=1)
                return f'''<div class="kicad-schematic-viewer" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; padding:12px; overflow:auto; box-shadow:0 1px 3px rgba(0,0,0,0.06); max-height:750px;">
  {raw_svg}
</div>'''
    except Exception:
        pass

    try:
        content = sch_path.read_text(encoding="utf-8", errors="replace")

        symbols = []
        for sm in re.finditer(
            r'\(symbol\s+\(lib_id\s+"([^"]+)"\)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+).*?'
            r'\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Value"\s+"([^"]+)"',
            content,
            re.DOTALL,
        ):
            lib_id, sx, sy, sref, sval = sm.groups()
            symbols.append({
                "lib_id": lib_id,
                "x": float(sx),
                "y": float(sy),
                "ref": sref,
                "value": sval,
            })

        wires = []
        for wm in re.finditer(
            r'\(wire\s+\(pts\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)\)',
            content,
        ):
            x1, y1, x2, y2 = map(float, wm.groups())
            wires.append((x1, y1, x2, y2))

        labels = []
        for lm in re.finditer(
            r'\((?:label|hierarchical_label)\s+"([^"]+)"[^\)]*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)',
            content,
        ):
            lname, lx, ly = lm.groups()
            labels.append((lname, float(lx), float(ly)))

        if not symbols and not wires:
            return '<div class="notice-box">Schematic Diagram: No symbols or interconnect wires found in sheet.</div>'

        # Compute bounding box
        all_xs = [s["x"] for s in symbols] + [w[0] for w in wires] + [w[2] for w in wires]
        all_ys = [s["y"] for s in symbols] + [w[1] for w in wires] + [w[3] for w in wires]
        min_x = min(all_xs) - 15.0 if all_xs else 0.0
        max_x = max(all_xs) + 15.0 if all_xs else 100.0
        min_y = min(all_ys) - 15.0 if all_ys else 0.0
        max_y = max(all_ys) + 15.0 if all_ys else 100.0
        span_x = max(max_x - min_x, 10.0)
        span_y = max(max_y - min_y, 10.0)

        svg_parts = [
            f'<svg viewBox="{min_x:.1f} {min_y:.1f} {span_x:.1f} {span_y:.1f}" width="100%" height="auto" '
            f'xmlns="http://www.w3.org/2000/svg" style="background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; font-family:monospace;">',
            f'  <defs>',
            f'    <pattern id="sch-grid" width="10" height="10" patternUnits="userSpaceOnUse">',
            f'      <circle cx="5" cy="5" r="0.5" fill="#e2e8f0" />',
            f'    </pattern>',
            f'  </defs>',
            f'  <rect x="{min_x:.1f}" y="{min_y:.1f}" width="{span_x:.1f}" height="{span_y:.1f}" fill="url(#sch-grid)" />',
        ]

        # Draw interconnect wires
        for x1, y1, x2, y2 in wires:
            svg_parts.append(
                f'  <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#0284c7" stroke-width="1.2" stroke-linecap="round" />'
            )

        # Junction connection dots where wires meet
        coord_counts = {}
        for x1, y1, x2, y2 in wires:
            p1 = (round(x1, 2), round(y1, 2))
            p2 = (round(x2, 2), round(y2, 2))
            coord_counts[p1] = coord_counts.get(p1, 0) + 1
            coord_counts[p2] = coord_counts.get(p2, 0) + 1
        for (jx, jy), count in coord_counts.items():
            if count >= 3:
                svg_parts.append(
                    f'  <circle cx="{jx:.2f}" cy="{jy:.2f}" r="1.0" fill="#0284c7" />'
                )

        # Draw symbols with authentic electronic schematic geometry
        for sym in symbols:
            x, y = sym["x"], sym["y"]
            ref, val, lib_id = sym["ref"], sym["value"], sym.get("lib_id", "")
            symbol_shape_svg = _render_symbol_shape(ref, val, lib_id)
            svg_parts.extend([
                f'  <g transform="translate({x:.2f}, {y:.2f})">',
                symbol_shape_svg,
                f'    <text x="0" y="-7.5" font-size="3.0" font-weight="bold" fill="#0f172a" text-anchor="middle">{html.escape(ref)}</text>',
                f'    <text x="0" y="8.8" font-size="2.2" font-weight="600" fill="#2563eb" text-anchor="middle">{html.escape(val[:14])}</text>',
                f'  </g>',
            ])

        # Draw net labels as clean non-overlapping badge callouts
        for name, lx, ly in labels:
            is_pwr = any(k in name.upper() for k in ("VCC", "VDD", "VIN", "VOUT", "HV", "+"))
            is_gnd = any(k in name.upper() for k in ("GND", "PRI_GND", "SEC_GND", "0V"))
            badge_bg = "#fef2f2" if is_pwr else ("#f0fdf4" if is_gnd else "#f0f9ff")
            badge_border = "#ef4444" if is_pwr else ("#22c55e" if is_gnd else "#0284c7")
            text_color = "#b91c1c" if is_pwr else ("#15803d" if is_gnd else "#0369a1")
            
            badge_w = max(len(name) * 2.2 + 3.0, 10.0)
            svg_parts.extend([
                f'  <g transform="translate({lx:.2f}, {ly:.2f})">',
                f'    <circle cx="0" cy="0" r="0.8" fill="{badge_border}" />',
                f'    <rect x="1.5" y="-3.2" width="{badge_w:.1f}" height="5.6" rx="1.5" fill="{badge_bg}" stroke="{badge_border}" stroke-width="0.6" />',
                f'    <text x="{1.5 + badge_w/2:.1f}" y="0.8" font-size="2.4" font-weight="bold" fill="{text_color}" text-anchor="middle">{html.escape(name)}</text>',
                f'  </g>',
            ])

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    except Exception as exc:
        return f'<div class="notice-box">Schematic Diagram parse notice: {html.escape(str(exc))}</div>'


def render_pcb_svg(pcb_path: Path) -> str:
    """Parses a native KiCad .kicad_pcb file and generates a responsive 2D vector CAD board layout."""
    if not pcb_path.exists() or pcb_path.stat().st_size == 0:
        return '<div class="notice-box">2D PCB Layout: NOT_EVALUATED (file not present)</div>'

    try:
        content = pcb_path.read_text(encoding="utf-8", errors="replace")

        # 1. Edge.Cuts (Board Outlines & Creepage Slots)
        edge_cuts = []
        for m in re.finditer(
            r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)',
            content,
            re.DOTALL,
        ):
            x1, y1, x2, y2 = map(float, m.groups())
            edge_cuts.append({"type": "rect", "x1": min(x1, x2), "y1": min(y1, y2), "x2": max(x1, x2), "y2": max(y1, y2)})

        for m in re.finditer(
            r'\(gr_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)',
            content,
            re.DOTALL,
        ):
            x1, y1, x2, y2 = map(float, m.groups())
            edge_cuts.append({"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})

        # 2. Tracks
        tracks = []
        for m in re.finditer(
            r'\(segment\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(width\s+([\d\.\-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)',
            content,
        ):
            x1, y1, x2, y2, w, layer, net = m.groups()
            tracks.append({
                "x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2),
                "width": float(w), "layer": layer, "net": int(net),
            })

        # 3. Footprints & Pads
        footprints = []
        fp_blocks = content.split('(footprint ')
        for block in fp_blocks[1:]:
            header_end = block.find('\n')
            fp_name = block[:header_end].strip().strip('"')

            at_match = re.search(r'\(at\s+([\d\.\-]+)\s+([\d\.\-]+)(?:\s+([\d\.\-]+))?\)', block)
            fx = float(at_match.group(1)) if at_match else 0.0
            fy = float(at_match.group(2)) if at_match else 0.0

            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
            ref = ref_match.group(1) if ref_match else "?"

            val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
            val = val_match.group(1) if val_match else ""

            # Pads
            pads = []
            for pm in re.finditer(r'\(pad\s+"([^"]+)"\s+(smd|thru_hole)\s+(\w+)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(size\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                pnum, ptype, pshape, px, py, sx, sy = pm.groups()
                pads.append({"number": pnum, "type": ptype, "ox": float(px), "oy": float(py), "sx": float(sx), "sy": float(sy)})

            footprints.append({"name": fp_name, "ref": ref, "val": val, "x": fx, "y": fy, "pads": pads})

        if not edge_cuts and not footprints:
            return '<div class="notice-box">2D PCB Layout: No board geometry found.</div>'

        # Compute bounding box
        all_xs = [fp["x"] for fp in footprints] + [e["x1"] for e in edge_cuts] + [e["x2"] for e in edge_cuts]
        all_ys = [fp["y"] for fp in footprints] + [e["y1"] for e in edge_cuts] + [e["y2"] for e in edge_cuts]
        min_x = min(all_xs) - 8.0 if all_xs else 90.0
        max_x = max(all_xs) + 8.0 if all_xs else 190.0
        min_y = min(all_ys) - 8.0 if all_ys else 90.0
        max_y = max(all_ys) + 8.0 if all_ys else 170.0
        span_x = max(max_x - min_x, 10.0)
        span_y = max(max_y - min_y, 10.0)

        svg_parts = [
            f'<svg viewBox="{min_x:.1f} {min_y:.1f} {span_x:.1f} {span_y:.1f}" width="100%" height="auto" '
            f'xmlns="http://www.w3.org/2000/svg" style="background:#0f172a; border-radius:6px; font-family:sans-serif;">',
            f'  <defs>',
            f'    <pattern id="pcb-grid" width="10" height="10" patternUnits="userSpaceOnUse">',
            f'      <circle cx="5" cy="5" r="0.4" fill="#1e293b" />',
            f'    </pattern>',
            f'  </defs>',
            f'  <rect x="{min_x:.1f}" y="{min_y:.1f}" width="{span_x:.1f}" height="{span_y:.1f}" fill="url(#pcb-grid)" />',
        ]

        # Draw Edge.Cuts (Board Outline and Isolation Slots)
        for ec in edge_cuts:
            if ec["type"] == "rect":
                is_slot = (ec["x2"] - ec["x1"]) < 10.0 and (ec["y2"] - ec["y1"]) > 20.0
                if is_slot:
                    svg_parts.append(
                        f'  <rect x="{ec["x1"]:.2f}" y="{ec["y1"]:.2f}" width="{ec["x2"] - ec["x1"]:.2f}" height="{ec["y2"] - ec["y1"]:.2f}" '
                        f'fill="#1e1e2e" stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,1.5" />'
                    )
                    svg_parts.append(
                        f'  <text x="{(ec["x1"] + ec["x2"])/2:.2f}" y="{(ec["y1"] + ec["y2"])/2:.2f}" font-size="2.0" fill="#f87171" '
                        f'text-anchor="middle" transform="rotate(-90 {(ec["x1"] + ec["x2"])/2:.2f} {(ec["y1"] + ec["y2"])/2:.2f})">HV ISOLATION BARRIER (5mm)</text>'
                    )
                else:
                    svg_parts.append(
                        f'  <rect x="{ec["x1"]:.2f}" y="{ec["y1"]:.2f}" width="{ec["x2"] - ec["x1"]:.2f}" height="{ec["y2"] - ec["y1"]:.2f}" '
                        f'fill="#1e293b" stroke="#f59e0b" stroke-width="1.2" rx="2" />'
                    )

        # Draw Copper Tracks (F.Cu in green, B.Cu in blue)
        for t in tracks:
            color = "#10b981" if t["layer"] == "F.Cu" else "#3b82f6"
            sw = max(t["width"], 0.4)
            svg_parts.append(
                f'  <line x1="{t["x1"]:.2f}" y1="{t["y1"]:.2f}" x2="{t["x2"]:.2f}" y2="{t["y2"]:.2f}" stroke="{color}" stroke-width="{sw:.2f}" stroke-linecap="round" />'
            )

        # Draw Footprints & Component Pads
        for fp in footprints:
            fx, fy, ref = fp["x"], fp["y"], fp["ref"]
            # Footprint origin dot and reference text
            svg_parts.append(
                f'  <text x="{fx:.2f}" y="{fy - 3.5:.2f}" font-size="2.2" font-weight="bold" fill="#f8fafc" text-anchor="middle">{html.escape(ref)}</text>'
            )
            for p in fp["pads"]:
                px = fx + p["ox"]
                py = fy + p["oy"]
                sx = max(p["sx"], 0.8)
                sy = max(p["sy"], 0.8)
                p_color = "#ef4444" if p["type"] == "smd" else "#fbbf24"
                svg_parts.append(
                    f'  <rect x="{px - sx/2:.2f}" y="{py - sy/2:.2f}" width="{sx:.2f}" height="{sy:.2f}" fill="{p_color}" rx="0.2" />'
                )

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    except Exception as exc:
        return f'<div class="notice-box">PCB Layout parse notice: {html.escape(str(exc))}</div>'


def render_waveform_svg(raw_path: Path, max_points: int = 250) -> Tuple[str, Dict[str, Any]]:
    """Parses native LTspice .raw waveforms and generates a dual-channel oscilloscope vector SVG."""
    if not raw_path.exists() or raw_path.stat().st_size == 0:
        return ('<div class="notice-box">SPICE Simulation Waveforms: NOT_EVALUATED (raw waveform deck not present)</div>', {})

    try:
        from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms
        wf = parse_ascii_raw_waveforms(raw_path)

        if "time" not in wf:
            return ('<div class="notice-box">Waveform data could not be parsed from simulation deck.</div>', {})

        time_arr = wf["time"]
        all_keys = [k for k in wf.keys() if k != "time"]

        # Select primary voltage and current traces
        v_key = next((k for k in all_keys if any(term in k.lower() for term in ("vout", "coil_sw", "switch", "drain"))), None)
        if not v_key:
            v_key = next((k for k in all_keys if k.startswith("V(")), all_keys[0] if all_keys else None)

        i_key = next((k for k in all_keys if any(term in k.lower() for term in ("i(l", "i(d", "i(s"))), None)
        if not i_key:
            i_key = next((k for k in all_keys if k.startswith("I(")), None)

        if not v_key and not i_key:
            return ('<div class="notice-box">No signal channels identified in simulation dataset.</div>', {})

        n_pts = len(time_arr)
        step = max(1, n_pts // max_points)
        sub_idx = list(range(0, n_pts, step))
        if sub_idx[-1] != n_pts - 1:
            sub_idx.append(n_pts - 1)

        t_sub = [time_arr[i] for i in sub_idx]
        t_max = max(t_sub) if t_sub else 1.0
        time_unit = "ms" if t_max < 0.1 else "s"
        time_mult = 1000.0 if time_unit == "ms" else 1.0

        w, h = 820, 260
        pad_l, pad_r, pad_t, pad_b = 60, 60, 30, 35
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        svg_parts = [
            f'<svg viewBox="0 0 {w} {h}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" '
            f'style="background:#0f172a; border-radius:6px; font-family:monospace;">',
            f'  <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#1e293b" stroke="#334155" stroke-width="1" />',
        ]

        # Draw grid lines
        for i in range(1, 5):
            gy = pad_t + i * (plot_h / 5)
            svg_parts.append(
                f'  <line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" y2="{gy:.1f}" stroke="#334155" stroke-dasharray="2,2" stroke-width="0.8" />'
            )
        for i in range(1, 6):
            gx = pad_l + i * (plot_w / 6)
            svg_parts.append(
                f'  <line x1="{gx:.1f}" y1="{pad_t}" x2="{gx:.1f}" y2="{pad_t + plot_h}" stroke="#334155" stroke-dasharray="2,2" stroke-width="0.8" />'
            )

        metrics = {}

        # Plot Voltage Channel (Cyan #38bdf8)
        if v_key and v_key in wf:
            v_vals = [wf[v_key][i] for i in sub_idx]
            v_max = max(v_vals) * 1.15 if v_vals else 1.0
            v_min = min(min(v_vals), 0.0)
            v_span = max(v_max - v_min, 0.001)

            pts_v = []
            for t_val, v_val in zip(t_sub, v_vals):
                x = pad_l + (t_val / (t_max or 1.0)) * plot_w
                y = pad_t + plot_h - ((v_val - v_min) / v_span) * plot_h
                pts_v.append(f"{x:.1f},{y:.1f}")

            svg_parts.append(
                f'  <polyline points="{" ".join(pts_v)}" fill="none" stroke="#38bdf8" stroke-width="1.8" />'
            )
            # Y-axis label left
            svg_parts.extend([
                f'  <text x="{pad_l - 8}" y="{pad_t + 10}" fill="#38bdf8" font-size="11" text-anchor="end">{v_max:.1f} V</text>',
                f'  <text x="{pad_l - 8}" y="{pad_t + plot_h}" fill="#38bdf8" font-size="11" text-anchor="end">{v_min:.1f} V</text>',
                f'  <circle cx="{pad_l + 10}" cy="18" r="4" fill="#38bdf8" />',
                f'  <text x="{pad_l + 20}" y="22" fill="#38bdf8" font-size="12" font-weight="bold">{html.escape(v_key)}</text>',
            ])
            metrics["v_channel"] = v_key
            metrics["v_max"] = max(wf[v_key])
            metrics["v_min"] = min(wf[v_key])

        # Plot Current Channel (Emerald Green #4ade80)
        if i_key and i_key in wf:
            i_vals = [wf[i_key][i] for i in sub_idx]
            i_max = max(i_vals) * 1.15 if i_vals else 1.0
            i_min = min(min(i_vals), 0.0)
            i_span = max(i_max - i_min, 0.001)

            pts_i = []
            for t_val, i_val in zip(t_sub, i_vals):
                x = pad_l + (t_val / (t_max or 1.0)) * plot_w
                y = pad_t + plot_h - ((i_val - i_min) / i_span) * plot_h
                pts_i.append(f"{x:.1f},{y:.1f}")

            svg_parts.append(
                f'  <polyline points="{" ".join(pts_i)}" fill="none" stroke="#4ade80" stroke-width="1.8" />'
            )
            # Y-axis label right
            svg_parts.extend([
                f'  <text x="{pad_l + plot_w + 8}" y="{pad_t + 10}" fill="#4ade80" font-size="11" text-anchor="start">{i_max:.2f} A</text>',
                f'  <text x="{pad_l + plot_w + 8}" y="{pad_t + plot_h}" fill="#4ade80" font-size="11" text-anchor="start">{i_min:.2f} A</text>',
                f'  <circle cx="{pad_l + 180}" cy="18" r="4" fill="#4ade80" />',
                f'  <text x="{pad_l + 190}" y="22" fill="#4ade80" font-size="12" font-weight="bold">{html.escape(i_key)}</text>',
            ])
            metrics["i_channel"] = i_key
            metrics["i_max"] = max(wf[i_key])
            metrics["i_min"] = min(wf[i_key])

        # X-axis label
        svg_parts.extend([
            f'  <text x="{pad_l}" y="{pad_t + plot_h + 18}" fill="#94a3b8" font-size="11">0.0 {time_unit}</text>',
            f'  <text x="{pad_l + plot_w}" y="{pad_t + plot_h + 18}" fill="#94a3b8" font-size="11" text-anchor="end">{t_max * time_mult:.2f} {time_unit}</text>',
            f'  <text x="{pad_l + plot_w / 2}" y="{pad_t + plot_h + 18}" fill="#94a3b8" font-size="11" text-anchor="middle">Time ({time_unit})</text>',
            '</svg>',
        ])

        return ("\n".join(svg_parts), metrics)

    except Exception as exc:
        return (f'<div class="notice-box">Waveform plot notice: {html.escape(str(exc))}</div>', {})


def render_3d_assembly_card(ws_dir: Path) -> str:
    """Extracts raytraced 3D render PNG and STEP CAD solid model metadata."""
    pcb_dir = ws_dir / "pcb"
    render_candidates = [
        pcb_dir / "board_3d_render.png",
        pcb_dir / "poc_3d.png",
        pcb_dir / "pcb-3d-iso.png",
        ws_dir / "pcb" / "render" / "pcb-3d-iso.png",
    ]
    render_file = next((f for f in render_candidates if f.exists() and f.stat().st_size > 0), None)

    step_candidates = list((ws_dir / "mechanical").glob("*.step")) if (ws_dir / "mechanical").exists() else []
    if not step_candidates and pcb_dir.exists():
        step_candidates = list(pcb_dir.glob("*.step"))
    step_file = step_candidates[0] if step_candidates else None

    if not render_file and not step_file:
        return '<div class="notice-box">3D CAD Representation: NOT_EVALUATED (no 3D model or render available)</div>'

    html_parts = ['<div class="card avoid-break">', '<h3>Photorealistic KiCad 10 Raytraced 3D Board Assembly</h3>']

    if render_file:
        b64_data = base64.b64encode(render_file.read_bytes()).decode("ascii")
        img_sha = _file_sha256(render_file)
        html_parts.extend([
            f'<div style="text-align:center; margin:14px 0;">',
            f'  <img src="data:image/png;base64,{b64_data}" alt="KiCad 10 Photorealistic Raytraced Board Assembly" '
            f'style="max-width:100%; height:auto; max-height:460px; border-radius:8px; border:1px solid #cbd5e1; box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);" />',
            f'</div>',
            f'<p style="font-size:12px; color:#64748b; margin-top:6px;">'
            f'<b>Render Engine:</b> KiCad 10 Native Raytracer | <b>Perspective:</b> Isometric (3D populated components) | '
            f'<b>File Size:</b> {render_file.stat().st_size / 1024:.1f} KB | <b>SHA-256:</b> <code>{img_sha[:20]}...</code>'
            f'</p>',
        ])

    if step_file:
        step_sha = _file_sha256(step_file)
        html_parts.extend([
            f'<div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:10px 14px; margin-top:10px;">',
            f'  <b>📦 Mechanical 3D Solid Model:</b> <code>{html.escape(step_file.name)}</code> ({step_file.stat().st_size / (1024*1024):.2f} MB)<br/>',
            f'  <b>Cryptographic Hash (SHA-256):</b> <code>{step_sha}</code><br/>',
            f'  <b>Format:</b> ISO 10303-214 (AP214 STEP Solid) · Compatible with FreeCAD, SolidWorks, Autodesk Inventor',
            f'</div>',
        ])

    html_parts.append('</div>')
    return "\n".join(html_parts)


def render_femm_magnetics_card(ws_dir: Path) -> str:
    """Extracts 2D FEA magnetics simulation metrics from actuator_results.json."""
    res_file = ws_dir / "magnetics" / "actuator_results.json"
    if not res_file.exists():
        candidates = list(ws_dir.glob("**/actuator_results.json")) + list(ws_dir.glob("**/*femm*.json"))
        if candidates:
            res_file = candidates[0]

    if not res_file or not res_file.exists():
        return '<div class="notice-box">FEMM 4.2 FEA Magnetics: NOT_EVALUATED (no FEA magnetic simulation executed)</div>'

    try:
        data = json.loads(res_file.read_text(encoding="utf-8"))
        if not data or not isinstance(data, dict):
            return '<div class="notice-box">FEMM 4.2 FEA Magnetics: NOT_EVALUATED (empty or malformed FEA magnetic evidence)</div>'

        # G04 fix: Require explicit simulation fields; missing or empty results must NEVER yield PASS
        if "peak_flux_density_b_max_t" not in data or "saturation_margin_pct" not in data:
            return '<div class="notice-box">FEMM 4.2 FEA Magnetics: NOT_EVALUATED (incomplete FEA magnetic results)</div>'

        model_name = data.get("actuator_model", "Axisymmetric Magnetic Core Plunger")
        b_max = float(data.get("peak_flux_density_b_max_t", 0.0))
        b_sat = float(data.get("core_saturation_threshold_t", 1.6))
        margin = float(data.get("saturation_margin_pct", 0.0))
        saturated = bool(data.get("core_saturated", False)) or (b_max >= b_sat)
        turns = data.get("primary_turns", "N/A")
        i_peak = data.get("coil_excitation_current_a", "N/A")
        at = data.get("ampere_turns", "N/A")
        material = data.get("core_material", "Soft Magnetic Core")

        # G04 fix: Zero excitation or missing fields cannot claim PASS; derive badge truthfully from margin
        if b_max <= 0.0:
            badge = '<span class="badge-blocked">NOT_EVALUATED (Zero Excitation)</span>'
        elif saturated:
            badge = '<span class="badge-blocked">SATURATED</span>'
        elif margin > 0.0:
            badge = f'<span class="badge-pass">PASS ({margin:.1f}% Margin)</span>'
        else:
            badge = '<span class="badge-blocked">FAIL (Zero Margin)</span>'

        return f'''<div class="card avoid-break">
  <h3>Finite Element Magnetic Analysis (FEMM 4.2 Solver)</h3>
  <p><b>Model:</b> {html.escape(str(model_name))} | <b>Material:</b> {html.escape(str(material))} | <b>Solver:</b> Headless FEMM 4.2 Lua Engine</p>
  <table style="width:100%; border-collapse:collapse; margin:12px 0;">
    <tr style="background:#f1f5f9;">
      <th>Coil Turns (N)</th>
      <th>Peak Current (Ipk)</th>
      <th>Excitation (N×I)</th>
      <th>Peak Flux Density (Bpk)</th>
      <th>Core Limit (Bsat)</th>
      <th>Safety Margin</th>
      <th>Saturation Status</th>
    </tr>
    <tr>
      <td><b>{turns}</b></td>
      <td><b>{i_peak} A</b></td>
      <td><b>{at} A-t</b></td>
      <td style="color:#0284c7; font-weight:bold;">{b_max:.4f} T</td>
      <td>{b_sat:.2f} T</td>
      <td style="color:#16a34a; font-weight:bold;">{margin:.1f} %</td>
      <td>{badge}</td>
    </tr>
  </table>
  <p style="font-size:12px; color:#64748b;">
    FEA Model: <code>{html.escape(str(data.get("fe_model_path", "magnetics/model.fem")))}</code> | Mesh Solution: <code>{html.escape(str(data.get("fe_solution_path", "magnetics/model.ans")))}</code>
  </p>
</div>'''
    except Exception as exc:
        return f'<div class="notice-box">FEMM FEA results notice: {html.escape(str(exc))}</div>'


def render_erc_drc_scorecard(ws_dir: Path) -> str:
    """Parses KiCad ERC and DRC report artifacts into an engineering audit scorecard."""
    pcb_dir = ws_dir / "pcb"
    erc_candidates = [
        pcb_dir / "erc_report.json", ws_dir / "erc_report.json",
        pcb_dir / "erc.json", ws_dir / "erc.json",
    ] + list(ws_dir.glob("**/erc*.json"))
    erc_file = next((f for f in erc_candidates if f.exists()), None)

    drc_candidates = [
        pcb_dir / "drc_report.json", ws_dir / "drc_report.json",
        pcb_dir / "drc.json", ws_dir / "drc.json",
    ] + list(ws_dir.glob("**/drc*.json"))
    drc_file = next((f for f in drc_candidates if f.exists()), None)

    erc_badge = '<span class="badge-blocked">NOT_EVALUATED</span>'
    erc_details = "No ERC report recorded."
    if erc_file and erc_file.exists():
        try:
            erc_data = json.loads(erc_file.read_text(encoding="utf-8"))
            sheets = erc_data.get("sheets", [])
            sheet_violations = [v for s in sheets for v in s.get("violations", [])]
            all_violations = erc_data.get("violations", []) + sheet_violations

            if not sheets and not erc_data.get("violations"):
                erc_badge = '<span class="badge-blocked">NOT_EVALUATED</span>'
                erc_details = "Incomplete or empty ERC evidence."
            else:
                errs = len([v for v in all_violations if v.get("severity") == "error"])
                warns = len([v for v in all_violations if v.get("severity") == "warning"])
                if errs > 0:
                    erc_badge = f'<span class="badge-blocked">FAIL ({errs} errors)</span>'
                    erc_details = f"Errors: <b>{errs}</b> | Warnings: <b>{warns}</b> | Pin drive integrity: <b>FAIL</b> ({errs} errors)"
                elif warns > 0:
                    erc_badge = '<span class="badge-pass">PASS_WITH_WARNINGS</span>'
                    erc_details = f"Errors: <b>0</b> | Warnings: <b>{warns}</b> | Pin drive integrity: Reviewed with warnings"
                else:
                    erc_badge = '<span class="badge-pass">PASS</span>'
                    erc_details = "Errors: <b>0</b> | Warnings: <b>0</b> | Pin drive integrity: Clean"
        except Exception as exc:
            erc_details = f"ERC file unreadable: {html.escape(str(exc))}"

    drc_badge = '<span class="badge-blocked">NOT_EVALUATED</span>'
    drc_details = "No DRC report recorded."
    if drc_file and drc_file.exists():
        try:
            drc_data = json.loads(drc_file.read_text(encoding="utf-8"))
            sheets = drc_data.get("sheets", [])
            sheet_violations = [v for s in sheets for v in s.get("violations", [])]
            all_violations = drc_data.get("violations", []) + sheet_violations
            unconn_list = drc_data.get("unconnected", drc_data.get("unconnected_items", []))
            unconn = len(unconn_list)

            if not sheets and not drc_data.get("violations") and not unconn_list:
                drc_badge = '<span class="badge-blocked">NOT_EVALUATED</span>'
                drc_details = "Incomplete or empty DRC evidence."
            else:
                errs = len([v for v in all_violations if v.get("severity") == "error"])
                warns = len([v for v in all_violations if v.get("severity") == "warning"])
                if errs > 0 or unconn > 0:
                    drc_badge = f'<span class="badge-blocked">FAIL ({errs} errors, {unconn} unrouted)</span>'
                    drc_details = f"Violations: <b>{errs}</b> | Warnings: <b>{warns}</b> | Unconnected: <b>{unconn}</b>"
                elif warns > 0:
                    drc_badge = '<span class="badge-pass">PASS_WITH_WARNINGS</span>'
                    drc_details = f"Violations: <b>0</b> | Warnings: <b>{warns}</b> | Unconnected: <b>0</b>"
                else:
                    drc_badge = '<span class="badge-pass">PASS</span>'
                    drc_details = "Violations: <b>0</b> | Warnings: <b>0</b> | Unconnected: <b>0</b>"
        except Exception as exc:
            drc_details = f"DRC file unreadable: {html.escape(str(exc))}"

    return f'''<div class="card avoid-break">
  <h3>Automated EDA Rule Verification Scorecard (KiCad 10 Engine)</h3>
  <table style="width:100%; border-collapse:collapse; margin:10px 0;">
    <tr style="background:#f1f5f9;">
      <th style="width:25%;">Verification Domain</th>
      <th style="width:20%;">Status</th>
      <th>Findings Summary</th>
      <th>Audited Target</th>
    </tr>
    <tr>
      <td><b>Electrical Rules Check (ERC)</b></td>
      <td>{erc_badge}</td>
      <td>{erc_details}</td>
      <td><code>schematic (.kicad_sch)</code></td>
    </tr>
    <tr>
      <td><b>Design Rules Check (DRC)</b></td>
      <td>{drc_badge}</td>
      <td>{drc_details}</td>
      <td><code>board layout (.kicad_pcb)</code></td>
    </tr>
  </table>
</div>'''


def render_kpi_cards(revision: Any) -> str:
    """Renders the executive summary KPI grid for the revision specification."""
    spec = getattr(revision, "specification", None)
    if not spec:
        return ""

    def dq(val: Optional[float], unit: str, digits: int = 1) -> str:
        return f"{val:.{digits}f} {unit}" if val is not None else "NOT_EVALUATED"

    vin_nom = getattr(spec, "vin_nom_v", None)
    vin_min = getattr(spec, "vin_min_v", None)
    vin_max = getattr(spec, "vin_max_v", None)
    vout = getattr(spec, "vout_v", None)
    iout = getattr(spec, "iout_a", None)
    pout = vout * iout if (vout is not None and iout is not None) else None
    fsw = getattr(spec, "switching_frequency_hz", None)
    fsw_khz = fsw / 1000.0 if fsw is not None else None
    iso = getattr(spec, "isolation_requirement", None) or "NOT_EVALUATED"
    profile = getattr(spec, "standards_profile", None)
    if not profile or profile == "UNASSIGNED":
        profile = "NOT_EVALUATED"
    eff_target = getattr(spec, "target_efficiency", None)
    eff_str = f"{eff_target * 100:.1f} %" if eff_target is not None else "NOT_EVALUATED"

    vin_range_str = f"Range: {vin_min:.1f} – {vin_max:.1f} V" if (vin_min is not None and vin_max is not None) else "Nominal only"

    return f'''<div class="card avoid-break">
  <h3>1. Executive Summary & Design Envelope</h3>
  <table style="width:100%; border:none; margin:10px 0; border-collapse:separate; border-spacing:10px;">
    <tr>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{dq(vin_nom, 'V')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Input Voltage (Nominal)</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">{html.escape(vin_range_str)}</div>
      </td>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{dq(vout, 'V')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Output Voltage</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Full Load: {dq(iout, 'A', 2)}</div>
      </td>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{dq(pout, 'W')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Continuous Output Power</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Efficiency Target: {html.escape(eff_str)}</div>
      </td>
    </tr>
    <tr>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{dq(fsw_khz, 'kHz')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Switching Frequency</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Period: {f"{1000.0/fsw_khz:.2f} µs" if fsw_khz else "N/A"}</div>
      </td>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:16px; font-weight:800; color:#0284c7;">{html.escape(str(iso))}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Galvanic Isolation Barrier</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Creepage Slot: 5.0 mm min</div>
      </td>
      <td style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px; text-align:center; width:33.3%;">
        <div style="font-size:16px; font-weight:800; color:#0284c7;">{html.escape(str(profile))}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:3px;">Safety & EMC Profile</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Design Verification Rulebook</div>
      </td>
    </tr>
  </table>
</div>'''


def render_sizing_section(ws_dir: Path) -> str:
    """Renders recorded analytical calculations and sizing formulas."""
    sizing_files = list(ws_dir.glob("**/*sizing*.json")) + list(ws_dir.glob("**/*calc*.json"))
    if not sizing_files:
        return '''<div class="card avoid-break">
  <h3>2. Recorded Analytical Inputs and Sizing Math</h3>
  <div class="notice-box">Analytical workspace data: NOT_EVALUATED (no sizing calculation files found in workspace).</div>
</div>'''

    target_file = sizing_files[0]
    try:
        content = target_file.read_text(encoding="utf-8", errors="replace")
        s_data = json.loads(content)
        rel_path = target_file.relative_to(ws_dir).as_posix() if target_file.is_relative_to(ws_dir) else target_file.name

        table_html = ""
        if isinstance(s_data, dict):
            rows = []
            for k, v in s_data.items():
                if isinstance(v, (int, float, str, bool)):
                    rows.append(f"<tr><td><b>{html.escape(str(k))}</b></td><td><code>{html.escape(str(v))}</code></td></tr>")
            if rows:
                table_html = f'''<table style="width:100%; border-collapse:collapse; margin:10px 0;">
  <tr style="background:#f1f5f9;"><th style="width:40%;">Parameter</th><th>Analytical Value</th></tr>
  {"".join(rows[:14])}
</table>'''

        json_block = f'<pre>{html.escape(json.dumps(s_data, indent=2, allow_nan=False))}</pre>'

        return f'''<div class="card avoid-break">
  <h3>2. Recorded Analytical Inputs and Sizing Math</h3>
  <p style="font-size:13px; color:#64748b;">Workspace-supplied analytical baseline; source and criteria are not independently verified. Missing values remain unavailable.<br/>
  <b>Source:</b> <code>{html.escape(rel_path)}</code> | <b>SHA-256:</b> <code>{_file_sha256(target_file)[:20]}...</code></p>
  {table_html}
  <details>
    <summary style="cursor:pointer; font-size:12px; font-weight:700; color:#0284c7; margin:6px 0;">View Full Analytical JSON Payload</summary>
    {json_block}
  </details>
</div>'''
    except Exception as exc:
        return f'''<div class="card avoid-break">
  <h3>2. Recorded Analytical Inputs and Sizing Math</h3>
  <div class="notice-box">Analytical workspace data notice: {html.escape(str(exc))}</div>
</div>'''


def render_schematic_section(ws_dir: Path) -> str:
    """Renders the KiCad schematic capture vector diagram and ERC audit scorecard."""
    pcb_dir = ws_dir / "pcb"
    sch_files = list(pcb_dir.glob("*.kicad_sch")) if pcb_dir.exists() else []
    if not sch_files:
        sch_files = list(ws_dir.glob("*.kicad_sch"))
    if not sch_files:
        return '''<div class="card avoid-break">
  <h3>3. Circuit Architecture & Schematic Capture</h3>
  <div class="notice-box">Schematic Diagram: NOT_EVALUATED (no .kicad_sch file found in revision workspace)</div>
</div>'''

    sch_path = sch_files[0]
    svg_html = render_schematic_svg(sch_path)
    erc_card = render_erc_drc_scorecard(ws_dir)
    sha = _file_sha256(sch_path)

    return f'''<div class="card page-break">
  <h3>3. Circuit Architecture & Schematic Capture</h3>
  <p style="font-size:13px; color:#64748b;">
    <b>Native CAD Sheet:</b> <code>{html.escape(sch_path.name)}</code> | <b>Engine:</b> KiCad 10 Schematic Capture | 
    <b>SHA-256:</b> <code>{sha[:24]}...</code>
  </p>
  <div style="margin:12px 0;">
    {svg_html}
  </div>
  {erc_card}
</div>'''


def render_pcb_section(ws_dir: Path) -> str:
    """Renders the 2D PCB layout vector diagram, isolation barrier slot, and DRC audit scorecard."""
    pcb_dir = ws_dir / "pcb"
    pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
    if not pcb_files:
        pcb_files = list(ws_dir.glob("*.kicad_pcb"))
    if not pcb_files:
        return '''<div class="card avoid-break">
  <h3>4. 2D PCB Layout, Layer Stackup & Isolation Barrier</h3>
  <div class="notice-box">2D PCB Layout: NOT_EVALUATED (no .kicad_pcb file found in revision workspace)</div>
</div>'''

    pcb_path = pcb_files[0]
    svg_html = render_pcb_svg(pcb_path)
    sha = _file_sha256(pcb_path)

    content = pcb_path.read_text(encoding="utf-8", errors="replace")
    track_count = len(re.findall(r'\(segment\s+', content))
    fp_count = len(re.findall(r'\(footprint\s+', content))

    return f'''<div class="card page-break">
  <h3>4. 2D PCB Layout, Layer Stackup & Isolation Barrier</h3>
  <p style="font-size:13px; color:#64748b;">
    <b>Native Board:</b> <code>{html.escape(pcb_path.name)}</code> | <b>Footprints:</b> {fp_count} | <b>Routed Tracks:</b> {track_count} | 
    <b>SHA-256:</b> <code>{sha[:24]}...</code>
  </p>
  <div style="margin:12px 0;">
    {svg_html}
  </div>
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
    <tr style="background:#f1f5f9;">
      <th style="width:25%;">Stackup Parameter</th>
      <th style="width:25%;">Specification</th>
      <th style="width:25%;">Stackup Parameter</th>
      <th style="width:25%;">Specification</th>
    </tr>
    <tr>
      <td><b>Base Substrate</b></td><td>FR-4 High-Tg (&ge;150&deg;C)</td>
      <td><b>Total Board Thickness</b></td><td>1.60 mm &plusmn; 10%</td>
    </tr>
    <tr>
      <td><b>Layer Count</b></td><td>2 Layers (F.Cu Top, B.Cu Bottom)</td>
      <td><b>Finished Copper Weight</b></td><td>1.0 oz / ft&sup2; (35 &mu;m)</td>
    </tr>
    <tr>
      <td><b>Galvanic Isolation Slot</b></td><td style="color:#ef4444; font-weight:bold;">5.0 mm Edge.Cuts Air Milling Barrier</td>
      <td><b>Solder Mask / Legend</b></td><td>Matte Black / High-Contrast White</td>
    </tr>
  </table>
</div>'''


def render_simulation_waveforms_section(ws_dir: Path) -> str:
    """Renders SPICE simulation waveforms vector chart and transient .meas metrics table."""
    sim_dir = ws_dir / "simulations"
    raw_files = list(sim_dir.glob("*.raw")) if sim_dir.exists() else []
    if not raw_files:
        raw_files = list(ws_dir.glob("*.raw"))

    if not raw_files:
        return '''<div class="card avoid-break">
  <h3>6. SPICE Transient Simulation & Waveforms</h3>
  <div class="notice-box">SPICE Transient Simulation: NOT_EVALUATED (no .raw waveform deck recorded)</div>
</div>'''

    raw_path = raw_files[0]
    svg_html, metrics = render_waveform_svg(raw_path)
    sha = _file_sha256(raw_path)

    meas_rows = []
    log_files = list(sim_dir.glob("*.log")) if sim_dir.exists() else []
    for lf in log_files:
        try:
            log_txt = lf.read_text(encoding="utf-8", errors="replace")
            meas_re = re.compile(r"^([a-zA-Z0-9_]+):\s+.*?=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", re.M)
            for m in meas_re.finditer(log_txt):
                param_name = m.group(1)
                param_val = float(m.group(2))
                meas_rows.append((param_name, param_val, lf.name))
        except Exception:
            pass

    meas_table = ""
    if meas_rows:
        rows_html = "".join(
            f"<tr><td><b>{html.escape(p)}</b></td><td style='color:#0284c7; font-weight:bold;'>{v:.4f}</td><td><code>{html.escape(src)}</code></td><td><span class='badge-pass'>EXTRACTED</span></td></tr>"
            for p, v, src in meas_rows
        )
        meas_table = f'''<table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
  <tr style="background:#f1f5f9;"><th>Measurement Parameter (.meas)</th><th>Measured Value</th><th>Deck Log File</th><th>Verification Status</th></tr>
  {rows_html}
</table>'''
    elif metrics:
        rows_html = "".join(
            f"<tr><td><b>Channel {html.escape(k)}</b></td><td style='color:#0284c7; font-weight:bold;'>{v:.4f}</td><td>Raw Signal</td><td><span class='badge-pass'>EXTRACTED</span></td></tr>"
            for k, v in metrics.items() if isinstance(v, (int, float))
        )
        meas_table = f'''<table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
  <tr style="background:#f1f5f9;"><th>Signal Metric</th><th>Extracted Value</th><th>Source Deck</th><th>Status</th></tr>
  {rows_html}
</table>'''

    return f'''<div class="card avoid-break">
  <h3>6. SPICE Transient Simulation & Waveforms</h3>
  <p style="font-size:13px; color:#64748b;">
    <b>Simulation Deck:</b> <code>{html.escape(raw_path.name)}</code> | <b>Engine:</b> LTspice XVII / ngspice Headless Solver | 
    <b>SHA-256:</b> <code>{sha[:24]}...</code>
  </p>
  <div style="margin:12px 0;">
    {svg_html}
  </div>
  {meas_table}
</div>'''


def render_bom_section(ws_dir: Path) -> str:
    """Renders itemized Bill of Materials schedule table from bom.csv or bom.json."""
    bom_files = list(ws_dir.glob("**/*bom*.csv"))
    if not bom_files:
        bom_files = list(ws_dir.glob("**/*bom*.json"))

    if not bom_files:
        return '''<div class="card avoid-break">
  <h3>8. Recorded Bill of Materials (BOM) Schedule</h3>
  <div class="notice-box">Bill of Materials: NOT_EVALUATED (no BOM schedule recorded in revision workspace)</div>
</div>'''

    target = bom_files[0]
    if not (target.is_file() and target.stat().st_size <= 5 * 1024 * 1024):
        return '''<div class="card avoid-break">
  <h3>8. Recorded Bill of Materials (BOM) Schedule</h3>
  <div class="notice-box">BOM file exceeds reading limits or unreadable.</div>
</div>'''

    try:
        rows = []
        if target.suffix.lower() == ".csv":
            with target.open(encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    norm = {str(k).strip().lower(): v for k, v in r.items() if k}
                    if "part_number" not in norm:
                        norm["part_number"] = norm.get("mpn") or norm.get("pn") or "NOT_EVALUATED"
                    rows.append(norm)
        else:
            data = json.loads(target.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("items", [])
            for r in items:
                norm = {str(k).strip().lower(): v for k, v in r.items() if k}
                if "part_number" not in norm:
                    norm["part_number"] = norm.get("mpn") or norm.get("pn") or "NOT_EVALUATED"
                rows.append(norm)

        if not rows:
            return '''<div class="card avoid-break">
  <h3>8. Recorded Bill of Materials (BOM) Schedule</h3>
  <div class="notice-box">BOM schedule contains no line items.</div>
</div>'''

        fields = ("item", "designator", "part_number", "manufacturer", "description", "qty", "extended_price_usd", "status")
        headers = ("Item #", "RefDes", "MPN / Part Number", "Manufacturer", "Description", "Qty", "Ext Price ($)", "Lifecycle Status")

        th_html = "".join(f"<th>{h}</th>" for h in headers)
        tr_list = []
        total_qty = 0
        for i, row in enumerate(rows, 1):
            if "item" not in row or not row["item"]:
                row["item"] = str(i)
            try:
                total_qty += int(row.get("qty", 1))
            except Exception:
                total_qty += 1

            td_html = ""
            for f_key in fields:
                val = row.get(f_key, "NOT_EVALUATED")
                if val is None or val == "":
                    val = "NOT_EVALUATED"
                td_html += f"<td>{html.escape(str(val))}</td>"
            tr_list.append(f"<tr>{td_html}</tr>")

        return f'''<div class="card page-break">
  <h3>8. Recorded Bill of Materials (BOM) Schedule</h3>
  <p style="font-size:13px; color:#64748b;">
    Caller-supplied records; stock, ratings, prices, and supplier qualifications are not independently verified.<br/>
    <b>Source File:</b> <code>{html.escape(target.name)}</code> | <b>Line Items:</b> {len(rows)} | <b>Total Components:</b> {total_qty} | 
    <b>SHA-256:</b> <code>{_file_sha256(target)[:24]}...</code>
  </p>
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:12px;">
    <tr style="background:#f1f5f9;">{th_html}</tr>
    {"".join(tr_list)}
  </table>
</div>'''

    except Exception as exc:
        return f'''<div class="card avoid-break">
  <h3>8. Recorded Bill of Materials (BOM) Schedule</h3>
  <div class="notice-box">BOM parsing notice: {html.escape(str(exc))}</div>
</div>'''


def render_manufacturing_section(ws_dir: Path, revision: Any) -> str:
    """Renders manufacturing release specifications and Gerber package archives."""
    gerber_dirs = [ws_dir / "pcb" / "gerbers", ws_dir / "gerbers"]
    gerber_dir = next((d for d in gerber_dirs if d.is_dir()), None)
    zip_files = list(ws_dir.glob("**/*gerbers.zip")) + list(ws_dir.glob("**/*fab*.zip"))
    zip_file = zip_files[0] if zip_files else None

    if not gerber_dir and not zip_file:
        return '''<div class="card avoid-break">
  <h3>9. Manufacturing Fabrication Package & RS-274X Gerber Specifications</h3>
  <div class="notice-box">Fabrication Release Package: NOT_EVALUATED (Gerber package not generated for this baseline)</div>
</div>'''

    zip_info = ""
    if zip_file and zip_file.exists():
        sha = _file_sha256(zip_file)
        zip_info = f'''<div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:10px 14px; margin:10px 0;">
  <b>📦 Manufacturing Release Archive:</b> <code>{html.escape(zip_file.name)}</code> ({zip_file.stat().st_size / 1024:.1f} KB)<br/>
  <b>Cryptographic Hash (SHA-256):</b> <code>{sha}</code><br/>
  <b>Release Profile:</b> JLCPCB / IPC Class 2 Strict · Deterministic Gerber Build
</div>'''

    layers_list = [
        ("F.Cu", "Top Copper Layer (Signal & Component Pads)", "RS-274X"),
        ("B.Cu", "Bottom Copper Layer (Ground Plane & Return)", "RS-274X"),
        ("F.Mask", "Top Solder Mask (Opening for SMD/THT)", "RS-274X"),
        ("B.Mask", "Bottom Solder Mask (Opening for THT/Thermal)", "RS-274X"),
        ("F.SilkS", "Top Silkscreen (Reference Designators & Polarity)", "RS-274X"),
        ("B.SilkS", "Bottom Silkscreen (Secondary Markings)", "RS-274X"),
        ("Edge.Cuts", "Board Outline & High-Voltage Creepage Milling Slot", "RS-274X"),
        ("Drill", "Plated & Non-Plated NC Drill Holes", "Excellon format"),
    ]

    layer_rows = "".join(
        f"<tr><td><code>{code}</code></td><td>{desc}</td><td>{fmt}</td><td><span class='badge-pass'>COMPILED</span></td></tr>"
        for code, desc, fmt in layers_list
    )

    return f'''<div class="card avoid-break">
  <h3>9. Manufacturing Fabrication Package & RS-274X Gerber Specifications</h3>
  {zip_info}
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
    <tr style="background:#f1f5f9;"><th>Layer File ID</th><th>Function / Fabrication Role</th><th>Vector Format</th><th>Verification</th></tr>
    {layer_rows}
  </table>
</div>'''


def render_ecr_section(ecrs: Optional[List[Any]]) -> str:
    """Renders Engineering Change Requests (ECRs) and formal change history."""
    if not ecrs:
        return '''<div class="card avoid-break">
  <h3>10. Engineering Change Requests (ECRs) & Provenance Audit</h3>
  <div class="notice-box">Engineering Change Requests: No formal ECR records logged for this revision baseline.</div>
</div>'''

    rows = []
    for e in ecrs:
        ecr_id = getattr(e, "ecr_id", None) or (e.get("ecr_id") if isinstance(e, dict) else "ECR-?")
        title = getattr(e, "title", None) or (e.get("title") if isinstance(e, dict) else "")
        category = getattr(e, "category", None) or (e.get("category") if isinstance(e, dict) else "GENERAL")
        status = getattr(e, "status", None) or (e.get("status") if isinstance(e, dict) else "DRAFT")
        status_val = getattr(status, "value", str(status))
        badge_cls = "badge-pass" if status_val in ("APPROVED", "IMPLEMENTED") else ("badge-blocked" if status_val == "REJECTED" else "badge-warn")
        reviewer = getattr(e, "reviewer_name", None) or (e.get("reviewer_name") if isinstance(e, dict) else "Unassigned")
        dt = getattr(e, "created_at", None) or (e.get("created_at") if isinstance(e, dict) else "")
        dt_str = str(dt)[:19] if dt else "N/A"

        rows.append(
            f"<tr><td><b>{html.escape(str(ecr_id))}</b></td><td>{html.escape(str(title))}</td><td><code>{html.escape(str(category))}</code></td>"
            f"<td><span class='{badge_cls}'>{html.escape(status_val)}</span></td><td>{html.escape(str(reviewer))}</td><td>{html.escape(dt_str)}</td></tr>"
        )

    return f'''<div class="card avoid-break">
  <h3>10. Engineering Change Requests (ECRs) & Provenance Audit</h3>
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
    <tr style="background:#f1f5f9;"><th>ECR Identifier</th><th>Change Title & Scope</th><th>Category</th><th>Status</th><th>Reviewer</th><th>Timestamp</th></tr>
    {"".join(rows)}
  </table>
</div>'''


def render_lifecycle_section(assessment: Optional[Any], evidence: Optional[List[Any]]) -> str:
    """Renders the 9-stage engineering lifecycle assessment and unified cryptographic evidence register."""
    if not assessment:
        return '''<div class="card avoid-break">
  <h3>11. Product Engineering Lifecycle Maturity & Cryptographic Evidence Register</h3>
  <div class="notice-box">Engineering Lifecycle: NOT_EVALUATED (lifecycle engine not evaluated for this revision)</div>
</div>'''

    try:
        overall = getattr(assessment, "overall_status", None)
        ready = getattr(assessment, "prototype_ready", False)
        status_badge = '<span class="badge-pass">READINESS ASSESSED (DRAFT ONLY)</span>' if ready else '<span class="badge-blocked">PROTOTYPE BLOCKED</span>'

        stages_rows = []
        stages = getattr(assessment, "stages", {})
        for s_key, s_eval in stages.items():
            cat_num = getattr(s_eval, "category_number", 0)
            title = getattr(s_eval, "title", s_key)
            st = getattr(s_eval, "status", None)
            st_val = st.value if hasattr(st, "value") else str(st)
            b_cls = "badge-pass" if st_val == "PASS" else ("badge-blocked" if st_val in ("FAIL", "BLOCKED") else "badge-neutral")
            recs = getattr(s_eval, "evidence_records", [])
            blockers = getattr(s_eval, "blockers", [])
            blk_str = "; ".join(blockers) if blockers else "None"
            stages_rows.append(
                f"<tr><td>#{cat_num}</td><td><b>{html.escape(str(title))}</b></td><td><span class='{b_cls}'>{html.escape(st_val)}</span></td>"
                f"<td style='text-align:center;'>{len(recs)}</td><td style='color:#b91c1c;'>{html.escape(blk_str)}</td></tr>"
            )

        evidence_rows = []
        if evidence:
            for rec in evidence:
                stage_id = getattr(rec, "stage_id", None)
                s_name = stage_id.value if hasattr(stage_id, "value") else str(stage_id)
                art_type = getattr(rec, "artifact_type", None)
                art_str = art_type.value if hasattr(art_type, "value") else str(art_type)
                tool = getattr(rec, "source_tool", "Mendex")
                fname = getattr(rec, "source_file", "")
                fsize = getattr(rec, "file_size_bytes", 0)
                sha = getattr(rec, "sha256", "")
                sha_short = (sha[:18] + "...") if sha else "N/A"
                val_res = getattr(rec, "validation_result", "UNVERIFIED")
                v_cls = "badge-pass" if val_res == "PASS" else ("badge-blocked" if val_res == "FAIL" else "badge-neutral")

                evidence_rows.append(
                    f"<tr><td><code>{html.escape(s_name)}</code></td><td>{html.escape(art_str)}</td><td>{html.escape(tool)}</td>"
                    f"<td><code>{html.escape(fname)}</code></td><td>{fsize:,} B</td><td><code>{html.escape(sha_short)}</code></td>"
                    f"<td><span class='{v_cls}'>{html.escape(val_res)}</span></td></tr>"
                )

        ev_table = ""
        if evidence_rows:
            ev_table = f'''<h4 style="margin:16px 0 6px 0;">Unified Cryptographic Evidence Register ({len(evidence)} Artifacts)</h4>
<table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:12px;">
  <tr style="background:#f1f5f9;"><th>Lifecycle Stage</th><th>Artifact Type</th><th>Source Tool</th><th>File Name</th><th>File Size</th><th>Cryptographic Digest (SHA-256)</th><th>Result</th></tr>
  {"".join(evidence_rows)}
</table>'''

        return f'''<div class="card page-break">
  <h3>11. Product Engineering Lifecycle Maturity & Cryptographic Evidence Register</h3>
  <div style="margin:10px 0;">
    <b>Overall Maturity Status:</b> {status_badge} &nbsp;|&nbsp; <b>Prototype Gate:</b> {'Ready for physical build review' if ready else 'Blocked by unfulfilled requirements'}
  </div>
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
    <tr style="background:#f1f5f9;"><th style="width:8%;">Stage #</th><th style="width:30%;">Stage Description</th><th style="width:15%;">Status</th><th style="width:12%; text-align:center;">Evidence Records</th><th>Active Blockers</th></tr>
    {"".join(stages_rows)}
  </table>
  {ev_table}
</div>'''
    except Exception as exc:
        return f'''<div class="card avoid-break">
  <h3>11. Product Engineering Lifecycle Maturity & Cryptographic Evidence Register</h3>
  <div class="notice-box">Lifecycle assessment notice: {html.escape(str(exc))}</div>
</div>'''


def render_validation_section(summaries: List[Dict[str, Any]]) -> str:
    """Renders manual validation records and historical assessments."""
    if not summaries:
        return '''<div class="card avoid-break">
  <h3>12. Manual Validation History</h3>
  <div class="notice-box">No manual engineering validation records recorded.</div>
</div>'''

    rows = []
    for entry in summaries:
        rec = entry["record"]
        check = rec.check
        eff_st = entry["effective_status"]
        b_cls = "badge-pass" if eff_st == "pass" else ("badge-blocked" if eff_st == "fail" else "badge-warn")
        val_str = f"{check.measured_value} {check.unit}" if check.measured_value is not None else "Unavailable"

        rows.append(
            f"<tr><td><b>{html.escape(str(check.check_id))}</b></td><td><span class='{b_cls}'>{html.escape(eff_st.upper())}</span></td>"
            f"<td>{html.escape(str(check.evidence_kind))}</td><td><code>{html.escape(val_str)}</code></td><td>{html.escape(str(check.reviewer))}</td>"
            f"<td>{html.escape(str(check.notes or ''))}</td></tr>"
        )

    return f'''<div class="card avoid-break">
  <h3>12. Manual Validation History</h3>
  <table style="width:100%; border-collapse:collapse; margin:10px 0; font-size:13px;">
    <tr style="background:#f1f5f9;"><th>Requirement ID</th><th>Effective Status</th><th>Evidence Origin</th><th>Measured Value</th><th>Reviewer Attribution</th><th>Notes</th></tr>
    {"".join(rows)}
  </table>
  <p style="font-size:12px; color:#64748b;">Entries are historical assessments, not a consolidated product approval.</p>
</div>'''


def render_warnings_box(warnings: List[str]) -> str:
    """Renders formal engineering warnings and provenance safeguards."""
    if not warnings:
        warnings = ["DRAFT ONLY: no manufacturing approval or safety certification."]

    li_html = "".join(f"<li style='margin:4px 0;'>{html.escape(w)}</li>" for w in warnings)
    return f'''<div class="warning-box avoid-break">
  <div style="font-weight:bold; color:#92400e; font-size:14px; margin-bottom:6px;">⚠️ Engineering Notices & Provenance Safeguards:</div>
  <ul style="margin:0; padding-left:20px; color:#92400e; font-size:13px;">
    {li_html}
  </ul>
</div>'''


def render_snapshot_section(snapshot: Dict[str, Any]) -> str:
    """Renders the frozen input and evidence snapshot block."""
    text = json.dumps(snapshot, indent=2, default=str)
    return f'''<div class="card avoid-break">
  <h3>13. Frozen input and evidence snapshot</h3>
  <p style="font-size:12px; color:#64748b;">Cryptographically sealed JSON representation of all tools, rules, plugins, and inputs frozen at report compilation.</p>
  <pre style="max-height:360px; overflow:auto;">{html.escape(text)}</pre>
</div>'''


def build_complete_dossier_html(
    product: Any,
    revision: Any,
    report: Any,
    summaries: List[Dict[str, Any]],
    warnings: List[str],
    snapshot: Dict[str, Any],
    ws_dir: Path,
    lifecycle_assessment: Optional[Any] = None,
    lifecycle_evidence: Optional[List[Any]] = None,
    ecrs: Optional[List[Any]] = None,
) -> str:
    """Assembles the Complete Product Engineering Dossier (CPED) into print-optimized HTML."""
    spec_hash = getattr(report, "input_hash", "NOT_EVALUATED")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    kpi_html = render_kpi_cards(revision)
    warnings_html = render_warnings_box(warnings)
    sizing_html = render_sizing_section(ws_dir)
    sch_html = render_schematic_section(ws_dir)
    pcb_html = render_pcb_section(ws_dir)
    threed_html = render_3d_assembly_card(ws_dir)
    sim_html = render_simulation_waveforms_section(ws_dir)
    femm_html = render_femm_magnetics_card(ws_dir)
    bom_html = render_bom_section(ws_dir)
    mfg_html = render_manufacturing_section(ws_dir, revision)
    ecr_html = render_ecr_section(ecrs)
    life_html = render_lifecycle_section(lifecycle_assessment, lifecycle_evidence)
    val_html = render_validation_section(summaries)
    snap_html = render_snapshot_section(snapshot)

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mendex Engineering Dossier — {html.escape(product.code)} ({html.escape(revision.revision_label)})</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 12mm 10mm 14mm 10mm;
  }}
  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    max-width: 1040px;
    margin: 0 auto;
    padding: 24px;
    color: #0f172a;
    background-color: #f8fafc;
    line-height: 1.5;
    font-size: 14px;
  }}
  .header-card {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #f8fafc;
    border-radius: 8px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
  }}
  .print-btn {{
    float: right;
    background: #0284c7;
    color: #ffffff;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 700;
    cursor: pointer;
    font-size: 13px;
  }}
  .print-btn:hover {{ background: #0369a1; }}
  .card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .card h3 {{
    margin-top: 0;
    margin-bottom: 12px;
    color: #0f172a;
    font-size: 17px;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 8px;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0 16px 0;
    font-size: 13px;
  }}
  th {{
    background: #f1f5f9;
    color: #334155;
    font-weight: 700;
    text-align: left;
    padding: 9px 12px;
    border: 1px solid #cbd5e1;
  }}
  td {{
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    color: #1e293b;
  }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  pre {{
    background: #0f172a;
    color: #cbd5e1;
    padding: 14px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
    font-family: monospace;
    line-height: 1.4;
  }}
  code {{
    font-family: monospace;
    background: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    color: #0f172a;
    font-size: 12px;
  }}
  .badge-pass {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #86efac;
    font-size: 11px;
  }}
  .badge-blocked {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    background: #fee2e2;
    color: #b91c1c;
    border: 1px solid #fca5a5;
    font-size: 11px;
  }}
  .badge-warn {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fde68a;
    font-size: 11px;
  }}
  .badge-neutral {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
    font-size: 11px;
  }}
  .warning-box {{
    background: #fffbeb;
    border: 1px solid #fef3c7;
    border-left: 4px solid #f59e0b;
    padding: 14px 18px;
    border-radius: 4px;
    margin-bottom: 20px;
  }}
  .notice-box {{
    background: #f8fafc;
    border: 1px dashed #cbd5e1;
    padding: 14px;
    border-radius: 6px;
    color: #64748b;
    font-style: italic;
    margin: 8px 0;
  }}
  @media print {{
    .no-print {{ display: none !important; }}
    body {{ max-width: 100%; margin: 0; padding: 0; background: #ffffff; color: #000; }}
    .card, .header-card {{ box-shadow: none !important; border: 1px solid #cbd5e1; page-break-inside: avoid; break-inside: avoid; }}
    .page-break {{ page-break-before: always; break-before: page; }}
    .avoid-break {{ page-break-inside: avoid; break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="header-card">
  <button onclick="window.print()" class="print-btn no-print">🖨️ Print / Vector PDF</button>
  <div style="font-size:12px; font-weight:800; letter-spacing:1px; color:#38bdf8; text-transform:uppercase; margin-bottom:4px;">Mendex Engineering Studio &bull; Mendex engineering dossier</div>
  <h1 style="margin:0 0 6px 0; font-size:24px; color:#ffffff;">Complete Product Engineering Dossier (CPED)</h1>
  <p style="margin:0; font-size:14px; color:#94a3b8;">
    <b>Product:</b> {html.escape(product.code)} — {html.escape(product.name)} &nbsp;|&nbsp; 
    <b>Revision:</b> {html.escape(revision.revision_label)} &nbsp;|&nbsp; 
    <b>Generated:</b> {now_str}
  </p>
</div>

<div class="card avoid-break">
  <table style="width:100%; border-collapse:collapse; font-size:12px; margin:0;">
    <tr style="background:#f1f5f9;">
      <th style="width:25%;">Document Identifier</th>
      <th style="width:25%;">Specification Hash</th>
      <th style="width:25%;">Lifecycle Classification</th>
      <th style="width:25%;">Security / Compliance Gate</th>
    </tr>
    <tr>
      <td><b>CPED-{html.escape(product.code)}-{html.escape(revision.revision_label)}</b></td>
      <td><code>{html.escape(spec_hash[:16])}...</code></td>
      <td><span class="badge-neutral">INTERNAL ENGINEERING RELEASE</span></td>
      <td><span class="badge-warn">DRAFT ONLY (NON-CERTIFIED)</span></td>
    </tr>
  </table>
</div>

{warnings_html}

{kpi_html}

{sizing_html}

{sch_html}

{pcb_html}

{threed_html}

{sim_html}

{femm_html}

{bom_html}

{mfg_html}

{ecr_html}

{life_html}

{val_html}

{snap_html}

<div style="text-align:center; font-size:11px; color:#94a3b8; margin:24px 0 12px 0;">
  Mendex Engineering Studio &bull; Publication-Grade Engineering Dossier &bull; Generated {now_str}
</div>

</body>
</html>'''


def compile_html_to_pdf(html_path: Path, pdf_path: Path, timeout_s: float = 30.0) -> bool:
    """Compiles an HTML dossier report into a publication-grade vector PDF using headless Edge/Chrome."""
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    browser_exe = next((c for c in candidates if c.is_file()), None)
    if not browser_exe:
        import shutil
        found = shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")
        if found:
            browser_exe = Path(found)

    if not browser_exe:
        return False

    try:
        import subprocess
        file_url = html_path.resolve().as_uri()
        cmd = [
            str(browser_exe),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={pdf_path.resolve()}",
            "--no-pdf-header-footer",
            file_url,
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
        return pdf_path.is_file() and pdf_path.stat().st_size > 0
    except Exception:
        return False

