from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class KiCadAdapter(BaseToolAdapter):
    """Adapter for KiCad CLI (ERC/DRC and manufacturing export)."""

    def __init__(self):
        super().__init__(
            tool_id="kicad",
            name="KiCad CLI",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="GPLv3+",
            official_url="https://www.kicad.org/",
            candidate_binaries=["kicad-cli.exe", "kicad-cli"],
            candidate_paths=["KiCad/*/bin/kicad-cli.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["erc", "drc", "export_gerber", "export_step"]
