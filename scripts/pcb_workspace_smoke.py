"""Render the PCB workspace with disposable empty CAD; no product data changed."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import argparse
import json
import time
from pathlib import Path

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    service=StudioService(args.output/"disposable-data")
    product=service.create_product("PCB-QA","Empty CAD interface test; not a converter design","pcb","QA fixture")
    revision=service.get_revision(product.active_revision_id)
    folder=service.workspace_path(revision)/"pcb"
    (folder/"empty.kicad_sch").write_text('(kicad_sch (version 20250114))')
    (folder/"outline.kicad_pcb").write_text('(kicad_pcb (version 20240108) (gr_rect (start 0 0) (end 42 25)))')
    service.pcb.save_review_notes(revision.revision_id,"QA fixture only. Proposed 42 x 25 mm board envelope; clearance and isolation review NOT_EVALUATED. No engineering approval.")
    app=QApplication.instance() or QApplication([])
    font_path=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/segoeui.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
    app.setFont(QFont("Segoe UI",10))
    window=StudioWindow(service)
    window.resize(1500,1000)
    window.navigation.setCurrentRow(5)
    window.show()
    panel=window.pcb_ws
    panel.files.selectRow(next(i for i in range(panel.files.rowCount()) if panel.files.item(i,0).text().endswith('.kicad_sch')))
    panel.start_check("erc")
    deadline=time.monotonic()+10
    while panel.is_running() and time.monotonic()<deadline:
        app.processEvents();QTest.qWait(20)
    assert not panel.is_running(),"Check worker did not finish"
    assert panel.history.item(0,3).text()=="NOT_EVALUATED"
    assert window.pages.currentIndex()==5 and panel.files.rowCount()==2
    app.processEvents()
    assert window.grab().save(str(args.output/"pcb-workspace-dark.png"))
    window.toggle_theme();app.processEvents()
    assert window.grab().save(str(args.output/"pcb-workspace-light.png"))
    service.create_revision(product.product_id,"NEXT")
    window.refresh()
    window.revisions.setCurrentIndex(0)
    app.processEvents()
    assert not panel.import_button.isEnabled()
    assert window.grab().save(str(args.output/"pcb-workspace-archived.png"))
    (args.output/"result.json").write_text(json.dumps({"status":"PASS","scope":"Disposable desktop UI smoke; no engineering qualification", "checks":["Navigation page 5","Empty schematic NOT_EVALUATED","Background check completed","Dark/light renders","Archived editing disabled"]},indent=2),encoding="utf-8")
    window.close()
    app.processEvents()
    print(f"PCB desktop smoke passed: {args.output}")


if __name__=="__main__":
    main()
