from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class FreeCADAdapter(BaseToolAdapter):
    """Adapter for FreeCAD mechanical CAD console (FreeCADCmd)."""

    def __init__(self):
        super().__init__(
            tool_id="freecad",
            name="FreeCAD",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="LGPLv2+",
            official_url="https://www.freecad.org/",
            candidate_binaries=["FreeCADCmd.exe", "FreeCADCmd"],
            candidate_paths=["FreeCAD*/bin/FreeCADCmd.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["export_step", "generate_bobbin", "export_stl"]
