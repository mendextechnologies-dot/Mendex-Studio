import argparse
import json
from pathlib import Path
import sys

from pydantic import ValidationError

from .models import Category
from .service import StudioError, StudioService


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mendex local engineering core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("products")
    commands.add_parser("tools")
    commands.add_parser("plugins")
    rules = commands.add_parser("rules")
    rules.add_argument("--revision")
    ai = commands.add_parser("ai-availability")
    ai.add_argument("--revision", required=True)
    ai.add_argument("question")
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
    report.add_argument("--revision", required=True)
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
    args = parser.parse_args(argv)
    try:
        return execute(args)
    except (StudioError, ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"error": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}), file=sys.stderr)
        return 1


def execute(args):
    service = StudioService(getattr(args, "doctor_root", None) or args.root)
    if args.command == "products":
        print(json.dumps([p.model_dump(mode="json") for p in service.list_products()], indent=2))
    elif args.command == "tools":
        print(json.dumps([t.model_dump(mode="json") for t in service.list_tools()], indent=2))
    elif args.command == "plugins":
        print(json.dumps(service.list_plugins(), indent=2))
    elif args.command == "rules":
        print(json.dumps([r.model_dump(mode="json") for r in service.list_rules(args.revision)], indent=2))
    elif args.command == "ai-availability":
        print(service.ai_advice(args.revision, args.question).model_dump_json(indent=2))
    elif args.command == "request-simulation":
        print(service.request_simulation(args.revision, args.tool).model_dump_json(indent=2))
    elif args.command == "runs":
        print(json.dumps([r.model_dump(mode="json") for r in service.list_runs(args.revision)], indent=2))
    elif args.command == "export-specification":
        print(json.dumps({"path": str(service.export_specification(args.revision))}))
    elif args.command == "validation":
        print(json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in service.validation_summary(args.revision)], indent=2))
    elif args.command == "report":
        print(service.generate_report(args.revision).model_dump_json(indent=2))
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
