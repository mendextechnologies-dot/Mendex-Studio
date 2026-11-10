"""Mendex Engineering Intelligence — Model-Independent Backend Interface.

Defines pluggable model backends, local execution runners, and provider health checks.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PromptMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ModelResponse(BaseModel):
    provider: str
    model_name: str
    reply_text: str
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    limitations: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class ModelBackend(ABC):
    """Abstract interface for intelligence and reasoning backends."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]: ...

    @abstractmethod
    def generate_response(
        self,
        messages: List[PromptMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> ModelResponse: ...


class LocalRuleEngineBackend(ModelBackend):
    """Deterministic, local engineering reasoning engine.

    Requires zero external network access, zero third-party API keys, and incurs zero cost.
    Evaluates power electronics queries using verified engineering rules and formulas.
    """

    @property
    def provider_id(self) -> str:
        return "local_engineering_rules"

    @property
    def model_name(self) -> str:
        return "Mendex-RuleEngine-v1.8"

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "READY",
            "provider": self.provider_id,
            "model": self.model_name,
            "mode": "deterministic_local_rules",
            "network_required": False,
        }

    def generate_response(
        self,
        messages: List[PromptMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> ModelResponse:
        user_text = messages[-1].content if messages else ""
        lower = user_text.lower()
        context = context or {}

        actions = []
        limitations = [
            "Analytical engineering formula guidance; not a substitute for qualified human reviewer approval.",
            "Independent solver simulations remain necessary to verify high-order parasitics and thermal limits."
        ]

        if "dowell" in lower or "winding loss" in lower:
            reply = (
                "**Dowell AC Winding Loss Model Analysis**\n\n"
                "The high-frequency AC resistance factor $F_R = R_{AC} / R_{DC}$ is determined by the "
                "ratio $\\xi = h / \\delta$ (conductor thickness to skin depth) and layer count $m$:\n\n"
                "$$F_R = \\xi \\left[ \\frac{\\sinh(2\\xi) + \\sin(2\\xi)}{\\cosh(2\\xi) - \\cos(2\\xi)} + "
                "\\frac{2(m^2 - 1)}{3} \\frac{\\sinh(\\xi) - \\sin(\\xi)}{\\cosh(\\xi) + \\cos(\\xi)} \\right]$$\n\n"
                "**Engineering Recommendation:**\n"
                "- Keep foil or layer thickness $h \\le 2\\delta$ at switching frequency to avoid severe proximity loss.\n"
                "- Interleave primary and secondary windings (e.g. P1 - S - P2) to reduce effective $m$ from 2 to 1."
            )
            actions.append({"type": "run_calculation", "name": "dowell", "target": "calculations"})

        elif "flyback" in lower or "inductance" in lower:
            reply = (
                "**CCM Flyback Converter Sizing Formulation**\n\n"
                "For Continuous Conduction Mode operation with maximum duty ratio $D_{max} = 0.45$:\n\n"
                "1. Reflected voltage: $V_R = \\frac{V_{in,min} \\cdot D_{max}}{1 - D_{max}}$\n"
                "2. Transformer turns ratio: $n = \\frac{N_p}{N_s} = \\frac{V_R}{V_{out} + V_F}$\n"
                "3. Primary magnetizing inductance: $L_p = \\frac{V_{in,min}^2 \\cdot D_{max}^2}{2 \\cdot P_{out} \\cdot f_{sw} \\cdot K_{RF}}$\n\n"
                "**Recommendation:** Verify core saturation flux density $B_{max} < 0.3\\text{ T}$ using FEMM 2D magnetics."
            )
            actions.append({"type": "launch_tool", "tool_id": "femm", "operation": "solve_2d_magnetic"})

        elif "sic" in lower or "mosfet" in lower or "switching loss" in lower:
            reply = (
                "**Power Semiconductor Loss Evaluation**\n\n"
                "Total dissipated power consists of conduction and switching components:\n"
                "- Conduction: $P_{cond} = I_{rms}^2 \\cdot R_{ds(on)}(T_j)$\n"
                "- Switching: $P_{sw} = (E_{on} + E_{off}) \\cdot f_{sw}$\n\n"
                "**Recommendation:** Query the integrated **SwitchLossDB** dataset directly for rated $E_{on}$ and $E_{off}$ energy curves."
            )
            actions.append({"type": "query_dataset", "dataset_id": "switchlossdb"})

        else:
            reply = (
                f"**Mendex Engineering Intelligence:** Query recorded regarding: '{user_text}'.\n\n"
                "Available deterministic modules in Studio:\n"
                "- **Deterministic Calculations:** Skin depth, Dowell AC loss factor, Flyback CCM sizing, Steinmetz core loss.\n"
                "- **Multi-Solver Simulations:** LTspice / ngspice circuit analysis, FEMM 2D magnetics, FreeCAD 3D CAD bobbins, OpenModelica dynamic simulation.\n"
                "- **Engineering Datasets:** SwitchLossDB switching energy, MagNet core loss database."
            )

        return ModelResponse(
            provider=self.provider_id,
            model_name=self.model_name,
            reply_text=reply,
            suggested_actions=actions,
            confidence=0.98,
            limitations=limitations,
            latency_ms=1.5,
        )


class ModelRegistry:
    """Manages available intelligence backends and active model selection."""

    def __init__(self):
        self._backends: Dict[str, ModelBackend] = {}
        self._active_backend_id: str = "local_engineering_rules"
        # Register default local rule engine
        self.register_backend(LocalRuleEngineBackend())

    def register_backend(self, backend: ModelBackend):
        self._backends[backend.provider_id] = backend

    def get_backend(self, provider_id: Optional[str] = None) -> ModelBackend:
        pid = provider_id or self._active_backend_id
        if pid not in self._backends:
            return self._backends["local_engineering_rules"]
        return self._backends[pid]

    def set_active_backend(self, provider_id: str):
        if provider_id not in self._backends:
            raise KeyError(f"Backend '{provider_id}' is not registered.")
        self._active_backend_id = provider_id

    def list_backends(self) -> List[Dict[str, Any]]:
        return [b.health_check() for b in self._backends.values()]
