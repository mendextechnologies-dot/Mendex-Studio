"""Presentation reads and safe handoffs. Engineering decisions remain in core services."""
import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
from uuid import uuid4

from ..evidence import specification_hash
from ..models import now
from ..service import StudioError
from . import models


class DesktopService:
    def __init__(self, studio):
        self.studio = studio
        try:
            from integrations.v15_connector import V15ConnectorRegistry
            for connector in V15ConnectorRegistry.all():
                if connector.descriptor.tool_id not in self.studio.integrations.adapters:
                    self.studio.integrations.register_reviewed_adapter(connector)
        except Exception:
            pass

    def handshake(self):
        return {"protocol_version": models.PROTOCOL_VERSION, "status": "READY", "data_root": str(self.studio.root),
                "python_version": platform.python_version(), "application": "Mendex Engineering Studio", "desktop_version": "3.1.0",
                "engineering_status": "NOT_EVALUATED", "timestamp": now().isoformat()}

    def projects(self):
        projects = []
        for product in self.studio.list_products():
            revision = self.studio.get_revision(product.active_revision_id)
            projects.append({**product.model_dump(mode="json"), "revision_label": revision.revision_label,
                             "revision_status": revision.lifecycle_status.value, "input_hash": specification_hash(revision.specification)})
        return projects

    def simulations(self):
        projects = {str(p.product_id): p for p in self.studio.list_products()}
        workspaces = {w["workspace_id"]: w for w in self.studio.integrations.list_workspaces()}
        rows = []
        for job in self.studio.integrations.list_jobs():
            wid = str(job.request.workspace_id)
            pid = job.request.parameters.get("project_id") or (wid if wid in projects else workspaces.get(wid, {}).get("product_id"))
            revision_id = job.request.parameters.get("revision_id")
            rows.append({"job_id": str(job.request.job_id), "project_id": pid, "project_name": projects[pid].name if pid in projects else workspaces.get(wid, {}).get("name", "Unassociated job"),
                         "revision_id": revision_id, "tool_id": job.request.tool_id, "operation": job.request.operation,
                         "status": job.status.value, "created_at": job.created_at.isoformat(),
                         "started_at": job.started_at.isoformat() if job.started_at else None,
                         "ended_at": job.result.ended_at.isoformat() if job.result else None,
                         "exit_code": job.result.exit_code if job.result else None, "progress": job.progress,
                         "evidence_available": job.manifest_path is not None, "workspace_id": wid,
                         "provenance": job.request.provenance, "engineering_status": "NOT_EVALUATED"})
        return rows

    def overview(self):
        projects, jobs = self.projects(), self.simulations()
        revisions = [r for p in projects for r in self.studio.list_revisions(p["product_id"])]
        pending = 0
        for revision in revisions:
            try:
                lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
                pending += sum(stage["status"] == "AWAITING_REVIEW" for stage in lifecycle["stages"])
            except StudioError as exc:
                if exc.code != "NOT_FOUND":
                    raise
        activity = [{"id": r["job_id"], "kind": "Simulation", "title": r["project_name"], "detail": r["tool_id"] + " · " + r["status"], "timestamp": r["ended_at"] or r["created_at"]} for r in jobs]
        activity += [{"id": str(r.revision_id), "kind": "Revision", "title": r.revision_label, "detail": "Recorded revision", "timestamp": r.created_at.isoformat()} for r in revisions]
        return {"projects": projects, "jobs": jobs[:8], "activity": sorted(activity, key=lambda a: a["timestamp"], reverse=True)[:12],
                "metrics": {"projects": len(projects), "revisions": len(revisions), "completed_simulations": sum(r["status"] == "SUCCEEDED" for r in jobs),
                            "failed_simulations": sum(r["status"] == "FAILED" for r in jobs), "review_requests": pending},
                "timestamp": now().isoformat()}

    def _records(self, kind, revision_id):
        return self.studio.engineering_records.list_records(kind, {"revision_id": revision_id, "limit": 500})

    def project(self, request):
        product = self.studio.get_product(request.project_id)
        revision = self.studio.get_revision(request.revision_id or product.active_revision_id)
        if revision.product_id != product.product_id:
            raise StudioError("INVALID_INPUT", "Revision does not belong to this project")
        try:
            lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
        except StudioError as exc:
            if exc.code != "NOT_FOUND":
                raise
            lifecycle = {"stages": [], "engineering_status": "NOT_EVALUATED", "approval_status": "UNAVAILABLE", "note": "This revision has not been explicitly enrolled. Historical assessment is not lifecycle completion."}
        files = []
        workspace = self.studio.workspace_path(revision)
        if workspace.exists():
            for path in sorted(workspace.rglob("*")):
                if len(files) >= 1000:
                    break
                if path.is_file() and path.resolve().is_relative_to(workspace):
                    stat = path.stat()
                    files.append({"relative_path": path.relative_to(workspace).as_posix(), "name": path.name,
                                  "extension": path.suffix.lower(), "size_bytes": stat.st_size, "modified_ns": stat.st_mtime_ns})
        designs = [d.model_dump(mode="json") for d in self.studio.design.list_designs()
                   if (d.product_id == str(product.product_id) or d.workspace_id in (str(product.product_id), str(revision.revision_id)))
                   and d.core_revision_id == str(revision.revision_id)]
        project_jobs = [j for j in self.simulations() if j["project_id"] == str(product.product_id)]
        return {"product": product.model_dump(mode="json"), "revision": revision.model_dump(mode="json"),
                "revisions": [r.model_dump(mode="json") for r in self.studio.list_revisions(product.product_id)],
                "input_hash": specification_hash(revision.specification), "lifecycle": lifecycle, "designs": designs,
                "calculations": self._records("calculation", revision.revision_id), "requirements": self._records("requirements", revision.revision_id),
                "registered_artifacts": self._records("artifact", revision.revision_id), "files": files,
                "simulations": [j for j in project_jobs if j["revision_id"] == str(revision.revision_id)],
                "unattributed_simulations": [j for j in project_jobs if j["revision_id"] is None],
                "availability_requests": [r.model_dump(mode="json") for r in self.studio.list_runs(revision.revision_id)],
                "validation": self.studio.engineering_records.validation_results(revision.revision_id),
                "pcb_checks": self.studio.pcb.list_checks(revision.revision_id),
                "reports": self.studio.engineering_records.list_reports(revision.revision_id),
                "measurements": [m.model_dump(mode="json") for m in self.studio.measurements.list_measurements(revision_id=revision.revision_id)],
                "timestamp": now().isoformat(), "limits": {"files": 1000, "records_per_kind": 500}}

    def components(self):
        library = self.studio.components
        return {"components": [c.model_dump(mode="json") for c in library.list_components()],
                "materials": [m.model_dump(mode="json") for m in library.list_materials()],
                "cores": [c.model_dump(mode="json") for c in library.list_cores()],
                "datasets": self.studio.integrations.list_datasets(),
                "provenance_note": "Seeded reference library. Manufacturer specifications, stock and source assertions are not independently verified."}

    def tools(self):
        rows = []
        for descriptor in self.studio.integrations.list_tools():
            health = self.studio.integrations.verify(descriptor.tool_id)
            config = self.studio.integrations.configuration(descriptor.tool_id)
            rows.append({
                "descriptor": descriptor.model_dump(mode="json"),
                "health": health.model_dump(mode="json"),
                "configured": bool(health.executable_path or config.executable_path or config.resource_path),
                "qualification": "NOT_EVALUATED",
            })
        return rows

    def reports(self):
        rows = []
        for product in self.studio.list_products():
            for revision in self.studio.list_revisions(product.product_id):
                for report in self.studio.engineering_records.list_reports(revision.revision_id):
                    rows.append({**report, "project_id": str(product.product_id), "project_name": product.name, "revision_label": revision.revision_label})
        return sorted(rows, key=lambda r: r["report"]["generated_at"], reverse=True)

    def waveform(self, request):
        """Existing ASCII parser; original samples only, with bounded windows and explicit units."""
        revision = self.studio.get_revision(request.revision_id)
        path = self.studio.engineering_records._confined(self.studio.workspace_path(revision), request.relative_path)
        if path.suffix.lower() != ".raw" or not path.is_file() or path.stat().st_size > 50 * 1024 * 1024:
            raise StudioError("UNSUPPORTED", "Choose an available ASCII .raw file up to 50 MiB")
        with path.open("rb") as handle:
            header = handle.read(65536)
        if b"Binary:" in header or b"\x00" in header:
            raise StudioError("UNSUPPORTED", "Binary/UTF-16 raw data is not supported by the existing parser; open it in the native viewer")
        text_header = header.decode("utf-8", errors="strict")
        if "Values:" not in text_header or "complex" in text_header.lower():
            raise StudioError("UNSUPPORTED", "Only existing real ASCII waveform samples are supported; no implicit conversion")
        from integrations.parsers.ltspice_parser import parse_ascii_raw_header, parse_ascii_raw_waveforms
        metadata = parse_ascii_raw_header(path)
        data = parse_ascii_raw_waveforms(path)
        declarations = {}
        in_variables = False
        for line in text_header.splitlines():
            if line.strip() == "Variables:":
                in_variables = True
            elif line.strip() == "Values:":
                break
            elif in_variables:
                parts = line.split()
                if len(parts) == 3:
                    declarations[parts[1]] = {"time": "s", "frequency": "Hz", "voltage": "V", "current": "A"}.get(parts[2].lower())
        domain = "time" if "time" in data else "frequency" if "frequency" in data else None
        if domain is None or declarations.get(domain) is None:
            raise StudioError("UNSUPPORTED", "Waveform domain/unit is not declared")
        count = len(data[domain])
        if count != metadata.get("no. points") or len(data) != metadata.get("no. variables") or any(len(v) != count for v in data.values()):
            raise StudioError("INVALID_INPUT", "Waveform samples disagree with declared shape")
        import numpy as np
        if not all(np.isfinite(v).all() for v in data.values()) or (count > 1 and not np.all(np.diff(data[domain]) > 0)):
            raise StudioError("UNSUPPORTED", "Nonfinite, stepped or non-monotonic data requires the native viewer")
        available = [name for name in data if name != domain]
        selected = request.traces or available[:4]
        if any(name not in available or not declarations.get(name) for name in selected):
            raise StudioError("UNSUPPORTED", "Requested trace/unit is unavailable; no units are guessed")
        end = min(count, request.start + request.limit)
        return {"revision_id": str(revision.revision_id), "relative_path": request.relative_path,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "domain": domain, "x_unit": declarations[domain],
                "x": data[domain][request.start:end].tolist(),
                "traces": [{"name": name, "unit": declarations[name], "y": data[name][request.start:end].tolist()} for name in selected],
                "available_traces": [{"name": name, "unit": declarations.get(name)} for name in available],
                "total_points": count, "start": request.start, "end": end, "metadata": metadata,
                "transformation": "NONE; contiguous original samples, no interpolation or downsampling", "engineering_status": "NOT_EVALUATED"}

    def dispatch(self, method, params):
        route = ROUTES.get(method)
        if route is None:
            raise StudioError("METHOD_NOT_ALLOWED", "Desktop method is not allowed")
        request = route.model_validate(params)
        if method in ("handshake", "shutdown"):
            return self.handshake()
        if method in ("overview", "projects", "simulations", "components", "tools", "reports"):
            return getattr(self, method)()
        if method == "project":
            return self.project(request)
        if method == "settings":
            return {**self.handshake(), "mcp_status": "NOT_EVALUATED", "cli_available": True,
                    "diagnostics": self.studio.diagnostics(), "approval_status": "UNAVAILABLE"}
        if method == "job":
            return self.studio.engineering_records.job_detail(request.job_id)
        if method == "job_logs":
            return self.studio.engineering_records.job_logs(request.job_id)
        if method == "waveform":
            return self.waveform(request)
        if method == "open_file":
            return {"opened": self.studio.open_project_file(request.revision_id, request.relative_path)}
        if method == "open_report":
            metadata = self.studio.engineering_records.report_metadata(request.report_id)
            if not metadata["available"] or metadata["integrity"] == "FAILED":
                raise StudioError("INVALID_INPUT", "Report is unavailable or modified")
            return {"opened": self.studio.open_report(request.report_id)}
        if method == "open_evidence":
            return {"opened": self.studio.open_evidence(request.record_id)}
        if method == "export_report":
            return self.studio.engineering_records.export_report({"report_id": request.report_id, "idempotency_key": request.idempotency_key,
                                                                  "source": "Studio Desktop", "reason": "User requested report export"})
        raise StudioError("METHOD_NOT_ALLOWED", "Desktop method is not implemented")


ROUTES = {name: models.Empty for name in ("handshake", "shutdown", "overview", "projects", "simulations", "components", "tools", "reports", "settings")}
ROUTES.update(project=models.ProjectQuery, job=models.JobQuery, job_logs=models.JobQuery, waveform=models.WaveformQuery,
              open_file=models.FileQuery, open_report=models.ReportQuery, open_evidence=models.EvidenceQuery, export_report=models.ExportReportQuery)
