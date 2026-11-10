"""Properties panel inspector for configuring selected nodes and viewing execution outputs."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFormLayout, QScrollArea, QFrame, QGroupBox
)

from mendex_core.workflows.contracts import NodeDefinition, NodeExecutionState
from mendex_core.workflows.registry import NodeRegistry


class NodePropertiesPanel(QWidget):
    """Inspector sidebar for viewing/editing configuration and execution results of selected node."""
    config_changed = Signal(str, dict)  # (node_id, config_dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_node: Optional[NodeDefinition] = None
        self._editors: Dict[str, QLineEdit] = {}
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header Title
        self.header_title = QLabel("Node Properties")
        self.header_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #89b4fa;")
        main_layout.addWidget(self.header_title)

        # Scrollable Form Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(12)

        self.scroll.setWidget(self.form_container)
        main_layout.addWidget(self.scroll, 1)

        # Initial Empty State
        self.empty_label = QLabel("Select a node on the canvas to inspect its configuration and outputs.")
        self.empty_label.setStyleSheet("color: #6c7086; font-style: italic;")
        self.empty_label.setWordWrap(True)
        self.form_layout.addWidget(self.empty_label)

    def set_node(self, node: Optional[NodeDefinition]) -> None:
        self.current_node = node
        self._clear_form()

        if not node:
            self.header_title.setText("Node Properties")
            self.form_layout.addWidget(self.empty_label)
            return

        node_cls = NodeRegistry.get(node.node_type)
        self.header_title.setText(f"{node.title} ({node.category.value.capitalize()})")

        # 1. Configuration Section
        cfg_group = QGroupBox("Configuration")
        cfg_form = QFormLayout(cfg_group)
        cfg_form.setSpacing(8)

        # Title Editor
        title_edit = QLineEdit(node.title)
        title_edit.textChanged.connect(self._on_title_changed)
        cfg_form.addRow("Title:", title_edit)

        # Node specific config fields
        if node.node_type == "numeric_input":
            val_edit = QLineEdit(str(node.config.get("value", "0.0")))
            unit_edit = QLineEdit(str(node.config.get("unit", "")))
            val_edit.textChanged.connect(lambda t: self._update_config_key("value", float(t) if t else 0.0))
            unit_edit.textChanged.connect(lambda t: self._update_config_key("unit", t))
            cfg_form.addRow("Value:", val_edit)
            cfg_form.addRow("Unit:", unit_edit)

        elif node.node_type == "formula_evaluation":
            expr_edit = QLineEdit(str(node.config.get("expression", "a + b")))
            unit_edit = QLineEdit(str(node.config.get("unit", "")))
            expr_edit.textChanged.connect(lambda t: self._update_config_key("expression", t))
            unit_edit.textChanged.connect(lambda t: self._update_config_key("unit", t))
            cfg_form.addRow("Expression:", expr_edit)
            cfg_form.addRow("Unit:", unit_edit)

        elif node.node_type == "deterministic_physics":
            fid_edit = QLineEdit(str(node.config.get("formula_id", "skin_depth")))
            fid_edit.textChanged.connect(lambda t: self._update_config_key("formula_id", t))
            cfg_form.addRow("Formula ID:", fid_edit)

        elif node.node_type == "range_validation":
            min_edit = QLineEdit(str(node.config.get("min_val", "0.0")))
            max_edit = QLineEdit(str(node.config.get("max_val", "1.0")))
            chk_edit = QLineEdit(str(node.config.get("check_id", "REQ-01")))
            min_edit.textChanged.connect(lambda t: self._update_config_key("min_val", float(t) if t else 0.0))
            max_edit.textChanged.connect(lambda t: self._update_config_key("max_val", float(t) if t else 1.0))
            chk_edit.textChanged.connect(lambda t: self._update_config_key("check_id", t))
            cfg_form.addRow("Check ID:", chk_edit)
            cfg_form.addRow("Min Limit:", min_edit)
            cfg_form.addRow("Max Limit:", max_edit)

        elif node.node_type == "tolerance_comparison":
            tol_edit = QLineEdit(str(node.config.get("tolerance_pct", "5.0")))
            chk_edit = QLineEdit(str(node.config.get("check_id", "REQ-TOL")))
            tol_edit.textChanged.connect(lambda t: self._update_config_key("tolerance_pct", float(t) if t else 5.0))
            chk_edit.textChanged.connect(lambda t: self._update_config_key("check_id", t))
            cfg_form.addRow("Check ID:", chk_edit)
            cfg_form.addRow("Tolerance %:", tol_edit)

        elif node.node_type == "report_export":
            rep_title = QLineEdit(str(node.config.get("report_title", "Engineering Dossier")))
            rep_title.textChanged.connect(lambda t: self._update_config_key("report_title", t))
            cfg_form.addRow("Report Title:", rep_title)

        else:
            # Generic JSON config editor
            raw_cfg = QLineEdit(json.dumps(node.config))
            raw_cfg.textChanged.connect(self._on_raw_config_changed)
            cfg_form.addRow("Config (JSON):", raw_cfg)

        self.form_layout.addWidget(cfg_group)

        # 2. Execution Status & Outputs Section
        out_group = QGroupBox("Execution State & Outputs")
        out_layout = QVBoxLayout(out_group)

        status_lbl = QLabel(f"Status: <b>{node.state.value}</b>")
        if node.state == NodeExecutionState.COMPLETED:
            status_lbl.setStyleSheet("color: #a6e3a1;")
        elif node.state == NodeExecutionState.FAILED:
            status_lbl.setStyleSheet("color: #f38ba8;")
        out_layout.addWidget(status_lbl)

        if node.error:
            err_box = QTextEdit(node.error)
            err_box.setReadOnly(True)
            err_box.setMaximumHeight(70)
            err_box.setStyleSheet("color: #f38ba8; background-color: #11111b;")
            out_layout.addWidget(err_box)

        if node.cached_output:
            out_box = QTextEdit(json.dumps(node.cached_output, indent=2))
            out_box.setReadOnly(True)
            out_box.setMaximumHeight(160)
            out_layout.addWidget(out_box)

        self.form_layout.addWidget(out_group)
        self.form_layout.addStretch()

    def _clear_form(self) -> None:
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _on_title_changed(self, new_title: str) -> None:
        if self.current_node:
            self.current_node.title = new_title

    def _update_config_key(self, key: str, value: Any) -> None:
        if self.current_node:
            self.current_node.config[key] = value
            self.config_changed.emit(self.current_node.id, self.current_node.config)

    def _on_raw_config_changed(self, text: str) -> None:
        if self.current_node:
            try:
                self.current_node.config = json.loads(text)
                self.config_changed.emit(self.current_node.id, self.current_node.config)
            except Exception:
                pass
