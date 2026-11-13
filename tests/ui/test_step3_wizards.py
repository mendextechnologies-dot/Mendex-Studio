import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.tradeoff_comparator_dialog import SemiconductorTradeoffComparatorDialog
from mendex_ui.product_wizard_dialog import ProductDesignWizardDialog


def test_tradeoff_comparator_dialog():
    app = QApplication.instance() or QApplication([])
    dlg = SemiconductorTradeoffComparatorDialog()
    assert dlg.res_table.rowCount() == 15  # 5 frequencies * 3 devices
    assert "Trade-Off Insights" in dlg.lbl_summary.text()

    # Change inputs and re-evaluate
    dlg.in_irms.setText("6.0")
    dlg.evaluate()
    assert dlg.res_table.rowCount() == 15
    dlg.close()


def test_product_wizard_dialog(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    wizard = ProductDesignWizardDialog(service)

    # 1. Check tabs exist
    assert wizard.tabs.count() == 4

    # 2. Check preview calculation
    wizard._update_preview()
    assert "DETERMINISTIC SIZING SYNTHESIS PREVIEW" in wizard.txt_preview.toPlainText()
    assert "TRANSFORMER SIZING" in wizard.txt_preview.toPlainText()
    assert "IEC 60664-1" in wizard.txt_preview.toPlainText()

    # 3. Test synthesis of a new project
    wizard.in_code.setText("TEST-HV500")
    wizard.in_name.setText("500V DC Converter Prototype")
    wizard.in_vout.setText("500.0")
    wizard.in_iout.setText("0.2")

    wizard._synthesize_and_create()
    assert wizard.created_product is not None
    assert wizard.created_product.code == "TEST-HV500"

    # Verify workspace files were synthesized
    rev = service.get_revision(wizard.created_product.active_revision_id)
    ws_path = service.workspace_path(rev)
    assert (ws_path / "calculations" / "test-hv500_sizing_analysis.json").exists()
    assert (ws_path / "bom" / "bom.csv").exists()
    assert (ws_path / "circuit" / "test-hv500_flyback.net").exists()
    wizard.close()
