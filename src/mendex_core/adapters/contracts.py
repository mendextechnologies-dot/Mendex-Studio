from pathlib import Path
from typing import Protocol

from pydantic import Field

from mendex_core.models import Model, Specification
from mendex_core.evidence import SimulationRun


class AdapterCapabilities(Model):
    tool_id: str
    adapter_version: str = "0.1.0"
    supported_os: list[str] = Field(default_factory=lambda: ["Windows"])
    supported_tool_versions: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=lambda: ["discovery"])
    input_schema: str = "Specification:1.0"
    output_schema: str = "SimulationRun:1.0"
    timeout_s: int = Field(default=60, gt=0)
    error_taxonomy: list[str] = Field(default_factory=lambda: ["NOT_INSTALLED", "UNQUALIFIED", "NOT_SUPPORTED"])
    execution_enabled: bool = False


class AdapterCheck(Model):
    status: str = "not_evaluated"
    diagnostic: str = "No independently checked benchmark has been executed"


class PreparedJob(Model):
    tool_id: str
    workdir: str
    input_hash: str


class ResultBundle(Model):
    status: str = "not_evaluated"
    metrics: dict[str, float] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class ToolAdapter(Protocol):
    tool_id: str
    def probe(self, configured_path=None): ...
    def capabilities(self) -> AdapterCapabilities: ...
    def validate(self, spec: Specification) -> AdapterCheck: ...
    def prepare(self, spec: Specification, workdir: Path) -> PreparedJob: ...
    def run(self, job: PreparedJob, timeout_s: int = 60) -> SimulationRun: ...
    def parse(self, record: SimulationRun) -> ResultBundle: ...
    def self_test(self) -> AdapterCheck: ...
