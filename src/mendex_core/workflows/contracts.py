"""Contracts and schemas for visual workflow definitions, nodes, and executions."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .types import PortDefinition, PortDataType


class NodeExecutionState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NodeCategory(str, Enum):
    INPUT = "input"
    CALCULATION = "calculation"
    TOOL = "tool"
    RESULTS = "results"
    VALIDATION = "validation"
    REPORTING = "reporting"
    INTELLIGENCE = "intelligence"


class ConnectionDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str


class NodeDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    node_type: str
    category: NodeCategory
    title: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    config: Dict[str, Any] = Field(default_factory=dict)
    state: NodeExecutionState = NodeExecutionState.PENDING
    cached_output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowDefinition(BaseModel):
    schema_version: str = "1.9.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = "Untitled Workflow"
    description: str = ""
    version: int = 1
    workspace_id: Optional[str] = None
    product_id: Optional[str] = None
    nodes: List[NodeDefinition] = Field(default_factory=list)
    connections: List[ConnectionDefinition] = Field(default_factory=list)
    canvas_viewport: Dict[str, float] = Field(default_factory=lambda: {"zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0})
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_node(self, node_id: str) -> Optional[NodeDefinition]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def find_incoming_connections(self, node_id: str) -> List[ConnectionDefinition]:
        return [c for c in self.connections if c.target_node_id == node_id]

    def find_outgoing_connections(self, node_id: str) -> List[ConnectionDefinition]:
        return [c for c in self.connections if c.source_node_id == node_id]


class NodeExecutionRecord(BaseModel):
    node_id: str
    node_type: str
    category: NodeCategory
    status: NodeExecutionState
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_s: float = 0.0
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class WorkflowExecutionRecord(BaseModel):
    schema_version: str = "1.9.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
    duration_s: float = 0.0
    node_records: Dict[str, NodeExecutionRecord] = Field(default_factory=dict)
    provenance: str = "Deterministic Studio Workflow Engine"
    manifest_sha256: Optional[str] = None
    error: Optional[str] = None
