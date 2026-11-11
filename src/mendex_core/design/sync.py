"""Cross-tool revision synchronization and external modification tracking.

Detects when an engineer modifies native CAD/CAE files externally in LTspice or KiCad,
creates versioned design revisions upon return, and marks downstream evidence stale.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import EngineeringDesign, DesignRevision, DesignArtifact, DesignStatus


class SyncStatus(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    MODIFIED_EXTERNALLY = "MODIFIED_EXTERNALLY"
    MISSING = "MISSING"


class CrossToolSyncService:
    """Manages cross-tool file tracking, external modification detection, and reconciliation."""

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Computes SHA-256 digest of a local file."""
        if not file_path.exists():
            return ""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def check_artifact_status(cls, artifact: DesignArtifact, root_dir: Path) -> SyncStatus:
        """Compares current on-disk artifact against stored SHA-256 fingerprint."""
        file_path = root_dir / artifact.path if not Path(artifact.path).is_absolute() else Path(artifact.path)
        if not file_path.exists():
            return SyncStatus.MISSING

        current_hash = cls.compute_sha256(file_path)
        if current_hash != artifact.sha256:
            return SyncStatus.MODIFIED_EXTERNALLY
        return SyncStatus.UP_TO_DATE

    @classmethod
    def detect_modifications(cls, revision: DesignRevision, root_dir: Path) -> List[Dict[str, Any]]:
        """Returns all artifacts in a revision modified outside Mendex Studio."""
        results: List[Dict[str, Any]] = []
        for art in revision.artifacts:
            status = cls.check_artifact_status(art, root_dir)
            if status != SyncStatus.UP_TO_DATE:
                results.append({
                    "artifact_id": art.id,
                    "name": art.name,
                    "kind": art.kind.value,
                    "path": art.path,
                    "status": status.value,
                    "stored_hash": art.sha256,
                })
        return results

    @classmethod
    def reconcile_and_branch_revision(
        cls,
        design: EngineeringDesign,
        root_dir: Path,
        engineer_notes: str = "External CAD edits reconciled into new revision",
    ) -> DesignRevision:
        """Creates a new immutable revision incorporating external file changes and invalidating stale results."""
        active_rev = design.get_active_revision()
        if not active_rev:
            raise ValueError("Design has no active revision to reconcile.")

        new_index = len(design.revisions) + 1
        new_ir = active_rev.ir.model_copy(deep=True)
        new_artifacts: List[DesignArtifact] = []

        for art in active_rev.artifacts:
            file_path = root_dir / art.path if not Path(art.path).is_absolute() else Path(art.path)
            current_hash = cls.compute_sha256(file_path) if file_path.exists() else art.sha256
            is_mod = current_hash != art.sha256

            new_art = art.model_copy(deep=True)
            new_art.id = str(uuid4())
            new_art.sha256 = current_hash
            new_art.is_external_modified = is_mod
            new_art.edit_provenance = "External Native Tool Modification" if is_mod else art.edit_provenance
            new_art.parent_ids = [art.id]
            new_artifacts.append(new_art)

        new_rev = DesignRevision(
            design_id=design.id,
            revision_index=new_index,
            label=f"Rev {new_index}",
            ir=new_ir,
            summary=engineer_notes,
            artifacts=new_artifacts,
        )

        design.revisions.append(new_rev)
        design.active_revision_id = new_rev.id
        design.status = DesignStatus.IN_REVIEW
        design.updated_at = datetime.now(timezone.utc).isoformat()

        return new_rev
