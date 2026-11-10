from .base import BaseToolAdapter
from .ltspice import LTspiceAdapter
from .kicad import KiCadAdapter
from .femm import FEMMAdapter
from .freecad import FreeCADAdapter
from .qucs_s import QucsSAdapter
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
from .commercial_stubs import (
    CommercialStubAdapter,
    PLECSAdapter,
    MATLABAdapter,
    AnsysMaxwellAdapter,
    AnsysIcepakAdapter,
    SolidWorksAdapter,
)
from .registry import ToolRegistry

__all__ = [
    "BaseToolAdapter",
    "LTspiceAdapter",
    "KiCadAdapter",
    "FEMMAdapter",
    "FreeCADAdapter",
    "QucsSAdapter",
    "OpenModelicaAdapter",
    "PythonRuntimeAdapter",
    "JupyterAdapter",
    "GitAdapter",
    "SwitchLossDBAdapter",
    "MagNetDatasetAdapter",
    "MagNetMLBenchmarksAdapter",
    "MagNetPrincetonAdapter",
    "CommercialStubAdapter",
    "PLECSAdapter",
    "MATLABAdapter",
    "AnsysMaxwellAdapter",
    "AnsysIcepakAdapter",
    "SolidWorksAdapter",
    "ToolRegistry",
]
