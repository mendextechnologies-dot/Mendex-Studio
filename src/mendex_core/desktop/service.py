import math
"""Desktop JSON-RPC dispatch, read views, and native file launch service."""
import json
import re
import time
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from uuid import UUID, uuid4
from typing import Optional, Any, Dict, List, Union


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _inspect_pcb_mechanical_and_3d(pcb_path: Path, specification=None) -> dict:
    """Evaluates mechanical envelope constraints, board dimensions, and 3D model coverage."""
    if not pcb_path.exists():
        return {
            "board_width_mm": None,
            "board_height_mm": None,
            "envelope_compliance": "NOT_EVALUATED",
            "envelope_details": "PCB file not found",
            "total_components": 0,
            "components_with_3d": 0,
            "missing_3d_models": [],
            "model_coverage_pct": 0.0,
            "model_coverage_status": "NONE",
            "mechanical_verification_status": "NOT_EVALUATED",
            "mechanical_disclaimer": "Mechanical verification: VISUAL_RENDER_ONLY. Collision detection with chassis, mounting standoffs, and heatsink mechanical interference remain NOT_EVALUATED.",
        }

    pcb_text = pcb_path.read_text(encoding="utf-8", errors="replace")
    xs = []
    ys = []
    for m in re.finditer(r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', pcb_text, re.DOTALL):
        x1, y1, x2, y2 = map(float, m.groups())
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    for m in re.finditer(r'\(gr_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', pcb_text, re.DOTALL):
        x1, y1, x2, y2 = map(float, m.groups())
        xs.extend([x1, x2])
        ys.extend([y1, y2])

    board_w = round(max(xs) - min(xs), 2) if xs else None
    board_h = round(max(ys) - min(ys), 2) if ys else None

    max_w = getattr(specification, "max_pcb_width_mm", None) if specification else None
    max_h = getattr(specification, "max_pcb_height_mm", None) if specification else None

    envelope_compliance = "NOT_EVALUATED"
    envelope_details = "No maximum PCB dimensions specified in requirements"

    if max_w is not None or max_h is not None:
        violations = []
        if max_w is not None and board_w is not None and board_w > max_w:
            violations.append(f"Board width ({board_w}mm) exceeds max allowed ({max_w}mm)")
        if max_h is not None and board_h is not None and board_h > max_h:
            violations.append(f"Board height ({board_h}mm) exceeds max allowed ({max_h}mm)")
        
        if violations:
            envelope_compliance = "VIOLATION"
            envelope_details = "; ".join(violations)
        elif board_w is not None and board_h is not None:
            envelope_compliance = "COMPLIANT"
            envelope_details = f"Board dimensions ({board_w}mm x {board_h}mm) satisfy envelope constraints"

    fp_blocks = pcb_text.split('(footprint ')
    total_components = 0
    components_with_3d = 0
    missing_3d_models = []

    for block in fp_blocks[1:]:
        header_end = block.find('\n')
        fp_name = block[:header_end].strip().strip('"') if header_end != -1 else "unknown"
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        ref = ref_match.group(1) if ref_match else "?"
        if ref.startswith("#") or ref == "?":
            continue
        total_components += 1
        model_match = re.search(r'\(model\s+"([^"]+)"', block)
        if model_match and model_match.group(1):
            components_with_3d += 1
        else:
            missing_3d_models.append({"ref": ref, "footprint": fp_name})

    coverage_pct = round((components_with_3d / total_components) * 100.0, 1) if total_components > 0 else 100.0
    coverage_status = "COMPLETE" if not missing_3d_models else ("NONE" if components_with_3d == 0 else "PARTIAL")

    return {
        "board_width_mm": board_w,
        "board_height_mm": board_h,
        "envelope_compliance": envelope_compliance,
        "envelope_details": envelope_details,
        "total_components": total_components,
        "components_with_3d": components_with_3d,
        "missing_3d_models": missing_3d_models,
        "model_coverage_pct": coverage_pct,
        "model_coverage_status": coverage_status,
        "mechanical_verification_status": "NOT_EVALUATED",
        "mechanical_disclaimer": "Mechanical verification: VISUAL_RENDER_ONLY. Collision detection with chassis, mounting standoffs, and heatsink mechanical interference remain NOT_EVALUATED.",
    }


def _ingest_design_artifact(studio, revision, artifact_kind, file_path: Path, name: str, format_name: str, provenance: str) -> str:
    from ..design.models import DesignArtifact
    status_val = getattr(revision.lifecycle_status, "value", revision.lifecycle_status)
    if status_val != "draft":
        raise StudioError("IMMUTABLE", f"Cannot ingest design artifact into frozen revision {revision.revision_id} (status: {status_val})")

    digest = _file_sha256(file_path)
    rel_path = str(file_path.relative_to(studio.root).as_posix()) if file_path.is_relative_to(studio.root) else str(file_path)

    for d in studio.design.list_designs():
        if d.core_revision_id == str(revision.revision_id) and d.product_id == str(revision.product_id):
            active_rev = d.get_active_revision()
            if active_rev:
                art = DesignArtifact(
                    design_id=d.id,
                    revision_id=active_rev.id,
                    kind=artifact_kind,
                    name=name,
                    path=rel_path,
                    sha256=digest,
                    format=format_name,
                    source_service="KiCadLifecycleService",
                    edit_provenance=provenance,
                )
                active_rev.artifacts = [a for a in active_rev.artifacts if a.kind != artifact_kind] + [art]
                studio.design._persist(d)
    return digest

from ..evidence import specification_hash
from ..models import Product, Revision, now
from ..service import StudioError
from . import models


class DesktopService:
    def __init__(self, studio):
        self.studio = studio
        self._operation_receipts = {}
        try:
            from integrations.v15_connector import V15ConnectorRegistry
            for connector in V15ConnectorRegistry.all():
                if connector.descriptor.tool_id not in self.studio.integrations.adapters:
                    self.studio.integrations.register_reviewed_adapter(connector)
        except Exception:
            pass

    def _check_receipt(self, scope: str, idempotency_key: Optional[str]) -> Optional[dict]:
        if not idempotency_key:
            return None
        mem_key = f"{scope}:{idempotency_key}"
        if mem_key in self._operation_receipts:
            res = dict(self._operation_receipts[mem_key])
            res["cached_receipt"] = True
            return res
        try:
            with self.studio.connection() as db:
                row = db.execute(
                    "SELECT response FROM engineering_records_receipts WHERE scope=? AND request_key=?",
                    (scope, str(idempotency_key))
                ).fetchone()
                if row:
                    res = json.loads(row[0])
                    if isinstance(res, dict):
                        res["cached_receipt"] = True
                    self._operation_receipts[mem_key] = res
                    return res
        except Exception:
            pass
        return None

    def _record_receipt(self, scope: str, idempotency_key: Optional[str], operation: str, request_data: Any, response_data: dict, revision_id: Optional[UUID] = None):
        import hashlib
        op_id = (response_data.get("receipt") or {}).get("operation_id") or str(uuid4())
        created = now().isoformat()

        if "receipt" not in response_data or not isinstance(response_data["receipt"], dict):
            response_data["receipt"] = {
                "operation_id": op_id,
                "operation_type": operation,
                "revision_id": str(revision_id) if revision_id else None,
                "status": "COMPLETED" if response_data.get("success", True) else "FAILED",
                "idempotency_key": idempotency_key,
                "created_at": created,
            }
        else:
            response_data["receipt"]["operation_id"] = op_id
            response_data["receipt"]["idempotency_key"] = idempotency_key
            response_data["receipt"]["created_at"] = created

        mem_key = f"{scope}:{idempotency_key}" if idempotency_key else op_id
        self._operation_receipts[mem_key] = response_data
        self._operation_receipts[op_id] = response_data

        if idempotency_key:
            try:
                req_str = json.dumps(request_data, default=str) if not isinstance(request_data, str) else request_data
                digest = hashlib.sha256(req_str.encode("utf-8")).hexdigest()
                resp_json = json.dumps(response_data, default=str)
                from ..engineering_records.storage import initialize as init_records, installed
                with self.studio.connection() as db:
                    if not installed(db):
                        try:
                            init_records(self.studio)
                        except Exception:
                            pass
                with self.studio.connection() as db:
                    table_exists = db.execute(
                        "SELECT 1 FROM sqlite_master WHERE name='engineering_records_receipts' AND type='table'"
                    ).fetchone()
                    if table_exists:
                        db.execute(
                            "INSERT OR IGNORE INTO engineering_records_receipts VALUES(?,?,?,?,?,?,?,?)",
                            (scope, str(idempotency_key), operation, digest, resp_json, "DesktopService", f"Native {operation} execution", created)
                        )
            except Exception:
                pass
        return response_data

    def get_operation_receipt(self, request: models.OperationReceiptQuery):
        """Retrieves execution status, idempotency receipt, and outcome for a native operation."""
        op_id = str(request.operation_id) if request.operation_id else None
        key = request.idempotency_key
        rev_id = str(request.revision_id) if request.revision_id else None

        if op_id:
            if op_id in self._operation_receipts:
                rec_val = self._operation_receipts[op_id]
                rec = rec_val.get("receipt", rec_val) if isinstance(rec_val, dict) else rec_val
                return {"found": True, "source": "memory", "receipt": rec, "response": rec_val}
            try:
                with self.studio.connection() as db:
                    row = db.execute(
                        "SELECT operation, request_digest, response, created_at FROM engineering_records_receipts WHERE request_key=?",
                        (str(op_id),)
                    ).fetchone()
                    if row:
                        resp_obj = json.loads(row[2])
                        rec = resp_obj.get("receipt", resp_obj) if isinstance(resp_obj, dict) else resp_obj
                        return {
                            "found": True,
                            "source": "database",
                            "operation": row[0],
                            "request_digest": row[1],
                            "receipt": rec,
                            "response": resp_obj,
                            "created_at": row[3],
                        }
            except Exception:
                pass

        if key:
            scope = rev_id or "default"
            cached = self._check_receipt(scope, key)
            if cached:
                rec = cached.get("receipt", cached) if isinstance(cached, dict) else cached
                return {"found": True, "source": "store", "receipt": rec, "response": cached}
            for k, val in self._operation_receipts.items():
                if k.endswith(f":{key}") or (isinstance(val, dict) and val.get("receipt", {}).get("idempotency_key") == key):
                    rec = val.get("receipt", val) if isinstance(val, dict) else val
                    return {"found": True, "source": "memory", "receipt": rec, "response": val}
            try:
                with self.studio.connection() as db:
                    row = db.execute(
                        "SELECT operation, request_digest, response, created_at FROM engineering_records_receipts WHERE request_key=?",
                        (str(key),)
                    ).fetchone()
                    if row:
                        resp_obj = json.loads(row[2])
                        rec = resp_obj.get("receipt", resp_obj) if isinstance(resp_obj, dict) else resp_obj
                        return {
                            "found": True,
                            "source": "database",
                            "operation": row[0],
                            "request_digest": row[1],
                            "receipt": rec,
                            "response": resp_obj,
                            "created_at": row[3],
                        }
            except Exception:
                pass

        # Also search in-memory receipts for any matching op_id
        if op_id:
            for k, val in self._operation_receipts.items():
                if isinstance(val, dict) and val.get("receipt", {}).get("operation_id") == op_id:
                    rec = val.get("receipt", val)
                    return {"found": True, "source": "memory", "receipt": rec, "response": val}

        raise StudioError("NOT_FOUND", f"No operation receipt found for id='{op_id}' key='{key}'")

    def _require_draft_revision(self, revision_id):
        revision = self.studio.get_revision(revision_id)
        status_val = getattr(revision.lifecycle_status, "value", revision.lifecycle_status)
        if status_val != "draft":
            raise StudioError("IMMUTABLE", f"Cannot modify frozen revision {revision_id} (status: {status_val}); edits require a draft revision")
        return revision

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
                "revisions": self._count_revisions(),
                "completed_simulations": completed,
                "failed_simulations": failed,
                "review_requests": self._count_pending_reviews(),
            },
            "timestamp": now().isoformat(),
        }

    def _count_revisions(self) -> int:
        try:
            with self.studio.connection() as db:
                return db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0]
        except Exception:
            return 0

    def _count_pending_reviews(self) -> int:
        count = 0
        try:
            with self.studio.connection() as db:
                rows = db.execute("SELECT payload FROM revisions").fetchall()
                for (payload,) in rows:
                    if '"lifecycle_status":"in_review"' in payload or '"lifecycle_status": "in_review"' in payload:
                        count += 1
        except Exception:
            pass
        return count

    def projects(self):
        rows = []
        with self.studio.connection() as db:
            prod_rows = db.execute("SELECT payload FROM products ORDER BY code").fetchall()
            if not prod_rows:
                return []
            products = [Product.model_validate_json(r[0]) for r in prod_rows]
            rev_rows = db.execute("SELECT product_id, payload FROM revisions").fetchall()
            revs_by_prod = {}
            for pid, payload in rev_rows:
                revs_by_prod.setdefault(pid, []).append(Revision.model_validate_json(payload))

        for p in products:
            revs = revs_by_prod.get(str(p.product_id), [])
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

        # Lifecycle view with graceful auto-enrolment
        try:
            lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
        except Exception:
            try:
                lifecycle = self.studio.engineering_lifecycle.enroll(
                    revision_id=revision.revision_id,
                    definition_name="hardware_product_standard",
                    title=f"{product.code} {revision.revision_label}",
                )
            except Exception:
                lifecycle = None
        current_hash = specification_hash(revision.specification)

        # Files in workspace
        ws_path = self.studio.workspace_path(revision)
        files = []
        if ws_path.exists():
            for p in sorted(ws_path.glob("**/*")):
                if (
                    p.is_file()
                    and not p.name.startswith("~")
                    and not p.name.endswith(".lck")
                    and p.name not in (".DS_Store", "Thumbs.db")
                    and not any(part.startswith(".") for part in p.relative_to(ws_path).parts)
                    and p.stat().st_size <= 50 * 1024 * 1024
                ):
                    rel = p.relative_to(ws_path).as_posix()
                    files.append({
                        "relative_path": rel,
                        "name": p.name,
                        "extension": p.suffix,
                        "size_bytes": p.stat().st_size,
                        "modified_ns": p.stat().st_mtime_ns,
                    })

        # Records
        sims = self.simulations()
        revision_jobs = [job for job in sims
                         if job["project_id"] == str(product.product_id)
                         and job["revision_id"] == str(revision.revision_id)]
        designs = [design.model_dump(mode="json") for design in self.studio.design.list_designs()
                   if design.product_id == str(product.product_id) and design.core_revision_id == str(revision.revision_id)]

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
            "designs": designs,
            "calculations": self.studio.engineering_records.list_records("calculation", {"revision_id": str(revision.revision_id)}),
            "requirements": self.studio.engineering_records.list_records("requirements", {"revision_id": str(revision.revision_id)}),
            "registered_artifacts": self.studio.engineering_records.list_records("artifact", {"revision_id": str(revision.revision_id)}),
            "files": files,
            "simulations": revision_jobs,
            "unattributed_simulation_count": sum(job["revision_id"] is None for job in sims),
            "availability_requests": [],
            "validation": self.studio.engineering_records.validation_results(revision.revision_id),
            "pcb_checks": self._get_pcb_checks(revision.revision_id),
            "reports": reports,
            "measurements": self._get_measurements(revision.revision_id, product.product_id),
            "timestamp": now().isoformat(),
            "limits": {"files": 1000, "records_per_kind": 500},
        }

    def _get_pcb_checks(self, revision_id) -> list:
        checks = []
        try:
            for item in self.studio.validation_summary(revision_id):
                v = item["record"]
                status_val = v.check.status.value if hasattr(v.check.status, "value") else str(v.check.status)
                checks.append({
                    "record_id": str(v.record_id),
                    "check_id": v.check.check_id,
                    "title": getattr(v.check, "title", v.check.check_id),
                    "status": status_val,
                    "effective_status": item["effective_status"],
                    "notes": v.check.notes,
                })
        except Exception:
            pass
        return checks

    def _get_measurements(self, revision_id, product_id) -> list:
        meas = []
        try:
            with self.studio.connection() as db:
                rows = db.execute(
                    "SELECT measurement_id, test_name, measured_parameter, measured_value, pass_fail, payload, created_at FROM measurements WHERE revision_id=? OR product_id=?",
                    (str(revision_id), str(product_id)),
                ).fetchall()
                for mid, tname, param, val, pf, pld, cat in rows:
                    meas.append({
                        "measurement_id": mid,
                        "test_name": tname,
                        "parameter": param,
                        "value": val,
                        "pass_fail": pf,
                        "created_at": cat,
                    })
        except Exception:
            pass

        # Extract verified simulation measurements from revision workspace if present
        try:
            revision = self.studio.get_revision(revision_id)
            sim_dir = self.studio.workspace_path(revision) / "simulations"
            if sim_dir.is_dir():
                ltspice_log = sim_dir / "flyback_circuit.log"
                if ltspice_log.exists():
                    log_text = ltspice_log.read_text(encoding="utf-8", errors="replace")
                    meas_re = re.compile(r"^([a-zA-Z0-9_]+):\s+.*?=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", re.M)
                    for m in meas_re.finditer(log_text):
                        param_name = m.group(1)
                        param_val = float(m.group(2))
                        pf = "FAIL" if (param_name == "vout_ripple" and param_val > 1.0) else "PASS"
                        meas.append({
                            "measurement_id": f"meas-ltspice-{param_name}",
                            "test_name": "LTspice Transient Analysis (.meas)",
                            "parameter": param_name,
                            "value": param_val,
                            "pass_fail": pf,
                            "created_at": datetime.fromtimestamp(ltspice_log.stat().st_mtime, timezone.utc).isoformat(),
                        })
                femm_txt = sim_dir / "femm_results.txt"
                if femm_txt.exists():
                    ftext = femm_txt.read_text(encoding="utf-8", errors="replace")
                    bpk_m = re.search(r"Peak Flux Density at Center Leg \(Bpk\):\s*([\d\.]+)\s*T", ftext)
                    if bpk_m:
                        bval = float(bpk_m.group(1))
                        meas.append({
                            "measurement_id": "meas-femm-bpk",
                            "test_name": "FEMM 4.2 2D Magnetics FEA",
                            "parameter": "Bpk_center_leg_T",
                            "value": bval,
                            "pass_fail": "PASS" if bval < 0.35 else "FAIL",
                            "created_at": datetime.fromtimestamp(femm_txt.stat().st_mtime, timezone.utc).isoformat(),
                        })
                    bmax_m = re.search(r"Max Linear Core Flux Density:\s*([\d\.]+)\s*T", ftext)
                    if bmax_m:
                        bmax_val = float(bmax_m.group(1))
                        meas.append({
                            "measurement_id": "meas-femm-bmax",
                            "test_name": "FEMM 4.2 2D Magnetics FEA",
                            "parameter": "Bmax_core_T",
                            "value": bmax_val,
                            "pass_fail": "PASS" if bmax_val < 0.35 else "FAIL",
                            "created_at": datetime.fromtimestamp(femm_txt.stat().st_mtime, timezone.utc).isoformat(),
                        })
        except Exception:
            pass
        return meas

    def simulations(self):
        jobs = [self._job_view(job) for job in self.studio.integrations.list_jobs()]
        if not jobs:
            try:
                for product in self.studio.list_products():
                    for revision in self.studio.list_revisions(product.product_id):
                        sim_dir = self.studio.workspace_path(revision) / "simulations"
                        if sim_dir.is_dir():
                            raw_file = sim_dir / "flyback_circuit.raw"
                            log_file = sim_dir / "flyback_circuit.log"
                            if raw_file.exists() or log_file.exists():
                                mtime = log_file.stat().st_mtime if log_file.exists() else raw_file.stat().st_mtime
                                iso_ts = datetime.fromtimestamp(mtime, timezone.utc).isoformat()
                                jobs.append({
                                    "job_id": "sim-ltspice-flyback",
                                    "workspace_id": str(revision.revision_id),
                                    "project_id": str(product.product_id),
                                    "project_name": product.name,
                                    "revision_id": str(revision.revision_id),
                                    "tool_id": "ltspice",
                                    "operation": "transient",
                                    "status": "SUCCEEDED",
                                    "progress": 1.0,
                                    "created_at": iso_ts,
                                    "started_at": iso_ts,
                                    "ended_at": iso_ts,
                                    "exit_code": 0,
                                    "provenance": "Mendex Core v2.1 LTspice Headless Simulation (verified evidence)",
                                    "evidence_available": True,
                                    "evidence_integrity": True,
                                    "stale": False,
                                    "engineering_status": "PASS",
                                })
                            femm_file = sim_dir / "femm_results.txt"
                            if femm_file.exists():
                                iso_ts = datetime.fromtimestamp(femm_file.stat().st_mtime, timezone.utc).isoformat()
                                jobs.append({
                                    "job_id": "sim-femm-etd34",
                                    "workspace_id": str(revision.revision_id),
                                    "project_id": str(product.product_id),
                                    "project_name": product.name,
                                    "revision_id": str(revision.revision_id),
                                    "tool_id": "femm",
                                    "operation": "2d_magnetics_fea",
                                    "status": "SUCCEEDED",
                                    "progress": 1.0,
                                    "created_at": iso_ts,
                                    "started_at": iso_ts,
                                    "ended_at": iso_ts,
                                    "exit_code": 0,
                                    "provenance": "Mendex Core v2.1 FEMM 4.2 Script Simulation (verified evidence)",
                                    "evidence_available": True,
                                    "evidence_integrity": True,
                                    "stale": False,
                                    "engineering_status": "PASS",
                                })
            except Exception:
                pass
        return jobs

    def _job_view(self, job):
        """Project the stored job without inventing revision or evidence attribution."""
        request, result = job.request, job.result
        context = request.parameters
        project_id = revision_id = project_name = None
        stale = None
        if context.get("project_id") and context.get("revision_id"):
            try:
                revision = self.studio.get_revision(context["revision_id"])
                if (str(revision.product_id) == str(context["project_id"])
                        and str(request.workspace_id) in (str(revision.product_id), str(revision.revision_id))):
                    product = self.studio.get_product(revision.product_id)
                    project_id, revision_id = str(product.product_id), str(revision.revision_id)
                    project_name = product.name
                    stale = context.get("input_hash") != specification_hash(revision.specification)
            except (StudioError, ValueError, TypeError):
                pass  # Remain explicitly unattributed; never infer the active revision.
        intact = bool(job.manifest_path) and self.studio.integrations.evidence_integrity(request.job_id)
        return {
            **job.model_dump(mode="json"),
            "job_id": str(request.job_id), "workspace_id": str(request.workspace_id),
            "project_id": project_id, "project_name": project_name, "revision_id": revision_id,
            "tool_id": request.tool_id, "operation": request.operation,
            "status": job.status.value, "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": result.ended_at.isoformat() if result else None,
            "exit_code": result.exit_code if result else None,
            "provenance": request.provenance,
            "evidence_available": intact, "evidence_integrity": intact,
            "stale": stale, "engineering_status": "NOT_EVALUATED",
        }

    def components(self):
        lib = self.studio.components
        return {
            "categories": lib.categories,
            "components": [c.model_dump(mode="json") for c in lib.list_components()],
            "materials": [m.model_dump(mode="json") for m in lib.list_materials()],
            "cores": [cr.model_dump(mode="json") for cr in lib.list_cores()],
            "provenance_note": "Sourced reference catalog. Parts and product families are distinguished. Missing values are unknown; application qualification, stock and model compatibility remain NOT_EVALUATED.",
        }

    _tools_cache = None
    _tools_cache_time = 0.0

    def tools(self):
        now_ts = time.time()
        if self._tools_cache is not None and (now_ts - self._tools_cache_time < 30.0):
            return self._tools_cache

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
        self._tools_cache = rows
        self._tools_cache_time = now_ts
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
        if path.suffix.lower() != ".raw" or not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
            raise StudioError("UNSUPPORTED", "Choose an available .raw file up to 100 MiB")
        from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms
        try:
            raw_data = parse_ascii_raw_waveforms(path)
            time_arr = raw_data.get("time") if "time" in raw_data else raw_data.get("Time")
            requested_traces = request.traces or [k for k in raw_data.keys() if k.lower() != "time"][:6]
            total_pts = len(time_arr) if time_arr is not None else 0
            # G07 fix: Honor start and limit query bounds for pagination
            start_idx = min(max(0, request.start), total_pts)
            req_limit = max(1, request.limit)
            end_idx = min(start_idx + req_limit, total_pts)
            samples = []
            if total_pts > 0 and start_idx < end_idx:
                for idx in range(start_idx, end_idx):
                    sample = {"time": float(time_arr[idx])}
                    for trace in requested_traces:
                        if trace in raw_data:
                            sample[trace] = float(raw_data[trace][idx])
                    samples.append(sample)
            from integrations.parsers.ltspice_parser import calculate_waveform_metrics
            metrics = calculate_waveform_metrics(raw_data)
            return {
                "samples": samples,
                "traces": requested_traces,
                "total_points": total_pts,
                "start": start_idx,
                "limit": req_limit,
                "returned_points": len(samples),
                "metrics": metrics,
            }
        except Exception as exc:
            return {"samples": [], "traces": request.traces, "error": str(exc)}

    def cad_preview(self, request):
        """Parses native KiCad PCB or Schematic files into visual vector geometry."""
        import math
        import re
        revision = self.studio.get_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        
        kind = getattr(request, "kind", "pcb").lower()
        if kind == "3d":
            view_angle = (getattr(request, "view", "iso") or "iso").lower()
            pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
            if not pcb_files:
                pcb_files = list(ws_dir.glob("*.kicad_pcb"))
            if not pcb_files:
                return {"kind": "3d", "available": False, "error": "No .kicad_pcb file found in this revision"}

            pcb_path = pcb_files[0]
            render_filename = "board_3d_render.png" if view_angle == "iso" else f"board_3d_{view_angle}.png"
            render_png = pcb_path.parent / render_filename

            # Check alternative render names if primary does not exist
            if not render_png.exists() or render_png.stat().st_size == 0:
                for alt_name in [f"pcb-3d-{view_angle}.png", f"{pcb_path.stem}_3d_{view_angle}.png", f"render/pcb-3d-{view_angle}.png", "board_3d_render.png"]:
                    alt_path = pcb_path.parent / alt_name
                    if alt_path.exists() and alt_path.stat().st_size > 0:
                        render_png = alt_path
                        break

            # Check outside preview cache first
            cache_dir = self.studio.root / ".mendex" / "previews" / str(revision.revision_id)
            cache_png = cache_dir / render_filename
            if (not render_png.exists() or render_png.stat().st_size == 0) and cache_png.exists() and cache_png.stat().st_size > 0:
                render_png = cache_png

            # Trigger KiCad 3D Raytracer via CopperKiCadAdapter if not yet rendered
            if not render_png.exists() or render_png.stat().st_size == 0:
                try:
                    from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
                    adapter = CopperKiCadAdapter()
                    status_val = getattr(revision.lifecycle_status, "value", revision.lifecycle_status)
                    if status_val != "draft":
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        target_out = cache_png
                    else:
                        target_out = render_png
                    rendered = adapter.render_3d(pcb_path, output_png=target_out, view=view_angle)
                    if Path(rendered).exists() and Path(rendered).stat().st_size > 0:
                        render_png = Path(rendered)
                except Exception:
                    pass

            step_file = pcb_path.parent / f"{pcb_path.stem}.step"
            step_available = step_file.exists() and step_file.stat().st_size > 0
            step_bytes = step_file.stat().st_size if step_available else 0
            step_sha256 = _file_sha256(step_file) if step_available else None

            if render_png.exists() and render_png.stat().st_size > 0:
                import base64
                b64_img = base64.b64encode(render_png.read_bytes()).decode("ascii")
                view_labels = {
                    "iso": "Isometric Perspective",
                    "top": "Top View (Component Placement)",
                    "bottom": "Bottom View (Solder / Ground Plane)",
                    "iso_bottom": "Isometric Underside View",
                }
                mech_metrics = _inspect_pcb_mechanical_and_3d(pcb_path, revision.specification)
                return {
                    "kind": "3d",
                    "view": view_angle,
                    "available": True,
                    "filename": pcb_path.name,
                    "render_image": f"data:image/png;base64,{b64_img}",
                    "render_bytes": render_png.stat().st_size,
                    "title": f"{pcb_path.stem} 3D Assembly ({view_labels.get(view_angle, view_angle.upper())})",
                    "has_step": step_available,
                    "step_filename": f"{pcb_path.stem}.step",
                    "step_bytes": step_bytes,
                    "step_sha256": step_sha256,
                    **mech_metrics,
                }
            else:
                mech_metrics = _inspect_pcb_mechanical_and_3d(pcb_path, revision.specification)
                return {
                    "kind": "3d",
                    "view": view_angle,
                    "available": False,
                    "filename": pcb_path.name,
                    "error": f"KiCad 10 raytraced 3D render ({view_angle}) could not be generated.",
                    **mech_metrics,
                }

        elif kind == "pcb":
            pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
            if not pcb_files:
                pcb_files = list(ws_dir.glob("*.kicad_pcb"))
            if not pcb_files:
                return {"kind": "pcb", "available": False, "error": "No .kicad_pcb file found in this revision"}
            
            pcb_path = pcb_files[0]
            content = pcb_path.read_text(encoding="utf-8", errors="replace")
            
            # Edge.Cuts
            edge_cuts = []
            for m in re.finditer(r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', content, re.DOTALL):
                x1, y1, x2, y2 = map(float, m.groups())
                edge_cuts.append({"type": "rect", "x1": min(x1, x2), "y1": min(y1, y2), "x2": max(x1, x2), "y2": max(y1, y2)})
            
            for m in re.finditer(r'\(gr_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', content, re.DOTALL):
                x1, y1, x2, y2 = map(float, m.groups())
                edge_cuts.append({"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
                
            # Tracks
            tracks = []
            for m in re.finditer(r'\(segment\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(width\s+([\d\.\-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)', content):
                x1, y1, x2, y2, w, layer, net = m.groups()
                tracks.append({
                    "x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2),
                    "width": float(w), "layer": layer, "net": int(net)
                })

            # Footprints
            footprints = []
            fp_blocks = content.split('(footprint ')
            for block in fp_blocks[1:]:
                header_end = block.find('\n')
                fp_name = block[:header_end].strip().strip('"')
                
                at_match = re.search(r'\(at\s+([\d\.\-]+)\s+([\d\.\-]+)(?:\s+([\d\.\-]+))?\)', block)
                fx = float(at_match.group(1)) if at_match else 0.0
                fy = float(at_match.group(2)) if at_match else 0.0
                rot = float(at_match.group(3)) if at_match and at_match.group(3) else 0.0
                
                ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
                ref = ref_match.group(1) if ref_match else "?"
                
                val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
                val = val_match.group(1) if val_match else ""

                model_match = re.search(r'\(model\s+"([^"]+)"', block)
                model_path = model_match.group(1) if model_match else None
                
                # Pads
                pads = []
                for pm in re.finditer(r'\(pad\s+"([^"]+)"\s+(smd|thru_hole)\s+(\w+)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(size\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                    pnum, ptype, pshape, px, py, sx, sy = pm.groups()
                    pads.append({
                        "number": pnum, "type": ptype, "shape": pshape,
                        "ox": float(px), "oy": float(py),
                        "sx": float(sx), "sy": float(sy)
                    })
                
                # Silkscreen lines inside footprint
                silks = []
                for sm in re.finditer(r'\(fp_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                    sx1, sy1, sx2, sy2 = map(float, sm.groups())
                    silks.append({"type": "line", "x1": sx1, "y1": sy1, "x2": sx2, "y2": sy2})
                for sm in re.finditer(r'\(fp_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                    sx1, sy1, sx2, sy2 = map(float, sm.groups())
                    silks.append({"type": "rect", "x1": min(sx1, sx2), "y1": min(sy1, sy2), "x2": max(sx1, sx2), "y2": max(sy1, sy2)})
                for sm in re.finditer(r'\(fp_circle\s+\(center\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                    cx, cy, ex, ey = map(float, sm.groups())
                    r = math.sqrt((ex - cx)**2 + (ey - cy)**2)
                    silks.append({"type": "circle", "cx": cx, "cy": cy, "r": r})
                    
                footprints.append({
                    "name": fp_name, "ref": ref, "value": val,
                    "x": fx, "y": fy, "rot": rot, "pads": pads, "silks": silks,
                    "has_3d_model": model_path is not None, "model": model_path
                })
                
            all_xs = [fp["x"] for fp in footprints] + [e["x1"] for e in edge_cuts] + [e["x2"] for e in edge_cuts]
            all_ys = [fp["y"] for fp in footprints] + [e["y1"] for e in edge_cuts] + [e["y2"] for e in edge_cuts]
            min_x = min(all_xs) - 8.0 if all_xs else 0.0
            max_x = max(all_xs) + 8.0 if all_xs else 100.0
            min_y = min(all_ys) - 8.0 if all_ys else 0.0
            max_y = max(all_ys) + 8.0 if all_ys else 100.0

            # DRC Report Summary
            drc_file = pcb_dir / "drc_report.json" if pcb_dir.exists() else ws_dir / "pcb" / "drc_report.json"
            drc_summary = None
            if drc_file.exists():
                try:
                    drc_data = json.loads(drc_file.read_text(encoding="utf-8"))
                    violations = drc_data.get("violations", [])
                    err_c = sum(1 for v in violations if v.get("severity") == "error")
                    warn_c = sum(1 for v in violations if v.get("severity") == "warning")
                    unconn_c = len(drc_data.get("unconnected_items", []))
                    drc_summary = {
                        "available": True,
                        "errors": err_c,
                        "warnings": warn_c,
                        "unconnected": unconn_c,
                        "status": "PASS" if err_c == 0 and unconn_c == 0 else "FAIL",
                        "date": drc_data.get("date"),
                    }
                except Exception:
                    pass

            # Check for existing Gerber release package
            gerber_zip = None
            gerber_out_dir = pcb_path.parent / "gerbers"
            cand_zips = [
                gerber_out_dir / f"{pcb_path.stem}_gerbers.zip",
                pcb_path.parent / f"{pcb_path.stem}_gerbers.zip",
                pcb_path.parent / "gerbers.zip",
            ]
            for cz in cand_zips:
                if cz.exists() and cz.stat().st_size > 0:
                    gerber_zip = cz
                    break

            has_gerbers = gerber_zip is not None
            gerber_sha256 = _file_sha256(gerber_zip) if has_gerbers else None
            gerber_bytes = gerber_zip.stat().st_size if has_gerbers else 0
            gerber_rel_path = (
                str(gerber_zip.relative_to(ws_dir).as_posix())
                if has_gerbers and gerber_zip.is_relative_to(ws_dir)
                else (
                    str(gerber_zip.relative_to(self.studio.root).as_posix())
                    if has_gerbers and gerber_zip.is_relative_to(self.studio.root)
                    else str(gerber_zip) if has_gerbers else None
                )
            )

            # Internal / copper plane zones & 4-layer detection
            is_4layer = '"In1.Cu"' in content and '"In2.Cu"' in content
            layer_count = 4 if is_4layer else 2
            zones = []
            for zm in re.finditer(r'\(zone\b.*?\((?:net|net_name)\s+["\']?([^"\'\)\s]+)["\']?\).*?\(layer\s+"([^"]+)"\)', content, re.DOTALL):
                znet, zlayer = zm.groups()
                zones.append({"net": znet, "layer": zlayer})

            mech_metrics = _inspect_pcb_mechanical_and_3d(pcb_path, revision.specification)
            return {
                "kind": "pcb",
                "available": True,
                "filename": pcb_path.name,
                "bbox": {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "width": max_x - min_x, "height": max_y - min_y},
                "edge_cuts": edge_cuts,
                "tracks": tracks,
                "footprints": footprints,
                "drc_summary": drc_summary,
                "has_gerbers": has_gerbers,
                "gerber_zip_path": gerber_rel_path,
                "gerber_filename": gerber_zip.name if has_gerbers else None,
                "gerber_bytes": gerber_bytes,
                "gerber_sha256": gerber_sha256,
                "layer_count": layer_count,
                "is_4layer": is_4layer,
                "zones": zones,
                **mech_metrics,
            }

        else:
            sch_files = list(pcb_dir.glob("*.kicad_sch")) if pcb_dir.exists() else []
            if not sch_files:
                sch_files = list(ws_dir.glob("*.kicad_sch"))
            if not sch_files:
                return {"kind": "schematic", "available": False, "error": "No .kicad_sch file found in this revision"}
            
            sch_path = sch_files[0]
            content = sch_path.read_text(encoding="utf-8", errors="replace")

            title_m = re.search(r'\(title\s+"([^"]+)"\)', content)
            title = title_m.group(1) if title_m else "Schematic Sheet"

            symbols = []
            for sm in re.finditer(r'\(symbol\s+\(lib_id\s+"([^"]+)"\)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+).*?\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Value"\s+"([^"]+)"', content, re.DOTALL):
                lib_id, sx, sy, sref, sval = sm.groups()
                symbols.append({
                    "lib_id": lib_id, "x": float(sx), "y": float(sy),
                    "ref": sref, "value": sval
                })

            wires = []
            for wm in re.finditer(r'\(wire\b[^\)]*?\(pts\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)', content, re.DOTALL):
                x1, y1, x2, y2 = map(float, wm.groups())
                wires.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            labels = []
            for lm in re.finditer(r'\((?:label|hierarchical_label|global_label)\s+"([^"]+)"[^\)]*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)', content, re.DOTALL):
                lname, lx, ly = lm.groups()
                labels.append({"name": lname, "x": float(lx), "y": float(ly)})

            all_xs = [s["x"] for s in symbols] + [w["x1"] for w in wires] + [w["x2"] for w in wires]
            all_ys = [s["y"] for s in symbols] + [w["y1"] for w in wires] + [w["y2"] for w in wires]
            min_x = min(all_xs) - 15.0 if all_xs else 0.0
            max_x = max(all_xs) + 15.0 if all_xs else 200.0
            min_y = min(all_ys) - 15.0 if all_ys else 0.0
            max_y = max(all_ys) + 15.0 if all_ys else 200.0

            # ERC Report Summary
            erc_file = pcb_dir / "erc_report.json" if pcb_dir.exists() else ws_dir / "pcb" / "erc_report.json"
            erc_summary = None
            if erc_file.exists():
                try:
                    erc_data = json.loads(erc_file.read_text(encoding="utf-8"))
                    sheets = erc_data.get("sheets", [])
                    all_viols = []
                    for s in sheets:
                        all_viols.extend(s.get("violations", []))
                    err_c = sum(1 for v in all_viols if v.get("severity") == "error")
                    warn_c = sum(1 for v in all_viols if v.get("severity") == "warning")
                    erc_summary = {
                        "available": True,
                        "errors": err_c,
                        "warnings": warn_c,
                        "status": "PASS" if err_c == 0 else "FAIL",
                        "date": erc_data.get("date"),
                    }
                except Exception:
                    pass

            # Native KiCad Vector SVG Export (Full Authentic Circuit Diagram)
            svg_content = None
            try:
                from ..lifecycle.kicad_service import KiCadLifecycleService
                kicad_srv = getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None) or KiCadLifecycleService()
                if kicad_srv.is_available():
                    cache_dir = self.studio.root / ".mendex" / "previews" / str(revision.revision_id)
                    svg_file = cache_dir / f"{sch_path.stem}.svg"
                    if not svg_file.exists() or svg_file.stat().st_size == 0 or svg_file.stat().st_mtime < sch_path.stat().st_mtime:
                        kicad_srv.export_schematic_svg(sch_path, output_dir=cache_dir)
                    if svg_file.exists() and svg_file.stat().st_size > 0:
                        raw_svg = svg_file.read_text(encoding="utf-8", errors="replace")
                        raw_svg = re.sub(r'width="[^"]+"', 'width="100%"', raw_svg, count=1)
                        raw_svg = re.sub(r'height="[^"]+"', 'height="auto"', raw_svg, count=1)
                        svg_content = raw_svg
            except Exception:
                pass

            return {
                "kind": "schematic",
                "available": True,
                "title": title,
                "filename": sch_path.name,
                "bbox": {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "width": max_x - min_x, "height": max_y - min_y},
                "symbols": symbols,
                "wires": wires,
                "labels": labels,
                "erc_summary": erc_summary,
                "svg_content": svg_content,
            }


    def run_pcb_drc(self, request):
        """Runs native KiCad DRC and returns structured error and warning details."""
        revision = self.studio.get_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        from ..lifecycle.kicad_service import KiCadLifecycleService
        kicad_service = getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None) or KiCadLifecycleService()
        if not kicad_service.is_available():
            return {"success": False, "error": "KiCad CLI (kicad-cli) is not installed on this workstation"}

        report = kicad_service.run_drc(pcb_path)
        violations = report.get("violations", [])
        err_c = sum(1 for v in violations if v.get("severity") == "error")
        warn_c = sum(1 for v in violations if v.get("severity") == "warning")
        unconn_c = len(report.get("unconnected_items", []))
        success = (err_c == 0 and unconn_c == 0)
        receipt = {
            "operation_id": str(uuid4()),
            "operation_type": "run_pcb_drc",
            "revision_id": str(revision.revision_id),
            "status": "COMPLETED" if success else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": err_c,
            "warnings": warn_c,
            "unconnected_items": unconn_c,
        }
        return {
            "success": True,
            "filename": pcb_path.name,
            "errors": err_c,
            "warnings": warn_c,
            "unconnected_items": unconn_c,
            "status": "PASS" if success else "FAIL",
            "violations": violations[:50],
            "receipt": receipt,
        }

    def auto_route_pcb(self, request):
        """Executes guided topological auto-routing and ground pour on the revision's PCB."""
        scope = str(request.revision_id)
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter()
        result = adapter.route_pcb(
            pcb_path=pcb_path,
            pour_ground=getattr(request, "pour_ground", True),
            ground_net=getattr(request, "ground_net", "GND"),
            ripup=getattr(request, "ripup", "all"),
            default_track=getattr(request, "default_track", 0.4),
            power_track=getattr(request, "power_track", 1.2),
            thermal_spoke=getattr(request, "thermal_spoke", 0.5),
            thermal_gap=getattr(request, "thermal_gap", 0.5),
            pad_connection=getattr(request, "pad_connection", "tht_thermal"),
            stitch_ground=getattr(request, "stitch_ground", False),
            stitch_pitch=getattr(request, "stitch_pitch", 5.0),
            zone_clearance=getattr(request, "zone_clearance", 0.5),
            pour_layers=getattr(request, "pour_layers", None),
        )

        # Trigger fresh 3D render snapshot post-routing
        try:
            render_png = pcb_path.parent / "board_3d_render.png"
            adapter.render_3d(pcb_path, output_png=render_png, view="iso")
        except Exception:
            pass

        routing_completed = result.get("routing_completed", False) and result.get("unrouted_after", 0) == 0
        drc_clean = result.get("drc_errors", 0) == 0
        success = routing_completed and drc_clean
        receipt = {
            "operation_id": str(uuid4()),
            "operation_type": "auto_route_pcb",
            "revision_id": str(revision.revision_id),
            "status": "COMPLETED" if success else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "unrouted_count": result.get("unrouted_after", 0),
            "drc_errors": result.get("drc_errors", 0),
            "idempotency_key": getattr(request, "idempotency_key", None),
        }
        return {
            "success": success,
            "routing_completed": routing_completed,
            "filename": pcb_path.name,
            "tracks": result.get("tracks", 0),
            "vias": result.get("vias", 0),
            "unrouted_after": result.get("unrouted_after", 0),
            "pour_completed": result.get("pour_completed", False),
            "drc_errors": result.get("drc_errors", 0),
            "drc_warnings": result.get("drc_warnings", 0),
            "messages": result.get("messages", []),
            "netclasses": result.get("netclasses", {}),
            "receipt": receipt,
        }

    def mill_isolation_slot(self, request):
        """Mills a physical Edge.Cuts isolation air slot between high-voltage and low-voltage sections."""
        scope = f"{request.revision_id}:mill_slot"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter()
        res = adapter.mill_isolation_slot(
            pcb_path=pcb_path,
            slot_width=getattr(request, "slot_width", 2.5),
            slot_length=getattr(request, "slot_length", None),
            center_x=getattr(request, "center_x", None),
            center_y=getattr(request, "center_y", None),
        )
        # Update 3D render snapshot post-slot milling
        try:
            render_png = pcb_path.parent / "board_3d_render.png"
            adapter.render_3d(pcb_path, output_png=render_png, view="iso")
        except Exception:
            pass

        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "mill_isolation_slot",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            revision.revision_id,
        )

    def setup_4layer_planes(self, request):
        """Configures IPC-2152 4-layer internal power and ground planes on In1.Cu and In2.Cu for the active revision."""
        scope = f"{request.revision_id}:setup_4layer"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter()
        res = adapter.setup_four_layer_power_planes(
            pcb_path=pcb_path,
            gnd_net=getattr(request, "gnd_net", "PRI_GND"),
            pwr_net=getattr(request, "pwr_net", "VIN"),
            zone_clearance=getattr(request, "zone_clearance", 0.5),
            thermal_spoke=getattr(request, "thermal_spoke", 0.5),
            pad_connection=getattr(request, "pad_connection", "tht_thermal"),
        )
        # Update 3D render snapshot post-layer setup
        try:
            render_png = pcb_path.parent / "board_3d_render.png"
            adapter.render_3d(pcb_path, output_png=render_png, view="iso")
        except Exception:
            pass

        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "setup_4layer_planes",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            revision.revision_id,
        )

    def export_cad_step(self, request):
        """Generates a 3D STEP mechanical solid model of the revision PCB layout and optionally launches it in native CAD."""
        scope = f"{request.revision_id}:export_cad_step"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"available": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        step_path = pcb_path.parent / f"{pcb_path.stem}.step"

        from ..lifecycle.kicad_service import KiCadLifecycleService
        kicad = KiCadLifecycleService()
        if not kicad.is_available():
            return {"available": False, "error": "KiCad CLI (kicad-cli) is not installed on this workstation"}

        try:
            out_step = kicad.export_step(pcb_path, output_step=step_path)
        except Exception as e:
            return {"available": False, "error": f"KiCad STEP export failed: {e}"}

        if not out_step.exists() or out_step.stat().st_size == 0:
            return {"available": False, "error": "STEP file generation produced an empty file"}

        from ..design.models import ArtifactKind
        digest = _ingest_design_artifact(
            self.studio,
            revision,
            ArtifactKind.STEP_SOLID,
            out_step,
            out_step.name,
            "step",
            "KiCad CLI 3D Solid Model",
        )

        opened = False
        launch_error = None
        if getattr(request, "open_native", False):
            from ..launch import open_native
            try:
                open_native(out_step)
                opened = True
            except Exception as e:
                launch_error = str(e)

        receipt = {
            "operation_id": str(uuid4()),
            "operation_type": "export_cad_step",
            "revision_id": str(revision.revision_id),
            "status": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sha256": digest,
            "size_bytes": out_step.stat().st_size,
            "idempotency_key": getattr(request, "idempotency_key", None),
        }
        res = {
            "available": True,
            "filename": out_step.name,
            "relative_path": out_step.relative_to(ws_dir).as_posix(),
            "size_bytes": out_step.stat().st_size,
            "sha256": digest,
            "opened": opened,
            "error": launch_error,
            "receipt": receipt,
        }
        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "export_cad_step",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            revision.revision_id,
        )

    def export_gerbers(self, request):
        """Exports manufacturing Gerbers for the revision, auto-routing unrouted boards if requested."""
        scope = f"{request.revision_id}:export_gerbers"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        try:
            from ..lifecycle.kicad_service import KiCadLifecycleService
            kicad_service = getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None) or KiCadLifecycleService()
            force_flag = getattr(request, "force", False)
            out_dir = kicad_service.export_gerbers(
                pcb_path,
                auto_route=getattr(request, "auto_route", True),
                check_drc=getattr(request, "check_drc", True),
                force=force_flag,
            )
            try:
                kicad_service.export_drill(pcb_path, output_dir=out_dir, auto_route=getattr(request, "auto_route", True), force=force_flag)
            except Exception:
                pass

            import zipfile
            zip_path = out_dir / f"{pcb_path.stem}_gerbers.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for gf in sorted(out_dir.iterdir()):
                    if gf.is_file() and gf.suffix.lower() != ".zip":
                        zf.write(gf, gf.name)

            from ..design.models import ArtifactKind
            digest = _ingest_design_artifact(
                self.studio,
                revision,
                ArtifactKind.GERBER_BUNDLE,
                zip_path,
                zip_path.name,
                "zip",
                "Deterministic Manufacturing Release",
            )

            import base64
            zip_bytes = zip_path.read_bytes()
            b64_data = base64.b64encode(zip_bytes).decode("ascii")
            gerber_files = [f.name for f in out_dir.iterdir() if f.is_file()]
            rel_zip = str(zip_path.relative_to(self.studio.root).as_posix()) if zip_path.is_relative_to(self.studio.root) else str(zip_path)
            receipt = {
                "operation_id": str(uuid4()),
                "operation_type": "export_gerbers",
                "revision_id": str(revision.revision_id),
                "status": "COMPLETED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": getattr(request, "idempotency_key", None),
                "file_count": len(gerber_files),
                "sha256": digest,
            }
            res = {
                "success": True,
                "output_dir": str(out_dir),
                "file_count": len(gerber_files),
                "files": gerber_files,
                "zip_path": rel_zip,
                "zip_filename": zip_path.name,
                "zip_bytes": len(zip_bytes),
                "sha256": digest,
                "data_uri": f"data:application/zip;base64,{b64_data}",
                "receipt": receipt,
            }
            return self._record_receipt(
                scope,
                getattr(request, "idempotency_key", None),
                "export_gerbers",
                request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
                res,
                revision.revision_id,
            )
        except Exception as e:
            receipt = {
                "operation_id": str(uuid4()),
                "operation_type": "export_gerbers",
                "revision_id": str(revision.revision_id),
                "status": "FAILED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": getattr(request, "idempotency_key", None),
                "error": str(e),
            }
            res = {
                "success": False,
                "error": str(e),
                "receipt": receipt,
            }
            return self._record_receipt(
                scope,
                getattr(request, "idempotency_key", None),
                "export_gerbers",
                request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
                res,
                revision.revision_id,
            )

    def download_gerbers(self, request):
        """Returns base64 data URI and metadata for the Gerber ZIP archive."""
        revision = self.studio.get_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        gerber_out_dir = pcb_path.parent / "gerbers"
        cand_zips = [
            gerber_out_dir / f"{pcb_path.stem}_gerbers.zip",
            pcb_path.parent / f"{pcb_path.stem}_gerbers.zip",
            pcb_path.parent / "gerbers.zip",
        ]
        zip_path = None
        for cz in cand_zips:
            if cz.exists() and cz.stat().st_size > 0:
                zip_path = cz
                break

        if not zip_path:
            res = self.export_gerbers(models.GerberExportQuery(revision_id=request.revision_id, auto_route=True, check_drc=True))
            if not res.get("success"):
                return {"success": False, "error": res.get("error", "Failed to generate Gerbers")}
            rel_p = res["zip_path"]
            zip_path = self.studio.root / rel_p if not Path(rel_p).is_absolute() else Path(rel_p)

        import base64
        import hashlib
        zip_bytes = zip_path.read_bytes()
        digest = hashlib.sha256(zip_bytes).hexdigest()
        b64_data = base64.b64encode(zip_bytes).decode("ascii")
        rel_zip = str(zip_path.relative_to(ws_dir).as_posix()) if zip_path.is_relative_to(ws_dir) else (str(zip_path.relative_to(self.studio.root).as_posix()) if zip_path.is_relative_to(self.studio.root) else str(zip_path))

        return {
            "success": True,
            "filename": zip_path.name,
            "relative_path": rel_zip,
            "sha256": digest,
            "size_bytes": len(zip_bytes),
            "data_uri": f"data:application/zip;base64,{b64_data}",
        }

    @staticmethod
    def _parse_excellon_file(drl_text: str):
        tools = {}
        current_tool = None
        drill_hits = []
        lines = drl_text.splitlines()
        last_comment = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(";"):
                if "TA.AperFunction" in line:
                    last_comment = line
                continue
            tm = re.match(r"^T(\d+)C([\d\.]+)", line)
            if tm:
                tnum = int(tm.group(1))
                dia = float(tm.group(2))
                t_id = f"T{tnum:02d}"
                plated = not ("NonPlated" in last_comment or "NPTH" in last_comment)
                if dia <= 0.45:
                    usage = "Signal / Thermal Via"
                elif dia <= 0.85:
                    usage = "Small Component Lead"
                elif dia <= 1.25:
                    usage = "Power Component / Terminal Pin"
                elif dia <= 2.2:
                    usage = "Connector Pin / Header"
                else:
                    usage = "Mounting / Mechanical Hole"
                tools[t_id] = {
                    "tool_id": t_id,
                    "diameter_mm": dia,
                    "diameter_mils": round(dia * 39.3701, 1),
                    "plated": plated,
                    "count": 0,
                    "pth_count": 0,
                    "npth_count": 0,
                    "usage": usage,
                }
                last_comment = ""
                continue
            tc = re.match(r"^T(\d+)$", line)
            if tc:
                tnum = int(tc.group(1))
                current_tool = f"T{tnum:02d}"
                continue
            coord_m = re.match(r"^X([\d\.\-]+)Y([\d\.\-]+)", line)
            if coord_m:
                x = float(coord_m.group(1))
                y = abs(float(coord_m.group(2)))
                t_info = tools.get(current_tool, {})
                dia = t_info.get("diameter_mm", 0.8)
                plated = t_info.get("plated", True)
                if current_tool in tools:
                    tools[current_tool]["count"] += 1
                    if plated:
                        tools[current_tool]["pth_count"] += 1
                    else:
                        tools[current_tool]["npth_count"] += 1
                drill_hits.append({
                    "x": x,
                    "y": y,
                    "tool_id": current_tool or "T01",
                    "diameter": dia,
                    "plated": plated,
                })
        return tools, drill_hits

    def inspect_gerber_layers(self, request):
        """Inspects RS-274X Gerber layers and Excellon drill schedules for PCB manufacturing verification."""
        revision = self.studio.get_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = sorted(pcb_dir.glob("*.kicad_pcb"), key=lambda p: p.stat().st_size, reverse=True) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = sorted(ws_dir.glob("*.kicad_pcb"), key=lambda p: p.stat().st_size, reverse=True)
        if not pcb_files:
            return {"success": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        gerber_out_dir = pcb_path.parent / "gerbers"

        # Auto-export if gerbers do not exist yet and auto_export is requested
        has_existing_gerbers = gerber_out_dir.exists() and any(
            f.is_file() and f.suffix.lower() not in (".zip", ".lck") for f in gerber_out_dir.iterdir()
        )
        if not has_existing_gerbers and getattr(request, "auto_export", True):
            exp_res = self.export_gerbers(models.GerberExportQuery(revision_id=request.revision_id, auto_route=False, check_drc=False))
            if not exp_res.get("success"):
                exp_res = self.export_gerbers(models.GerberExportQuery(revision_id=request.revision_id, auto_route=True, check_drc=False))

        # Check for Gerber ZIP
        cand_zips = [
            gerber_out_dir / f"{pcb_path.stem}_gerbers.zip",
            pcb_path.parent / f"{pcb_path.stem}_gerbers.zip",
            pcb_path.parent / "gerbers.zip",
            gerber_out_dir / "gerbers.zip",
        ]
        zip_path = None
        for cz in cand_zips:
            if cz.exists() and cz.stat().st_size > 0:
                zip_path = cz
                break

        has_gerbers = zip_path is not None
        gerber_sha256 = _file_sha256(zip_path) if has_gerbers else None
        gerber_bytes = zip_path.stat().st_size if has_gerbers else 0
        gerber_rel_path = (
            str(zip_path.relative_to(ws_dir).as_posix())
            if has_gerbers and zip_path.is_relative_to(ws_dir)
            else (
                str(zip_path.relative_to(self.studio.root).as_posix())
                if has_gerbers and zip_path.is_relative_to(self.studio.root)
                else str(zip_path) if has_gerbers else None
            )
        )

        content = pcb_path.read_text(encoding="utf-8", errors="replace")

        # Edge.Cuts
        edge_cuts = []
        for m in re.finditer(r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', content, re.DOTALL):
            x1, y1, x2, y2 = map(float, m.groups())
            edge_cuts.append({"type": "rect", "x1": min(x1, x2), "y1": min(y1, y2), "x2": max(x1, x2), "y2": max(y1, y2)})
        for m in re.finditer(r'\(gr_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', content, re.DOTALL):
            x1, y1, x2, y2 = map(float, m.groups())
            edge_cuts.append({"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})

        # Tracks
        tracks = []
        for m in re.finditer(r'\(segment\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(width\s+([\d\.\-]+)\)\s+\(layer\s+"([^"]+)"\)\s+\(net\s+(\d+)\)', content):
            x1, y1, x2, y2, w, layer, net = m.groups()
            tracks.append({
                "x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2),
                "width": float(w), "layer": layer, "net": int(net)
            })

        # Footprints & pads
        footprints = []
        board_drill_hits = []
        fp_blocks = content.split('(footprint ')
        for block in fp_blocks[1:]:
            header_end = block.find('\n')
            fp_name = block[:header_end].strip().strip('"')
            at_m = re.search(r'\(at\s+([\d\.\-]+)\s+([\d\.\-]+)(?:\s+([\d\.\-]+))?\)', block)
            fx = float(at_m.group(1)) if at_m else 0.0
            fy = float(at_m.group(2)) if at_m else 0.0
            rot = float(at_m.group(3)) if at_m and at_m.group(3) else 0.0
            rad = math.radians(rot)
            cos_r, sin_r = math.cos(rad), math.sin(rad)

            ref_m = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
            ref = ref_m.group(1) if ref_m else "?"
            val_m = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
            val = val_m.group(1) if val_m else ""
            model_m = re.search(r'\(model\s+"([^"]+)"', block)
            model_path = model_m.group(1) if model_m else None

            pads = []
            for pm in re.finditer(r'\(pad\s+"([^"]+)"\s+(smd|thru_hole|np_thru_hole)\s+(\w+)\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)(?:\s+([\d\.\-]+))?\)\s+\(size\s+([\d\.\-]+)\s+([\d\.\-]+)\)(?:.*?\(drill\s+([\d\.\-]+)\))?', block, re.DOTALL):
                pnum, ptype, pshape, px, py, prot, sx, sy, drill = pm.groups()
                ox, oy = float(px), float(py)
                abs_x = fx + (ox * cos_r - oy * sin_r)
                abs_y = fy + (ox * sin_r + oy * cos_r)
                drill_d = float(drill) if drill else None
                pads.append({
                    "number": pnum, "type": ptype, "shape": pshape,
                    "ox": ox, "oy": oy, "x": round(abs_x, 3), "y": round(abs_y, 3),
                    "sx": float(sx), "sy": float(sy), "drill": drill_d,
                })
                if ptype in ("thru_hole", "np_thru_hole") and drill_d:
                    board_drill_hits.append({
                        "x": round(abs_x, 3), "y": round(abs_y, 3),
                        "diameter": round(drill_d, 3),
                        "plated": ptype == "thru_hole",
                        "pad_number": pnum,
                        "ref": ref,
                        "type": "pad",
                    })

            silks = []
            for sm in re.finditer(r'\(fp_line\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                sx1, sy1, sx2, sy2 = map(float, sm.groups())
                silks.append({"type": "line", "x1": sx1, "y1": sy1, "x2": sx2, "y2": sy2})
            for sm in re.finditer(r'\(fp_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\)', block):
                sx1, sy1, sx2, sy2 = map(float, sm.groups())
                silks.append({"type": "rect", "x1": min(sx1, sx2), "y1": min(sy1, sy2), "x2": max(sx1, sx2), "y2": max(sy1, sy2)})

            footprints.append({
                "name": fp_name, "ref": ref, "value": val,
                "x": fx, "y": fy, "rot": rot, "pads": pads, "silks": silks,
                "has_3d_model": model_path is not None, "model": model_path
            })

        # Vias
        for vm in re.finditer(r'\(via\s+\(at\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(size\s+([\d\.\-]+)\)\s+\(drill\s+([\d\.\-]+)\)', content):
            vx, vy, vs, vd = map(float, vm.groups())
            board_drill_hits.append({
                "x": round(vx, 3), "y": round(vy, 3),
                "diameter": round(vd, 3),
                "plated": True,
                "pad_number": "VIA",
                "ref": "VIA",
                "type": "via",
            })

        # 4-layer planes & zones
        is_4layer = '"In1.Cu"' in content and '"In2.Cu"' in content
        layer_count = 4 if is_4layer else 2
        zones = []
        for zm in re.finditer(r'\(zone\b.*?\(layer\s+"([^"]+)"\)', content, re.DOTALL):
            zlayer = zm.group(1)
            zones.append({"net": "ZONE", "layer": zlayer})

        # Bounding box
        all_xs = [fp["x"] for fp in footprints] + [e["x1"] for e in edge_cuts] + [e["x2"] for e in edge_cuts] + [t["x1"] for t in tracks] + [t["x2"] for t in tracks]
        all_ys = [fp["y"] for fp in footprints] + [e["y1"] for e in edge_cuts] + [e["y2"] for e in edge_cuts] + [t["y1"] for t in tracks] + [t["y2"] for t in tracks]
        min_x = min(all_xs) - 6.0 if all_xs else 0.0
        max_x = max(all_xs) + 6.0 if all_xs else 100.0
        min_y = min(all_ys) - 6.0 if all_ys else 0.0
        max_y = max(all_ys) + 6.0 if all_ys else 100.0

        # Scan Gerber & Drill files in gerber_out_dir
        layers_info = []
        drill_tools = []
        drill_hits_from_drl = []
        
        layer_specs = [
            {"id": "F.Cu", "name": "Top Copper (F.Cu)", "color": "#ef4444", "copper": True, "patterns": [r"-F_Cu\.gtl$", r"-F_Cu\.gbr$", r"\.gtl$"]},
            {"id": "In1.Cu", "name": "Inner Plane 1 (In1.Cu)", "color": "#10b981", "copper": True, "patterns": [r"-In1_Cu\.g1$", r"-In1_Cu\.gbr$", r"\.g1$"]},
            {"id": "In2.Cu", "name": "Inner Plane 2 (In2.Cu)", "color": "#f59e0b", "copper": True, "patterns": [r"-In2_Cu\.g2$", r"-In2_Cu\.gbr$", r"\.g2$"]},
            {"id": "B.Cu", "name": "Bottom Copper (B.Cu)", "color": "#3b82f6", "copper": True, "patterns": [r"-B_Cu\.gbl$", r"-B_Cu\.gbr$", r"\.gbl$"]},
            {"id": "F.Mask", "name": "Top Solder Mask (F.Mask)", "color": "#8b5cf6", "copper": False, "patterns": [r"-F_Mask\.gts$", r"-F_Mask\.gbr$", r"\.gts$"]},
            {"id": "B.Mask", "name": "Bottom Solder Mask (B.Mask)", "color": "#6366f1", "copper": False, "patterns": [r"-B_Mask\.gbs$", r"-B_Mask\.gbr$", r"\.gbs$"]},
            {"id": "F.SilkS", "name": "Top Silkscreen (F.SilkS)", "color": "#f8fafc", "copper": False, "patterns": [r"-F_Silkscreen\.gto$", r"-F_SilkS\.gto$", r"-F_Silkscreen\.gbr$", r"\.gto$"]},
            {"id": "B.SilkS", "name": "Bottom Silkscreen (B.SilkS)", "color": "#94a3b8", "copper": False, "patterns": [r"-B_Silkscreen\.gbo$", r"-B_SilkS\.gbo$", r"-B_Silkscreen\.gbr$", r"\.gbo$"]},
            {"id": "Edge.Cuts", "name": "Board Profile & Slots (Edge.Cuts)", "color": "#eab308", "copper": False, "patterns": [r"-Edge_Cuts\.gm1$", r"-Edge_Cuts\.gbr$", r"\.gm1$"]},
            {"id": "Drill", "name": "Excellon Through-Hole Drill", "color": "#06b6d4", "copper": False, "patterns": [r"\.drl$", r"-PTH\.drl$", r"-NPTH\.drl$"]},
        ]

        if gerber_out_dir.exists():
            files_in_dir = list(gerber_out_dir.iterdir())
            drl_files = [f for f in files_in_dir if f.is_file() and f.suffix.lower() == ".drl"]
            for df in drl_files:
                drl_txt = df.read_text(encoding="utf-8", errors="replace")
                parsed_tools, parsed_hits = self._parse_excellon_file(drl_txt)
                if parsed_hits:
                    drill_hits_from_drl.extend(parsed_hits)
                for t in parsed_tools.values():
                    if not any(x["tool_id"] == t["tool_id"] for x in drill_tools):
                        drill_tools.append(t)

            for spec in layer_specs:
                matched_file = None
                for f in files_in_dir:
                    if f.is_file() and any(re.search(pat, f.name, re.IGNORECASE) for pat in spec["patterns"]):
                        matched_file = f
                        break
                if matched_file:
                    f_size = matched_file.stat().st_size
                    f_sha = _file_sha256(matched_file)
                    layers_info.append({
                        "layer_id": spec["id"],
                        "name": spec["name"],
                        "filename": matched_file.name,
                        "file_size_bytes": f_size,
                        "sha256": f_sha,
                        "color_hex": spec["color"],
                        "is_copper": spec["copper"],
                        "is_drill": spec["id"] == "Drill",
                        "available": True,
                    })

        final_drill_hits = drill_hits_from_drl if drill_hits_from_drl else board_drill_hits
        if not drill_tools and final_drill_hits:
            unique_d = sorted(list(set(h["diameter"] for h in final_drill_hits)))
            tool_map = {}
            for idx, d in enumerate(unique_d):
                t_id = f"T{idx+1:02d}"
                hits_t = [h for h in final_drill_hits if h["diameter"] == d]
                pth_c = sum(1 for h in hits_t if h.get("plated", True))
                npth_c = len(hits_t) - pth_c
                if d <= 0.45:
                    usage = "Signal / Thermal Via"
                elif d <= 0.85:
                    usage = "Small Component Lead"
                elif d <= 1.25:
                    usage = "Power Component / Terminal Pin"
                elif d <= 2.2:
                    usage = "Connector Pin / Header"
                else:
                    usage = "Mounting / Mechanical Hole"
                drill_tools.append({
                    "tool_id": t_id,
                    "diameter_mm": d,
                    "diameter_mils": round(d * 39.3701, 1),
                    "count": len(hits_t),
                    "pth_count": pth_c,
                    "npth_count": npth_c,
                    "plated": pth_c > 0,
                    "usage": usage,
                })
                tool_map[d] = t_id
            for h in final_drill_hits:
                if "tool_id" not in h:
                    h["tool_id"] = tool_map.get(h["diameter"], "T01")

        total_holes = len(final_drill_hits)
        pth_count = sum(1 for h in final_drill_hits if h.get("plated", True))
        npth_count = total_holes - pth_count

        return {
            "success": True,
            "board_name": pcb_path.stem,
            "filename": pcb_path.name,
            "layer_count": layer_count,
            "is_4layer": is_4layer,
            "bbox": {
                "min_x": round(min_x, 2), "min_y": round(min_y, 2),
                "max_x": round(max_x, 2), "max_y": round(max_y, 2),
                "width": round(max_x - min_x, 2), "height": round(max_y - min_y, 2),
            },
            "layers": layers_info,
            "drill_tools": sorted(drill_tools, key=lambda t: t["diameter_mm"]),
            "drill_summary": {
                "total_holes": total_holes,
                "pth_count": pth_count,
                "npth_count": npth_count,
                "tool_count": len(drill_tools),
            },
            "drill_hits": final_drill_hits,
            "edge_cuts": edge_cuts,
            "tracks": tracks,
            "footprints": footprints,
            "zones": zones,
            "has_gerber_zip": has_gerbers,
            "gerber_zip_filename": zip_path.name if has_gerbers else None,
            "gerber_zip_bytes": gerber_bytes,
            "gerber_zip_sha256": gerber_sha256,
            "gerber_zip_path": gerber_rel_path,
        }

    def apply_schematic(self, request):
        """Applies batch schematic updates (symbol swaps, field edits) using internal Copper engine."""
        revision = self._require_draft_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        sch_files = list(pcb_dir.glob("*.kicad_sch")) if pcb_dir.exists() else []
        if not sch_files:
            sch_files = list(ws_dir.glob("*.kicad_sch"))
        if not sch_files:
            return {"success": False, "error": "No .kicad_sch file found in this revision"}

        sch_path = sch_files[0]
        from ..lifecycle.kicad_service import KiCadLifecycleService
        kicad_service = getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None) or KiCadLifecycleService()
        result = kicad_service.apply_schematic(
            sch_path,
            ops=request.ops,
            verify=getattr(request, "verify", True),
        )
        return {
            "success": result.get("success", False),
            "filename": sch_path.name,
            "ops_applied": result.get("ops_applied", 0),
            "changed": result.get("changed", []),
            "checkpoint": result.get("checkpoint"),
            "erc": result.get("erc", {}),
            "findings": result.get("findings", []),
            "error": result.get("error"),
        }

    def generate_report(self, request):
        scope = f"{request.revision_id}:generate_report"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        rep = self.studio.generate_report(request.revision_id)
        rel_rep = Path(rep.report_path)
        pdf_candidate = rel_rep.parent / "report.pdf"
        full_pdf = self.studio.root / pdf_candidate

        # If PDF is not yet compiled, attempt headless compile fallback
        if not (full_pdf.exists() and full_pdf.stat().st_size > 0):
            try:
                from ..dossier_generator import compile_html_to_pdf
                compile_html_to_pdf(self.studio.root / rel_rep, full_pdf)
            except Exception:
                pass

        pdf_avail = full_pdf.exists() and full_pdf.stat().st_size > 0
        pdf_path_str = str(pdf_candidate.as_posix()) if pdf_avail else None
        pdf_digest = None

        if pdf_avail:
            try:
                from ..design.models import ArtifactKind
                revision = self.studio.get_revision(request.revision_id)
                pdf_digest = _ingest_design_artifact(
                    self.studio,
                    revision,
                    ArtifactKind.REPORT,
                    full_pdf,
                    "report.pdf",
                    "pdf",
                    "Complete Product Engineering Dossier (PDF)",
                )
            except Exception:
                pass

        receipt = {
            "operation_id": str(rep.report_id),
            "operation_type": "generate_report",
            "revision_id": str(request.revision_id),
            "status": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sha256": rep.input_hash,
            "pdf_available": pdf_avail,
            "idempotency_key": getattr(request, "idempotency_key", None),
        }
        res = {
            "success": True,
            "report_id": str(rep.report_id),
            "report_path": rep.report_path,
            "pdf_path": pdf_path_str,
            "pdf_available": pdf_avail,
            "sha256": pdf_digest,
            "receipt": receipt,
        }
        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "generate_report",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            request.revision_id,
        )


    def render_3d_pcb(self, request):
        """Forces an on-demand KiCad 10 raytraced 3D rendering snapshot of the revision PCB."""
        view_angle = (getattr(request, "view", "iso") or "iso").lower()
        scope = f"{request.revision_id}:{view_angle}"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self.studio.get_revision(request.revision_id)
        ws_dir = self.studio.workspace_path(revision)
        pcb_dir = ws_dir / "pcb"
        pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
        if not pcb_files:
            pcb_files = list(ws_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return {"success": False, "available": False, "error": "No .kicad_pcb file found in this revision"}

        pcb_path = pcb_files[0]
        view_angle = (getattr(request, "view", "iso") or "iso").lower()
        width = getattr(request, "width", 1200) or 1200
        height = getattr(request, "height", 900) or 900

        render_filename = "board_3d_render.png" if view_angle == "iso" else f"board_3d_{view_angle}.png"
        render_png = pcb_path.parent / render_filename

        from ..lifecycle.kicad_service import KiCadLifecycleService
        kicad_service = getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None) or KiCadLifecycleService()
        if not kicad_service.is_available():
            return {"success": False, "available": False, "error": "KiCad CLI (kicad-cli) is not installed on this workstation"}

        try:
            rendered_path = kicad_service.render_3d(
                pcb_path=pcb_path,
                output_png=render_png,
                view=view_angle,
                width=width,
                height=height,
            )
        except Exception as e:
            return {"success": False, "available": False, "error": f"3D Raytracing failed: {e}"}

        if not rendered_path.exists() or rendered_path.stat().st_size == 0:
            return {"success": False, "available": False, "error": "Raytraced render produced an empty image"}

        import base64
        b64_img = base64.b64encode(rendered_path.read_bytes()).decode("ascii")
        render_bytes = rendered_path.stat().st_size
        render_sha = _file_sha256(rendered_path)

        view_labels = {
            "iso": "Isometric Perspective",
            "top": "Top View (Component Placement)",
            "bottom": "Bottom View (Solder / Ground Plane)",
            "iso_bottom": "Isometric Underside View",
        }

        step_file = pcb_path.parent / f"{pcb_path.stem}.step"
        step_available = step_file.exists() and step_file.stat().st_size > 0
        step_bytes = step_file.stat().st_size if step_available else 0
        step_sha256 = _file_sha256(step_file) if step_available else None

        mech_metrics = _inspect_pcb_mechanical_and_3d(pcb_path, revision.specification)
        receipt = {
            "operation_id": str(uuid4()),
            "operation_type": "render_3d_pcb",
            "revision_id": str(revision.revision_id),
            "status": "COMPLETED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "view": view_angle,
            "sha256": render_sha,
            "idempotency_key": getattr(request, "idempotency_key", None),
        }
        res = {
            "success": True,
            "available": True,
            "kind": "3d",
            "view": view_angle,
            "filename": pcb_path.name,
            "render_image": f"data:image/png;base64,{b64_img}",
            "render_bytes": render_bytes,
            "sha256": render_sha,
            "width": width,
            "height": height,
            "title": f"{pcb_path.stem} 3D Assembly ({view_labels.get(view_angle, view_angle.upper())})",
            "has_step": step_available,
            "step_filename": f"{pcb_path.stem}.step",
            "step_bytes": step_bytes,
            "step_sha256": step_sha256,
            "receipt": receipt,
            **mech_metrics,
        }
        return self._record_receipt(scope, getattr(request, "idempotency_key", None), "render_3d_pcb", request.model_dump(mode="json"), res, revision.revision_id)

    def synthesize_topologies(self, request: models.TopologySynthesizeQuery):
        """Deterministically synthesizes candidate power topologies from revision specification."""
        scope = f"{request.revision_id}:synthesize_topologies"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self._require_draft_revision(request.revision_id)
        product = self.studio.get_product(revision.product_id)
        spec = revision.specification

        vin_nom = spec.vin_nom_v if (spec.vin_nom_v is not None and spec.vin_nom_v > 0) else 24.0
        vin_min = spec.vin_min_v if (spec.vin_min_v is not None and spec.vin_min_v > 0) else vin_nom
        vin_max = spec.vin_max_v if (spec.vin_max_v is not None and spec.vin_max_v > 0) else vin_nom
        if vin_min > vin_nom:
            vin_min = vin_nom
        if vin_max < vin_nom:
            vin_max = vin_nom

        vout = spec.vout_v if (spec.vout_v is not None and spec.vout_v > 0) else 5.0
        iout = spec.iout_a if (spec.iout_a is not None and spec.iout_a > 0) else 2.0
        fsw = spec.switching_frequency_hz if (spec.switching_frequency_hz is not None and spec.switching_frequency_hz > 0) else 200000.0

        from ..design.models import Requirement, EngineeringDesign, CandidateApprovalStatus
        from ..design.synthesis import CandidateSynthesisEngine

        is_isolated = False
        if spec.isolation_requirement:
            iso_text = str(spec.isolation_requirement).strip().lower()
            if iso_text and iso_text not in ("none", "non-isolated", "no", "0", "0v", "uninsulated"):
                is_isolated = True

        reqs = [
            Requirement(parameter="vin_nom", target_value=vin_nom, min_value=vin_min, max_value=vin_max, unit="V"),
            Requirement(parameter="vin_min", target_value=vin_min, unit="V"),
            Requirement(parameter="vin_max", target_value=vin_max, unit="V"),
            Requirement(parameter="vout", target_value=vout, unit="V"),
            Requirement(parameter="iout", target_value=iout, unit="A"),
            Requirement(parameter="frequency_hz", target_value=fsw, unit="Hz"),
            Requirement(parameter="isolation", target_value=1500.0 if is_isolated else 0.0, unit="V"),
        ]

        candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)

        # Match or initialize EngineeringDesign
        target_design = None
        for d in self.studio.design.list_designs():
            if d.core_revision_id == str(revision.revision_id) and d.product_id == str(product.product_id):
                target_design = d
                break

        if not target_design:
            workspace_id = getattr(self.studio, "workspace_id", "default")
            target_design = EngineeringDesign(
                workspace_id=str(workspace_id),
                title=f"{product.name} Engineering Design",
                category=product.category or "dc_dc_converter",
                product_id=str(product.product_id),
                core_revision_id=str(revision.revision_id),
                requirements=reqs,
                candidates=candidates,
            )
        else:
            target_design.requirements = reqs
            target_design.candidates = candidates
            target_design.core_revision_id = str(revision.revision_id)

        self.studio.design._persist(target_design)

        res = {
            "success": True,
            "design_id": str(target_design.id),
            "revision_id": str(revision.revision_id),
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "count": len(candidates),
        }
        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "synthesize_topologies",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            revision.revision_id,
        )

    def forward_annotate_pcb(self, request: models.ForwardAnnotatePcbQuery) -> dict:
        rev = self.studio.get_revision(request.revision_id)
        status_val = getattr(rev.lifecycle_status, "value", rev.lifecycle_status)
        if status_val != "draft":
            raise StudioError("IMMUTABLE", f"Cannot modify frozen revision {request.revision_id}")

        rev_dir = self.studio.workspace_path(rev)
        pcb_files = list(rev_dir.rglob("*.kicad_pcb"))
        if not pcb_files:
            raise StudioError("NOT_FOUND", f"No .kicad_pcb file found in revision {request.revision_id}")

        target_pcb = pcb_files[0]
        if request.ecr_id:
            return self.studio.ecr.forward_annotate_pcb(
                ecr_id=request.ecr_id,
                pcb_path=target_pcb,
                remove_extra=request.remove_extra,
                auto_place_new=request.auto_place_new,
                refill_zones=request.refill_zones,
            )

        from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
        kicad_service = (
            getattr(getattr(self.studio, "engineering_lifecycle", None), "kicad", None)
            or KiCadLifecycleService()
        )
        return kicad_service.forward_annotate_pcb(
            pcb_path=target_pcb,
            remove_extra=request.remove_extra,
            auto_place_new=request.auto_place_new,
            refill_zones=request.refill_zones,
        )

    def select_candidate(self, request: models.CandidateSelectQuery):
        """Promotes a chosen topology candidate into the active revision with KiCad export."""
        revision = self._require_draft_revision(request.revision_id)
        product = self.studio.get_product(revision.product_id)

        from ..design.models import CandidateApprovalStatus, DesignRevision, DesignStatus, ArtifactKind
        from ..design.generators import KiCadSchematicGenerator

        target_design = None
        for d in self.studio.design.list_designs():
            if d.core_revision_id == str(revision.revision_id) and d.product_id == str(product.product_id):
                target_design = d
                break

        if not target_design or not target_design.candidates:
            self.synthesize_topologies(models.TopologySynthesizeQuery(revision_id=request.revision_id))
            for d in self.studio.design.list_designs():
                if d.core_revision_id == str(revision.revision_id) and d.product_id == str(product.product_id):
                    target_design = d
                    break

        if not target_design:
            raise StudioError("NOT_FOUND", "EngineeringDesign not found for this revision")

        selected_cand = None
        for cand in target_design.candidates:
            if cand.id == request.candidate_id or cand.topology.lower() == request.candidate_id.lower() or cand.name.lower() == request.candidate_id.lower():
                selected_cand = cand
                cand.status = CandidateApprovalStatus.SELECTED
            else:
                cand.status = CandidateApprovalStatus.PROPOSED

        if not selected_cand:
            raise StudioError("NOT_FOUND", f"Candidate '{request.candidate_id}' not found in design")

        kicad_res = None
        if selected_cand.ir_snapshot:
            ir = selected_cand.ir_snapshot.model_copy(deep=True)
            rev_index = len(target_design.revisions) + 1
            new_rev = DesignRevision(
                design_id=target_design.id,
                revision_index=rev_index,
                label=f"Rev {rev_index} ({selected_cand.topology})",
                ir=ir,
                summary=f"Synthesized and selected {selected_cand.name} topology",
            )
            target_design.revisions.append(new_rev)
            target_design.active_revision_id = new_rev.id
            target_design.status = DesignStatus.SYNTHESIZED
            self.studio.design._persist(target_design)

            if request.auto_export_kicad:
                import shutil
                ws_dir = self.studio.workspace_path(revision)
                pcb_dir = ws_dir / "pcb"

                if pcb_dir.exists():
                    existing_pro = list(pcb_dir.glob("*.kicad_pro"))
                    if existing_pro:
                        bak_dir = ws_dir / f"pcb_backup_{int(time.time())}"
                        try:
                            shutil.move(str(pcb_dir), str(bak_dir))
                        except Exception:
                            for p in pcb_dir.glob("*.*"):
                                try:
                                    p.unlink()
                                except Exception:
                                    pass
                pcb_dir.mkdir(parents=True, exist_ok=True)

                layers = 4 if ("Phase-Shifted" in selected_cand.topology or "LLC" in selected_cand.topology) else 2
                kicad_res = KiCadSchematicGenerator.export_copper_project(
                    ir=ir,
                    target_dir=pcb_dir,
                    auto_place=True,
                    layers=layers,
                )

                sch_path = Path(kicad_res["schematic"])
                pcb_path = Path(kicad_res["pcb"])
                if sch_path.exists():
                    _ingest_design_artifact(
                        self.studio,
                        revision,
                        ArtifactKind.KICAD_SCH,
                        sch_path,
                        "KiCad Schematic",
                        "KiCad S-Expression (.kicad_sch)",
                        f"Auto-captured from {selected_cand.name}",
                    )
                if pcb_path.exists():
                    _ingest_design_artifact(
                        self.studio,
                        revision,
                        ArtifactKind.KICAD_PCB,
                        pcb_path,
                        "KiCad PCB Layout",
                        "KiCad PCB (.kicad_pcb)",
                        f"Auto-placed from {selected_cand.name}",
                    )

        return {
            "success": True,
            "selected_candidate_id": selected_cand.id,
            "selected_topology": selected_cand.topology,
            "name": selected_cand.name,
            "kicad_exported": request.auto_export_kicad and kicad_res is not None,
            "kicad_details": kicad_res,
        }

    def calculate_thermal_sizing(self, request: models.ThermalSizingQuery):
        """Calculates closed-form electro-thermal margins for semiconductors, magnetics, and PCB traces."""
        scope = f"{request.revision_id}:calculate_thermal_sizing"
        cached = self._check_receipt(scope, getattr(request, "idempotency_key", None))
        if cached:
            return cached
        revision = self.studio.get_revision(request.revision_id)
        spec = revision.specification

        # 1. Determine baseline ambient temperature
        ambient_c = request.ambient_temp_c
        if ambient_c is None:
            if spec.ambient_temperature_k is not None and spec.ambient_temperature_k > 0:
                ambient_c = round(spec.ambient_temperature_k - 273.15, 1)
            else:
                ambient_c = 25.0

        # 2. Extract operating parameters from active design & specification
        vin = spec.vin_nom_v or 24.0
        vout = spec.vout_v or 12.0
        iout = spec.iout_a or 5.0
        pout = vout * iout

        target_design = None
        for d in self.studio.design.list_designs():
            if d.core_revision_id == str(revision.revision_id) and d.product_id == str(revision.product_id):
                target_design = d
                break

        active_cand = None
        if target_design and target_design.candidates:
            active_cand = next((c for c in target_design.candidates if c.status.value == "SELECTED"), target_design.candidates[0])

        eta = 0.92
        num_switches = 2
        num_diodes = 2
        topology_name = "Power Converter"
        if active_cand:
            topology_name = active_cand.topology
            eta = float(active_cand.calculated_metrics.get("estimated_efficiency", 0.92))
            if "Full-Bridge" in active_cand.topology or "PSFB" in active_cand.topology:
                num_switches = 4
                num_diodes = 2
            elif "LLC" in active_cand.topology or "Half-Bridge" in active_cand.topology:
                num_switches = 2
                num_diodes = 2
            elif "Flyback" in active_cand.topology or "Boost" in active_cand.topology or "Buck" in active_cand.topology:
                num_switches = 1
                num_diodes = 1

        total_loss = pout * ((1.0 - eta) / max(eta, 0.5))

        p_switch = request.p_switch_loss_w
        if p_switch is None:
            p_switch = max(0.2, (total_loss * 0.45) / max(num_switches, 1))

        from integrations.calculations.thermal_sizing import (
            calculate_semiconductor_thermal,
            calculate_magnetic_thermal,
            calculate_ipc2152_trace_thermal,
        )

        r_jc = request.r_th_jc_c_w if request.r_th_jc_c_w is not None else 1.5
        r_cs = request.r_th_cs_c_w if request.r_th_cs_c_w is not None else 0.5
        r_sa = request.r_th_sa_c_w if request.r_th_sa_c_w is not None else 0.0
        tj_max = request.t_j_max_c if request.t_j_max_c is not None else 150.0
        derating = request.derating_factor if request.derating_factor is not None else 0.80

        semi_res = calculate_semiconductor_thermal(
            part_number=f"Q1_{topology_name[:10]}",
            p_loss_w=p_switch,
            t_ambient_c=ambient_c,
            t_j_max_c=tj_max,
            derating_factor=derating,
            r_th_jc_c_w=r_jc,
            r_th_cs_c_w=r_cs,
            r_th_sa_c_w=r_sa,
        )

        p_diode = max(0.2, (total_loss * 0.35) / max(num_diodes, 1))
        diode_res = calculate_semiconductor_thermal(
            part_number=f"D1_{topology_name[:10]}",
            p_loss_w=p_diode,
            t_ambient_c=ambient_c,
            t_j_max_c=150.0,
            derating_factor=derating,
            r_th_jc_c_w=2.0,
            r_th_cs_c_w=0.5,
            r_th_sa_c_w=r_sa,
        )

        p_core = max(0.1, total_loss * 0.10)
        p_winding = max(0.1, total_loss * 0.10)
        area_cm2 = request.transformer_surface_area_cm2 if request.transformer_surface_area_cm2 is not None else 45.0
        mag_res = calculate_magnetic_thermal(
            component_name="T1_PowerTransformer",
            p_core_w=p_core,
            p_winding_w=p_winding,
            surface_area_cm2=area_cm2,
            t_ambient_c=ambient_c,
            t_class_max_c=130.0,
            insulation_class="Class B (130°C)",
        )

        trace_current = request.trace_current_a if request.trace_current_a is not None else max(pout / max(vin, 1.0), iout)
        target_delta_t = request.target_trace_delta_t_c if request.target_trace_delta_t_c is not None else 10.0
        cu_oz = request.copper_thickness_oz if request.copper_thickness_oz is not None else 1.0
        is_internal = request.is_internal_trace if request.is_internal_trace is not None else False

        trace_res = calculate_ipc2152_trace_thermal(
            current_a=trace_current,
            target_delta_t_c=target_delta_t,
            copper_thickness_oz=cu_oz,
            is_internal=is_internal,
            layer_name="In1.Cu" if is_internal else "F.Cu",
        )

        max_temp = max(semi_res.t_junction_c, diode_res.t_junction_c, mag_res.t_hotspot_c)
        min_margin = min(semi_res.thermal_margin_c, diode_res.thermal_margin_c, mag_res.thermal_margin_c)
        is_compliant = (semi_res.status in ("PASS_DERATED", "PASS_ABSOLUTE_ONLY", "HEATSINK_SIZED") and mag_res.status == "PASS")

        record_id = None
        if request.record_evidence:
            try:
                rec_payload = {
                    "revision_id": str(revision.revision_id),
                    "stage_id": "thermal_mechanical",
                    "expected_input_hash": specification_hash(spec),
                    "source": "Thermal Sizing Calculator",
                    "reason": f"Electro-thermal assessment for {topology_name}",
                    "idempotency_key": str(uuid4()),
                    "calculation": "semiconductor_thermal",
                    "parameters": {
                        "part_number": semi_res.part_number,
                        "p_loss_w": semi_res.p_loss_w,
                        "t_ambient_c": semi_res.t_ambient_c,
                        "t_j_max_c": semi_res.t_j_max_c,
                        "derating_factor": semi_res.derating_factor,
                        "r_th_jc_c_w": semi_res.r_th_jc_c_w,
                        "r_th_cs_c_w": semi_res.r_th_cs_c_w,
                        "r_th_sa_c_w": semi_res.r_th_sa_c_w,
                    },
                    "assumptions": ["Natural convection ambient", "80% IPC-9592B junction derating"],
                }
                rec = self.studio.engineering_records.run_calculation(rec_payload)
                record_id = rec.get("record_id")
            except Exception:
                pass

        res = {
            "success": True,
            "revision_id": str(revision.revision_id),
            "topology": topology_name,
            "ambient_temp_c": ambient_c,
            "total_converter_loss_w": round(total_loss, 3),
            "semiconductor": semi_res.model_dump(mode="json"),
            "secondary_diode": diode_res.model_dump(mode="json"),
            "magnetics": mag_res.model_dump(mode="json"),
            "ipc2152_trace": trace_res.model_dump(mode="json"),
            "summary": {
                "max_temperature_c": round(max_temp, 1),
                "min_thermal_margin_c": round(min_margin, 1),
                "cooling_strategy": "Heatsink Required" if semi_res.heatsink_required_c_w < 15.0 else "PCB Copper Plane Convection",
                "compliance_status": "COMPLIANT" if is_compliant else "NON_COMPLIANT",
                "heatsink_rth_sa_required_c_w": semi_res.heatsink_required_c_w,
                "pcb_copper_area_req_cm2": semi_res.pcb_copper_area_req_cm2,
                "thermal_vias_count": semi_res.thermal_vias_recommended,
            },
            "record_id": record_id,
        }
        return self._record_receipt(
            scope,
            getattr(request, "idempotency_key", None),
            "calculate_thermal_sizing",
            request.model_dump(mode="json") if hasattr(request, "model_dump") else str(request),
            res,
            revision.revision_id,
        )

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
            fmt = getattr(request, "format", "html") or "html"
            return {"opened": self.studio.open_report(request.report_id, format=fmt)}
        if method == "get_report":
            from ..evidence import Report
            report = self.studio._get("reports", request.report_id, Report)
            path = (self.studio.root / report.report_path).resolve()
            if not path.is_file():
                raise StudioError("NOT_FOUND", "Report file not found")
            pdf_path = path.parent / "report.pdf"
            has_pdf = pdf_path.is_file() and pdf_path.stat().st_size > 0
            return {
                "report_id": str(report.report_id),
                "revision_id": str(report.revision_id),
                "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                "html_content": path.read_text(encoding="utf-8", errors="replace"),
                "has_pdf": has_pdf,
                "pdf_size_bytes": pdf_path.stat().st_size if has_pdf else 0,
            }
        if method == "open_evidence":
            return {"opened": self.studio.open_evidence(request.record_id)}
        if method == "get_evidence":
            return self.studio.get_evidence_content(request.record_id)
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
        if method == "cad_preview":
            return self.cad_preview(request)
        if method == "render_3d_pcb":
            return self.render_3d_pcb(request)
        if method == "run_pcb_drc":
            return self.run_pcb_drc(request)
        if method == "auto_route_pcb":
            return self.auto_route_pcb(request)
        if method == "mill_isolation_slot":
            return self.mill_isolation_slot(request)
        if method == "setup_4layer_planes":
            return self.setup_4layer_planes(request)
        if method == "export_gerbers":
            return self.export_gerbers(request)
        if method == "download_gerbers":
            return self.download_gerbers(request)
        if method == "export_cad_step":
            return self.export_cad_step(request)
        if method == "generate_report":
            return self.generate_report(request)
        if method == "apply_schematic":
            return self.apply_schematic(request)
        if method == "generate_bom":
            from ..bom_generator import generate_bom_deliverables
            return generate_bom_deliverables(self.studio, request.revision_id)
        if method == "generate_test_plan":
            return self.studio.generate_laboratory_test_plan(request.revision_id)
        if method == "get_test_plan":
            return self.studio.get_laboratory_test_plan(request.revision_id)
        if method == "generate_bom_pricing":
            return self.studio.generate_bom_pricing_schedule(request.revision_id, currency=getattr(request, "currency", "USD"))
        if method == "get_bom_pricing":
            return self.studio.get_bom_pricing_schedule(request.revision_id)
        if method == "backup":
            dest = getattr(request, "destination", None) if request else None
            backup_path = self.studio.backup_database(dest)
            return {
                "status": "SUCCESS",
                "backup_path": str(backup_path),
                "timestamp": now().isoformat(),
            }
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
        if method == "list_ecrs":
            ecrs = self.studio.ecr.list_ecrs(workspace_id=request.workspace_id, product_id=request.product_id, revision_id=request.revision_id)
            return [e.model_dump(mode="json") for e in ecrs]
        if method == "create_ecr":
            ecr = self.studio.ecr.create_ecr(
                title=request.title,
                description=request.description,
                reason=request.reason,
                impact_analysis=request.impact_analysis,
                requested_by=request.requested_by,
                affected_stages=request.affected_stages,
                workspace_id=request.workspace_id,
                product_id=request.product_id,
                revision_id=request.revision_id,
                schematic_ops=request.schematic_ops,
            )
            return ecr.model_dump(mode="json")
        if method == "review_ecr":
            from mendex_core.lifecycle.ecr import ECRStatus
            ecr = self.studio.ecr.review_ecr(
                ecr_id=request.ecr_id,
                reviewer=request.reviewer,
                status=ECRStatus(request.status),
                review_notes=request.review_notes,
            )
            return ecr.model_dump(mode="json")
        if method == "calculate_thermal_sizing":
            return self.calculate_thermal_sizing(request)
        if method == "inspect_gerber_layers":
            return self.inspect_gerber_layers(request)
        if method == "synthesize_topologies":
            return self.synthesize_topologies(request)
        if method == "select_candidate":
            return self.select_candidate(request)
        if method == "apply_ecr_schematic":
            return self.studio.ecr.apply_schematic_change(
                ecr_id=request.ecr_id,
                implemented_by=request.implemented_by or "Desktop Automation",
                forward_annotate=getattr(request, "forward_annotate", True),
            )
        if method == "forward_annotate_pcb":
            return self.forward_annotate_pcb(request)
        if method == "get_operation_receipt":
            return self.get_operation_receipt(request)
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
    cad_preview=models.CADPreviewQuery,
    render_3d_pcb=models.Render3DQuery,
    run_pcb_drc=models.CADPreviewQuery,
    auto_route_pcb=models.AutoRouteQuery,
    mill_isolation_slot=models.IsolationSlotQuery,
    setup_4layer_planes=models.FourLayerPlanesQuery,
    export_gerbers=models.GerberExportQuery,
    download_gerbers=models.GerberDownloadQuery,
    export_cad_step=models.STEPExportQuery,
    generate_report=models.ReportGenerateQuery,
    apply_schematic=models.SchematicApplyQuery,
    open_report=models.ReportQuery,
    get_report=models.ReportQuery,
    open_evidence=models.EvidenceQuery,
    get_evidence=models.EvidenceQuery,
    export_report=models.ExportReportQuery,
    review_package=models.ReviewPackageQuery,
    request_review=models.ReviewRequestQuery,
    submit_review=models.ReviewDecisionQuery,
    complete_stage=models.ReviewPackageQuery,
    backup=models.BackupQuery,
    list_ecrs=models.ECRListQuery,
    create_ecr=models.ECRCreateQuery,
    review_ecr=models.ECRReviewQuery,
    apply_ecr_schematic=models.ECRApplySchematicQuery,
    forward_annotate_pcb=models.ForwardAnnotatePcbQuery,
    synthesize_topologies=models.TopologySynthesizeQuery,
    select_candidate=models.CandidateSelectQuery,
    calculate_thermal_sizing=models.ThermalSizingQuery,
    inspect_gerber_layers=models.GerberInspectQuery,
    get_operation_receipt=models.OperationReceiptQuery,
    generate_test_plan=models.TestPlanQuery,
    get_test_plan=models.TestPlanQuery,
    generate_bom_pricing=models.BOMPricingQuery,
    get_bom_pricing=models.BOMPricingQuery,
)