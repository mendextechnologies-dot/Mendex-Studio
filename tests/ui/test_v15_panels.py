import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def test_generic_ui_to_job_evidence_report_without_product(tmp_path):
    app = QApplication.instance() or QApplication([])
    studio = StudioService(tmp_path)
    window = StudioWindow(studio)
    window.show()
    app.processEvents()
    assert window.tool_center.list.count() == 13
    assert window.navigation.item(0).text() == "Dashboard"
    assert window.navigation.count() == 7
    assert window.navigation.item(1).text() == "Engineering Projects"
    assert window.navigation.item(4).text() == "Engineering Tools"
    window.jobs_panel.create_workspace()
    window.jobs_panel.parameters.setText('{"steps":1,"delay_s":0}')
    window.jobs_panel.start()
    submitted = window.jobs_panel.selected_job()
    studio.integrations.wait(submitted.request.job_id)
    window.jobs_panel.refresh()
    assert "SUCCEEDED" in window.jobs_panel.status.toPlainText()
    assert "SYNTHETIC" in window.jobs_panel.logs.toPlainText()
    assert "NOT_EVALUATED" in window.jobs_panel.evidence.toPlainText()
    window.jobs_panel.preview()
    assert "SYNTHETIC" in window.jobs_panel.artifact_preview.toPlainText()
    window.jobs_panel.report()
    assert "report.html" in window.jobs_panel.report_path.text()
    assert not studio.list_products()  # generic integration workflow, no product design
    window.dataset_panel.version.setText("synthetic-1")
    window.dataset_panel.license.setText("Software fixture authorship reference, not real upstream license approval")
    window.dataset_panel.provenance.setText("Synthetic metadata UI test")
    window.dataset_panel.register()
    assert "NOT_REVIEWED" in window.dataset_panel.output.toPlainText()
    window.close()
