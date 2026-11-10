from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class QucsSAdapter(BaseToolAdapter):
    """Adapter for Qucs-S circuit simulator."""

    def __init__(self):
        super().__init__(
            tool_id="qucs-s",
            name="Qucs-S",
            kind=ToolKind.APPLICATION,
            category="high",
            license_name="GPLv2+",
            official_url="https://ra3xdh.github.io/",
            candidate_binaries=["qucs-s.exe", "qucs-s"],
            candidate_paths=["qucs-s/bin/qucs-s.exe", "Qucs-S*/bin/qucs-s.exe", "qucs-s*/bin/qucs-s.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["batch_simulate", "netlist_export"]
