"""Mendex Engineering Intelligence — Reasoning & Context Orchestration.

Orchestrates workspace context retrieval, solver capability mapping, calculation requests,
and recommendation generation with confidence reporting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .knowledge import EngineeringKnowledgeService
from .calculations import DeterministicCalculationService, CalculationResult
from .models import ModelRegistry, PromptMessage, ModelResponse


class EngineeringRecommendation(BaseModel):
    recommendation_id: str
    headline: str
    description: str
    target_tool_or_module: str
    action_type: str  # "calculation", "simulation", "dataset_lookup", "erc_check"
    suggested_inputs: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    limitations: List[str] = Field(default_factory=list)


class EngineeringReasoningOrchestrator:
    """Central orchestrator bridging knowledge, calculations, context, and AI backends."""

    def __init__(
        self,
        knowledge_service: Optional[EngineeringKnowledgeService] = None,
        calculation_service: Optional[DeterministicCalculationService] = None,
        model_registry: Optional[ModelRegistry] = None,
    ):
        self.knowledge = knowledge_service or EngineeringKnowledgeService()
        self.calculations = calculation_service or DeterministicCalculationService()
        self.models = model_registry or ModelRegistry()

    def process_query(
        self,
        question: str,
        workspace_context: Optional[Dict[str, Any]] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        workspace_context = workspace_context or {}
        backend = self.models.get_backend(provider_id)

        # 1. Inspect workspace context for active files and parameters
        active_netlists = workspace_context.get("netlists", [])
        active_tools = workspace_context.get("available_tools", [])

        # 2. Query AI / Reasoning Backend
        messages = [
            PromptMessage(
                role="system",
                content=(
                    "You are the Mendex Engineering Intelligence Assistant. "
                    "Analyze power electronics, magnetics, PCB layout, and simulation questions. "
                    "Provide explicit mathematical equations, recommended solver tools, and unit constraints."
                ),
            ),
            PromptMessage(role="user", content=question),
        ]
        response: ModelResponse = backend.generate_response(messages, context=workspace_context)

        # 3. Formulate Deterministic Recommendations
        recommendations = self._formulate_recommendations(question, active_tools)

        return {
            "query": question,
            "provider": response.provider,
            "model": response.model_name,
            "reply": response.reply_text,
            "suggested_actions": response.suggested_actions,
            "recommendations": [r.model_dump() for r in recommendations],
            "confidence": response.confidence,
            "limitations": response.limitations,
            "latency_ms": response.latency_ms,
        }

    def _formulate_recommendations(
        self,
        question: str,
        available_tools: List[str],
    ) -> List[EngineeringRecommendation]:
        lower = question.lower()
        recs = []

        if "transient" in lower or "circuit" in lower or "spice" in lower:
            recs.append(EngineeringRecommendation(
                recommendation_id="REC-SIM-SPICE",
                headline="Execute SPICE Transient Circuit Simulation",
                description="Verify switching transients, peak node voltages, and diode recovery using the verified LTspice or ngspice engine.",
                target_tool_or_module="ltspice",
                action_type="simulation",
                suggested_inputs={"operation": "batch_simulate", "netlist": "circuit.net"},
                confidence=0.95,
                limitations=["Requires circuit netlist with valid SPICE models for active semiconductors."],
            ))

        if "magnetic" in lower or "core" in lower or "flux" in lower or "femm" in lower:
            recs.append(EngineeringRecommendation(
                recommendation_id="REC-SIM-FEMM",
                headline="Perform 2D Finite Element Magnetic Field Analysis",
                description="Simulate peak B-field distribution, fringing flux around the core air gap, and leakage inductance in FEMM 4.2.",
                target_tool_or_module="femm",
                action_type="simulation",
                suggested_inputs={"operation": "solve_2d_magnetic", "frequency_hz": 100000.0},
                confidence=0.92,
                limitations=["2D axisymmetric planar representation; 3D end-turn effects require correction."],
            ))

        if "pcb" in lower or "clearance" in lower or "creepage" in lower or "drc" in lower:
            recs.append(EngineeringRecommendation(
                recommendation_id="REC-TOOL-KICAD",
                headline="Run KiCad Design Rules Check (DRC)",
                description="Verify high-voltage electrical clearance against IEC 62368-1 / IPC-2221B standards using the headless KiCad 10 CLI.",
                target_tool_or_module="kicad",
                action_type="erc_check",
                suggested_inputs={"operation": "drc"},
                confidence=0.98,
                limitations=["PCB layout must be saved in native KiCad format (.kicad_pcb)."],
            ))

        return recs
