from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class OpenModelicaAdapter(BaseToolAdapter):
    """Adapter for OpenModelica Compiler (omc)."""

    def __init__(self):
        super().__init__(
            tool_id="openmodelica",
            name="OpenModelica",
            kind=ToolKind.APPLICATION,
            category="high",
            license_name="OSMC-PL",
            official_url="https://openmodelica.org/",
            candidate_binaries=["omc.exe", "omc"],
            candidate_paths=["OpenModelica*/bin/omc.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["simulate_modelica", "check_model"]
