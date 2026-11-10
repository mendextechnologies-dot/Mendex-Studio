"""Versioned engineering check definitions. No invented acceptance thresholds."""
from typing import Literal

from pydantic import Field, model_validator

from .models import Category, Model, Specification


class EngineeringRule(Model):
    rule_id: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    categories: list[Category]
    required_fields: list[str] = Field(default_factory=list)
    evidence_required: str
    physical_verification: bool = False
    automatic_evaluation: Literal[False] = False

    @model_validator(mode="after")
    def known_fields(self):
        if any(name not in Specification.model_fields for name in self.required_fields):
            raise ValueError("Rule references an unknown specification field")
        return self


class RuleAssessment(Model):
    rule_id: str
    rule_version: str
    status: Literal["not_evaluated", "physical_verification_required"]
    missing_fields: list[str]
    notes: str


class RuleRegistry:
    def __init__(self):
        self._rules = {}

    def register(self, rule: EngineeringRule):
        rule = EngineeringRule.model_validate(rule)
        if rule.rule_id in self._rules:
            raise ValueError(f"Duplicate engineering rule: {rule.rule_id}")
        self._rules[rule.rule_id] = rule

    def list(self, category=None):
        return [r for r in self._rules.values() if category is None or category in r.categories]

    def assess(self, category, specification):
        assessments = []
        for rule in self.list(category):
            missing = [name for name in rule.required_fields if getattr(specification, name) in (None, "", [], "UNASSIGNED")]
            assessments.append(RuleAssessment(rule_id=rule.rule_id, rule_version=rule.version, status="physical_verification_required" if rule.physical_verification else "not_evaluated", missing_fields=missing, notes=("Missing specification inputs: " + ", ".join(missing)) if missing else f"Inputs available; {rule.evidence_required}. No engineering check has been executed."))
        return assessments

    @classmethod
    def defaults(cls):
        from importlib.resources import files
        import json
        registry = cls()
        for entry in json.loads(files("mendex_core.config").joinpath("engineering-rules.json").read_text(encoding="utf-8")):
            registry.register(EngineeringRule.model_validate(entry))
        return registry
