"""Desktop views consume core services; engineering policy stays in the core."""
import json

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from mendex_core.evidence import ManualCheck


class ToolPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded = service, guarded
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tool Manager · discovery only · compatibility and benchmarks unverified"))
        self.tools = QComboBox()
        for adapter in service.registry.list():
            self.tools.addItem(adapter.tool_id)
        layout.addWidget(self.tools)
        self.path = QLineEdit()
        self.path.setPlaceholderText("Optional absolute executable path")
        layout.addWidget(self.path)
        actions = QHBoxLayout()
        for title, callback in [("Browse executable", self.browse), ("Save path", self.configure), ("Use auto-discovery", self.reset), ("Refresh detection", self.refresh)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            actions.addWidget(button)
        layout.addLayout(actions)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.tools.currentIndexChanged.connect(self.selected)
        self.selected()

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select native tool executable", "", "Executables (*.exe);;All files (*)")
        if path:
            self.path.setText(path)

    def selected(self):
        self.path.setText(self.service.check_tool(self.tools.currentText()).configured_path or "")
        self.refresh()

    def configure(self):
        if not self.path.text().strip():
            raise ValueError("Select a path or use auto-discovery")
        self.service.configure_tool(self.tools.currentText(), self.path.text())
        self.refresh()

    def reset(self):
        self.service.configure_tool(self.tools.currentText())
        self.selected()

    def refresh(self):
        tools = self.service.list_tools()
        overview = "\n".join(f"{tool.display_name}: {tool.state} · version {tool.installed_version or 'unknown'}\n{tool.executable or 'Configure a path if installed elsewhere'}\n" for tool in tools)
        self.output.setPlainText(overview + "\nDiscovery details\n\n" + json.dumps([t.model_dump(mode="json") for t in tools], indent=2))


class ValidationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record manual validation · supplied evidence")
        self.resize(700, 520)
        form = QFormLayout(self)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlainText(ManualCheck(check_id="REQ-001", reviewer="Engineer", notes="Not evaluated: evidence unavailable").model_dump_json(indent=2))
        form.addRow("Check JSON (SI units)", self.editor)
        self.path = QLineEdit()
        form.addRow("Evidence file (optional for unevaluated)", self.path)
        browse = QPushButton("Attach evidence file")
        browse.clicked.connect(self.browse)
        form.addRow(browse)
        form.addRow(QLabel("PASS/FAIL requires evidence, value, unit and minimum/maximum.\nThis records a manual assessment; it does not approve the product."))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose evidence file")
        if path:
            self.path.setText(path)


class ValidationPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded, self.revision = service, guarded, None
        layout = QVBoxLayout(self)
        self.context = QLabel("Select a product and revision in Products")
        layout.addWidget(self.context)
        actions = QHBoxLayout()
        for title, callback in [("Record manual validation", self.record), ("Refresh records", self.refresh)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            actions.addWidget(button)
        layout.addLayout(actions)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

    def set_revision(self, revision):
        self.revision = revision
        self.context.setText(f"Revision {revision.revision_label} · {revision.revision_id}\nAppend-only manual entries; no product approval")
        self.refresh()

    def refresh(self):
        if self.revision:
            entries = self.service.validation_summary(self.revision.revision_id)
            overview = "\n".join(f"{entry['record'].check.check_id}: {entry['effective_status'].upper()} · {entry['record'].check.evidence_kind}\nReviewer: {entry['record'].check.reviewer} · stale: {entry['stale']} · evidence intact: {entry['evidence_integrity']}\n{entry['record'].check.notes}\n" for entry in entries)
            self.output.setPlainText(overview + "\nRecord details\n\n" + json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in entries], indent=2) if entries else "NOT_EVALUATED · No validation entries recorded")

    def record(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        dialog = ValidationDialog(self)
        if dialog.exec() == QDialog.Accepted:
            check = ManualCheck.model_validate_json(dialog.editor.toPlainText())
            self.service.record_validation(self.revision.revision_id, check, dialog.path.text() or None)
            self.refresh()


class ReportsPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded, self.revision = service, guarded, None
        layout = QVBoxLayout(self)
        self.context = QLabel("Select a product revision in Products · HTML + JSON draft export")
        layout.addWidget(self.context)
        actions = QHBoxLayout()
        for title, callback in [("Generate draft dossier", self.generate), ("Open selected report", self.open_report)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            actions.addWidget(button)
        layout.addLayout(actions)
        self.list = QListWidget()
        layout.addWidget(self.list)
        layout.addWidget(QLabel("Draft only. Word/PDF export and approval workflows are not implemented."))

    def set_revision(self, revision):
        self.revision = revision
        self.context.setText(f"Draft dossiers · {revision.revision_label} · {revision.revision_id}")
        self.refresh()

    def refresh(self):
        self.reports = self.service.list_reports(self.revision.revision_id) if self.revision else []
        self.list.clear()
        for report in self.reports:
            self.list.addItem(f"DRAFT · {report.generated_at.isoformat()}\nReport {str(report.report_id)[:8]} · HTML dossier + JSON snapshot · {len(report.warnings)} notices")
            self.list.item(self.list.count() - 1).setToolTip(report.report_path)

    def generate(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        self.service.generate_report(self.revision.revision_id)
        self.refresh()

    def open_report(self):
        index = self.list.currentRow()
        if index < 0:
            raise ValueError("Select a report first")
        path = (self.service.root / self.reports[index].report_path).resolve()
        if not path.is_relative_to(self.service.root) or not path.is_file():
            raise ValueError("Report is unavailable or outside the data root")
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            raise ValueError("Could not open report with the default application")
