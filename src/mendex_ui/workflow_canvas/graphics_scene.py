"""Interactive QGraphicsScene with grid drawing, wire routing, and port drag connection."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsSceneMouseEvent

from mendex_core.workflows.contracts import (
    WorkflowDefinition, NodeDefinition, ConnectionDefinition
)
from mendex_core.workflows.registry import NodeRegistry
from mendex_core.workflows.types import check_type_compatibility, check_unit_compatibility
from .graphics_items import NodeGraphicsItem, PortGraphicsItem, ConnectionGraphicsItem


class WorkflowScene(QGraphicsScene):
    """Workflow designer canvas supporting grid snapping, interactive wire dragging, and node management."""
    node_selected = Signal(object)  # Emits NodeDefinition or None
    connection_created = Signal(object)  # Emits ConnectionDefinition
    workflow_modified = Signal()

    GRID_SIZE = 16.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-4000, -4000, 8000, 8000)
        self.setBackgroundBrush(QColor("#11111b"))  # Catppuccin Crust

        self.current_workflow: Optional[WorkflowDefinition] = None
        self.node_items: Dict[str, NodeGraphicsItem] = {}
        self.connection_items: Dict[str, ConnectionGraphicsItem] = {}

        # Interactive wire dragging state
        self._dragging_port: Optional[PortGraphicsItem] = None
        self._temp_wire: Optional[QGraphicsPathItem] = None

        self.selectionChanged.connect(self._on_selection_changed)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Draw subtle grid dots
        pen = QPen(QColor("#313244"), 1.0)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % int(self.GRID_SIZE))
        top = int(rect.top()) - (int(rect.top()) % int(self.GRID_SIZE))

        points = []
        for x in range(left, int(rect.right()), int(self.GRID_SIZE)):
            for y in range(top, int(rect.bottom()), int(self.GRID_SIZE)):
                points.append(QPointF(x, y))

        if points:
            painter.drawPoints(points)

    def clear(self) -> None:
        self.node_items.clear()
        self.connection_items.clear()
        super().clear()

    def load_workflow(self, workflow: WorkflowDefinition) -> None:
        """Clear canvas and populate nodes and connections from workflow definition."""
        self.clear()
        self.current_workflow = workflow

        catalog = NodeRegistry.get_port_catalog()

        # Add Nodes
        for node_def in workflow.nodes:
            in_ports, out_ports = catalog.get(node_def.node_type, ([], []))
            item = NodeGraphicsItem(node_def, in_ports, out_ports)
            self.addItem(item)
            self.node_items[node_def.id] = item

        # Add Connections
        for conn_def in workflow.connections:
            self._create_connection_item(conn_def)

    def _create_connection_item(self, conn: ConnectionDefinition) -> Optional[ConnectionGraphicsItem]:
        src_node = self.node_items.get(conn.source_node_id)
        dst_node = self.node_items.get(conn.target_node_id)
        if not src_node or not dst_node:
            return None

        src_port = src_node.port_items_out.get(conn.source_port)
        dst_port = dst_node.port_items_in.get(conn.target_port)
        if not src_port or not dst_port:
            return None

        conn_item = ConnectionGraphicsItem(conn, src_port, dst_port)
        self.addItem(conn_item)
        self.connection_items[conn.id] = conn_item
        return conn_item

    def add_node_to_scene(self, node_type: str, pos: QPointF) -> Optional[NodeGraphicsItem]:
        """Instantiate and place a new node on the canvas."""
        node_cls = NodeRegistry.get(node_type)
        if not node_cls or not self.current_workflow:
            return None

        in_ports = node_cls.get_input_ports()
        out_ports = node_cls.get_output_ports()

        # Snap position to grid
        snapped_x = round(pos.x() / self.GRID_SIZE) * self.GRID_SIZE
        snapped_y = round(pos.y() / self.GRID_SIZE) * self.GRID_SIZE

        node_def = NodeDefinition(
            id=str(uuid4()),
            node_type=node_type,
            category=node_cls.category,
            title=node_cls.title,
            pos_x=snapped_x,
            pos_y=snapped_y,
            config={},
        )
        self.current_workflow.nodes.append(node_def)

        item = NodeGraphicsItem(node_def, in_ports, out_ports)
        self.addItem(item)
        self.node_items[node_def.id] = item
        self.clearSelection()
        item.setSelected(True)
        self.workflow_modified.emit()
        return item

    def delete_selected(self) -> None:
        """Delete currently selected nodes and their attached connection wires."""
        if not self.current_workflow:
            return

        selected = self.selectedItems()
        modified = False

        for item in selected:
            if isinstance(item, NodeGraphicsItem):
                nid = item.node_def.id
                # Remove incoming/outgoing connections
                conns_to_remove = [
                    c for c in self.current_workflow.connections
                    if c.source_node_id == nid or c.target_node_id == nid
                ]
                for c in conns_to_remove:
                    c_item = self.connection_items.pop(c.id, None)
                    if c_item:
                        self.removeItem(c_item)
                    self.current_workflow.connections.remove(c)

                # Remove node item and definition
                self.removeItem(item)
                self.node_items.pop(nid, None)
                self.current_workflow.nodes = [n for n in self.current_workflow.nodes if n.id != nid]
                modified = True

        if modified:
            self.workflow_modified.emit()

    def update_connections_for_node(self, node_id: str) -> None:
        """Update wire paths connected to moved node."""
        if not self.current_workflow:
            return
        for conn in self.current_workflow.connections:
            if conn.source_node_id == node_id or conn.target_node_id == node_id:
                item = self.connection_items.get(conn.id)
                if item:
                    item.update_path()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Check if clicked on a port socket to start dragging a connection wire
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
        if isinstance(item, PortGraphicsItem) and item.is_output:
            self._dragging_port = item
            self._temp_wire = QGraphicsPathItem()
            self._temp_wire.setPen(QPen(QColor("#f9e2af"), 2.0, Qt.DashLine))
            self._temp_wire.setZValue(10)
            self.addItem(self._temp_wire)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging_port and self._temp_wire:
            p1 = self._dragging_port.get_scene_connection_pos()
            p2 = event.scenePos()
            dx = max(40.0, abs(p2.x() - p1.x()) * 0.5)
            path = QPainterPath(p1)
            path.cubicTo(QPointF(p1.x() + dx, p1.y()), QPointF(p2.x() - dx, p2.y()), p2)
            self._temp_wire.setPath(path)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._dragging_port and self._temp_wire:
            # Drop target check
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
            if isinstance(item, PortGraphicsItem) and not item.is_output:
                src_port = self._dragging_port
                dst_port = item

                # Validation checks: different node, type compatibility
                if src_port.parent_node.node_def.id != dst_port.parent_node.node_def.id:
                    if check_type_compatibility(src_port.port_def.data_type, dst_port.port_def.data_type):
                        conn = ConnectionDefinition(
                            source_node_id=src_port.parent_node.node_def.id,
                            source_port=src_port.port_def.name,
                            target_node_id=dst_port.parent_node.node_def.id,
                            target_port=dst_port.port_def.name,
                        )
                        if self.current_workflow:
                            self.current_workflow.connections.append(conn)
                            self._create_connection_item(conn)
                            self.connection_created.emit(conn)
                            self.workflow_modified.emit()

            # Clean up temporary dragging wire
            self.removeItem(self._temp_wire)
            self._temp_wire = None
            self._dragging_port = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _on_selection_changed(self) -> None:
        selected = self.selectedItems()
        if selected and isinstance(selected[0], NodeGraphicsItem):
            self.node_selected.emit(selected[0].node_def)
        else:
            self.node_selected.emit(None)
