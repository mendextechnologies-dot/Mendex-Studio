"""Desktop views consume core services; engineering policy stays in the core."""
import json

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit,
    QVBoxLayout, QWidget, QTabWidget, QGroupBox, QCheckBox, QMessageBox,
)

from mendex_core.evidence import ManualCheck
from mendex_core.knowledge import GUIDELINES, GUIDELINES_REVISION


class SimulationPanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded, self.revision = service, guarded, None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Interactive Multi-Solver Simulation Lab & Live Waveform Viewer
        try:
            from .v17_panels import SimulationLabPanel
            self.lab_panel = SimulationLabPanel(service)
            self.tabs.addTab(self.lab_panel, "Simulation Lab & Waveforms")
        except Exception:
            self.lab_panel = None

        # Tab 2: Product Revision Simulation Baseline
        legacy_widget = QWidget()
        legacy_layout = QVBoxLayout(legacy_widget)
        self.context = QLabel("Select a product revision in Products")
        legacy_layout.addWidget(self.context)
        self.tools = QComboBox()
        self.tools.addItems([adapter.tool_id for adapter in service.registry.list()])
        legacy_layout.addWidget(self.tools)
        button = QPushButton("Record simulation availability request")
        button.clicked.connect(lambda: guarded(self.request))
        legacy_layout.addWidget(button)
        legacy_layout.addWidget(QLabel("Product Baseline Mode: Historical product request archive."))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        legacy_layout.addWidget(self.output)
        self.tabs.addTab(legacy_widget, "Product Simulation Archive")

    def set_revision(self, revision):
        self.revision = revision
        self.context.setText(f"Simulation requests · {revision.revision_label} · execution unavailable")
        self.refresh()

    def refresh(self):
        runs = self.service.list_runs(self.revision.revision_id) if self.revision else []
        self.output.setPlainText(json.dumps([run.model_dump(mode="json") for run in runs], indent=2) if runs else "NOT_RUN · No simulation requests or solver outputs")

    def request(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        self.service.request_simulation(self.revision.revision_id, self.tools.currentText())
        self.refresh()


class KnowledgePanel(QTabWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded, self.revision = service, guarded, None
        try:
            from .v17_panels import AIAssistantPanel
            self.ai_assistant = AIAssistantPanel(service)
            self.addTab(self.ai_assistant, "Engineering AI Assistant")
        except Exception:
            self.ai_assistant = None

        # Dedicated AI & API Key Settings Tab
        try:
            from .ai_config_dialog import AIKeySetupWidget
            self.ai_config_widget = AIKeySetupWidget(service.root, self)
            self.addTab(self.ai_config_widget, "AI & API Key Settings")
        except Exception:
            self.ai_config_widget = None

        guidelines = QTextEdit()
        guidelines.setReadOnly(True)
        guidelines.setPlainText(f"Engineering guidelines · revision {GUIDELINES_REVISION}\n\n" + "\n\n".join(f"{title}\n{body}" for title, body in GUIDELINES))
        self.addTab(guidelines, "Guidelines")
        self.rules = QTextEdit()
        self.rules.setReadOnly(True)
        self.addTab(self.rules, "Engineering rules")
        self.plugins = QTextEdit()
        self.plugins.setReadOnly(True)
        self.plugins.setPlainText("Data-only plugin manifests load from .mendex/plugins/*.json on startup. No plugin Python or model scripts are executed.\n\n" + json.dumps(service.list_plugins(), indent=2))
        self.addTab(self.plugins, "Plugins")
        ai_page = QWidget()
        layout = QVBoxLayout(ai_page)

        # AI Provider & API Key Setup Group
        cfg_group = QGroupBox("AI Copilot & Cloud Provider Configuration")
        cfg_form = QFormLayout(cfg_group)

        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems([
            "Offline Deterministic Engine (Default / Zero Cost)",
            "Google Gemini API (Cloud)",
            "OpenAI API (Cloud)",
        ])
        cfg_form.addRow("Provider:", self.ai_provider_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter API Key (e.g. AIzaSy... or sk-...)")

        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key_input)
        self.btn_toggle_key = QPushButton("👁️ Show")
        self.btn_toggle_key.setFixedWidth(70)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.btn_toggle_key)
        cfg_form.addRow("API Key:", key_row)

        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("e.g. gemini-2.0-flash or gpt-4o")
        cfg_form.addRow("Model Name:", self.ai_model_input)

        self.chk_cloud_opt_in = QCheckBox("Explicit Cloud Opt-In (allow technical requirements to be processed by cloud provider)")
        cfg_form.addRow("", self.chk_cloud_opt_in)

        self.btn_save_ai = QPushButton("💾 Save API Key & Provider Settings")
        self.btn_save_ai.setStyleSheet("font-weight: 700; color: #89b4fa; padding: 6px;")
        self.btn_save_ai.clicked.connect(self._save_ai_settings)
        cfg_form.addRow("", self.btn_save_ai)

        self.lbl_ai_status = QLabel("Status: Local Offline Engine")
        self.lbl_ai_status.setStyleSheet("color: #a6e3a1; font-weight: 600;")
        cfg_form.addRow("Active Backend:", self.lbl_ai_status)
        layout.addWidget(cfg_group)

        # AI Interface Query Section
        query_group = QGroupBox("Engineering Query & Diagnostics")
        q_layout = QVBoxLayout(query_group)
        q_layout.addWidget(QLabel("Query active engineering intelligence rules and configured provider:"))
        self.question = QLineEdit()
        self.question.setPlaceholderText("Ask a question about circuit topology, loss calculations, or component rules...")
        q_layout.addWidget(self.question)
        button = QPushButton("Ask Engineering Intelligence")
        button.clicked.connect(lambda: guarded(self.ask))
        q_layout.addWidget(button)
        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        q_layout.addWidget(self.ai_output)
        layout.addWidget(query_group, 1)

        self.addTab(ai_page, "AI interface")
        self.rules.setPlainText(json.dumps([rule.model_dump(mode="json") for rule in service.list_rules()], indent=2))
        self._load_ai_settings()

    def _toggle_key_visibility(self):
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setText("🔒 Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setText("👁️ Show")

    def _load_ai_settings(self):
        try:
            from mendex_core.ai.config import load_ai_config
            cfg = load_ai_config(self.service.root)
            if cfg.provider == "gemini":
                self.ai_provider_combo.setCurrentIndex(1)
            elif cfg.provider == "openai":
                self.ai_provider_combo.setCurrentIndex(2)
            else:
                self.ai_provider_combo.setCurrentIndex(0)

            self.api_key_input.setText(cfg.api_key)
            self.ai_model_input.setText(cfg.model)
            self.chk_cloud_opt_in.setChecked(cfg.cloud_opt_in)

            if cfg.api_key and cfg.provider in ("gemini", "openai"):
                masked = cfg.api_key[:6] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 10 else "***"
                self.lbl_ai_status.setText(f"● Connected to {cfg.provider.upper()} ({cfg.model}) [{masked}]")
            else:
                self.lbl_ai_status.setText("● Local Offline Engine (Deterministic, Zero Cost)")
        except Exception:
            self.lbl_ai_status.setText("● Local Offline Engine (Default)")

    def _save_ai_settings(self):
        try:
            from mendex_core.ai.config import save_ai_config, AIProviderConfig
            prov_idx = self.ai_provider_combo.currentIndex()
            prov = "gemini" if prov_idx == 1 else "openai" if prov_idx == 2 else "offline"
            cfg = AIProviderConfig(
                provider=prov,
                model=self.ai_model_input.text().strip() or ("gemini-2.0-flash" if prov == "gemini" else "gpt-4o" if prov == "openai" else "local_engineering_rules"),
                api_key=self.api_key_input.text().strip(),
                cloud_opt_in=self.chk_cloud_opt_in.isChecked(),
            )
            save_ai_config(cfg, self.service.root)
            self._load_ai_settings()
            QMessageBox.information(self, "AI Settings Saved", f"AI Provider '{prov.upper()}' configuration saved to .mendex/ai_config.json.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save AI settings:\n\n{exc}")

    def set_revision(self, revision):
        self.revision = revision
        self.rules.setPlainText(json.dumps([rule.model_dump(mode="json") for rule in self.service.list_rules(revision.revision_id)], indent=2))

    def ask(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        self.ai_output.setPlainText(self.service.ai_advice(self.revision.revision_id, self.question.text()).model_dump_json(indent=2))


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
        diagnostics = QHBoxLayout()
        for title, callback in [("Run workstation doctor", self.doctor), ("Export diagnostics", self.export_diagnostics)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: guarded(callback))
            diagnostics.addWidget(button)
        layout.addLayout(diagnostics)
        self.tools.currentIndexChanged.connect(self.selected)
        self.selected()

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select native tool executable", "", "Executables (*.exe);;All files (*)")
        if path:
            self.path.setText(path)

    def doctor(self):
        diagnostic = self.service.diagnostics()
        self.output.setPlainText(f"Workstation: {diagnostic['status']}\nFramework ready: {diagnostic['framework_ready']}\n\n" + json.dumps(diagnostic, indent=2))

    def export_diagnostics(self):
        destination = self.service.export_diagnostics()
        self.output.setPlainText(f"Diagnostics exported locally:\n{destination}\n\nIncludes OS, dependency versions and executable paths; review before sharing.")

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
        self.evidence = QComboBox()
        layout.addWidget(self.evidence)
        open_button = QPushButton("Open selected evidence")
        open_button.clicked.connect(lambda: guarded(self.open_evidence))
        layout.addWidget(open_button)
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
            self.evidence.clear()
            for entry in entries:
                record = entry["record"]
                if record.evidence_uri:
                    self.evidence.addItem(f"{record.check.check_id} · {record.evidence_filename or 'evidence'}", str(record.record_id))
            overview = "\n".join(f"{entry['record'].check.check_id}: {entry['effective_status'].upper()} · {entry['record'].check.evidence_kind}\nReviewer: {entry['record'].check.reviewer} · stale: {entry['stale']} · evidence: {'not supplied' if entry['record'].evidence_uri is None else ('intact' if entry['evidence_integrity'] else 'missing or altered')}\n{entry['record'].check.notes}\n" for entry in entries)
            self.output.setPlainText(overview + "\nRecord details\n\n" + json.dumps([{**entry, "record": entry["record"].model_dump(mode="json")} for entry in entries], indent=2) if entries else "NOT_EVALUATED · No validation entries recorded")

    def record(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        dialog = ValidationDialog(self)
        if dialog.exec() == QDialog.Accepted:
            check = ManualCheck.model_validate_json(dialog.editor.toPlainText())
            self.service.record_validation(self.revision.revision_id, check, dialog.path.text() or None)
            self.refresh()

    def open_evidence(self):
        identifier = self.evidence.currentData()
        if not identifier:
            raise ValueError("No attached evidence selected")
        self.service.open_evidence(identifier)


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
        self.service.open_report(self.reports[index].report_id)
