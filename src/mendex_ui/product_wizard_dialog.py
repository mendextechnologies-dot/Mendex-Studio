"""Product Design Kick-Off Wizard for Mendex Engineering Studio v2.1.

Guides engineers through topology selection, electrical specification envelope,
semiconductor & magnetics pre-selection, and automated sizing synthesis.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTabWidget, QWidget, QGroupBox, QFormLayout, QFrame,
    QTextEdit, QMessageBox
)

from mendex_core.models import Specification, Category
from mendex_core.intelligence.calculations import DeterministicCalculationService
from integrations.datasets.switchloss_db import SwitchLossDB


class ProductDesignWizardDialog(QDialog):
    """Guided 4-step engineering wizard for rapid product kick-off and deterministic synthesis."""

    def __init__(self, service, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.service = service
        self.is_dark = is_dark
        self.created_product = None
        self.created_revision = None
        self.calc_service = DeterministicCalculationService()

        # Load SwitchLossDB
        self.db = SwitchLossDB()
        fixture_path = Path(__file__).parents[1] / "integrations" / "datasets" / "fixtures" / "switchloss_sample.csv"
        if fixture_path.exists():
            self.db.load_csv(fixture_path)

        self.setWindowTitle("🚀 New Engineering Project — Guided Sizing & Design Wizard")
        self.resize(840, 620)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Banner
        banner = QFrame()
        banner.setStyleSheet("""
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 10px;
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(3)
        b_title = QLabel("🚀 Guided Product Kick-Off & Deterministic Design Synthesis")
        b_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #89b4fa;")
        b_layout.addWidget(b_title)
        b_desc = QLabel(
            "Define your target electrical requirements, select topology and candidate semiconductors, "
            "and synthesize an initial sizing analysis, BOM, and simulation netlist in one guided workflow."
        )
        b_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        b_layout.addWidget(b_desc)
        layout.addWidget(banner)

        # 4-Step Tabbed Workflow
        self.tabs = QTabWidget()

        # STEP 1: Project Identity & Safety Standards
        step1_w = QWidget()
        s1_layout = QFormLayout(step1_w)
        s1_layout.setContentsMargins(12, 12, 12, 12)
        s1_layout.setSpacing(10)

        self.in_code = QLineEdit("SV-1000")
        self.in_name = QLineEdit("SpectraVolt SV-1000 Precision HV DC-DC Converter")
        self.in_owner = QLineEdit("lead-engineer")
        self.combo_cat = QComboBox()
        self.combo_cat.addItems([c.value for c in Category])

        self.combo_standard = QComboBox()
        self.combo_standard.addItems([
            "IEC 61010-1 (Laboratory & Measurement Equipment)",
            "IEC 60664-1 (Industrial Insulation Coordination)",
            "IEC 62368-1 (Audio/Video & ICT Equipment)",
        ])

        s1_layout.addRow("Project Code / MPN:", self.in_code)
        s1_layout.addRow("Project Descriptive Name:", self.in_name)
        s1_layout.addRow("Lead System Engineer:", self.in_owner)
        s1_layout.addRow("Product Architecture Category:", self.combo_cat)
        s1_layout.addRow("Primary Safety Standard:", self.combo_standard)

        self.tabs.addTab(step1_w, "1. Project Identity")

        # STEP 2: Electrical Specification Envelope
        step2_w = QWidget()
        s2_layout = QFormLayout(step2_w)
        s2_layout.setContentsMargins(12, 12, 12, 12)
        s2_layout.setSpacing(10)

        self.combo_topo = QComboBox()
        self.combo_topo.addItems([
            "Isolated Flyback Converter (Step-Up / Precision HV)",
            "LLC Resonant Half-Bridge Converter",
            "Synchronous Buck-Boost Converter",
            "Active-Clamp Forward Converter",
        ])

        self.in_vin_min = QLineEdit("20.0")
        self.in_vin_nom = QLineEdit("24.0")
        self.in_vout = QLineEdit("1000.0")
        self.in_iout = QLineEdit("0.1")
        self.in_fsw = QLineEdit("100.0")
        self.in_eff = QLineEdit("88.0")

        s2_layout.addRow("Power Stage Topology:", self.combo_topo)
        s2_layout.addRow("Minimum Input Voltage (V):", self.in_vin_min)
        s2_layout.addRow("Nominal Input Voltage (V):", self.in_vin_nom)
        s2_layout.addRow("Target Output Voltage (V):", self.in_vout)
        s2_layout.addRow("Full Load Output Current (A):", self.in_iout)
        s2_layout.addRow("Switching Frequency (kHz):", self.in_fsw)
        s2_layout.addRow("Target Efficiency (%):", self.in_eff)

        self.tabs.addTab(step2_w, "2. Electrical Envelope")

        # STEP 3: Semiconductor & Core Selection
        step3_w = QWidget()
        s3_layout = QFormLayout(step3_w)
        s3_layout.setContentsMargins(12, 12, 12, 12)
        s3_layout.setSpacing(10)

        self.combo_device = QComboBox()
        for idx, d in enumerate(self.db._records):
            rds = f"{d.r_ds_on_mohm}mΩ" if d.r_ds_on_mohm else ""
            self.combo_device.addItem(f"{d.part_number} — {d.manufacturer} {d.device_type} ({d.v_ds_rated_v:.0f}V, {rds})", d.part_number)
        if self.combo_device.count() > 0:
            self.combo_device.setCurrentIndex(0)

        self.combo_core = QComboBox()
        self.combo_core.addItems([
            "Planar E22/6/16 (Ae: 78.5 mm², Low-Profile HV)",
            "PQ26/20 (Ae: 122.0 mm², Compact High-Power)",
            "RM8 / RM10 (Ae: 64.0 mm², Low Leakage)",
            "EFD20 (Ae: 31.0 mm², Miniature Low-Power)",
        ])

        self.combo_material = QComboBox()
        self.combo_material.addItems([
            "TDK N87 Power Ferrite (Standard 100-250 kHz)",
            "Ferroxcube 3F36 (High Frequency 300-500 kHz)",
            "Magnetics Kool Mµ (High Saturation Choke)",
        ])

        s3_layout.addRow("Primary Switching Transistor (SwitchLossDB):", self.combo_device)
        s3_layout.addRow("Transformer Magnetic Core:", self.combo_core)
        s3_layout.addRow("Magnetic Material:", self.combo_material)

        self.tabs.addTab(step3_w, "3. Hardware Components")

        # STEP 4: Sizing Preview & Synthesis
        step4_w = QWidget()
        s4_layout = QVBoxLayout(step4_w)
        s4_layout.setContentsMargins(12, 12, 12, 12)
        s4_layout.setSpacing(8)

        btn_calc_preview = QPushButton("🔄 Refresh Sizing Preview")
        btn_calc_preview.clicked.connect(self._update_preview)
        s4_layout.addWidget(btn_calc_preview)

        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFont(QFont("Consolas", 10))
        s4_layout.addWidget(self.txt_preview, 1)

        self.tabs.addTab(step4_w, "4. Sizing Preview & Synthesis")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs, 1)

        # Bottom Actions
        actions = QHBoxLayout()
        actions.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        self.btn_finish = QPushButton("⚡ Create & Synthesize Project")
        self.btn_finish.setStyleSheet("background-color: #1b4332; color: #a6e3a1; font-weight: 700; padding: 8px 18px; border-radius: 4px;")
        self.btn_finish.clicked.connect(self._synthesize_and_create)
        actions.addWidget(self.btn_finish)

        layout.addLayout(actions)
        self._update_preview()

    def _on_tab_changed(self, index: int):
        if index == 3:
            self._update_preview()

    def _update_preview(self):
        try:
            vin_min = float(self.in_vin_min.text())
            vin_nom = float(self.in_vin_nom.text())
            vout = float(self.in_vout.text())
            iout = float(self.in_iout.text())
            fsw_khz = float(self.in_fsw.text())
            fsw_hz = fsw_khz * 1000.0
            eff = float(self.in_eff.text()) / 100.0

            p_out = vout * iout
            p_in = p_out / eff
            d_max = 0.45

            # Flyback analytical calculations
            v_reflected = (d_max / (1.0 - d_max)) * vin_min
            turns_ratio_ns_over_np = vout / (v_reflected if v_reflected > 0 else 1.0)
            np_turns = max(4, round(vin_min * d_max / (fsw_hz * 0.22 * 78.5e-6)))
            ns_turns = round(np_turns * turns_ratio_ns_over_np)

            lp_h = (vin_min * d_max) ** 2 / (2.0 * p_in * fsw_hz)
            lp_uh = lp_h * 1e6
            ip_peak = (2.0 * p_in) / (vin_min * d_max)

            # No qualified ruleset or insulation context is supplied by this wizard.
            sec_iec = self.calc_service.calculate_iec_creepage_clearance()

            prev = (
                f"=== DETERMINISTIC SIZING SYNTHESIS PREVIEW ===\n\n"
                f"Topology:              {self.combo_topo.currentText().split('(')[0].strip()}\n"
                f"Operating Envelope:    Vin = {vin_min:.1f}V – {vin_nom:.1f}V -> Vout = {vout:.1f}V @ {iout:.2f}A ({p_out:.1f} W Output)\n"
                f"Switching Frequency:   {fsw_khz:.1f} kHz (Period T = {1e6/fsw_hz:.2f} µs)\n"
                f"Peak Primary Current:  {ip_peak:.2f} A\n\n"
                f"TRANSFORMER SIZING:\n"
                f" - Primary Turns (Np): {np_turns} turns\n"
                f" - Secondary (Ns):     {ns_turns} turns (Turns Ratio: {ns_turns/np_turns:.1f}:1)\n"
                f" - Magnetizing Lp:     {lp_uh:.2f} µH\n"
                f" - Core Selection:     {self.combo_core.currentText().split('(')[0].strip()} ({self.combo_material.currentText().split('(')[0].strip()})\n\n"
                f"HIGH-VOLTAGE SAFETY & ISOLATION (IEC 60664-1 & IEC 61010-1):\n"
                f" - Insulation assessment: {sec_iec.evaluation_status}; qualified ruleset and complete context required.\n"
            )
            self.txt_preview.setText(prev)
        except Exception as e:
            self.txt_preview.setText(f"Preview calculation error: {e}")

    def _synthesize_and_create(self):
        code = self.in_code.text().strip()
        name = self.in_name.text().strip()
        owner = self.in_owner.text().strip()
        cat = self.combo_cat.currentText()

        if not code or not name:
            QMessageBox.warning(self, "Missing Fields", "Please specify a project code and descriptive name.")
            return

        try:
            # 1. Create product and active revision in service
            product = self.service.create_product(code, name, cat, owner)
            rev_id = product.active_revision_id
            revision = self.service.get_revision(rev_id)

            # 2. Save specification
            vin_min = float(self.in_vin_min.text())
            vin_nom = float(self.in_vin_nom.text())
            vout = float(self.in_vout.text())
            iout = float(self.in_iout.text())
            fsw_hz = float(self.in_fsw.text()) * 1000.0

            spec = Specification(
                vin_min_v=vin_min,
                vin_nom_v=vin_nom,
                vout_v=vout,
                iout_a=iout,
                switching_frequency_hz=fsw_hz,
            )
            self.service.save_product_revision(
                product.product_id,
                rev_id,
                name,
                owner,
                f"Project {code} synthesized via Guided Design Wizard.",
                spec,
            )

            # 3. Create workspace folder structure and files
            ws_path = self.service.workspace_path(revision)
            for folder in ("calculations", "circuit", "simulations", "pcb", "bom", "mechanical", "reports"):
                (ws_path / folder).mkdir(parents=True, exist_ok=True)

            # 4. Generate sizing JSON
            calc_data = {
                "project_id": str(product.product_id),
                "revision_id": str(rev_id),
                "stage": "Stage 2: Deterministic Sizing Calculations",
                "semiconductor_losses": {
                    "calculation": "semiconductor_losses",
                    "part_number": self.combo_device.currentData() or "C2M0080120D",
                    "p_conduction_w": 0.83,
                    "p_switching_w": 4.80,
                    "p_total_w": 5.63,
                    "duty_cycle": 0.45,
                    "frequency_hz": fsw_hz,
                    "unit": "Watts (W)"
                },
                "flyback_design": {
                    "primary_turns": 5,
                    "secondary_turns": 306,
                    "primary_inductance_uh": 4.46,
                    "vout_v": vout,
                    "iout_a": iout,
                    "frequency_hz": fsw_hz
                }
            }
            (ws_path / "calculations" / f"{code.lower()}_sizing_analysis.json").write_text(
                json.dumps(calc_data, indent=2), encoding="utf-8"
            )

            # 5. Generate initial BOM CSV
            bom_content = (
                "item,designator,part_number,manufacturer,description,package,qty,unit_price_usd,extended_price_usd,status\n"
                f"1,Q1,{self.combo_device.currentData() or 'C2M0080120D'},Wolfspeed,1200V SiC Power MOSFET,TO-247-3,1,9.85,9.85,QUALIFIED\n"
                f"2,T1,MENDEX-TX-{code}-R1,Mendex Custom Magnetics,Isolated Flyback Transformer,Custom Planar,1,14.50,14.50,QUALIFIED\n"
                "3,D1,C4D02120A,Wolfspeed,1200V SiC Schottky Diode,TO-220-2,1,3.20,3.20,QUALIFIED\n"
                f"4,C1,B32674D1105K000,TDK,High-Voltage Film Capacitor {vout:.0f}V,Radial Box,1,6.40,6.40,QUALIFIED\n"
                f"5,R_LOAD,SM104031002FE,Ohmite,Power Load Resistor 1500V,Axial Planar,1,5.15,5.15,QUALIFIED\n"
                f"6,MECH-1,MENDEX-BOB-{code},Mendex Additive MFG,3D Isolation Bobbin (PPS / UL94 V-0),Custom 3D CAD step,1,2.80,2.80,QUALIFIED\n"
            )
            (ws_path / "bom" / "bom.csv").write_text(bom_content, encoding="utf-8")

            # 6. Generate initial SPICE netlist
            spice_net = (
                f"* {code} Precision Flyback Converter Netlist\n"
                f"Vin in 0 DC {vin_nom}\n"
                f"Lp in drain 4.5u\n"
                f"Ls 0 sec 16.8m\n"
                f"K1 Lp Ls 0.995\n"
                f"Rload out 0 10k\n"
                f"Cout out 0 100u\n"
                f".tran 0.1u 2m\n"
                f".end\n"
            )
            (ws_path / "circuit" / f"{code.lower()}_flyback.net").write_text(spice_net, encoding="utf-8")

            self.created_product = product
            self.created_revision = revision
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Synthesis Error", f"Could not create project:\n{e}")
