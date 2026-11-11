import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.component_library_panel import ComponentLibraryPanel
from mendex_ui.product_lifecycle_panel import ProductEngineeringOverviewPanel


def test_component_library_switchloss_tab(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = ComponentLibraryPanel(service, lambda fn: fn())

    # 1. SwitchLoss tab exists and can be selected
    assert hasattr(panel, "switchloss_widget")
    panel.select_switchloss_tab()
    assert panel.tabs.currentWidget() == panel.switchloss_widget

    # 2. Devices loaded from SwitchLossDB
    assert panel.sw_table.rowCount() >= 8
    assert len(panel._all_sw_records) >= 8

    # 3. Filtering by technology
    panel.sw_tech_filter.setCurrentText("GaN")
    gan_count = panel.sw_table.rowCount()
    assert gan_count >= 2
    for r in range(gan_count):
        assert panel.sw_table.item(r, 2).text() == "GaN"

    # Reset filter
    panel.sw_tech_filter.setCurrentText("All Technologies")
    assert panel.sw_table.rowCount() >= 8

    # 4. Device selection and loss calculation
    panel.sw_table.selectRow(0)
    rec = panel._get_selected_switchloss_record()
    assert rec is not None
    assert rec.part_number in panel.sw_dev_details.toPlainText()
    assert "Conduction Loss" in panel.sw_loss_output.toPlainText()
    assert "Switching Loss" in panel.sw_loss_output.toPlainText()


def test_calculations_tab_switchloss_nav(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = ProductEngineeringOverviewPanel(service)

    # Check button exists
    assert hasattr(panel, "tab_calc")
    buttons = panel.tab_calc.findChildren(type(panel.btn_calc_approve))
    btn_texts = [b.text() for b in buttons]
    assert any("SwitchLossDB" in t for t in btn_texts)
