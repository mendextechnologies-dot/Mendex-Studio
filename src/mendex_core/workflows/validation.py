"""Workflow topology validation, cycle detection, and port compatibility checker."""
from __future__ import annotations

from typing import Dict, List, Set, Tuple, Optional
from pydantic import BaseModel

from .contracts import WorkflowDefinition, NodeDefinition, ConnectionDefinition
from .types import PortDefinition, check_type_compatibility, check_unit_compatibility


class WorkflowValidationError(BaseModel):
    node_id: Optional[str] = None
    port_name: Optional[str] = None
    severity: str = "ERROR"  # ERROR or WARNING
    message: str


class WorkflowValidationResult(BaseModel):
    is_valid: bool
    errors: List[WorkflowValidationError] = []
    warnings: List[WorkflowValidationError] = []
    topological_order: List[str] = []


def detect_cycles_and_toposort(nodes: List[NodeDefinition], connections: List[ConnectionDefinition]) -> Tuple[List[str], Optional[List[str]]]:
    """Detect cycles and return (topological_order, cycle_node_ids).
    
    Uses Kahn's algorithm (indegree tracking).
    """
    node_ids = [n.id for n in nodes]
    in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}

    for conn in connections:
        src = conn.source_node_id
        dst = conn.target_node_id
        if src in adj and dst in in_degree:
            adj[src].append(dst)
            in_degree[dst] += 1

    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    topological_order: List[str] = []

    while queue:
        # Deterministic ordering by node ID/type
        curr = queue.pop(0)
        topological_order.append(curr)

        for neighbor in adj.get(curr, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topological_order) != len(node_ids):
        # Cycle detected! Collect nodes involved in cycle
        cycle_nodes = [nid for nid in node_ids if nid not in topological_order]
        return [], cycle_nodes

    return topological_order, None


def validate_workflow(
    workflow: WorkflowDefinition,
    node_port_catalog: Dict[str, Tuple[List[PortDefinition], List[PortDefinition]]]
) -> WorkflowValidationResult:
    """Validate full workflow: cycle detection, required ports, type and unit compatibility."""
    errors: List[WorkflowValidationError] = []
    warnings: List[WorkflowValidationError] = []

    if not workflow.nodes:
        warnings.append(WorkflowValidationError(message="Workflow contains no nodes."))
        return WorkflowValidationResult(is_valid=True, errors=errors, warnings=warnings, topological_order=[])

    # 1. Cycle detection & Topological Sort
    topological_order, cycle_nodes = detect_cycles_and_toposort(workflow.nodes, workflow.connections)
    if cycle_nodes:
        errors.append(WorkflowValidationError(
            message=f"Directed cycle detected involving nodes: {', '.join(cycle_nodes)}. Workflows must be Directed Acyclic Graphs (DAGs)."
        ))

    # 2. Connection Validation
    nodes_map = {n.id: n for n in workflow.nodes}
    target_ports_connected: Dict[Tuple[str, str], str] = {}  # (target_node_id, target_port) -> source_node_id

    for conn in workflow.connections:
        src_node = nodes_map.get(conn.source_node_id)
        dst_node = nodes_map.get(conn.target_node_id)

        if not src_node:
            errors.append(WorkflowValidationError(
                message=f"Connection references nonexistent source node {conn.source_node_id}."
            ))
            continue
        if not dst_node:
            errors.append(WorkflowValidationError(
                message=f"Connection references nonexistent target node {conn.target_node_id}."
            ))
            continue

        src_ports = node_port_catalog.get(src_node.node_type, ([], []))[1]  # outputs
        dst_ports = node_port_catalog.get(dst_node.node_type, ([], []))[0]  # inputs

        src_port_def = next((p for p in src_ports if p.name == conn.source_port), None)
        dst_port_def = next((p for p in dst_ports if p.name == conn.target_port), None)

        if not src_port_def:
            errors.append(WorkflowValidationError(
                node_id=src_node.id,
                port_name=conn.source_port,
                message=f"Source node '{src_node.title}' has no output port named '{conn.source_port}'."
            ))
            continue
        if not dst_port_def:
            errors.append(WorkflowValidationError(
                node_id=dst_node.id,
                port_name=conn.target_port,
                message=f"Target node '{dst_node.title}' has no input port named '{conn.target_port}'."
            ))
            continue

        # Prevent multiple incoming connections to single target port
        target_key = (dst_node.id, dst_port_def.name)
        if target_key in target_ports_connected:
            errors.append(WorkflowValidationError(
                node_id=dst_node.id,
                port_name=dst_port_def.name,
                message=f"Port '{dst_port_def.display_name}' on node '{dst_node.title}' already has an incoming connection."
            ))
        else:
            target_ports_connected[target_key] = src_node.id

        # Type Compatibility Check
        if not check_type_compatibility(src_port_def.data_type, dst_port_def.data_type):
            errors.append(WorkflowValidationError(
                node_id=dst_node.id,
                port_name=dst_port_def.name,
                message=(
                    f"Incompatible types: '{src_node.title}.{src_port_def.display_name}' ({src_port_def.data_type.value}) "
                    f"cannot connect to '{dst_node.title}.{dst_port_def.display_name}' ({dst_port_def.data_type.value})."
                )
            ))

        # Unit Compatibility Check
        if not check_unit_compatibility(src_port_def.unit, dst_port_def.unit):
            warnings.append(WorkflowValidationError(
                node_id=dst_node.id,
                port_name=dst_port_def.name,
                severity="WARNING",
                message=(
                    f"Unit dimension mismatch: '{src_port_def.display_name}' ({src_port_def.unit}) "
                    f"vs '{dst_port_def.display_name}' ({dst_port_def.unit}). Conversion may be required."
                )
            ))

    # 3. Required Input Verification
    for node in workflow.nodes:
        in_ports = node_port_catalog.get(node.node_type, ([], []))[0]
        for p in in_ports:
            if p.required:
                is_connected = (node.id, p.name) in target_ports_connected
                has_configured_value = p.name in node.config and node.config[p.name] is not None
                if not is_connected and not has_configured_value and p.default_value is None:
                    errors.append(WorkflowValidationError(
                        node_id=node.id,
                        port_name=p.name,
                        message=f"Required input '{p.display_name}' on node '{node.title}' is not connected and has no value."
                    ))

    is_valid = len(errors) == 0
    return WorkflowValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        topological_order=topological_order if is_valid else []
    )
