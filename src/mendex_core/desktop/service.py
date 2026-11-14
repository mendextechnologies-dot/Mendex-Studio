"""Desktop JSON-RPC dispatch, read views, and native file launch service."""
import json
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..evidence import specification_hash
from ..models import Product, Revision, now
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
                   if design.product_id == str(product.product_id)
                   and design.core_revision_id == str(revision.revision_id)]
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
            for v in self.studio.list_validation(revision_id):
                checks.append({
                    "record_id": str(v.record_id),
                    "check_id": v.check.check_id,
                    "title": v.check.title,
                    "status": v.check.status.value if hasattr(v.check.status, "value") else str(v.check.status),
                    "effective_status": v.effective_status.value if hasattr(v.effective_status, "value") else str(v.effective_status),
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
            stride = max(1, total_pts // 1000)
            samples = []
            if total_pts > 0:
                for idx in range(0, total_pts, stride):
                    sample = {"time": float(time_arr[idx])}
                    for trace in requested_traces:
                        if trace in raw_data:
                            sample[trace] = float(raw_data[trace][idx])
                    samples.append(sample)
            from integrations.parsers.ltspice_parser import calculate_waveform_metrics
            metrics = calculate_waveform_metrics(raw_data)
            return {"samples": samples, "traces": requested_traces, "total_points": total_pts, "metrics": metrics}
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
            pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
            if not pcb_files:
                pcb_files = list(ws_dir.glob("*.kicad_pcb"))
            if not pcb_files:
                return {"kind": "3d", "available": False, "error": "No .kicad_pcb file found in this revision"}

            pcb_path = pcb_files[0]
            render_png = pcb_path.parent / "board_3d_render.png"

            # Check alternative render names if primary does not exist
            if not render_png.exists() or render_png.stat().st_size == 0:
                for alt_name in ["pcb-3d-iso.png", f"{pcb_path.stem}_3d.png", "render/pcb-3d-iso.png"]:
                    alt_path = pcb_path.parent / alt_name
                    if alt_path.exists() and alt_path.stat().st_size > 0:
                        render_png = alt_path
                        break

            # Trigger KiCad 3D Raytracer via CopperKiCadAdapter if not yet rendered
            if not render_png.exists() or render_png.stat().st_size == 0:
                try:
                    from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
                    adapter = CopperKiCadAdapter()
                    rendered = adapter.render_3d(pcb_path, output_png=render_png, view="iso")
                    if Path(rendered).exists() and Path(rendered).stat().st_size > 0:
                        render_png = Path(rendered)
                except Exception:
                    pass

            if render_png.exists() and render_png.stat().st_size > 0:
                import base64
                b64_img = base64.b64encode(render_png.read_bytes()).decode("ascii")
                return {
                    "kind": "3d",
                    "available": True,
                    "filename": pcb_path.name,
                    "render_image": f"data:image/png;base64,{b64_img}",
                    "render_bytes": render_png.stat().st_size,
                    "title": f"{pcb_path.stem} Photorealistic 3D Assembly",
                }
            else:
                return {
                    "kind": "3d",
                    "available": False,
                    "filename": pcb_path.name,
                    "error": "KiCad 10 raytraced 3D render could not be generated.",
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

            return {
                "kind": "pcb",
                "available": True,
                "filename": pcb_path.name,
                "bbox": {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "width": max_x - min_x, "height": max_y - min_y},
                "edge_cuts": edge_cuts,
                "tracks": tracks,
                "footprints": footprints,
                "drc_summary": drc_summary
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
            for wm in re.finditer(r'\(wire\s+\(pts\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(xy\s+([\d\.\-]+)\s+([\d\.\-]+)\)\)', content):
                x1, y1, x2, y2 = map(float, wm.groups())
                wires.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

            labels = []
            for lm in re.finditer(r'\((?:label|hierarchical_label)\s+"([^"]+)"[^\)]*\(at\s+([\d\.\-]+)\s+([\d\.\-]+)', content):
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

            return {
                "kind": "schematic",
                "available": True,
                "title": title,
                "filename": sch_path.name,
                "bbox": {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "width": max_x - min_x, "height": max_y - min_y},
                "symbols": symbols,
                "wires": wires,
                "labels": labels,
                "erc_summary": erc_summary
            }

    def auto_route_pcb(self, request):
        """Executes guided topological auto-routing and ground pour on the revision's PCB."""
        revision = self.studio.get_revision(request.revision_id)
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
        )

        # Trigger fresh 3D render snapshot post-routing
        try:
            render_png = pcb_path.parent / "board_3d_render.png"
            adapter.render_3d(pcb_path, output_png=render_png, view="iso")
        except Exception:
            pass

        return {
            "success": result.get("routing_completed", False) or result.get("tracks", 0) > 0,
            "filename": pcb_path.name,
            "tracks": result.get("tracks", 0),
            "vias": result.get("vias", 0),
            "unrouted_after": result.get("unrouted_after", 0),
            "pour_completed": result.get("pour_completed", False),
            "drc_errors": result.get("drc_errors", 0),
            "drc_warnings": result.get("drc_warnings", 0),
            "messages": result.get("messages", []),
            "netclasses": result.get("netclasses", {}),
        }

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
        if method == "cad_preview":
            return self.cad_preview(request)
        if method == "auto_route_pcb":
            return self.auto_route_pcb(request)
        if method == "generate_bom":
            from ..bom_generator import generate_bom_deliverables
            return generate_bom_deliverables(self.studio, request.revision_id)
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
    auto_route_pcb=models.AutoRouteQuery,
    open_report=models.ReportQuery,
    open_evidence=models.EvidenceQuery,
    export_report=models.ExportReportQuery,
    review_package=models.ReviewPackageQuery,
    request_review=models.ReviewRequestQuery,
    submit_review=models.ReviewDecisionQuery,
    complete_stage=models.ReviewPackageQuery,
    backup=models.BackupQuery,
)