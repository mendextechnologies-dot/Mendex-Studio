"""Domain models for AI Engineering Copilot, Model Gateway, and Typed Actions."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Protocol
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from ..models import Model


class AIRequest(Model):
    revision_id: UUID
    question: str = Field(min_length=1, max_length=8000)
    context: dict = Field(default_factory=dict)


class AIResponse(Model):
    status: Literal["unavailable", "needs_review"]
    provider: str
    text: str
    limitations: list[str]


class AIService(Protocol):
    def advise(self, request: AIRequest) -> AIResponse: ...


class UnavailableAIService:
    def advise(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            status="unavailable",
            provider="none",
            text="No AI provider is configured. No answer or engineering result was generated.",
            limitations=[
                "Read-only advice interface only; no design edits, tool execution, evidence approval or release authority."
            ],
        )


class AIActionKind(str, Enum):
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    GENERATE_CANDIDATES = "generate_candidates"
    CALCULATE = "calculate"
    GENERATE_ARTIFACT = "generate_artifact"
    OPEN_NATIVE_TOOL = "open_native_tool"
    RUN_SOLVER = "run_solver"
    PARSE_RESULTS = "parse_results"
    COMPARE = "compare"
    PROPOSE_REVISION = "propose_revision"
    GENERATE_REPORT = "generate_report"


class ActionApprovalStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class AIEngineeringAction(BaseModel):
    """Registered, typed engineering action proposed by AI Copilot."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: AIActionKind
    title: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requires_user_approval: bool = True
    approval_status: ActionApprovalStatus = ActionApprovalStatus.PENDING_APPROVAL
    diff_preview: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AIPlan(BaseModel):
    """Structured plan of proposed engineering actions with provenance and rationale."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    objective: str
    rationale: str = ""
    provider_used: str = "offline_deterministic"
    model_used: str = "mendex_deterministic_rule_engine"
    actions: List[AIEngineeringAction] = Field(default_factory=list)
    cloud_opt_in_confirmed: bool = False
    estimated_cost_usd: float = 0.0


class AICopilotResponse(BaseModel):
    """Unified response from AI Copilot containing structured text, plan, and actions."""
    message: str
    plan: Optional[AIPlan] = None
    missing_requirements: List[str] = Field(default_factory=list)
    deterministic_validation: Dict[str, Any] = Field(default_factory=dict)
