"""Workflow database persistence, version history, and import/export service."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .contracts import (
    WorkflowDefinition, WorkflowExecutionRecord, WorkflowStatus, NodeExecutionState
)


def migrate_workflows_table(db: sqlite3.Connection) -> None:
    """Additive schema migration for visual workflows and execution records."""
    with db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                workspace_id TEXT,
                product_id TEXT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                version INTEGER DEFAULT 1,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_workflow_ws ON workflows(workspace_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_workflow_prod ON workflows(product_id)")

        db.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL REFERENCES workflows(id),
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration_s REAL DEFAULT 0.0,
                provenance TEXT,
                manifest_sha256 TEXT,
                payload TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_workflow_runs_wf ON workflow_runs(workflow_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status)")


class WorkflowStorageService:
    """Manages CRUD persistence, schema migration, and runs for visual workflows."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        conn = self._get_connection()
        try:
            migrate_workflows_table(conn)
        finally:
            conn.close()

    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Create or update a workflow definition."""
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        payload = workflow.model_dump_json()

        conn = self._get_connection()
        try:
            with conn:
                existing = conn.execute("SELECT version FROM workflows WHERE id = ?", (workflow.id,)).fetchone()
                if existing:
                    new_version = existing["version"] + 1
                    workflow.version = new_version
                    payload = workflow.model_dump_json()
                    conn.execute("""
                        UPDATE workflows 
                        SET workspace_id = ?, product_id = ?, name = ?, description = ?, version = ?, payload = ?, updated_at = ?
                        WHERE id = ?
                    """, (workflow.workspace_id, workflow.product_id, workflow.name, workflow.description, workflow.version, payload, workflow.updated_at, workflow.id))
                else:
                    conn.execute("""
                        INSERT INTO workflows (id, workspace_id, product_id, name, description, version, payload, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (workflow.id, workflow.workspace_id, workflow.product_id, workflow.name, workflow.description, workflow.version, payload, workflow.created_at, workflow.updated_at))
            return workflow
        finally:
            conn.close()

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieve workflow by ID."""
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT payload FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
            if not row:
                return None
            return WorkflowDefinition.model_validate_json(row["payload"])
        finally:
            conn.close()

    def list_workflows(self, workspace_id: Optional[str] = None) -> List[WorkflowDefinition]:
        """List workflows, optionally filtered by workspace."""
        conn = self._get_connection()
        try:
            if workspace_id:
                rows = conn.execute("SELECT payload FROM workflows WHERE workspace_id = ? ORDER BY updated_at DESC", (workspace_id,)).fetchall()
            else:
                rows = conn.execute("SELECT payload FROM workflows ORDER BY updated_at DESC").fetchall()
            return [WorkflowDefinition.model_validate_json(r["payload"]) for r in rows]
        finally:
            conn.close()

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow and its associated run records."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM workflow_runs WHERE workflow_id = ?", (workflow_id,))
                cur = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    def duplicate_workflow(self, workflow_id: str, new_name: Optional[str] = None) -> Optional[WorkflowDefinition]:
        """Duplicate an existing workflow under a new ID."""
        wf = self.get_workflow(workflow_id)
        if not wf:
            return None

        new_wf = wf.model_copy(deep=True)
        new_wf.id = str(uuid4())
        new_wf.name = new_name or f"{wf.name} (Copy)"
        new_wf.version = 1
        new_wf.created_at = datetime.now(timezone.utc).isoformat()
        new_wf.updated_at = new_wf.created_at

        # Remap internal node IDs so connections remain intact
        id_map = {node.id: str(uuid4()) for node in new_wf.nodes}
        for node in new_wf.nodes:
            node.id = id_map[node.id]
        for conn in new_wf.connections:
            conn.id = str(uuid4())
            conn.source_node_id = id_map.get(conn.source_node_id, conn.source_node_id)
            conn.target_node_id = id_map.get(conn.target_node_id, conn.target_node_id)

        return self.save_workflow(new_wf)

    def record_run(self, run_record: WorkflowExecutionRecord) -> WorkflowExecutionRecord:
        """Save a completed or active workflow execution record."""
        payload = run_record.model_dump_json()
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO workflow_runs (id, workflow_id, status, started_at, finished_at, duration_s, provenance, manifest_sha256, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_record.id,
                    run_record.workflow_id,
                    run_record.status.value,
                    run_record.started_at,
                    run_record.finished_at,
                    run_record.duration_s,
                    run_record.provenance,
                    run_record.manifest_sha256,
                    payload
                ))
            return run_record
        finally:
            conn.close()

    def get_run(self, run_id: str) -> Optional[WorkflowExecutionRecord]:
        """Retrieve run record by ID."""
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT payload FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return WorkflowExecutionRecord.model_validate_json(row["payload"])
        finally:
            conn.close()

    def list_runs(self, workflow_id: str) -> List[WorkflowExecutionRecord]:
        """List execution records for a workflow."""
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT payload FROM workflow_runs WHERE workflow_id = ? ORDER BY started_at DESC", (workflow_id,)).fetchall()
            return [WorkflowExecutionRecord.model_validate_json(r["payload"]) for r in rows]
        finally:
            conn.close()

    def export_workflow_json(self, workflow_id: str) -> str:
        """Export workflow definition to JSON string."""
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow {workflow_id} not found")
        return wf.model_dump_json(indent=2)

    def import_workflow_json(self, json_str: str, workspace_id: Optional[str] = None) -> WorkflowDefinition:
        """Import a workflow from JSON string, validating schema."""
        data = json.loads(json_str)
        wf = WorkflowDefinition.model_validate(data)
        # Assign new ID to avoid collisions
        wf.id = str(uuid4())
        if workspace_id:
            wf.workspace_id = workspace_id
        wf.created_at = datetime.now(timezone.utc).isoformat()
        wf.updated_at = wf.created_at
        return self.save_workflow(wf)
