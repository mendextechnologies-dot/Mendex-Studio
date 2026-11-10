"""Custom QGraphicsView with smooth pan, zoom, rubberband drag, and shortcuts."""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QGraphicsView

from .graphics_scene import WorkflowScene


class WorkflowGraphicsView(QGraphicsView):
    """Viewport for visual workflow canvas with hardware acceleration, pan, and zoom."""

    def __init__(self, scene: WorkflowScene, parent=None):
        super().__init__(scene, parent)
        self.workflow_scene = scene

        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self._panning = False
        self._pan_start = QPoint()
        self._zoom_factor = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in/out with mouse wheel."""
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        
        # Clamp zoom limits
        new_zoom = self._zoom_factor * factor
        if 0.2 <= new_zoom <= 3.0:
            self._zoom_factor = new_zoom
            self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle mouse button or Alt+Left for canvas panning
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.workflow_scene.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def zoom_in(self) -> None:
        if self._zoom_factor < 3.0:
            self._zoom_factor *= 1.2
            self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        if self._zoom_factor > 0.2:
            self._zoom_factor /= 1.2
            self.scale(1.0 / 1.2, 1.0 / 1.2)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom_factor = 1.0

    def fit_all(self) -> None:
        """Center and fit all active nodes in the viewport."""
        items_rect = self.scene().itemsBoundingRect()
        if not items_rect.isEmpty():
            self.fitInView(items_rect.adjusted(-50, -50, 50, 50), Qt.KeepAspectRatio)
            self._zoom_factor = self.transform().m11()
