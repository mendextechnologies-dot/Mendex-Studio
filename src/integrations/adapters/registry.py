from __future__ import annotations

from typing import Dict, List
from integrations.contracts import ToolDescriptor, ToolAdapter
from .ltspice import LTspiceAdapter
from .kicad import KiCadAdapter
from .femm import FEMMAdapter
from .freecad import FreeCADAdapter
from .qucs_s import QucsSAdapter
from .ngspice import NgspiceAdapter
from .openmodelica import OpenModelicaAdapter
from .python_runtime import PythonRuntimeAdapter
from .jupyter import JupyterAdapter
from .git_adapter import GitAdapter
from .research_adapters import (
    SwitchLossDBAdapter,
    MagNetDatasetAdapter,
    MagNetMLBenchmarksAdapter,
    MagNetPrincetonAdapter,
)


class ToolRegistry:
    """Registry for currently supported engineering tools, datasets, and platforms."""

    def __init__(self):
        self._adapters: Dict[str, ToolAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        # 1. Core Engineering Tools
        self.register(LTspiceAdapter())
        self.register(PythonRuntimeAdapter())
        self.register(GitAdapter())
        self.register(KiCadAdapter())
        self.register(FEMMAdapter())
        self.register(FreeCADAdapter())

        # 2. High-Adoption Simulation, Tools & Research Resources
        self.register(QucsSAdapter())
        self.register(OpenModelicaAdapter())
        self.register(JupyterAdapter())
        self.register(SwitchLossDBAdapter())
        self.register(MagNetDatasetAdapter())
        self.register(MagNetMLBenchmarksAdapter())
        self.register(MagNetPrincetonAdapter())


    def register(self, adapter: ToolAdapter):
        tool_id = adapter.descriptor.tool_id
        if tool_id in self._adapters:
            raise ValueError(f"Duplicate tool adapter registration: {tool_id}")
        self._adapters[tool_id] = adapter

    def get(self, tool_id: str) -> ToolAdapter:
        if tool_id not in self._adapters:
            raise KeyError(f"Tool adapter not found: {tool_id}")
        return self._adapters[tool_id]

    def list_descriptors(self) -> List[ToolDescriptor]:
        return [adapter.descriptor for adapter in self._adapters.values()]

    def list_tools(self) -> List[ToolAdapter]:
        return list(self._adapters.values())

    def count(self) -> int:
        return len(self._adapters)
