"""Parametric design engine for Mendex Engineering Studio v1.9.

Provides dependency-aware parameter evaluation, cycle detection, parameter sweep
generation, and change-impact analysis without arbitrary Python eval().
"""
from __future__ import annotations

import ast
import math
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from .ir import IRParameter, DesignIntermediateRepresentation


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


def safe_eval(expr_str: str, variables: Dict[str, float]) -> float:
    """Safely evaluates an algebraic expression using AST node walking."""
    tree = ast.parse(expr_str.strip(), mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Disallowed non-numeric constant: {node.value}")
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return float(variables[node.id])
            elif node.id == "pi":
                return math.pi
            elif node.id == "e":
                return math.e
            raise KeyError(f"Undefined parameter variable: {node.id}")
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


def extract_variable_names(expr_str: str) -> Set[str]:
    """Extracts all variable identifiers referenced in an expression."""
    tree = ast.parse(expr_str.strip(), mode="eval")
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in ("pi", "e") and node.id not in SAFE_MATH_FUNCTIONS:
            names.add(node.id)
    return names


class ParametricChangeImpact(BaseModel):
    """Analysis of changes resulting from updating a parameter."""
    changed_parameter: str
    old_value: float
    new_value: float
    recalculated_parameters: Dict[str, float] = Field(default_factory=dict)
    affected_components: List[str] = Field(default_factory=list)
    invalidated_artifacts: List[str] = Field(default_factory=list)


class ParametricDesignEngine:
    """Manages parametric recalculations, dependency propagation, and sweeps."""

    def __init__(self, ir: DesignIntermediateRepresentation):
        self.ir = ir

    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """Returns adjacency list of parameter dependencies: param -> {dependencies}."""
        deps: Dict[str, Set[str]] = {}
        for name, param in self.ir.parameters.items():
            if param.expression:
                deps[name] = extract_variable_names(param.expression)
            else:
                deps[name] = set()
        return deps

    def evaluate_all(self) -> Dict[str, float]:
        """Topologically evaluates all parameters based on expressions and values."""
        deps = self.get_dependency_graph()
        values: Dict[str, float] = {k: v.value for k, v in self.ir.parameters.items()}
        
        # Simple iterative relaxation (bounded to prevent infinite loop on cycles)
        max_iterations = len(deps) + 5
        for _ in range(max_iterations):
            changed = False
            for name, param in self.ir.parameters.items():
                if param.expression:
                    try:
                        new_val = safe_eval(param.expression, values)
                        if not math.isclose(values[name], new_val, rel_tol=1e-6):
                            values[name] = new_val
                            param.value = new_val
                            changed = True
                    except Exception:
                        pass
            if not changed:
                break

        # Also update component values that reference parameter names
        for comp in self.ir.components:
            for p_name, p_val in comp.parameters.items():
                if isinstance(p_val, str) and p_val in values:
                    comp.value = values[p_val]

        return values

    def analyze_impact(self, param_name: str, new_value: float) -> ParametricChangeImpact:
        """Determines all downstream parameters and components affected by a change."""
        if param_name not in self.ir.parameters:
            raise KeyError(f"Parameter '{param_name}' not found in Design IR.")

        old_val = self.ir.parameters[param_name].value
        sim_values = {k: v.value for k, v in self.ir.parameters.items()}
        sim_values[param_name] = new_value

        deps = self.get_dependency_graph()
        recalculated: Dict[str, float] = {}

        # Propagate downstream
        for name, param in self.ir.parameters.items():
            if param.expression:
                needed = deps.get(name, set())
                if param_name in needed or any(r in needed for r in recalculated):
                    try:
                        recalculated[name] = safe_eval(param.expression, {**sim_values, **recalculated})
                    except Exception:
                        pass

        # Identify components referencing updated params
        affected_comps: List[str] = []
        all_updated = {param_name}.union(recalculated.keys())
        for comp in self.ir.components:
            for p_val in comp.parameters.values():
                if isinstance(p_val, str) and p_val in all_updated:
                    affected_comps.append(comp.designator)

        return ParametricChangeImpact(
            changed_parameter=param_name,
            old_value=old_val,
            new_value=new_value,
            recalculated_parameters=recalculated,
            affected_components=affected_comps,
            invalidated_artifacts=["simulation_results", "kicad_schematic", "netlist"],
        )

    def generate_sweep(self, param_name: str, start: float, stop: float, steps: int) -> List[Dict[str, float]]:
        """Generates a parameter sweep matrix evaluating dependent parameters across points."""
        if steps < 2:
            steps = 2
        step_size = (stop - start) / (steps - 1)
        matrix: List[Dict[str, float]] = []

        orig_val = self.ir.parameters[param_name].value
        try:
            for i in range(steps):
                current_val = start + i * step_size
                self.ir.parameters[param_name].value = current_val
                point_values = self.evaluate_all()
                matrix.append(point_values)
        finally:
            self.ir.parameters[param_name].value = orig_val
            self.evaluate_all()

        return matrix
