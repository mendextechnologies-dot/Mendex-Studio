"""Export/check new record contracts without rewriting historical/lifecycle schemas."""
import argparse
import json
from pathlib import Path

from mendex_core.engineering_records import calculations, models

MODEL_NAMES = ("ProjectQuery", "ProjectUpdate", "RevisionQuery", "RecordList", "RecordQuery", "Requirement",
               "RequirementsWrite", "CalculationWrite", "ArtifactWrite", "ValidationWrite", "JobQuery",
               "JobCancel", "JobArtifact", "ReportQuery", "ReportGenerate", "ReportExport")
CALCULATOR_NAMES = ("DowellInputs", "LossInputs", "SteinmetzInputs", "FlybackInputs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    destination = Path(__file__).resolve().parents[1] / "contracts" / "v3.1"
    entries = [getattr(models, name) for name in MODEL_NAMES] + [getattr(calculations, name) for name in CALCULATOR_NAMES]
    for model in entries:
        path = destination / ("records." + model.__name__ + ".schema.json")
        text = json.dumps(model.model_json_schema(), indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                raise SystemExit("Contract differs from canonical model: " + str(path))
        else:
            destination.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
    print(f"{'Verified' if args.check else 'Exported'} {len(entries)} engineering record contracts")


if __name__ == "__main__":
    main()
