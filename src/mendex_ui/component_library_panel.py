"""Component Library Panel for Mendex Engineering Studio v2.1.

Provides access to verified semiconductor models, magnetic cores, and engineering datasets,
including an interactive SwitchLossDB wide-bandgap and silicon switching loss catalog.
"""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QLineEdit, QComboBox, QPushButton, QTextEdit, QGroupBox,
    QFormLayout, QMessageBox
)

from mendex_core.components.service import ComponentLibraryService
from integrations.datasets.switchloss_db import SwitchLossDB, DeviceSwitchLossRecord
from integrations.calculations.power_losses import calculate_semiconductor_losses
from .workspace_panels import SemiconductorWorkspacePanel, TransformerWorkspacePanel
from .integration_panels import DatasetPanel


class ComponentLibraryPanel(QWidget):
    """Unified component library, magnetic materials, and dataset catalog."""

    def __init__(self, service, guarded_callback=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.guarded = guarded_callback or (lambda fn: fn())
        self.comp_service = ComponentLibraryService()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Tabbed interface for components, switchloss research, magnetics, datasets
        self.tabs = QTabWidget()

        # 1. Power Semiconductors Tab (Project Discrete Catalog)
        semi_widget = QWidget()
        semi_layout = QVBoxLayout(semi_widget)
        semi_layout.setContentsMargins(8, 8, 8, 8)
        self.semi_table = QTableWidget()
        self.semi_table.setColumnCount(6)
        self.semi_table.setHorizontalHeaderLabels([
            "Part Number", "Technology", "V_ds (V)", "I_d (A)", "R_ds(on) (mΩ)", "Package"
        ])
        self.semi_table.horizontalHeader().setStretchLastSection(True)
        self._populate_semiconductors()
        semi_layout.addWidget(self.semi_table)
        self.tabs.addTab(semi_widget, "⚡ Power Semiconductors")

        # 2. SwitchLossDB Research Catalog Tab
        self._init_switchloss_tab()
        self.tabs.addTab(self.switchloss_widget, "🔬 SwitchLossDB Research Catalog")

        # 3. Magnetic Cores & Materials Tab
        mag_widget = QWidget()
        mag_layout = QVBoxLayout(mag_widget)
        mag_layout.setContentsMargins(8, 8, 8, 8)
        self.mag_table = QTableWidget()
        self.mag_table.setColumnCount(6)
        self.mag_table.setHorizontalHeaderLabels([
            "Core Geometry", "Material", "Ae (mm²)", "le (mm)", "Ve (mm³)", "B_sat (T)"
        ])
        self.mag_table.horizontalHeader().setStretchLastSection(True)
        self._populate_magnetics()
        mag_layout.addWidget(self.mag_table)
        self.tabs.addTab(mag_widget, "🧲 Magnetic Cores & Materials")

        # 4. Engineering Datasets & Provenance Tab
        self.dataset_panel = DatasetPanel(self.service, self.guarded)
        self.tabs.addTab(self.dataset_panel, "📚 Datasets & Research Provenance")

        layout.addWidget(self.tabs)

    def select_switchloss_tab(self):
        """Switch view to the SwitchLossDB research catalog."""
        if hasattr(self, "switchloss_widget"):
            self.tabs.setCurrentWidget(self.switchloss_widget)

    def _init_switchloss_tab(self):
        self.switchloss_widget = QWidget()
        layout = QVBoxLayout(self.switchloss_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header with provenance & product explanation
        banner = QFrame()
        banner.setObjectName("switchlossBanner")
        banner.setStyleSheet("""
            #switchlossBanner {
                background-color: rgba(137, 180, 250, 0.08);
                border: 1px solid rgba(137, 180, 250, 0.25);
                border-radius: 6px;
                padding: 10px;
            }
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setContentsMargins(10, 8, 10, 8)
        b_layout.setSpacing(4)

        b_title = QLabel("🔬 SwitchLossDB Semiconductor Research Benchmark Catalog (CC-BY-4.0)")
        b_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #89b4fa;")
        b_layout.addWidget(b_title)

        b_desc = QLabel(
            "Curated wide-bandgap (SiC, GaN) and Silicon power transistor switching loss database. "
            "Provides laboratory-verified turn-on energy (E_on), turn-off energy (E_off), and R_ds(on) across test voltages and currents."
        )
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        b_layout.addWidget(b_desc)

        b_prod_note = QLabel(
            "💡 Why & When is SwitchLossDB used? SwitchLossDB is an open research benchmark dataset for device selection and trade-off comparison. "
            "Whether it is used depends on the product: custom hardware with specific vendor components (such as SV-1000's Wolfspeed C2M0080120D) uses direct datasheet curves. "
            "Select any device below to inspect its parameters, estimate losses, or copy JSON blocks into your project's sizing analysis."
        )
        b_prod_note.setWordWrap(True)
        b_prod_note.setStyleSheet("color: #f9e2af; font-size: 11px; font-weight: 600;")
        b_layout.addWidget(b_prod_note)
        layout.addWidget(banner)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Search:"))
        self.sw_search = QLineEdit()
        self.sw_search.setPlaceholderText("Filter by part number or manufacturer...")
        self.sw_search.textChanged.connect(self._filter_switchloss_devices)
        filter_bar.addWidget(self.sw_search, 2)

        filter_bar.addWidget(QLabel("Technology:"))
        self.sw_tech_filter = QComboBox()
        self.sw_tech_filter.addItems(["All Technologies", "SiC", "GaN", "MOSFET"])
        self.sw_tech_filter.currentIndexChanged.connect(self._filter_switchloss_devices)
        filter_bar.addWidget(self.sw_tech_filter, 1)

        filter_bar.addWidget(QLabel("Min Voltage:"))
        self.sw_volt_filter = QComboBox()
        self.sw_volt_filter.addItems(["All Voltages", "≥ 100 V", "≥ 350 V", "≥ 600 V", "≥ 900 V", "≥ 1200 V"])
        self.sw_volt_filter.currentIndexChanged.connect(self._filter_switchloss_devices)
        filter_bar.addWidget(self.sw_volt_filter, 1)

        self.sw_count_lbl = QLabel("")
        self.sw_count_lbl.setStyleSheet("color: #a6adc8; font-weight: 600;")
        filter_bar.addWidget(self.sw_count_lbl)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # Splitter: Table on left (60%), Inspector & Calculator on right (40%)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Devices table
        self.sw_table = QTableWidget()
        self.sw_table.setColumnCount(11)
        self.sw_table.setHorizontalHeaderLabels([
            "Part Number", "Manufacturer", "Type", "V_ds (V)", "I_d (A)",
            "R_ds(on) (mΩ)", "E_on (µJ)", "E_off (µJ)", "V_test (V)", "I_test (A)", "T_j (°C)"
        ])
        self.sw_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sw_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sw_table.horizontalHeader().setStretchLastSection(True)
        self.sw_table.itemSelectionChanged.connect(self._on_switchloss_selection_changed)
        splitter.addWidget(self.sw_table)

        # Right: Details & Loss Calculator
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(8, 0, 8, 0)
        rp_layout.setSpacing(10)

        # Device Inspection Box
        dev_group = QGroupBox("Selected Device Specification & Provenance")
        dev_layout = QVBoxLayout(dev_group)
        self.sw_dev_details = QTextEdit()
        self.sw_dev_details.setReadOnly(True)
        self.sw_dev_details.setMaximumHeight(130)
        self.sw_dev_details.setFont(QFont("Consolas", 9))
        dev_layout.addWidget(self.sw_dev_details)

        btn_copy_json = QPushButton("📋 Copy Sizing JSON Block")
        btn_copy_json.setStyleSheet("font-weight: 700; color: #89b4fa; background-color: #24273a; border: 1px solid #45475a; padding: 4px 8px; border-radius: 4px;")
        btn_copy_json.clicked.connect(self._copy_switchloss_json)
        dev_layout.addWidget(btn_copy_json)
        rp_layout.addWidget(dev_group)

        # Loss Calculator Box
        calc_group = QGroupBox("Semiconductor Conduction & Switching Loss Estimator")
        c_layout = QFormLayout(calc_group)

        self.sw_in_irms = QLineEdit("4.8")
        self.sw_in_duty = QLineEdit("0.45")
        self.sw_in_fsw = QLineEdit("100.0")

        c_layout.addRow("RMS Drain Current (A):", self.sw_in_irms)
        c_layout.addRow("Duty Cycle (0.0 - 1.0):", self.sw_in_duty)
        c_layout.addRow("Switching Freq (kHz):", self.sw_in_fsw)

        btn_calc_loss = QPushButton("⚡ Estimate Power Dissipation")
        btn_calc_loss.setStyleSheet("font-weight: 700; color: #a6e3a1; background-color: #1b4332; border: 1px solid #2d6a4f; padding: 5px; border-radius: 4px;")
        btn_calc_loss.clicked.connect(self._calculate_selected_loss)
        c_layout.addRow(btn_calc_loss)

        self.sw_loss_output = QTextEdit()
        self.sw_loss_output.setReadOnly(True)
        self.sw_loss_output.setMaximumHeight(110)
        self.sw_loss_output.setFont(QFont("Consolas", 9))
        c_layout.addRow("Loss Breakdown:", self.sw_loss_output)

        rp_layout.addWidget(calc_group)
        rp_layout.addStretch()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Load database
        self.db = SwitchLossDB()
        self._all_sw_records: list[DeviceSwitchLossRecord] = []
        self._filtered_records: list[DeviceSwitchLossRecord] = []
        fixture_path = Path(__file__).parents[1] / "integrations" / "datasets" / "fixtures" / "switchloss_sample.csv"
        if fixture_path.exists():
            self.db.load_csv(fixture_path)
            self._all_sw_records = list(self.db._records)

        self._filter_switchloss_devices()
        if self.sw_table.rowCount() > 0:
            self.sw_table.selectRow(0)

    def _filter_switchloss_devices(self):
        query = self.sw_search.text().strip().lower() if hasattr(self, "sw_search") else ""
        tech = self.sw_tech_filter.currentText() if hasattr(self, "sw_tech_filter") else "All Technologies"
        volt_txt = self.sw_volt_filter.currentText() if hasattr(self, "sw_volt_filter") else "All Voltages"

        min_volt = 0.0
        if "100" in volt_txt:
            min_volt = 100.0
        elif "350" in volt_txt:
            min_volt = 350.0
        elif "600" in volt_txt:
            min_volt = 600.0
        elif "900" in volt_txt:
            min_volt = 900.0
        elif "1200" in volt_txt:
            min_volt = 1200.0

        filtered = []
        for r in self._all_sw_records:
            if query and (query not in r.part_number.lower() and query not in r.manufacturer.lower()):
                continue
            if tech != "All Technologies" and r.device_type.upper() != tech.upper():
                continue
            if r.v_ds_rated_v < min_volt:
                continue
            filtered.append(r)

        self._filtered_records = filtered
        self.sw_table.setRowCount(len(filtered))
        for row, d in enumerate(filtered):
            self.sw_table.setItem(row, 0, QTableWidgetItem(d.part_number))
            self.sw_table.setItem(row, 1, QTableWidgetItem(d.manufacturer))
            self.sw_table.setItem(row, 2, QTableWidgetItem(d.device_type))
            self.sw_table.setItem(row, 3, QTableWidgetItem(f"{d.v_ds_rated_v:.0f}"))
            self.sw_table.setItem(row, 4, QTableWidgetItem(f"{d.i_d_rated_a:.1f}"))
            self.sw_table.setItem(row, 5, QTableWidgetItem(f"{d.r_ds_on_mohm:.1f}" if d.r_ds_on_mohm is not None else "—"))
            self.sw_table.setItem(row, 6, QTableWidgetItem(f"{d.e_on_uj:.1f}" if d.e_on_uj is not None else "—"))
            self.sw_table.setItem(row, 7, QTableWidgetItem(f"{d.e_off_uj:.1f}" if d.e_off_uj is not None else "—"))
            self.sw_table.setItem(row, 8, QTableWidgetItem(f"{d.v_test_v:.0f}" if d.v_test_v is not None else "—"))
            self.sw_table.setItem(row, 9, QTableWidgetItem(f"{d.i_test_a:.1f}" if d.i_test_a is not None else "—"))
            self.sw_table.setItem(row, 10, QTableWidgetItem(f"{d.t_j_c:.0f}" if d.t_j_c is not None else "—"))

        self.sw_count_lbl.setText(f"Showing {len(filtered)} / {len(self._all_sw_records)} verified devices")
        if filtered:
            self.sw_table.selectRow(0)

    def _get_selected_switchloss_record(self) -> DeviceSwitchLossRecord | None:
        sel = self.sw_table.currentRow()
        if 0 <= sel < len(self._filtered_records):
            return self._filtered_records[sel]
        return None

    def _on_switchloss_selection_changed(self):
        rec = self._get_selected_switchloss_record()
        if not rec:
            self.sw_dev_details.setPlainText("No device selected.")
            self.sw_loss_output.setPlainText("Select a device to estimate losses.")
            return

        rds_txt = f"{rec.r_ds_on_mohm} mΩ" if rec.r_ds_on_mohm is not None else "N/A"
        eon_txt = f"{rec.e_on_uj} µJ" if rec.e_on_uj is not None else "N/A"
        eoff_txt = f"{rec.e_off_uj} µJ" if rec.e_off_uj is not None else "N/A"
        vtest_txt = f"{rec.v_test_v} V" if rec.v_test_v is not None else "N/A"
        itest_txt = f"{rec.i_test_a} A" if rec.i_test_a is not None else "N/A"
        tj_txt = f"{rec.t_j_c} °C" if rec.t_j_c is not None else "25 °C"

        details = (
            f"Part Number:   {rec.part_number}\n"
            f"Manufacturer:  {rec.manufacturer} ({rec.device_type})\n"
            f"Ratings:       {rec.v_ds_rated_v} V | {rec.i_d_rated_a} A | Rds(on) = {rds_txt}\n"
            f"Switching:     Eon = {eon_txt} | Eoff = {eoff_txt}\n"
            f"Test Point:    Vtest = {vtest_txt}, Itest = {itest_txt}, Tj = {tj_txt}\n"
            f"Provenance:    SwitchLossDB (CC-BY-4.0) verified fixture"
        )
        self.sw_dev_details.setPlainText(details)
        self._calculate_selected_loss()

    def _calculate_selected_loss(self):
        rec = self._get_selected_switchloss_record()
        if not rec:
            return
        try:
            i_rms = float(self.sw_in_irms.text())
            duty = float(self.sw_in_duty.text())
            f_sw_khz = float(self.sw_in_fsw.text())
            f_sw_hz = f_sw_khz * 1000.0

            r_ds = (rec.r_ds_on_mohm or 50.0) / 1000.0
            e_on_j = ((rec.e_on_uj or 0.0) * 1e-6)
            e_off_j = ((rec.e_off_uj or 0.0) * 1e-6)

            res = calculate_semiconductor_losses(
                part_number=rec.part_number,
                r_ds_on_ohm=r_ds,
                i_rms_a=i_rms,
                duty_cycle=duty,
                e_on_j=e_on_j,
                e_off_j=e_off_j,
                frequency_hz=f_sw_hz,
            )

            p_cond = res.p_conduction_w
            p_sw = res.p_switching_w
            p_tot = res.p_total_w

            out = (
                f"Device: {res.part_number} @ {f_sw_khz:.1f} kHz\n"
                f"Conduction Loss (P_cond): {p_cond:.3f} W\n"
                f"Switching Loss  (P_sw):   {p_sw:.3f} W\n"
                f"Total MOSFET Loss (P_tot): {p_tot:.3f} W\n"
                f"Evaluation: Analytical model (P_cond = Irms² * Rds * D, P_sw = (Eon + Eoff) * fsw)"
            )
            self.sw_loss_output.setPlainText(out)
        except Exception as e:
            self.sw_loss_output.setPlainText(f"Calculation error: {e}")

    def _copy_switchloss_json(self):
        rec = self._get_selected_switchloss_record()
        if not rec:
            return
        r_ds_ohm = round((rec.r_ds_on_mohm or 50.0) / 1000.0, 4)
        e_on_j = round((rec.e_on_uj or 0.0) * 1e-6, 7)
        e_off_j = round((rec.e_off_uj or 0.0) * 1e-6, 7)
        snippet = {
            "semiconductor_losses": {
                "calculation": "semiconductor_losses",
                "part_number": rec.part_number,
                "inputs": {
                    "r_ds_on_ohm": r_ds_ohm,
                    "i_rms_a": float(self.sw_in_irms.text() or 4.8),
                    "duty_cycle": float(self.sw_in_duty.text() or 0.45),
                    "e_on_j": e_on_j,
                    "e_off_j": e_off_j,
                    "frequency_hz": float(self.sw_in_fsw.text() or 100.0) * 1000.0
                },
                "unit": "Watts (W)",
                "provenance": "SwitchLossDB (CC-BY-4.0)"
            }
        }
        json_txt = json.dumps(snippet, indent=2)
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(json_txt)
        QMessageBox.information(
            self,
            "JSON Snippet Copied",
            f"Copied SwitchLossDB sizing parameters for {rec.part_number} to clipboard!\n\nYou can paste this into any sizing analysis JSON.",
        )

    def _populate_semiconductors(self):
        devices = self.comp_service.list_components()
        self.semi_table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            self.semi_table.setItem(row, 0, QTableWidgetItem(getattr(d, "mpn", str(d))))
            self.semi_table.setItem(row, 1, QTableWidgetItem(getattr(d, "category", "mosfet").upper()))
            self.semi_table.setItem(row, 2, QTableWidgetItem(str(getattr(d, "voltage_rating_v", "—"))))
            self.semi_table.setItem(row, 3, QTableWidgetItem(str(getattr(d, "current_rating_a", "—"))))
            rds = getattr(d, "rds_on_ohm", None)
            rds_str = f"{rds * 1000:.2f}" if rds is not None else "—"
            self.semi_table.setItem(row, 4, QTableWidgetItem(rds_str))
            self.semi_table.setItem(row, 5, QTableWidgetItem(getattr(d, "package", "TDSON-8")))

    def _populate_magnetics(self):
        materials = self.comp_service.list_materials()
        self.mag_table.setRowCount(len(materials))
        for row, m in enumerate(materials):
            self.mag_table.setItem(row, 0, QTableWidgetItem(getattr(m, "name", str(m))))
            self.mag_table.setItem(row, 1, QTableWidgetItem(getattr(m, "material_type", "MnZn Ferrite")))
            self.mag_table.setItem(row, 2, QTableWidgetItem(str(getattr(m, "initial_permeability_ui", "—"))))
            self.mag_table.setItem(row, 3, QTableWidgetItem(f"{getattr(m, 'curie_temp_c', 0)} °C"))
            self.mag_table.setItem(row, 4, QTableWidgetItem(f"α={getattr(m, 'steinmetz_alpha', 0)}, β={getattr(m, 'steinmetz_beta', 0)}"))
            self.mag_table.setItem(row, 5, QTableWidgetItem(f"{getattr(m, 'saturation_flux_t', 0.49)} T"))
