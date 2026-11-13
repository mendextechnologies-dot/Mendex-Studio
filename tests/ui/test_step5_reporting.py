"""Tests for Step 5: Team Collaboration & Executive Reporting (Revision Diff & Dossier Export)."""
import os
import gc
gc.disable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from mendex_core.service import StudioService
from mendex_core.models import Specification
from mendex_ui.revision_diff_dialog import RevisionDiffDialog
from mendex_ui.product_lifecycle_panel import ProductEngineeringOverviewPanel

_KEEP_ALIVE = []


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_executive_dossier_html_generation(tmp_path):
    service = StudioService(tmp_path)
    prod = service.create_product(code="TST-100", name="Test Converter", category="dc_dc_converter", owner="Test Engineer")
    rev = service.get_revision(prod.active_revision_id)
    service.update_specification(
        rev.revision_id,
        Specification(vin_nom_v=24.0, vout_v=500.0, iout_a=0.2, switching_frequency_hz=100000.0)
    )

    report = service.generate_report(rev.revision_id)
    assert report is not None
    assert report.report_path.endswith("report.html")

    report_file = tmp_path / report.report_path
    assert report_file.exists()
    html_content = report_file.read_text(encoding="utf-8")

    # Verify Executive Dossier components
    assert "Mendex Engineering Dossier" in html_content
    assert "Executive Summary & Design Envelope" in html_content
    assert "Switching Frequency" in html_content
    assert "window.print()" in html_content  # Print to PDF button
    assert "@media print" in html_content
    assert "Frozen input and evidence snapshot" in html_content


def test_revision_diff_dialog_ui(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    service = StudioService(tmp_path)
    prod = service.create_product(code="TST-200", name="Diff Test Product", category="dc_dc_converter", owner="Test Engineer")
    rev1 = service.get_revision(prod.active_revision_id)
    service.update_specification(
        rev1.revision_id,
        Specification(vin_nom_v=24.0, vout_v=500.0, iout_a=0.2, switching_frequency_hz=100000.0)
    )

    # Branch a second revision R002 with modified specifications
    rev2 = service.create_revision(prod.product_id, "R002")
    service.update_specification(
        rev2.revision_id,
        Specification(vin_nom_v=28.0, vout_v=600.0, iout_a=0.25, switching_frequency_hz=150000.0)
    )

    dlg = RevisionDiffDialog(service, prod.product_id, rev1_id=rev1.revision_id, rev2_id=rev2.revision_id)
    _KEEP_ALIVE.append(dlg)

    # 1. Check revision selector
    assert dlg.combo_rev_a.count() == 2
    assert dlg.combo_rev_b.count() == 2
    assert "Comparison:" in dlg.lbl_summary_bar.text()

    # 2. Check specifications diff table
    assert dlg.table_specs.rowCount() >= 8
    # Vin nom changed 24 -> 28: should indicate MODIFIED
    vin_row = -1
    for r in range(dlg.table_specs.rowCount()):
        if "Input Voltage Nom" in dlg.table_specs.item(r, 0).text():
            vin_row = r
            break
    assert vin_row >= 0
    assert "24.0" in dlg.table_specs.item(vin_row, 1).text()
    assert "28.0" in dlg.table_specs.item(vin_row, 2).text()
    assert "MODIFIED" in dlg.table_specs.item(vin_row, 3).text()

    # 3. Check sizing diff table
    assert dlg.table_sizing.rowCount() >= 5

    # 4. Check swap button
    dlg._swap_revisions()
    assert "28.0" in dlg.table_specs.item(vin_row, 1).text()
    assert "24.0" in dlg.table_specs.item(vin_row, 2).text()

    # 5. Check copy actions do not raise errors
    dlg._copy_diff_markdown()
    dlg._copy_diff_json()
    dlg.close()


def test_product_lifecycle_diff_and_dossier_buttons(qapp, tmp_path):
    service = StudioService(tmp_path)
    prod = service.create_product(code="TST-300", name="Panel Buttons Test", category="dc_dc_converter", owner="Test Engineer")
    plc = ProductEngineeringOverviewPanel(service)
    _KEEP_ALIVE.append(plc)
    plc.set_product(prod.product_id, prod.active_revision_id)

    # Check that Compare Revisions and Export Dossier buttons exist
    buttons = plc.findChildren(type(plc.btn_edit_spec))
    btn_texts = [b.text() for b in buttons]
    assert any("Compare Revisions" in t for t in btn_texts)
    assert any("Export Engineering Dossier" in t for t in btn_texts)
