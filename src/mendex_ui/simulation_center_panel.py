"""Simulation Center Panel for Mendex Engineering Studio v2.1.

Combines headless simulation dispatch, execution logs, and interactive waveform inspection
with non-blocking asynchronous execution.
"""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget
)

from mendex_core.controller import MendexEngineeringController
from .waveform_viewer import WaveformViewerWidget


class SimulationWorker(QThread):
    """Background worker executing industrial simulations without blocking the UI thread."""
    simulation_finished = Signal(dict)
    simulation_error = Signal(str)

    def __init__(self, controller: MendexEngineeringController, workspace_id: str, tool: str, duration_s: float):
        super().__init__()
        self.controller = controller
        self.workspace_id = workspace_id
        self.tool = tool
        self.duration_s = duration_s

    def run(self):
        try:
            res = self.controller.run_simulation(
                workspace_id=self.workspace_id,
                tool=self.tool,
                duration_s=self.duration_s,
            )
            self.simulation_finished.emit(res)
        except Exception as exc:
            self.simulation_error.emit(str(exc))


class SimulationCenterPanel(QWidget):
    """Central industrial simulation hub with execution controls and waveform visualizer."""

    def __init__(self, service, guarded_callback=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.controller = MendexEngineeringController(service.root)
        self.guarded = guarded_callback or (lambda fn: fn())
        self._worker: Optional[SimulationWorker] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Top Controls Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 10px;")
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setSpacing(12)

        bar_layout.addWidget(QLabel("Target Project:"))
        self.combo_ws = QComboBox()
        self.combo_ws.setMinimumWidth(180)
        self._refresh_workspaces()
        bar_layout.addWidget(self.combo_ws)

        bar_layout.addWidget(QLabel("Solver:"))
        self.combo_solver = QComboBox()
        self.combo_solver.addItems(["LTspice (Transient)", "FEMM (Magnetics)"])
        bar_layout.addWidget(self.combo_solver)

        bar_layout.addWidget(QLabel("Duration (ms):"))
        self.txt_duration = QLineEdit("2.0")
        self.txt_duration.setMaximumWidth(60)
        bar_layout.addWidget(self.txt_duration)

        self.btn_run_sim = QPushButton("⚡ Execute Simulation")
        self.btn_run_sim.setStyleSheet(
            "background-color: #a6e3a1; color: #11111b; font-weight: 700; padding: 6px 16px; border-radius: 4px;"
        )
        self.btn_run_sim.clicked.connect(self._run_simulation)
        bar_layout.addWidget(self.btn_run_sim)

        btn_open_raw = QPushButton("📂 Open .RAW File")
        btn_open_raw.setStyleSheet(
            "background-color: #313244; color: #cdd6f4; font-weight: 600; padding: 6px 12px; border-radius: 4px;"
        )
        btn_open_raw.clicked.connect(self._open_custom_raw)
        bar_layout.addWidget(btn_open_raw)

        bar_layout.addStretch()
        layout.addWidget(top_bar)

        # 2. Main Content Splitter: Waveform Viewer & Execution Logs
        splitter = QSplitter(Qt.Vertical)

        # Top: Interactive Waveform Viewer
        self.waveform_viewer = WaveformViewerWidget()
        splitter.addWidget(self.waveform_viewer)

        # Bottom: Logs and Metrics Tabs
        tabs = QTabWidget()
        tabs.setMaximumHeight(220)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #11111b; color: #a6adc8; font-family: monospace; font-size: 11px;")
        tabs.addTab(self.txt_logs, "📋 Solver Logs & Output")

        self.txt_metrics = QTextEdit()
        self.txt_metrics.setReadOnly(True)
        self.txt_metrics.setStyleSheet("background-color: #11111b; color: #89b4fa; font-family: monospace; font-size: 11px;")
        tabs.addTab(self.txt_metrics, "📊 Steady-State Metrics")

        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _refresh_workspaces(self):
        self.combo_ws.clear()
        try:
            ws_list = self.controller.list_workspaces()
            for ws in ws_list:
                ws_id = ws.get("workspace_id")
                name = ws.get("name", ws_id)
                self.combo_ws.addItem(f"{name} ({ws_id[:8]}...)", ws_id)
        except Exception:
            self.combo_ws.addItem("Default Project", "default")

    def _run_simulation(self):
        ws_id = self.combo_ws.currentData() or "default"
        solver = "ltspice" if "LTspice" in self.combo_solver.currentText() else "femm"
        try:
            dur_ms = float(self.txt_duration.text().strip())
            dur_s = dur_ms / 1000.0
        except ValueError:
            dur_s = 0.002

        self.btn_run_sim.setEnabled(False)
        self.btn_run_sim.setText("⏳ Simulating...")
        self.txt_logs.append(f"Starting {solver.upper()} simulation asynchronously on workspace '{ws_id}'...")

        self._worker = SimulationWorker(self.controller, ws_id, solver, dur_s)
        self._worker.simulation_finished.connect(self._on_simulation_finished)
        self._worker.simulation_error.connect(self._on_simulation_error)
        self._worker.start()

    def _on_simulation_finished(self, res: dict):
        self.btn_run_sim.setEnabled(True)
        self.btn_run_sim.setText("⚡ Execute Simulation")
        self.txt_logs.append(f"Status: {res.get('status')} (Exit code: {res.get('exit_code', 0)})")
        if res.get("raw_file"):
            raw_path = self.service.root / res["raw_file"]
            if raw_path.exists():
                self.txt_logs.append(f"Loading waveform: {raw_path.name}")
                self.waveform_viewer.load_raw_file(raw_path)
        if res.get("steady_state_metrics"):
            self.txt_metrics.setPlainText(json.dumps(res["steady_state_metrics"], indent=2))

    def _on_simulation_error(self, err_msg: str):
        self.btn_run_sim.setEnabled(True)
        self.btn_run_sim.setText("⚡ Execute Simulation")
        self.txt_logs.append(f"Simulation error: {err_msg}")
        QMessageBox.warning(self, "Simulation Note", err_msg)

    def _open_custom_raw(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open SPICE Waveform (.raw)", str(self.service.root), "SPICE Waveform (*.raw)")
        if path:
            self.waveform_viewer.load_raw_file(Path(path))
            self.txt_logs.append(f"Opened waveform: {Path(path).name}")
