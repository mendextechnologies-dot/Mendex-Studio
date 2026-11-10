"""Full-featured visual engineering Workflow Studio panel for Mendex Engineering Studio."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from PySide6.QtCore import Qt, QPointF, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QSplitter, QTreeWidget, QTreeWidgetItem, QProgressBar, QTextEdit,
    QMessageBox, QFileDialog, QTabWidget, QFrame, QLineEdit
)

from mendex_core.service import StudioService
from mendex_core.workflows.contracts import (
    WorkflowDefinition, NodeDefinition, ConnectionDefinition,
    NodeCategory, WorkflowStatus, NodeExecutionState
)
from mendex_core.workflows.registry import NodeRegistry
from mendex_core.workflows.engine import WorkflowExecutionEngine, CancellationToken
from ..waveform_viewer import WaveformViewerWidget
from .graphics_scene import WorkflowScene
from .graphics_view import WorkflowGraphicsView
from .properties_panel import NodePropertiesPanel


class WorkflowExecutionWorker(QObject):
    """Background worker thread executing workflow DAG without blocking Qt UI."""
    finished = Signal(object)  # Emits WorkflowExecutionRecord
    progress = Signal(int, int, str, str)  # (current, total, node_id, status)
    error = Signal(str)

    def __init__(self, engine: WorkflowExecutionEngine, workflow: WorkflowDefinition, workspace_id: Optional[str], cancel_token: CancellationToken):
        super().__init__()
        self.engine = engine
        self.workflow = workflow
        self.workspace_id = workspace_id
        self.cancel_token = cancel_token

    def run(self) -> None:
        try:
            record = self.engine.execute_workflow(
                workflow=self.workflow,
                workspace_id=self.workspace_id,
                timeout_s=300.0,
                progress_callback=lambda cur, tot, nid, st: self.progress.emit(cur, tot, nid, st),
                cancel_token=self.cancel_token,
            )
            self.finished.emit(record)
        except Exception as exc:
            self.error.emit(str(exc))


class WorkflowStudioPanel(QWidget):
    """Primary Workflow Studio engineering interface."""

    def __init__(self, service: StudioService, parent=None):
        super().__init__(parent)
        self.service = service
        self.current_workflow: Optional[WorkflowDefinition] = None
        self.current_workspace_id: Optional[str] = None
        self._cancel_token: Optional[CancellationToken] = None
        self._thread: Optional[QThread] = None

        self.init_ui()
        self.load_initial_workflow()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Top Control & Action Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        lbl_wf = QLabel("Workflow:")
        lbl_wf.setStyleSheet("font-weight: 600; color: #a6adc8;")
        top_bar.addWidget(lbl_wf)

        self.wf_selector = QComboBox()
        self.wf_selector.setMinimumWidth(220)
        self.wf_selector.currentIndexChanged.connect(self._on_workflow_selected)
        top_bar.addWidget(self.wf_selector)

        self.btn_new = QPushButton("+ New")
        self.btn_new.clicked.connect(self.new_workflow)
        top_bar.addWidget(self.btn_new)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_workflow)
        top_bar.addWidget(self.btn_save)

        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.clicked.connect(self.duplicate_workflow)
        top_bar.addWidget(self.btn_duplicate)

        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "Load Template...",
            "1. Calculation & Validation",
            "2. Simulation & Analysis",
            "3. Evidence & Reporting",
        ])
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        top_bar.addWidget(self.template_combo)

        top_bar.addStretch()

        # Canvas Controls
        btn_fit = QPushButton("Fit")
        btn_fit.clicked.connect(lambda: self.view.fit_all())
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.clicked.connect(lambda: self.view.zoom_in())
        btn_zoom_out = QPushButton("-")
        btn_zoom_out.clicked.connect(lambda: self.view.zoom_out())
        top_bar.addWidget(btn_fit)
        top_bar.addWidget(btn_zoom_in)
        top_bar.addWidget(btn_zoom_out)

        # Run / Cancel Controls
        self.btn_run = QPushButton("▶ Run Workflow")
        self.btn_run.setStyleSheet("background-color: #1e4a38; color: #a6e3a1; font-weight: 700; padding: 6px 14px;")
        self.btn_run.clicked.connect(self.run_workflow)
        top_bar.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("■ Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("background-color: #4a1e28; color: #f38ba8; font-weight: 700; padding: 6px 14px;")
        self.btn_cancel.clicked.connect(self.cancel_workflow)
        top_bar.addWidget(self.btn_cancel)

        main_layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #181825; border: none; } QProgressBar::chunk { background-color: #89b4fa; }")
        main_layout.addWidget(self.progress_bar)

        # 2. Main Workspace Splitter (Left: Library, Center: Canvas, Right: Inspector)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Node Library Palette
        lib_box = QFrame()
        lib_box.setFixedWidth(230)
        lib_box.setObjectName("node_library")
        lib_layout = QVBoxLayout(lib_box)
        lib_layout.setContentsMargins(0, 0, 0, 0)
        lib_layout.setSpacing(6)

        lib_title = QLabel("Node Library")
        lib_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #cdd6f4; padding: 8px;")
        lib_layout.addWidget(lib_title)

        self.search_node = QLineEdit()
        self.search_node.setPlaceholderText("Filter nodes...")
        self.search_node.textChanged.connect(self._filter_library)
        lib_layout.addWidget(self.search_node)

        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderHidden(True)
        self.node_tree.itemDoubleClicked.connect(self._on_library_item_double_clicked)
        lib_layout.addWidget(self.node_tree, 1)

        self._populate_node_library()
        splitter.addWidget(lib_box)

        # Center: Canvas
        self.scene = WorkflowScene()
        self.view = WorkflowGraphicsView(self.scene)
        splitter.addWidget(self.view)

        # Right: Tabbed Inspector (Properties, Logs, Waveforms)
        self.right_tabs = QTabWidget()
        self.right_tabs.setMinimumWidth(320)

        self.properties_panel = NodePropertiesPanel()
        self.right_tabs.addTab(self.properties_panel, "Properties")

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #11111b; color: #a6adc8; font-family: 'Consolas', monospace; font-size: 11px;")
        self.right_tabs.addTab(self.log_output, "Run Log")

        self.waveform_widget = WaveformViewerWidget()
        self.right_tabs.addTab(self.waveform_widget, "Waveforms")

        splitter.addWidget(self.right_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter, 1)

        # Connect scene signals
        self.scene.node_selected.connect(self.properties_panel.set_node)
        self.scene.workflow_modified.connect(self._on_canvas_modified)

    def _populate_node_library(self) -> None:
        self.node_tree.clear()
        categories = {
            NodeCategory.INPUT: "1. Inputs",
            NodeCategory.CALCULATION: "2. Calculations",
            NodeCategory.TOOL: "3. Solvers & Tools",
            NodeCategory.RESULTS: "4. Results",
            NodeCategory.VALIDATION: "5. Validation",
            NodeCategory.REPORTING: "6. Reporting",
            NodeCategory.INTELLIGENCE: "7. Intelligence",
        }

        cat_items = {}
        for cat, label in categories.items():
            item = QTreeWidgetItem([label])
            item.setExpanded(True)
            self.node_tree.addTopLevelItem(item)
            cat_items[cat] = item

        for node_cls in NodeRegistry.list_nodes():
            parent_item = cat_items.get(node_cls.category)
            if parent_item:
                child = QTreeWidgetItem([node_cls.title])
                child.setData(0, Qt.UserRole, node_cls.node_type)
                parent_item.addChild(child)

    def _filter_library(self, text: str) -> None:
        text = text.lower()
        for i in range(self.node_tree.topLevelItemCount()):
            top = self.node_tree.topLevelItem(i)
            has_visible_child = False
            for j in range(top.childCount()):
                child = top.child(j)
                match = text in child.text(0).lower()
                child.setHidden(not match)
                if match:
                    has_visible_child = True
            top.setHidden(not has_visible_child and bool(text))

    def _on_library_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        node_type = item.data(0, Qt.UserRole)
        if node_type:
            # Place in center of current view
            center = self.view.mapToScene(self.view.viewport().rect().center())
            self.scene.add_node_to_scene(node_type, center)

    def load_initial_workflow(self) -> None:
        wfs = self.service.workflows.list_workflows()
        self.wf_selector.clear()
        for wf in wfs:
            self.wf_selector.addItem(wf.name, wf.id)

        if wfs:
            self.load_workflow_by_id(wfs[0].id)
        else:
            self.load_template(1)

    def load_workflow_by_id(self, wf_id: str) -> None:
        wf = self.service.workflows.get_workflow(wf_id)
        if wf:
            self.current_workflow = wf
            self.scene.load_workflow(wf)
            self.log_output.append(f"Loaded workflow '{wf.name}' (v{wf.version}).")
            self.view.fit_all()

    def new_workflow(self) -> None:
        wf = WorkflowDefinition(
            name=f"Workflow {len(self.service.workflows.list_workflows()) + 1}",
            workspace_id=self.current_workspace_id,
        )
        saved = self.service.workflows.save_workflow(wf)
        self.wf_selector.addItem(saved.name, saved.id)
        self.wf_selector.setCurrentIndex(self.wf_selector.count() - 1)

    def save_workflow(self) -> None:
        if self.current_workflow:
            self.service.workflows.save_workflow(self.current_workflow)
            self.log_output.append(f"Workflow '{self.current_workflow.name}' saved successfully.")

    def duplicate_workflow(self) -> None:
        if self.current_workflow:
            dup = self.service.workflows.duplicate_workflow(self.current_workflow.id)
            if dup:
                self.wf_selector.addItem(dup.name, dup.id)
                self.wf_selector.setCurrentIndex(self.wf_selector.count() - 1)

    def run_workflow(self) -> None:
        if not self.current_workflow:
            return

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        self.log_output.append(f"Starting execution of workflow '{self.current_workflow.name}'...")

        self._cancel_token = CancellationToken()
        self._thread = QThread()
        self._worker = WorkflowExecutionWorker(
            engine=self.service.workflow_engine,
            workflow=self.current_workflow,
            workspace_id=self.current_workspace_id,
            cancel_token=self._cancel_token,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_run_progress)
        self._worker.finished.connect(self._on_run_finished)
        self._worker.error.connect(self._on_run_error)

        self._thread.start()

    def cancel_workflow(self) -> None:
        if self._cancel_token:
            self._cancel_token.cancel()
            self.log_output.append("Cancellation signal dispatched...")

    def _on_run_progress(self, current: int, total: int, node_id: str, status: str) -> None:
        pct = int((current / total) * 100) if total else 0
        self.progress_bar.setValue(pct)
        self.log_output.append(f"[{current}/{total}] Node {node_id[:8]} -> {status}")
        # Refresh visual node card
        item = self.scene.node_items.get(node_id)
        if item:
            item.node_def.state = NodeExecutionState(status)
            item.update()

    def _on_run_finished(self, record) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log_output.append(f"Workflow finished with status: {record.status.value} in {record.duration_s:.3f}s")
        self.log_output.append(f"Manifest SHA256: {record.manifest_sha256}")

        # Update properties panel
        if self.properties_panel.current_node:
            self.properties_panel.set_node(self.properties_panel.current_node)

        # Plot waveforms if simulation results exist
        for rec in record.node_records.values():
            if rec.outputs and "waveform" in rec.outputs:
                wf_data = rec.outputs["waveform"]
                if isinstance(wf_data, dict) and "signals" in wf_data:
                    t = wf_data.get("time", [])
                    sigs = wf_data.get("signals", {})
                    if t and sigs:
                        self.waveform_widget.set_waveform(t, sigs)
                        self.right_tabs.setCurrentIndex(2)

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def _on_run_error(self, err_msg: str) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log_output.append(f"Workflow Execution Error: {err_msg}")
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def _on_workflow_selected(self, idx: int) -> None:
        if idx >= 0:
            wf_id = self.wf_selector.itemData(idx)
            if wf_id and (not self.current_workflow or self.current_workflow.id != wf_id):
                self.load_workflow_by_id(wf_id)

    def _on_canvas_modified(self) -> None:
        pass

    def _on_template_selected(self, idx: int) -> None:
        if idx > 0:
            self.load_template(idx)
            self.template_combo.setCurrentIndex(0)

    def load_template(self, template_num: int) -> None:
        """Instantiate pre-configured generic engineering workflow templates."""
        if template_num == 1:
            # 1. Calculation & Validation
            wf = WorkflowDefinition(
                name="Template: Dowell Factor Calculation & Validation",
                workspace_id=self.current_workspace_id,
            )
            n1 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Winding Layers", pos_x=40, pos_y=80, config={"value": 2.0})
            n2 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Height/Delta Ratio", pos_x=40, pos_y=200, config={"value": 1.0})
            n3 = NodeDefinition(node_type="deterministic_physics", category=NodeCategory.CALCULATION, title="Dowell Factor", pos_x=320, pos_y=120, config={"formula_id": "dowell_factor"})
            n4 = NodeDefinition(node_type="range_validation", category=NodeCategory.VALIDATION, title="AC Resistance Check", pos_x=600, pos_y=120, config={"min_val": 1.0, "max_val": 2.5, "check_id": "REQ-DOWELL"})
            n5 = NodeDefinition(node_type="report_export", category=NodeCategory.REPORTING, title="Export Dossier", pos_x=880, pos_y=120)

            wf.nodes = [n1, n2, n3, n4, n5]
            wf.connections = [
                ConnectionDefinition(source_node_id=n1.id, source_port="value", target_node_id=n3.id, target_port="param1"),
                ConnectionDefinition(source_node_id=n2.id, source_port="value", target_node_id=n3.id, target_port="param2"),
                ConnectionDefinition(source_node_id=n3.id, source_port="result", target_node_id=n4.id, target_port="value_in"),
            ]
        elif template_num == 2:
            # 2. Simulation & Analysis
            wf = WorkflowDefinition(
                name="Template: LTspice Transient Analysis",
                workspace_id=self.current_workspace_id,
            )
            n1 = NodeDefinition(node_type="text_input", category=NodeCategory.INPUT, title="Netlist", pos_x=40, pos_y=100, config={"text": "* RC Circuit\nV1 1 0 PULSE(0 10 0 1n 1n 10u 20u)\nR1 1 2 1k\nC1 2 0 100n\n.tran 0 50u 0 100n\n.end\n"})
            n2 = NodeDefinition(node_type="ltspice_simulation", category=NodeCategory.TOOL, title="LTspice Solver", pos_x=320, pos_y=100)
            n3 = NodeDefinition(node_type="waveform_extract", category=NodeCategory.RESULTS, title="Extract V(out)", pos_x=600, pos_y=100, config={"signal_name": "V(out)"})
            n4 = NodeDefinition(node_type="numerical_summary", category=NodeCategory.CALCULATION, title="Signal Metrics", pos_x=860, pos_y=100)
            wf.nodes = [n1, n2, n3, n4]
            wf.connections = [
                ConnectionDefinition(source_node_id=n1.id, source_port="text", target_node_id=n2.id, target_port="netlist_text"),
                ConnectionDefinition(source_node_id=n2.id, source_port="waveform", target_node_id=n3.id, target_port="waveform_in"),
                ConnectionDefinition(source_node_id=n3.id, source_port="signal_vector", target_node_id=n4.id, target_port="signal"),
            ]
        else:
            # 3. Evidence & Reporting
            wf = WorkflowDefinition(
                name="Template: Multi-Check Evidence Dossier",
                workspace_id=self.current_workspace_id,
            )
            n1 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Measured Voltage", pos_x=40, pos_y=80, config={"value": 24.2, "unit": "V"})
            n2 = NodeDefinition(node_type="tolerance_comparison", category=NodeCategory.VALIDATION, title="Voltage Regulation", pos_x=320, pos_y=80, config={"target": 24.0, "tolerance_pct": 2.0, "check_id": "REQ-VOUT"})
            n3 = NodeDefinition(node_type="evidence_aggregation", category=NodeCategory.REPORTING, title="Sealed Evidence", pos_x=600, pos_y=80)
            n4 = NodeDefinition(node_type="report_export", category=NodeCategory.REPORTING, title="Generate Dossier", pos_x=860, pos_y=80)
            wf.nodes = [n1, n2, n3, n4]
            wf.connections = [
                ConnectionDefinition(source_node_id=n1.id, source_port="value", target_node_id=n2.id, target_port="actual"),
                ConnectionDefinition(source_node_id=n2.id, source_port="validation_result", target_node_id=n3.id, target_port="check1"),
                ConnectionDefinition(source_node_id=n3.id, source_port="manifest", target_node_id=n4.id, target_port="manifest"),
            ]

        saved = self.service.workflows.save_workflow(wf)
        self.current_workflow = saved
        self.wf_selector.addItem(saved.name, saved.id)
        self.wf_selector.setCurrentIndex(self.wf_selector.count() - 1)
        self.scene.load_workflow(saved)
        self.view.fit_all()
