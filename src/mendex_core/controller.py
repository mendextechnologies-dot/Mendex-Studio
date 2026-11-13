"""Authoritative Engineering Controller for Mendex Engineering Core v2.1.

Provides a unified, AI-agent-independent facade consumed identically by:
1. Mendex CLI (`python -m mendex_core.cli`)
2. Mendex MCP Server (`python -m mendex_core.mcp`)
3. Mendex Engineering Studio Desktop GUI
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import ValidationError

from .models import Category, Specification, Product, Revision
from .service import StudioService, StudioError
from .evidence import specification_hash
from .design.service import EngineeringDesignService
from .design.models import Requirement, EngineeringDesign, DesignRevision, DesignCandidate, DesignArtifact
from .integration_contracts import JobRequest, JobRecord, JobStatus, JobResult, Diagnostic, ErrorCode
from .design.synthesis import CandidateSynthesisEngine
from .design.naming import clean_title, sanitize_filename
from .design.ltspice_runner import LTspiceRunner
from .design.femm_runner import FEMMRunner
from .launch import open_native, launch_tool
from .paths import default_data_root
from .adapters.version import windows_file_version


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class MendexEngineeringController:
    """Central unified controller providing deterministic engineering operations."""

    def __init__(self, data_root: Optional[Union[str, Path]] = None, *, service=None):
        self.root = service.root if service is not None else Path(data_root or default_data_root()).resolve()
        if service is not None and data_root is not None and Path(data_root).resolve() != service.root:
            raise ValueError("Controller and service data roots must match")
        self.service = service if service is not None else StudioService(self.root)
        self.design_service = self.service.design
    # -------------------------------------------------------------------------
    # PATH CONFINEMENT & WORKSPACE RESOLUTION (F01)
    # -------------------------------------------------------------------------
    def _resolve_workspace_dir(self, workspace_id: str, must_exist: bool = False) -> Path:
        """Validates UUID and resolved containment of a workspace directory within the root."""
        if not workspace_id or not isinstance(workspace_id, str):
            raise ValueError("Workspace ID must be a non-empty string.")
        clean_id = workspace_id.strip()

        # Reject path traversal and directory separators in workspace ID
        if "/" in clean_id or "\\" in clean_id or ".." in clean_id:
            raise ValueError(f"Access denied: Traversal or path separators not allowed in workspace ID '{workspace_id}'.")

        # Must be a valid UUID or 'default'
        if clean_id != "default":
            try:
                clean_id = str(UUID(clean_id))
            except (ValueError, AttributeError):
                raise ValueError(f"Invalid workspace ID format: '{workspace_id}'. Must be a valid UUID or 'default'.")

        # First check if clean_id corresponds to an authoritative project or revision
        if clean_id != "default":
            try:
                product = self.service.get_product(UUID(clean_id))
                rev = self.service.get_revision(product.active_revision_id)
                p_dir = self.service.workspace_path(rev).resolve()
                p_dir.relative_to(self.root)
                if must_exist and not p_dir.exists():
                    raise FileNotFoundError(f"Project workspace '{clean_id}' not found.")
                return p_dir
            except FileNotFoundError:
                raise
            except Exception:
                try:
                    rev = self.service.get_revision(UUID(clean_id))
                    r_dir = self.service.workspace_path(rev).resolve()
                    r_dir.relative_to(self.root)
                    if must_exist and not r_dir.exists():
                        raise FileNotFoundError(f"Revision workspace '{clean_id}' not found.")
                    return r_dir
                except FileNotFoundError:
                    raise
                except Exception:
                    pass

        ws_root = (self.root / "workspaces").resolve()
        ws_dir = (ws_root / clean_id).resolve()

        # Confinement check - must be strictly inside ws_root
        try:
            ws_dir.relative_to(ws_root)
        except ValueError:
            raise ValueError(f"Access denied: Workspace directory '{ws_dir}' escapes workspaces root '{ws_root}'.")

        if must_exist and not ws_dir.exists():
            raise FileNotFoundError(f"Workspace '{clean_id}' not found.")

        return ws_dir

    def _resolve_artifact_path(self, ws_dir: Path, relative_path: str) -> Path:
        """Validates that an artifact relative path is strictly confined within ws_dir."""
        if not relative_path or not isinstance(relative_path, str):
            raise ValueError("Artifact relative path must be a non-empty string.")
        if Path(relative_path).is_absolute() or Path(relative_path).drive:
            raise ValueError("Artifact path must be relative")
        clean_rel = relative_path.strip().lstrip("/\\")
        parts = Path(clean_rel).parts
        if ".." in parts:
            raise ValueError(f"Access denied: Path traversal ('..') not allowed in artifact path '{relative_path}'.")

        target = (ws_dir / clean_rel).resolve()
        try:
            target.relative_to(ws_dir.resolve())
        except ValueError:
            raise ValueError(f"Access denied: Artifact path '{relative_path}' escapes workspace directory '{ws_dir}'.")
        return target

    def _workspace_revision(self, workspace_id):
        if workspace_id == "default":
            return None
        for lookup in (self.service.get_product, self.service.get_revision):
            try:
                value = lookup(UUID(str(workspace_id)))
            except StudioError as exc:
                if exc.code != "NOT_FOUND":
                    raise
                continue
            if isinstance(value, Product):
                return self.service.get_revision(value.active_revision_id)
            return value
        return None

    def _stage_simulation_input(self, workspace_id, name, suffixes, job_id):
        workspace = self._resolve_workspace_dir(workspace_id, must_exist=True)
        revision = self._workspace_revision(workspace_id)
        if revision and revision.lifecycle_status != "draft":
            raise StudioError("IMMUTABLE", "Run simulations on a draft revision; historical inputs remain frozen")
        candidates = [a for a in self.list_design_artifacts(workspace_id) if a["extension"] in suffixes]
        if name:
            if Path(name).is_absolute() or Path(name).drive or ".." in Path(name).parts:
                raise StudioError("INVALID_INPUT", "Simulation input must be a confined relative path")
            candidates = [a for a in candidates if a["relative_path"] == name or a["name"] == name]
        if not candidates:
            raise FileNotFoundError("No matching native simulation input")
        if len(candidates) != 1:
            raise StudioError("CONFLICT", "Multiple native inputs; specify the registered relative path")
        selected = candidates[0]
        if selected["integrity"] is False:
            raise StudioError("CONFLICT", "Registered simulation input has changed")
        source = Path(selected["absolute_path"])
        if source.stat().st_size > 10 * 1024 * 1024:
            raise StudioError("INVALID_INPUT", "Native input exceeds 10 MiB")
        data = source.read_bytes()
        if source.suffix.lower() in (".net", ".cir"):
            import re
            if re.search(r"(?im)^\s*\.(?:include|inc|lib)\s", data.decode("utf-8", errors="replace")):
                raise StudioError("UNSUPPORTED", "External SPICE model bundles require explicit confined staging")
        directory = self.service.integrations.job_path(job_id)
        directory.mkdir(parents=True, exist_ok=False)
        staged = directory / ("input" + source.suffix.lower())
        staged.write_bytes(data)
        context = {"source_path": str(source.relative_to(self.root)), "source_sha256": _sha256(staged)}
        if revision:
            context.update(project_id=str(revision.product_id), revision_id=str(revision.revision_id),
                           input_hash=specification_hash(revision.specification))
        return staged, directory, context

    def _finalize_native_job(self, record, directory):
        (directory / "request.json").write_text(record.request.model_dump_json(indent=2), encoding="utf-8")
        self.service.integrations._finalize(record, record.result, directory,
            {p: _sha256(directory / p) for p in record.request.input_paths})


    # -------------------------------------------------------------------------
    # WORKSPACE OPERATIONS
    # -------------------------------------------------------------------------
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """Lists all active engineering workspaces and product workspaces."""
        workspaces = self.service.integrations.list_workspaces()
        products = self.service.list_products()
        results: List[Dict[str, Any]] = []

        existing_ws_ids = {w.get("workspace_id") for w in workspaces}
        for ws in workspaces:
            results.append({
                "workspace_id": ws.get("workspace_id"),
                "name": ws.get("name", "Unnamed Workspace"),
                "description": ws.get("description", ""),
                "created_at": ws.get("created_at"),
                "product_id": ws.get("product_id"),
                "kind": "integration_workspace",
            })

        for p in products:
            if str(p.product_id) not in existing_ws_ids:
                results.append({
                    "workspace_id": str(p.product_id),
                    "name": f"{p.code} — {p.name}",
                    "description": p.description,
                    "created_at": p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at),
                    "product_id": str(p.product_id),
                    "kind": "product_workspace",
                })
        return results

    def create_workspace(self, name: str, description: str = "", product_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new engineering workspace."""
        if not name or not name.strip():
            raise ValueError("Workspace name cannot be empty.")
        clean_name = clean_title(name.strip())
        ws = self.service.integrations.create_workspace(
            name=clean_name,
            description=description.strip(),
            product_id=product_id,
        )
        ws_dir = self._resolve_workspace_dir(ws["workspace_id"])
        ws_dir.mkdir(parents=True, exist_ok=True)
        return {
            "status": "CREATED",
            "workspace_id": ws["workspace_id"],
            "name": ws["name"],
            "description": ws.get("description", ""),
            "path": str(ws_dir),
        }

    def get_workspace_status(self, workspace_id: str) -> Dict[str, Any]:
        """Returns comprehensive status of an engineering workspace."""
        ws_dir = self._resolve_workspace_dir(workspace_id)
        designs = [d for d in self.design_service.list_designs() if d.workspace_id == workspace_id]
        jobs = [j.model_dump(mode="json") for j in self.service.integrations.list_jobs() if getattr(j.request, "workspace_id", None) == workspace_id]

        file_counts = {
            "schematics": len(list(ws_dir.glob("**/*.kicad_sch"))) if ws_dir.exists() else 0,
            "pcb_layouts": len(list(ws_dir.glob("**/*.kicad_pcb"))) if ws_dir.exists() else 0,
            "spice_netlists": len(list(ws_dir.glob("**/*.net"))) + len(list(ws_dir.glob("**/*.cir"))) if ws_dir.exists() else 0,
            "waveforms": len(list(ws_dir.glob("**/*.raw"))) if ws_dir.exists() else 0,
            "cad_solids": len(list(ws_dir.glob("**/*.step"))) if ws_dir.exists() else 0,
        }
        registered = self.list_design_artifacts(workspace_id)
        file_counts.update(schematics=sum(a["extension"] == ".kicad_sch" for a in registered),
                           pcb_layouts=sum(a["extension"] == ".kicad_pcb" for a in registered))

        return {
            "workspace_id": workspace_id,
            "directory_exists": ws_dir.exists(),
            "path": str(ws_dir),
            "design_count": len(designs),
            "designs": [{"design_id": d.id, "title": d.title, "status": d.status, "revisions": len(d.revisions)} for d in designs],
            "total_simulations": len(jobs),
            "simulation_jobs": jobs[-5:],
            "artifact_summary": file_counts,
        }

    # -------------------------------------------------------------------------
    # ENGINEERING PROJECTS (v2.1 Project-Oriented Architecture)
    # -------------------------------------------------------------------------
    def list_projects(self) -> List[Dict[str, Any]]:
        """Lists all authoritative engineering projects and active baseline revisions."""
        products = self.service.list_products()
        results: List[Dict[str, Any]] = []
        for p in products:
            try:
                rev = self.service.get_revision(p.active_revision_id)
                spec = rev.specification.model_dump(mode="json")
                ws_path = str(self.service.workspace_path(rev))
            except Exception:
                spec = {}
                ws_path = ""
            results.append({
                "project_id": str(p.product_id),
                "workspace_id": str(p.product_id),
                "code": p.code,
                "name": p.name,
                "category": p.category.value if hasattr(p.category, "value") else str(p.category),
                "owner": p.owner,
                "description": p.description,
                "active_revision_id": str(p.active_revision_id),
                "status": "ACTIVE",
                "specifications": spec,
                "created_at": p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at),
                "directory": ws_path,
            })
        return results

    def create_project(
        self,
        name: str,
        code: Optional[str] = None,
        category: str = "dc_dc_converter",
        owner: str = "Engineer",
        description: str = "",
        auto_enroll: bool = False,
    ) -> Dict[str, Any]:
        """Creates a new authoritative engineering project with baseline specifications and storage."""
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty.")
        clean_name = name.strip()
        proj_code = code.strip() if code and code.strip() else clean_name.replace(" ", "-")[:12].upper()

        created = self.create_product(
            code=proj_code,
            name=clean_name,
            category=category,
            owner=owner,
            description=description,
        )
        pid = created["product_id"]

        try:
            with self.service.connection() as db:
                db.execute(
                    "INSERT OR IGNORE INTO integration_workspaces (id, name, description, owner, product_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (pid, clean_name, description, owner, pid, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
                )
        except Exception:
            pass

        if auto_enroll:
            try:
                self.enroll_project(pid)
            except Exception:
                pass

        return {
            "status": "CREATED",
            "project_id": pid,
            "workspace_id": pid,
            "code": created["code"],
            "name": created["name"],
            "category": created["category"],
            "revision_id": created["revision_id"],
            "revision_label": created["revision_label"],
        }

    def enroll_project(
        self,
        project_id: str,
        definition_id: str = "engineering",
        version: str = "3.1.0",
    ) -> Dict[str, Any]:
        """Enrolls a project's active revision into the specified engineering lifecycle."""
        proj = self.get_project(project_id)
        from mendex_core.engineering_lifecycle.models import Enrollment
        self.service.engineering_lifecycle.enroll(
            Enrollment(
                revision_id=UUID(proj["active_revision_id"]),
                definition_id=definition_id,
                version=version,
                source=f"controller:{proj.get('owner', 'Engineer')}",
                reason=f"Enrollment of {proj['code']} into {definition_id} lifecycle",
                idempotency_key=f"enroll-{proj['active_revision_id']}",
            )
        )
        return {
            "status": "ENROLLED",
            "project_id": proj["project_id"],
            "revision_id": proj["active_revision_id"],
            "definition_id": definition_id,
        }

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Retrieves comprehensive project status, active revision, specifications, and evidence."""
        try:
            prod_uuid = UUID(project_id)
            prod = self.service.get_product(prod_uuid)
        except Exception:
            with self.service.connection() as db:
                row = db.execute("SELECT id FROM products WHERE code=? COLLATE NOCASE", (project_id,)).fetchone()
            if not row:
                raise FileNotFoundError(f"Project '{project_id}' not found.")
            prod = self.service.get_product(UUID(row[0]))

        rev = self.service.get_revision(prod.active_revision_id)
        revisions = self.service.list_revisions(prod.product_id)
        ws_path = self.service.workspace_path(rev)

        artifacts = self.list_design_artifacts(str(prod.product_id)) if ws_path.exists() else []
        sims = self.list_simulations(str(prod.product_id))
        validations = self.get_validation_summary(str(rev.revision_id))

        return {
            "project_id": str(prod.product_id),
            "workspace_id": str(prod.product_id),
            "code": prod.code,
            "name": prod.name,
            "category": prod.category.value if hasattr(prod.category, "value") else str(prod.category),
            "owner": prod.owner,
            "description": prod.description,
            "active_revision_id": str(prod.active_revision_id),
            "active_revision_label": rev.revision_label,
            "lifecycle_status": rev.lifecycle_status.value if hasattr(rev.lifecycle_status, "value") else str(rev.lifecycle_status),
            "specification": rev.specification.model_dump(mode="json"),
            "spec_hash": specification_hash(rev.specification),
            "revisions": [r.model_dump(mode="json") for r in revisions],
            "artifacts_count": len(artifacts),
            "simulations_count": len(sims),
            "validations": validations,
            "directory": str(ws_path),
        }

    def get_project_specifications(self, project_id: str) -> Dict[str, Any]:
        """Retrieves electrical specifications and physical hash for an engineering project."""
        proj = self.get_project(project_id)
        return {
            "project_id": proj["project_id"],
            "code": proj["code"],
            "active_revision_id": proj["active_revision_id"],
            "specification": proj["specification"],
            "input_hash": proj["spec_hash"],
        }

    def save_project_specification(self, project_id: str, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persists validated operating specifications to a project's active revision."""
        proj = self.get_project(project_id)
        rev_id = proj["active_revision_id"]
        res = self.save_specification(rev_id, spec_data)
        res["project_id"] = proj["project_id"]
        return res

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Deletes an engineering project, its revisions, jobs, and workspace files."""
        res = self.delete_product(project_id)
        pid = res.get("product_id")
        try:
            with self.service.connection() as db:
                db.execute("DELETE FROM integration_workspaces WHERE id=? OR product_id=?", (pid, pid))
        except Exception:
            pass
        return {
            "status": "DELETED",
            "project_id": pid,
            "message": f"Project '{project_id}' and all associated revisions were cleanly removed.",
        }

    # -------------------------------------------------------------------------
    # SPECIFICATION OPERATIONS
    # -------------------------------------------------------------------------
    def validate_specification(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates electrical specification parameters against SI schema."""
        try:
            spec = Specification.model_validate(spec_data)
            return {
                "valid": True,
                "specification": spec.model_dump(mode="json"),
                "supplied_fields": sum(getattr(spec, f) is not None for f in (
                    "vin_min_v", "vin_nom_v", "vin_max_v", "vout_v", "iout_a", "switching_frequency_hz", "ambient_temperature_k"
                )),
                "message": "Specification satisfies all schema and ordering constraints.",
            }
        except (ValidationError, ValueError) as exc:
            clean_errors = []
            if isinstance(exc, ValidationError):
                for err in exc.errors():
                    clean_err = {}
                    for k, v in err.items():
                        if k == "ctx":
                            clean_err[k] = {ck: str(cv) for ck, cv in v.items()}
                        elif isinstance(v, (str, int, float, bool, list, type(None))):
                            clean_err[k] = v
                        else:
                            clean_err[k] = str(v)
                    clean_errors.append(clean_err)
            else:
                clean_errors = [{"msg": str(exc), "type": "value_error"}]

            return {
                "valid": False,
                "errors": clean_errors,
                "message": f"Specification validation failed: {str(exc)}",
            }

    def save_specification(self, revision_id: str, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates and persists a specification on a product revision."""
        spec = Specification.model_validate(spec_data)
        updated_rev = self.service.update_specification(UUID(revision_id), spec)
        return {
            "status": "UPDATED",
            "revision_id": str(updated_rev.revision_id),
            "specification_hash": specification_hash(updated_rev.specification),
            "specification": updated_rev.specification.model_dump(mode="json"),
        }

    # -------------------------------------------------------------------------
    # DESIGN SYNTHESIS OPERATIONS
    # -------------------------------------------------------------------------
    def generate_design(
        self,
        workspace_id: str,
        title: str,
        category: str = "dc_dc_converter",
        vin_nom: float | None = None,
        vout: float | None = None,
        iout: float | None = None,
        fsw_hz: float | None = None,
        ripple_v: float | None = None,
        vin_min: Optional[float] = None,
        vin_max: Optional[float] = None,
        isolation_v: Optional[float] = None,
        generate_artifacts: bool = True,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesizes candidate topologies and generates native engineering artifacts."""
        from .design.requests import DesignGenerationRequest
        DesignGenerationRequest.model_validate(dict(
            workspace_id=workspace_id, title=title, category=category, vin_nom=vin_nom,
            vout=vout, iout=iout, fsw_hz=fsw_hz, ripple_v=ripple_v, vin_min=vin_min,
            vin_max=vin_max, isolation_v=isolation_v, generate_artifacts=generate_artifacts,
            product_id=product_id))
        workspace_revision = self._workspace_revision(workspace_id)
        if workspace_revision and workspace_revision.lifecycle_status != "draft":
            raise StudioError("IMMUTABLE", "Design generation requires a draft revision")
        if workspace_revision:
            product_id = product_id or str(workspace_revision.product_id)
            if vin_min is None:
                vin_min = workspace_revision.specification.vin_min_v
            if vin_max is None:
                vin_max = workspace_revision.specification.vin_max_v
        safe_title = clean_title(title, fallback="Power Converter Design")
        # No invented input range: without explicit limits the design covers nominal input only.
        v_min = vin_min if vin_min is not None else vin_nom
        v_max = vin_max if vin_max is not None else vin_nom
        design_assumptions = []
        if vin_min is None or vin_max is None:
            design_assumptions.append("Input voltage range not specified; design evaluated at nominal input only.")

        reqs = [
            Requirement(parameter="vin_nom", target_value=vin_nom, unit="V", min_value=v_min, max_value=v_max),
            Requirement(parameter="vout", target_value=vout, unit="V"),
            Requirement(parameter="iout", target_value=iout, unit="A"),
            Requirement(parameter="fsw", target_value=fsw_hz, unit="Hz"),
            Requirement(parameter="ripple", target_value=ripple_v, max_value=ripple_v, unit="V"),
        ]
        if isolation_v and isolation_v > 0:
            reqs.append(Requirement(parameter="isolation_v", target_value=isolation_v, unit="V"))

        # Resolve linked project context before creating files or design records.
        # Design generation never rewrites a supplied specification implicitly.
        authoritative_rev_id = None
        if product_id:
            product = self.service.get_product(UUID(product_id))
            revision = self.service.get_revision(product.active_revision_id)
            if str(workspace_id) not in (str(product.product_id), str(revision.revision_id)):
                raise StudioError("INVALID_INPUT", "Design workspace and product must identify the same draft")
            if revision.lifecycle_status != "draft":
                raise StudioError("IMMUTABLE", "Design generation requires a draft revision")
            updates = dict(vin_min_v=v_min, vin_nom_v=vin_nom, vin_max_v=v_max,
                           vout_v=vout, iout_a=iout, switching_frequency_hz=fsw_hz)
            for field, value in updates.items():
                existing = getattr(revision.specification, field)
                if existing is not None and existing != value:
                    raise StudioError("CONFLICT", f"Design {field} differs from the saved specification; revise specifications explicitly")
            spec_obj = Specification.model_validate({**revision.specification.model_dump(), **updates})
            self.service.update_specification(revision.revision_id, spec_obj)
            authoritative_rev_id = str(revision.revision_id)

        design = self.design_service.create_design_from_requirements(
            workspace_id=workspace_id,
            title=safe_title,
            category=category,
            requirements=reqs,
            product_id=product_id,
        )
        design.core_revision_id = authoritative_rev_id
        self.design_service._persist(design)

        artifacts_meta: List[Dict[str, Any]] = []
        if generate_artifacts:
            ws_path = self._resolve_workspace_dir(workspace_id)
            ws_path.mkdir(parents=True, exist_ok=True)
            artifacts = self.design_service.generate_native_artifacts(design.id, ws_path)
            artifacts_meta = [a.model_dump(mode="json") for a in artifacts]

        active_rev = design.get_active_revision()

        return {
            "status": "SYNTHESIZED",
            "assumptions": design_assumptions,
            "design_id": design.id,
            "title": design.title,
            "category": design.category,
            "workspace_id": workspace_id,
            "revision_id": authoritative_rev_id or (active_rev.id if active_rev else None),
            "active_revision": active_rev.label if active_rev else "Rev 1",
            "topology": active_rev.topology if active_rev else "Synthesized",
            "candidate_count": len(design.candidates),
            "candidates": [{"id": c.id, "name": c.name, "topology": c.topology, "score": c.feasibility_score} for c in design.candidates],
            "generated_artifacts": artifacts_meta,
            "electrical_summary": {
                "vin_nom": vin_nom,
                "vout": vout,
                "iout": iout,
                "pout_w": vout * iout,
                "switching_frequency_hz": fsw_hz,
            },
        }

    def get_design(self, design_id: str) -> Dict[str, Any]:
        """Retrieves design details and component sizing."""
        design = self.design_service.get_design(design_id)
        if not design:
            raise StudioError("NOT_FOUND", f"Engineering design '{design_id}' not found.")
        active_rev = design.get_active_revision()
        components = []
        if active_rev and active_rev.ir:
            components = [c.model_dump(mode="json") for c in active_rev.ir.components]
        return {
            "design_id": design.id,
            "workspace_id": design.workspace_id,
            "title": design.title,
            "status": design.status,
            "active_revision_id": design.active_revision_id,
            "active_topology": active_rev.topology if active_rev else "Unknown",
            "components": components,
            "revisions": [{"id": r.id, "index": r.revision_index, "label": r.label, "summary": r.summary} for r in design.revisions],
        }

    def list_design_candidates(self, design_id: str) -> List[Dict[str, Any]]:
        """Lists all synthesized candidate topologies for an engineering design."""
        design = self.design_service.get_design(design_id)
        if not design:
            raise StudioError("NOT_FOUND", f"Engineering design '{design_id}' not found.")
        return [
            {
                "id": c.id,
                "name": c.name,
                "topology": c.topology,
                "feasibility_score": c.feasibility_score,
                "calculated_metrics": c.calculated_metrics,
                "constraints_satisfied": c.constraints_satisfied,
            }
            for c in design.candidates
        ]

    # -------------------------------------------------------------------------
    # DETERMINISTIC ENGINEERING CALCULATIONS
    # -------------------------------------------------------------------------
    # Required inputs per calculation: (canonical name, accepted aliases). No values are ever defaulted.
    CALCULATION_INPUTS = {
        "dowell": [("frequency_hz", ("freq",)), ("layers", ("layers_count",)), ("conductor_diameter_mm", ("wire_diameter_mm",)),
                   ("layer_porosity_factor", ("porosity",)), ("r_dc_ohm", ("rdc",)), ("temperature_c", ("temp_c",))],
        "losses": [("r_ds_on_ohm", ("r_dson_ohm", "rdson")), ("i_rms_a", ("current_rms",)), ("duty_cycle", ("duty",)),
                   ("e_on_j", ("eon",)), ("e_off_j", ("eoff",)), ("frequency_hz", ("f_sw_hz",))],
        "steinmetz": [("k", ()), ("alpha", ()), ("beta", ()), ("frequency_hz", ("freq",)), ("b_peak_t", ("bmax",)),
                      ("core_volume_m3", ("volume",))],
        "flyback": [("vin_min_v", ()), ("vin_nom_v", ()), ("vout_v", ()), ("iout_a", ()), ("frequency_hz", ()), ("d_max", ()),
                    ("efficiency", ()), ("b_max_t", ()), ("core_ae_mm2", ())],
    }
    CALCULATION_ALIASES = {
        "dowell": "dowell", "winding_loss": "dowell", "ac_loss": "dowell",
        "losses": "losses", "semiconductor_loss": "losses", "mosfet_loss": "losses",
        "steinmetz": "steinmetz", "core_loss": "steinmetz", "magnetics": "steinmetz",
        "flyback": "flyback", "transformer": "flyback", "transformer_design": "flyback",
    }

    def run_calculation(self, calc_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes deterministic analytical calculations. Every numeric input must be supplied explicitly."""
        calc = self.CALCULATION_ALIASES.get(calc_type.lower().strip())
        if calc is None:
            raise ValueError(
                f"Unknown calculation type '{calc_type}'. Supported: 'dowell', 'losses', 'steinmetz', 'flyback'."
            )
        params = params or {}
        values: Dict[str, float] = {}
        missing = []
        for name, aliases in self.CALCULATION_INPUTS[calc]:
            raw = next((params[k] for k in (name, *aliases) if params.get(k) is not None), None)
            if raw is None:
                missing.append(name)
                continue
            try:
                values[name] = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"Calculation input '{name}' must be numeric (got {raw!r}).")
        if missing:
            raise ValueError(f"Missing required inputs for '{calc}' calculation: {', '.join(missing)}. No defaults are assumed.")

        if calc == "dowell":
            from integrations.calculations.winding_losses import calculate_dowell_ac_resistance
            res = calculate_dowell_ac_resistance(
                frequency_hz=values["frequency_hz"],
                conductor_diameter_mm=values["conductor_diameter_mm"],
                layers_count=int(values["layers"]),
                layer_porosity_factor=values["layer_porosity_factor"],
                r_dc_ohm=values["r_dc_ohm"],
                temperature_c=values["temperature_c"],
            )
            name = "dowell_ac_winding_factor"
        elif calc == "losses":
            from integrations.calculations.power_losses import calculate_semiconductor_losses
            res = calculate_semiconductor_losses(
                part_number=str(params.get("part_number") or "UNSPECIFIED"),
                r_ds_on_ohm=values["r_ds_on_ohm"],
                i_rms_a=values["i_rms_a"],
                duty_cycle=values["duty_cycle"],
                e_on_j=values["e_on_j"],
                e_off_j=values["e_off_j"],
                frequency_hz=values["frequency_hz"],
            )
            name = "semiconductor_losses"
        elif calc == "steinmetz":
            from integrations.calculations.power_losses import calculate_core_loss_steinmetz
            res = calculate_core_loss_steinmetz(
                material=str(params.get("material") or "UNSPECIFIED"),
                k=values["k"],
                alpha=values["alpha"],
                beta=values["beta"],
                frequency_hz=values["frequency_hz"],
                b_peak_t=values["b_peak_t"],
                core_volume_m3=values["core_volume_m3"],
            )
            name = "steinmetz_core_loss"
        else:
            from integrations.calculations.transformer_design import calculate_flyback_transformer_parameters
            explicit = {"v_diode_drop_v": float(params["v_diode_drop_v"])} if "v_diode_drop_v" in params else {}
            res = calculate_flyback_transformer_parameters(**values, **explicit)
            name = "flyback_transformer_design"

        return {
            "calculation": name,
            "inputs": values,
            **res.model_dump(mode="json"),
        }

    # -------------------------------------------------------------------------
    # SIMULATION OPERATIONS
    # -------------------------------------------------------------------------
    def run_simulation(
        self,
        workspace_id: str,
        tool: str = "ltspice",
        netlist_name: Optional[str] = None,
        duration_s: float = 0.002,
    ) -> Dict[str, Any]:
        """Runs headless industrial simulation (LTspice / FEMM) and records evidence."""
        tool_lower = tool.lower().strip()
        ws_dir = self._resolve_workspace_dir(workspace_id, must_exist=True)

        job_id = uuid4()
        try:
            ws_uuid = UUID(str(workspace_id))
        except (ValueError, AttributeError):
            ws_uuid = uuid4()

        if tool_lower == "ltspice":
            netlist_path, ws_dir, context = self._stage_simulation_input(workspace_id, netlist_name, (".net", ".cir"), job_id)
            start_t = datetime.now(timezone.utc)
            result = self.design_service.ltspice_runner.run_simulation(
                netlist_path=netlist_path,
                stop_time_s=duration_s,
                working_dir=ws_dir,
            )

            # Persist authoritative job record (F04)
            ev_paths = []
            rf = getattr(result, "raw_file", None) or (Path(result.raw_file_path) if getattr(result, "raw_file_path", None) else None)
            lf = getattr(result, "log_file", None) or (Path(result.log_file_path) if getattr(result, "log_file_path", None) else None)
            if rf and rf.exists():
                try:
                    ev_paths.append(str(rf.relative_to(ws_dir)).replace("\\", "/"))
                except ValueError:
                    pass
            if lf and lf.exists():
                try:
                    ev_paths.append(str(lf.relative_to(ws_dir)).replace("\\", "/"))
                except ValueError:
                    pass

            req = JobRequest(
                job_id=job_id,
                workspace_id=ws_uuid,
                tool_id="ltspice",
                operation="transient",
                input_paths=[str(netlist_path.relative_to(ws_dir)).replace("\\", "/")],
                parameters={
                    **context,
                    "requested_duration_s": duration_s,
                    "duration_applied": False,  # the netlist's own .tran directive governs the run
                    "netlist_sha256": _sha256(netlist_path),
                    "raw_sha256": _sha256(rf) if rf and rf.exists() else None,
                    "convergence_status": result.convergence_status,
                    "summary_verdict": result.summary_verdict,
                    "log_errors": result.log_errors,
                    "log_warnings": result.log_warnings,
                    "worker_pid": os.getpid(),
                },
                provenance="Mendex Core v2.1 LTspice Headless Simulation",
            )
            rec = JobRecord(
                request=req,
                status=JobStatus.SUCCEEDED if result.success else JobStatus.FAILED,
                started_at=start_t,
                progress=1.0,
                result=JobResult(
                    job_id=job_id,
                    tool_id="ltspice",
                    tool_version=windows_file_version(self.design_service.ltspice_runner.exe_path) if self.design_service.ltspice_runner.exe_path else None,
                    status=JobStatus.SUCCEEDED if result.success else JobStatus.FAILED,
                    started_at=start_t,
                    ended_at=datetime.now(timezone.utc),
                    exit_code=0 if result.success else (result.exit_code or 1),
                    evidence_paths=ev_paths,
                    diagnostics=[Diagnostic(code=ErrorCode.EXECUTION_FAILED, message=str(result.error_message))] if result.error_message else [],
                ),
            )
            try:
                with self.service.connection() as db:
                    db.execute("INSERT OR IGNORE INTO integration_workspaces (id, name) VALUES (?, ?)", (str(ws_uuid), str(ws_uuid)))
            except Exception:
                pass
            self.service.integrations._store_job(rec)
            (ws_dir / "metrics.json").write_text(json.dumps(result.steady_state_metrics), encoding="utf-8")
            rec.result.outputs.append("metrics.json")
            if lf and lf.is_file():
                self.service.integrations._log(ws_dir, lf.read_text(encoding="utf-8", errors="replace")[:4000])
            self._finalize_native_job(rec, ws_dir)

            return {
                "status": "COMPLETED" if result.success else "FAILED",
                "job_id": str(job_id),
                "tool": "ltspice",
                "netlist": str(netlist_path.name),
                "exit_code": result.exit_code,
                "execution_time_s": result.execution_time_s,
                "raw_file": str(result.raw_file.relative_to(self.root)) if result.raw_file and result.raw_file.exists() else None,
                "log_file": str(result.log_file.relative_to(self.root)) if result.log_file and result.log_file.exists() else None,
                "steady_state_metrics": result.steady_state_metrics,
                "convergence_status": result.convergence_status,
                "summary_verdict": result.summary_verdict,
                "requirements_evaluated": result.requirements_evaluated,
                "log_errors": result.log_errors,
                "log_warnings": result.log_warnings,
                "netlist_sha256": req.parameters["netlist_sha256"],
                "duration_note": "Requested duration is not applied; the netlist .tran directive governs the run.",
                "error": result.error_message,
            }

        elif tool_lower == "femm":
            lua, ws_dir, context = self._stage_simulation_input(workspace_id, netlist_name, (".lua",), job_id)
            lua_files = [lua]
            femm_start_t = datetime.now(timezone.utc)
            femm_res = FEMMRunner.run_script(lua_files[0], working_dir=ws_dir)

            # Persist authoritative job record (F04)
            req = JobRequest(
                job_id=job_id,
                workspace_id=ws_uuid,
                tool_id="femm",
                operation="script",
                input_paths=[str(lua_files[0].relative_to(ws_dir)).replace("\\", "/")],
                parameters={**context, "worker_pid": os.getpid()},
                provenance="Mendex Core v2.1 FEMM 4.2 Script Simulation",
            )
            rec = JobRecord(
                request=req,
                status=JobStatus.SUCCEEDED if femm_res.success else JobStatus.FAILED,
                started_at=femm_start_t,
                progress=1.0,
                result=JobResult(
                    job_id=job_id,
                    tool_id="femm",
                    status=JobStatus.SUCCEEDED if femm_res.success else JobStatus.FAILED,
                    started_at=femm_start_t,
                    ended_at=datetime.now(timezone.utc),
                    exit_code=0 if femm_res.success else 1,
                    evidence_paths=[str(lua_files[0].relative_to(ws_dir)).replace("\\", "/")],
                    diagnostics=[Diagnostic(code=ErrorCode.EXECUTION_FAILED, message=str(femm_res.error_message))] if femm_res.error_message else [],
                ),
            )
            try:
                with self.service.connection() as db:
                    db.execute("INSERT OR IGNORE INTO integration_workspaces (id, name) VALUES (?, ?)", (str(ws_uuid), str(ws_uuid)))
            except Exception:
                pass
            self.service.integrations._store_job(rec)
            rec.result.evidence_paths = [p.name for p in ws_dir.iterdir() if p.is_file()]
            self._finalize_native_job(rec, ws_dir)

            return {
                "status": "COMPLETED" if femm_res.success else "FAILED",
                "job_id": str(job_id),
                "tool": "femm",
                "script": str(lua_files[0].name),
                "solver_status": femm_res.solver_status,
                "summary_verdict": femm_res.summary_verdict,
                "b_max_tesla": femm_res.b_max_tesla if femm_res.summary_verdict != "NOT_EVALUATED" else None,
                "core_saturated": femm_res.is_saturated,
                "execution_time_s": femm_res.execution_time_s,
                "error": femm_res.error_message,
            }

        else:
            raise ValueError(f"Simulation tool '{tool}' not supported. Supported: 'ltspice', 'femm'.")

    @staticmethod
    def _single_input(ws_dir: Path, patterns, label: str, workspace_id: str) -> Path:
        """Returns the only matching input file; refuses to guess when several exist."""
        found = sorted({p for pat in patterns for p in ws_dir.glob(f"**/{pat}")})
        if not found:
            raise FileNotFoundError(f"No {label} found in workspace '{workspace_id}'.")
        if len(found) > 1:
            names = ", ".join(str(p.relative_to(ws_dir)).replace("\\", "/") for p in found)
            raise ValueError(f"Multiple {label} files in workspace '{workspace_id}'; specify one explicitly: {names}")
        return found[0]

    def list_simulations(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists simulation jobs executed across workspaces."""
        if workspace_id:
            try:
                ws_uuid = str(UUID(workspace_id))
            except (ValueError, AttributeError):
                ws_uuid = workspace_id
            jobs = self.service.integrations.list_jobs(ws_uuid)
        else:
            jobs = self.service.integrations.list_jobs()
        return [j.model_dump(mode="json") for j in jobs]

    # -------------------------------------------------------------------------
    # ARTIFACT OPERATIONS
    # -------------------------------------------------------------------------
    def list_design_artifacts(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Lists all design files, CAD models, netlists, and waveforms in a workspace."""
        ws_dir = self._resolve_workspace_dir(workspace_id)
        if not ws_dir.exists():
            return []

        results = []
        registered = {}
        for design in self.design_service.list_designs():
            if design.workspace_id != workspace_id and design.product_id != workspace_id:
                continue
            for revision in design.revisions:
                for artifact in revision.artifacts:
                    candidate = (self.root / artifact.path).resolve()
                    if candidate.is_relative_to(self.root):
                        registered[candidate] = artifact
        candidates = set(ws_dir.rglob("*")) | set(registered)
        for p in sorted(candidates):
            if p.is_file():
                ext = p.suffix.lower()
                category = "other"
                if ext in (".kicad_sch", ".kicad_pro"):
                    category = "schematic"
                elif ext in (".kicad_pcb", ".kicad_dru"):
                    category = "pcb_layout"
                elif ext in (".asc", ".net", ".cir"):
                    category = "simulation_netlist"
                elif ext in (".raw", ".log"):
                    category = "simulation_output"
                elif ext in (".step", ".stp", ".stl"):
                    category = "mechanical_cad"
                elif ext == ".lua":
                    category = "femm_script"

                # Compute checksum
                sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
                results.append({
                    "name": p.name,
                    "relative_path": str(p.relative_to(ws_dir)) if p.is_relative_to(ws_dir) else str(p.relative_to(self.root)),
                    "absolute_path": str(p),
                    "size_bytes": p.stat().st_size,
                    "category": category,
                    "extension": ext,
                    "sha256": sha256,
                    "registered_sha256": registered[p].sha256 if p in registered else None,
                    "integrity": sha256 == registered[p].sha256 if p in registered else None,
                })
        return results

    def open_artifact(self, workspace_id: str, relative_path: str) -> Dict[str, Any]:
        """Launches external CAD/viewer for an artifact in the workspace."""
        ws_dir = self._resolve_workspace_dir(workspace_id, must_exist=True)
        registered = next((a for a in self.list_design_artifacts(workspace_id)
                           if a["relative_path"] == relative_path and a["registered_sha256"]), None)
        if registered:
            if not registered["integrity"]:
                raise StudioError("CONFLICT", "Registered artifact has changed")
            target = Path(registered["absolute_path"])
        else:
            target = self._resolve_artifact_path(ws_dir, relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Artifact '{relative_path}' not found in workspace '{workspace_id}'.")
        pid = open_native(target)
        return {
            "status": "OPENED",
            "workspace_id": workspace_id,
            "path": str(target),
            "process_id": pid,
        }

    # -------------------------------------------------------------------------
    # REVISIONS & VALIDATION
    # -------------------------------------------------------------------------
    def list_revisions(self, product_id: str) -> List[Dict[str, Any]]:
        """Lists all revisions for a given product."""
        revs = self.service.list_revisions(UUID(product_id))
        return [
            {
                "revision_id": str(r.revision_id),
                "product_id": str(r.product_id),
                "revision_label": r.revision_label,
                "lifecycle_status": r.lifecycle_status,
                "created_at": r.created_at.isoformat(),
                "specification_hash": specification_hash(r.specification),
            }
            for r in revs
        ]

    def create_revision(self, product_id: str, label: str) -> Dict[str, Any]:
        """Creates a new immutable revision snapshot for a product."""
        rev = self.service.create_revision(UUID(product_id), label)
        return {
            "status": "CREATED",
            "revision_id": str(rev.revision_id),
            "label": rev.revision_label,
            "lifecycle_status": rev.lifecycle_status,
            "created_at": rev.created_at.isoformat(),
        }

    def list_products(self) -> List[Dict[str, Any]]:
        """Lists all authoritative engineering products stored in SQLite."""
        prods = self.service.list_products()
        return [
            {
                "product_id": str(p.product_id),
                "code": p.code,
                "name": p.name,
                "category": p.category.value,
                "owner": p.owner,
                "description": p.description,
                "created_at": p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at),
            }
            for p in prods
        ]

    def create_product(
        self,
        code: str,
        name: str,
        category: str = "dc_dc_converter",
        owner: str = "Engineer",
        description: str = "",
    ) -> Dict[str, Any]:
        """Creates a new authoritative engineering product and initial baseline revision."""
        if not code or not code.strip():
            raise ValueError("Product code cannot be empty.")
        if not name or not name.strip():
            raise ValueError("Product name cannot be empty.")

        cat_enum = Category.DC_DC
        for c in Category:
            if c.value == category or c.name.lower() == category.lower():
                cat_enum = c
                break

        product = self.service.create_product(
            code=code.strip(),
            name=name.strip(),
            category=cat_enum,
            owner=owner.strip() or "Engineer",
            description=description.strip(),
        )
        rev = self.service.get_revision(product.active_revision_id)
        return {
            "status": "CREATED",
            "product_id": str(product.product_id),
            "revision_id": str(rev.revision_id),
            "code": product.code,
            "name": product.name,
            "category": product.category.value,
            "revision_label": rev.revision_label,
        }

    def delete_product(self, product_id: str) -> Dict[str, Any]:
        """Deletes an engineering product and all associated revisions."""
        self.service.delete_product(product_id)
        return {
            "status": "DELETED",
            "product_id": str(product_id),
            "message": f"Product '{product_id}' and all associated revisions were cleanly removed.",
        }

    def get_validation_summary(self, revision_id: str) -> Dict[str, Any]:
        """Returns the formal engineering validation summary for a revision."""
        summary_list = self.service.validation_summary(UUID(revision_id))
        checks_serialized = []
        for item in summary_list:
            rec = item["record"]
            rec_dump = rec.model_dump(mode="json") if hasattr(rec, "model_dump") else rec
            checks_serialized.append({
                "record": rec_dump,
                "effective_status": item.get("effective_status"),
                "stale": item.get("stale", False),
                "evidence_integrity": item.get("evidence_integrity", True),
            })
        return {
            "revision_id": str(revision_id),
            "total_checks": len(checks_serialized),
            "checks": checks_serialized,
        }

    # -------------------------------------------------------------------------
    # REPORTING & EVIDENCE
    # -------------------------------------------------------------------------
    def generate_report(self, revision_id: Optional[str] = None) -> Dict[str, Any]:
        """Generates formal immutable engineering dossier."""
        rev_id = revision_id
        if not rev_id:
            prods = self.service.list_products()
            if prods:
                revs = self.service.list_revisions(prods[0].product_id)
                if revs:
                    rev_id = str(revs[0].revision_id)
        if not rev_id:
            raise ValueError("No product revision specified or available to generate dossier.")

        report = self.service.generate_report(UUID(rev_id))
        report_file = self.root / report.report_path
        report_hash = hashlib.sha256(report_file.read_bytes()).hexdigest() if report_file.exists() else report.input_hash
        return {
            "status": "GENERATED",
            "report_id": str(report.report_id),
            "report_path": str(report_file),
            "input_hash": report.input_hash,
            "hash": report_hash,
            "created_at": report.generated_at.isoformat(),
        }

    # -------------------------------------------------------------------------
    # TOOL MANAGEMENT
    # -------------------------------------------------------------------------
    def list_tools(self) -> List[Dict[str, Any]]:
        """Lists host engineering tools with installation and operational status."""
        tools = self.service.list_tools()
        results = []
        for t in tools:
            health = self.service.integrations.detect(t.tool_id)
            health_state = getattr(health, "state", getattr(health, "status", "UNKNOWN"))
            if hasattr(health_state, "value"):
                health_state = health_state.value
            results.append({
                "tool_id": t.tool_id,
                "display_name": getattr(t, "display_name", t.tool_id),
                "state": t.state,
                "status": str(health_state),
                "installed_path": getattr(health, "installed_path", None) or t.executable,
                "version": getattr(health, "version", None),
            })
        return results

    def check_tool(self, tool_id: str) -> Dict[str, Any]:
        """Performs a live diagnostic health check on a specific host tool."""
        health = self.service.integrations.detect(tool_id)
        health_state = getattr(health, "state", getattr(health, "status", "UNKNOWN"))
        if hasattr(health_state, "value"):
            health_state = health_state.value
        return {
            "tool_id": tool_id,
            "status": str(health_state),
            "installed_path": getattr(health, "installed_path", None),
            "version": getattr(health, "version", None),
            "issues": getattr(health, "issues", []),
        }

    def open_tool_file(self, tool_id: str, file_path: str) -> Dict[str, Any]:
        """Launches native external engineering tool with target file."""
        candidate = Path(file_path)
        target = (candidate if candidate.is_absolute() else self.root / candidate).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Access denied: '{file_path}' is outside the Mendex data root '{self.root}'.")
        if not target.exists():
            raise FileNotFoundError(f"Engineering file '{target}' does not exist.")
        pid = launch_tool(tool_id, target)
        return {
            "status": "LAUNCHED",
            "tool_id": tool_id,
            "file": str(target),
            "process_id": pid,
        }
