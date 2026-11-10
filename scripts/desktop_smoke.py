"""Render the real desktop against disposable data; never modifies user products."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from mendex_core.service import StudioService
from mendex_core.evidence import ManualCheck
from mendex_ui.window import StudioWindow

app = QApplication([])
font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
if font_path.exists():
    QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont("Segoe UI", 10))
with TemporaryDirectory() as root:
    service = StudioService(Path(root))
    product = service.create_product("DEMO-100", "Illustrative transformer workspace", "transformer", "Demo engineer")
    service.record_validation(product.active_revision_id, ManualCheck(check_id="DEMO-REQ-001", reviewer="Demo engineer", notes="Illustrative workspace: no evidence available; not evaluated"))
    service.generate_report(product.active_revision_id)
    window = StudioWindow(service)
    window.navigation.setCurrentRow(1)
    window.show()
    app.processEvents()
    for index, name in [(1, "products"), (2, "transformer"), (7, "validation"), (8, "reports"), (9, "tools"), (10, "knowledge")]:
        window.navigation.setCurrentRow(index)
        app.processEvents()
        destination = Path(f".mendex/qa/day2-{name}.png")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(destination)):
            raise RuntimeError("Screenshot failed")
    window.close()
    print("Desktop smoke passed: six screens captured under .mendex/qa")
