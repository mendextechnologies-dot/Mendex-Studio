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
    x_pts = [i * 1e-4 for i in range(20)]
    y_pts = [5.0 if i >= 10 else 0.0 for i in range(20)]
    viewer.set_waveform_data(
        "Custom Transient",
        x_pts,
        {"V_out": y_pts},
    )
    app.processEvents()
    assert viewer.chart.title() == "Custom Transient"
    assert "V_out" in viewer.series_map

    # Test automated signal metrics
    assert "Peak" in viewer.lbl_vmax.text()
    assert "5.0" in viewer.lbl_vmax.text()
    assert "Ripple" in viewer.lbl_vpp.text()

    # Test interactive cursors
    viewer.btn_cursors.setChecked(True)
    app.processEvents()
    assert viewer.cursor_panel.isVisible()
    assert viewer._cursor_a_series is not None
    assert viewer._cursor_b_series is not None

    viewer.slider_a.setValue(100)
    viewer.slider_b.setValue(900)
    app.processEvents()
    assert "Δt:" in viewer.lbl_delta_t.text()
    assert "Freq" in viewer.lbl_freq.text()
    assert "ΔV:" in viewer.lbl_delta_v.text()

    # Toggle cursors off
    viewer.btn_cursors.setChecked(False)
    app.processEvents()
    assert not viewer.cursor_panel.isVisible()

    # Test FFT Harmonic Spectrum
    viewer.btn_fft.setChecked(True)
    app.processEvents()
    assert "FFT" in viewer.chart.title()

    viewer.btn_fft.setChecked(False)
    app.processEvents()
    assert "Custom Transient" in viewer.chart.title()

    # Test theme toggle
    viewer.apply_theme(False)  # Light
    app.processEvents()
    viewer.apply_theme(True)   # Dark
    app.processEvents()

    # Test reset zoom and grid toggle
    viewer.reset_zoom()
    viewer.toggle_grid()
    viewer.close()
