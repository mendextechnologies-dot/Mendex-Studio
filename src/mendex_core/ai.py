"""Provider-neutral, read-only AI boundary. No provider is installed or contacted."""
from typing import Literal, Protocol
from uuid import UUID

from pydantic import Field

from .models import Model


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
        return AIResponse(status="unavailable", provider="none", text="No AI provider is configured. No answer or engineering result was generated.", limitations=["Read-only advice interface only; no design edits, tool execution, evidence approval or release authority."])
