from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind
from .base import BaseToolAdapter


class JupyterAdapter(BaseToolAdapter):
    """Adapter for Jupyter notebook execution (nbconvert)."""

    def __init__(self):
        super().__init__(
            tool_id="jupyter",
            name="Jupyter Notebook",
            kind=ToolKind.APPLICATION,
            category="high",
            license_name="Modified BSD",
            official_url="https://jupyter.org/",
            candidate_binaries=["jupyter.exe", "jupyter"],
            candidate_paths=["jupyter.exe", "Scripts/jupyter.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["execute_notebook", "export_html"]
