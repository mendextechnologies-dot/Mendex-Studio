"""Interactive engineering waveform viewer built with PySide6.QtCharts.

Provides real-time signal metrics (V_max, V_min, V_pp ripple, V_avg, V_rms),
interactive measurement cursors (Cursor A & B, dt, frequency, dV, dV/dt slew rate),
and single-click Fast Fourier Transform (FFT) harmonic spectrum analysis.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QMessageBox, QFrame, QSlider, QGridLayout
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis


class WaveformViewerWidget(QWidget):
    """Enterprise-grade interactive waveform viewer with zoom, pan, measurement cursors,

    automated ripple & RMS metrics, and FFT spectrum analysis.
    """

    DARK_PALETTE = [
        QColor("#89b4fa"),  # Blue
        QColor("#a6e3a1"),  # Green
        QColor("#f9e2af"),  # Yellow
        QColor("#f38ba8"),  # Red / Pink
        QColor("#cba6f7"),  # Mauve
        QColor("#fab387"),  # Peach
    ]

    LIGHT_PALETTE = [
        QColor("#0066cc"),
        QColor("#2d8a4e"),
        QColor("#b06000"),
        QColor("#c92a2a"),
        QColor("#6741d9"),
        QColor("#e67700"),
    ]

    def __init__(self, parent=None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.series_map: Dict[str, QLineSeries] = {}
        self._raw_x_values: List[float] = []
        self._raw_traces: Dict[str, List[float]] = {}
        self._active_trace: str = ""
        self._cursor_a_series: Optional[QLineSeries] = None
        self._cursor_b_series: Optional[QLineSeries] = None
        self._fft_active: bool = False
        self._original_title: str = ""
        self._original_x_label: str = "Time (s)"
        self._original_y_label: str = "Amplitude"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # 1. Main Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl = QLabel("Waveform Canvas:")
        lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
        toolbar.addWidget(lbl)

        self.benchmark_combo = QComboBox()
        self.benchmark_combo.addItems([
            "RC Step Transient (10V, tau=1ms)",
            "Flyback Switch Ringing (CCM 100kHz)",
            "Half-Bridge PWM Inverter (800V)",
            "Custom SPICE Output (.raw)",
        ])
        self.benchmark_combo.currentIndexChanged.connect(self._on_benchmark_changed)
        toolbar.addWidget(self.benchmark_combo)

        # Trace selector for metrics and cursors
        toolbar.addWidget(QLabel("Active Trace:"))
        self.combo_trace = QComboBox()
        self.combo_trace.currentIndexChanged.connect(self._on_active_trace_changed)
        toolbar.addWidget(self.combo_trace)

        # Toggle Cursors tool
        self.btn_cursors = QPushButton("📍 Cursors")
        self.btn_cursors.setCheckable(True)
        self.btn_cursors.setToolTip("Toggle interactive time/voltage measurement cursors (Cursor A & B)")
        self.btn_cursors.toggled.connect(self._toggle_cursors)
        toolbar.addWidget(self.btn_cursors)

        # Toggle FFT tool
        self.btn_fft = QPushButton("📊 FFT Spectrum")
        self.btn_fft.setCheckable(True)
        self.btn_fft.setToolTip("Compute Fast Fourier Transform (FFT) harmonic spectrum of active trace")
        self.btn_fft.toggled.connect(self._toggle_fft)
        toolbar.addWidget(self.btn_fft)

        btn_reset = QPushButton("Reset Zoom")
        btn_reset.setToolTip("Reset pan and zoom to show all data")
        btn_reset.clicked.connect(self.reset_zoom)
        toolbar.addWidget(btn_reset)

        btn_grid = QPushButton("Toggle Grid")
        btn_grid.clicked.connect(self.toggle_grid)
        toolbar.addWidget(btn_grid)

        btn_export = QPushButton("Export PNG")
        btn_export.clicked.connect(self.export_image)
        toolbar.addWidget(btn_export)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 2. Automated Signal Metrics Strip
        self.metrics_frame = QFrame()
        self.metrics_frame.setObjectName("metricsFrame")
        self.metrics_frame.setStyleSheet("""
            #metricsFrame {
                background-color: rgba(30, 30, 46, 0.85);
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        m_layout = QHBoxLayout(self.metrics_frame)
        m_layout.setContentsMargins(8, 4, 8, 4)
        m_layout.setSpacing(14)

        self.lbl_vmax = QLabel("Peak (Vmax): —")
        self.lbl_vmax.setStyleSheet("font-weight: 700; color: #a6e3a1; font-size: 11px;")
        m_layout.addWidget(self.lbl_vmax)

        self.lbl_vmin = QLabel("Min (Vmin): —")
        self.lbl_vmin.setStyleSheet("font-weight: 600; color: #89b4fa; font-size: 11px;")
        m_layout.addWidget(self.lbl_vmin)

        self.lbl_vpp = QLabel("Ripple (ΔVpp): —")
        self.lbl_vpp.setStyleSheet("font-weight: 700; color: #f9e2af; font-size: 11px;")
        m_layout.addWidget(self.lbl_vpp)

        self.lbl_ripple_pct = QLabel("Ripple %: —")
        self.lbl_ripple_pct.setStyleSheet("font-weight: 600; color: #fab387; font-size: 11px;")
        m_layout.addWidget(self.lbl_ripple_pct)

        self.lbl_vavg = QLabel("DC Avg: —")
        self.lbl_vavg.setStyleSheet("font-weight: 600; color: #cdd6f4; font-size: 11px;")
        m_layout.addWidget(self.lbl_vavg)

        self.lbl_vrms = QLabel("RMS: —")
        self.lbl_vrms.setStyleSheet("font-weight: 600; color: #cba6f7; font-size: 11px;")
        m_layout.addWidget(self.lbl_vrms)

        m_layout.addStretch()
        layout.addWidget(self.metrics_frame)

        # 3. Interactive Cursor Measurement Panel (Collapsible)
        self.cursor_panel = QFrame()
        self.cursor_panel.setObjectName("cursorPanel")
        self.cursor_panel.setStyleSheet("""
            #cursorPanel {
                background-color: rgba(24, 24, 37, 0.95);
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        cp_layout = QGridLayout(self.cursor_panel)
        cp_layout.setContentsMargins(8, 6, 8, 6)
        cp_layout.setHorizontalSpacing(10)
        cp_layout.setVerticalSpacing(4)

        # Cursor A
        cp_layout.addWidget(QLabel("Cursor A (Cyan):"), 0, 0)
        self.slider_a = QSlider(Qt.Horizontal)
        self.slider_a.setRange(0, 1000)
        self.slider_a.setValue(200)
        self.slider_a.valueChanged.connect(self._on_cursors_moved)
        cp_layout.addWidget(self.slider_a, 0, 1)
        self.lbl_cursor_a_val = QLabel("tA: — | VA: —")
        self.lbl_cursor_a_val.setStyleSheet("font-family: Consolas; font-weight: 600; color: #00f0ff;")
        cp_layout.addWidget(self.lbl_cursor_a_val, 0, 2)

        # Cursor B
        cp_layout.addWidget(QLabel("Cursor B (Orange):"), 1, 0)
        self.slider_b = QSlider(Qt.Horizontal)
        self.slider_b.setRange(0, 1000)
        self.slider_b.setValue(800)
        self.slider_b.valueChanged.connect(self._on_cursors_moved)
        cp_layout.addWidget(self.slider_b, 1, 1)
        self.lbl_cursor_b_val = QLabel("tB: — | VB: —")
        self.lbl_cursor_b_val.setStyleSheet("font-family: Consolas; font-weight: 600; color: #ff9e3b;")
        cp_layout.addWidget(self.lbl_cursor_b_val, 1, 2)

        # Delta Readouts
        delta_row = QHBoxLayout()
        delta_row.setSpacing(16)
        self.lbl_delta_t = QLabel("Δt: —")
        self.lbl_delta_t.setStyleSheet("font-weight: 700; color: #a6e3a1; font-family: Consolas;")
        delta_row.addWidget(self.lbl_delta_t)

        self.lbl_freq = QLabel("Freq (1/Δt): —")
        self.lbl_freq.setStyleSheet("font-weight: 700; color: #f9e2af; font-family: Consolas;")
        delta_row.addWidget(self.lbl_freq)

        self.lbl_delta_v = QLabel("ΔV: —")
        self.lbl_delta_v.setStyleSheet("font-weight: 700; color: #89b4fa; font-family: Consolas;")
        delta_row.addWidget(self.lbl_delta_v)

        self.lbl_slew = QLabel("Slew Rate (dV/dt): —")
        self.lbl_slew.setStyleSheet("font-weight: 700; color: #f38ba8; font-family: Consolas;")
        delta_row.addWidget(self.lbl_slew)
        delta_row.addStretch()

        cp_layout.addLayout(delta_row, 2, 0, 1, 3)
        self.cursor_panel.setVisible(False)
        layout.addWidget(self.cursor_panel)

        # 4. QtChart Canvas
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.NoAnimation)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)

        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(self.chart_view.renderHints())
        self.chart_view.setRubberBand(QChartView.RectangleRubberBand)
        layout.addWidget(self.chart_view, 1)

        self.apply_theme(self.is_dark)
        self.load_benchmark_data(0)

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if is_dark:
            self.chart.setBackgroundBrush(QColor("#181825"))
            self.chart.setTitleBrush(QColor("#cdd6f4"))
            self.chart.legend().setLabelBrush(QColor("#cdd6f4"))

            grid_pen = QPen(QColor("#313244"))
            grid_pen.setStyle(Qt.DotLine)
            self.axis_x.setGridLinePen(grid_pen)
            self.axis_y.setGridLinePen(grid_pen)
            self.axis_x.setLabelsBrush(QColor("#a6adc8"))
            self.axis_y.setLabelsBrush(QColor("#a6adc8"))
            self.axis_x.setTitleBrush(QColor("#a6adc8"))
            self.axis_y.setTitleBrush(QColor("#a6adc8"))
            if hasattr(self, "metrics_frame"):
                self.metrics_frame.setStyleSheet("""
                    #metricsFrame {
                        background-color: rgba(30, 30, 46, 0.85);
                        border: 1px solid #313244;
                        border-radius: 6px;
                        padding: 4px;
                    }
                """)
            if hasattr(self, "cursor_panel"):
                self.cursor_panel.setStyleSheet("""
                    #cursorPanel {
                        background-color: rgba(24, 24, 37, 0.95);
                        border: 1px solid #45475a;
                        border-radius: 6px;
                        padding: 6px;
                    }
                """)
        else:
            self.chart.setBackgroundBrush(QColor("#ffffff"))
            self.chart.setTitleBrush(QColor("#212529"))
            self.chart.legend().setLabelBrush(QColor("#212529"))

            grid_pen = QPen(QColor("#dee2e6"))
            grid_pen.setStyle(Qt.DotLine)
            self.axis_x.setGridLinePen(grid_pen)
            self.axis_y.setGridLinePen(grid_pen)
            self.axis_x.setLabelsBrush(QColor("#495057"))
            self.axis_y.setLabelsBrush(QColor("#495057"))
            self.axis_x.setTitleBrush(QColor("#495057"))
            self.axis_y.setTitleBrush(QColor("#495057"))
            if hasattr(self, "metrics_frame"):
                self.metrics_frame.setStyleSheet("""
                    #metricsFrame {
                        background-color: #f8f9fa;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        padding: 4px;
                    }
                """)
            if hasattr(self, "cursor_panel"):
                self.cursor_panel.setStyleSheet("""
                    #cursorPanel {
                        background-color: #f1f3f5;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        padding: 6px;
                    }
                """)

    def clear(self):
        self.chart.removeAllSeries()
        self.series_map.clear()
        self._cursor_a_series = None
        self._cursor_b_series = None

    def set_waveform_data(
        self,
        title: str,
        x_values: List[float],
        traces: Dict[str, List[float]],
        x_label: str = "Time (s)",
        y_label: str = "Amplitude",
    ):
        self._raw_x_values = list(x_values)
        self._raw_traces = {k: list(v) for k, v in traces.items()}
        self._original_title = title
        self._original_x_label = x_label
        self._original_y_label = y_label
        self._fft_active = False
        if hasattr(self, "btn_fft"):
            self.btn_fft.blockSignals(True)
            self.btn_fft.setChecked(False)
            self.btn_fft.blockSignals(False)

        self._render_traces(title, x_values, traces, x_label, y_label)

        # Update trace selector
        self.combo_trace.blockSignals(True)
        self.combo_trace.clear()
        for k in traces.keys():
            self.combo_trace.addItem(k)
        if traces:
            self._active_trace = list(traces.keys())[0]
            self.combo_trace.setCurrentIndex(0)
        self.combo_trace.blockSignals(False)

        self._update_metrics()
        if self.btn_cursors.isChecked():
            self._render_cursors()

    def _render_traces(
        self,
        title: str,
        x_values: List[float],
        traces: Dict[str, List[float]],
        x_label: str,
        y_label: str,
    ):
        self.clear()
        self.chart.setTitle(title)
        self.axis_x.setTitleText(x_label)
        self.axis_y.setTitleText(y_label)

        if not x_values or not traces:
            return

        min_x = min(x_values)
        max_x = max(x_values)
        min_y = float("inf")
        max_y = float("-inf")

        palette = self.DARK_PALETTE if self.is_dark else self.LIGHT_PALETTE

        for idx, (trace_name, y_values) in enumerate(traces.items()):
            series = QLineSeries()
            series.setName(trace_name)
            color = palette[idx % len(palette)]
            pen = QPen(color)
            pen.setWidthF(1.8)
            series.setPen(pen)

            points = []
            for x, y in zip(x_values, y_values):
                points.append(QPointF(x, y))
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

            series.append(points)
            self.chart.addSeries(series)
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)
            self.series_map[trace_name] = series

        pad_y = (max_y - min_y) * 0.1 if max_y > min_y else 1.0
        self.axis_x.setRange(min_x, max_x)
        self.axis_y.setRange(min_y - pad_y, max_y + pad_y)

    def _on_active_trace_changed(self, index: int):
        if index >= 0 and self.combo_trace.count() > 0:
            self._active_trace = self.combo_trace.currentText()
            self._update_metrics()
            if self.btn_cursors.isChecked():
                self._on_cursors_moved()

    def _update_metrics(self):
        """Calculates deterministic signal parameters for the active trace."""
        if not self._raw_traces or not self._active_trace or self._active_trace not in self._raw_traces:
            return
        y_arr = np.array(self._raw_traces[self._active_trace], dtype=float)
        if len(y_arr) == 0:
            return

        v_max = float(np.max(y_arr))
        v_min = float(np.min(y_arr))
        v_pp = v_max - v_min
        v_avg = float(np.mean(y_arr))
        v_rms = float(np.sqrt(np.mean(y_arr ** 2)))

        ripple_pct = (v_pp / abs(v_avg) * 100.0) if abs(v_avg) > 1e-4 else 0.0

        def _fmt(val: float, unit: str = "V") -> str:
            if abs(val) >= 1000:
                return f"{val:.1f} {unit}"
            elif abs(val) >= 1:
                return f"{val:.2f} {unit}"
            elif abs(val) >= 1e-3:
                return f"{val * 1e3:.2f} m{unit}"
            else:
                return f"{val * 1e6:.2f} µ{unit}"

        self.lbl_vmax.setText(f"Peak (Vmax): {_fmt(v_max)}")
        self.lbl_vmin.setText(f"Min (Vmin): {_fmt(v_min)}")
        self.lbl_vpp.setText(f"Ripple (ΔVpp): {_fmt(v_pp)}")
        self.lbl_ripple_pct.setText(f"Ripple %: {ripple_pct:.1f}%")
        self.lbl_vavg.setText(f"DC Avg: {_fmt(v_avg)}")
        self.lbl_vrms.setText(f"RMS: {_fmt(v_rms)}")

    def _toggle_cursors(self, checked: bool):
        self.cursor_panel.setVisible(checked)
        if checked:
            self._render_cursors()
        else:
            if self._cursor_a_series:
                self.chart.removeSeries(self._cursor_a_series)
                self._cursor_a_series = None
            if self._cursor_b_series:
                self.chart.removeSeries(self._cursor_b_series)
                self._cursor_b_series = None

    def _render_cursors(self):
        if not self._raw_x_values:
            return
        min_x = self.axis_x.min()
        max_x = self.axis_x.max()
        min_y = self.axis_y.min()
        max_y = self.axis_y.max()

        frac_a = self.slider_a.value() / 1000.0
        frac_b = self.slider_b.value() / 1000.0
        t_a = min_x + frac_a * (max_x - min_x)
        t_b = min_x + frac_b * (max_x - min_x)

        if not self._cursor_a_series:
            self._cursor_a_series = QLineSeries()
            self._cursor_a_series.setName("Cursor A")
            pen_a = QPen(QColor("#00f0ff") if self.is_dark else QColor("#0088cc"))
            pen_a.setStyle(Qt.DashLine)
            pen_a.setWidthF(1.5)
            self._cursor_a_series.setPen(pen_a)
            self.chart.addSeries(self._cursor_a_series)
            self._cursor_a_series.attachAxis(self.axis_x)
            self._cursor_a_series.attachAxis(self.axis_y)

        if not self._cursor_b_series:
            self._cursor_b_series = QLineSeries()
            self._cursor_b_series.setName("Cursor B")
            pen_b = QPen(QColor("#ff9e3b") if self.is_dark else QColor("#d97706"))
            pen_b.setStyle(Qt.DashLine)
            pen_b.setWidthF(1.5)
            self._cursor_b_series.setPen(pen_b)
            self.chart.addSeries(self._cursor_b_series)
            self._cursor_b_series.attachAxis(self.axis_x)
            self._cursor_b_series.attachAxis(self.axis_y)

        self._cursor_a_series.replace([QPointF(t_a, min_y), QPointF(t_a, max_y)])
        self._cursor_b_series.replace([QPointF(t_b, min_y), QPointF(t_b, max_y)])

        self._update_cursor_readouts(t_a, t_b)

    def _on_cursors_moved(self):
        if not self.btn_cursors.isChecked() or not self._raw_x_values:
            return
        min_x = self.axis_x.min()
        max_x = self.axis_x.max()
        min_y = self.axis_y.min()
        max_y = self.axis_y.max()

        t_a = min_x + (self.slider_a.value() / 1000.0) * (max_x - min_x)
        t_b = min_x + (self.slider_b.value() / 1000.0) * (max_x - min_x)

        if self._cursor_a_series:
            self._cursor_a_series.replace([QPointF(t_a, min_y), QPointF(t_a, max_y)])
        if self._cursor_b_series:
            self._cursor_b_series.replace([QPointF(t_b, min_y), QPointF(t_b, max_y)])

        self._update_cursor_readouts(t_a, t_b)

    def _interpolate_y(self, t: float) -> float:
        if not self._raw_x_values or not self._active_trace or self._active_trace not in self._raw_traces:
            return 0.0
        x = np.array(self._raw_x_values)
        y = np.array(self._raw_traces[self._active_trace])
        return float(np.interp(t, x, y))

    def _update_cursor_readouts(self, t_a: float, t_b: float):
        v_a = self._interpolate_y(t_a)
        v_b = self._interpolate_y(t_b)

        def _fmt_t(t: float) -> str:
            if abs(t) >= 1:
                return f"{t:.3f} s"
            elif abs(t) >= 1e-3:
                return f"{t * 1e3:.3f} ms"
            elif abs(t) >= 1e-6:
                return f"{t * 1e6:.3f} µs"
            else:
                return f"{t * 1e9:.1f} ns"

        def _fmt_v(v: float) -> str:
            if abs(v) >= 1000:
                return f"{v:.1f} V"
            elif abs(v) >= 1:
                return f"{v:.2f} V"
            elif abs(v) >= 1e-3:
                return f"{v * 1e3:.2f} mV"
            else:
                return f"{v * 1e6:.2f} µV"

        self.lbl_cursor_a_val.setText(f"tA: {_fmt_t(t_a)} | VA: {_fmt_v(v_a)}")
        self.lbl_cursor_b_val.setText(f"tB: {_fmt_t(t_b)} | VB: {_fmt_v(v_b)}")

        dt = abs(t_b - t_a)
        dv = abs(v_b - v_a)
        self.lbl_delta_t.setText(f"Δt: {_fmt_t(dt)}")
        self.lbl_delta_v.setText(f"ΔV: {_fmt_v(dv)}")

        if dt > 1e-12:
            freq = 1.0 / dt
            if freq >= 1e6:
                freq_str = f"{freq / 1e6:.2f} MHz"
            elif freq >= 1e3:
                freq_str = f"{freq / 1e3:.2f} kHz"
            else:
                freq_str = f"{freq:.1f} Hz"
            self.lbl_freq.setText(f"Freq (1/Δt): {freq_str}")

            slew_v_per_us = (dv / dt) * 1e-6
            self.lbl_slew.setText(f"Slew Rate (dV/dt): {slew_v_per_us:.2f} V/µs")
        else:
            self.lbl_freq.setText("Freq (1/Δt): —")
            self.lbl_slew.setText("Slew Rate (dV/dt): —")

    def _toggle_fft(self, checked: bool):
        """Switches between Time-Domain waveform and FFT Harmonic Spectrum."""
        if checked:
            self._show_fft_spectrum()
        else:
            self._render_traces(
                self._original_title,
                self._raw_x_values,
                self._raw_traces,
                self._original_x_label,
                self._original_y_label,
            )
            if self.btn_cursors.isChecked():
                self._render_cursors()

    def _show_fft_spectrum(self):
        if not self._raw_x_values or not self._active_trace or self._active_trace not in self._raw_traces:
            return
        x = np.array(self._raw_x_values)
        y = np.array(self._raw_traces[self._active_trace])
        if len(x) < 4:
            return

        # Uniform interpolation for accurate FFT
        dt_est = np.median(np.diff(x))
        if dt_est <= 0:
            return
        n_pts = min(2048, len(x))
        x_uniform = np.linspace(x[0], x[-1], n_pts)
        y_uniform = np.interp(x_uniform, x, y)
        dt = x_uniform[1] - x_uniform[0]

        # Single-sided FFT
        fft_vals = np.fft.rfft(y_uniform)
        freqs = np.fft.rfftfreq(n_pts, d=dt)
        mags = (2.0 / n_pts) * np.abs(fft_vals)

        # Truncate DC component for clean harmonic visualization
        if len(freqs) > 1:
            freqs = freqs[1:]
            mags = mags[1:]

        # Convert frequency to kHz
        freqs_khz = [float(f / 1000.0) for f in freqs]
        mags_v = [float(m) for m in mags]

        self.clear()
        self.chart.setTitle(f"Harmonic Spectrum (FFT): {self._active_trace}")
        self.axis_x.setTitleText("Frequency (kHz)")
        self.axis_y.setTitleText("Amplitude (V)")

        series = QLineSeries()
        series.setName(f"FFT Spectrum of {self._active_trace}")
        pen = QPen(QColor("#a6e3a1") if self.is_dark else QColor("#2d8a4e"))
        pen.setWidthF(1.8)
        series.setPen(pen)

        for f_khz, m in zip(freqs_khz, mags_v):
            series.append(QPointF(f_khz, m))

        self.chart.addSeries(series)
        series.attachAxis(self.axis_x)
        series.attachAxis(self.axis_y)

        min_f = min(freqs_khz) if freqs_khz else 0.0
        max_f = max(freqs_khz) if freqs_khz else 1000.0
        max_m = max(mags_v) if mags_v else 1.0

        self.axis_x.setRange(min_f, max_f)
        self.axis_y.setRange(0.0, max_m * 1.15)

    def _on_benchmark_changed(self, index: int):
        self.load_benchmark_data(index)

    def load_raw_file(self, raw_path: Path | str) -> bool:
        """Parses and renders real solver output waveforms from an ASCII .raw file."""
        p = Path(raw_path)
        if not p.exists():
            return False
        try:
            from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms
            parsed = parse_ascii_raw_waveforms(p)
            if not parsed or "time" not in parsed:
                return False
            time_arr = [float(x) for x in parsed["time"]]
            traces = {k: [float(x) for x in v] for k, v in parsed.items() if k.lower() != "time"}
            if traces:
                self.set_waveform_data(
                    f"Measured Solver Waveforms: {p.name}",
                    time_arr,
                    traces,
                    x_label="Time (s)",
                    y_label="Amplitude (V / A)",
                )
                return True
        except Exception:
            pass
        return False

    def load_benchmark_data(self, index: int):
        if index == 0:
            # RC Step: V(in) = 10V step, V(out) = 10*(1 - exp(-t/1ms))
            n_points = 200
            t_max = 5e-3
            x = [i * (t_max / n_points) for i in range(n_points + 1)]
            v_in = [10.0 if t >= 0 else 0.0 for t in x]
            v_out = [10.0 * (1.0 - math.exp(-t / 1e-3)) for t in x]
            self.set_waveform_data(
                "Transient Analysis: RC Integrator Benchmark",
                x,
                {"V(out) [Capacitor]": v_out, "V(in) [10V Step]": v_in},
                x_label="Time (s)",
                y_label="Voltage (V)",
            )
        elif index == 1:
            # Flyback CCM switch voltage: 24V bus + 100V reflected + ringing
            n_points = 300
            t_max = 20e-6  # 2 cycles at 100kHz
            x = [i * (t_max / n_points) for i in range(n_points + 1)]
            v_ds = []
            i_pri = []
            for t in x:
                phase = (t % 10e-6) / 10e-6
                if phase < 0.5:
                    # Switch ON
                    v_ds.append(0.5)
                    i_pri.append(10.0 * phase * 2)
                else:
                    # Switch OFF with ringing
                    ring = 15.0 * math.exp(-(phase - 0.5) * 8) * math.sin(2 * math.pi * 10 * phase)
                    v_ds.append(60.0 + ring)
                    i_pri.append(0.0)
            self.set_waveform_data(
                "Flyback CCM Primary MOSFET: V_DS and I_PRI",
                x,
                {"V_DS (Drain-Source) [V]": v_ds, "I_PRI (Primary Current) [A]": i_pri},
                x_label="Time (s)",
                y_label="Amplitude",
            )
        elif index == 2:
            # 800V Traction Inverter PWM
            n_points = 300
            t_max = 50e-6
            x = [i * (t_max / n_points) for i in range(n_points + 1)]
            pwm = [800.0 if (i // 25) % 2 == 0 else 0.0 for i in range(n_points + 1)]
            i_phase = [150.0 * math.sin(2 * math.pi * 1000 * t) for t in x]
            self.set_waveform_data(
                "SiC Traction Inverter 800V Bus Phase Switching",
                x,
                {"V_Phase (PWM) [V]": pwm, "I_Phase (Filtered) [A]": i_phase},
                x_label="Time (s)",
                y_label="Amplitude",
            )

    def reset_zoom(self):
        self.chart.zoomReset()

    def toggle_grid(self):
        self.axis_x.setGridLineVisible(not self.axis_x.isGridLineVisible())
        self.axis_y.setGridLineVisible(not self.axis_y.isGridLineVisible())

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Waveform Image", "waveform.png", "PNG Image (*.png)")
        if path:
            pixmap = self.chart_view.grab()
            pixmap.save(path)
            QMessageBox.information(self, "Export Complete", f"Waveform saved to:\n{path}")
