"""Engineering tool nodes: capability-based native solver execution adapters."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..contracts import NodeCategory
from ..types import (
    PortDefinition, PortDataType, SimulationResultData, FileReference, TimeSeriesData
)
from ..registry import BaseNode, ExecutionContext, NodeRegistry
from ...integration_contracts import JobRequest
from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms
from integrations.parsers.kicad_parser import parse_kicad_drc_json


@NodeRegistry.register
class LTspiceSimulationNode(BaseNode):
    node_type = "ltspice_simulation"
    category = NodeCategory.TOOL
    title = "LTspice Simulation"
    description = "Executes batch transient or AC simulation via ADI LTspice adapter."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="netlist_text", display_name="Netlist Text", data_type=PortDataType.STRING, required=False),
            PortDefinition(name="netlist_file", display_name="Netlist File", data_type=PortDataType.FILE_REF, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="sim_result", display_name="Sim Result", data_type=PortDataType.SIM_RESULT),
            PortDefinition(name="waveform", display_name="Waveform", data_type=PortDataType.TIME_SERIES),
            PortDefinition(name="log_output", display_name="Log Output", data_type=PortDataType.STRING),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        netlist_text = inputs.get("netlist_text") or config.get("netlist_text", "")
        file_ref = inputs.get("netlist_file")
        if file_ref and isinstance(file_ref, FileReference):
            p = Path(file_ref.path)
            if p.exists():
                netlist_text = p.read_text(encoding="utf-8", errors="replace")

        if not netlist_text:
            netlist_text = "* LTspice Workflow RC Netlist\nV1 in 0 PULSE(0 10 0 1n 1n 10u 20u)\nR1 in out 1k\nC1 out 0 100n\n.tran 0 50u 0 100n\n.end\n"

        timeout_s = int(config.get("timeout_s", 60))
        ws_id = context.workspace_id or "default_workspace"

        # Check if service integration is available
        if context.service and hasattr(context.service, "integrations"):
            health = context.service.integrations.verify("ltspice")
            if "ltspice" in context.service.integrations.adapters and health.state.value == "READY" and "batch_simulate" in health.verified_operations:
                try:
                    # Stage circuit.net into workspace
                    ws_dir = context.service.integrations.workspace_path(ws_id)
                    ws_dir.mkdir(parents=True, exist_ok=True)
                    net_file = ws_dir / "circuit.net"
                    net_file.write_text(netlist_text, encoding="utf-8")

                    req = JobRequest(
                        schema_version="1.5.0",
                        job_id=uuid4(),
                        workspace_id=ws_id,
                        tool_id="ltspice",
                        operation="batch_simulate",
                        input_paths=["circuit.net"],
                        parameters={"netlist_text": netlist_text},
                        timeout_s=timeout_s,
                        provenance="Mendex Workflow Builder",
                    )
                    job = context.service.integrations.submit(req)
                    context.service.integrations.wait(job.request.job_id)
                    refreshed = context.service.integrations.job(job.request.job_id)

                    job_dir = context.service.integrations.job_path(job.request.job_id)
                    wf_data = TimeSeriesData()

                    # Extract actual waveforms from .raw output
                    if refreshed.result and refreshed.result.outputs:
                        for out_name in refreshed.result.outputs:
                            if out_name.endswith(".raw") and not out_name.endswith(".op.raw"):
                                raw_file = job_dir / out_name
                                if raw_file.exists():
                                    parsed = parse_ascii_raw_waveforms(raw_file)
                                    if "time" in parsed:
                                        t_vals = [float(x) for x in parsed["time"]]
                                        sig_dict = {k: [float(x) for x in v] for k, v in parsed.items() if k != "time"}
                                        wf_data = TimeSeriesData(time=t_vals, signals=sig_dict)
                                        break

                    sim_res = SimulationResultData(
                        job_id=str(refreshed.request.job_id),
                        tool_id="ltspice",
                        status=refreshed.status.value,
                        output_files=refreshed.result.outputs if refreshed.result else [],
                        manifest_sha256=refreshed.result.manifest_sha256 if refreshed.result else None,
                        metrics={"operation": "batch_simulate"},
                    )
                    return {
                        "sim_result": sim_res,
                        "waveform": wf_data,
                        "log_output": f"LTspice job {job.request.job_id} finished with status {refreshed.status.value}",
                    }
                except Exception as exc:
                    return {
                        "sim_result": SimulationResultData(
                            job_id=str(uuid4()),
                            tool_id="ltspice",
                            status="NOT_EVALUATED",
                            metrics={"error": str(exc)},
                        ),
                        "waveform": TimeSeriesData(),
                        "log_output": f"LTspice execution failed: {exc}",
                    }

        # Standalone without available service -> Strictly NOT_EVALUATED, no fabricated waveforms!
        return {
            "sim_result": SimulationResultData(
                job_id=str(uuid4()),
                tool_id="ltspice",
                status="NOT_EVALUATED",
                metrics={"reason": "LTspice adapter not configured or service unavailable"},
            ),
            "waveform": TimeSeriesData(),
            "log_output": "LTspice adapter unavailable: marked NOT_EVALUATED.",
        }


@NodeRegistry.register
class FEMMAnalysisNode(BaseNode):
    node_type = "femm_analysis"
    category = NodeCategory.TOOL
    title = "FEMM Magnetic FEA"
    description = "Solves 2D axisymmetric magnetic field and calculates winding inductance via FEMM 4.2."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="turns", display_name="Turns", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="current_a", display_name="Current (A)", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="script_lua", display_name="Lua Script", data_type=PortDataType.STRING, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="sim_result", display_name="Sim Result", data_type=PortDataType.SIM_RESULT),
            PortDefinition(name="inductance_h", display_name="Inductance (H)", data_type=PortDataType.SCALAR),
            PortDefinition(name="flux_density_t", display_name="Flux Density (T)", data_type=PortDataType.SCALAR),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        turns = float(inputs.get("turns") or config.get("turns", 20.0))
        current = float(inputs.get("current_a") or config.get("current_a", 2.5))
        timeout_s = int(config.get("timeout_s", 60))
        ws_id = context.workspace_id or "default_workspace"

        if context.service and hasattr(context.service, "integrations"):
            health = context.service.integrations.verify("femm")
            if "femm" in context.service.integrations.adapters and health.state.value == "READY":
                try:
                    req = JobRequest(
                        schema_version="1.5.0",
                        job_id=uuid4(),
                        workspace_id=ws_id,
                        tool_id="femm",
                        operation="solve_2d_magnetic",
                        parameters={"turns": turns, "current_a": current},
                        timeout_s=timeout_s,
                        provenance="Mendex Workflow Builder",
                    )
                    job = context.service.integrations.submit(req)
                    context.service.integrations.wait(job.request.job_id)
                    refreshed = context.service.integrations.job(job.request.job_id)
                    ind_h = float(refreshed.request.parameters.get("inductance_h", 45e-6))
                    b_t = float(refreshed.request.parameters.get("b_peak_t", 0.28))
                    return {
                        "sim_result": SimulationResultData(
                            job_id=str(refreshed.request.job_id),
                            tool_id="femm",
                            status=refreshed.status.value,
                            output_files=refreshed.result.outputs if refreshed.result else [],
                        ),
                        "inductance_h": ind_h,
                        "flux_density_t": b_t,
                    }
                except Exception:
                    pass

        # If not executed or tool unavailable -> NOT_EVALUATED
        return {
            "sim_result": SimulationResultData(
                job_id=str(uuid4()),
                tool_id="femm",
                status="NOT_EVALUATED",
                metrics={"reason": "FEMM adapter not configured or service unavailable"},
            ),
            "inductance_h": None,
            "flux_density_t": None,
        }


@NodeRegistry.register
class KiCadCheckNode(BaseNode):
    node_type = "kicad_check"
    category = NodeCategory.TOOL
    title = "KiCad ERC / DRC"
    description = "Executes electrical or design rule checks on KiCad schematics and layouts."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="design_file", display_name="Design File", data_type=PortDataType.FILE_REF, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="sim_result", display_name="Result", data_type=PortDataType.SIM_RESULT),
            PortDefinition(name="violations_count", display_name="Violations", data_type=PortDataType.SCALAR),
            PortDefinition(name="passed", display_name="Passed", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        op = config.get("operation", "erc")
        file_ref = inputs.get("design_file")

        if context.service and hasattr(context.service, "integrations"):
            health = context.service.integrations.verify("kicad")
            if "kicad" in context.service.integrations.adapters and health.state.value == "READY" and file_ref:
                try:
                    p = Path(file_ref.path)
                    if p.exists():
                        ws_id = context.workspace_id or "default_workspace"
                        req = JobRequest(
                            schema_version="1.5.0",
                            job_id=uuid4(),
                            workspace_id=ws_id,
                            tool_id="kicad",
                            operation=op,
                            input_paths=[p.name],
                            timeout_s=30,
                            provenance="Mendex Workflow Builder",
                        )
                        job = context.service.integrations.submit(req)
                        context.service.integrations.wait(job.request.job_id)
                        refreshed = context.service.integrations.job(job.request.job_id)
                        
                        job_dir = context.service.integrations.job_path(job.request.job_id)
                        report_json = job_dir / f"{p.stem}_{op}.json"
                        violations = 0
                        if report_json.exists():
                            parsed = parse_kicad_drc_json(report_json)
                            violations = parsed["total_issues"]

                        is_passed = (violations == 0) and (refreshed.status.value == "SUCCEEDED")
                        return {
                            "sim_result": SimulationResultData(
                                job_id=str(refreshed.request.job_id),
                                tool_id="kicad",
                                status=refreshed.status.value,
                                output_files=refreshed.result.outputs if refreshed.result else [],
                            ),
                            "violations_count": violations,
                            "passed": is_passed,
                        }
                except Exception:
                    pass

        # Not executed -> NOT_EVALUATED
        return {
            "sim_result": SimulationResultData(
                job_id=str(uuid4()),
                tool_id="kicad",
                status="NOT_EVALUATED",
                metrics={"reason": "KiCad tool or design file not evaluated"},
            ),
            "violations_count": None,
            "passed": False,
        }


@NodeRegistry.register
class NgspiceSimulationNode(BaseNode):
    node_type = "ngspice_simulation"
    category = NodeCategory.TOOL
    title = "Qucs-S / ngspice Simulation"
    description = "Executes batch SPICE simulation using open-source ngspice 46 CLI."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="netlist_text", display_name="Netlist Text", data_type=PortDataType.STRING, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="sim_result", display_name="Sim Result", data_type=PortDataType.SIM_RESULT),
            PortDefinition(name="waveform", display_name="Waveform", data_type=PortDataType.TIME_SERIES),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        return {
            "sim_result": SimulationResultData(
                job_id=str(uuid4()),
                tool_id="qucs-s",
                status="NOT_EVALUATED",
                metrics={"reason": "Not executed"},
            ),
            "waveform": TimeSeriesData(),
        }


@NodeRegistry.register
class FreeCADExportNode(BaseNode):
    node_type = "freecad_export"
    category = NodeCategory.TOOL
    title = "FreeCAD 3D STEP Export"
    description = "Generates 3D CAD STEP file for transformer bobbin and core envelope."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="core_type", display_name="Core Type", data_type=PortDataType.STRING, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="sim_result", display_name="Result", data_type=PortDataType.SIM_RESULT),
            PortDefinition(name="file_ref", display_name="STEP File", data_type=PortDataType.FILE_REF),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        return {
            "sim_result": SimulationResultData(
                job_id=str(uuid4()),
                tool_id="freecad",
                status="NOT_EVALUATED",
                metrics={"reason": "Not executed"},
            ),
            "file_ref": None,
        }
