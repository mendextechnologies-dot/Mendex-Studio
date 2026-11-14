"""Deterministic, dependency-aware workflow execution engine."""
from __future__ import annotations

import time
import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from .contracts import (
    WorkflowDefinition,
    WorkflowExecutionRecord,
    NodeExecutionRecord,
    WorkflowStatus,
    NodeExecutionState,
    NodeCategory,
)
from .registry import NodeRegistry, ExecutionContext, BaseNode
from .validation import detect_cycles_and_toposort, validate_workflow
from .storage import WorkflowStorageService
from .types import QuantityValue, PortDataType


class CancellationToken:
    """Thread-safe cooperative cancellation token."""
    def __init__(self):
        self._is_cancelled = threading.Event()

    def cancel(self) -> None:
        self._is_cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled.is_set()


class WorkflowExecutionEngine:
    """Dependency-aware DAG execution engine for engineering workflows."""

    def __init__(self, service: Any = None, storage: Optional[WorkflowStorageService] = None):
        self.service = service
        self.storage = storage

    def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        workspace_id: Optional[str] = None,
        timeout_s: float = 300.0,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
        cancel_token: Optional[CancellationToken] = None,
    ) -> WorkflowExecutionRecord:
        """Execute a complete workflow DAG deterministically with per-node tracking."""
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid4())
        effective_ws_id = workspace_id or workflow.workspace_id

        # 1. Validation & Topological Sort
        catalog = NodeRegistry.get_port_catalog()
        val_result = validate_workflow(workflow, catalog)
        if not val_result.is_valid:
            err_msg = "; ".join(e.message for e in val_result.errors)
            rec = WorkflowExecutionRecord(
                id=run_id,
                workflow_id=workflow.id,
                workflow_name=workflow.name,
                status=WorkflowStatus.FAILED,
                started_at=start_iso,
                finished_at=datetime.now(timezone.utc).isoformat(),
                duration_s=time.time() - start_time,
                error=f"Validation failed: {err_msg}",
            )
            if self.storage:
                self.storage.record_run(rec)
            return rec

        topological_order = val_result.topological_order
        total_nodes = len(topological_order)
        nodes_map = {n.id: n for n in workflow.nodes}

        # Graph adjacency to propagate skips on failure
        downstream_map: Dict[str, List[str]] = {nid: [] for nid in topological_order}
        for conn in workflow.connections:
            if conn.source_node_id in downstream_map:
                downstream_map[conn.source_node_id].append(conn.target_node_id)

        node_outputs: Dict[str, Dict[str, Any]] = {}
        node_records: Dict[str, NodeExecutionRecord] = {}
        failed_or_skipped_nodes: Set[str] = set()

        overall_status = WorkflowStatus.COMPLETED

        # Context builder
        ws_path = None
        if self.service and hasattr(self.service, "workspace_path") and effective_ws_id:
            try:
                ws_path = str(self.service.workspace_path(effective_ws_id))
            except Exception:
                ws_path = None

        context = ExecutionContext(
            workspace_id=effective_ws_id,
            workspace_path=ws_path,
            product_id=workflow.product_id,
            run_id=run_id,
            service=self.service,
        )

        # 2. Sequential Topological Execution
        for idx, node_id in enumerate(topological_order):
            node_def = nodes_map[node_id]
            node_cls = NodeRegistry.get(node_def.node_type)

            # Check cooperative cancellation
            if cancel_token and cancel_token.is_cancelled:
                overall_status = WorkflowStatus.CANCELLED
                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.CANCELLED,
                    logs=["Workflow cancelled by user."],
                )
                continue

            # Check timeout
            if (time.time() - start_time) > timeout_s:
                overall_status = WorkflowStatus.FAILED
                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.FAILED,
                    error_message=f"Workflow exceeded maximum timeout of {timeout_s}s.",
                )
                failed_or_skipped_nodes.add(node_id)
                continue

            # Check if any dependency failed or was skipped
            incoming_conns = workflow.find_incoming_connections(node_id)
            dep_failed = any(conn.source_node_id in failed_or_skipped_nodes for conn in incoming_conns)
            if dep_failed:
                failed_or_skipped_nodes.add(node_id)
                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.SKIPPED,
                    logs=["Skipped due to upstream dependency failure."],
                )
                if progress_callback:
                    progress_callback(idx + 1, total_nodes, node_id, "SKIPPED")
                continue

            if not node_cls:
                overall_status = WorkflowStatus.FAILED
                failed_or_skipped_nodes.add(node_id)
                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.FAILED,
                    error_message=f"Node type '{node_def.node_type}' is not registered.",
                )
                continue

            # Gather resolved inputs from incoming connections
            resolved_inputs: Dict[str, Any] = {}
            for conn in incoming_conns:
                src_outputs = node_outputs.get(conn.source_node_id, {})
                if conn.source_port in src_outputs:
                    resolved_inputs[conn.target_port] = src_outputs[conn.source_port]

            # Execute Node
            node_instance = node_cls()
            node_start = time.time()
            node_logs: List[str] = [f"Executing node '{node_def.title}' ({node_def.node_type})..."]
            
            if progress_callback:
                progress_callback(idx + 1, total_nodes, node_id, "RUNNING")

            try:
                outputs = node_instance.execute(
                    inputs=resolved_inputs,
                    config=node_def.config,
                    context=context,
                )
                duration = time.time() - node_start
                node_outputs[node_id] = outputs
                node_logs.append(f"Completed in {duration:.3f}s with outputs: {list(outputs.keys())}")

                # Save cached output in node definition
                node_def.cached_output = {k: v if isinstance(v, (int, float, str, bool, list, dict)) else str(v) for k, v in outputs.items()}
                node_def.state = NodeExecutionState.COMPLETED
                node_def.error = None

                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.COMPLETED,
                    started_at=datetime.fromtimestamp(node_start, tz=timezone.utc).isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    duration_s=duration,
                    inputs={k: str(v) for k, v in resolved_inputs.items()},
                    outputs={k: v if isinstance(v, (int, float, str, bool, list, dict)) else str(v) for k, v in outputs.items()},
                    logs=node_logs,
                )
                if progress_callback:
                    progress_callback(idx + 1, total_nodes, node_id, "COMPLETED")

            except Exception as exc:
                duration = time.time() - node_start
                overall_status = WorkflowStatus.FAILED
                failed_or_skipped_nodes.add(node_id)
                node_def.state = NodeExecutionState.FAILED
                node_def.error = str(exc)
                node_logs.append(f"Execution failed: {exc}")

                node_records[node_id] = NodeExecutionRecord(
                    node_id=node_id,
                    node_type=node_def.node_type,
                    category=node_def.category,
                    status=NodeExecutionState.FAILED,
                    started_at=datetime.fromtimestamp(node_start, tz=timezone.utc).isoformat(),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    duration_s=duration,
                    inputs={k: str(v) for k, v in resolved_inputs.items()},
                    error_message=str(exc),
                    logs=node_logs,
                )
                if progress_callback:
                    progress_callback(idx + 1, total_nodes, node_id, "FAILED")

        total_duration = time.time() - start_time
        finished_iso = datetime.now(timezone.utc).isoformat()

        # Generate cryptographic manifest hash
        manifest_summary = {
            "run_id": run_id,
            "workflow_id": workflow.id,
            "status": overall_status.value,
            "duration_s": total_duration,
            "node_count": total_nodes,
            "completed_nodes": sum(1 for r in node_records.values() if r.status == NodeExecutionState.COMPLETED),
        }
        manifest_sha256 = hashlib.sha256(json.dumps(manifest_summary, sort_keys=True).encode("utf-8")).hexdigest()

        exec_record = WorkflowExecutionRecord(
            id=run_id,
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status=overall_status,
            started_at=start_iso,
            finished_at=finished_iso,
            duration_s=total_duration,
            node_records=node_records,
            provenance="Deterministic Studio Workflow Engine",
            manifest_sha256=manifest_sha256,
        )

        if self.storage:
            if not self.storage.get_workflow(workflow.id):
                self.storage.save_workflow(workflow)
            self.storage.record_run(exec_record)

        return exec_record
