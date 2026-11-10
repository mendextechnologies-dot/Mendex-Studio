from __future__ import annotations

from pathlib import Path
from integrations.contracts import ToolKind, ToolState, ToolDescriptor
from .base import BaseToolAdapter


class CommercialStubAdapter(BaseToolAdapter):
    """Base stub for commercial proprietary engineering tools."""

    def __init__(self, tool_id: str, name: str, vendor: str, official_url: str, candidate_paths: list[str]):
        super().__init__(
            tool_id=tool_id,
            name=name,
            kind=ToolKind.APPLICATION,
            category="optional",
            license_name=f"Commercial Proprietary ({vendor})",
            official_url=official_url,
            candidate_paths=candidate_paths,
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        desc = super().detect(configured_path)
        if desc.state == ToolState.NOT_INSTALLED:
            return ToolDescriptor(
                tool_id=desc.tool_id,
                name=desc.name,
                kind=desc.kind,
                category=desc.category,
                version=desc.version,
                license_name=desc.license_name,
                official_url=desc.official_url,
                capabilities=desc.capabilities,
                state=ToolState.OPTIONAL_UNLICENSED,
                executable_path=desc.executable_path,
                diagnostic=f"{desc.name} is an optional commercial tool. No valid license or executable detected.",
            )
        return desc


class PLECSAdapter(CommercialStubAdapter):
    def __init__(self):
        super().__init__(
            tool_id="plecs",
            name="PLECS",
            vendor="Plexim",
            official_url="https://www.plexim.com/plecs",
            candidate_paths=["Plexim/PLECS*/plecs.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["simulate_converter", "thermal_loss_calculation"]


class MATLABAdapter(CommercialStubAdapter):
    def __init__(self):
        super().__init__(
            tool_id="matlab",
            name="MATLAB / Simulink",
            vendor="MathWorks",
            official_url="https://www.mathworks.com/products/matlab.html",
            candidate_paths=["MATLAB/*/bin/matlab.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["run_m_script", "simulate_simulink"]


class AnsysMaxwellAdapter(CommercialStubAdapter):
    def __init__(self):
        super().__init__(
            tool_id="ansys_maxwell",
            name="Ansys Maxwell",
            vendor="Ansys",
            official_url="https://www.ansys.com/products/electronics/ansys-maxwell",
            candidate_paths=["AnsysEM/*/Win64/ansysedt.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["solve_3d_em_field", "core_loss_extraction"]


class AnsysIcepakAdapter(CommercialStubAdapter):
    def __init__(self):
        super().__init__(
            tool_id="ansys_icepak",
            name="Ansys Icepak",
            vendor="Ansys",
            official_url="https://www.ansys.com/products/electronics/ansys-icepak",
            candidate_paths=["AnsysEM/*/Win64/icepak.exe", "ANSYS Inc/*/Icepak/*/bin/icepak.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["thermal_cfd_simulation", "junction_temperature_solve"]


class SolidWorksAdapter(CommercialStubAdapter):
    def __init__(self):
        super().__init__(
            tool_id="solidworks",
            name="SolidWorks",
            vendor="Dassault Systemes",
            official_url="https://www.solidworks.com/",
            candidate_paths=["SOLIDWORKS Corp/SOLIDWORKS/SLDWORKS.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["export_step", "mechanical_clearance_check"]
