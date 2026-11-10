"""Interactive engineering workspace panels for Transformer, DC-DC, Semiconductors, and PCB."""
from pathlib import Path
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget, QMessageBox, QFileDialog,
)

from integrations.calculations.power_losses import calculate_semiconductor_losses
from integrations.calculations.winding_losses import calculate_dowell_ac_resistance
from integrations.calculations.transformer_design import calculate_flyback_transformer_parameters
from integrations.generators.femm_generator import generate_femm_transformer_script
from integrations.generators.freecad_generator import generate_freecad_bobbin_script
from integrations.generators.modelica_generator import generate_openmodelica_flyback_script
from integrations.datasets.switchloss_db import SwitchLossDB


class TransformerWorkspacePanel(QWidget):
    """Interactive workspace panel for high-frequency transformer design & magnetics."""

    def __init__(self, service, guarded, header_label: QLabel):
        super().__init__()
        self.service, self.guarded, self.header_label = service, guarded, header_label

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(header_label)

        # Calculation Box
        calc_group = QGroupBox("Analytical Transformer Sizing & Dowell AC Loss Calculator")
        form = QFormLayout(calc_group)

        self.vin_min = QLineEdit("20.0")
        self.vout = QLineEdit("1000.0")
        self.iout = QLineEdit("0.05")
        self.freq_khz = QLineEdit("100.0")
        self.b_max = QLineEdit("0.22")
        self.ae_mm2 = QLineEdit("52.5")
        self.wire_diam_mm = QLineEdit("0.35")
        self.layers = QLineEdit("2")

        form.addRow("Min Input Voltage (V):", self.vin_min)
        form.addRow("Output Voltage (V):", self.vout)
        form.addRow("Output Current (A):", self.iout)
        form.addRow("Switching Frequency (kHz):", self.freq_khz)
        form.addRow("Peak Flux Density Bmax (T):", self.b_max)
        form.addRow("Core Area Ae (mm²):", self.ae_mm2)
        form.addRow("Wire Conductor Diameter (mm):", self.wire_diam_mm)
        form.addRow("Winding Layers Count:", self.layers)

        btn_layout = QHBoxLayout()
        calc_btn = QPushButton("Calculate Parameters")
        calc_btn.clicked.connect(self.calculate)
        btn_layout.addWidget(calc_btn)

        femm_btn = QPushButton("Export FEMM Lua Script")
        femm_btn.clicked.connect(self.export_femm_script)
        btn_layout.addWidget(femm_btn)

        freecad_btn = QPushButton("Export FreeCAD Bobbin Script")
        freecad_btn.clicked.connect(self.export_freecad_script)
        btn_layout.addWidget(freecad_btn)

        form.addRow(btn_layout)

        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.results_box.setMaximumHeight(180)
        self.results_box.setPlaceholderText("Calculation results will appear here...")
        form.addRow("Analytical Results:", self.results_box)

        main_layout.addWidget(calc_group)
        main_layout.addStretch(1)

    def set_revision(self, revision):
        """Update form fields from revision specifications."""
        if not revision or not getattr(revision, "specification", None):
            return
        spec = revision.specification
        if spec.vin_min_v:
            self.vin_min.setText(str(spec.vin_min_v))
        if spec.vout_v:
            self.vout.setText(str(spec.vout_v))
        if spec.iout_a:
            self.iout.setText(str(spec.iout_a))
        if spec.switching_frequency_hz:
            self.freq_khz.setText(str(spec.switching_frequency_hz / 1000.0))

    def calculate(self):
        try:
            vin_min = float(self.vin_min.text())
            vout = float(self.vout.text())
            iout = float(self.iout.text())
            freq_hz = float(self.freq_khz.text()) * 1000.0
            b_max = float(self.b_max.text())
            ae_mm2 = float(self.ae_mm2.text())
            wire_d = float(self.wire_diam_mm.text())
            layers = int(self.layers.text())

            design = calculate_flyback_transformer_parameters(
                vin_min_v=vin_min,
                vin_nom_v=vin_min * 1.2,
                vout_v=vout,
                iout_a=iout,
                frequency_hz=freq_hz,
                b_max_t=b_max,
                core_ae_mm2=ae_mm2,
            )

            dowell = calculate_dowell_ac_resistance(
                frequency_hz=freq_hz,
                conductor_diameter_mm=wire_d,
                layers_count=layers,
            )

            report = (
                f"=== TRANSFORMER ANALYTICAL SIZING ===\n"
                f"Power Output: {design.power_output_w:.2f} W | Input: {design.power_input_w:.2f} W\n"
                f"Primary Turns (Np): {design.primary_turns} | Secondary Turns (Ns): {design.secondary_turns}\n"
                f"Actual Turns Ratio (Np/Ns): {design.turns_ratio_np_over_ns:.4f}\n"
                f"Primary Inductance (Lm): {design.primary_inductance_uh:.2f} uH\n"
                f"Primary Peak Current: {design.primary_peak_current_a:.3f} A | RMS: {design.primary_rms_current_a:.3f} A\n"
                f"Physical Air Gap Length: {design.air_gap_mm:.4f} mm\n\n"
                f"=== DOWELL HIGH-FREQUENCY WINDING LOSS ===\n"
                f"Skin Depth (delta): {dowell.skin_depth_mm:.4f} mm\n"
                f"Dowell Resistance Factor (Rac/Rdc): {dowell.f_r:.4f}\n"
                f"Effective AC Resistance (Rac): {dowell.r_ac_ohm:.6f} Ohm (for Rdc={dowell.r_dc_ohm} Ohm)\n"
            )
            self.results_box.setPlainText(report)
            return design, dowell
        except Exception as e:
            if not getattr(self, "_suppress_dialogs", False):
                QMessageBox.warning(self, "Calculation Error", str(e))
            raise

    def export_femm_script(self, target_path=None):
        try:
            freq_hz = float(self.freq_khz.text()) * 1000.0
            script = generate_femm_transformer_script(
                core_type="EE",
                primary_turns=24,
                secondary_turns=1000,
                frequency_hz=freq_hz,
            )
            file_path = str(target_path) if target_path else None
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save FEMM Lua Script", "transformer_sim.lua", "Lua Scripts (*.lua)")
            if file_path:
                Path(file_path).write_text(script, encoding="utf-8")
                if not target_path and not getattr(self, "_suppress_dialogs", False):
                    QMessageBox.information(self, "Export Complete", f"FEMM script exported to:\n{file_path}")
            return script
        except Exception as e:
            if not target_path and not getattr(self, "_suppress_dialogs", False):
                QMessageBox.warning(self, "Export Failed", str(e))
            raise

    def export_freecad_script(self, target_path=None):
        try:
            script = generate_freecad_bobbin_script(
                flange_od_mm=32.0,
                core_id_mm=16.0,
                height_mm=25.0,
            )
            file_path = str(target_path) if target_path else None
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save FreeCAD Script", "make_bobbin.py", "Python Scripts (*.py)")
            if file_path:
                Path(file_path).write_text(script, encoding="utf-8")
                if not target_path and not getattr(self, "_suppress_dialogs", False):
                    QMessageBox.information(self, "Export Complete", f"FreeCAD script exported to:\n{file_path}")
            return script
        except Exception as e:
            if not target_path and not getattr(self, "_suppress_dialogs", False):
                QMessageBox.warning(self, "Export Failed", str(e))
            raise


class SemiconductorWorkspacePanel(QWidget):
    """Interactive workspace panel for power semiconductor loss analysis."""

    def __init__(self, service, guarded, header_label: QLabel):
        super().__init__()
        self.service, self.guarded, self.header_label = service, guarded, header_label

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(header_label)

        loss_group = QGroupBox("Semiconductor Conduction & Switching Loss Calculator")
        form = QFormLayout(loss_group)

        # Database Quick Picker
        self.device_picker = QComboBox()
        self.db = SwitchLossDB()
        fixture_path = Path(__file__).parents[1] / "integrations" / "datasets" / "fixtures" / "switchloss_sample.csv"
        self._devices = []
        if fixture_path.exists():
            self.db.load_csv(fixture_path)
            self._devices = self.db._records
            for d in self._devices:
                self.device_picker.addItem(f"{d.part_number} ({d.manufacturer} {d.device_type} {d.v_ds_rated_v}V {d.i_d_rated_a}A)")
            self.device_picker.currentIndexChanged.connect(self._on_device_selected)
        form.addRow("Preset Device (SwitchLossDB):", self.device_picker)

        self.part_number = QLineEdit("C3M0065090D")
        self.r_ds_on_mohm = QLineEdit("65.0")
        self.i_rms = QLineEdit("8.0")
        self.duty = QLineEdit("0.45")
        self.e_on_uj = QLineEdit("85.0")
        self.e_off_uj = QLineEdit("22.0")
        self.f_sw_khz = QLineEdit("100.0")

        form.addRow("Part Number:", self.part_number)
        form.addRow("Rds(on) (mOhm):", self.r_ds_on_mohm)
        form.addRow("RMS Drain Current (A):", self.i_rms)
        form.addRow("Duty Cycle (0.0 - 1.0):", self.duty)
        form.addRow("Turn-on Energy Eon (uJ):", self.e_on_uj)
        form.addRow("Turn-off Energy Eoff (uJ):", self.e_off_uj)
        form.addRow("Switching Frequency (kHz):", self.f_sw_khz)

        calc_btn = QPushButton("Calculate Semiconductor Losses")
        calc_btn.clicked.connect(self.calculate)
        form.addRow(calc_btn)

        self.loss_results = QTextEdit()
        self.loss_results.setReadOnly(True)
        self.loss_results.setMaximumHeight(140)
        form.addRow("Loss Breakdown:", self.loss_results)

        main_layout.addWidget(loss_group)
        main_layout.addStretch(1)

    def set_revision(self, revision):
        """Update form fields from revision specifications."""
        if not revision or not getattr(revision, "specification", None):
            return
        spec = revision.specification
        if spec.iout_a:
            self.i_rms.setText(str(spec.iout_a))
        if spec.switching_frequency_hz:
            self.f_sw_khz.setText(str(spec.switching_frequency_hz / 1000.0))

    def _on_device_selected(self, index):
        if 0 <= index < len(self._devices):
            d = self._devices[index]
            self.part_number.setText(d.part_number)
            if d.r_ds_on_mohm:
                self.r_ds_on_mohm.setText(str(d.r_ds_on_mohm))
            if d.e_on_uj:
                self.e_on_uj.setText(str(d.e_on_uj))
            if d.e_off_uj:
                self.e_off_uj.setText(str(d.e_off_uj))

    def calculate(self):
        try:
            r_ds_on_ohm = float(self.r_ds_on_mohm.text()) / 1000.0
            i_rms = float(self.i_rms.text())
            duty = float(self.duty.text())
            e_on_j = float(self.e_on_uj.text()) * 1e-6
            e_off_j = float(self.e_off_uj.text()) * 1e-6
            f_sw_hz = float(self.f_sw_khz.text()) * 1000.0

            loss = calculate_semiconductor_losses(
                part_number=self.part_number.text(),
                r_ds_on_ohm=r_ds_on_ohm,
                i_rms_a=i_rms,
                duty_cycle=duty,
                e_on_j=e_on_j,
                e_off_j=e_off_j,
                frequency_hz=f_sw_hz,
            )

            res = (
                f"Device: {loss.part_number}\n"
                f"Conduction Loss (P_cond): {loss.p_conduction_w:.3f} W\n"
                f"Switching Loss (P_sw):    {loss.p_switching_w:.3f} W\n"
                f"Total Power Loss:         {loss.p_total_w:.3f} W\n"
                f"Operating Conditions:     D={loss.duty_cycle:.2f}, Fsw={loss.frequency_hz/1000.0:.1f} kHz\n"
            )
            self.loss_results.setPlainText(res)
            return loss
        except Exception as e:
            if not getattr(self, "_suppress_dialogs", False):
                QMessageBox.warning(self, "Calculation Error", str(e))
            raise


class DCDCWorkspacePanel(QWidget):
    """Interactive workspace panel for DC-DC Converter simulation modeling."""

    def __init__(self, service, guarded, header_label: QLabel):
        super().__init__()
        self.service, self.guarded, self.header_label = service, guarded, header_label

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(header_label)

        group = QGroupBox("Modelica Transient Simulation Script Generator")
        form = QFormLayout(group)

        self.vin = QLineEdit("24.0")
        self.vout = QLineEdit("1000.0")
        self.fsw = QLineEdit("100.0")
        self.rload = QLineEdit("20000.0")

        form.addRow("Input Voltage (V):", self.vin)
        form.addRow("Target Output Voltage (V):", self.vout)
        form.addRow("Switching Frequency (kHz):", self.fsw)
        form.addRow("Load Resistance (Ohm):", self.rload)

        export_btn = QPushButton("Export OpenModelica (.mos) Script")
        export_btn.clicked.connect(self.export_script)
        form.addRow(export_btn)

        main_layout.addWidget(group)
        main_layout.addStretch(1)

    def set_revision(self, revision):
        """Update form fields from revision specifications."""
        if not revision or not getattr(revision, "specification", None):
            return
        spec = revision.specification
        if spec.vin_nom_v:
            self.vin.setText(str(spec.vin_nom_v))
        elif spec.vin_min_v:
            self.vin.setText(str(spec.vin_min_v))
        if spec.vout_v:
            self.vout.setText(str(spec.vout_v))
        if spec.switching_frequency_hz:
            self.fsw.setText(str(spec.switching_frequency_hz / 1000.0))
        if spec.vout_v and spec.iout_a and spec.iout_a > 0:
            self.rload.setText(str(round(spec.vout_v / spec.iout_a, 2)))

    def export_script(self, target_path=None):
        try:
            script = generate_openmodelica_flyback_script(
                vin_v=float(self.vin.text()),
                vout_target_v=float(self.vout.text()),
                f_sw_hz=float(self.fsw.text()) * 1000.0,
                r_load_ohm=float(self.rload.text()),
            )
            file_path = str(target_path) if target_path else None
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Modelica Script", "flyback.mos", "Modelica Scripts (*.mos)")
            if file_path:
                Path(file_path).write_text(script, encoding="utf-8")
                if not target_path and not getattr(self, "_suppress_dialogs", False):
                    QMessageBox.information(self, "Export Complete", f"OpenModelica script exported to:\n{file_path}")
            return script
        except Exception as e:
            if not target_path and not getattr(self, "_suppress_dialogs", False):
                QMessageBox.warning(self, "Export Failed", str(e))
            raise
