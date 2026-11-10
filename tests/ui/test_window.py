import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mendex_core.models import Specification
from mendex_core.evidence import ManualCheck
from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def test_real_service_editor_roundtrip_and_restart(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    product = service.create_product("MC-100", "Pilot", "transformer", "Engineer")
    window = StudioWindow(service)
    window.show()
    app.processEvents()
    assert window.product.product_id == product.product_id
    window.specification.setPlainText(Specification(vin_nom_v=24, source="Test fixture").model_dump_json())
    window.save()
    window.close()
    reopened = StudioWindow(StudioService(tmp_path))
    assert '24.0' in reopened.specification.toPlainText()
    assert reopened.pages.count() == 11
    reopened.service.record_validation(product.active_revision_id, ManualCheck(check_id="REQ-UI", reviewer="Test engineer", notes="No evidence available"))
    reopened.validation_panel.refresh()
    assert "REQ-UI" in reopened.validation_panel.output.toPlainText()
    reopened.reports_panel.generate()
    assert reopened.reports_panel.list.count() == 1
    assert "FOUND_UNVERIFIED" in reopened.tool_panel.output.toPlainText() or "NOT_INSTALLED" in reopened.tool_panel.output.toPlainText()
    reopened.close()
