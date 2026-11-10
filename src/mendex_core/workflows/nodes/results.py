"""Results nodes: waveform extraction, data transformation, and comparison."""
from __future__ import annotations

from typing import Any, Dict, List
import numpy as np

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, TimeSeriesData, SimulationResultData, QuantityValue
from ..registry import BaseNode, ExecutionContext, NodeRegistry


@NodeRegistry.register
class WaveformExtractNode(BaseNode):
    node_type = "waveform_extract"
    category = NodeCategory.RESULTS
    title = "Waveform Extract"
    description = "Extracts an individual signal vector (e.g. V(out), I(L1)) from a simulation result or time series."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="waveform_in", display_name="Waveform", data_type=PortDataType.TIME_SERIES, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="signal_vector", display_name="Signal", data_type=PortDataType.VECTOR),
            PortDefinition(name="time_vector", display_name="Time", data_type=PortDataType.VECTOR),
            PortDefinition(name="peak_value", display_name="Peak Value", data_type=PortDataType.SCALAR),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        wf = inputs.get("waveform_in")
        sig_name = config.get("signal_name", "")

        t_vec: List[float] = []
        s_vec: List[float] = []

        if isinstance(wf, TimeSeriesData):
            t_vec = wf.time
            if sig_name and sig_name in wf.signals:
                s_vec = wf.signals[sig_name]
            elif wf.signals:
                s_vec = next(iter(wf.signals.values()))
        elif isinstance(wf, dict) and "signals" in wf:
            t_vec = wf.get("time", [])
            sigs = wf.get("signals", {})
            if sig_name in sigs:
                s_vec = sigs[sig_name]
            elif sigs:
                s_vec = next(iter(sigs.values()))

        pk = float(max(s_vec)) if s_vec else 0.0
        return {
            "signal_vector": s_vec,
            "time_vector": t_vec,
            "peak_value": pk,
        }


@NodeRegistry.register
class ResultComparisonNode(BaseNode):
    node_type = "result_comparison"
    category = NodeCategory.RESULTS
    title = "Result Comparison"
    description = "Compares actual simulation result against a reference or calculation baseline."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="actual", display_name="Actual", data_type=PortDataType.SCALAR, required=True),
            PortDefinition(name="reference", display_name="Reference", data_type=PortDataType.SCALAR, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="delta", display_name="Delta", data_type=PortDataType.SCALAR),
            PortDefinition(name="percent_error", display_name="Error (%)", data_type=PortDataType.SCALAR),
            PortDefinition(name="within_tolerance", display_name="Within Tol", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        def _to_float(v: Any) -> float:
            if isinstance(v, QuantityValue):
                return v.value
            return float(v)

        act = _to_float(inputs.get("actual", 0.0))
        ref = _to_float(inputs.get("reference", 1.0))
        tol_pct = float(config.get("tolerance_pct", 5.0))

        delta = act - ref
        pct_err = abs(delta / ref) * 100.0 if ref != 0 else 0.0
        within_tol = pct_err <= tol_pct

        return {
            "delta": delta,
            "percent_error": pct_err,
            "within_tolerance": within_tol,
        }
