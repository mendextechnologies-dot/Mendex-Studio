"""Render the v1.7 Enterprise UI shell, workspace switcher, and theme."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow

app = QApplication([])
font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
if font.is_file():
    QFontDatabase.addApplicationFont(str(font))
app.setFont(QFont("Segoe UI", 10))

destination = Path(".mendex/qa/v17-enterprise")
destination.mkdir(parents=True, exist_ok=True)

with TemporaryDirectory(prefix="mendex-v17-") as temporary:
    service = StudioService(Path(temporary))
    # 1. Create a product-independent workspace
    ws = service.integrations.create_workspace(
        name="SiC-Inverter-Optimization",
        description="High-voltage 800V automotive traction inverter design",
        owner="Lead Power Engineer",
    )
    
    # 2. Launch Studio Window
    window = StudioWindow(service)
    window.resize(1380, 880)
    window.show()
    app.processEvents()

    # Capture 1: Enterprise Dashboard (Dark Theme)
    window.navigation.setCurrentRow(0)
    app.processEvents()
    if not window.grab().save(str(destination / "dashboard-dark.png")):
        raise RuntimeError("Failed to capture dashboard-dark.png")

    # Capture 2: Enterprise Light Theme
    window.toggle_theme()
    app.processEvents()
    if not window.grab().save(str(destination / "dashboard-light.png")):
        raise RuntimeError("Failed to capture dashboard-light.png")
    window.toggle_theme()  # Return to dark
    app.processEvents()

    # Capture 3: Tool Center (18 tools, 6 native ready)
    window.navigation.setCurrentRow(11)
    app.processEvents()
    if not window.grab().save(str(destination / "tool-center.png")):
        raise RuntimeError("Failed to capture tool-center.png")

    # Capture 4: Jobs & Workspaces
    window.navigation.setCurrentRow(12)
    app.processEvents()
    if not window.grab().save(str(destination / "jobs-workspaces.png")):
        raise RuntimeError("Failed to capture jobs-workspaces.png")

    # Capture 5: Research Center / Datasets
    window.navigation.setCurrentRow(13)
    app.processEvents()
    if not window.grab().save(str(destination / "research-datasets.png")):
        raise RuntimeError("Failed to capture research-datasets.png")

    # Verify no products were created
    assert len(service.list_products()) == 0
    assert len(service.integrations.list_workspaces()) == 1
    window.close()

print("Mendex Studio v1.7 Enterprise UI smoke passed; 5 screens captured under .mendex/qa/v17-enterprise")
