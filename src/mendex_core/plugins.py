"""Load data-only discovery/rule plugins. Manifests cannot execute Python code."""
import json
from pathlib import Path

from pydantic import Field

from .adapters.registry import DiscoveryAdapter
from .evidence import digest
from .models import Model
from .rules import EngineeringRule


class AdapterDefinition(Model):
    tool_id: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=1)
    binaries: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    official_url: str = Field(pattern=r"^https://")


class PluginManifest(Model):
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    plugin_id: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    adapters: list[AdapterDefinition] = Field(default_factory=list)
    rules: list[EngineeringRule] = Field(default_factory=list)


def load_plugin_file(path: Path, adapters, rules, loaded_ids=None):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Plugin manifest exceeds 1 MiB")
    raw = path.read_bytes()
    manifest = PluginManifest.model_validate(json.loads(raw))
    if loaded_ids is not None and manifest.plugin_id in loaded_ids:
        raise ValueError("Duplicate plugin ID; plugin was not loaded")
    ids = [entry.tool_id for entry in manifest.adapters]
    rule_ids = [entry.rule_id for entry in manifest.rules]
    if len(set(ids)) != len(ids) or any(entry in {a.tool_id for a in adapters.list()} for entry in ids):
        raise ValueError("Duplicate adapter ID; plugin was not loaded")
    if len(set(rule_ids)) != len(rule_ids) or any(entry in {r.rule_id for r in rules.list()} for entry in rule_ids):
        raise ValueError("Duplicate rule ID; plugin was not loaded")
    for definition in manifest.adapters:
        if any(Path(name).name != name or "/" in name or "\\" in name for name in definition.binaries):
            raise ValueError("Binary names must be basenames")
        if any(Path(pattern).anchor or ".." in Path(pattern).parts or "**" in pattern for pattern in definition.locations):
            raise ValueError("Discovery patterns must stay within installation roots")
    for definition in manifest.adapters:
        adapters.register(DiscoveryAdapter(**definition.model_dump()))
    for rule in manifest.rules:
        rules.register(rule)
    if loaded_ids is not None:
        loaded_ids.add(manifest.plugin_id)
    return {"plugin_id": manifest.plugin_id, "version": manifest.version, "status": "loaded", "sha256": digest(raw), "path": str(path)}
