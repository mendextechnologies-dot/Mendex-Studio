"""Automated UI tests for v1.9 WorkflowStudioPanel and visual canvas."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_ui.workflow_canvas import WorkflowStudioPanel, WorkflowScene, NodeGraphicsItem


def test_workflow_studio_ui_initialization(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = WorkflowStudioPanel(service)
    panel.show()
    app.processEvents()

    # Verify node library populated
    assert panel.node_tree.topLevelItemCount() == 7  # 7 categories
    assert panel.wf_selector.count() >= 1

    # Verify canvas scene initialized
    assert panel.scene is not None
    assert panel.view is not None
    assert panel.properties_panel is not None

    panel.close()


def test_canvas_add_node_and_connect(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = WorkflowStudioPanel(service)
    panel.show()
    app.processEvents()

    # Clear current
    panel.scene.clear()
    panel.current_workflow.nodes.clear()
    panel.current_workflow.connections.clear()

    # Add NumericInput and RangeValidation nodes
    n1_item = panel.scene.add_node_to_scene("numeric_input", QPointF(50, 50))
    n2_item = panel.scene.add_node_to_scene("range_validation", QPointF(350, 50))

    assert n1_item is not None
    assert n2_item is not None
    assert len(panel.scene.node_items) == 2

    # Select node and verify properties panel update
    panel.scene.clearSelection()
    n1_item.setSelected(True)
    app.processEvents()
    assert panel.properties_panel.current_node.id == n1_item.node_def.id

    # Test template loading
    panel.load_template(1)
    app.processEvents()
    assert len(panel.scene.node_items) == 5
    assert len(panel.current_workflow.connections) == 3

    panel.close()
