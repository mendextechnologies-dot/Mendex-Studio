"""Codex-owned catalog/settings semantics; native discovery stays with Agent 2."""
import json
from importlib.resources import files
from pathlib import Path

from .integration_contracts import ToolDescriptor, ToolHealth, ToolState


def descriptors():
    entries = json.loads(files("mendex_core.config").joinpath("integration_catalog.json").read_text(encoding="utf-8"))
    result = [ToolDescriptor.model_validate(entry) for entry in entries]
    if len(result) != len({entry.tool_id for entry in result}):
        raise ValueError("Integration catalog contains duplicate tool IDs")
    return {entry.tool_id: entry for entry in result}


def unconnected_health(descriptor, configuration, legacy_registry):
    if descriptor.category in ("dataset", "benchmark", "research_resource"):
        exists = configuration.resource_path and Path(configuration.resource_path).exists()
        return ToolHealth(tool_id=descriptor.tool_id, state=ToolState.DETECTED if exists else ToolState.NOT_CONFIGURED, diagnostic="Resource metadata only; source, version, license and data interpretation await review. No executable readiness applies.")
    legacy_ids = {adapter.tool_id for adapter in legacy_registry.list()}
    if descriptor.tool_id in legacy_ids:
        probe = legacy_registry.get(descriptor.tool_id).probe(configuration.executable_path)
        return ToolHealth(tool_id=descriptor.tool_id, state=ToolState.DETECTED if probe.detected else ToolState.NOT_INSTALLED, version=probe.installed_version, executable_path=probe.executable, diagnostic=probe.diagnostic + " No v1.5 operation verification supplied by Agent 2.")
    if configuration.executable_path:
        exists = Path(configuration.executable_path).is_file()
        return ToolHealth(tool_id=descriptor.tool_id, state=ToolState.DETECTED if exists else ToolState.NOT_INSTALLED, executable_path=configuration.executable_path, diagnostic="Configured path exists; connector, version and operation verification are pending." if exists else "Configured executable no longer exists; repair the path.")
    return ToolHealth(tool_id=descriptor.tool_id, state=ToolState.NOT_CONFIGURED, diagnostic="Awaiting Agent 2 detection/connector. Configure a local path; no executable is silently installed or launched.")
