"""Comprehensive visual smoke test and screenshot capture for Mendex Studio v1.9 Revised."""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def run_visual_smoke():
    app = QApplication.instance() or QApplication([])

    test_root = root_dir / ".mendex" / "qa" / "v19_revised_temp"
    test_root.mkdir(parents=True, exist_ok=True)
    service = StudioService(test_root)

    window = StudioWindow(service)
    window.resize(1440, 900)
    window.show()
    app.processEvents()

    out_dir = root_dir / ".mendex" / "qa" / "v19-revised-ui"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dashboard (Page 0)
    window.navigation.setCurrentRow(0)
    app.processEvents()
    screen_dash = out_dir / "01_enterprise_dashboard.png"
    window.grab().save(str(screen_dash))

    # 2. Product Engineering Overview (Page 1)
    window.navigation.setCurrentRow(1)
    app.processEvents()
    screen_prod = out_dir / "02_product_lifecycle.png"
    window.grab().save(str(screen_prod))

    # 3. PCB Workspace (Page 5)
    window.navigation.setCurrentRow(5)
    app.processEvents()
    screen_pcb = out_dir / "03_pcb_workspace.png"
    window.grab().save(str(screen_pcb))

    # 4. Visual Workflow Studio (Page 14)
    window.navigation.setCurrentRow(14)
    app.processEvents()
    wf_panel = window.workflow_studio
    wf_panel.load_template(1)
    app.processEvents()
    screen_wf = out_dir / "04_visual_workflow_studio.png"
    window.grab().save(str(screen_wf))

    # 5. Command Palette
    window.command_palette.show_palette()
    app.processEvents()
    screen_cp = out_dir / "05_command_palette.png"
    window.command_palette.grab().save(str(screen_cp))
    window.command_palette.close()
    app.processEvents()

    # 6. Notification Center
    window.notification_center.add_notification("System", "Mendex Studio v1.9 Platform Initialization Complete", "SUCCESS")
    window.notification_center.show()
    app.processEvents()
    screen_notif = out_dir / "06_notification_center.png"
    window.notification_center.grab().save(str(screen_notif))
    window.notification_center.close()
    app.processEvents()

    window.close()
    print(f"All 6 screens captured successfully in {out_dir}")

    # Copy to brain artifact directory for display
    artifact_dir = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\0a1dae9f-d647-4c88-987e-ccfaaa950d01")
    if artifact_dir.exists():
        for src_img in out_dir.glob("*.png"):
            dest_img = artifact_dir / src_img.name
            shutil.copy2(src_img, dest_img)
            print(f"Copied to artifact: {dest_img}")


if __name__ == "__main__":
    run_visual_smoke()
