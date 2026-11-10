"""Headless offscreen smoke test for Mendex Engineering Studio v1.9 Visual Workflow Studio."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def run_smoke():
    app = QApplication.instance() or QApplication([])

    test_root = root_dir / ".mendex" / "qa" / "v19_temp"
    test_root.mkdir(parents=True, exist_ok=True)
    service = StudioService(test_root)

    window = StudioWindow(service)
    window.resize(1400, 900)
    window.show()
    app.processEvents()

    # Navigate to Workflow Studio (Page 14)
    window.navigation.setCurrentRow(14)
    app.processEvents()

    # Verify panel is active
    wf_panel = window.workflow_studio
    wf_panel.load_template(1)
    app.processEvents()

    # Execute workflow synchronously for smoke
    rec = service.workflow_engine.execute_workflow(wf_panel.current_workflow)
    wf_panel._on_run_finished(rec)
    app.processEvents()

    # Capture screenshots
    out_dir = root_dir / ".mendex" / "qa" / "v19-workflow"
    out_dir.mkdir(parents=True, exist_ok=True)

    screenshot_dark = out_dir / "workflow-studio-dark.png"
    window.grab().save(str(screenshot_dark))

    # Toggle to light theme and capture
    window.toggle_theme()
    app.processEvents()
    screenshot_light = out_dir / "workflow-studio-light.png"
    window.grab().save(str(screenshot_light))

    window.close()
    print(f"Mendex Studio v1.9 Workflow Studio smoke passed; screens captured under {out_dir}")


if __name__ == "__main__":
    run_smoke()
