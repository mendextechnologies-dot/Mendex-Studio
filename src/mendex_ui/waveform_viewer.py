"""Interactive engineering waveform viewer built with PySide6.QtCharts."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis


class WaveformViewerWidget(QWidget):
    """Enterprise-grade interactive waveform viewer with zoom, pan, and multi-trace support."""

    # Catppuccin Mocha colors for dark theme traces
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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Toolbar
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

        # QtChart
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

    def clear(self):
        self.chart.removeAllSeries()
        self.series_map.clear()

    def set_waveform_data(
        self,
        title: str,
        x_values: List[float],
        traces: Dict[str, List[float]],
        x_label: str = "Time (s)",
        y_label: str = "Amplitude",
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
                {"V(in) [10V Step]": v_in, "V(out) [Capacitor]": v_out},
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
