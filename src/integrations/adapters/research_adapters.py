from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from integrations.contracts import (
    ToolDescriptor,
    ToolKind,
    ToolState,
    JobRequest,
    JobResult,
    JobState,
)
from .base import BaseToolAdapter


class SwitchLossDBAdapter(BaseToolAdapter):
    """Adapter for SwitchLossDB power semiconductor switching loss dataset."""

    def __init__(self):
        super().__init__(
            tool_id="switchlossdb",
            name="SwitchLossDB",
            kind=ToolKind.DATASET,
            category="dataset",
            license_name="CC-BY-4.0",
            official_url="https://github.com/switchloss/switchloss-db",
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version="1.0-dataset",
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=ToolState.READY,
            diagnostic="SwitchLossDB dataset interface ready for CSV/JSON ingestion",
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["query_device", "import_csv", "verify_checksum"]


class MagNetDatasetAdapter(BaseToolAdapter):
    """Adapter for MagNet research dataset (core loss under arbitrary waveforms)."""

    def __init__(self):
        super().__init__(
            tool_id="magnet-dataset",
            name="MagNet Dataset",
            kind=ToolKind.DATASET,
            category="dataset",
            license_name="CC-BY-4.0 / Academic",
            official_url="https://www.princeton.edu/~minjie/magnet.html",
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version="2024.1",
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=ToolState.READY,
            diagnostic="MagNet dataset reader ready for core loss waveform ingestion",
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["query_material", "import_waveform_data", "verify_checksum"]


class MagNetMLBenchmarksAdapter(BaseToolAdapter):
    """Adapter for MagNet ML Benchmarks."""

    def __init__(self):
        super().__init__(
            tool_id="magnet-ml-benchmarks",
            name="MagNet ML Benchmarks",
            kind=ToolKind.BENCHMARK,
            category="benchmark",
            license_name="Academic Open Source",
            official_url="https://github.com/minjiechen/MagNet",
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version="1.2-benchmarks",
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=ToolState.READY,
            diagnostic="Neural network benchmark metrics schema active",
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["evaluate_benchmark", "compare_error_metrics"]


class MagNetPrincetonAdapter(BaseToolAdapter):
    """Adapter / Reference entry for MagNet (Princeton University)."""

    def __init__(self):
        super().__init__(
            tool_id="magnet-princeton",
            name="MagNet (Princeton University)",
            kind=ToolKind.RESEARCH_RESOURCE,
            category="research_resource",
            license_name="Academic Research",
            official_url="https://www.princeton.edu/~minjie/magnet.html",
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version="Reference-Hub",
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=ToolState.READY,
            diagnostic="Princeton Power Electronics research hub reference entry",
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["browse_publications", "fetch_material_constants"]
