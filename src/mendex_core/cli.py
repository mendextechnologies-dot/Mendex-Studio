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
    elif args.command == "validation":
        print(json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in service.validation_summary(args.revision)], indent=2))
    elif args.command == "report":
        print(service.generate_report(args.revision).model_dump_json(indent=2))
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
