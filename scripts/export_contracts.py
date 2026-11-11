"""Regenerate checked-in JSON contracts from the canonical application models."""
import json
from pathlib import Path

from mendex_core.models import Product, Revision, Specification
from mendex_core.evidence import ManualCheck, ValidationRecord, SimulationRun, Report
from mendex_core.adapters.registry import ToolStatus
from mendex_core.adapters.contracts import AdapterCapabilities, AdapterCheck, PreparedJob, ResultBundle
from mendex_core.rules import EngineeringRule, RuleAssessment
from mendex_core.plugins import PluginManifest, AdapterDefinition

destination = Path(__file__).resolve().parents[1] / "contracts"
for model in (Product, Revision, Specification, ManualCheck, ValidationRecord, SimulationRun, Report, ToolStatus, AdapterCapabilities, AdapterCheck, PreparedJob, ResultBundle, EngineeringRule, RuleAssessment, PluginManifest, AdapterDefinition):
    (destination / f"{model.__name__}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
print("Exported 18 canonical contracts")
