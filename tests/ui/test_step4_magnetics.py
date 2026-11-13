"""Tests for Step 4: Magnetics Design & Core Loss Comparator (MagNet Dataset & Dowell Visualizer)."""
import os
import gc
gc.disable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_core.intelligence.calculations import DeterministicCalculationService
from mendex_core.components.service import ComponentLibraryService
from mendex_ui.dowell_visualizer_dialog import DowellWindingLossDialog
from mendex_ui.magnetic_comparator_dialog import MagneticCoreLossComparatorDialog
from mendex_ui.component_library_panel import ComponentLibraryPanel


# Retain references to prevent premature C++ Qt object destruction
_KEEP_ALIVE = []


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dowell_analysis_calculation():
    svc = DeterministicCalculationService()
    res = svc.calculate_dowell_analysis(
        frequency_hz=100000.0,
        conductor_diameter_mm=0.405,  # AWG 26
        num_layers=2,
        temperature_c=100.0,
        layer_porosity_factor=0.85,
        r_dc_ohm=0.045
    )
    assert res.formula_id == "EQ-DOWELL-02"
    assert 0.20 <= res.outputs["skin_depth_mm"] <= 0.26
    assert res.outputs["f_r"] >= 1.0
    assert res.outputs["r_ac_ohm"] >= 0.045
    assert len(res.notes) >= 3


def test_magnetic_core_sizing_and_loss_calculation():
    svc = DeterministicCalculationService()
    res = svc.calculate_magnetic_core_sizing_and_loss(
        frequency_hz=100000.0,
        b_peak_t=0.18,
        core_volume_mm3=2470.0,  # Planar E22/6/16
        core_ae_mm2=78.5,
        cm=16.9,
        alpha=1.25,
        beta=2.35,
        b_sat_t=0.40,
        vin_v=24.0,
        duty_cycle=0.45
    )
    assert res.formula_id == "EQ-MAGNET-01"
    assert res.outputs["volumetric_loss_w_m3"] > 0.0
    assert res.outputs["total_core_loss_w"] > 0.0
    assert res.outputs["calculated_primary_turns"] > 0.0
    assert 40.0 <= res.outputs["saturation_margin_pct"] <= 60.0
    assert res.outputs["compliant"] == 1.0


def test_dowell_visualizer_dialog_ui(qapp):
    dlg = DowellWindingLossDialog(is_dark=True)
    _KEEP_ALIVE.append(dlg)
    assert dlg.spin_fsw.value() == 100.0
    assert dlg.spin_layers.value() == 2

    # Verify initial calculation readouts
    assert "mm" in dlg.lbl_skin_depth.text()
    assert "F_R" in dlg.lbl_fr.text()
    assert dlg.series_fr.count() > 20  # Frequency sweep populated
    assert dlg.series_current.count() == 1  # Current operating point marker

    # Change wire preset to AWG 28
    dlg.combo_wire.setCurrentText("AWG 28 (0.321 mm)")
    assert abs(dlg.spin_d.value() - 0.321) < 1e-4

    # Change frequency and verify recalculation
    dlg.spin_fsw.setValue(200.0)
    dlg.recalculate()
    assert "200" not in dlg.lbl_skin_depth.text()


def test_magnetic_comparator_dialog_ui(qapp):
    dlg = MagneticCoreLossComparatorDialog(is_dark=True)
    _KEEP_ALIVE.append(dlg)
    assert len(dlg.cards) == 3
    assert len(dlg.cores) >= 5
    assert len(dlg.materials) >= 4

    # Verify candidate 1 readouts
    c1 = dlg.cards[0]
    assert "Ae:" in c1.lbl_ae.text()
    assert "Total Core Loss:" in c1.lbl_pcore.text()
    assert "PASS" in c1.badge_status.text() or "MARGINAL" in c1.badge_status.text()

    # Modify global operating frequency
    dlg.spin_fsw.setValue(150.0)
    dlg.recalculate()
    assert "W" in c1.lbl_pcore.text()


def test_component_library_panel_magnetics_tab(qapp, tmp_path):
    service = StudioService(tmp_path)
    panel = ComponentLibraryPanel(service, lambda fn: fn())
    _KEEP_ALIVE.append(panel)
    panel.select_magnetics_tab()
    assert panel.tabs.currentWidget() == panel.mag_widget

    # Cores and Materials tables populated
    assert panel.cores_table.rowCount() >= 5
    assert panel.mag_table.rowCount() >= 4

    # Quick Estimator test
    panel.in_est_fsw.setText("120.0")
    panel._recalculate_mag_loss()
    assert "Volumetric Loss:" in panel.txt_est_mag_output.toPlainText()
    assert "MagNet" in panel.txt_est_mag_output.toPlainText()
