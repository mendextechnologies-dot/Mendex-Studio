"""Desktop JSON-RPC dispatch, read views, and native file launch service."""
import json
from uuid import UUID, uuid4

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
        diag = self.studio.diagnostics()
        import platform
        py_ver = diag["environment"].get("python_version") or platform.python_version()
        return {
            "protocol_version": "3.1.0",
            "status": "READY" if diag["framework_ready"] else "DEGRADED",
            "data_root": str(self.studio.root),
            "python_version": py_ver,
            "application": "Mendex Engineering Studio",
            "desktop_version": "3.1.0",
            "engineering_status": "NOT_EVALUATED",
            "timestamp": now().isoformat(),
        }

    def overview(self):
        diag = self.studio.diagnostics()
        projs = self.projects()
        jobs = self.simulations()
        completed = sum(1 for j in jobs if j["status"] == "SUCCEEDED")
        failed = sum(1 for j in jobs if j["status"] == "FAILED")
        activity = []
        for p in projs[:5]:
            activity.append({
                "id": f"act-{p['product_id'][:8]}",
                "kind": "project",
                "title": f"Project active: {p['code']}",
                "detail": f"{p['name']} (Rev {p['revision_label']})",
                "timestamp": p["created_at"],
            })
        for j in jobs[:5]:
            activity.append({
                "id": f"act-{j['job_id'][:8]}",
                "kind": "simulation",
                "title": f"Simulation {j['status'].lower()}: {j['tool_id']}",
                "detail": f"Operation: {j['operation']}",
                "timestamp": j["created_at"],
            })
        activity.sort(key=lambda a: a["timestamp"], reverse=True)
        return {
            "projects": projs,
            "jobs": jobs,
            "activity": activity,
            "metrics": {
                "projects": len(projs),
                "revisions": len(projs),
                "completed_simulations": completed,
                "failed_simulations": failed,
                "review_requests": 0,
            },
            "timestamp": now().isoformat(),
        }

    def projects(self):
        rows = []
        for p in self.studio.list_products():
            revs = self.studio.list_revisions(p.product_id)
            active_rev = next((r for r in revs if r.revision_id == p.active_revision_id), revs[0] if revs else None)
            spec_hash = specification_hash(active_rev.specification) if active_rev else None
            rows.append({
                "product_id": str(p.product_id),
                "code": p.code,
                "name": p.name,
                "category": p.category,
                "owner": p.owner,
                "description": p.description,
                "active_revision_id": str(p.active_revision_id),
                "revision_label": active_rev.revision_label if active_rev else "R001",
                "revision_status": active_rev.lifecycle_status if active_rev else "draft",
                "input_hash": spec_hash,
                "created_at": p.created_at.isoformat(),
            })
        return rows

    def project(self, request):
        product = self.studio.get_product(request.project_id)
        revisions = self.studio.list_revisions(product.product_id)
        target_rev_id = request.revision_id or product.active_revision_id
        revision = next((r for r in revisions if r.revision_id == target_rev_id), None)
        if revision is None:
            raise StudioError("NOT_FOUND", "Revision not found for this product")

        # Lifecycle view
        lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
        current_hash = specification_hash(revision.specification)

        # Files in workspace
        ws_path = self.studio.workspace_path(revision)
        files = []
        if ws_path.exists():
            for p in sorted(ws_path.glob("**/*")):
                if p.is_file() and p.stat().st_size <= 50 * 1024 * 1024:
                    rel = p.relative_to(ws_path).as_posix()
                    files.append({
                        "relative_path": rel,
                        "name": p.name,
                        "extension": p.suffix,
                        "size_bytes": p.stat().st_size,
                        "modified_ns": p.stat().st_mtime_ns,
                    })

        # Records
        sims = self.studio.integrations.list_jobs()
        reports = self.studio.engineering_records.list_reports(revision.revision_id)

        return {
            "product": {
                "product_id": str(product.product_id),
                "code": product.code,
                "name": product.name,
                "category": product.category,
                "owner": product.owner,
                "description": product.description,
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat(),
                "active_revision_id": str(product.active_revision_id),
                "revision_status": revision.lifecycle_status,
            },
            "revision": {
                "revision_id": str(revision.revision_id),
                "product_id": str(product.product_id),
                "revision_label": revision.revision_label,
                "lifecycle_status": revision.lifecycle_status,
                "specification": revision.specification.model_dump(mode="json"),
                "created_at": revision.created_at.isoformat(),
            },
            "revisions": [
                {
                    "revision_id": str(r.revision_id),
                    "product_id": str(product.product_id),
                    "revision_label": r.revision_label,
                    "lifecycle_status": r.lifecycle_status,
                    "specification": r.specification.model_dump(mode="json"),
                    "created_at": r.created_at.isoformat(),
                }
                for r in revisions
            ],
            "input_hash": current_hash,
            "lifecycle": lifecycle,
            "designs": [],
            "calculations": self.studio.engineering_records.list_records("calculation", {"revision_id": str(revision.revision_id)}),
            "requirements": self.studio.engineering_records.list_records("requirements", {"revision_id": str(revision.revision_id)}),
            "registered_artifacts": self.studio.engineering_records.list_records("artifact", {"revision_id": str(revision.revision_id)}),
            "files": files,
            "simulations": [s.model_dump(mode="json") for s in sims],
            "unattributed_simulations": [u.model_dump(mode="json") for u in sims if not getattr(u, "product_id", None)],
            "availability_requests": [],
            "validation": self.studio.engineering_records.validation_results(revision.revision_id),
            "pcb_checks": [],
            "reports": reports,
            "measurements": [],
            "timestamp": now().isoformat(),
            "limits": {"files": 1000, "records_per_kind": 500},
        }

    def simulations(self):
        jobs = self.studio.integrations.list_jobs()
        return [j.model_dump(mode="json") for j in jobs]

    def components(self):
        lib = self.studio.components
        return {
            "categories": lib.categories,
            "components": [c.model_dump(mode="json") for c in lib.list_components()],
            "materials": [m.model_dump(mode="json") for m in lib.list_materials()],
            "cores": [cr.model_dump(mode="json") for cr in lib.list_cores()],
            "provenance_note": "Sourced reference catalog. Parts and product families are distinguished. Missing values are unknown; application qualification, stock and model compatibility remain NOT_EVALUATED.",
        }

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
        return {"samples": [], "traces": request.traces}

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
            return {
                **self.handshake(),
                "mcp_status": "NOT_EVALUATED",
                "cli_available": True,
                "diagnostics": self.studio.diagnostics(),
                "approval_status": "UNAVAILABLE",
            }
        if method == "job":
            return self.studio.engineering_records.job_detail(request.job_id)
        if method == "job_logs":
            return self.studio.engineering_records.job_logs(request.job_id)
        if method == "waveform":
            return self.waveform(request)
        if method == "open_file":
            return {"opened": self.studio.open_project_file(request.revision_id, request.relative_path)}
        if method == "reveal_file":
            return {"revealed": self.studio.reveal_project_file(request.revision_id, request.relative_path)}
        if method == "open_report":
            metadata = self.studio.engineering_records.report_metadata(request.report_id)
            if not metadata["available"] or metadata["integrity"] == "FAILED":
                raise StudioError("INVALID_INPUT", "Report is unavailable or modified")
            return {"opened": self.studio.open_report(request.report_id)}
        if method == "open_evidence":
            return {"opened": self.studio.open_evidence(request.record_id)}
        if method == "export_report":
            return self.studio.engineering_records.export_report({
                "report_id": request.report_id,
                "idempotency_key": request.idempotency_key,
                "source": "Studio Desktop",
                "reason": "User requested report export",
            })
        if method == "list_reviewers":
            return self.studio.reviews.list_reviewers()
        if method == "review_package":
            return self.studio.reviews.prepare_package(request.revision_id, request.stage_id)
        if method == "request_review":
            return self.studio.reviews.request_review(request.model_dump())
        if method == "submit_review":
            return self.studio.reviews.record_manual_decision(request.model_dump())
        if method == "generate_bom":
            from ..bom_generator import generate_bom_deliverables
            return generate_bom_deliverables(self.studio, request.revision_id)
        if method == "complete_stage":
            return self.studio.engineering_lifecycle.apply({
                "schema_version": "3.1.0",
                "revision_id": str(request.revision_id),
                "stage_id": request.stage_id,
                "action": "complete",
                "source": "Studio Desktop",
                "reason": "Engineer completed stage",
                "idempotency_key": str(uuid4()),
            })
        raise StudioError("METHOD_NOT_ALLOWED", "Desktop method is not implemented")


ROUTES = {
    name: models.Empty
    for name in ("handshake", "shutdown", "overview", "projects", "simulations", "components", "tools", "reports", "settings", "list_reviewers")
}
ROUTES.update(
    project=models.ProjectQuery,
    job=models.JobQuery,
    job_logs=models.JobQuery,
    waveform=models.WaveformQuery,
    open_file=models.FileQuery,
    reveal_file=models.FileQuery,
    generate_bom=models.BOMQuery,
    open_report=models.ReportQuery,
    open_evidence=models.EvidenceQuery,
    export_report=models.ExportReportQuery,
    review_package=models.ReviewPackageQuery,
    request_review=models.ReviewRequestQuery,
    submit_review=models.ReviewDecisionQuery,
    complete_stage=models.ReviewPackageQuery,
)
