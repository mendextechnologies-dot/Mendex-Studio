from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class FEMMAdapter(BaseToolAdapter):
    """Adapter for Finite Element Method Magnetics (FEMM 4.2)."""

    def __init__(self):
        super().__init__(
            tool_id="femm",
            name="FEMM",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="Aladdin Free Public License",
            official_url="https://www.femm.info/",
            candidate_binaries=["femm.exe"],
            candidate_paths=["femm42/bin/femm.exe", "femm*/bin/femm.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["solve_2d_magnetic", "inductance_matrix", "core_loss"]
