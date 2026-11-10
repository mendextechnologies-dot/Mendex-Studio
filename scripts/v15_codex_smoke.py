"""Render the Codex-owned v1.5 UI with a generic synthetic job, no product."""
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
destination = Path(".mendex/qa/v15-codex")
destination.mkdir(parents=True, exist_ok=True)
with TemporaryDirectory(prefix="mendex-v15-") as temporary:
    service = StudioService(Path(temporary))
    window = StudioWindow(service)
    window.resize(1380, 900)
    window.show()
    window.jobs_panel.create_workspace()
    window.jobs_panel.parameters.setText('{"steps":1,"delay_s":0,"echo":"SYNTHETIC SOFTWARE FIXTURE"}')
    window.jobs_panel.start()
    job = window.jobs_panel.selected_job()
    service.integrations.wait(job.request.job_id)
    window.jobs_panel.refresh()
    window.jobs_panel.report()
    for index, label in [(11, "tool-center"), (12, "jobs"), (13, "datasets")]:
        window.navigation.setCurrentRow(index)
        app.processEvents()
        if not window.grab().save(str(destination / f"{label}.png")):
            raise RuntimeError("Screenshot write failed")
    window.navigation.setCurrentRow(12)
    for index, label in [(1, "logs"), (2, "evidence")]:
        window.jobs_panel.details.setCurrentIndex(index)
        app.processEvents()
        window.grab().save(str(destination / f"{label}.png"))
    window.close()
print("Codex v1.5 synthetic UI smoke passed; screenshots under .mendex/qa/v15-codex")
