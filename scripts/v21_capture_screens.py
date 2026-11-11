"""Captures screenshots of the 7 simplified navigation views of Mendex Studio v2.1."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow

def main():
    app = QApplication.instance() or QApplication([])
    root = Path.cwd()
    service = StudioService(root)
    window = StudioWindow(service)
    window.resize(1380, 880)
    window.show()
    app.processEvents()

    artifact_dir = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\0a1dae9f-d647-4c88-987e-ccfaaa950d01")

    pages = [
        ("screen_v21_dashboard.png", 0),
        ("screen_v21_workspaces.png", 1),
        ("screen_v21_simulation.png", 2),
        ("screen_v21_components.png", 3),
        ("screen_v21_tools.png", 4),
        ("screen_v21_reports.png", 5),
        ("screen_v21_settings.png", 6),
    ]

    for fname, idx in pages:
        window.navigation.setCurrentRow(idx)
        app.processEvents()
        target = artifact_dir / fname
        window.grab().save(str(target))
        print(f"Saved: {target.name}")

    window.close()

if __name__ == "__main__":
    main()
