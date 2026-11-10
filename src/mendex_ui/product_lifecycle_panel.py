"""Product Engineering Lifecycle and Verification Overview Panel."""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from mendex_core.lifecycle.models import (
    ArtifactType,
    LifecycleStage,
    ProductLifecycleAssessment,
    StageEvaluation,
    StageStatus,
    UnifiedEvidenceRecord,
)
from mendex_core.service import StudioService
from .waveform_viewer import WaveformViewerWidget


class StageCardWidget(QFrame):
    """Visual clickable card displaying the status and evidence count for one lifecycle stage."""

    clicked = Signal(str)

    STATUS_COLORS = {
        StageStatus.NOT_STARTED: ("#45475a", "#a6adc8"),
        StageStatus.IN_PROGRESS: ("#1e3a5f", "#89b4fa"),
        StageStatus.PENDING_VERIFICATION: ("#45381f", "#f9e2af"),
        StageStatus.PASSED: ("#1b4332", "#a6e3a1"),
        StageStatus.FAILED: ("#4a1525", "#f38ba8"),
        StageStatus.BLOCKED: ("#4a2810", "#fab387"),
        StageStatus.NOT_APPLICABLE: ("#313244", "#6c7086"),
    }

    def __init__(self, stage_id: str, stage_eval: StageEvaluation, parent=None):
        super().__init__(parent)
        self.stage_id = stage_id
        self.stage_eval = stage_eval
        self.is_selected = False
        self.setObjectName("stage_card")
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        num_lbl = QLabel(f"#{self.stage_eval.category_number}")
        num_lbl.setStyleSheet("font-weight: 700; color: #89b4fa; font-size: 11px;")
        header_layout.addWidget(num_lbl)

        self.status_badge = QLabel(self.stage_eval.status.value)
        bg, fg = self.STATUS_COLORS.get(self.stage_eval.status, ("#313244", "#cdd6f4"))
        self.status_badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10px;"
        )
        self.status_badge.setAlignment(Qt.AlignCenter)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        layout.addLayout(header_layout)

        title_lbl = QLabel(self.stage_eval.title)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 11px; color: #cdd6f4;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        ev_count = len(self.stage_eval.evidence_records)
        ev_lbl = QLabel(f"● {ev_count} evidence records")
        ev_lbl.setStyleSheet("color: #a6adc8; font-size: 10px;")
        layout.addWidget(ev_lbl)

        if self.stage_eval.blockers:
            blk_lbl = QLabel(f"⚠ {self.stage_eval.blockers[0]}")
            blk_lbl.setStyleSheet("color: #f38ba8; font-size: 9px; font-style: italic;")
            blk_lbl.setWordWrap(True)
            layout.addWidget(blk_lbl)

        self.update_border()

    def update_border(self):
        border_color = "#89b4fa" if self.is_selected else "#313244"
        bg_color = "#24273a" if self.is_selected else "#181825"
        self.setStyleSheet(
            f"QFrame#stage_card {{ background-color: {bg_color}; border: 1.5px solid {border_color}; border-radius: 6px; }}"
        )

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_border()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.stage_id)
        super().mousePressEvent(event)


class ProductEngineeringOverviewPanel(QWidget):
    """Complete product engineering dashboard displaying lifecycle maturity, simulation history, PCB status, and evidence."""

    navigate_requested = Signal(str)

    def __init__(self, service: StudioService, parent=None):
        super().__init__(parent)
        self.service = service
        self.current_product_id: Optional[UUID] = None
        self.current_revision_id: Optional[UUID] = None
        self.current_assessment: Optional[ProductLifecycleAssessment] = None
        self.cards: Dict[str, StageCardWidget] = {}
        self.selected_stage_id: str = LifecycleStage.REQUIREMENTS.value
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Top Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 8px;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.lbl_title = QLabel("Product Engineering Overview")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #cdd6f4;")
        top_row.addWidget(self.lbl_title)

        top_row.addStretch()

        self.badge_readiness = QLabel("PROTOTYPE BLOCKED")
        self.badge_readiness.setStyleSheet("background-color: #4a1525; color: #f38ba8; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        top_row.addWidget(self.badge_readiness)

        self.badge_overall = QLabel("IN PROGRESS")
        self.badge_overall.setStyleSheet("background-color: #1e3a5f; color: #89b4fa; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        top_row.addWidget(self.badge_overall)

        header_layout.addLayout(top_row)

        sub_row = QHBoxLayout()
        self.lbl_meta = QLabel("Product Code: N/A | Category: N/A | Owner: N/A")
        self.lbl_meta.setStyleSheet("color: #a6adc8; font-size: 11px;")
        sub_row.addWidget(self.lbl_meta)

        sub_row.addStretch()

        lbl_rev = QLabel("Active Revision:")
        lbl_rev.setStyleSheet("color: #a6adc8; font-weight: 600; font-size: 11px;")
        sub_row.addWidget(lbl_rev)

        self.combo_revisions = QComboBox()
        self.combo_revisions.setMinimumWidth(120)
        self.combo_revisions.currentIndexChanged.connect(self._on_revision_changed)
        sub_row.addWidget(self.combo_revisions)

        btn_refresh = QPushButton("Re-Assess Lifecycle")
        btn_refresh.clicked.connect(self.refresh_assessment)
        sub_row.addWidget(btn_refresh)

        btn_open_ws = QPushButton("Open Workspace")
        btn_open_ws.clicked.connect(self._open_workspace_folder)
        sub_row.addWidget(btn_open_ws)

        header_layout.addLayout(sub_row)
        main_layout.addWidget(header)

        # 2. Critical Blockers Banner
        self.blocker_frame = QFrame()
        self.blocker_frame.setStyleSheet("background-color: #2e1720; border-left: 4px solid #f38ba8; border-radius: 4px; padding: 6px;")
        blocker_layout = QHBoxLayout(self.blocker_frame)
        self.lbl_blockers = QLabel("No blockers detected.")
        self.lbl_blockers.setStyleSheet("color: #f38ba8; font-size: 11px;")
        self.lbl_blockers.setWordWrap(True)
        blocker_layout.addWidget(self.lbl_blockers)
        main_layout.addWidget(self.blocker_frame)

        # 3. Stage Timeline / 12 Cards Grid (Scrollable)
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setFixedHeight(230)
        cards_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_container = QWidget()
        self.cards_grid = QGridLayout(cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(8)
        cards_scroll.setWidget(cards_container)
        main_layout.addWidget(cards_scroll)

        # 4. Interactive Detail Tabs
        self.detail_tabs = QTabWidget()
        main_layout.addWidget(self.detail_tabs, 1)

        # Tab A: Stage Deep-Dive & Approvals
        self.tab_stage = QWidget()
        self._init_stage_tab()
        self.detail_tabs.addTab(self.tab_stage, "Stage Detail & Approvals")

        # Tab B: Electrical Simulation & Waveforms
        self.tab_sim = QWidget()
        self._init_simulation_tab()
        self.detail_tabs.addTab(self.tab_sim, "Electrical Simulations & Waveforms")

        # Tab C: KiCad Schematic & PCB Design
        self.tab_pcb = QWidget()
        self._init_pcb_tab()
        self.detail_tabs.addTab(self.tab_pcb, "KiCad Schematic & PCB")

        # Tab D: Unified Evidence Register
        self.tab_evidence = QWidget()
        self._init_evidence_tab()
        self.detail_tabs.addTab(self.tab_evidence, "Unified Evidence Register")

        # Tab E: Prototype Readiness Gates
        self.tab_gates = QWidget()
        self._init_gates_tab()
        self.detail_tabs.addTab(self.tab_gates, "Prototype Readiness Gates")

    def _init_stage_tab(self):
        layout = QVBoxLayout(self.tab_stage)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.lbl_stage_title = QLabel("Stage Detail")
        self.lbl_stage_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #cdd6f4;")
        layout.addWidget(self.lbl_stage_title)

        info_layout = QHBoxLayout()
        self.lbl_stage_status = QLabel("Status: N/A")
        self.lbl_stage_status.setStyleSheet("font-weight: 600; color: #89b4fa;")
        info_layout.addWidget(self.lbl_stage_status)

        self.lbl_stage_target = QLabel("Nav Target: N/A")
        self.lbl_stage_target.setStyleSheet("color: #a6adc8;")
        info_layout.addWidget(self.lbl_stage_target)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        form = QFormLayout()
        self.lbl_stage_req = QLabel("Required Evidence:")
        self.lbl_stage_req.setWordWrap(True)
        form.addRow("Required Evidence:", self.lbl_stage_req)

        self.lbl_stage_act = QLabel("Actual Evidence:")
        self.lbl_stage_act.setWordWrap(True)
        form.addRow("Actual Evidence:", self.lbl_stage_act)

        self.txt_stage_blockers = QTextEdit()
        self.txt_stage_blockers.setReadOnly(True)
        self.txt_stage_blockers.setMaximumHeight(70)
        form.addRow("Blockers:", self.txt_stage_blockers)
        layout.addLayout(form)

        # Stage Approval Group
        app_box = QGroupBox("Formal Engineering Stage Sign-Off")
        app_form = QFormLayout(app_box)
        self.in_reviewer = QLineEdit("Lead Systems Engineer")
        self.in_notes = QLineEdit("Verified compliant with project baseline")
        self.combo_decision = QComboBox()
        self.combo_decision.addItems(["PASS", "FAIL"])
        app_form.addRow("Reviewer Identity:", self.in_reviewer)
        app_form.addRow("Decision:", self.combo_decision)
        app_form.addRow("Review Notes:", self.in_notes)

        btn_sign = QPushButton("Record Stage Approval Decision")
        btn_sign.clicked.connect(self._record_approval)
        app_form.addRow(btn_sign)
        layout.addWidget(app_box)
        layout.addStretch()

    def _init_simulation_tab(self):
        layout = QVBoxLayout(self.tab_sim)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        actions = QHBoxLayout()
        btn_run_lt = QPushButton("Execute Batch LTspice Run")
        btn_run_lt.clicked.connect(self._run_ltspice)
        actions.addWidget(btn_run_lt)

        btn_run_ng = QPushButton("Execute Batch ngspice Run")
        btn_run_ng.clicked.connect(self._run_ngspice)
        actions.addWidget(btn_run_ng)

        actions.addStretch()
        layout.addLayout(actions)

        split = QSplitter(Qt.Vertical)
        self.sim_table = QTableWidget()
        self.sim_table.setColumnCount(7)
        self.sim_table.setHorizontalHeaderLabels(["Job ID", "Tool", "Operation", "Solver Status", "Exit Code", "Output Files", "Engineering Decision"])
        self.sim_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sim_table.setMaximumHeight(160)
        self.sim_table.itemDoubleClicked.connect(self._on_sim_row_clicked)
        split.addWidget(self.sim_table)

        self.sim_waveform = WaveformViewerWidget(is_dark=True)
        split.addWidget(self.sim_waveform)
        layout.addWidget(split, 1)

    def _init_pcb_tab(self):
        layout = QVBoxLayout(self.tab_pcb)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_actions = QHBoxLayout()
        btn_erc = QPushButton("Run KiCad Schematic ERC")
        btn_erc.clicked.connect(self._run_kicad_erc)
        top_actions.addWidget(btn_erc)

        btn_drc = QPushButton("Run KiCad PCB DRC")
        btn_drc.clicked.connect(self._run_kicad_drc)
        top_actions.addWidget(btn_drc)

        btn_import = QPushButton("Import / Link KiCad Files...")
        btn_import.clicked.connect(self._import_kicad_files)
        top_actions.addWidget(btn_import)

        btn_export_gerbers = QPushButton("Export Manufacturing Gerbers")
        btn_export_gerbers.clicked.connect(self._export_gerbers)
        top_actions.addWidget(btn_export_gerbers)

        top_actions.addStretch()
        layout.addLayout(top_actions)

        self.lbl_pcb_status = QLabel("KiCad Workspace: No active board or schematic selected.")
        self.lbl_pcb_status.setStyleSheet("color: #a6adc8; font-weight: 600;")
        layout.addWidget(self.lbl_pcb_status)

        self.txt_kicad_results = QTextEdit()
        self.txt_kicad_results.setReadOnly(True)
        layout.addWidget(self.txt_kicad_results, 1)

    def _init_evidence_tab(self):
        layout = QVBoxLayout(self.tab_evidence)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        search_row = QHBoxLayout()
        self.in_ev_search = QLineEdit()
        self.in_ev_search.setPlaceholderText("Filter evidence by stage, artifact type, tool, or filename...")
        self.in_ev_search.textChanged.connect(self._filter_evidence)
        search_row.addWidget(self.in_ev_search)

        btn_open_file = QPushButton("Open Selected File")
        btn_open_file.clicked.connect(self._open_selected_evidence)
        search_row.addWidget(btn_open_file)
        layout.addLayout(search_row)

        self.ev_table = QTableWidget()
        self.ev_table.setColumnCount(8)
        self.ev_table.setHorizontalHeaderLabels([
            "Evidence ID", "Stage", "Artifact Type", "Tool", "File Name", "Size (bytes)", "SHA-256", "Validation Result"
        ])
        self.ev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.ev_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.ev_table, 1)

    def _init_gates_tab(self):
        layout = QVBoxLayout(self.tab_gates)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.lbl_gate_summary = QLabel("Readiness Gates Evaluation:")
        self.lbl_gate_summary.setStyleSheet("font-weight: 700; color: #cdd6f4;")
        layout.addWidget(self.lbl_gate_summary)

        self.gates_table = QTableWidget()
        self.gates_table.setColumnCount(5)
        self.gates_table.setHorizontalHeaderLabels(["Gate ID", "Title", "Mandatory", "Status", "Reason / Blockers"])
        self.gates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.gates_table, 1)

    def set_product(self, product_id: UUID, revision_id: Optional[UUID] = None):
        """Sets the active product and revision, populates revision combo, and executes lifecycle assessment."""
        self.current_product_id = product_id
        product = self.service.get_product(product_id)
        revisions = self.service.list_revisions(product_id)

        self.combo_revisions.blockSignals(True)
        self.combo_revisions.clear()
        target_idx = 0
        for idx, rev in enumerate(revisions):
            self.combo_revisions.addItem(f"{rev.revision_label} ({rev.lifecycle_status.value})", str(rev.revision_id))
            if revision_id and rev.revision_id == revision_id:
                target_idx = idx
            elif not revision_id and rev.revision_id == product.active_revision_id:
                target_idx = idx

        self.combo_revisions.setCurrentIndex(target_idx)
        self.combo_revisions.blockSignals(False)

        selected_rev_id = UUID(self.combo_revisions.currentData()) if self.combo_revisions.currentData() else product.active_revision_id
        self.current_revision_id = selected_rev_id

        self.lbl_title.setText(f"{product.code} — {product.name}")
        self.lbl_meta.setText(f"Product Code: {product.code} | Category: {product.category.value} | Owner: {product.owner}")
        self.refresh_assessment()

    def _on_revision_changed(self, index: int):
        if index >= 0 and self.combo_revisions.currentData():
            self.current_revision_id = UUID(self.combo_revisions.currentData())
            self.refresh_assessment()

    def refresh_assessment(self):
        """Runs the lifecycle engine assessment and refreshes all UI cards and tabs."""
        if not self.current_product_id or not self.current_revision_id:
            return

        assessment = self.service.lifecycle.assess(self.current_product_id, self.current_revision_id)
        self.current_assessment = assessment

        # Update Readiness Badges
        if assessment.prototype_ready:
            self.badge_readiness.setText("PROTOTYPE READY")
            self.badge_readiness.setStyleSheet("background-color: #1b4332; color: #a6e3a1; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        else:
            self.badge_readiness.setText("PROTOTYPE BLOCKED")
            self.badge_readiness.setStyleSheet("background-color: #4a1525; color: #f38ba8; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")

        self.badge_overall.setText(assessment.overall_status.value)
        if assessment.overall_status == StageStatus.PASSED:
            self.badge_overall.setStyleSheet("background-color: #1b4332; color: #a6e3a1; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        elif assessment.overall_status == StageStatus.FAILED:
            self.badge_overall.setStyleSheet("background-color: #4a1525; color: #f38ba8; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        else:
            self.badge_overall.setStyleSheet("background-color: #1e3a5f; color: #89b4fa; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 4px;")

        # Update Blockers banner
        if assessment.critical_blockers:
            self.blocker_frame.setVisible(True)
            self.lbl_blockers.setText(f"CRITICAL BLOCKERS ({len(assessment.critical_blockers)}):\n" + "\n".join(f"• {b}" for b in assessment.critical_blockers[:3]))
        else:
            self.blocker_frame.setVisible(False)

        # Clear and rebuild Stage Cards
        for c in self.cards.values():
            c.deleteLater()
        self.cards.clear()

        # Build grid (2 rows of 6 cards)
        row = 0
        col = 0
        for stage_key, stage_eval in assessment.stages.items():
            card = StageCardWidget(stage_key, stage_eval)
            card.clicked.connect(self._on_stage_card_clicked)
            if stage_key == self.selected_stage_id:
                card.set_selected(True)
            self.cards_grid.addWidget(card, row, col)
            self.cards[stage_key] = card
            col += 1
            if col >= 6:
                col = 0
                row += 1

        # Refresh Sub-Tabs
        self._refresh_stage_tab()
        self._refresh_simulation_tab()
        self._refresh_pcb_tab()
        self._refresh_evidence_tab()
        self._refresh_gates_tab()

    def _on_stage_card_clicked(self, stage_id: str):
        self.selected_stage_id = stage_id
        for sid, card in self.cards.items():
            card.set_selected(sid == stage_id)
        self._refresh_stage_tab()
        self.detail_tabs.setCurrentIndex(0)

    def _refresh_stage_tab(self):
        if not self.current_assessment:
            return
        stage = self.current_assessment.stages.get(self.selected_stage_id)
        if not stage:
            return

        self.lbl_stage_title.setText(f"Stage #{stage.category_number}: {stage.title}")
        self.lbl_stage_status.setText(f"Status: {stage.status.value}")
        self.lbl_stage_target.setText(f"Target View: {stage.nav_target}")
        self.lbl_stage_req.setText(stage.required_evidence_desc)
        self.lbl_stage_act.setText(stage.actual_evidence_desc)

        if stage.blockers:
            self.txt_stage_blockers.setText("\n".join(f"• {b}" for b in stage.blockers))
        else:
            self.txt_stage_blockers.setText("No blockers recorded for this stage.")

    def _record_approval(self):
        reviewer = self.in_reviewer.text().strip()
        if not reviewer:
            QMessageBox.warning(self, "Invalid Reviewer", "Reviewer identity is required.")
            return

        passed = self.combo_decision.currentText() == "PASS"
        notes = self.in_notes.text().strip()

        try:
            stage_enum = LifecycleStage(self.selected_stage_id)
            self.service.lifecycle.record_stage_approval(
                self.current_revision_id, stage_enum, reviewer, passed, notes
            )
            QMessageBox.information(self, "Approval Recorded", f"Approval recorded for stage: {stage_enum.value}")
            self.refresh_assessment()
        except Exception as e:
            QMessageBox.warning(self, "Error Recording Approval", str(e))

    def _refresh_simulation_tab(self):
        self.sim_table.setRowCount(0)
        if not self.current_revision_id:
            return

        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        raw_files = list(ws_path.glob("**/*.raw"))
        if raw_files:
            self.sim_waveform.load_raw_file(raw_files[0])

    def _on_sim_row_clicked(self, item):
        pass

    def _run_ltspice(self):
        QMessageBox.information(self, "Simulation Lab", "Navigating to Simulation Lab to execute verified LTspice batch simulation.")
        self.navigate_requested.emit("Simulations")

    def _run_ngspice(self):
        QMessageBox.information(self, "Simulation Lab", "Navigating to Simulation Lab to execute verified ngspice batch simulation.")
        self.navigate_requested.emit("Simulations")

    def _refresh_pcb_tab(self):
        if not self.current_revision_id:
            return
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        files = self.service.lifecycle.kicad.discover_files(ws_path)

        sch_count = len(files["schematics"])
        pcb_count = len(files["pcbs"])
        erc_count = len(files["erc_reports"])
        drc_count = len(files["drc_reports"])

        status_text = f"KiCad Workspace: {sch_count} Schematics | {pcb_count} PCB Layouts | {erc_count} ERC Reports | {drc_count} DRC Reports"
        self.lbl_pcb_status.setText(status_text)

        report_txt = "=== KICAD SCHEMATIC & PCB WORKSPACE AUDIT ===\n\n"
        if files["schematics"]:
            report_txt += "Schematics:\n" + "\n".join(f" - {f.name} ({f.stat().st_size} bytes)" for f in files["schematics"]) + "\n\n"
        else:
            report_txt += "Schematics: [NONE] No .kicad_sch file found in workspace.\n\n"

        if files["pcbs"]:
            report_txt += "PCB Layouts:\n" + "\n".join(f" - {f.name} ({f.stat().st_size} bytes)" for f in files["pcbs"]) + "\n\n"
        else:
            report_txt += "PCB Layouts: [NONE] No .kicad_pcb file found in workspace.\n\n"

        if files["erc_reports"]:
            report_txt += "ERC Reports:\n" + "\n".join(f" - {f.name}" for f in files["erc_reports"]) + "\n\n"
        if files["drc_reports"]:
            report_txt += "DRC Reports:\n" + "\n".join(f" - {f.name}" for f in files["drc_reports"]) + "\n\n"

        self.txt_kicad_results.setText(report_txt)

    def _run_kicad_erc(self):
        if not self.current_revision_id:
            return
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        files = self.service.lifecycle.kicad.discover_files(ws_path)
        if not files["schematics"]:
            QMessageBox.warning(self, "No Schematic", "No KiCad schematic (.kicad_sch) file found in product workspace.")
            return

        sch = files["schematics"][0]
        try:
            res = self.service.lifecycle.kicad.run_erc(sch)
            self.refresh_assessment()
            total = res.get("parsed", {}).get("total_issues", "N/A")
            QMessageBox.information(self, "ERC Complete", f"KiCad Electrical Rule Check complete.\nTotal Issues: {total}\nReport: {res['output_report']}")
        except Exception as e:
            QMessageBox.warning(self, "ERC Error", str(e))

    def _run_kicad_drc(self):
        if not self.current_revision_id:
            return
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        files = self.service.lifecycle.kicad.discover_files(ws_path)
        if not files["pcbs"]:
            QMessageBox.warning(self, "No PCB Layout", "No KiCad board (.kicad_pcb) file found in product workspace.")
            return

        pcb = files["pcbs"][0]
        try:
            res = self.service.lifecycle.kicad.run_drc(pcb)
            self.refresh_assessment()
            total = res.get("parsed", {}).get("total_issues", "N/A")
            QMessageBox.information(self, "DRC Complete", f"KiCad Design Rule Check complete.\nTotal Issues: {total}\nReport: {res['output_report']}")
        except Exception as e:
            QMessageBox.warning(self, "DRC Error", str(e))

    def _import_kicad_files(self):
        if not self.current_revision_id:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select KiCad Schematic or Board", "", "KiCad Files (*.kicad_sch *.kicad_pcb)")
        if file_path:
            p = Path(file_path)
            revision = self.service.get_revision(self.current_revision_id)
            ws_path = self.service.workspace_path(revision)
            target_dir = (ws_path / "pcb")
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / p.name
            shutil.copy2(p, dest)
            QMessageBox.information(self, "File Imported", f"Imported {p.name} into product workspace:\n{dest}")
            self.refresh_assessment()

    def _export_gerbers(self):
        if not self.current_revision_id:
            return
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        files = self.service.lifecycle.kicad.discover_files(ws_path)
        if not files["pcbs"]:
            QMessageBox.warning(self, "No PCB Layout", "Cannot export Gerbers: no .kicad_pcb file exists.")
            return
        pcb = files["pcbs"][0]
        try:
            out_dir = self.service.lifecycle.kicad.export_gerbers(pcb)
            QMessageBox.information(self, "Gerber Export Complete", f"Manufacturing Gerbers exported to:\n{out_dir}")
            self.refresh_assessment()
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def _refresh_evidence_tab(self):
        self.ev_table.setRowCount(0)
        if not self.current_product_id or not self.current_revision_id:
            return
        records = self.service.lifecycle.get_evidence_register(self.current_product_id, self.current_revision_id)
        query = self.in_ev_search.text().lower().strip()

        filtered = []
        for r in records:
            if query:
                match = (
                    query in r.stage_id.value.lower()
                    or query in r.artifact_type.value.lower()
                    or query in r.source_tool.lower()
                    or query in r.source_file.lower()
                )
                if not match:
                    continue
            filtered.append(r)

        self.ev_table.setRowCount(len(filtered))
        for row, rec in enumerate(filtered):
            self.ev_table.setItem(row, 0, QTableWidgetItem(str(rec.evidence_id)[:8]))
            self.ev_table.setItem(row, 1, QTableWidgetItem(rec.stage_id.value))
            self.ev_table.setItem(row, 2, QTableWidgetItem(rec.artifact_type.value))
            self.ev_table.setItem(row, 3, QTableWidgetItem(rec.source_tool))
            self.ev_table.setItem(row, 4, QTableWidgetItem(rec.source_file))
            self.ev_table.setItem(row, 5, QTableWidgetItem(str(rec.file_size_bytes)))
            self.ev_table.setItem(row, 6, QTableWidgetItem(rec.sha256[:12] if rec.sha256 else "N/A"))

            res_item = QTableWidgetItem(rec.validation_result)
            if rec.validation_result == "PASSED":
                res_item.setForeground(Qt.green)
            elif rec.validation_result == "FAILED":
                res_item.setForeground(Qt.red)
            else:
                res_item.setForeground(Qt.yellow)
            self.ev_table.setItem(row, 7, res_item)

    def _filter_evidence(self, text: str):
        self._refresh_evidence_tab()

    def _open_selected_evidence(self):
        row = self.ev_table.currentRow()
        if row < 0 or not self.current_revision_id:
            return
        fname = self.ev_table.item(row, 4).text()
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        matches = list(ws_path.glob(f"**/{fname}"))
        if matches and matches[0].exists():
            os.startfile(matches[0])
        else:
            QMessageBox.information(self, "File Info", f"Evidence file reference: {fname}")

    def _refresh_gates_tab(self):
        self.gates_table.setRowCount(0)
        if not self.current_assessment:
            return

        gates = self.current_assessment.readiness_gates
        self.gates_table.setRowCount(len(gates))
        for row, g in enumerate(gates):
            self.gates_table.setItem(row, 0, QTableWidgetItem(g.gate_id))
            self.gates_table.setItem(row, 1, QTableWidgetItem(g.title))
            self.gates_table.setItem(row, 2, QTableWidgetItem("Yes" if g.mandatory else "No"))

            st_item = QTableWidgetItem(g.status)
            if g.passed:
                st_item.setForeground(Qt.green)
            elif g.status == "FAILED":
                st_item.setForeground(Qt.red)
            elif g.status == "BLOCKED":
                st_item.setForeground(Qt.yellow)
            else:
                st_item.setForeground(Qt.gray)
            self.gates_table.setItem(row, 3, st_item)
            self.gates_table.setItem(row, 4, QTableWidgetItem(g.reason))

    def _open_workspace_folder(self):
        if not self.current_revision_id:
            return
        revision = self.service.get_revision(self.current_revision_id)
        ws_path = self.service.workspace_path(revision)
        if ws_path.exists():
            os.startfile(ws_path)
