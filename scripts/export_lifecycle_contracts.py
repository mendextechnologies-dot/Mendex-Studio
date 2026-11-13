"""Export/check only new v3.1 schemas; never regenerate historical frozen contracts."""
import argparse
import json
from pathlib import Path

from mendex_core.engineering_lifecycle import models

NAMES = ("LifecycleDefinition", "StageDefinition", "Criterion", "DefinitionQuery",
         "RegisterDefinition", "LifecycleQuery", "HistoryQuery", "Enrollment", "StageCommand")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "contracts" / "v3.1"
    for name in NAMES:
        payload = json.dumps(getattr(models, name).model_json_schema(), indent=2) + "\n"
        path = destination / (name + ".schema.json")
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != payload:
                raise SystemExit(f"Contract differs from canonical model: {path}")
        else:
            destination.mkdir(exist_ok=True)
            path.write_text(payload, encoding="utf-8")
    print(f"{'Verified' if args.check else 'Exported'} {len(NAMES)} lifecycle contracts")


if __name__ == "__main__":
    main()
