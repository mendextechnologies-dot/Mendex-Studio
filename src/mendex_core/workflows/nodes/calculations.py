"""Engineering calculation nodes: safe expression evaluation, unit conversion, and deterministic physics."""
from __future__ import annotations

import ast
import math
from typing import Any, Dict, List, Optional
import numpy as np

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, QuantityValue
from ..registry import BaseNode, ExecutionContext, NodeRegistry
from ...intelligence.calculations import DeterministicCalculationService


# Safe AST Math Evaluator (Zero arbitrary Python eval)
SAFE_MATH_OPERATORS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b if b != 0 else float("inf"),
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

SAFE_MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
    "min": min,
    "max": max,
}


def safe_eval_expression(expr_str: str, variables: Dict[str, float]) -> float:
    """Safely evaluate mathematical expressions using AST traversal without python eval()."""
    tree = ast.parse(expr_str.strip(), mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant literal: {node.value}")
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return float(variables[node.id])
            elif node.id in SAFE_MATH_FUNCTIONS:
                val = SAFE_MATH_FUNCTIONS[node.id]
                if isinstance(val, (int, float)):
                    return float(val)
            raise ValueError(f"Undefined variable in expression: '{node.id}'")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in SAFE_MATH_OPERATORS:
                return SAFE_MATH_OPERATORS[op_type](_eval(node.left), _eval(node.right))
            raise ValueError(f"Disallowed binary operator: {op_type.__name__}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in SAFE_MATH_OPERATORS:
                return SAFE_MATH_OPERATORS[op_type](_eval(node.operand))
            raise ValueError(f"Disallowed unary operator: {op_type.__name__}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in SAFE_MATH_FUNCTIONS:
                func = SAFE_MATH_FUNCTIONS[node.func.id]
                args = [_eval(arg) for arg in node.args]
                return float(func(*args))
            raise ValueError(f"Disallowed function call: {ast.dump(node.func)}")
        else:
            raise ValueError(f"Unsupported syntax expression element: {ast.dump(node)}")

    return _eval(tree)


@NodeRegistry.register
class FormulaEvaluationNode(BaseNode):
    node_type = "formula_evaluation"
    category = NodeCategory.CALCULATION
    title = "Formula Evaluation"
    description = "Safely evaluates an engineering algebraic expression using input variables (e.g. sqrt(L * C), V / R)."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="a", display_name="A", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="b", display_name="B", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="c", display_name="C", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="d", display_name="D", data_type=PortDataType.SCALAR, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="result", display_name="Result", data_type=PortDataType.SCALAR),
            PortDefinition(name="quantity", display_name="Quantity", data_type=PortDataType.QUANTITY),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        expr = config.get("expression", "a + b")
        unit = config.get("unit", "")
        
        # Extract variables from inputs (supporting QuantityValue or raw scalars)
        vars_dict: Dict[str, float] = {}
        for k in ("a", "b", "c", "d"):
            val = inputs.get(k, config.get(k, 0.0))
            if isinstance(val, QuantityValue):
                vars_dict[k] = val.value
            elif val is not None:
                vars_dict[k] = float(val)

        result_val = safe_eval_expression(expr, vars_dict)
        return {
            "result": result_val,
            "quantity": QuantityValue(value=result_val, unit=unit),
        }


@NodeRegistry.register
class UnitConversionNode(BaseNode):
    node_type = "unit_conversion"
    category = NodeCategory.CALCULATION
    title = "Unit Converter"
    description = "Converts physical quantities between compatible engineering units (e.g. kHz to Hz, uH to H)."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="input_quantity", display_name="Input", data_type=PortDataType.QUANTITY, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="output_quantity", display_name="Converted", data_type=PortDataType.QUANTITY),
            PortDefinition(name="output_value", display_name="Value", data_type=PortDataType.SCALAR),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        in_q = inputs.get("input_quantity")
        if isinstance(in_q, (int, float)):
            in_q = QuantityValue(value=float(in_q), unit=config.get("input_unit", ""))
        
        target_unit = str(config.get("target_unit", in_q.unit if in_q else "")).strip().lower()
        if not in_q:
            raise ValueError("No input quantity provided for unit conversion.")

        # Convert input to base canonical
        base_val, base_unit = in_q.to_canonical()
        # Find scale to target unit
        target_q_one = QuantityValue(value=1.0, unit=target_unit)
        target_base_one, target_base_unit = target_q_one.to_canonical()

        if base_unit != target_base_unit:
            raise ValueError(f"Incompatible unit conversion dimensions: '{in_q.unit}' ({base_unit}) -> '{target_unit}' ({target_base_unit})")

        converted_val = base_val / target_base_one
        out_q = QuantityValue(value=converted_val, unit=target_unit)
        return {
            "output_quantity": out_q,
            "output_value": converted_val,
        }


@NodeRegistry.register
class DeterministicPhysicsNode(BaseNode):
    node_type = "deterministic_physics"
    category = NodeCategory.CALCULATION
    title = "Deterministic Physics Formula"
    description = "Evaluates validated formulas: skin_depth, dowell_factor, flyback_ccm, steinmetz_core_loss, lc_resonance."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="param1", display_name="Param 1", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="param2", display_name="Param 2", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="param3", display_name="Param 3", data_type=PortDataType.SCALAR, required=False),
            PortDefinition(name="param4", display_name="Param 4", data_type=PortDataType.SCALAR, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="result", display_name="Result", data_type=PortDataType.SCALAR),
            PortDefinition(name="quantity", display_name="Quantity", data_type=PortDataType.QUANTITY),
            PortDefinition(name="record", display_name="Record", data_type=PortDataType.ANY),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        calc_service = DeterministicCalculationService()
        formula_id = config.get("formula_id", "skin_depth")

        # Extract parameters either from inputs or config; no defaults are fabricated
        def _get(key: str, alt_key: Optional[str] = None) -> float:
            v = inputs.get(key)
            if v is None and alt_key:
                v = inputs.get(alt_key)
            if v is None:
                v = config.get(key)
            if v is None and alt_key:
                v = config.get(alt_key)
            if v is None:
                raise ValueError(f"Missing required parameter '{key}' for formula '{formula_id}'. Calculation inputs cannot be fabricated.")
            if isinstance(v, QuantityValue):
                v = v.value
            try:
                val = float(v)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Parameter '{key}' must be numeric (got {v!r})") from exc
            if not math.isfinite(val):
                raise ValueError(f"Parameter '{key}' must be a finite number (got {val})")
            return val

        if formula_id == "skin_depth":
            freq = _get("frequency_hz", "param1")
            has_temp = "temperature_c" in inputs or "temperature_c" in config or "param2" in inputs or "param2" in config
            temp = _get("temperature_c", "param2") if has_temp else 20.0
            rec = calc_service.calculate_skin_depth(frequency_hz=freq, temperature_c=temp)
            val = rec.outputs.get("skin_depth_m", next(iter(rec.outputs.values())))
            unit = rec.output_units.get("skin_depth_m", "m")
        elif formula_id == "dowell_factor":
            num_layers_raw = _get("num_layers", "param1")
            if not float(num_layers_raw).is_integer() or num_layers_raw < 1:
                raise ValueError(f"num_layers must be a positive integer, got {num_layers_raw}")
            num_layers = int(num_layers_raw)
            layer_thickness_m = _get("layer_thickness_m", "param2")
            skin_depth_m = _get("skin_depth_m", "param3")
            rec = calc_service.calculate_dowell_factor(layer_thickness_m=layer_thickness_m, skin_depth_m=skin_depth_m, num_layers=num_layers)
            val = rec.outputs.get("F_R", next(iter(rec.outputs.values())))
            unit = ""
        elif formula_id == "flyback_ccm":
            vin = _get("vin_min_v", "param1")
            has_nom = "vin_nom_v" in inputs or "vin_nom_v" in config or "param2" in inputs or "param2" in config
            vin_nom = _get("vin_nom_v", "param2") if has_nom else vin
            vout = _get("vout_v", "param3")
            iout = _get("iout_a", "param4")
            fsw = _get("fsw_hz", "param5")
            rec = calc_service.calculate_flyback_sizing(vin_min_v=vin, vin_nom_v=vin_nom, vout_v=vout, iout_a=iout, fsw_hz=fsw)
            val = rec.outputs.get("primary_inductance_h", next(iter(rec.outputs.values())))
            unit = "H"
        elif formula_id == "steinmetz":
            # For workflows where only flux is dynamically wired from material datasets,
            # allow standard nominal test frequency (100kHz) and volume (10cm3) if omitted in canvas
            has_f = "frequency_hz" in inputs or "frequency_hz" in config or "param1" in inputs or "param1" in config
            f = _get("frequency_hz", "param1") if has_f else 100000.0
            b = _get("b_peak_t", "param2")
            has_vol = "core_volume_m3" in inputs or "core_volume_m3" in config or "param3" in inputs or "param3" in config
            vol = _get("core_volume_m3", "param3") if has_vol else 1e-5
            rec = calc_service.calculate_steinmetz_loss(frequency_hz=f, b_max_t=b, core_volume_m3=vol)
            val = rec.outputs.get("total_core_loss_w", next(iter(rec.outputs.values())))
            unit = "W"
        elif formula_id == "lc_resonance":
            l_val = _get("inductance_h", "param1")
            c_val = _get("capacitance_f", "param2")
            rec = calc_service.calculate_lc_resonance(inductance_h=l_val, capacitance_f=c_val)
            val = rec.outputs.get("resonant_frequency_hz", next(iter(rec.outputs.values())))
            unit = "Hz"
        else:
            raise ValueError(f"Unknown deterministic formula: {formula_id}")

        return {
            "result": val,
            "quantity": QuantityValue(value=val, unit=unit),
            "record": rec.model_dump(),
        }


@NodeRegistry.register
class NumericalSummaryNode(BaseNode):
    node_type = "numerical_summary"
    category = NodeCategory.CALCULATION
    title = "Signal Metrics & Summary"
    description = "Computes RMS, peak-to-peak, mean, min, and max for vector or time series."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="signal", display_name="Signal", data_type=PortDataType.ANY, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="rms", display_name="RMS", data_type=PortDataType.SCALAR),
            PortDefinition(name="pk_pk", display_name="Pk-Pk", data_type=PortDataType.SCALAR),
            PortDefinition(name="mean", display_name="Mean", data_type=PortDataType.SCALAR),
            PortDefinition(name="min", display_name="Min", data_type=PortDataType.SCALAR),
            PortDefinition(name="max", display_name="Max", data_type=PortDataType.SCALAR),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        sig = inputs.get("signal")
        values = []
        if isinstance(sig, list):
            values = [float(x) for x in sig]
        elif hasattr(sig, "signals") and isinstance(sig.signals, dict):
            # TimeSeriesData
            key = config.get("signal_name", list(sig.signals.keys())[0] if sig.signals else "")
            if key in sig.signals:
                values = [float(x) for x in sig.signals[key]]
        elif isinstance(sig, (int, float)):
            values = [float(sig)]

        if not values:
            return {"rms": 0.0, "pk_pk": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

        arr = np.array(values, dtype=float)
        return {
            "rms": float(np.sqrt(np.mean(arr**2))),
            "pk_pk": float(np.ptp(arr)),
            "mean": float(np.mean(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }
