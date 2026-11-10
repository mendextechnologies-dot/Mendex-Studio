from __future__ import annotations

import json
from pathlib import Path


def parse_kicad_drc_json(report_path: Path) -> dict[str, int]:
    """Parses a KiCad CLI JSON DRC/ERC report, checking top-level and sheet-level violations."""
    if not report_path.exists():
        raise FileNotFoundError(f"KiCad report not found: {report_path}")

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        violations = list(data.get("violations", []))
        unconnected = list(data.get("unconnected", []))
        
        # KiCad schematic ERC nests violations per sheet
        for sheet in data.get("sheets", []):
            if isinstance(sheet, dict):
                violations.extend(sheet.get("violations", []))
                unconnected.extend(sheet.get("unconnected", []))

        return {
            "violation_count": len(violations),
            "unconnected_count": len(unconnected),
            "total_issues": len(violations) + len(unconnected),
        }
    except Exception:
        # Fallback for plain text format
        text = report_path.read_text(encoding="utf-8", errors="replace")
        violation_count = text.count("** Found ")
        return {
            "violation_count": violation_count,
            "unconnected_count": 0,
            "total_issues": violation_count,
        }
