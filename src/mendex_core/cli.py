import argparse
import json
from pathlib import Path

from .models import Category
from .service import StudioService


def main():
    parser = argparse.ArgumentParser(description="Mendex local engineering core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("products")
    commands.add_parser("tools")
    validation = commands.add_parser("validation")
    validation.add_argument("--revision", required=True)
    report = commands.add_parser("report")
    report.add_argument("--revision", required=True)
    create = commands.add_parser("create")
    create.add_argument("code")
    create.add_argument("name")
    create.add_argument("--owner", required=True)
    create.add_argument("--category", choices=[c.value for c in Category], default="transformer")
    args = parser.parse_args()
    service = StudioService(args.root)
    if args.command == "products":
        print(json.dumps([p.model_dump(mode="json") for p in service.list_products()], indent=2))
    elif args.command == "tools":
        print(json.dumps([t.model_dump(mode="json") for t in service.list_tools()], indent=2))
    elif args.command == "validation":
        print(json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in service.validation_summary(args.revision)], indent=2))
    elif args.command == "report":
        print(service.generate_report(args.revision).model_dump_json(indent=2))
    else:
        print(service.create_product(args.code, args.name, args.category, args.owner).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
