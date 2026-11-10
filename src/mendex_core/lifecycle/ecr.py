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

    def list_ecrs(
        self,
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
    ) -> List[EngineeringChangeRequest]:
        ecrs = []
        try:
            with self.service.connection() as db:
                query = "SELECT payload FROM engineering_change_requests WHERE 1=1"
                params = []
                if workspace_id:
                    query += " AND workspace_id=?"
                    params.append(workspace_id)
                if product_id:
                    query += " AND product_id=?"
                    params.append(str(product_id))
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
            row = db.execute("SELECT payload FROM engineering_change_requests WHERE ecr_id=?", (str(ecr_id),)).fetchone()
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
