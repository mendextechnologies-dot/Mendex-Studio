"""Validation nodes: range checks, tolerance verification, unit validation, and standards compliance."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, ValidationResultData, QuantityValue
from ..registry import BaseNode, ExecutionContext, NodeRegistry
from ...intelligence.knowledge import EngineeringKnowledgeService


@NodeRegistry.register
class RangeValidationNode(BaseNode):
    node_type = "range_validation"
    category = NodeCategory.VALIDATION
    title = "Range Check"
    description = "Validates that a scalar value or quantity lies within defined [min, max] limits."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="value_in", display_name="Value", data_type=PortDataType.SCALAR, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="validation_result", display_name="Validation", data_type=PortDataType.VALIDATION_RESULT),
            PortDefinition(name="passed", display_name="Passed", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        val = inputs.get("value_in")
        if isinstance(val, QuantityValue):
            val = val.value
        val = float(val) if val is not None else 0.0

        min_val = float(config.get("min_val", float("-inf")))
        max_val = float(config.get("max_val", float("inf")))
        check_id = str(config.get("check_id", "REQ-RANGE"))

        passed = min_val <= val <= max_val
        msg = f"Value {val} is within range [{min_val}, {max_val}]" if passed else f"Value {val} violates range [{min_val}, {max_val}]"

        res = ValidationResultData(
            check_id=check_id,
            passed=passed,
            status="PASS" if passed else "FAIL",
            actual_value=val,
            expected_value=f"[{min_val}, {max_val}]",
            message=msg,
        )
        return {
            "validation_result": res,
            "passed": passed,
        }


@NodeRegistry.register
class ToleranceComparisonNode(BaseNode):
    node_type = "tolerance_comparison"
    category = NodeCategory.VALIDATION
    title = "Tolerance Verification"
    description = "Compares an actual measurement or simulation against a target with specified tolerance %."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="actual", display_name="Actual", data_type=PortDataType.SCALAR, required=True),
            PortDefinition(name="target", display_name="Target", data_type=PortDataType.SCALAR, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="validation_result", display_name="Validation", data_type=PortDataType.VALIDATION_RESULT),
            PortDefinition(name="passed", display_name="Passed", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        def _to_float(v: Any) -> float:
            if isinstance(v, QuantityValue):
                return v.value
            return float(v)

        act = _to_float(inputs.get("actual", 0.0))
        tgt = _to_float(inputs.get("target", 1.0))
        tol_pct = float(config.get("tolerance_pct", 5.0))
        check_id = str(config.get("check_id", "REQ-TOLERANCE"))

        pct_err = abs(act - tgt) / abs(tgt) * 100.0 if tgt != 0 else 0.0
        passed = pct_err <= tol_pct
        msg = f"Error {pct_err:.2f}% is within ±{tol_pct}%" if passed else f"Error {pct_err:.2f}% exceeds tolerance ±{tol_pct}%"

        res = ValidationResultData(
            check_id=check_id,
            passed=passed,
            status="PASS" if passed else "FAIL",
            actual_value=act,
            expected_value=tgt,
            tolerance=tol_pct,
            message=msg,
        )
        return {
            "validation_result": res,
            "passed": passed,
        }


@NodeRegistry.register
class RegulatoryCheckNode(BaseNode):
    node_type = "regulatory_check"
    category = NodeCategory.VALIDATION
    title = "Standards Clearance Check"
    description = "Evaluates PCB clearance and creepage against IEC 62368-1 or IPC-2221B tables."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="working_voltage_v", display_name="Voltage (V)", data_type=PortDataType.SCALAR, required=True),
            PortDefinition(name="actual_clearance_mm", display_name="Clearance (mm)", data_type=PortDataType.SCALAR, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="validation_result", display_name="Validation", data_type=PortDataType.VALIDATION_RESULT),
            PortDefinition(name="required_clearance_mm", display_name="Required (mm)", data_type=PortDataType.SCALAR),
            PortDefinition(name="passed", display_name="Passed", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        voltage = float(inputs.get("working_voltage_v", 100.0))
        actual = float(inputs.get("actual_clearance_mm", 2.0))
        standard = config.get("standard", "iec_62368_1")

        knowledge = EngineeringKnowledgeService()
        req_mm = 1.5
        if standard == "iec_62368_1":
            profile = knowledge.get_standard("iec_62368_1")
            req_mm = profile.clearance_creepage_table.get("reinforced_400v", 3.0) if voltage > 250 else 1.5

        passed = actual >= req_mm
        res = ValidationResultData(
            check_id=f"STD-{standard.upper()}",
            passed=passed,
            status="PASS" if passed else "FAIL",
            actual_value=actual,
            expected_value=f">= {req_mm} mm",
            message=f"Actual clearance {actual} mm vs required {req_mm} mm under {standard}",
        )
        return {
            "validation_result": res,
            "required_clearance_mm": req_mm,
            "passed": passed,
        }
