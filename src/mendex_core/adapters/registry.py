import os
import shutil
from pathlib import Path
from typing import Protocol

from pydantic import Field

from mendex_core.models import Model, now


class ToolStatus(Model):
    tool_id: str
    display_name: str
    configured_path: str | None = None
    executable: str | None = None
    detected: bool = False
    installed_version: str | None = None
    compatibility: str = "unknown"
    state: str = "NOT_INSTALLED"
    checked_at: str = Field(default_factory=lambda: now().isoformat())
    diagnostic: str
    official_url: str
    adapter_version: str = "0.1.0"
    capabilities: list[str] = Field(default_factory=lambda: ["discovery"])
    self_test_status: str = "NOT_EVALUATED"


class ToolAdapter(Protocol):
    tool_id: str
    def probe(self, configured_path: str | None = None) -> ToolStatus: ...
    def run(self, *args, **kwargs): ...


class DiscoveryAdapter:
    def __init__(self, tool_id, display_name, binaries, locations, official_url):
        self.tool_id = tool_id
        self.display_name = display_name
        self.binaries = binaries
        self.locations = locations
        self.official_url = official_url

    def probe(self, configured_path=None):
        candidates = []
        if configured_path:
            candidates.append(Path(configured_path))
        else:
            candidates.extend(Path(p) for binary in self.binaries if (p := shutil.which(binary)))
            roots = [Path(os.environ.get("ProgramFiles", "C:/Program Files")), Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "Programs"]
            for root in roots:
                for pattern in self.locations:
                    candidates.extend(sorted(root.glob(pattern)))
            if self.tool_id == "femm":
                candidates.append(Path("C:/femm42/bin/femm.exe"))
        executable = next((p.resolve() for p in candidates if p.is_absolute() and p.is_file() and (p.suffix.lower() == ".exe" if os.name == "nt" else os.access(p, os.X_OK))), None)
        detected = executable is not None
        return ToolStatus(
            tool_id=self.tool_id, display_name=self.display_name, configured_path=configured_path,
            executable=str(executable) if executable else None, detected=detected,
            state="FOUND_UNVERIFIED" if detected else "NOT_INSTALLED",
            diagnostic=("Executable found. Version, compatibility and reference benchmark are not verified; solver execution disabled." if detected else "No executable found. Configure an absolute executable path or install from the official source."),
            official_url=self.official_url,
        )

    def run(self, *args, **kwargs):
        raise NotImplementedError("Solver execution is not implemented or qualified")


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter):
        if adapter.tool_id in self._adapters:
            raise ValueError(f"Duplicate adapter: {adapter.tool_id}")
        self._adapters[adapter.tool_id] = adapter

    def get(self, tool_id):
        if tool_id not in self._adapters:
            raise ValueError(f"Unknown registered tool: {tool_id}")
        return self._adapters[tool_id]

    def list(self):
        return list(self._adapters.values())

    @classmethod
    def defaults(cls):
        registry = cls()
        definitions = [
            ("ltspice", "LTspice", ["LTspice.exe"], ["ADI/LTspice/LTspice.exe"], "https://www.analog.com/ltspice"),
            ("femm", "FEMM", ["femm.exe"], ["femm*/bin/femm.exe"], "https://www.femm.info/"),
            ("kicad", "KiCad CLI", ["kicad-cli.exe", "kicad-cli"], ["KiCad/*/bin/kicad-cli.exe"], "https://www.kicad.org/"),
        ]
        for definition in definitions:
            registry.register(DiscoveryAdapter(*definition))
        return registry
