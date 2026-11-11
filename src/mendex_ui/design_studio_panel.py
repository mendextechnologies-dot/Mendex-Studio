"""Engineering Design Studio & Specification-Driven Design Creation Panel.

Provides:
- NewEngineeringDesignDialog: Interactive technical specification input and design synthesis wizard.
- EngineeringDesignStudioPanel: Full engineering workspace to inspect calculations, run simulations,
  inspect waveforms, launch native tools (LTspice, KiCad, FreeCAD, FEMM), and execute closed-loop AI iteration.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mendex_core.design.models import (
    EngineeringDesign,
    DesignRevision,
    DesignCandidate,
    Requirement,
    DesignStatus,
)
from mendex_core.launch import open_native, launch_tool
from .waveform_viewer import WaveformViewerWidget


class NewEngineeringDesignDialog(QDialog):
    """Wizard dialog to enter technical specifications and synthesize a new engineering design."""

    design_created = Signal(str)  # Emits design_id

    def __init__(self, service, current_workspace_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.current_workspace_id = current_workspace_id
        self.created_design: Optional[EngineeringDesign] = None

        self.setWindowTitle("New Engineering Design — Specification-to-Design Wizard")
        self.resize(720, 680)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 10px;")
        h_layout = QVBoxLayout(header)
        h_title = QLabel("⚙ Specification-Driven Engineering Design Generation")
        h_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #89b4fa;")
        h_desc = QLabel(
            "Enter electrical operating parameters. Mendex Studio will automatically synthesize candidate "
            "topologies, calculate analytical component values, and generate editable native circuit & CAD artifacts."
        )
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        h_layout.addWidget(h_title)
        h_layout.addWidget(h_desc)
        layout.addWidget(header)

        # Presets bar
        presets_box = QHBoxLayout()
        presets_box.addWidget(QLabel("Reference Presets:"))
        btn_preset_buck = QPushButton("Buck 20W (24V→5V, 4A)")
        btn_preset_buck.clicked.connect(self._apply_buck_preset)
        presets_box.addWidget(btn_preset_buck)

        btn_preset_flyback = QPushButton("Flyback 36W (24V→12V, Isolated)")
        btn_preset_flyback.clicked.connect(self._apply_flyback_preset)
        presets_box.addWidget(btn_preset_flyback)

        btn_preset_pushpull = QPushButton("Push-Pull 100W (48V→24V)")
        btn_preset_pushpull.clicked.connect(self._apply_pushpull_preset)
        presets_box.addWidget(btn_preset_pushpull)
        presets_box.addStretch()
        layout.addLayout(presets_box)

        # Form Layout
        form_group = QGroupBox("Design Metadata & Technical Requirements")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(8)

        self.txt_title = QLineEdit("Synchronous Buck Converter 20W")
        form_layout.addRow("Design Title:", self.txt_title)

        self.combo_workspace = QComboBox()
        self._populate_workspaces()
        form_layout.addRow("Target Workspace:", self.combo_workspace)

        self.combo_category = QComboBox()
        self.combo_category.addItems([
            "dc_dc_converter (Non-isolated Step-down / Step-up)",
            "isolated_dc_dc (Isolated Flyback / Forward)",
            "inverter (Push-Pull / Half-Bridge Inverter)",
        ])
        form_layout.addRow("Converter Category:", self.combo_category)

        # Technical Grid
        grid_group = QGroupBox("Electrical Specifications (SI Units)")
        grid_layout = QGridLayout(grid_group)
        grid_layout.setSpacing(10)

        grid_layout.addWidget(QLabel("Nominal Input Voltage Vin (V):"), 0, 0)
        self.txt_vin = QLineEdit("24.0")
        grid_layout.addWidget(self.txt_vin, 0, 1)

        grid_layout.addWidget(QLabel("Min Input Vin_min (V):"), 0, 2)
        self.txt_vin_min = QLineEdit("18.0")
        grid_layout.addWidget(self.txt_vin_min, 0, 3)

        grid_layout.addWidget(QLabel("Max Input Vin_max (V):"), 1, 2)
        self.txt_vin_max = QLineEdit("32.0")
        grid_layout.addWidget(self.txt_vin_max, 1, 3)

        grid_layout.addWidget(QLabel("Regulated Output Vout (V):"), 1, 0)
        self.txt_vout = QLineEdit("5.0")
        grid_layout.addWidget(self.txt_vout, 1, 1)

        grid_layout.addWidget(QLabel("Rated Output Current Iout (A):"), 2, 0)
        self.txt_iout = QLineEdit("4.0")
        grid_layout.addWidget(self.txt_iout, 2, 1)

        grid_layout.addWidget(QLabel("Switching Frequency (kHz):"), 2, 2)
        self.txt_fsw = QLineEdit("100.0")
        grid_layout.addWidget(self.txt_fsw, 2, 3)

        grid_layout.addWidget(QLabel("Max Output Ripple ΔVout (mV):"), 3, 0)
        self.txt_ripple = QLineEdit("50.0")
        grid_layout.addWidget(self.txt_ripple, 3, 1)

        self.chk_isolated = QCheckBox("Galvanic Isolation Required")
        self.chk_isolated.stateChanged.connect(self._on_isolated_toggle)
        grid_layout.addWidget(self.chk_isolated, 3, 2)

        self.txt_iso_v = QLineEdit("1500.0")
        self.txt_iso_v.setEnabled(False)
        grid_layout.addWidget(self.txt_iso_v, 3, 3)

        layout.addWidget(form_group)
        layout.addWidget(grid_group)

        # Validation feedback
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setStyleSheet("color: #f38ba8; font-weight: 600;")
        layout.addWidget(self.lbl_feedback)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()

        self.btn_generate = QPushButton("⚡ Synthesize & Generate Engineering Design")
        self.btn_generate.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: 700; font-size: 13px; padding: 8px 16px; border-radius: 4px;"
        )
        self.btn_generate.clicked.connect(self._synthesize_design)
        btn_row.addWidget(self.btn_generate)
        layout.addLayout(btn_row)

    def _populate_workspaces(self):
        self.combo_workspace.clear()
        try:
            ws_list = self.service.integrations.list_workspaces()
            for ws in ws_list:
                ws_id = ws.get("workspace_id", "")
                ws_name = ws.get("name", ws_id)
                self.combo_workspace.addItem(f"{ws_name} ({ws_id[:8]}...)", ws_id)
            if self.current_workspace_id:
                for i in range(self.combo_workspace.count()):
                    if self.combo_workspace.itemData(i) == self.current_workspace_id:
                        self.combo_workspace.setCurrentIndex(i)
                        break
        except Exception:
            self.combo_workspace.addItem("Default Workspace", "default")

    def _apply_buck_preset(self):
        self.txt_title.setText("Synchronous Buck Converter 20W")
        self.combo_category.setCurrentIndex(0)
        self.txt_vin.setText("24.0")
        self.txt_vin_min.setText("18.0")
        self.txt_vin_max.setText("32.0")
        self.txt_vout.setText("5.0")
        self.txt_iout.setText("4.0")
        self.txt_fsw.setText("100.0")
        self.txt_ripple.setText("50.0")
        self.chk_isolated.setChecked(False)

    def _apply_flyback_preset(self):
        self.txt_title.setText("Isolated Offline Flyback 36W")
        self.combo_category.setCurrentIndex(1)
        self.txt_vin.setText("24.0")
        self.txt_vin_min.setText("18.0")
        self.txt_vin_max.setText("36.0")
        self.txt_vout.setText("12.0")
        self.txt_iout.setText("3.0")
        self.txt_fsw.setText("65.0")
        self.txt_ripple.setText("80.0")
        self.chk_isolated.setChecked(True)
        self.txt_iso_v.setText("1500.0")

    def _apply_pushpull_preset(self):
        self.txt_title.setText("Push-Pull Inverter 100W")
        self.combo_category.setCurrentIndex(2)
        self.txt_vin.setText("48.0")
        self.txt_vin_min.setText("36.0")
        self.txt_vin_max.setText("60.0")
        self.txt_vout.setText("24.0")
        self.txt_iout.setText("4.2")
        self.txt_fsw.setText("80.0")
        self.txt_ripple.setText("100.0")
        self.chk_isolated.setChecked(True)
        self.txt_iso_v.setText("2000.0")

    def _on_isolated_toggle(self, state):
        self.txt_iso_v.setEnabled(bool(state))

    def _validate_inputs(self) -> Optional[List[Requirement]]:
        try:
            vin = float(self.txt_vin.text().strip())
            vin_min = float(self.txt_vin_min.text().strip())
            vin_max = float(self.txt_vin_max.text().strip())
            vout = float(self.txt_vout.text().strip())
            iout = float(self.txt_iout.text().strip())
            fsw_khz = float(self.txt_fsw.text().strip())
            ripple_mv = float(self.txt_ripple.text().strip())

            if vin <= 0 or vout <= 0 or iout <= 0 or fsw_khz <= 0 or ripple_mv <= 0:
                self.lbl_feedback.setText("Error: Electrical parameters must be positive non-zero numbers.")
                return None
            if not (vin_min <= vin <= vin_max):
                self.lbl_feedback.setText("Warning: Vin must be between Vin_min and Vin_max.")
                return None

            reqs = [
                Requirement(parameter="vin_nom", target_value=vin, unit="V", min_value=vin_min, max_value=vin_max),
                Requirement(parameter="vout", target_value=vout, unit="V", tolerance_pct=5.0),
                Requirement(parameter="iout", target_value=iout, unit="A"),
                Requirement(parameter="fsw", target_value=fsw_khz * 1000.0, unit="Hz"),
                Requirement(parameter="ripple", target_value=ripple_mv / 1000.0, max_value=ripple_mv / 1000.0, unit="V"),
            ]
            if self.chk_isolated.isChecked():
                iso_v = float(self.txt_iso_v.text().strip() or "1500.0")
                reqs.append(Requirement(parameter="isolation_v", target_value=iso_v, unit="V"))

            self.lbl_feedback.setText("")
            return reqs
        except ValueError as exc:
            self.lbl_feedback.setText(f"Invalid input: Please enter valid numerical values ({exc})")
            return None

    def _synthesize_design(self):
        reqs = self._validate_inputs()
        if not reqs:
            return

        ws_id = self.combo_workspace.currentData() or "default"
        title = self.txt_title.text().strip() or "Untitled Engineering Design"
        cat_key = self.combo_category.currentText().split()[0]

        try:
            design = self.service.design.create_design_from_requirements(
                workspace_id=ws_id,
                title=title,
                category=cat_key,
                requirements=reqs,
            )
            # Automatically generate native artifacts
            ws_path = self.service.root / "workspaces" / ws_id
            ws_path.mkdir(parents=True, exist_ok=True)
            self.service.design.generate_native_artifacts(design.id, ws_path)

            self.created_design = design
            self.design_created.emit(design.id)
            QMessageBox.information(
                self,
                "Design Synthesized Successfully",
                f"Engineering Design '{title}' created!\n\n"
                f"• Top Candidate: {design.get_active_revision().topology if design.get_active_revision() else 'Synthesized'}\n"
                f"• Generated Artifacts: SPICE netlist (.net), graphical schematic (.asc), KiCad project (.kicad_sch), PCB (.kicad_pcb).\n\n"
                "Navigating to Design Studio workspace.",
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Synthesis Error", f"Could not synthesize engineering design:\n\n{exc}")


class EngineeringDesignStudioPanel(QWidget):
    """Full enterprise workspace panel to inspect, simulate, iterate, and export engineering designs."""

    def __init__(self, service, guarded, parent=None):
        super().__init__(parent)
        self.service = service
        self.guarded = guarded
        self.current_design_id: Optional[str] = None
        self.current_design: Optional[EngineeringDesign] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top Control Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 8px 12px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel("Design:"))
        self.combo_designs = QComboBox()
        self.combo_designs.setMinimumWidth(260)
        self.combo_designs.currentIndexChanged.connect(self._on_design_selected)
        tb_layout.addWidget(self.combo_designs)

        btn_new_design = QPushButton("➕ New Engineering Design")
        btn_new_design.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: 700; padding: 5px 12px;")
        btn_new_design.clicked.connect(self.open_new_design_dialog)
        tb_layout.addWidget(btn_new_design)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.refresh_designs)
        tb_layout.addWidget(btn_refresh)

        tb_layout.addStretch()

        self.lbl_topology_badge = QLabel("TOPOLOGY: —")
        self.lbl_topology_badge.setStyleSheet("background-color: #1e3a5f; color: #89b4fa; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;")
        tb_layout.addWidget(self.lbl_topology_badge)

        self.lbl_status_badge = QLabel("STATUS: —")
        self.lbl_status_badge.setStyleSheet("background-color: #1c3b2b; color: #a6e3a1; padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;")
        tb_layout.addWidget(self.lbl_status_badge)

        layout.addWidget(top_bar)

        # Quick Tool Actions Bar
        actions_bar = QHBoxLayout()
        self.btn_open_ltspice = QPushButton("📐 Open in LTspice")
        self.btn_open_ltspice.setStyleSheet("font-weight: 700; color: #89b4fa;")
        self.btn_open_ltspice.clicked.connect(lambda: self._open_tool_for_design("ltspice"))
        actions_bar.addWidget(self.btn_open_ltspice)

        self.btn_open_kicad_sch = QPushButton("🔌 Open Schematic in KiCad")
        self.btn_open_kicad_sch.setStyleSheet("font-weight: 700; color: #a6e3a1;")
        self.btn_open_kicad_sch.clicked.connect(lambda: self._open_tool_for_design("kicad_sch"))
        actions_bar.addWidget(self.btn_open_kicad_sch)

        self.btn_open_kicad_pcb = QPushButton("🟩 Open PCB in KiCad")
        self.btn_open_kicad_pcb.setStyleSheet("font-weight: 700; color: #f9e2af;")
        self.btn_open_kicad_pcb.clicked.connect(lambda: self._open_tool_for_design("kicad_pcb"))
        actions_bar.addWidget(self.btn_open_kicad_pcb)

        self.btn_open_freecad = QPushButton("🧊 Open 3D CAD in FreeCAD")
        self.btn_open_freecad.setStyleSheet("font-weight: 700; color: #cba6f7;")
        self.btn_open_freecad.clicked.connect(lambda: self._open_tool_for_design("freecad"))
        actions_bar.addWidget(self.btn_open_freecad)

        self.btn_run_sim = QPushButton("⚡ Execute LTspice Simulation")
        self.btn_run_sim.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: 800; padding: 6px 14px;")
        self.btn_run_sim.clicked.connect(self._run_simulation)
        actions_bar.addWidget(self.btn_run_sim)

        actions_bar.addStretch()
        layout.addLayout(actions_bar)

        # Main Workspace Tab View
        self.tabs = QTabWidget()

        # Tab 1: Architecture & Sizing Calculations
        self.tab_calc = QWidget()
        self._init_calc_tab()
        self.tabs.addTab(self.tab_calc, "Architecture & Calculations")

        # Tab 2: Simulation & Waveforms
        self.tab_sim = QWidget()
        self._init_sim_tab()
        self.tabs.addTab(self.tab_sim, "Simulation & Waveforms")

        # Tab 3: AI Copilot Closed-Loop Iteration
        self.tab_ai = QWidget()
        self._init_ai_tab()
        self.tabs.addTab(self.tab_ai, "AI Copilot Iteration")

        # Tab 4: Native Engineering Artifacts
        self.tab_artifacts = QWidget()
        self._init_artifacts_tab()
        self.tabs.addTab(self.tab_artifacts, "Native Artifacts")

        layout.addWidget(self.tabs, 1)

        self.refresh_designs()

    # -------------------------------------------------------------------------
    # Tab 1: Calculations
    # -------------------------------------------------------------------------
    def _init_calc_tab(self):
        layout = QVBoxLayout(self.tab_calc)
        split = QSplitter(Qt.Horizontal)

        # Left: Component sizing table
        left_box = QWidget()
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.addWidget(QLabel("Synthesized Components & Sizing Values:"))
        self.table_comps = QTableWidget(0, 4)
        self.table_comps.setHorizontalHeaderLabels(["Designator", "Type", "Calculated Value", "Footprint / Model"])
        self.table_comps.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l_layout.addWidget(self.table_comps)
        split.addWidget(left_box)

        # Right: Parameters & Candidate Ranking
        right_box = QWidget()
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.addWidget(QLabel("Operating Parameters & Topology Analysis:"))
        self.txt_calc_details = QTextEdit()
        self.txt_calc_details.setReadOnly(True)
        self.txt_calc_details.setFont(QFont("Consolas", 10))
        r_layout.addWidget(self.txt_calc_details)
        split.addWidget(right_box)

        layout.addWidget(split)

    # -------------------------------------------------------------------------
    # Tab 2: Simulation & Waveforms
    # -------------------------------------------------------------------------
    def _init_sim_tab(self):
        layout = QVBoxLayout(self.tab_sim)
        self.waveform_viewer = WaveformViewerWidget()
        layout.addWidget(self.waveform_viewer, 1)

        # Metrics bar below waveform
        self.txt_sim_metrics = QTextEdit()
        self.txt_sim_metrics.setReadOnly(True)
        self.txt_sim_metrics.setMaximumHeight(140)
        self.txt_sim_metrics.setFont(QFont("Consolas", 10))
        layout.addWidget(self.txt_sim_metrics)

    # -------------------------------------------------------------------------
    # Tab 3: AI Copilot Iteration
    # -------------------------------------------------------------------------
    def _init_ai_tab(self):
        layout = QVBoxLayout(self.tab_ai)
        layout.setSpacing(12)

        self.ai_status_banner = QFrame()
        self.ai_status_banner.setStyleSheet("background-color: #181825; border: 1px solid #45475a; border-radius: 6px; padding: 12px;")
        ai_b_layout = QVBoxLayout(self.ai_status_banner)
        self.lbl_ai_title = QLabel("AI Engineering Copilot — Closed-Loop Optimizer")
        self.lbl_ai_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #89b4fa;")
        self.lbl_ai_desc = QLabel("Simulate design to evaluate requirements and receive analytical sizing proposals.")
        self.lbl_ai_desc.setWordWrap(True)
        self.lbl_ai_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        ai_b_layout.addWidget(self.lbl_ai_title)
        ai_b_layout.addWidget(self.lbl_ai_desc)
        layout.addWidget(self.ai_status_banner)

        self.txt_ai_proposal = QTextEdit()
        self.txt_ai_proposal.setReadOnly(True)
        self.txt_ai_proposal.setFont(QFont("Consolas", 10))
        layout.addWidget(self.txt_ai_proposal, 1)

        ai_actions = QHBoxLayout()
        self.btn_apply_proposal = QPushButton("✅ Approve Proposal & Branch Revision 2")
        self.btn_apply_proposal.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: 700; padding: 8px 16px; border-radius: 4px;")
        self.btn_apply_proposal.setEnabled(False)
        self.btn_apply_proposal.clicked.connect(self._apply_ai_proposal)
        ai_actions.addWidget(self.btn_apply_proposal)
        ai_actions.addStretch()
        layout.addLayout(ai_actions)

        self.current_proposal = None

    # -------------------------------------------------------------------------
    # Tab 4: Native Artifacts
    # -------------------------------------------------------------------------
    def _init_artifacts_tab(self):
        layout = QVBoxLayout(self.tab_artifacts)
        self.table_artifacts = QTableWidget(0, 5)
        self.table_artifacts.setHorizontalHeaderLabels(["Artifact Name", "Format", "Path", "SHA-256", "Open Native Tool"])
        self.table_artifacts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_artifacts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_artifacts.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_artifacts.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_artifacts.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table_artifacts)

    # -------------------------------------------------------------------------
    # Design Operations
    # -------------------------------------------------------------------------
    def refresh_designs(self):
        self.combo_designs.blockSignals(True)
        self.combo_designs.clear()
        designs = self.service.design.list_designs()
        for d in designs:
            self.combo_designs.addItem(f"{d.title} ({d.id[:8]}...)", d.id)
        self.combo_designs.blockSignals(False)

        if self.combo_designs.count() > 0:
            if not self.current_design_id or self.combo_designs.findData(self.current_design_id) == -1:
                self.combo_designs.setCurrentIndex(0)
            else:
                idx = self.combo_designs.findData(self.current_design_id)
                self.combo_designs.setCurrentIndex(idx)
            self._load_design(self.combo_designs.currentData())
        else:
            self._clear_view()

    def open_new_design_dialog(self):
        dlg = NewEngineeringDesignDialog(self.service, parent=self)
        dlg.design_created.connect(self._on_new_design_created)
        dlg.exec()

    def _on_new_design_created(self, design_id: str):
        self.current_design_id = design_id
        self.refresh_designs()

    def _on_design_selected(self, idx: int):
        if idx >= 0:
            d_id = self.combo_designs.itemData(idx)
            self._load_design(d_id)

    def _clear_view(self):
        self.current_design = None
        self.lbl_topology_badge.setText("TOPOLOGY: —")
        self.lbl_status_badge.setText("STATUS: —")
        self.table_comps.setRowCount(0)
        self.txt_calc_details.clear()
        self.txt_sim_metrics.clear()
        self.txt_ai_proposal.clear()
        self.table_artifacts.setRowCount(0)

    def _load_design(self, design_id: str):
        self.current_design_id = design_id
        design = self.service.design.get_design(design_id)
        self.current_design = design
        if not design:
            self._clear_view()
            return

        active_rev = design.get_active_revision()
        topo = active_rev.topology if active_rev else "UNSPECIFIED"
        status = design.status.value if hasattr(design.status, "value") else str(design.status)

        self.lbl_topology_badge.setText(f"TOPOLOGY: {topo.upper()}")
        self.lbl_status_badge.setText(f"STATUS: {status}")

        # Populate calculations table
        if active_rev and active_rev.ir:
            ir = active_rev.ir
            self.table_comps.setRowCount(len(ir.components))
            for i, c in enumerate(ir.components):
                self.table_comps.setItem(i, 0, QTableWidgetItem(c.designator))
                self.table_comps.setItem(i, 1, QTableWidgetItem(c.type.value if hasattr(c.type, "value") else str(c.type)))
                val_str = f"{c.value:.6g} {c.unit}".strip()
                self.table_comps.setItem(i, 2, QTableWidgetItem(val_str))
                self.table_comps.setItem(i, 3, QTableWidgetItem(c.spice_model or c.footprint or "—"))

            calc_text = [
                f"Design: {design.title}",
                f"Active Revision: {active_rev.label} (Index {active_rev.revision_index})",
                f"Topology: {ir.topology}",
                "",
                "Operating Parameters:",
            ]
            for p_name, p in ir.parameters.items():
                calc_text.append(f"  • {p_name} ({p.description or p_name}): {p.value:.6g} {p.unit}")

            if design.candidates:
                calc_text.extend(["", "Synthesized Topology Candidates:"])
                for cand in design.candidates:
                    calc_text.append(f"  • {cand.topology_name} (Score: {cand.score:.2f}) — Status: {cand.status.value}")
                    calc_text.append(f"    Rationale: {cand.rationale}")

            self.txt_calc_details.setPlainText("\n".join(calc_text))

            # Populate artifacts table
            self.table_artifacts.setRowCount(len(active_rev.artifacts))
            for i, art in enumerate(active_rev.artifacts):
                self.table_artifacts.setItem(i, 0, QTableWidgetItem(art.name))
                self.table_artifacts.setItem(i, 1, QTableWidgetItem(art.format))
                self.table_artifacts.setItem(i, 2, QTableWidgetItem(art.path))
                self.table_artifacts.setItem(i, 3, QTableWidgetItem(art.sha256[:12] + "..."))

                btn_open = QPushButton("Open Tool")
                btn_open.clicked.connect(lambda checked=False, p=art.path: self._open_artifact_path(p))
                self.table_artifacts.setCellWidget(i, 4, btn_open)

    def _open_artifact_path(self, rel_path: str):
        full_p = self.service.root / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
        try:
            open_native(full_p)
        except Exception as exc:
            QMessageBox.critical(self, "Tool Handoff Error", f"Could not launch native tool for {full_p.name}:\n\n{exc}")

    def _open_tool_for_design(self, tool_key: str):
        if not self.current_design or not self.current_design.get_active_revision():
            QMessageBox.warning(self, "No Active Design", "Please select or create an engineering design first.")
            return

        rev = self.current_design.get_active_revision()
        target_art = None
        for art in rev.artifacts:
            path_lower = art.path.lower()
            if tool_key == "ltspice" and (path_lower.endswith(".asc") or path_lower.endswith(".net")):
                target_art = art
                if path_lower.endswith(".asc"):
                    break  # Prefer graphical schematic
            elif tool_key == "kicad_sch" and path_lower.endswith(".kicad_sch"):
                target_art = art
                break
            elif tool_key == "kicad_pcb" and path_lower.endswith(".kicad_pcb"):
                target_art = art
                break
            elif tool_key == "freecad" and (path_lower.endswith(".step") or path_lower.endswith(".stp")):
                target_art = art
                break

        if not target_art:
            reply = QMessageBox.question(
                self,
                "Artifact Required",
                f"The required {tool_key.upper()} input artifact has not been generated yet for this design.\n\n"
                f"Would you like Mendex Studio to compile and generate native artifacts from current specifications now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                ws_path = self.service.root / "workspaces" / self.current_design.workspace_id
                ws_path.mkdir(parents=True, exist_ok=True)
                self.service.design.generate_native_artifacts(self.current_design.id, ws_path)
                self._load_design(self.current_design.id)
                rev = self.current_design.get_active_revision()
                for art in rev.artifacts:
                    path_lower = art.path.lower()
                    if tool_key == "ltspice" and (path_lower.endswith(".asc") or path_lower.endswith(".net")):
                        target_art = art
                        if path_lower.endswith(".asc"):
                            break
                    elif tool_key == "kicad_sch" and path_lower.endswith(".kicad_sch"):
                        target_art = art
                        break
                    elif tool_key == "kicad_pcb" and path_lower.endswith(".kicad_pcb"):
                        target_art = art
                        break
                    elif tool_key == "freecad" and (path_lower.endswith(".step") or path_lower.endswith(".stp")):
                        target_art = art
                        break

        if target_art:
            self._open_artifact_path(target_art.path)
        else:
            QMessageBox.warning(self, "Artifact Not Found", f"No generated {tool_key.upper()} artifact could be found for this design.")

    def _run_simulation(self):
        if not self.current_design:
            return
        ws_path = self.service.root / "workspaces" / self.current_design.workspace_id
        try:
            res = self.service.design.run_ltspice_simulation(self.current_design.id, ws_path)
            self.tabs.setCurrentIndex(1)  # Switch to Simulation & Waveforms tab

            # Plot waveforms in embedded viewer
            if res.time_trace and res.vout_trace:
                self.waveform_viewer.load_simulation_traces(
                    res.time_trace,
                    res.vout_trace,
                    channel_name="V(Vout)",
                    channel_unit="V",
                )

            metrics_lines = [
                f"LTspice Simulation Status: {res.convergence_status} (Exit code: {res.exit_code})",
                f"Elapsed Solver Time: {res.elapsed_time_s:.3f} s",
                f"Mean Output Voltage: {res.vout_mean_v:.3f} V",
                f"Peak-to-Peak Ripple: {res.vout_ripple_pk_pk_v * 1000.0:.1f} mV",
                "",
                "Requirements Graded:",
            ]
            for req_name, verdict in res.requirements_evaluated.items():
                metrics_lines.append(f"  • {req_name.upper()}: {verdict}")
            self.txt_sim_metrics.setPlainText("\n".join(metrics_lines))

            # Propose AI design iteration
            proposal = self.service.design.propose_iteration(self.current_design.id, res)
            if proposal:
                self.current_proposal = proposal
                self.txt_ai_proposal.setPlainText(
                    f"Requirement Violation Detected:\n  {proposal.target_requirement}\n"
                    f"Observed Metric: {proposal.observed_metric:.4g} vs Threshold: {proposal.required_metric:.4g}\n\n"
                    f"AI Copilot Analytical Recommendation:\n"
                    f"  • Parameter to Adjust: {proposal.parameter_to_change}\n"
                    f"  • Current Value: {proposal.current_value:.6g} {proposal.unit}\n"
                    f"  • Proposed Value: {proposal.proposed_value:.6g} {proposal.unit}\n\n"
                    f"Engineering Rationale:\n{proposal.rationale}\n\n"
                    f"Trade-Off Analysis:\n{proposal.trade_offs}\n"
                )
                self.btn_apply_proposal.setEnabled(True)
                self.lbl_ai_desc.setText(f"Optimization proposal ready for {proposal.parameter_to_change}. Engineer approval required.")
            else:
                self.txt_ai_proposal.setPlainText("✅ All engineering requirements are satisfied in current revision. No iteration needed.")
                self.btn_apply_proposal.setEnabled(False)
                self.lbl_ai_desc.setText("Design meets all technical specifications.")

        except Exception as exc:
            QMessageBox.critical(self, "Simulation Error", f"LTspice simulation failed:\n\n{exc}")

    def _apply_ai_proposal(self):
        if not self.current_proposal or not self.current_design:
            return

        self.current_proposal.approval_status = "APPROVED"
        try:
            res = self.service.design.apply_iteration(self.current_design.id, self.current_proposal)
            self._load_design(self.current_design.id)
            QMessageBox.information(
                self,
                "Iteration Applied Successfully",
                f"Branched Revision 2 with {res['parameter_changed']} = {res['new_value']:.6g}.\n\n"
                f"• Previous Ripple: {res['ripple_before_v']*1000.0:.1f} mV\n"
                f"• New Ripple in Rev 2: {res['ripple_after_v']*1000.0:.1f} mV\n\n"
                f"Verdict: {res['summary_verdict']}",
            )
            # Switch to simulation view to inspect new results
            self._run_simulation()
        except Exception as exc:
            QMessageBox.critical(self, "Iteration Error", f"Could not apply iteration:\n\n{exc}")
