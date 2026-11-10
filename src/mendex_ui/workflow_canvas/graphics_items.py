"""PySide6 QGraphicsItem implementations for visual workflow nodes, ports, and wires."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QLinearGradient
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, QMenu
)

from mendex_core.workflows.contracts import (
    NodeDefinition, ConnectionDefinition, NodeCategory, NodeExecutionState
)
from mendex_core.workflows.types import PortDefinition, PortDataType


CATEGORY_COLORS = {
    NodeCategory.INPUT: QColor("#89b4fa"),       # Blue
    NodeCategory.CALCULATION: QColor("#cba6f7"), # Mauve
    NodeCategory.TOOL: QColor("#fab387"),        # Peach
    NodeCategory.RESULTS: QColor("#a6e3a1"),     # Green
    NodeCategory.VALIDATION: QColor("#f9e2af"),  # Yellow
    NodeCategory.REPORTING: QColor("#94e2d5"),   # Teal
    NodeCategory.INTELLIGENCE: QColor("#f38ba8"),# Coral
}

PORT_COLORS = {
    PortDataType.SCALAR: QColor("#89b4fa"),
    PortDataType.QUANTITY: QColor("#89dceb"),
    PortDataType.BOOLEAN: QColor("#cba6f7"),
    PortDataType.STRING: QColor("#f5c2e7"),
    PortDataType.VECTOR: QColor("#a6e3a1"),
    PortDataType.TIME_SERIES: QColor("#a6e3a1"),
    PortDataType.FILE_REF: QColor("#fab387"),
    PortDataType.DATASET_REF: QColor("#fab387"),
    PortDataType.SIM_RESULT: QColor("#94e2d5"),
    PortDataType.ARTIFACT: QColor("#f2cdcd"),
    PortDataType.VALIDATION_RESULT: QColor("#f9e2af"),
    PortDataType.ANY: QColor("#bac2de"),
}

STATUS_COLORS = {
    NodeExecutionState.PENDING: QColor("#45475a"),
    NodeExecutionState.RUNNING: QColor("#f9e2af"),
    NodeExecutionState.COMPLETED: QColor("#a6e3a1"),
    NodeExecutionState.FAILED: QColor("#f38ba8"),
    NodeExecutionState.SKIPPED: QColor("#585b70"),
    NodeExecutionState.CANCELLED: QColor("#6c7086"),
}


class PortGraphicsItem(QGraphicsItem):
    """Circular socket representing an input or output port."""
    RADIUS = 6.0

    def __init__(self, port_def: PortDefinition, is_output: bool, parent_node: NodeGraphicsItem):
        super().__init__(parent_node)
        self.port_def = port_def
        self.is_output = is_output
        self.parent_node = parent_node
        self.setAcceptHoverEvents(True)
        self._hovered = False

    def boundingRect(self) -> QRectF:
        r = self.RADIUS + 3.0
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        c = PORT_COLORS.get(self.port_def.data_type, QColor("#bac2de"))
        
        if self._hovered:
            painter.setPen(QPen(QColor("#ffffff"), 2.0))
            painter.setBrush(QBrush(c.lighter(130)))
        else:
            painter.setPen(QPen(QColor("#11111b"), 1.5))
            painter.setBrush(QBrush(c))

        painter.drawEllipse(QPointF(0, 0), self.RADIUS, self.RADIUS)

    def hoverEnterEvent(self, event: Any) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def get_scene_connection_pos(self) -> QPointF:
        """Returns connection anchor point in scene coordinates."""
        return self.mapToScene(QPointF(0, 0))


class ConnectionGraphicsItem(QGraphicsPathItem):
    """Cubic bezier curve connecting an output port to an input port."""

    def __init__(self, conn_def: ConnectionDefinition, source_port_item: PortGraphicsItem, target_port_item: PortGraphicsItem):
        super().__init__()
        self.conn_def = conn_def
        self.source_port_item = source_port_item
        self.target_port_item = target_port_item
        self.setZValue(-1)  # Wires sit behind nodes
        self.setPen(QPen(QColor("#89dceb"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.update_path()

    def update_path(self) -> None:
        p1 = self.source_port_item.get_scene_connection_pos()
        p2 = self.target_port_item.get_scene_connection_pos()

        dx = max(40.0, abs(p2.x() - p1.x()) * 0.5)
        ctrl1 = QPointF(p1.x() + dx, p1.y())
        ctrl2 = QPointF(p2.x() - dx, p2.y())

        path = QPainterPath(p1)
        path.cubicTo(ctrl1, ctrl2, p2)
        self.setPath(path)


class NodeGraphicsItem(QGraphicsItem):
    """Draggable, selectable visual card representing an engineering node."""
    WIDTH = 210.0
    HEADER_HEIGHT = 32.0
    ROW_HEIGHT = 22.0

    def __init__(self, node_def: NodeDefinition, input_ports: List[PortDefinition], output_ports: List[PortDefinition]):
        super().__init__()
        self.node_def = node_def
        self.input_ports = input_ports
        self.output_ports = output_ports

        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setPos(node_def.pos_x, node_def.pos_y)

        # Compute height
        max_rows = max(len(input_ports), len(output_ports), 1)
        self.height = self.HEADER_HEIGHT + (max_rows * self.ROW_HEIGHT) + 14.0

        # Create port items
        self.port_items_in: Dict[str, PortGraphicsItem] = {}
        self.port_items_out: Dict[str, PortGraphicsItem] = {}
        self._build_ports()

    def _build_ports(self) -> None:
        # Input ports on left edge
        y_offset = self.HEADER_HEIGHT + 14.0
        for p in self.input_ports:
            item = PortGraphicsItem(p, is_output=False, parent_node=self)
            item.setPos(0, y_offset)
            self.port_items_in[p.name] = item
            y_offset += self.ROW_HEIGHT

        # Output ports on right edge
        y_offset = self.HEADER_HEIGHT + 14.0
        for p in self.output_ports:
            item = PortGraphicsItem(p, is_output=True, parent_node=self)
            item.setPos(self.WIDTH, y_offset)
            self.port_items_out[p.name] = item
            y_offset += self.ROW_HEIGHT

    def boundingRect(self) -> QRectF:
        margin = 6.0
        return QRectF(-margin, -margin, self.WIDTH + 2 * margin, self.height + 2 * margin)

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)

        # Body background
        body_rect = QRectF(0, 0, self.WIDTH, self.height)
        painter.setBrush(QBrush(QColor("#181825")))
        
        # Border style based on status and selection
        status_color = STATUS_COLORS.get(self.node_def.state, QColor("#45475a"))
        if self.isSelected():
            painter.setPen(QPen(QColor("#89b4fa"), 2.5))
        else:
            painter.setPen(QPen(status_color, 1.8))

        painter.drawRoundedRect(body_rect, 8.0, 8.0)

        # Header bar
        header_path = QPainterPath()
        header_path.addRoundedRect(QRectF(0, 0, self.WIDTH, self.HEADER_HEIGHT), 8.0, 8.0)
        # Flatten bottom corners of header
        header_clip = QRectF(0, 0, self.WIDTH, self.HEADER_HEIGHT)
        cat_color = CATEGORY_COLORS.get(self.node_def.category, QColor("#89b4fa"))
        painter.fillPath(header_path, QBrush(cat_color.darker(150)))

        # Header accent stripe
        painter.fillRect(QRectF(0, self.HEADER_HEIGHT - 2, self.WIDTH, 2), cat_color)

        # Header Title Text
        painter.setPen(QColor("#ffffff"))
        f = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(10, 0, self.WIDTH - 20, self.HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignLeft, self.node_def.title)

        # Port Labels
        painter.setFont(QFont("Segoe UI", 8))
        for p in self.input_ports:
            item = self.port_items_in.get(p.name)
            if item:
                py = item.pos().y()
                painter.setPen(QColor("#a6adc8"))
                painter.drawText(QRectF(14, py - 10, self.WIDTH / 2 - 16, 20), Qt.AlignVCenter | Qt.AlignLeft, p.display_name)

        for p in self.output_ports:
            item = self.port_items_out.get(p.name)
            if item:
                py = item.pos().y()
                painter.setPen(QColor("#cdd6f4"))
                painter.drawText(QRectF(self.WIDTH / 2, py - 10, self.WIDTH / 2 - 14, 20), Qt.AlignVCenter | Qt.AlignRight, p.display_name)

        # Status badge dot on top right
        painter.setBrush(QBrush(status_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self.WIDTH - 12, 16), 4.5, 4.5)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.ItemPositionHasChanged:
            pos = self.pos()
            self.node_def.pos_x = pos.x()
            self.node_def.pos_y = pos.y()
            # Update connected wires
            scene = self.scene()
            if scene and hasattr(scene, "update_connections_for_node"):
                scene.update_connections_for_node(self.node_def.id)
        return super().itemChange(change, value)
