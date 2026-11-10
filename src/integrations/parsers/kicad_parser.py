from __future__ import annotations

import json
from pathlib import Path


def parse_kicad_drc_json(report_path: Path) -> dict[str, int]:
    """Parses a KiCad CLI JSON DRC/ERC report, checking top-level and sheet-level violations."""
    if not report_path.exists():
        raise FileNotFoundError(f"KiCad report not found: {report_path}")

    data = json.loads(report_path.read_text(encoding="utf-8-sig"))
    fields = ("violations", "unconnected", "unconnected_items", "schematic_parity", "sheets")
    if not isinstance(data, dict) or not any(key in data for key in fields):
        raise ValueError("Not a recognized KiCad JSON check report")

    counts = {"violation_count": 0, "unconnected_count": 0, "parity_count": 0}

    def visit(node):
        if not isinstance(node, dict):
            raise ValueError("Invalid KiCad sheet report")
        for key in fields:
            values = node.get(key, [])
            if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
                raise ValueError(f"Invalid KiCad report field: {key}")
            if key == "sheets":
                for sheet in values:
                    visit(sheet)
            else:
                target = "violation_count" if key == "violations" else (
                    "parity_count" if key == "schematic_parity" else "unconnected_count")
                counts[target] += len(values)

    visit(data)
    return {**counts, "total_issues": sum(counts.values())}
