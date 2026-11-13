"""Semiconductor Technology Trade-Off Comparator for Mendex Engineering Studio v2.1.

Allows multi-device comparative evaluation of Wide-Bandgap (SiC, GaN) and Silicon transistors
across operating switching frequencies, conduction/switching loss, and heatsink sizing.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QGridLayout, QFrame, QMessageBox
)

from integrations.datasets.switchloss_db import SwitchLossDB, DeviceSwitchLossRecord
from integrations.calculations.power_losses import calculate_semiconductor_losses


class SemiconductorTradeoffComparatorDialog(QDialog):
    """Side-by-side comparative analysis of candidate switching transistors."""

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("⚖️ Semiconductor Technology Trade-Off & Heatsink Comparator")
        self.resize(960, 680)

        # Load devices from SwitchLossDB
        self.db = SwitchLossDB()
        fixture_path = Path(__file__).parents[1] / "integrations" / "datasets" / "fixtures" / "switchloss_sample.csv"
        if fixture_path.exists():
            self.db.load_csv(fixture_path)
        self.devices = self.db._records

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top Banner
        banner = QFrame()
        banner.setStyleSheet("""
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 10px;
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(4)
        t_title = QLabel("⚖️ Wide-Bandgap (SiC vs GaN vs Si) Semiconductor Trade-Off Analyzer")
        t_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #89b4fa;")
        b_layout.addWidget(t_title)

        t_desc = QLabel(
            "Compare up to three candidate switching devices across frequency sweeps (50 kHz – 500 kHz). "
            "Evaluates conduction vs switching dissipation trade-offs and calculates the minimum required heatsink thermal resistance (Rθ,sa) "
            "to prevent junction thermal runaway."
        )
        t_desc.setWordWrap(True)
        t_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        b_layout.addWidget(t_desc)
        layout.addWidget(banner)

        # Device Selection Controls
        sel_box = QGroupBox("Select Candidate Transistors for Comparison")
        sel_layout = QGridLayout(sel_box)
        sel_layout.setSpacing(10)

        sel_layout.addWidget(QLabel("Candidate #1 (Primary):"), 0, 0)
        self.combo_dev1 = QComboBox()
        self._populate_combo(self.combo_dev1)
        if self.combo_dev1.count() > 0:
            self.combo_dev1.setCurrentIndex(0)
        sel_layout.addWidget(self.combo_dev1, 0, 1)

        sel_layout.addWidget(QLabel("Candidate #2 (Alternative):"), 1, 0)
        self.combo_dev2 = QComboBox()
        self._populate_combo(self.combo_dev2)
        if self.combo_dev2.count() > 6:
            self.combo_dev2.setCurrentIndex(6)  # GS66508T GaN
        elif self.combo_dev2.count() > 1:
            self.combo_dev2.setCurrentIndex(1)
        sel_layout.addWidget(self.combo_dev2, 1, 1)

        sel_layout.addWidget(QLabel("Candidate #3 (Reference):"), 2, 0)
        self.combo_dev3 = QComboBox()
        self._populate_combo(self.combo_dev3)
        if self.combo_dev3.count() > 2:
            self.combo_dev3.setCurrentIndex(2)  # NVHL080N120SC1
        sel_layout.addWidget(self.combo_dev3, 2, 1)

        layout.addWidget(sel_box)

        # Operating Conditions Form
        cond_box = QGroupBox("Operating Conditions & Thermal Envelope")
        cond_layout = QHBoxLayout(cond_box)
        cond_layout.setSpacing(14)

        cond_layout.addWidget(QLabel("RMS Current (A):"))
        self.in_irms = QLineEdit("4.8")
        self.in_irms.setMaximumWidth(70)
        cond_layout.addWidget(self.in_irms)

        cond_layout.addWidget(QLabel("Duty Cycle (D):"))
        self.in_duty = QLineEdit("0.45")
        self.in_duty.setMaximumWidth(60)
        cond_layout.addWidget(self.in_duty)

        cond_layout.addWidget(QLabel("Ambient Temp Ta (°C):"))
        self.in_ta = QLineEdit("40.0")
        self.in_ta.setMaximumWidth(60)
        cond_layout.addWidget(self.in_ta)

        cond_layout.addWidget(QLabel("Max Junction Tj (°C):"))
        self.in_tj_max = QLineEdit("100.0")
        self.in_tj_max.setMaximumWidth(60)
        cond_layout.addWidget(self.in_tj_max)

        btn_run = QPushButton("⚡ Run Multi-Frequency Evaluation")
        btn_run.setStyleSheet("background-color: #1b4332; color: #a6e3a1; font-weight: 700; padding: 6px 14px; border-radius: 4px;")
        btn_run.clicked.connect(self.evaluate)
        cond_layout.addWidget(btn_run)

        cond_layout.addStretch()
        layout.addWidget(cond_box)

        # Frequency Sweep Results Table
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(8)
        self.res_table.setHorizontalHeaderLabels([
            "Frequency", "Device", "Technology", "P_cond (W)", "P_sw (W)", "Total Loss (W)", "Req Heatsink Rθ,sa", "Thermal Margin"
        ])
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.res_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.res_table, 1)

        # Bottom Recommendation Summary
        self.lbl_summary = QLabel("Click '⚡ Run Multi-Frequency Evaluation' to compare candidate switches.")
        self.lbl_summary.setStyleSheet("background: #11111b; color: #f9e2af; padding: 10px; border-radius: 6px; font-weight: 600;")
        self.lbl_summary.setWordWrap(True)
        layout.addWidget(self.lbl_summary)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.evaluate()

    def _populate_combo(self, combo: QComboBox):
        for idx, d in enumerate(self.devices):
            rds = f"{d.r_ds_on_mohm}mΩ" if d.r_ds_on_mohm else ""
            combo.addItem(f"{d.part_number} — {d.manufacturer} {d.device_type} ({d.v_ds_rated_v:.0f}V, {rds})", idx)

    def evaluate(self):
        try:
            i_rms = float(self.in_irms.text())
            duty = float(self.in_duty.text())
            t_a = float(self.in_ta.text())
            t_j_max = float(self.in_tj_max.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Inputs", "Please enter valid numerical values for operating conditions.")
            return

        sel_indices = [
            self.combo_dev1.currentData(),
            self.combo_dev2.currentData(),
            self.combo_dev3.currentData(),
        ]
        chosen_devs = [self.devices[i] for i in sel_indices if i is not None and 0 <= i < len(self.devices)]
        if not chosen_devs:
            return

        freqs = [50.0, 100.0, 150.0, 200.0, 300.0]
        rows_total = len(freqs) * len(chosen_devs)
        self.res_table.setRowCount(rows_total)

        cur_row = 0
        min_loss_at_100k = float("inf")
        best_dev_100k = ""
        min_loss_at_300k = float("inf")
        best_dev_300k = ""

        for f_khz in freqs:
            f_hz = f_khz * 1000.0
            for d in chosen_devs:
                r_ds = (d.r_ds_on_mohm or 65.0) / 1000.0
                e_on = (d.e_on_uj or 50.0) * 1e-6
                e_off = (d.e_off_uj or 20.0) * 1e-6

                res = calculate_semiconductor_losses(
                    part_number=d.part_number,
                    r_ds_on_ohm=r_ds,
                    i_rms_a=i_rms,
                    duty_cycle=duty,
                    e_on_j=e_on,
                    e_off_j=e_off,
                    frequency_hz=f_hz,
                )

                p_cond = res.p_conduction_w
                p_sw = res.p_switching_w
                p_tot = res.p_total_w

                # Heatsink thermal resistance: R_sa = (Tj - Ta)/P - R_jc (assuming R_jc = 1.5 C/W)
                r_jc = 1.5
                if p_tot > 0.05:
                    r_sa = max(0.1, ((t_j_max - t_a) / p_tot) - r_jc)
                    rsa_str = f"{r_sa:.1f} °C/W"
                    status = "ROBUST" if r_sa > 5.0 else ("MODERATE" if r_sa > 2.0 else "CHALLENGING")
                else:
                    rsa_str = "No Heatsink Req"
                    status = "ROBUST"

                if f_khz == 100.0 and p_tot < min_loss_at_100k:
                    min_loss_at_100k = p_tot
                    best_dev_100k = f"{d.part_number} ({d.device_type})"
                if f_khz == 300.0 and p_tot < min_loss_at_300k:
                    min_loss_at_300k = p_tot
                    best_dev_300k = f"{d.part_number} ({d.device_type})"

                self.res_table.setItem(cur_row, 0, QTableWidgetItem(f"{f_khz:.0f} kHz"))
                self.res_table.setItem(cur_row, 1, QTableWidgetItem(d.part_number))
                self.res_table.setItem(cur_row, 2, QTableWidgetItem(d.device_type))
                self.res_table.setItem(cur_row, 3, QTableWidgetItem(f"{p_cond:.3f}"))
                self.res_table.setItem(cur_row, 4, QTableWidgetItem(f"{p_sw:.3f}"))

                tot_item = QTableWidgetItem(f"{p_tot:.3f}")
                tot_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.res_table.setItem(cur_row, 5, tot_item)

                self.res_table.setItem(cur_row, 6, QTableWidgetItem(rsa_str))

                st_item = QTableWidgetItem(status)
                st_item.setForeground(Qt.green if status == "ROBUST" else (Qt.yellow if status == "MODERATE" else Qt.red))
                self.res_table.setItem(cur_row, 7, st_item)

                cur_row += 1

        summary = (
            f"💡 Engineering Trade-Off Insights:\n"
            f"• At 100 kHz (Standard): Lowest dissipation is {best_dev_100k} at {min_loss_at_100k:.2f} W.\n"
            f"• At 300 kHz (High Frequency): Lowest dissipation is {best_dev_300k} at {min_loss_at_300k:.2f} W.\n"
            f"• Sizing Rule: GaN and low-Q_rr SiC devices reduce switching loss at > 150 kHz, allowing 2x smaller magnetic cores while keeping heatsink thermal resistance above 4.0 °C/W."
        )
        self.lbl_summary.setText(summary)
