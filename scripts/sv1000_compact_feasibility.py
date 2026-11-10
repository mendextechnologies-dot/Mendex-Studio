"""Read-only SV-1000 feasibility audit; writes a new report directory only.

Run from the repository root with the project virtual environment. No solver,
approval, validation or product-file mutation is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from mendex_core.service import StudioService


def write_json(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, default=str)


def hashes(folder):
    return {str(f.relative_to(folder)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(folder.rglob("*")) if f.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    out = args.output.resolve()
    # Limit writes to separate reports, never a product or evidence directory.
    if not out.is_relative_to(root / "reports"):
        parser.error("Output must be a new directory under reports/")
    out.mkdir(parents=True, exist_ok=False)
    before = hashes(root / "products")
    write_json(out / "product-files-before.json", before)
    source_files = [Path(__file__).resolve(), root / "scripts/unblock_sv1000.py",
                    root / "src/mendex_core/lifecycle/engine.py",
                    root / "src/integrations/parsers/ltspice_parser.py"]
    write_json(out / "audit-source-sha256.json", {
        str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in source_files if f.is_file()})
    service = StudioService(root)
    product = next(p for p in service.list_products() if p.code == "SV-1000")
    revision = service.get_revision(product.active_revision_id)
    ws = service.workspace_path(revision)
    assessment = service.lifecycle.assess(product.product_id, revision.revision_id)
    write_json(out / "application-assessment.json", assessment.model_dump(mode="json"))
    write_json(out / "approval-records.json", service.lifecycle.get_stage_approvals(revision.revision_id))
    summaries = [{**e, "record": e["record"].model_dump(mode="json")}
                 for e in service.validation_summary(revision.revision_id)]
    write_json(out / "effective-validations.json", summaries)

    board = (ws / "pcb/sv1000.kicad_pcb").read_text(encoding="utf-8")
    schematic = (ws / "pcb/sv1000.kicad_sch").read_text(encoding="utf-8")
    netlist = (ws / "circuit/sv1000_zvs_multiplier.cir").read_text(encoding="utf-8")
    code = [line.strip() for line in netlist.splitlines()
            if line.strip() and not line.lstrip().startswith(("*", ";", "."))]
    rectangles = re.findall(r'\(gr_rect\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)', board)
    rects = [{"width_mm": abs(float(c)-float(a)), "height_mm": abs(float(d)-float(b))}
             for a,b,c,d in rectangles]
    static = {
        "scope": "Static audit of these simple source files, not a general KiCad parser",
        "board_rectangles": rects,
        "board_footprints": len(re.findall(r'\(footprint\s', board)),
        "board_tracks": len(re.findall(r'\(segment\s', board)),
        "board_vias": len(re.findall(r'\(via\s', board)),
        "schematic_symbols": len(re.findall(r'\(symbol\s', schematic)),
        "schematic_wires": len(re.findall(r'\(wire\s', schematic)),
        "coupled_inductor_statements": [x for x in code if x[0].upper()=="K"],
        "diode_statements": [x for x in code if x[0].upper()=="D"],
        "forced_output_sources": [x for x in code if x.upper().startswith("V_OUT_IDEAL ")],
        "application_ready_badge": assessment.prototype_ready,
        "effective_validation_count": len(summaries),
        "effective_not_evaluated_count": sum(e["effective_status"]=="not_evaluated" for e in summaries),
        "independent_engineering_performance": "NOT_EVALUATED",
    }
    write_json(out / "static-findings.json", static)

    # Native CAD reads the existing solid; all outputs stay in this new report.
    freecad = Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
    cad = {"status": "NOT_EVALUATED", "reason": "FreeCAD executable unavailable"}
    if freecad.is_file():
        script = out / "inspect_existing_step.py"
        script.write_text("import Part, json\nfrom pathlib import Path\n"
                          f"shape = Part.read({str(ws / 'mechanical/bobbin.step')!r})\n"
                          "b=shape.BoundBox\n"
                          "data={'status':'READ','x_mm':b.XLength,'y_mm':b.YLength,'z_mm':b.ZLength,"
                          "'volume_mm3':shape.Volume,'valid':shape.isValid()}\n"
                          f"Path({str(out / 'step-bounds.json')!r}).write_text(json.dumps(data,indent=2))\n",
                          encoding="utf-8")
        try:
            result = subprocess.run([str(freecad), str(script)], cwd=out, capture_output=True,
                                    text=True, timeout=45, shell=False)
            (out / "freecad-read.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
            if result.returncode == 0 and (out / "step-bounds.json").is_file():
                cad = json.loads((out / "step-bounds.json").read_text())
            else:
                cad = {"status":"NOT_EVALUATED", "reason":"Native STEP read failed", "exit_code":result.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            cad = {"status":"NOT_EVALUATED", "reason":str(exc)}
    write_json(out / "mechanical-audit.json", cad)

    # Reuse the application's waveform parser on existing raw data. This is not
    # a new solve or an assessment of the proposed future circuit.
    waveform = {"status": "NOT_EVALUATED"}
    try:
        from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms, calculate_waveform_metrics
        waves = parse_ascii_raw_waveforms(ws / "simulations/circuit.raw")
        stats = calculate_waveform_metrics(waves)
        waveform = {"status":"PARSED_EXISTING_OUTPUT_ONLY", "points":len(waves.get("time", [])),
                    "metrics":stats, "limitation":"Ideal output source invalidates converter regulation/ripple inference"}
    except (OSError, ValueError, ImportError) as exc:
        waveform = {"status":"NOT_EVALUATED", "reason":str(exc)}
    write_json(out / "existing-waveform-metrics.json", waveform)

    # These are explicit packaging assumptions, never electrical clearances.
    dims = {
        "units":"m", "external":[.045,.028,.013], "wall_assumption":.0005,
        "interior":[.044,.027,.012], "board_candidate":[.042,.025,.001],
        "board_edge_mechanical_margin_each":.001,
        "bottom_mechanical_allowance":.001, "top_mechanical_allowance":.001,
        "component_height_budget":.009,
        "transformer_reservation":[.021,.017,.0085],
        "assumption_notice":"No insulation, creepage, clearance, thermal or winding-fit verification",
        "pcb_footprint_area_ratio_to_old":(.042*.025)/(.050*.032),
        "side_by_side_width_with_5mm_barrier_and_10mm_hv":.021+.005+.010,
    }
    assert abs(dims["interior"][2] - sum([dims["bottom_mechanical_allowance"], .001,
               dims["component_height_budget"], dims["top_mechanical_allowance"]])) < 1e-12
    assert dims["side_by_side_width_with_5mm_barrier_and_10mm_hv"] > .025
    write_json(out / "packaging-assumptions-si.json", dims)
    draw(out)
    after = hashes(root / "products")
    write_json(out / "product-files-after.json", after)
    unchanged = before == after
    write_json(out / "preservation-check.json", {"products_unchanged":unchanged,
        "checked_files":len(before), "checked_at_utc":datetime.now(timezone.utc).isoformat(),
        "notice":"Historical approvals and validations preserved; none created by this audit"})
    if not unchanged:
        raise RuntimeError("Product files changed during audit; investigate before relying on this snapshot")
    print(json.dumps({"output":str(out),"static":static,"cad":cad,"product_files_unchanged":unchanged},indent=2))


def draw(out):
    """Dimensioned native SVG of proposed space reservations, not a PCB design."""
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="830" viewBox="0 0 1100 830">
<style>text{font-family:Arial,sans-serif;fill:#20304a} .small{font-size:14px}.label{font-size:16px}.title{font-size:25px;font-weight:bold} .dim{stroke:#435673;stroke-width:1.5} .warn{fill:#a33321}</style>
<rect width="1100" height="830" fill="#f7f9fc"/>
<text x="40" y="45" class="title">SV-1000 · compact packaging feasibility</text>
<text x="40" y="72" class="label">Proposed reservations only · 11 November 2026 · all drawing dimensions in mm</text>
<text x="40" y="100" class="small warn">NOT a routed board or verified insulation design. Geometry alone does not establish feasibility.</text>
<g transform="translate(70 155)">
<rect width="540" height="336" rx="8" fill="#e2e8f1" stroke="#263b58" stroke-width="2"/>
<rect x="6" y="6" width="528" height="324" fill="white" stroke="#92a3bd" stroke-dasharray="5 4"/>
<rect x="18" y="18" width="504" height="300" fill="#edf7f3" stroke="#31876e" stroke-width="2"/>
<text x="25" y="39" class="small">42 × 25 candidate board</text>
<rect x="162" y="66" width="252" height="204" fill="#dbe8fb" stroke="#31609b" stroke-width="2"/>
<text x="180" y="147" class="label">Transformer reservation</text>
<text x="211" y="174" class="label">21 × 17 × 8.5</text>
<text x="181" y="199" class="small">EFD15 family study candidate</text>
<text x="174" y="226" class="small">Winding / isolation not established</text>
<rect x="30" y="66" width="120" height="108" fill="#faf0cb" stroke="#b88a24"/>
<text x="39" y="107" class="small">Control + aux</text><text x="50" y="132" class="small">10 × 9</text>
<rect x="30" y="186" width="120" height="108" fill="#faf0cb" stroke="#b88a24"/>
<text x="41" y="225" class="small">Input + switch</text><text x="50" y="250" class="small">10 × 9</text>
<rect x="426" y="42" width="84" height="252" fill="#f8ded7" stroke="#b6654f"/>
<text x="468" y="168" class="small" text-anchor="middle" transform="rotate(-90 468 168)">HV reserve 7 × 21 — fit unresolved</text>
<line x1="0" y1="-25" x2="540" y2="-25" class="dim"/><text x="231" y="-33" class="label">45 outside</text>
<line x1="-25" y1="0" x2="-25" y2="336" class="dim"/><text x="-35" y="207" class="label" transform="rotate(-90 -35 207)">28 outside</text>
</g>
<text x="660" y="165" class="label">Assumed mechanical budget</text>
<text x="660" y="197" class="small">Outside: 45 × 28 × 13</text>
<text x="660" y="224" class="small">Walls: 0.5 each (unselected enclosure)</text>
<text x="660" y="251" class="small">Interior: 44 × 27 × 12</text>
<text x="660" y="278" class="small">Board: 42 × 25 × 1.0 (proposal)</text>
<text x="660" y="305" class="small">Board-edge gap: 1.0 each (mechanical only)</text>
<text x="660" y="332" class="small">Top + bottom allowances: 1.0 each</text>
<text x="660" y="359" class="small">Component height budget: 9.0</text>
<text x="660" y="402" class="small warn">No allowance yet proves HV separation.</text>
<text x="660" y="429" class="small warn">Connectors / potting / tolerances unresolved.</text>
<text x="40" y="545" class="label">Section height budget · 13 total</text>
<rect x="70" y="570" width="540" height="156" fill="#e2e8f1" stroke="#263b58"/>
<rect x="76" y="576" width="528" height="144" fill="white" stroke="#92a3bd"/>
<rect x="88" y="696" width="504" height="12" fill="#31876e"/>
<rect x="232" y="594" width="252" height="102" fill="#dbe8fb" stroke="#31609b"/>
<text x="262" y="649" class="small">8.5 tall reservation</text>
<text x="660" y="593" class="small">12 internal = 1 bottom + 1 PCB</text>
<text x="660" y="620" class="small">+ 9 component budget + 1 top</text>
<text x="660" y="664" class="small warn">Existing bobbin: 22 dia × 16 tall — does not fit</text>
<text x="40" y="773" class="small">A continuous 5-wide side-by-side barrier plus a 21-wide transformer and 10-wide HV area needs 36 mm.</text>
<text x="40" y="801" class="small">That exceeds the 25 mm board width. Isolation geometry requires a separate redesign; no slot is silently waived.</text>
</svg>'''
    (out / "compact-space-concept.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
