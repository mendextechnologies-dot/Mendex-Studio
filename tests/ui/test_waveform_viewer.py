"""Test interactive WaveformViewerWidget with PySide6.QtCharts."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from mendex_ui.waveform_viewer import WaveformViewerWidget


def test_waveform_viewer_widget():
    app = QApplication.instance() or QApplication([])
    viewer = WaveformViewerWidget()
    viewer.resize(800, 600)
    viewer.show()
    app.processEvents()

    assert viewer.chart.title() != ""
    assert len(viewer.series_map) > 0

    # Test benchmark switching
    viewer.load_benchmark_data(1)
    app.processEvents()
    assert "Flyback" in viewer.chart.title()

    # Test custom data
    viewer.set_waveform_data(
        "Custom Transient",
        [0.0, 1e-3, 2e-3],
        {"V_out": [0.0, 5.0, 5.0]},
    )
    app.processEvents()
    assert viewer.chart.title() == "Custom Transient"
    assert "V_out" in viewer.series_map

    # Test theme toggle
    viewer.apply_theme(False)  # Light
    app.processEvents()
    viewer.apply_theme(True)   # Dark
    app.processEvents()

    # Test reset zoom and grid toggle
    viewer.reset_zoom()
    viewer.toggle_grid()
    viewer.close()
