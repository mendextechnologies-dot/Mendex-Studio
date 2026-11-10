"""Codex queue, persistence and evidence orchestration, not a subprocess runner."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, RLock
from time import monotonic
from uuid import UUID, uuid4
import html
import json
import os

from pydantic import ValidationError

from .catalog import descriptors, unconnected_health
from .demo_adapter import SyntheticAdapter
from .evidence import digest
from .integration_contracts import (ArtifactManifest, Diagnostic, ErrorCode, EvidenceManifest, ExecutionCancelled, ExecutionContext, ExecutionTimedOut, JobRecord, JobRequest, JobResult, JobStatus, TERMINAL, ToolConfiguration, ToolHealth, ToolState, safe_relative)
from .models import now
from .service import StudioError


class IntegrationService:
    def __init__(self, studio):
        self.studio = studio
        self.catalog = descriptors()
        self.adapters = {"studio-demo": SyntheticAdapter()}
        self._executor = None
        self._events, self._futures = {}, {}
        self._staged_hashes = {}
        self._lock = RLock()
        self._closed = False

    def list_tools(self):
        return list(self.catalog.values())

    def descriptor(self, tool_id):
        if tool_id in self.catalog:
            return self.catalog[tool_id]
        if tool_id in self.adapters:
            return self.adapters[tool_id].descriptor
        raise StudioError("NOT_FOUND", "Tool is not registered in the frozen catalog")

    def configuration(self, tool_id):
        self.descriptor(tool_id)
        with self.studio.connection() as db:
            row = db.execute("SELECT payload FROM integration_settings WHERE tool_id=?", (tool_id,)).fetchone()
        return ToolConfiguration.model_validate_json(row[0]) if row else ToolConfiguration()

    def configure(self, tool_id, configuration):
        self.descriptor(tool_id)
        configuration = ToolConfiguration.model_validate(configuration)
        for key in ("executable_path", "resource_path"):
            value = getattr(configuration, key)
            if value:
                path = Path(value)
                if not path.is_absolute() or not path.exists():
                    raise StudioError("INVALID_INPUT", "Configure an existing absolute path")
                if key == "executable_path" and (not path.is_file() or (os.name == "nt" and path.suffix.lower() != ".exe")):
                    raise StudioError("INVALID_INPUT", "Executable configuration requires a real executable file")
                setattr(configuration, key, str(path.resolve()))
        with self.studio.connection() as db:
            db.execute("INSERT OR REPLACE INTO integration_settings VALUES (?,?)", (tool_id, configuration.model_dump_json()))
            db.execute("DELETE FROM integration_health WHERE tool_id=?", (tool_id,))
        return self.detect(tool_id)

    def detect(self, tool_id):
        descriptor, configuration = self.descriptor(tool_id), self.configuration(tool_id)
        if tool_id in self.adapters:
            health = ToolHealth.model_validate(self.adapters[tool_id].detect(configuration))
            # detect() may never upgrade software readiness; verify() owns that gate.
            if health.state == ToolState.READY:
                health.state = ToolState.DETECTED
                health.verified_operations = []
        else:
            health = unconnected_health(descriptor, configuration, self.studio.registry)
        return health

    def verify(self, tool_id):
        descriptor, configuration = self.descriptor(tool_id), self.configuration(tool_id)
        if descriptor.optional_paid and not configuration.license_reference:
            return ToolHealth(tool_id=tool_id, state=ToolState.NOT_CONFIGURED, diagnostic="Optional licensed connector needs a local license-review reference; no purchase or activation is performed")
        if tool_id not in self.adapters:
            detected = self.detect(tool_id)
            detected.diagnostic += " Verification unavailable until Agent 2 supplies an approved connector."
            return detected
        adapter = self.adapters[tool_id]
        health = ToolHealth.model_validate(adapter.verify(configuration))
        capabilities = {cap.operation: cap for cap in adapter.supported_operations()}
        if health.tool_id != tool_id:
            raise StudioError("INVALID_INPUT", "Adapter verification returned a different tool ID")
        if health.state == ToolState.READY:
            if not health.version or not health.verified_operations or any(op not in capabilities or not capabilities[op].supported or capabilities[op].tested_version != health.version or not capabilities[op].verification_evidence for op in health.verified_operations):
                health = ToolHealth(tool_id=tool_id, state=ToolState.DETECTED, version=health.version, diagnostic="READY rejected: missing tested-version/operation/smoke-evidence declarations")
        with self.studio.connection() as db:
            db.execute("INSERT OR REPLACE INTO integration_health VALUES (?,?)", (tool_id, health.model_dump_json()))
        return health

    def register_reviewed_adapter(self, adapter):
        descriptor = self.descriptor(adapter.descriptor.tool_id)
        if descriptor.tool_id in self.adapters:
            raise StudioError("CONFLICT", "Adapter already attached")
        # Integration hook for an agreed, reviewed Agent 2 PR; no dynamic imports.
        self.adapters[descriptor.tool_id] = adapter

    def create_workspace(self, name="Generic integration workspace"):
        if not name.strip() or len(name) > 200:
            raise StudioError("INVALID_INPUT", "Supply a workspace name up to 200 characters")
        workspace_id = uuid4()
        with self.studio.connection() as db:
            db.execute("INSERT INTO integration_workspaces VALUES (?,?)", (str(workspace_id), name.strip()))
        self.workspace_path(workspace_id).mkdir(parents=True, exist_ok=False)
        return {"workspace_id": str(workspace_id), "name": name.strip()}

    def list_workspaces(self):
        with self.studio.connection() as db:
            return [{"workspace_id": row[0], "name": row[1]} for row in db.execute("SELECT id,name FROM integration_workspaces ORDER BY rowid")]

    def workspace_path(self, workspace_id):
        identifier = str(UUID(str(workspace_id)))
        with self.studio.connection() as db:
            if not db.execute("SELECT 1 FROM integration_workspaces WHERE id=?", (identifier,)).fetchone():
                raise StudioError("NOT_FOUND", "Integration workspace not found")
        path = (self.studio.root / ".mendex" / "iw" / UUID(identifier).hex).resolve()
        if not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "Workspace path escapes data root")
        return path

    def attach_input(self, workspace_id, source):
        source = Path(source)
        if not source.is_absolute() or not source.is_file() or source.stat().st_size > 10 * 1024 * 1024:
            raise StudioError("INVALID_INPUT", "Choose an existing absolute input file up to 10 MiB")
        data = source.read_bytes()
        if len(data) > 10 * 1024 * 1024:
            raise StudioError("INVALID_INPUT", "Input file grew beyond 10 MiB")
        workspace = self.workspace_path(workspace_id)
        destination = (workspace / "inputs" / (uuid4().hex[:12] + source.suffix[:16])).resolve()
        if not destination.is_relative_to(workspace):
            raise StudioError("INVALID_INPUT", "Input staging path escapes workspace")
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(data)
        return str(destination.relative_to(workspace))

    def job_path(self, job_id):
        path = (self.studio.root / ".mendex" / "ij" / UUID(str(job_id)).hex).resolve()
        if not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "Job path escapes data root")
        return path

    def job(self, job_id):
        with self.studio.connection() as db:
            row = db.execute("SELECT payload FROM integration_jobs WHERE id=?", (str(UUID(str(job_id))),)).fetchone()
        if not row:
            raise StudioError("NOT_FOUND", "Integration job not found")
        return JobRecord.model_validate_json(row[0])

    def list_jobs(self, workspace_id=None):
        with self.studio.connection() as db:
            query, params = ("SELECT payload FROM integration_jobs ORDER BY rowid DESC", ()) if workspace_id is None else ("SELECT payload FROM integration_jobs WHERE workspace_id=? ORDER BY rowid DESC", (str(workspace_id),))
            return [JobRecord.model_validate_json(row[0]) for row in db.execute(query, params)]

    def _store_job(self, record, manifest_hash=None):
        with self.studio.connection() as db:
            db.execute("UPDATE integration_jobs SET status=?,payload=?,manifest_sha256=COALESCE(?,manifest_sha256) WHERE id=?", (record.status.value, record.model_dump_json(), manifest_hash, str(record.request.job_id)))

    def submit(self, request, retry_of=None):
        if self._closed:
            raise StudioError("CONFLICT", "This job session is closed; reopen Studio before submitting")
        request = JobRequest.model_validate(request)
        if len(request.model_dump_json()) > 128 * 1024:
            raise StudioError("INVALID_INPUT", "Job request exceeds 128 KiB")
        adapter = self.adapters.get(request.tool_id)
        health = self.verify(request.tool_id)
        if adapter is None or health.state != ToolState.READY or request.operation not in health.verified_operations:
            raise StudioError("UNSUPPORTED", "This exact tool operation/version has no verified execution connector. Use the synthetic demo or wait for Agent 2.")
        workspace, directory = self.workspace_path(request.workspace_id), self.job_path(request.job_id)
        if directory.exists():
            raise StudioError("CONFLICT", "Job ID/workdir already exists; retry must use a new ID")
        staged = []
        for relative in request.input_paths:
            source = (workspace / relative).resolve()
            if not source.is_relative_to(workspace) or not source.is_file() or source.stat().st_size > 10 * 1024 * 1024:
                raise StudioError("INVALID_INPUT", "Input is missing, outside workspace or exceeds 10 MiB")
            if Path(relative).parts[0] in {"job.log", "request.json", "manifest.json", "report.html", "report.json"}:
                raise StudioError("INVALID_INPUT", "Input conflicts with reserved job metadata")
            with source.open("rb") as handle:
                data = handle.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024:
                raise StudioError("INVALID_INPUT", "Input grew beyond the 10 MiB limit")
            staged.append((relative, data))
        directory.mkdir(parents=True, exist_ok=False)
        hashes = {}
        for relative, data in staged:
            destination = (directory / relative).resolve()
            if not destination.is_relative_to(directory):
                raise StudioError("INVALID_INPUT", "Input path escapes job")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            hashes[relative] = digest(data)
        (directory / "request.json").write_text(request.model_dump_json(indent=2), encoding="utf-8")
        record = JobRecord(request=request, retry_of=retry_of)
        with self.studio.connection() as db:
            db.execute("INSERT INTO integration_jobs (id,workspace_id,status,payload) VALUES (?,?,?,?)", (str(request.job_id), str(request.workspace_id), record.status.value, record.model_dump_json()))
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mendex-integration")
            event = Event()
            self._events[str(request.job_id)] = event
            self._staged_hashes[str(request.job_id)] = hashes
            self._futures[str(request.job_id)] = self._executor.submit(self._run, record, adapter, directory, hashes, event)
        return self.job(request.job_id)

    def _log(self, directory, message):
        path = (directory / "job.log").resolve()
        if not path.is_relative_to(directory):
            raise ValueError("Log path escapes job directory")
        if path.exists() and path.stat().st_size >= 1024 * 1024:
            return
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{now().isoformat()} {str(message)[:4000]}\n")

    def _run(self, record, adapter, directory, hashes, event):
        record.status, record.started_at = JobStatus.RUNNING, now()
        self._store_job(record)
        def progress(value):
            record.progress = value
            self._store_job(record)
        context = ExecutionContext(directory, event, monotonic() + record.request.timeout_s, lambda message: self._log(directory, message), progress)
        try:
            context.checkpoint()
            result = JobResult.model_validate(adapter.execute(record.request.model_copy(deep=True), context))
            context.checkpoint()
            if result.job_id != record.request.job_id or result.tool_id != record.request.tool_id:
                raise ValueError("Adapter returned a mismatched job/tool ID")
            if len(result.outputs) + len(result.evidence_paths) > 128:
                raise ValueError("Adapter reported more than 128 artifacts")
            for relative in result.outputs + result.evidence_paths:
                path = (directory / safe_relative(relative)).resolve()
                if not path.is_relative_to(directory) or not path.is_file() or Path(relative).parts[0] in {"request.json", "job.log", "manifest.json", "report.html", "report.json"}:
                    raise ValueError("Adapter reported a missing, escaping or reserved artifact")
                if path.stat().st_size > 20 * 1024 * 1024:
                    raise ValueError("Reported artifact exceeds 20 MiB orchestration limit")
        except ExecutionCancelled:
            result = self._failure(record, JobStatus.CANCELLED, ErrorCode.CANCELLED, "Cooperative cancellation acknowledged; no engineering result")
        except ExecutionTimedOut:
            result = self._failure(record, JobStatus.TIMED_OUT, ErrorCode.TIMED_OUT, "Execution deadline exceeded; Agent 2 owns native process-tree termination")
        except (ValidationError, ValueError) as exc:
            result = self._failure(record, JobStatus.FAILED, ErrorCode.MALFORMED_OUTPUT, str(exc))
        except Exception as exc:
            result = self._failure(record, JobStatus.FAILED, ErrorCode.EXECUTION_FAILED, str(exc))
        try:
            return self._finalize(record, result, directory, hashes)
        except Exception as exc:
            record.status = JobStatus.FAILED
            record.result = self._failure(record, JobStatus.FAILED, ErrorCode.EXECUTION_FAILED, f"Evidence finalization failed; no successful evidence is claimed: {exc}")
            record.manifest_path = None
            self._store_job(record)
            return record

    def _finalize(self, record, result, directory, hashes):
        self._log(directory, f"Terminal software status: {result.status.value}; engineering NOT_EVALUATED")
        record.status, record.result = result.status, result
        if record.status == JobStatus.SUCCEEDED:
            record.progress = 1
        artifacts = []
        relatives = list(dict.fromkeys(result.outputs + result.evidence_paths + ["request.json", "job.log"]))
        for relative in relatives:
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory) or not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("Final evidence path is missing, escaping or oversized")
            artifacts.append(ArtifactManifest(relative_path=relative, file_type=path.suffix or "unknown", sha256=digest(path.read_bytes()), size_bytes=path.stat().st_size, source_job=record.request.job_id, provenance=record.request.provenance, source_label="SOFTWARE_LOG" if relative == "job.log" else ("SYNTHETIC" if record.request.tool_id == "studio-demo" else "IMPORTED"), raw_vs_derived="log" if relative == "job.log" else ("raw" if relative in result.evidence_paths or relative == "request.json" else "derived"), unit_conventions="No engineering quantities; synthetic software fixture" if record.request.tool_id == "studio-demo" else "Not interpreted by orchestration; adapter-specific unit review required"))
        manifest = EvidenceManifest(job_id=record.request.job_id, request=record.request, result=result, input_hashes=hashes, artifacts=artifacts)
        manifest_text = manifest.model_dump_json(indent=2)
        (directory / "manifest.json").write_bytes(manifest_text.encode("utf-8"))
        record.manifest_path = str((directory / "manifest.json").relative_to(self.studio.root))
        self._store_job(record, digest(manifest_text.encode("utf-8")))
        return record

    def _failure(self, record, status, code, message):
        return JobResult(job_id=record.request.job_id, tool_id=record.request.tool_id, status=status, started_at=record.started_at, diagnostics=[Diagnostic(code=code, message=message)])

    def cancel(self, job_id):
        record = self.job(job_id)
        if record.status in TERMINAL:
            return record
        with self._lock:
            event = self._events.get(str(record.request.job_id))
            if event is None:
                raise StudioError("INTERRUPTED", "This job belongs to another process/session; its runner must acknowledge cancellation")
            event.set()
            future = self._futures.get(str(record.request.job_id))
            if future and future.cancel():
                result = self._failure(record, JobStatus.CANCELLED, ErrorCode.CANCELLED, "Queued job cancelled before adapter execution")
                self._finalize(record, result, self.job_path(job_id), self._staged_hashes[str(record.request.job_id)])
        return self.job(job_id)

    def retry(self, job_id):
        record = self.job(job_id)
        if record.status not in TERMINAL:
            raise StudioError("CONFLICT", "Wait for a terminal status before retrying")
        data = record.request.model_dump()
        data["job_id"] = uuid4()
        return self.submit(JobRequest.model_validate(data), retry_of=record.request.job_id)

    def wait(self, job_id, timeout=10):
        future = self._futures.get(str(job_id))
        if future and not future.cancelled():
            future.result(timeout=timeout)
        return self.job(job_id)

    def logs(self, job_id):
        record = self.job(job_id)
        root = self.job_path(job_id)
        path = (root / "job.log").resolve()
        if not path.is_relative_to(root):
            raise StudioError("INVALID_INPUT", "Log path escapes job directory")
        if not path.is_file():
            return "QUEUED · no logs yet" if record.status == JobStatus.QUEUED else "Log unavailable; check evidence integrity"
        with path.open("rb") as handle:
            handle.seek(max(0, path.stat().st_size - 65536))
            return handle.read(65536).decode("utf-8", errors="replace")

    def evidence(self, job_id):
        record = self.job(job_id)
        if not record.manifest_path:
            return None
        path = (self.studio.root / record.manifest_path).resolve()
        if not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "Manifest path escapes data root")
        data = path.read_bytes()
        with self.studio.connection() as db:
            expected = db.execute("SELECT manifest_sha256 FROM integration_jobs WHERE id=?", (str(record.request.job_id),)).fetchone()[0]
        if not expected or digest(data) != expected:
            raise StudioError("INVALID_INPUT", "Evidence manifest was modified or is incomplete")
        return EvidenceManifest.model_validate_json(data)

    def evidence_integrity(self, job_id):
        try:
            manifest = self.evidence(job_id)
        except (OSError, ValueError, StudioError):
            return False
        if manifest is None:
            return False
        root = self.job_path(job_id)
        try:
            for relative, expected in list(manifest.input_hashes.items()) + [(artifact.relative_path, artifact.sha256) for artifact in manifest.artifacts]:
                path = (root / safe_relative(relative)).resolve()
                if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 20 * 1024 * 1024 or digest(path.read_bytes()) != expected:
                    return False
        except (OSError, ValueError):
            return False
        return True

    def export_report(self, job_id):
        record, manifest = self.job(job_id), self.evidence(job_id)
        if manifest is None:
            raise StudioError("CONFLICT", "A terminal job with an evidence manifest is required")
        intact = self.evidence_integrity(job_id)
        payload = {"status": "DRAFT SOFTWARE FRAMEWORK REPORT", "engineering_status": "NOT_EVALUATED", "evidence_integrity": intact, "record": record.model_dump(mode="json"), "manifest": manifest.model_dump(mode="json"), "limitations": ["Synthetic outputs are software test fixtures, not engineering simulation or measurement.", "Successful software execution is not an engineering pass."]}
        folder = self.job_path(job_id) / "reports" / uuid4().hex[:12]
        folder.mkdir(parents=True)
        text = json.dumps(payload, indent=2)
        (folder / "report.json").write_text(text, encoding="utf-8")
        (folder / "report.html").write_text('<!doctype html><html><head><meta charset="utf-8"><title>Mendex framework report</title></head><body><h1>Draft software-framework report</h1><p>Engineering NOT_EVALUATED · ' + ("evidence intact" if intact else "EVIDENCE INTEGRITY FAILURE") + '</p><pre style="white-space:pre-wrap;overflow-wrap:anywhere">' + html.escape(text) + '</pre></body></html>', encoding="utf-8")
        return folder / "report.html"

    def preview_artifact(self, job_id, relative_path):
        manifest = self.evidence(job_id)
        allowed = set(manifest.input_hashes) | {artifact.relative_path for artifact in manifest.artifacts} if manifest else set()
        if relative_path not in allowed or not self.evidence_integrity(job_id):
            raise StudioError("INVALID_INPUT", "Select an intact artifact declared by this job's manifest")
        path = (self.job_path(job_id) / safe_relative(relative_path)).resolve()
        if not path.is_relative_to(self.job_path(job_id)):
            raise StudioError("INVALID_INPUT", "Artifact preview escapes the job directory")
        if path.suffix.lower() not in {".json", ".txt", ".csv", ".log", ".md"}:
            return f"Binary/unsupported preview · {path.stat().st_size} bytes · SHA-256 recorded in manifest. No file was executed."
        with path.open("rb") as handle:
            data = handle.read(65536)
        return data.decode("utf-8", errors="replace") + ("\n[Preview limited to first 64 KiB]" if path.stat().st_size > 65536 else "")

    def open_framework_report(self, job_id, report_path):
        from .launch import open_native
        self.job(job_id)
        path = Path(report_path).resolve()
        report_root = (self.job_path(job_id) / "reports").resolve()
        if not path.is_relative_to(report_root) or not path.is_file() or path.suffix.lower() != ".html":
            raise StudioError("INVALID_INPUT", "Select this job's exported HTML report")
        try:
            open_native(path)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", str(exc)) from exc
        return str(path)

    def register_dataset(self, tool_id, source_url, version, license_reference, provenance, source_file=None):
        descriptor = self.descriptor(tool_id)
        if descriptor.category not in ("dataset", "benchmark", "research_resource"):
            raise StudioError("INVALID_INPUT", "Select a research/dataset/benchmark catalog entry")
        if not source_url.startswith("https://") or not version.strip() or not license_reference.strip() or not provenance.strip():
            raise StudioError("INVALID_INPUT", "Supply an HTTPS source, exact release/version, license-review reference and provenance")
        record = {"import_id": str(uuid4()), "tool_id": tool_id, "source_url": source_url, "version": version, "license_reference": license_reference, "provenance": provenance, "created_at": now().isoformat(), "review_state": "NOT_REVIEWED", "interpretation": "METADATA_ONLY; Agent 2 format parsing/license verification not performed", "sha256": None, "stored_path": None}
        if source_file:
            source = Path(source_file)
            if not source.is_absolute() or not source.is_file() or source.stat().st_size > 20 * 1024 * 1024:
                raise StudioError("INVALID_INPUT", "Optional resource file must be an existing absolute file up to 20 MiB")
            with source.open("rb") as handle:
                data = handle.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise StudioError("INVALID_INPUT", "Resource grew beyond the 20 MiB limit")
            folder = self.studio.root / ".mendex" / "datasets" / UUID(record["import_id"]).hex
            folder.mkdir(parents=True)
            destination = folder / "resource.bin"
            destination.write_bytes(data)
            record["sha256"], record["stored_path"] = digest(data), str(destination.relative_to(self.studio.root))
        with self.studio.connection() as db:
            db.execute("INSERT INTO integration_datasets VALUES (?,?,?)", (record["import_id"], tool_id, json.dumps(record)))
        return record

    def list_datasets(self):
        with self.studio.connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM integration_datasets ORDER BY rowid DESC")]

    def shutdown(self):
        with self._lock:
            self._closed = True
            for event in self._events.values():
                event.set()
            if self._executor:
                self._executor.shutdown(wait=False)
