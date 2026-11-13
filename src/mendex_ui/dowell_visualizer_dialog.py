"""Dowell High-Frequency AC Winding Loss & Skin Effect Visualizer Dialog.

Provides interactive evaluation of skin depth, proximity effect, Dowell AC-to-DC
resistance multiplier (F_R = R_ac / R_dc), and conductor recommendations (solid wire,
copper foil, or high-frequency stranded Litz wire).
"""
from __future__ import annotations

import json
import math
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPen, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QFrame,
    QGroupBox, QMessageBox, QWidget
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries

from mendex_core.intelligence.calculations import DeterministicCalculationService


class DowellWindingLossDialog(QDialog):
    """Interactive visualizer for high-frequency transformer winding Dowell AC resistance."""

    WIRE_PRESETS = {
        "AWG 22 (0.644 mm)": 0.644,
        "AWG 24 (0.511 mm)": 0.511,
        "AWG 26 (0.405 mm)": 0.405,
        "AWG 28 (0.321 mm)": 0.321,
        "AWG 30 (0.255 mm)": 0.255,
        "Planar PCB Copper (0.105 mm - 3oz)": 0.105,
        "Planar PCB Copper (0.070 mm - 2oz)": 0.070,
        "Planar PCB Copper (0.035 mm - 1oz)": 0.035,
        "Custom Diameter / Thickness": None,
    }

    def __init__(self, parent=None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.calc_service = DeterministicCalculationService()
        self.setWindowTitle("🧲 Dowell High-Frequency Winding Loss & Skin Effect Visualizer")
        self.resize(880, 680)
        if self.is_dark:
            self.setStyleSheet("background-color: #11111b; color: #cdd6f4;")
        self.init_ui()
        self.recalculate()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header banner
        header = QFrame()
        header.setStyleSheet("background-color: #1e1e2e; border: 1px solid #313244; border-radius: 8px;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(4)

        t_lbl = QLabel("🧲 Dowell Analytical High-Frequency AC Winding Factor (F_R = R_ac / R_dc)")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #89b4fa;")
        h_layout.addWidget(t_lbl)

        d_lbl = QLabel(
            "Evaluates high-frequency eddy current, skin depth (δ), and proximity factor across multi-layer transformer windings. "
            "Recommends solid copper wire (F_R ≤ 1.5), copper foil (1.5 < F_R ≤ 3.0), or stranded Litz wire (F_R > 3.0)."
        )
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("color: #a6adc8; font-size: 11px;")
        h_layout.addWidget(d_lbl)
        root.addWidget(header)

        # Controls & KPI strip in a 2-column or grid layout
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Left: Parameter inputs
        param_box = QGroupBox("Winding & Operating Parameters")
        param_box.setStyleSheet("QGroupBox { font-weight: 700; color: #cdd6f4; background-color: #181825; border: 1px solid #313244; border-radius: 6px; margin-top: 6px; padding-top: 10px; }")
        p_grid = QGridLayout(param_box)
        p_grid.setContentsMargins(10, 10, 10, 10)
        p_grid.setSpacing(8)

        # 1. Frequency
        p_grid.addWidget(QLabel("Switching Frequency (f_sw):"), 0, 0)
        self.spin_fsw = QDoubleSpinBox()
        self.spin_fsw.setRange(10.0, 1000.0)
        self.spin_fsw.setValue(100.0)
        self.spin_fsw.setSuffix(" kHz")
        self.spin_fsw.valueChanged.connect(self.recalculate)
        p_grid.addWidget(self.spin_fsw, 0, 1)

        # 2. Number of Layers
        p_grid.addWidget(QLabel("Number of Winding Layers (m):"), 1, 0)
        self.spin_layers = QSpinBox()
        self.spin_layers.setRange(1, 12)
        self.spin_layers.setValue(2)
        self.spin_layers.valueChanged.connect(self.recalculate)
        p_grid.addWidget(self.spin_layers, 1, 1)

        # 3. Conductor Preset
        p_grid.addWidget(QLabel("Conductor Type / Gauge:"), 2, 0)
        self.combo_wire = QComboBox()
        self.combo_wire.addItems(list(self.WIRE_PRESETS.keys()))
        self.combo_wire.setCurrentText("AWG 26 (0.405 mm)")
        self.combo_wire.currentTextChanged.connect(self._on_wire_preset_changed)
        p_grid.addWidget(self.combo_wire, 2, 1)

        # 4. Conductor Diameter / Thickness
        p_grid.addWidget(QLabel("Conductor Diameter / Height (d):"), 3, 0)
        self.spin_d = QDoubleSpinBox()
        self.spin_d.setRange(0.01, 5.0)
        self.spin_d.setDecimals(3)
        self.spin_d.setValue(0.405)
        self.spin_d.setSuffix(" mm")
        self.spin_d.valueChanged.connect(self.recalculate)
        p_grid.addWidget(self.spin_d, 3, 1)

        # 5. Temperature
        p_grid.addWidget(QLabel("Winding Temperature (T):"), 4, 0)
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(20.0, 180.0)
        self.spin_temp.setValue(100.0)
        self.spin_temp.setSuffix(" °C")
        self.spin_temp.valueChanged.connect(self.recalculate)
        p_grid.addWidget(self.spin_temp, 4, 1)

        # 6. DC Resistance
        p_grid.addWidget(QLabel("DC Winding Resistance (R_dc):"), 5, 0)
        self.spin_rdc = QDoubleSpinBox()
        self.spin_rdc.setRange(0.1, 1000.0)
        self.spin_rdc.setValue(45.0)
        self.spin_rdc.setSuffix(" mΩ")
        self.spin_rdc.valueChanged.connect(self.recalculate)
        p_grid.addWidget(self.spin_rdc, 5, 1)

        top_row.addWidget(param_box, 1)

        # Right: KPI Results Strip
        kpi_box = QGroupBox("Analytical High-Frequency Readouts")
        kpi_box.setStyleSheet("QGroupBox { font-weight: 700; color: #cdd6f4; background-color: #181825; border: 1px solid #313244; border-radius: 6px; margin-top: 6px; padding-top: 10px; }")
        k_layout = QVBoxLayout(kpi_box)
        k_layout.setContentsMargins(10, 10, 10, 10)
        k_layout.setSpacing(6)

        self.lbl_skin_depth = QLabel("<b>Skin Depth (δ):</b> 0.236 mm")
        self.lbl_skin_depth.setStyleSheet("color: #a6adc8; font-size: 12px;")
        k_layout.addWidget(self.lbl_skin_depth)

        self.lbl_xi = QLabel("<b>Normalized Height (ξ = h/δ):</b> 1.85")
        self.lbl_xi.setStyleSheet("color: #a6adc8; font-size: 12px;")
        k_layout.addWidget(self.lbl_xi)

        self.lbl_fr = QLabel("<b>Dowell Factor (F_R = R_ac / R_dc):</b> 3.78x")
        self.lbl_fr.setStyleSheet("color: #fab387; font-size: 14px; font-weight: 700;")
        k_layout.addWidget(self.lbl_fr)

        self.lbl_rac = QLabel("<b>Effective AC Resistance (R_ac):</b> 170.1 mΩ")
        self.lbl_rac.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        k_layout.addWidget(self.lbl_rac)

        # Wire Recommendation Badge
        self.badge_recommendation = QLabel("RECOMMENDATION PENDING")
        self.badge_recommendation.setWordWrap(True)
        self.badge_recommendation.setAlignment(Qt.AlignCenter)
        self.badge_recommendation.setStyleSheet(
            "background-color: #3b2f15; color: #f9e2af; font-weight: 700; padding: 8px 10px; border-radius: 6px; border: 1px solid #7c5e10;"
        )
        k_layout.addWidget(self.badge_recommendation)
        k_layout.addStretch()

        top_row.addWidget(kpi_box, 1)
        root.addLayout(top_row)

        # Interactive QtChart: Dowell Factor F_R vs Frequency Curve
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px;")
        cf_layout = QVBoxLayout(chart_frame)
        cf_layout.setContentsMargins(4, 4, 4, 4)

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.NoAnimation)
        self.chart.setTitle("Dowell AC Winding Loss Factor (F_R) vs Frequency Sweep (20 kHz – 500 kHz)")
        self.chart.setTitleBrush(QColor("#cdd6f4"))
        self.chart.setBackgroundBrush(QColor("#181825"))
        self.chart.legend().setAlignment(Qt.AlignBottom)
        self.chart.legend().setLabelBrush(QColor("#cdd6f4"))

        self.series_fr = QLineSeries()
        self.series_fr.setName("F_R (R_ac / R_dc)")
        pen_fr = QPen(QColor("#89b4fa"), 2.5)
        self.series_fr.setPen(pen_fr)
        self.chart.addSeries(self.series_fr)

        # Limit lines: Solid limit (F_R = 1.5) and Foil limit (F_R = 3.0)
        self.series_limit_solid = QLineSeries()
        self.series_limit_solid.setName("Solid Wire Limit (1.5x)")
        pen_solid = QPen(QColor("#a6e3a1"), 1.5, Qt.DashLine)
        self.series_limit_solid.setPen(pen_solid)
        self.chart.addSeries(self.series_limit_solid)

        self.series_limit_foil = QLineSeries()
        self.series_limit_foil.setName("Foil/Interleaved Limit (3.0x)")
        pen_foil = QPen(QColor("#fab387"), 1.5, Qt.DashLine)
        self.series_limit_foil.setPen(pen_foil)
        self.chart.addSeries(self.series_limit_foil)

        # Current Operating Point Marker
        self.series_current = QScatterSeries()
        self.series_current.setName("Current Operating Point")
        self.series_current.setMarkerSize(10.0)
        self.series_current.setColor(QColor("#f38ba8"))
        self.chart.addSeries(self.series_current)

        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Frequency (kHz)")
        self.axis_x.setRange(20.0, 500.0)
        self.axis_x.setGridLinePen(QPen(QColor("#313244"), 1, Qt.DotLine))
        self.axis_x.setLabelsBrush(QColor("#a6adc8"))
        self.axis_x.setTitleBrush(QColor("#a6adc8"))
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Dowell Factor F_R")
        self.axis_y.setRange(1.0, 10.0)
        self.axis_y.setGridLinePen(QPen(QColor("#313244"), 1, Qt.DotLine))
        self.axis_y.setLabelsBrush(QColor("#a6adc8"))
        self.axis_y.setTitleBrush(QColor("#a6adc8"))
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self.series_fr.attachAxis(self.axis_x)
        self.series_fr.attachAxis(self.axis_y)
        self.series_limit_solid.attachAxis(self.axis_x)
        self.series_limit_solid.attachAxis(self.axis_y)
        self.series_limit_foil.attachAxis(self.axis_x)
        self.series_limit_foil.attachAxis(self.axis_y)
        self.series_current.attachAxis(self.axis_x)
        self.series_current.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(self.chart_view.renderHints())
        cf_layout.addWidget(self.chart_view)
        root.addWidget(chart_frame, 1)

        # Bottom Actions Row
        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Dowell Sizing JSON Snippet")
        btn_copy.setStyleSheet("background-color: #24273a; color: #89b4fa; font-weight: 700; border: 1px solid #45475a; padding: 6px 14px; border-radius: 4px;")
        btn_copy.clicked.connect(self._copy_sizing_json)
        btn_row.addWidget(btn_copy)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _on_wire_preset_changed(self, text: str):
        val = self.WIRE_PRESETS.get(text)
        if val is not None:
            self.spin_d.setValue(val)

    def recalculate(self):
        fsw_khz = self.spin_fsw.value()
        fsw_hz = fsw_khz * 1000.0
        m_layers = self.spin_layers.value()
        d_mm = self.spin_d.value()
        temp_c = self.spin_temp.value()
        rdc_mohm = self.spin_rdc.value()
        rdc_ohm = rdc_mohm / 1000.0

        try:
            res = self.calc_service.calculate_dowell_analysis(
                frequency_hz=fsw_hz,
                conductor_diameter_mm=d_mm,
                num_layers=m_layers,
                temperature_c=temp_c,
                layer_porosity_factor=0.85,
                r_dc_ohm=rdc_ohm,
            )
        except Exception as e:
            self.lbl_fr.setText(f"Error: {e}")
            return

        delta_mm = res.outputs["skin_depth_mm"]
        h_eff_mm = res.outputs["h_eff_mm"]
        xi = res.outputs["xi_ratio"]
        fr = res.outputs["f_r"]
        rac_ohm = res.outputs["r_ac_ohm"]
        rac_mohm = rac_ohm * 1000.0

        self.lbl_skin_depth.setText(f"<b>Skin Depth (δ):</b> {delta_mm:.3f} mm")
        self.lbl_xi.setText(f"<b>Normalized Conductor Height (ξ = h/δ):</b> {xi:.3f}")
        self.lbl_fr.setText(f"<b>Dowell Factor (F_R = R_ac / R_dc):</b> {fr:.2f}x")
        self.lbl_rac.setText(f"<b>Effective AC Resistance (R_ac):</b> {rac_mohm:.2f} mΩ")

        # Recommendation badge
        if fr <= 1.5:
            self.badge_recommendation.setText("✅ PASS: Solid Copper Magnet Wire Suitable\n(Minimal proximity penalty; F_R ≤ 1.5)")
            self.badge_recommendation.setStyleSheet("background-color: #1b4332; color: #a6e3a1; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #2d6a4f;")
        elif fr <= 3.0:
            self.badge_recommendation.setText("⚠️ CAUTION: Copper Foil or Interleaved Winding Recommended\n(Moderate AC eddy penalty; 1.5 < F_R ≤ 3.0)")
            self.badge_recommendation.setStyleSheet("background-color: #3b2f15; color: #f9e2af; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #7c5e10;")
        else:
            self.badge_recommendation.setText("❌ SEVERE PROXIMITY PENALTY: Stranded Litz Wire Mandatory\n(High AC loss; use strands with diameter ≤ 2δ ≈ " + f"{2*delta_mm:.2f} mm)")
            self.badge_recommendation.setStyleSheet("background-color: #3e1b1b; color: #f38ba8; font-weight: 700; padding: 6px 10px; border-radius: 6px; border: 1px solid #7a2828;")

        # Update Plot Frequency Sweep (20 kHz to 500 kHz)
        self.series_fr.clear()
        self.series_limit_solid.clear()
        self.series_limit_foil.clear()
        self.series_current.clear()

        max_fr = 4.0
        frequencies = [20.0 + i * 10.0 for i in range(49)]  # 20 to 500 kHz
        for f_k in frequencies:
            sw_res = self.calc_service.calculate_dowell_analysis(
                frequency_hz=f_k * 1000.0,
                conductor_diameter_mm=d_mm,
                num_layers=m_layers,
                temperature_c=temp_c,
                layer_porosity_factor=0.85,
                r_dc_ohm=rdc_ohm,
            )
            val_fr = sw_res.outputs["f_r"]
            self.series_fr.append(f_k, val_fr)
            self.series_limit_solid.append(f_k, 1.5)
            self.series_limit_foil.append(f_k, 3.0)
            if val_fr > max_fr:
                max_fr = val_fr

        # Marker at operating point
        self.series_current.append(fsw_khz, fr)

        # Scale Y axis with margin
        self.axis_y.setRange(1.0, min(25.0, math.ceil(max_fr * 1.25)))

    def _copy_sizing_json(self):
        fsw_khz = self.spin_fsw.value()
        m_layers = self.spin_layers.value()
        d_mm = self.spin_d.value()
        temp_c = self.spin_temp.value()
        rdc_mohm = self.spin_rdc.value()

        res = self.calc_service.calculate_dowell_analysis(
            frequency_hz=fsw_khz * 1000.0,
            conductor_diameter_mm=d_mm,
            num_layers=m_layers,
            temperature_c=temp_c,
            layer_porosity_factor=0.85,
            r_dc_ohm=rdc_mohm / 1000.0,
        )

        data = {
            "dowell_high_frequency_ac_winding_factor": {
                "calculation": "dowell_ac_resistance",
                "frequency_khz": fsw_khz,
                "conductor_diameter_mm": d_mm,
                "winding_layers": m_layers,
                "temperature_deg_c": temp_c,
                "skin_depth_mm": res.outputs["skin_depth_mm"],
                "normalized_height_xi": res.outputs["xi_ratio"],
                "dowell_factor_fr": res.outputs["f_r"],
                "r_dc_mohm": rdc_mohm,
                "r_ac_mohm": round(res.outputs["r_ac_ohm"] * 1000.0, 2),
                "verdict": "PASS" if res.outputs["compliant"] == 1.0 else ("CAUTION" if res.outputs["compliant"] == 0.5 else "HIGH_LOSS"),
                "provenance": "Deterministic Dowell Equation (1966) analytical model"
            }
        }
        json_txt = json.dumps(data, indent=2)
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(json_txt)
        QMessageBox.information(
            self,
            "JSON Snippet Copied",
            "Copied Dowell high-frequency winding loss parameters to clipboard!\n\nYou can paste this into sizing analysis JSON.",
        )
