"""Codex-owned integration UI; uses application services, never starts tools directly."""
import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from mendex_core.integration_contracts import JobRequest, TERMINAL, ToolConfiguration


class ToolCenter(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.engine, self.guarded = service.integrations, guarded
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tools & Integrations · 18 approved inventory entries · installed ≠ verified"))
        split = QSplitter()
        self.list = QListWidget()
        self.list.setWordWrap(True)
        for descriptor in self.engine.list_tools():
            self.list.addItem(f"{descriptor.name} · {descriptor.category}" + (" · optional licensed" if descriptor.optional_paid else ""))
        split.addWidget(self.list)
        detail = QWidget()
        form = QVBoxLayout(detail)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        form.addWidget(self.summary)
        fields = QFormLayout()
        self.executable, self.resource, self.license = QLineEdit(), QLineEdit(), QLineEdit()
        self.license.setPlaceholderText("Review reference only; do not paste license keys or secrets")
        fields.addRow("Executable path", self.executable)
        fields.addRow("Resource path", self.resource)
        fields.addRow("License review", self.license)
        form.addLayout(fields)
        buttons = QHBoxLayout()
        for title, callback in [("Browse executable", self.browse_executable), ("Browse resource", self.browse_resource), ("Save settings", self.save), ("Detect", self.detect), ("Verify operation", self.verify)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            buttons.addWidget(button)
        form.addLayout(buttons)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        form.addWidget(self.output, 1)
        split.addWidget(detail)
        split.setStretchFactor(1, 3)
        layout.addWidget(split, 1)
        self.list.currentRowChanged.connect(lambda: guarded(self.selected))
        self.list.setCurrentRow(0)

    def descriptor(self):
        return self.engine.list_tools()[self.list.currentRow()]

    def selected(self):
        descriptor = self.descriptor()
        configuration = self.engine.configuration(descriptor.tool_id)
        self.executable.setText(configuration.executable_path or "")
        self.resource.setText(configuration.resource_path or "")
        self.license.setText(configuration.license_reference)
        self.summary.setText(f"{descriptor.name} · {descriptor.category}\nLicense: {descriptor.license_status} · {descriptor.license_notes}\nSource: {descriptor.source_url or 'Unresolved'}\n{descriptor.source_notes}")
        self.detect()

    def browse_executable(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select existing executable", "", "Executables (*.exe)")
        if path:
            self.executable.setText(path)

    def browse_resource(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select local resource file")
        if path:
            self.resource.setText(path)

    def show_health(self, health):
        self.output.setPlainText(f"{health.state.value}\n{health.diagnostic}\n\n" + health.model_dump_json(indent=2))

    def save(self):
        health = self.engine.configure(self.descriptor().tool_id, ToolConfiguration(executable_path=self.executable.text() or None, resource_path=self.resource.text() or None, license_reference=self.license.text()))
        self.show_health(health)

    def detect(self):
        self.show_health(self.engine.detect(self.descriptor().tool_id))

    def verify(self):
        self.show_health(self.engine.verify(self.descriptor().tool_id))


class JobsPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.engine, self.guarded = service.integrations, guarded
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Generic software workspaces · no engineering product or simulation model is created"))
        self.workspaces = QComboBox()
        workspace_actions = QHBoxLayout()
        workspace_actions.addWidget(self.workspaces, 1)
        for title, callback in [("New generic workspace", self.create_workspace), ("Attach input", self.attach_input)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            workspace_actions.addWidget(button)
        layout.addLayout(workspace_actions)
        self.input_paths = QLineEdit()
        self.input_paths.setPlaceholderText("Workspace-relative input paths, separated by semicolons (optional)")
        layout.addWidget(self.input_paths)
        parameters = QHBoxLayout()
        self.parameters = QLineEdit('{"steps": 20, "delay_s": 0.1, "echo": "synthetic software fixture"}')
        parameters.addWidget(self.parameters, 1)
        parameters.addWidget(QLabel("Timeout (s)"))
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(.05, 3600)
        self.timeout.setValue(30)
        parameters.addWidget(self.timeout)
        layout.addLayout(parameters)
        buttons = QHBoxLayout()
        for title, callback in [("Start synthetic demo", self.start), ("Cancel selected", self.cancel), ("Retry selected", self.retry), ("Refresh", self.refresh), ("Export evidence report", self.report)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Only the synthetic contract fixture is runnable. Native operation support awaits Agent 2 smoke evidence."))
        artifact_actions = QHBoxLayout()
        self.artifacts = QComboBox()
        self.artifacts.setPlaceholderText("Terminal job artifacts / staged inputs")
        artifact_actions.addWidget(self.artifacts, 1)
        preview = QPushButton("Preview verified artifact")
        preview.clicked.connect(lambda: guarded(self.preview))
        artifact_actions.addWidget(preview)
        self.open_report_button = QPushButton("Open exported report")
        self.open_report_button.setEnabled(False)
        self.open_report_button.clicked.connect(lambda: guarded(self.open_report))
        artifact_actions.addWidget(self.open_report_button)
        self.last_report = None
        layout.addLayout(artifact_actions)
        split = QSplitter()
        self.jobs = QListWidget()
        split.addWidget(self.jobs)
        self.details = QTabWidget()
        self.status, self.logs, self.evidence, self.artifact_preview = QTextEdit(), QTextEdit(), QTextEdit(), QTextEdit()
        for widget, title in [(self.status, "Status / progress"), (self.logs, "Logs (tail)"), (self.evidence, "Evidence / provenance"), (self.artifact_preview, "Artifact preview")]:
            widget.setReadOnly(True)
            self.details.addTab(widget, title)
        split.addWidget(self.details)
        split.setStretchFactor(1, 3)
        layout.addWidget(split, 1)
        self.report_path = QLabel("Reports remain DRAFT; successful software execution never means an engineering pass.")
        self.report_path.setWordWrap(True)
        layout.addWidget(self.report_path)
        self.jobs.currentRowChanged.connect(lambda: guarded(self.selected))
        self.workspaces.currentIndexChanged.connect(lambda: guarded(self.refresh))
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(lambda: guarded(self.refresh))
        self.refresh_workspaces()
        self.refresh()
        self.timer.start()

    def refresh_workspaces(self):
        current = self.workspaces.currentData()
        self.workspaces.blockSignals(True)
        self.workspaces.clear()
        for workspace in self.engine.list_workspaces():
            self.workspaces.addItem(workspace["name"], workspace["workspace_id"])
        index = self.workspaces.findData(current)
        self.workspaces.setCurrentIndex(index if index >= 0 else (0 if self.workspaces.count() else -1))
        self.workspaces.blockSignals(False)

    def create_workspace(self):
        workspace = self.engine.create_workspace()
        self.refresh_workspaces()
        self.workspaces.setCurrentIndex(self.workspaces.findData(workspace["workspace_id"]))
        self.refresh()

    def attach_input(self):
        workspace = self.workspaces.currentData()
        if not workspace:
            raise ValueError("Create a generic workspace first")
        path, _ = QFileDialog.getOpenFileName(self, "Attach a generic local input (max 10 MiB)")
        if path:
            relative = self.engine.attach_input(workspace, path)
            self.input_paths.setText(";".join(filter(None, [self.input_paths.text(), relative])))

    def start(self):
        workspace = self.workspaces.currentData()
        if not workspace:
            raise ValueError("Create a generic workspace first")
        request = JobRequest(workspace_id=workspace, tool_id="studio-demo", operation="synthetic-echo", input_paths=[path.strip() for path in self.input_paths.text().split(";") if path.strip()], parameters=json.loads(self.parameters.text()), timeout_s=self.timeout.value(), provenance="User-requested SYNTHETIC SOFTWARE FIXTURE; no engineering validity asserted")
        job = self.engine.submit(request)
        self.refresh()
        self.jobs.setCurrentRow(next((i for i, row in enumerate(self.rows) if row.request.job_id == job.request.job_id), 0))

    def selected_job(self):
        index = self.jobs.currentRow()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def refresh(self):
        previous = self.selected_job() if hasattr(self, "rows") else None
        self.rows = self.engine.list_jobs(self.workspaces.currentData()) if self.workspaces.currentData() else []
        self.jobs.blockSignals(True)
        self.jobs.clear()
        for job in self.rows:
            self.jobs.addItem(f"{job.status.value} · {int(job.progress * 100)}%\n{str(job.request.job_id)[:8]} · {job.request.tool_id}")
        self.jobs.setCurrentRow(next((i for i, row in enumerate(self.rows) if previous and row.request.job_id == previous.request.job_id), 0) if self.rows else -1)
        self.jobs.blockSignals(False)
        self.selected()

    def selected(self):
        job = self.selected_job()
        previous_artifact = self.artifacts.currentData()
        self.artifacts.clear()
        if not job:
            self.status.setPlainText("No jobs. Create a generic workspace, then start a synthetic fixture.")
            self.logs.clear()
            self.evidence.clear()
            self.artifact_preview.clear()
            return
        if getattr(self, "preview_job", None) != job.request.job_id:
            self.artifact_preview.clear()
            self.preview_job = job.request.job_id
        self.status.setPlainText(job.model_dump_json(indent=2))
        self.logs.setPlainText(self.engine.logs(job.request.job_id))
        try:
            manifest = self.engine.evidence(job.request.job_id)
        except Exception as exc:
            self.evidence.setPlainText(f"Evidence unavailable or invalid: {exc}\nEngineering: NOT_EVALUATED")
            return
        self.evidence.setPlainText((f"Evidence intact: {self.engine.evidence_integrity(job.request.job_id)}\nEngineering: NOT_EVALUATED\n\n" + manifest.model_dump_json(indent=2)) if manifest else "No terminal evidence manifest yet")
        if manifest:
            for relative in list(dict.fromkeys([artifact.relative_path for artifact in manifest.artifacts] + list(manifest.input_hashes))):
                self.artifacts.addItem(relative, relative)
            index = self.artifacts.findData(previous_artifact)
            self.artifacts.setCurrentIndex(index if index >= 0 else 0)

    def cancel(self):
        job = self.selected_job()
        if not job:
            raise ValueError("Select a job first")
        self.engine.cancel(job.request.job_id)
        self.refresh()

    def retry(self):
        job = self.selected_job()
        if not job:
            raise ValueError("Select a terminal job first")
        self.engine.retry(job.request.job_id)
        self.refresh()

    def report(self):
        job = self.selected_job()
        if not job:
            raise ValueError("Select a terminal job first")
        path = self.engine.export_report(job.request.job_id)
        self.last_report = (job.request.job_id, path)
        self.open_report_button.setEnabled(True)
        self.report_path.setText(f"Draft HTML + JSON report exported locally:\n{path}")

    def open_report(self):
        if not self.last_report:
            raise ValueError("Export a job report first")
        self.engine.open_framework_report(*self.last_report)

    def preview(self):
        job, relative = self.selected_job(), self.artifacts.currentData()
        if not job or not relative:
            raise ValueError("Select a terminal job and declared artifact")
        self.artifact_preview.setPlainText(self.engine.preview_artifact(job.request.job_id, relative))
        self.details.setCurrentIndex(3)


class DatasetPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.engine, self.guarded = service.integrations, guarded
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Research catalog · local provenance registration only · no silent downloads or format interpretation"))
        form = QFormLayout()
        self.resource = QComboBox()
        for descriptor in self.engine.list_tools():
            if descriptor.category in ("dataset", "benchmark", "research_resource"):
                self.resource.addItem(f"{descriptor.name} · {descriptor.category}", descriptor.tool_id)
        form.addRow("Resource", self.resource)
        self.source, self.version, self.license, self.provenance, self.path = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.version.setPlaceholderText("Exact upstream release/version; use synthetic-1 for software fixtures")
        self.license.setPlaceholderText("License review reference; not license keys")
        for title, field in [("HTTPS source", self.source), ("Release/version", self.version), ("License reference", self.license), ("Provenance", self.provenance), ("Optional file", self.path)]:
            form.addRow(title, field)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        for title, callback in [("Choose local file", self.browse), ("Register metadata / opaque file", self.register), ("Refresh history", self.refresh)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        layout.addWidget(self.notes)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
        self.resource.currentIndexChanged.connect(self.selected)
        self.selected()
        self.refresh()

    def selected(self):
        descriptor = self.engine.descriptor(self.resource.currentData())
        self.source.setText(descriptor.source_url or "")
        self.notes.setText(descriptor.license_notes + "\n" + descriptor.source_notes + "\nAll records remain NOT_REVIEWED. Actual dataset parsing and license qualification belong to Agent 2.")

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Optional local resource (max 20 MiB)")
        if path:
            self.path.setText(path)

    def register(self):
        self.engine.register_dataset(self.resource.currentData(), self.source.text(), self.version.text(), self.license.text(), self.provenance.text(), self.path.text() or None)
        self.refresh()

    def refresh(self):
        self.output.setPlainText(json.dumps(self.engine.list_datasets(), indent=2) if self.engine.list_datasets() else "No local research-resource metadata registered")
