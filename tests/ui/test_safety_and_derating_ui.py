import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_core.intelligence.calculations import DeterministicCalculationService
from mendex_ui.product_lifecycle_panel import ProductEngineeringOverviewPanel


def test_deterministic_safety_and_derating_math():
    calc = DeterministicCalculationService()

    # 1. IEC 60664-1 & 61010-1 Clearance and Creepage
    res = calc.calculate_iec_creepage_clearance(
        working_voltage_rms=1000.0,
        peak_voltage_v=1000.0,
        pollution_degree=2,
        material_group="IIIa",
        insulation_type="reinforced",
        slot_width_mm=5.0,
    )
    assert res.outputs["required_clearance_mm"] == 5.0  # 2 * 2.5mm
    assert res.outputs["required_creepage_mm"] == 20.0  # 2 * 10mm
    assert res.outputs["compliant"] == 1.0

    # Test basic insulation with insufficient slot
    res_fail = calc.calculate_iec_creepage_clearance(
        working_voltage_rms=1000.0,
        peak_voltage_v=1000.0,
        pollution_degree=2,
        material_group="IIIa",
        insulation_type="reinforced",
        slot_width_mm=2.0,  # Less than required 5.0mm
    )
    assert res_fail.outputs["compliant"] == 0.0

    # 2. Component Derating (IPC-9592B)
    res_mosfet = calc.calculate_component_derating("mosfet", 600.0, 1200.0)
    assert res_mosfet.outputs["stress_ratio"] == 0.50
    assert res_mosfet.outputs["compliant"] == 1.0

    res_resistor = calc.calculate_component_derating("resistor", 8.0, 10.0)
    assert res_resistor.outputs["stress_ratio"] == 0.80
    assert res_resistor.outputs["compliant"] == 0.0  # Exceeds 60% resistor limit


def test_ui_pcb_safety_and_bom_derating():
    app = QApplication.instance() or QApplication([])
    service = StudioService(Path(r"C:\Mendex studio"))
    panel = ProductEngineeringOverviewPanel(service)

    # Set to SV-1000
    prods = service.list_products()
    if prods:
        p = prods[0]
        panel.set_product(p.product_id, p.active_revision_id)
        app.processEvents()

        # Audit IEC safety
        panel._audit_iec_safety(quiet=True)
        assert "5.0 mm" in panel.lbl_s3.text()
        assert "COMPLIANT" in panel.lbl_s4.text()

        # Audit BOM derating
        panel._audit_bom_derating(quiet=True)
        assert panel.bom_table.rowCount() == 6
        assert "Industrial Derating" in panel.lbl_bom_summary.text()
        assert panel.bom_table.columnCount() == 10

        # Check Q1 and R_LOAD status
        q1_status = panel.bom_table.item(0, 8).text()
        assert "PASS" in q1_status
