"""Render the real desktop against disposable data; never modifies user products."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow

app = QApplication([])
font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
if font_path.exists():
    QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont("Segoe UI", 10))
with TemporaryDirectory() as root:
    service = StudioService(Path(root))
    service.create_product("DEMO-100", "Illustrative transformer workspace", "transformer", "Demo engineer")
    window = StudioWindow(service)
    window.navigation.setCurrentRow(1)
    window.show()
    app.processEvents()
    destination = Path(".mendex/qa/day1-desktop.png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(destination)):
        raise RuntimeError("Screenshot failed")
    window.close()
    print(destination.resolve())
