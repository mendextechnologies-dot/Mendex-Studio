"""Engineering Change Request (ECR) and Change Impact Analysis Service."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from .models import LifecycleStage, now


class ECRStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"


class EngineeringChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ecr_id: UUID = Field(default_factory=uuid4)
    ecr_number: str
    title: str
    description: str
    reason: str
    impact_analysis: str
    affected_stages: List[str] = Field(default_factory=list)
    requested_by: str
    status: ECRStatus = ECRStatus.DRAFT
    created_at: datetime = Field(default_factory=now)
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    review_notes: str = ""
    workspace_id: Optional[str] = None
    product_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None
    schematic_ops: Optional[List[Dict[str, Any]]] = None
    applied_at: Optional[datetime] = None
    applied_checkpoint: Optional[str] = None
    erc_result: Optional[Dict[str, Any]] = None
    eco_result: Optional[Dict[str, Any]] = None


class ECRService:
    """Manages Engineering Change Requests and assesses design change impacts."""

    def __init__(self, service: Any):
        self.service = service
        self._init_db()

    def _init_db(self):
        try:
            with self.service.connection() as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS engineering_change_requests (
                        ecr_id TEXT PRIMARY KEY,
                        ecr_number TEXT NOT NULL UNIQUE,
                        workspace_id TEXT,
                        product_id TEXT,
                        revision_id TEXT,
                        status TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                db.execute(
                    "CREATE TRIGGER IF NOT EXISTS engineering_change_requests_no_delete "
                    "BEFORE DELETE ON engineering_change_requests BEGIN "
                    "SELECT RAISE(ABORT, 'Engineering change requests cannot be deleted'); END;"
                )
        except Exception:
            pass

    def create_ecr(
        self,
        title: str,
        description: str,
        reason: str,
        impact_analysis: str,
        requested_by: str,
        affected_stages: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        revision_id: Optional[UUID] = None,
        schematic_ops: Optional[List[Dict[str, Any]]] = None,
    ) -> EngineeringChangeRequest:
        count = self.count_ecrs() + 1
        year = datetime.now().year
        ecr_number = f"ECR-{year}-{count:03d}"

        ecr = EngineeringChangeRequest(
            ecr_number=ecr_number,
            title=title,
            description=description,
            reason=reason,
            impact_analysis=impact_analysis,
            affected_stages=affected_stages or [],
            requested_by=requested_by,
            workspace_id=workspace_id,
            product_id=product_id,
            revision_id=revision_id,
            schematic_ops=schematic_ops,
        )

        with self.service.connection() as db:
            db.execute(
                """
                INSERT INTO engineering_change_requests (ecr_id, ecr_number, workspace_id, product_id, revision_id, status, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(ecr.ecr_id),
                    ecr.ecr_number,
                    workspace_id,
                    str(product_id) if product_id else None,
                    str(revision_id) if revision_id else None,
                    ecr.status.value,
                    ecr.model_dump_json(),
                    ecr.created_at.isoformat(),
                ),
            )
        return ecr

    def count_ecrs(self) -> int:
        try:
            with self.service.connection() as db:
                row = db.execute("SELECT COUNT(*) FROM engineering_change_requests").fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    def get_ecr(self, ecr_id: UUID) -> Optional[EngineeringChangeRequest]:
        with self.service.connection() as db:
            row = db.execute(
                "SELECT payload FROM engineering_change_requests WHERE ecr_id=?",
                (str(ecr_id),),
            ).fetchone()
            if not row:
                return None
            return EngineeringChangeRequest.model_validate_json(row[0])

    def list_ecrs(
        self,
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        revision_id: Optional[UUID] = None,
    ) -> List[EngineeringChangeRequest]:
        ecrs = []
        try:
            with self.service.connection() as db:
                query = "SELECT payload FROM engineering_change_requests WHERE 1=1"
                params: List[str] = []
                if workspace_id:
                    query += " AND workspace_id=?"
                    params.append(workspace_id)
                if product_id:
                    query += " AND product_id=?"
                    params.append(str(product_id))
                if revision_id:
                    query += " AND revision_id=?"
                    params.append(str(revision_id))
                query += " ORDER BY created_at DESC"
                rows = db.execute(query, params).fetchall()
                for r in rows:
                    ecrs.append(EngineeringChangeRequest.model_validate_json(r[0]))
        except Exception:
            pass
        return ecrs

    def review_ecr(
        self,
        ecr_id: UUID,
        reviewer: str,
        status: ECRStatus,
        review_notes: str = "",
    ) -> EngineeringChangeRequest:
        with self.service.connection() as db:
            row = db.execute(
                "SELECT payload FROM engineering_change_requests WHERE ecr_id=?",
                (str(ecr_id),),
            ).fetchone()
            if not row:
                raise ValueError(f"ECR {ecr_id} not found")
            ecr = EngineeringChangeRequest.model_validate_json(row[0])
            ecr.status = status
            ecr.approved_by = reviewer if status == ECRStatus.APPROVED else None
            ecr.approval_date = now() if status in (ECRStatus.APPROVED, ECRStatus.REJECTED) else None
            ecr.review_notes = review_notes

            db.execute(
                "UPDATE engineering_change_requests SET status=?, payload=? WHERE ecr_id=?",
                (ecr.status.value, ecr.model_dump_json(), str(ecr_id)),
            )
        return ecr

    def apply_schematic_change(
        self,
        ecr_id: UUID,
        sch_path: Optional[Path] = None,
        implemented_by: Optional[str] = None,
        forward_annotate: bool = True,
    ) -> Dict[str, Any]:
        """Applies an approved ECR's schematic operations to the KiCad schematic.

        Requires ECR status == APPROVED and revision to be editable (draft).
        Updates status to IMPLEMENTED with checkpoint and KiCad ERC audit evidence.
        """
        ecr = self.get_ecr(ecr_id)
        if not ecr:
            raise ValueError(f"ECR {ecr_id} not found")

        if ecr.status != ECRStatus.APPROVED:
            raise ValueError(
                f"Cannot apply ECR {ecr.ecr_number}: status is {ecr.status.value}, "
                f"must be {ECRStatus.APPROVED.value} before implementation"
            )

        if not ecr.schematic_ops:
            raise ValueError(f"ECR {ecr.ecr_number} has no schematic operations defined")

        # Determine target schematic path
        target_sch: Optional[Path] = None
        if sch_path:
            target_sch = Path(sch_path).resolve()
        elif ecr.revision_id:
            rev = self.service.get_revision(ecr.revision_id)
            status_val = getattr(rev.lifecycle_status, "value", rev.lifecycle_status)
            if status_val != "draft":
                raise ValueError(
                    f"Cannot apply ECR to frozen revision {ecr.revision_id}: status is {status_val}"
                )
            rev_dir = self.service.workspace_path(rev)
            sch_files = list(rev_dir.rglob("*.kicad_sch"))
            if not sch_files:
                raise FileNotFoundError(f"No .kicad_sch file found in revision {ecr.revision_id}")
            target_sch = sch_files[0]
        else:
            raise ValueError("No schematic path or revision_id provided for ECR schematic change")

        if not target_sch.exists():
            raise FileNotFoundError(f"Schematic file not found: {target_sch}")

        # Execute schematic change with verification
        from .kicad_service import KiCadLifecycleService
        kicad_service = (
            getattr(getattr(self.service, "engineering_lifecycle", None), "kicad", None)
            or KiCadLifecycleService()
        )
        result = kicad_service.apply_schematic(
            target_sch,
            ops=ecr.schematic_ops,
            verify=True,
        )

        if not result.get("success"):
            return {
                "success": False,
                "ecr_id": str(ecr.ecr_id),
                "ecr_number": ecr.ecr_number,
                "error": result.get("error", "Schematic modification failed"),
                "ops_applied": 0,
            }

        # Optional forward annotation to PCB layout (ECO)
        eco_result: Optional[Dict[str, Any]] = None
        if forward_annotate:
            pcb_candidates: List[Path] = []
            if target_sch:
                pcb_candidates.extend(target_sch.parent.glob("*.kicad_pcb"))
            if not pcb_candidates and ecr.revision_id:
                rev = self.service.get_revision(ecr.revision_id)
                rev_dir = self.service.workspace_path(rev)
                pcb_candidates.extend(rev_dir.rglob("*.kicad_pcb"))

            if pcb_candidates and pcb_candidates[0].exists():
                eco_result = kicad_service.forward_annotate_pcb(
                    pcb_path=pcb_candidates[0],
                    sch_path=target_sch,
                )

        # Update ECR to IMPLEMENTED
        ecr.status = ECRStatus.IMPLEMENTED
        ecr.applied_at = now()
        ecr.applied_checkpoint = result.get("checkpoint")
        ecr.erc_result = result.get("erc")
        ecr.eco_result = eco_result
        if implemented_by:
            note_suffix = f" [Implemented by {implemented_by} at {ecr.applied_at.isoformat()}]"
            ecr.review_notes = (ecr.review_notes + note_suffix).strip()

        with self.service.connection() as db:
            db.execute(
                "UPDATE engineering_change_requests SET status=?, payload=? WHERE ecr_id=?",
                (ecr.status.value, ecr.model_dump_json(), str(ecr.ecr_id)),
            )

        return {
            "success": True,
            "ecr_id": str(ecr.ecr_id),
            "ecr_number": ecr.ecr_number,
            "status": ecr.status.value,
            "ops_applied": result.get("ops_applied", len(ecr.schematic_ops)),
            "checkpoint": result.get("checkpoint"),
            "erc": result.get("erc", {}),
            "eco": eco_result,
            "changed": result.get("changed", []),
        }

    def forward_annotate_pcb(
        self,
        ecr_id: UUID,
        pcb_path: Optional[Path] = None,
        remove_extra: bool = True,
        auto_place_new: bool = True,
        refill_zones: bool = True,
    ) -> Dict[str, Any]:
        """Explicitly forward-annotates an approved/implemented ECR's changes to the PCB layout."""
        ecr = self.get_ecr(ecr_id)
        if not ecr:
            raise ValueError(f"ECR {ecr_id} not found")

        target_pcb: Optional[Path] = None
        if pcb_path:
            target_pcb = Path(pcb_path).resolve()
        elif ecr.revision_id:
            rev = self.service.get_revision(ecr.revision_id)
            rev_dir = self.service.workspace_path(rev)
            pcb_files = list(rev_dir.rglob("*.kicad_pcb"))
            if not pcb_files:
                raise FileNotFoundError(f"No .kicad_pcb file found in revision {ecr.revision_id}")
            target_pcb = pcb_files[0]
        else:
            raise ValueError("No PCB path or revision_id provided for forward annotation")

        if not target_pcb.exists():
            raise FileNotFoundError(f"PCB file not found: {target_pcb}")

        from .kicad_service import KiCadLifecycleService
        kicad_service = (
            getattr(getattr(self.service, "engineering_lifecycle", None), "kicad", None)
            or KiCadLifecycleService()
        )
        eco_res = kicad_service.forward_annotate_pcb(
            pcb_path=target_pcb,
            remove_extra=remove_extra,
            auto_place_new=auto_place_new,
            refill_zones=refill_zones,
        )
        if eco_res.get("success"):
            ecr.eco_result = eco_res
            with self.service.connection() as db:
                db.execute(
                    "UPDATE engineering_change_requests SET payload=? WHERE ecr_id=?",
                    (ecr.model_dump_json(), str(ecr.ecr_id)),
                )
        return eco_res
