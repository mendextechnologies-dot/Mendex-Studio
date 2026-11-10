"""PCB panel selection/context and background work against disposable roots."""
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from mendex_core.service import StudioService
from mendex_ui.pcb_panel import PCBWorkspacePanel


def test_empty_check_in_background_and_revision_switch(tmp_path):
    app=QApplication.instance() or QApplication([])
    service=StudioService(tmp_path)
    p=service.create_product("PCB-UI","Disposable UI fixture","pcb","Test")
    revision=service.get_revision(p.active_revision_id)
    pcb=service.workspace_path(revision)/"pcb"
    (pcb/"empty.kicad_sch").write_text('(kicad_sch (version 20250114))')
    panel=PCBWorkspacePanel(service,lambda callback:callback())
    assert not panel.erc_button.isEnabled()
    panel.set_revision(revision)
    panel.files.selectRow(0)
    assert panel.erc_button.isEnabled() and not panel.drc_button.isEnabled()
    assert "No placed symbols" in panel.files.item(0,3).text()
    panel.start_check("erc")
    assert panel.is_running() and not panel.erc_button.isEnabled()
    deadline=time.monotonic()+5
    while panel.is_running() and time.monotonic()<deadline:
        app.processEvents();QTest.qWait(10)
    assert not panel.is_running()
    assert panel.history.rowCount()==1
    assert panel.history.item(0,3).text()=="NOT_EVALUATED"
    assert "NOT_EVALUATED" in panel.summary.text()
    next_revision=service.create_revision(p.product_id,"NEXT")
    panel.set_revision(next_revision)
    assert panel.files.rowCount()==0 and panel.history.rowCount()==0
    assert not panel.details.toPlainText()
    panel.set_revision(service.get_revision(revision.revision_id))
    assert not panel.import_button.isEnabled() and panel.notes.isReadOnly()
    panel.set_revision(None)
    assert panel.files.rowCount()==0 and not panel.open_button.isEnabled()
    panel.close()
    service.integrations.shutdown()
