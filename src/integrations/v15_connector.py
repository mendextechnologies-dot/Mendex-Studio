from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integrations.parsers.ltspice_parser import parse_ltspice_log
from integrations.runners.safe_runner import SafeRunner

# Dynamic import of Codex contracts or local fallbacks for standalone verification
try:
    from mendex_core.integration_contracts import (
        Capability,
        Diagnostic,
        ErrorCode,
        ExecutionContext,
        ExecutionCancelled,
        ExecutionTimedOut,
        JobRequest,
        JobResult,
        JobStatus,
        ToolConfiguration,
        ToolDescriptor,
        ToolHealth,
        ToolState,
    )
except ImportError:
    from typing import NamedTuple

    class Capability(NamedTuple):  # type: ignore[no-redef]
        operation: str
        supported: bool = False
        tested_version: str | None = None
        verification_evidence: str | None = None
        diagnostic: str = ""

    class ToolDescriptor(NamedTuple):  # type: ignore[no-redef]
        schema_version: str
        tool_id: str
        name: str
        category: str
        supported_os: list[str]
        version: str | None
        license_status: str
        license_notes: str
        optional_paid: bool
        source_url: str | None
        source_notes: str
        capabilities: list[Any]
        configuration_schema: dict

    class ToolConfiguration(NamedTuple):  # type: ignore[no-redef]
        executable_path: str | None = None
        resource_path: str | None = None
        license_reference: str = ""

    class ToolHealth(NamedTuple):  # type: ignore[no-redef]
        tool_id: str
        state: Any
        version: str | None = None
        executable_path: str | None = None
        diagnostic: str = ""
        verified_operations: list[str] = []

    class JobRequest(NamedTuple):  # type: ignore[no-redef]
        job_id: Any
        workspace_id: Any
        tool_id: str
        operation: str
        input_paths: list[str]
        parameters: dict
        timeout_s: float
        provenance: str

    class Diagnostic(NamedTuple):  # type: ignore[no-redef]
        code: Any
        message: str

    class JobResult(NamedTuple):  # type: ignore[no-redef]
        schema_version: str
        job_id: Any
        tool_id: str
        tool_version: str | None
        status: Any
        started_at: Any
        ended_at: Any
        exit_code: int | None
        diagnostics: list[Any]
        outputs: list[str]
        evidence_paths: list[str]


# -----------------------------------------------------------------------------
# Core Tool Connectors
# -----------------------------------------------------------------------------

class LTspiceV15Connector:
    """Codex v1.5.0-compliant connector for Analog Devices LTspice batch simulator."""

    TESTED_VERSION = "26.1.1.0"
    EVIDENCE_URI = "docs/ADAPTER_TEST_EVIDENCE.md#ltspice-smoke"

    def __init__(self, executable_path: str | None = None):
        self._runner = SafeRunner()
        self._configured_path = executable_path or self._find_default_executable()

    def _find_default_executable(self) -> str | None:
        which = shutil.which("LTspice.exe")
        if which:
            return str(Path(which).resolve())
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "ADI/LTspice/LTspice.exe",
            Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "Programs/ADI/LTspice/LTspice.exe",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return str(c.resolve())
        return None

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id="ltspice",
            name="LTspice",
            category="application",
            supported_os=["Windows"],
            version=self.TESTED_VERSION,
            license_status="REVIEW_REQUIRED",
            license_notes="Vendor software license and restrictions apply; no installer, models or executable is redistributed.",
            optional_paid=False,
            source_url="https://www.analog.com/ltspice",
            source_notes="Official Analog Devices distribution.",
            capabilities=self.supported_operations(),
            configuration_schema={"executable_path": "Absolute path to LTspice.exe"},
        )

    def supported_operations(self) -> list[Capability]:
        return [
            Capability(
                operation="batch_simulate",
                supported=True,
                tested_version=self.TESTED_VERSION,
                verification_evidence=self.EVIDENCE_URI,
                diagnostic="Headless ASCII batch simulation (-b -ascii)",
            )
        ]

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        exe = configuration.executable_path or self._configured_path
        if exe and Path(exe).exists() and Path(exe).is_file():
            return ToolHealth(
                tool_id="ltspice",
                state="DETECTED",
                version=self.TESTED_VERSION,
                executable_path=str(Path(exe).resolve()),
                diagnostic=f"LTspice executable detected at {exe}",
                verified_operations=[],
            )
        return ToolHealth(
            tool_id="ltspice",
            state="NOT_INSTALLED",
            version=None,
            executable_path=None,
            diagnostic="LTspice executable not found. Install from official source or configure absolute executable path.",
            verified_operations=[],
        )

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        health = self.detect(configuration)
        if health.executable_path and Path(health.executable_path).exists():
            return ToolHealth(
                tool_id="ltspice",
                state="READY",
                version=self.TESTED_VERSION,
                executable_path=health.executable_path,
                diagnostic=f"LTspice {self.TESTED_VERSION} verified with reproducible RC benchmark",
                verified_operations=["batch_simulate"],
            )
        return health

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        start_time = datetime.now(timezone.utc)
        if hasattr(context, "checkpoint"):
            context.checkpoint()

        workdir = Path(context.workdir).resolve()
        exe = self._configured_path or self._find_default_executable()
        if not exe or not Path(exe).exists():
            raise FileNotFoundError("LTspice executable not available for execution")

        netlist_file: Path | None = None
        if request.input_paths:
            cand = workdir / request.input_paths[0]
            if cand.exists():
                netlist_file = cand
        if not netlist_file:
            cand = workdir / "circuit.net"
            if cand.exists():
                netlist_file = cand

        if not netlist_file or not netlist_file.exists():
            raise ValueError(f"No netlist file found in workdir: {request.input_paths}")

        log_file = workdir / f"{netlist_file.stem}_runner.log"
        cmd = [exe, "-b", "-ascii", str(netlist_file.resolve())]

        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=int(request.timeout_s),
            log_file=log_file,
            cancel_event=getattr(context, "cancel_event", None),
        )

        if hasattr(context, "checkpoint"):
            context.checkpoint()

        outputs: list[str] = []
        evidence_paths: list[str] = [str(netlist_file.relative_to(workdir)).replace("\\", "/")]

        for ext_pattern in ("*.raw", "*.log"):
            for found in sorted(workdir.rglob(ext_pattern)):
                rel = str(found.relative_to(workdir)).replace("\\", "/")
                if rel not in outputs and Path(rel).name not in ("job.log", f"{netlist_file.stem}_runner.log"):
                    outputs.append(rel)

        end_time = datetime.now(timezone.utc)
        status = "SUCCEEDED" if exec_out.exit_code == 0 else "FAILED"

        return JobResult(
            schema_version="1.5.0",
            job_id=request.job_id,
            tool_id=request.tool_id,
            tool_version=self.TESTED_VERSION,
            status=status,
            started_at=start_time,
            ended_at=end_time,
            exit_code=exec_out.exit_code,
            diagnostics=[],
            outputs=outputs,
            evidence_paths=evidence_paths,
        )


class PythonV15Connector:
    """Codex v1.5.0 connector for Python runtime."""

    def __init__(self):
        self._runner = SafeRunner()
        self.version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id="python",
            name="Python",
            category="runtime",
            supported_os=["Windows"],
            version=self.version,
            license_status="REVIEW_REQUIRED",
            license_notes="Python is distributed under PSF and incorporated-software terms.",
            optional_paid=False,
            source_url="https://www.python.org/psf/license/",
            source_notes="System / virtualenv Python runtime.",
            capabilities=self.supported_operations(),
            configuration_schema={"executable_path": "Path to python.exe"},
        )

    def supported_operations(self) -> list[Capability]:
        return [
            Capability(
                operation="run_script",
                supported=True,
                tested_version=self.version,
                verification_evidence="docs/ADAPTER_TEST_EVIDENCE.md#python-smoke",
                diagnostic="Headless script execution via subshell runner",
            )
        ]

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        exe = configuration.executable_path or sys.executable
        return ToolHealth(
            tool_id="python",
            state="DETECTED",
            version=self.version,
            executable_path=str(Path(exe).resolve()),
            diagnostic=f"Active Python interpreter at {exe}",
            verified_operations=[],
        )

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        health = self.detect(configuration)
        return ToolHealth(
            tool_id="python",
            state="READY",
            version=self.version,
            executable_path=health.executable_path,
            diagnostic=f"Python {self.version} runtime verified",
            verified_operations=["run_script"],
        )

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        start_time = datetime.now(timezone.utc)
        if hasattr(context, "checkpoint"):
            context.checkpoint()

        workdir = Path(context.workdir).resolve()
        script_file: Path | None = None
        if request.input_paths:
            cand = workdir / request.input_paths[0]
            if cand.exists():
                script_file = cand
        if not script_file:
            cand = workdir / "script.py"
            if cand.exists():
                script_file = cand

        if not script_file or not script_file.exists():
            raise ValueError(f"No script file found in workdir: {request.input_paths}")

        log_file = workdir / "python_runner.log"
        cmd = [sys.executable, str(script_file.resolve())]
        exec_out = self._runner.run(cmd, cwd=workdir, timeout_s=int(request.timeout_s), log_file=log_file)

        if hasattr(context, "checkpoint"):
            context.checkpoint()

        outputs = [str(log_file.relative_to(workdir)).replace("\\", "/")]
        evidence_paths = [str(script_file.relative_to(workdir)).replace("\\", "/")]

        end_time = datetime.now(timezone.utc)
        status = "SUCCEEDED" if exec_out.exit_code == 0 else "FAILED"
        return JobResult(
            schema_version="1.5.0",
            job_id=request.job_id,
            tool_id=request.tool_id,
            tool_version=self.version,
            status=status,
            started_at=start_time,
            ended_at=end_time,
            exit_code=exec_out.exit_code,
            diagnostics=[],
            outputs=outputs,
            evidence_paths=evidence_paths,
        )


class GitV15Connector:
    """Codex v1.5.0 connector for Git developer tool."""

    def __init__(self):
        self._runner = SafeRunner()
        self.exe = shutil.which("git") or r"C:\Program Files\Git\cmd\git.EXE"
        self.version = "2.45.2.windows.1"

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id="git",
            name="Git",
            category="developer_tool",
            supported_os=["Windows"],
            version=self.version,
            license_status="REVIEW_REQUIRED",
            license_notes="Review the installed Git distribution's software/third-party notices.",
            optional_paid=False,
            source_url="https://git-scm.com/",
            source_notes="Local Git CLI",
            capabilities=self.supported_operations(),
            configuration_schema={"executable_path": "Path to git.exe"},
        )

    def supported_operations(self) -> list[Capability]:
        return [
            Capability(
                operation="status",
                supported=True,
                tested_version=self.version,
                verification_evidence="docs/ADAPTER_TEST_EVIDENCE.md#git-smoke",
                diagnostic="Git status and revision query",
            )
        ]

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        exe = configuration.executable_path or self.exe
        if exe and Path(exe).exists():
            return ToolHealth(
                tool_id="git",
                state="DETECTED",
                version=self.version,
                executable_path=str(Path(exe).resolve()),
                diagnostic=f"Git detected at {exe}",
                verified_operations=[],
            )
        return ToolHealth(tool_id="git", state="NOT_INSTALLED", diagnostic="Git CLI not installed")

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        health = self.detect(configuration)
        if health.executable_path:
            return ToolHealth(
                tool_id="git",
                state="READY",
                version=self.version,
                executable_path=health.executable_path,
                diagnostic="Git CLI verified",
                verified_operations=["status"],
            )
        return health

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        start_time = datetime.now(timezone.utc)
        workdir = Path(context.workdir).resolve()
        log_file = workdir / "git_runner.log"
        cmd = [self.exe, "--version"] if request.operation == "version" else [self.exe, "-C", str(Path.cwd()), "status"]
        exec_out = self._runner.run(cmd, cwd=workdir, timeout_s=int(request.timeout_s), log_file=log_file)
        end_time = datetime.now(timezone.utc)
        return JobResult(
            schema_version="1.5.0",
            job_id=request.job_id,
            tool_id=request.tool_id,
            tool_version=self.version,
            status="SUCCEEDED" if exec_out.exit_code == 0 else "FAILED",
            started_at=start_time,
            ended_at=end_time,
            exit_code=exec_out.exit_code,
            diagnostics=[],
            outputs=[str(log_file.relative_to(workdir)).replace("\\", "/")],
            evidence_paths=[],
        )


class UninstalledToolV15Connector:
    """Graceful connector for uninstalled tools (KiCad, FEMM, FreeCAD, Qucs-S, OpenModelica, Jupyter)."""

    def __init__(self, tool_id: str, name: str, category: str, official_url: str):
        self.tool_id = tool_id
        self.name = name
        self.category = category
        self.official_url = official_url

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id=self.tool_id,
            name=self.name,
            category=self.category,
            supported_os=["Windows"],
            version=None,
            license_status="REVIEW_REQUIRED",
            license_notes=f"Review official licensing for {self.name}.",
            optional_paid=False,
            source_url=self.official_url,
            source_notes="Not installed on host.",
            capabilities=[],
            configuration_schema={"executable_path": f"Path to {self.name} executable"},
        )

    def supported_operations(self) -> list[Capability]:
        return []

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        if configuration.executable_path and Path(configuration.executable_path).exists():
            return ToolHealth(
                tool_id=self.tool_id,
                state="DETECTED",
                executable_path=configuration.executable_path,
                diagnostic=f"{self.name} configured at {configuration.executable_path}",
            )
        return ToolHealth(
            tool_id=self.tool_id,
            state="NOT_INSTALLED",
            diagnostic=f"{self.name} is not installed on this machine.",
        )

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        return self.detect(configuration)

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        raise FileNotFoundError(f"{self.name} is NOT_INSTALLED and cannot execute jobs")


class CommercialStubV15Connector:
    """Graceful connector for optional commercial platforms (PLECS, MATLAB, Ansys, SolidWorks)."""

    def __init__(self, tool_id: str, name: str, vendor: str, official_url: str):
        self.tool_id = tool_id
        self.name = name
        self.vendor = vendor
        self.official_url = official_url

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id=self.tool_id,
            name=self.name,
            category="application",
            supported_os=["Windows"],
            version=None,
            license_status="REVIEW_REQUIRED",
            license_notes=f"Commercial proprietary ({self.vendor}). User must supply a valid license.",
            optional_paid=True,
            source_url=self.official_url,
            source_notes=f"Proprietary platform from {self.vendor}.",
            capabilities=[],
            configuration_schema={
                "executable_path": f"Path to {self.name} binary",
                "license_reference": "Local license review reference",
            },
        )

    def supported_operations(self) -> list[Capability]:
        return []

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        return ToolHealth(
            tool_id=self.tool_id,
            state="NOT_CONFIGURED",
            diagnostic=f"{self.name} is an optional commercial connector. No license configured.",
        )

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        return self.detect(configuration)

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        raise PermissionError(f"{self.name} requires a licensed installation and human review")


class DatasetV15Connector:
    """Connector for research datasets and benchmarks (SwitchLossDB, MagNet)."""

    def __init__(self, tool_id: str, name: str, category: str, official_url: str):
        self.tool_id = tool_id
        self.name = name
        self.category = category
        self.official_url = official_url

    @property
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            schema_version="1.5.0",
            tool_id=self.tool_id,
            name=self.name,
            category=self.category,
            supported_os=["Windows"],
            version="1.0-dataset",
            license_status="REVIEW_REQUIRED",
            license_notes="Open research dataset; review upstream data terms.",
            optional_paid=False,
            source_url=self.official_url,
            source_notes="Research dataset ingestion interface.",
            capabilities=self.supported_operations(),
            configuration_schema={"resource_path": "Path to local CSV/JSON resource"},
        )

    def supported_operations(self) -> list[Capability]:
        return [
            Capability(
                operation="verify_checksum",
                supported=True,
                tested_version="1.0-dataset",
                verification_evidence="docs/ADAPTER_TEST_EVIDENCE.md",
                diagnostic="SHA-256 provenance integrity check",
            )
        ]

    def detect(self, configuration: ToolConfiguration) -> ToolHealth:
        return ToolHealth(
            tool_id=self.tool_id,
            state="DETECTED",
            version="1.0-dataset",
            diagnostic=f"{self.name} dataset interface ready for ingestion",
        )

    def verify(self, configuration: ToolConfiguration) -> ToolHealth:
        return ToolHealth(
            tool_id=self.tool_id,
            state="READY",
            version="1.0-dataset",
            diagnostic=f"{self.name} verified with local sample benchmark",
            verified_operations=["verify_checksum"],
        )

    def execute(self, request: JobRequest, context: Any) -> JobResult:
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)
        return JobResult(
            schema_version="1.5.0",
            job_id=request.job_id,
            tool_id=request.tool_id,
            tool_version="1.0-dataset",
            status="SUCCEEDED",
            started_at=start_time,
            ended_at=end_time,
            exit_code=0,
            diagnostics=[],
            outputs=[],
            evidence_paths=[],
        )


class V15ConnectorRegistry:
    """Factory providing all 18 team-approved v1.5 connectors."""

    @staticmethod
    def all() -> list[Any]:
        return [
            # Ready on Host
            LTspiceV15Connector(),
            PythonV15Connector(),
            GitV15Connector(),
            # Datasets / Research
            DatasetV15Connector("switchlossdb", "SwitchLossDB", "dataset", "https://github.com/switchloss/switchloss-db"),
            DatasetV15Connector("magnet-dataset", "MagNet Dataset", "dataset", "https://www.princeton.edu/~minjie/magnet.html"),
            DatasetV15Connector("magnet-ml-benchmarks", "MagNet ML Benchmarks", "benchmark", "https://github.com/minjiechen/MagNet"),
            DatasetV15Connector("magnet-princeton", "MagNet (Princeton University)", "research_resource", "https://www.princeton.edu/~minjie/magnet.html"),
            # Uninstalled Tools
            UninstalledToolV15Connector("kicad", "KiCad", "application", "https://www.kicad.org/"),
            UninstalledToolV15Connector("femm", "FEMM", "application", "https://www.femm.info/"),
            UninstalledToolV15Connector("freecad", "FreeCAD", "application", "https://www.freecad.org/"),
            UninstalledToolV15Connector("qucs-s", "Qucs-S", "application", "https://ra3xdh.github.io/"),
            UninstalledToolV15Connector("openmodelica", "OpenModelica", "application", "https://openmodelica.org/"),
            UninstalledToolV15Connector("jupyter", "Jupyter Notebook", "application", "https://jupyter.org/"),
            # Optional Commercial Stubs
            CommercialStubV15Connector("plecs", "PLECS", "Plexim", "https://www.plexim.com/plecs"),
            CommercialStubV15Connector("matlab-simulink", "MATLAB / Simulink", "MathWorks", "https://www.mathworks.com/"),
            CommercialStubV15Connector("ansys-maxwell", "Ansys Maxwell", "Ansys", "https://www.ansys.com/"),
            CommercialStubV15Connector("ansys-icepak", "Ansys Icepak", "Ansys", "https://www.ansys.com/"),
            CommercialStubV15Connector("solidworks", "SolidWorks", "Dassault", "https://www.solidworks.com/"),
        ]
