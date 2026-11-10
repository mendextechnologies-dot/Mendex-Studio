from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class FEMMResults(NamedTuple):
    metrics: dict[str, float]
    diagnostics: list[str]


def parse_femm_results(results_path: Path) -> FEMMResults:
    """Parses key-value simulation metrics extracted from a FEMM Lua run."""
    metrics: dict[str, float] = {}
    diagnostics: list[str] = []

    if not results_path.exists():
        diagnostics.append(f"FEMM results file not found: {results_path}")
        return FEMMResults(metrics=metrics, diagnostics=diagnostics)

    try:
        content = results_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            try:
                metrics[k] = float(v)
            except ValueError:
                diagnostics.append(f"Failed to parse numeric value for '{k}': {v}")
    except Exception as e:
        diagnostics.append(f"Error reading FEMM results: {e}")

    return FEMMResults(metrics=metrics, diagnostics=diagnostics)
