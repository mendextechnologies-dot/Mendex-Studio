"""Mendex local engineering core CLI v2.1.

Provides standardized, AI-agent-independent command-line interface for:
- VS Code + OpenAI Codex
- Anthropic Claude Code
- Human engineers and scripts
All commands route to authoritative core services.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import ValidationError

from .models import Category, Specification
from .paths import default_data_root
from .service import StudioError, StudioService
from .controller import MendexEngineeringController


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mendex",
        description="Mendex Engineering Studio Core CLI v2.1",
    )
    parser.add_argument("--root", type=Path, default=None, help="Mendex data root directory (default: Mendex project root or MENDEX_DATA_ROOT)")
    parser.add_argument("--json", action="store_true", help="Ensure JSON output")

    commands = parser.add_subparsers(dest="command", required=True)

    # -------------------------------------------------------------------------
    # LEGACY COMMANDS (PRESERVED FOR BACKWARD COMPATIBILITY)
    # -------------------------------------------------------------------------
    commands.add_parser("products")
    del_prod = commands.add_parser("delete-product", help="Delete product and all revisions")
    del_prod.add_argument("product_id", help="Product UUID or code to delete")
    commands.add_parser("tools")
    commands.add_parser("plugins")

    rules = commands.add_parser("rules")
    rules.add_argument("--revision")

    request = commands.add_parser("request-simulation")
    request.add_argument("--revision", required=True)
    request.add_argument("--tool", required=True)

    runs = commands.add_parser("runs")
    runs.add_argument("--revision", required=True)

    export = commands.add_parser("export-specification")
    export.add_argument("--revision", required=True)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--root", type=Path, dest="doctor_root")
    doctor.add_argument("--export", action="store_true")

    for name in ("open-vscode", "open-file"):
        launch = commands.add_parser(name)
        launch.add_argument("--revision", required=True)
        if name == "open-file":
            launch.add_argument("path", help="Path relative to the selected revision workspace")

    validation = commands.add_parser("validation")
    validation.add_argument("--revision", required=True)

    report = commands.add_parser("report")
    report.add_argument("--revision")

    for name in ("pcb-files", "pcb-checks", "pcb-import", "pcb-open", "pcb-check", "pcb-notes"):
        pcb = commands.add_parser(name)
        pcb.add_argument("--revision", required=True)
        if name in {"pcb-import", "pcb-open", "pcb-check"}:
            pcb.add_argument("path", help="Source file for import; otherwise path relative to revision workspace")
        if name == "pcb-check":
            pcb.add_argument("--kind", choices=("erc", "drc"), required=True)
        if name == "pcb-notes":
            pcb.add_argument("--file", type=Path, help="UTF-8 notes to save; omit to read notes")

    create = commands.add_parser("create")
    create.add_argument("code")
    create.add_argument("name")
    create.add_argument("--owner", required=True)
    create.add_argument("--category", choices=[c.value for c in Category], default="transformer")

    # -------------------------------------------------------------------------
    # V2.1 STRUCTURED ENGINEERING COMMANDS
    # -------------------------------------------------------------------------
    # 0. ENGINEERING PROJECTS (v2.1 Project-Oriented CLI)
    commands.add_parser("projects", help="List all engineering projects")

    c_proj = commands.add_parser("create-project", help="Create a new engineering project")
    c_proj.add_argument("name", help="Project full title")
    c_proj.add_argument("--code", default=None, help="Project code (e.g. PRJ-001)")
    c_proj.add_argument("--category", default="dc_dc_converter", help="Project category")
    c_proj.add_argument("--owner", default="Engineer", help="Lead engineer or team name")
    c_proj.add_argument("--description", default="", help="Project description")

    d_proj = commands.add_parser("delete-project", help="Delete an engineering project")
    d_proj.add_argument("project_id", help="Project UUID or code to delete")

    proj_cmd = commands.add_parser("project", help="Engineering project operations")
    proj_sub = proj_cmd.add_subparsers(dest="subaction", required=True)
    proj_sub.add_parser("list", help="List all engineering projects")
    p_get = proj_sub.add_parser("show", help="Show project details, specifications, and revisions")
    p_get.add_argument("project_id", help="Project UUID or code")
    p_spec = proj_sub.add_parser("spec", help="Get project electrical specifications")
    p_spec.add_argument("project_id", help="Project UUID or code")
    p_save_spec = proj_sub.add_parser("save-spec", help="Save electrical specification to project")
    p_save_spec.add_argument("project_id", help="Project UUID or code")
    p_save_spec.add_argument("spec_json", help="JSON string or path to JSON file")

    # 1. WORKSPACE
    ws_cmd = commands.add_parser("workspace", help="Engineering workspace operations")
    ws_sub = ws_cmd.add_subparsers(dest="subaction", required=True)
    ws_sub.add_parser("list", help="List all engineering workspaces")
    ws_create = ws_sub.add_parser("create", help="Create a new engineering workspace")
    ws_create.add_argument("name", help="Workspace title")
    ws_create.add_argument("--description", default="", help="Workspace description")
    ws_create.add_argument("--product-id", default=None, help="Associated product ID")
    ws_status = ws_sub.add_parser("status", help="Get workspace engineering status")
    ws_status.add_argument("workspace_id", help="Workspace UUID")

    # 2. SPECIFICATION
    spec_cmd = commands.add_parser("specification", help="Engineering specification validation")
    spec_sub = spec_cmd.add_subparsers(dest="subaction", required=True)
    spec_val = spec_sub.add_parser("validate", help="Validate electrical specification parameters")
    spec_val.add_argument("spec_json", help="JSON string or path to JSON file containing specification")
    spec_save = spec_sub.add_parser("save", help="Save specification to product revision")
    spec_save.add_argument("revision_id", help="Product revision UUID")
    spec_save.add_argument("spec_json", help="JSON string or path to JSON file")

    # 3. DESIGN
    design_cmd = commands.add_parser("design", help="Design synthesis and candidate exploration")
    design_sub = design_cmd.add_subparsers(dest="subaction", required=True)
    d_gen = design_sub.add_parser("generate", help="Synthesize candidate topologies and generate native CAD artifacts")
    d_gen.add_argument("--workspace", default=None, help="Target workspace or project ID")
    d_gen.add_argument("--project", default=None, help="Target engineering project ID")
    d_gen.add_argument("--title", required=True, help="Design title")
    d_gen.add_argument("--category", default="dc_dc_converter", help="Design category")
    d_gen.add_argument("--vin-nom", type=float, default=24.0, help="Nominal input voltage (V)")
    d_gen.add_argument("--vin-min", type=float, default=None, help="Minimum input voltage (V)")
    d_gen.add_argument("--vin-max", type=float, default=None, help="Maximum input voltage (V)")
    d_gen.add_argument("--vout", type=float, default=5.0, help="Regulated output voltage (V)")
    d_gen.add_argument("--iout", type=float, default=4.0, help="Rated output current (A)")
    d_gen.add_argument("--fsw", type=float, default=100000.0, help="Switching frequency (Hz)")
    d_gen.add_argument("--ripple", type=float, default=0.05, help="Output voltage ripple (V)")
    d_gen.add_argument("--isolation", type=float, default=None, help="Isolation test voltage (V)")
    d_gen.add_argument("--product-id", default=None, help="Optional linked product ID")

    d_show = design_sub.add_parser("show", help="Show engineering design details and components")
    d_show.add_argument("design_id", help="Design UUID")
    d_cands = design_sub.add_parser("candidates", help="List synthesized candidate topologies")
    d_cands.add_argument("design_id", help="Design UUID")

    # 4. CALCULATE
    calc_cmd = commands.add_parser("calculate", help="Pure deterministic engineering calculations")
    calc_sub = calc_cmd.add_subparsers(dest="subaction", required=True)
    c_dowell = calc_sub.add_parser("dowell", help="Dowell high-frequency AC winding factor")
    c_dowell.add_argument("--freq", type=float, required=True, help="Frequency in Hz")
    c_dowell.add_argument("--layers", type=int, required=True, help="Number of winding layers")
    c_dowell.add_argument("--wire-dia", type=float, required=True, help="Conductor diameter in mm")
    c_dowell.add_argument("--porosity", type=float, required=True, help="Layer porosity factor")
    c_dowell.add_argument("--rdc", type=float, required=True, help="DC resistance in Ohms")
    c_dowell.add_argument("--temp", type=float, required=True, help="Temperature in deg C")

    c_losses = calc_sub.add_parser("losses", help="Semiconductor conduction and switching losses")
    c_losses.add_argument("--part", default=None, help="Part number")
    c_losses.add_argument("--rdson", type=float, required=True, help="Rds(on) in Ohms")
    c_losses.add_argument("--irms", type=float, required=True, help="RMS current in Amperes")
    c_losses.add_argument("--duty", type=float, required=True, help="Duty cycle [0.0 - 1.0]")
    c_losses.add_argument("--eon", type=float, required=True, help="Turn-on energy in Joules")
    c_losses.add_argument("--eoff", type=float, required=True, help="Turn-off energy in Joules")
    c_losses.add_argument("--freq", type=float, required=True, help="Switching frequency in Hz")

    c_stein = calc_sub.add_parser("steinmetz", help="Steinmetz magnetic core loss calculation")
    c_stein.add_argument("--material", default=None, help="Core material name")
    c_stein.add_argument("--freq", type=float, required=True, help="Frequency in Hz")
    c_stein.add_argument("--bmax", type=float, required=True, help="Peak flux density in Tesla")
    c_stein.add_argument("--volume", type=float, required=True, help="Core volume in m^3")
    c_stein.add_argument("--k", type=float, required=True, help="Steinmetz k parameter")
    c_stein.add_argument("--alpha", type=float, required=True, help="Steinmetz alpha parameter")
    c_stein.add_argument("--beta", type=float, required=True, help="Steinmetz beta parameter")

    c_flyback = calc_sub.add_parser("flyback", help="First-principles flyback transformer sizing")
    c_flyback.add_argument("--vin-min", type=float, required=True, help="Min input voltage (V)")
    c_flyback.add_argument("--vin-nom", type=float, required=True, help="Nominal input voltage (V)")
    c_flyback.add_argument("--vout", type=float, required=True, help="Output voltage (V)")
    c_flyback.add_argument("--iout", type=float, required=True, help="Output current (A)")
    c_flyback.add_argument("--freq", type=float, required=True, help="Frequency (Hz)")
    c_flyback.add_argument("--dmax", type=float, required=True, help="Max duty cycle")
    c_flyback.add_argument("--eff", type=float, required=True, help="Target efficiency")
    c_flyback.add_argument("--bmax", type=float, required=True, help="Max flux density (T)")
    c_flyback.add_argument("--ae", type=float, required=True, help="Core effective cross section (mm^2)")

    # 5. SIMULATION
    sim_cmd = commands.add_parser("simulation", help="Industrial simulation dispatch and monitoring")
    sim_sub = sim_cmd.add_subparsers(dest="subaction", required=True)
    s_run = sim_sub.add_parser("run", help="Execute simulation run (LTspice / FEMM)")
    s_run.add_argument("--workspace", default=None, help="Workspace ID")
    s_run.add_argument("--project", default=None, help="Engineering project ID")
    s_run.add_argument("--tool", choices=("ltspice", "femm"), default="ltspice", help="Simulation solver")
    s_run.add_argument("--netlist", default=None, help="Optional netlist or script name")
    s_run.add_argument("--duration", type=float, default=0.002, help="Simulation duration (s)")
    s_list = sim_sub.add_parser("list", help="List simulation jobs")
    s_list.add_argument("--workspace", default=None, help="Filter by workspace ID")

    # 6. ARTIFACT
    art_cmd = commands.add_parser("artifact", help="Engineering artifact inspection and launch")
    art_sub = art_cmd.add_subparsers(dest="subaction", required=True)
    a_list = art_sub.add_parser("list", help="List native artifacts in workspace")
    a_list.add_argument("--workspace", required=True, help="Workspace ID")
    a_open = art_sub.add_parser("open", help="Open native artifact in external CAD tool")
    a_open.add_argument("--workspace", required=True, help="Workspace ID")
    a_open.add_argument("--file", required=True, help="Artifact relative path")

    # 7. TOOL
    tool_cmd = commands.add_parser("tool", help="Engineering host tool discovery and health")
    tool_sub = tool_cmd.add_subparsers(dest="subaction", required=True)
    tool_sub.add_parser("list", help="List all host engineering tools")
    t_chk = tool_sub.add_parser("check", help="Live diagnostic check on a specific tool")
    t_chk.add_argument("tool_id", help="Tool identifier (e.g., ltspice, kicad, femm)")
    t_open = tool_sub.add_parser("open", help="Launch native tool with a design file")
    t_open.add_argument("tool_id", help="Tool identifier")
    t_open.add_argument("file_path", help="Target design file path")

    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (StudioError, ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"error": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}), file=sys.stderr)
        return 1


def _parse_json_or_file(text: str) -> Dict[str, Any]:
    cand = Path(text)
    if cand.is_file():
        return json.loads(cand.read_text(encoding="utf-8"))
    return json.loads(text)


def execute(args):
    root = getattr(args, "doctor_root", None) or args.root or default_data_root()
    service = StudioService(root)
    controller = MendexEngineeringController(root)

    # -------------------------------------------------------------------------
    # V2.1 STRUCTURED COMMANDS EXECUTION
    # -------------------------------------------------------------------------
    # 0. PROJECTS EXECUTION
    if args.command == "projects":
        print(json.dumps(controller.list_projects(), indent=2))
        return 0

    elif args.command == "create-project":
        res = controller.create_project(
            name=args.name,
            code=args.code,
            category=args.category,
            owner=args.owner,
            description=args.description,
        )
        print(json.dumps(res, indent=2))
        return 0

    elif args.command == "delete-project":
        res = controller.delete_project(args.project_id)
        print(json.dumps(res, indent=2))
        return 0

    elif args.command == "project":
        if args.subaction == "list":
            print(json.dumps(controller.list_projects(), indent=2))
        elif args.subaction == "show":
            print(json.dumps(controller.get_project(args.project_id), indent=2))
        elif args.subaction == "spec":
            print(json.dumps(controller.get_project_specifications(args.project_id), indent=2))
        elif args.subaction == "save-spec":
            data = _parse_json_or_file(args.spec_json)
            print(json.dumps(controller.save_project_specification(args.project_id, data), indent=2))
        return 0

    elif args.command == "workspace":
        if args.subaction == "list":
            print(json.dumps(controller.list_workspaces(), indent=2))
        elif args.subaction == "create":
            print(json.dumps(controller.create_workspace(args.name, args.description, args.product_id), indent=2))
        elif args.subaction == "status":
            print(json.dumps(controller.get_workspace_status(args.workspace_id), indent=2))
        return None

    elif args.command == "specification":
        if args.subaction == "validate":
            data = _parse_json_or_file(args.spec_json)
            res = controller.validate_specification(data)
            print(json.dumps(res, indent=2))
            if not res.get("valid", False):
                sys.exit(1)
            return None
        elif args.subaction == "save":
            data = _parse_json_or_file(args.spec_json)
            print(json.dumps(controller.save_specification(args.revision_id, data), indent=2))
        return None

    elif args.command == "design":
        if args.subaction == "generate":
            res = controller.generate_design(
                workspace_id=args.project or args.workspace,
                title=args.title,
                category=args.category,
                vin_nom=args.vin_nom,
                vin_min=args.vin_min,
                vin_max=args.vin_max,
                vout=args.vout,
                iout=args.iout,
                fsw_hz=args.fsw,
                ripple_v=args.ripple,
                isolation_v=args.isolation,
                product_id=args.product_id,
            )
            print(json.dumps(res, indent=2))
        elif args.subaction == "show":
            print(json.dumps(controller.get_design(args.design_id), indent=2))
        elif args.subaction == "candidates":
            print(json.dumps(controller.list_design_candidates(args.design_id), indent=2))
        return None

    elif args.command == "calculate":
        if args.subaction == "dowell":
            params = {
                "frequency_hz": args.freq,
                "layers": args.layers,
                "conductor_diameter_mm": args.wire_dia,
                "layer_porosity_factor": args.porosity,
                "r_dc_ohm": args.rdc,
                "temperature_c": args.temp,
            }
            print(json.dumps(controller.run_calculation("dowell", params), indent=2))
        elif args.subaction == "losses":
            params = {
                "part_number": args.part,
                "r_ds_on_ohm": args.rdson,
                "i_rms_a": args.irms,
                "duty_cycle": args.duty,
                "e_on_j": args.eon,
                "e_off_j": args.eoff,
                "frequency_hz": args.freq,
            }
            print(json.dumps(controller.run_calculation("losses", params), indent=2))
        elif args.subaction == "steinmetz":
            params = {
                "material": args.material,
                "frequency_hz": args.freq,
                "b_peak_t": args.bmax,
                "core_volume_m3": args.volume,
                "k": args.k,
                "alpha": args.alpha,
                "beta": args.beta,
            }
            print(json.dumps(controller.run_calculation("steinmetz", params), indent=2))
        elif args.subaction == "flyback":
            params = {
                "vin_min_v": args.vin_min,
                "vin_nom_v": args.vin_nom,
                "vout_v": args.vout,
                "iout_a": args.iout,
                "frequency_hz": args.freq,
                "d_max": args.dmax,
                "efficiency": args.eff,
                "b_max_t": args.bmax,
                "core_ae_mm2": args.ae,
            }
            print(json.dumps(controller.run_calculation("flyback", params), indent=2))
        return None

    elif args.command == "simulation":
        if args.subaction == "run":
            res = controller.run_simulation(
                workspace_id=args.project or args.workspace,
                tool=args.tool,
                netlist_name=args.netlist,
                duration_s=args.duration,
            )
            print(json.dumps(res, indent=2))
        elif args.subaction == "list":
            print(json.dumps(controller.list_simulations(args.workspace), indent=2))
        return None

    elif args.command == "artifact":
        if args.subaction == "list":
            print(json.dumps(controller.list_design_artifacts(args.workspace), indent=2))
        elif args.subaction == "open":
            print(json.dumps(controller.open_artifact(args.workspace, args.file), indent=2))
        return None

    elif args.command == "tool":
        if args.subaction == "list":
            print(json.dumps(controller.list_tools(), indent=2))
        elif args.subaction == "check":
            print(json.dumps(controller.check_tool(args.tool_id), indent=2))
        elif args.subaction == "open":
            print(json.dumps(controller.open_tool_file(args.tool_id, args.file_path), indent=2))
        return None

    # -------------------------------------------------------------------------
    # LEGACY COMMANDS EXECUTION
    # -------------------------------------------------------------------------
    elif args.command == "products":
        print(json.dumps([p.model_dump(mode="json") for p in service.list_products()], indent=2))
    elif args.command == "delete-product":
        print(json.dumps(controller.delete_product(args.product_id), indent=2))
    elif args.command == "tools":
        print(json.dumps([t.model_dump(mode="json") for t in service.list_tools()], indent=2))
    elif args.command == "plugins":
        print(json.dumps(service.list_plugins(), indent=2))
    elif args.command == "rules":
        print(json.dumps([r.model_dump(mode="json") for r in service.list_rules(args.revision)], indent=2))
    elif args.command == "request-simulation":
        print(service.request_simulation(args.revision, args.tool).model_dump_json(indent=2))
    elif args.command == "runs":
        print(json.dumps([r.model_dump(mode="json") for r in service.list_runs(args.revision)], indent=2))
    elif args.command == "export-specification":
        print(json.dumps({"path": str(service.export_specification(args.revision))}))
    elif args.command == "validation":
        print(json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in service.validation_summary(args.revision)], indent=2))
    elif args.command == "report":
        rev_id = args.revision
        if not rev_id:
            prods = service.list_products()
            if prods:
                revs = service.list_revisions(prods[0].product_id)
                if revs:
                    rev_id = str(revs[0].revision_id)
        if not rev_id:
            raise ValueError("No revision specified or available to generate report.")
        print(service.generate_report(rev_id).model_dump_json(indent=2))
    elif args.command == "pcb-files":
        print(json.dumps(service.pcb.overview(args.revision), indent=2))
    elif args.command == "pcb-checks":
        print(json.dumps(service.pcb.list_checks(args.revision), indent=2))
    elif args.command == "pcb-import":
        print(json.dumps({"path": service.pcb.import_file(args.revision, args.path)}))
    elif args.command == "pcb-open":
        print(json.dumps({"opened": service.pcb.open_file(args.revision, args.path)}))
    elif args.command == "pcb-notes":
        if args.file:
            print(json.dumps({"path": service.pcb.save_review_notes(args.revision, args.file.read_text(encoding="utf-8"))}))
        else:
            print(json.dumps({"notes": service.pcb.review_notes(args.revision)}))
    elif args.command == "pcb-check":
        result = service.pcb.run_check(args.revision, args.path, args.kind)
        print(json.dumps(result, indent=2))
        return 0 if result["effective_status"] == "CLEAR" else (2 if result["effective_status"] == "NOT_EVALUATED" else 1)
    elif args.command == "doctor":
        diagnostics = service.diagnostics()
        if args.export:
            diagnostics["export_path"] = str(service.export_diagnostics())
        print(json.dumps(diagnostics, indent=2))
        return 0 if diagnostics["framework_ready"] else 1
    elif args.command == "open-vscode":
        print(json.dumps(service.open_in_vscode(args.revision), indent=2))
    elif args.command == "open-file":
        print(json.dumps({"opened": service.open_project_file(args.revision, args.path)}))
    else:
        print(service.create_product(args.code, args.name, args.category, args.owner).model_dump_json(indent=2))


if __name__ == "__main__":
    sys.exit(main())
