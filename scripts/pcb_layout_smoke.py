"""Native read/plot smoke on a disposable copy; never modifies the supplied board."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from copper_kicad import sexpr
from mendex_core.pcb import file_hash
from mendex_core.service import StudioService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New disposable directory; must not exist")
    args = parser.parse_args()
    source_hash = file_hash(args.source)
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = args.output / "fixture.kicad_pcb"
    tree = sexpr.loads(args.source.read_text(encoding="utf-8-sig"))
    if sexpr.head(tree) != "kicad_pcb":
        raise ValueError("Expected KiCad PCB")
    # Strip only the disposable fixture's copper to exercise guarded placement moves.
    tree[:] = [n for n in tree if not isinstance(n, list) or (
        sexpr.head(n) not in {"segment", "arc", "via", "zone"}
        or (sexpr.head(n) == "zone" and sexpr.find(n, "keepout") is not None))]
    fixture.write_text(sexpr.dumps(tree) + "\n", encoding="utf-8")
    studio = StudioService(args.output / "studio")
    try:
        product = studio.create_product("LAYOUT-SMOKE", "Disposable layout fixture", "pcb", "Software smoke")
        revision_id = product.active_revision_id
        relative_path = studio.pcb.import_file(revision_id, fixture)
        analysis = studio.pcb_layout.analyze(revision_id, relative_path)
        component = next(c for c in analysis["components"] if not c["locked"])
        request = {
            "relative_path": relative_path, "expected_context_sha256": analysis["context_sha256"],
            "moves": [{"reference": component["reference"], "x_m": component["x_m"] + .001, "y_m": component["y_m"]}],
            "rationale": "Native serialization smoke: translate one unlocked component by 1 mm on disposable unrouted fixture",
            "fixed_references": [c["reference"] for c in analysis["components"] if c["reference"] != component["reference"]],
        }
        preview = studio.pcb_layout.preview_plan(revision_id, request)
        (args.output / "placement-preview.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
        candidate = studio.pcb_layout.create_candidate(revision_id, request)
        tool = studio.lifecycle.kicad
        if not tool.is_available():
            raise RuntimeError("KiCad CLI unavailable; native smoke NOT_EVALUATED")
        version = subprocess.run([str(tool.kicad_cli), "--version"], capture_output=True, text=True, timeout=10, check=True)
        working = args.output / "render-input"
        shutil.copytree(Path(candidate["folder"]) / "output", working)
        command = [str(tool.kicad_cli), "pcb", "export", "svg", "--layers", "F.Cu,Edge.Cuts", "--mode-single",
                   "--output", str((args.output / "candidate.svg").resolve()), str((working / "fixture.kicad_pcb").resolve())]
        checked = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (args.output / "stdout.log").write_text(checked.stdout, encoding="utf-8")
        (args.output / "stderr.log").write_text(checked.stderr, encoding="utf-8")
        result = {"source": str(args.source.resolve()), "source_sha256": source_hash,
                  "source_unchanged": file_hash(args.source) == source_hash,
                  "tool_version": version.stdout.strip(), "command": command, "exit_code": checked.returncode,
                  "svg_available": (args.output / "candidate.svg").is_file(),
                  "candidate_id": candidate["candidate_id"], "candidate_integrity": studio.pcb_layout.read_candidate(revision_id, candidate["candidate_id"])["integrity"],
                  "placement_constraints": candidate["placement_constraints"],
                  "evaluation_status": "NOT_EVALUATED", "notice": "Native file read/plot only; no DRC or engineering qualification"}
        (args.output / "smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if checked.returncode == 0 and result["svg_available"] and result["source_unchanged"] and result["candidate_integrity"] else 1
    finally:
        studio.integrations.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
