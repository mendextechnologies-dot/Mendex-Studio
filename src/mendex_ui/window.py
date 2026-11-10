import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QFileDialog,
)

from mendex_core.models import Category, Specification
from mendex_core.knowledge import GUIDELINES, GUIDELINES_REVISION
from .panels import ToolPanel, ValidationPanel, ReportsPanel, SimulationPanel, KnowledgePanel
from .integration_panels import ToolCenter, JobsPanel, DatasetPanel
from .workspace_panels import (
    TransformerWorkspacePanel,
    DCDCWorkspacePanel,
    SemiconductorWorkspacePanel,
)


class ProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create engineering product")
        form = QFormLayout(self)
        self.code = QLineEdit()
        self.name = QLineEdit()
        self.owner = QLineEdit()
        self.category = QComboBox()
        self.category.addItems([c.value for c in Category])
        for label, field in [("Product code", self.code), ("Name", self.name), ("Owner", self.owner), ("Category", self.category)]:
            form.addRow(label, field)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class StudioWindow(QMainWindow):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.product = None
        self.revision = None
        self.setWindowTitle("Mendex Engineering Studio · v0.1 foundation")
        self.resize(1180, 790)
        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        nav = QListWidget()
        self.navigation = nav
        nav.setFixedWidth(215)
        nav.addItems(["Dashboard", "Products", "Transformer", "DC–DC Converter", "Switching Devices", "PCB Workspace", "Simulations", "Validation", "Reports", "Tool Manager", "Knowledge Center"])
        self.pages = QStackedWidget()
        layout.addWidget(nav)
        layout.addWidget(self.pages, 1)
        self.dashboard = QLabel()
        self.dashboard.setMargin(30)
        self.dashboard.setAlignment(Qt.AlignTop)
        self.pages.addWidget(self.dashboard)
        products = QWidget()
        pane = QVBoxLayout(products)
        actions = QHBoxLayout()
        create = QPushButton("New product")
        create.clicked.connect(self.create_product)
        actions.addWidget(create)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        actions.addStretch()
        pane.addLayout(actions)
        split = QSplitter()
        self.products = QListWidget()
        self.products.currentRowChanged.connect(self.select_product)
        split.addWidget(self.products)
        editor = QWidget()
        form = QVBoxLayout(editor)
        self.detail = QLabel("Select or create a product")
        self.detail.setWordWrap(True)
        form.addWidget(self.detail)
        self.name = QLineEdit()
        self.owner = QLineEdit()
        self.description = QLineEdit()
        fields = QFormLayout()
        fields.addRow("Name", self.name)
        fields.addRow("Owner", self.owner)
        fields.addRow("Description", self.description)
        self.revisions = QComboBox()
        self.revisions.currentIndexChanged.connect(self.select_revision)
        fields.addRow("Revision", self.revisions)
        form.addLayout(fields)
        form.addWidget(QLabel("Specification JSON · SI units · null means unspecified"))
        self.specification = QTextEdit()
        self.specification.setAcceptRichText(False)
        form.addWidget(self.specification)
        save = QPushButton("Save draft specification")
        save.clicked.connect(self.save)
        form.addWidget(save)
        revision = QPushButton("Create revision from active baseline")
        revision.clicked.connect(self.new_revision)
        form.addWidget(revision)
        revision_actions = QHBoxLayout()
        for title, callback in [("Rename draft", self.rename_revision), ("Toggle draft / review", self.toggle_review), ("Export specification", self.export_specification)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: self.guarded(callback))
            revision_actions.addWidget(button)
        form.addLayout(revision_actions)
        handoff = QHBoxLayout()
        for title, callback in [("Open in VS Code", self.open_vscode), ("Open workspace", self.open_workspace), ("Open project file", self.open_file)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: self.guarded(callback))
            handoff.addWidget(button)
        form.addLayout(handoff)
        split.addWidget(editor)
        split.setStretchFactor(1, 3)
        pane.addWidget(split)
        self.pages.addWidget(products)
        self.module_pages = []
        labels = {}
        for title in ("Transformer", "DC–DC Converter", "Switching Devices", "PCB Workspace"):
            label = QLabel(f"{title}\n\nImplementation: NOT IMPLEMENTED\nProduct evaluation: NOT_EVALUATED\n\nFoundation workspace only. No calculation, tool execution or result is available.")
            label.setMargin(15)
            label.setAlignment(Qt.AlignTop)
            self.module_pages.append(label)
            labels[title] = label

        self.transformer_ws = TransformerWorkspacePanel(service, self.guarded, labels["Transformer"])
        self.dcdc_ws = DCDCWorkspacePanel(service, self.guarded, labels["DC–DC Converter"])
        self.semiconductor_ws = SemiconductorWorkspacePanel(service, self.guarded, labels["Switching Devices"])
        self.pcb_ws = labels["PCB Workspace"]

        for ws in (self.transformer_ws, self.dcdc_ws, self.semiconductor_ws, self.pcb_ws):
            self.pages.addWidget(ws)
        self.simulation_panel = SimulationPanel(service, self.guarded)
        self.pages.addWidget(self.simulation_panel)
        self.validation_panel = ValidationPanel(service, self.guarded)
        self.reports_panel = ReportsPanel(service, self.guarded)
        self.tool_panel = ToolPanel(service, self.guarded)
        for panel in (self.validation_panel, self.reports_panel, self.tool_panel):
            self.pages.addWidget(panel)
        self.knowledge_panel = KnowledgePanel(service, self.guarded)
        self.pages.addWidget(self.knowledge_panel)
        self.tool_center = ToolCenter(service, self.guarded)
        self.jobs_panel = JobsPanel(service, self.guarded)
        self.dataset_panel = DatasetPanel(service, self.guarded)
        for title, panel in [("Tools & Integrations", self.tool_center), ("Jobs & Results", self.jobs_panel), ("Dataset Catalog", self.dataset_panel)]:
            nav.addItem(title)
            self.pages.addWidget(panel)
        nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        nav.setCurrentRow(0)
        self.setStyleSheet("QMainWindow {background:#f3f6fa;} QListWidget {background:#142639;color:#ecf1f8;border:0;padding:10px;} QListWidget::item {padding:12px;} QListWidget::item:selected {background:#29628c;} QPushButton {padding:9px;} QTextEdit,QLineEdit,QComboBox {background:white;padding:6px;} QLabel {color:#172e44;}")
        self.statusBar().showMessage(f"Local data: {service.root} · Approval and simulation execution unavailable")
        try:
            from integrations.v15_connector import V15ConnectorRegistry
            for connector in V15ConnectorRegistry.all():
                if connector.descriptor.tool_id not in self.service.integrations.adapters:
                    self.service.integrations.register_reviewed_adapter(connector)
        except Exception:
            pass
        self.refresh()

    def guarded(self, callback):
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, "Action could not be completed", str(exc))

    def closeEvent(self, event):
        self.jobs_panel.timer.stop()
        self.service.integrations.shutdown()
        super().closeEvent(event)

    def refresh(self):
        selected = self.product.product_id if self.product else None
        self.items = self.service.list_products()
        self.products.clear()
        for product in self.items:
            self.products.addItem(f"{product.code}\n{product.name} · {product.owner}")
        self.dashboard.setText(f"Mendex Engineering Studio\n\nv0.1 · Integrated foundation\n\n{len(self.items)} local products\n\nNext action: select a product, review specifications, open its workspace, discover tools, and record manual evidence.\n\nEngineering modules: framework only\nValidation: manual records available per revision\nTool qualification: pending · discovery and doctor available\n\nNo automated engineering results or approvals are generated.")
        index = next((i for i, p in enumerate(self.items) if p.product_id == selected), 0)
        if self.items:
            self.products.setCurrentRow(index)

    def select_product(self, row):
        if row < 0:
            self.product = None
            return
        self.product = self.items[row]
        self.name.setText(self.product.name)
        self.owner.setText(self.product.owner)
        self.description.setText(self.product.description)
        self.revisions.blockSignals(True)
        self.revisions.clear()
        for revision in self.service.list_revisions(self.product.product_id):
            self.revisions.addItem(f"{revision.revision_label} · {revision.lifecycle_status}", str(revision.revision_id))
        self.revisions.blockSignals(False)
        self.revisions.setCurrentIndex(self.revisions.count() - 1)
        self.select_revision(self.revisions.currentIndex())

    def select_revision(self, index):
        identifier = self.revisions.itemData(index)
        if not identifier:
            return
        self.revision = self.service.get_revision(identifier)
        path = self.service.workspace_path(self.revision)
        entries = self.service.validation_summary(self.revision.revision_id)
        validation = f"{len(entries)} manual entries; no product approval" if entries else "NOT_EVALUATED"
        numeric_fields = ("vin_min_v", "vin_nom_v", "vin_max_v", "vout_v", "iout_a", "switching_frequency_hz", "ambient_temperature_k")
        supplied = sum(getattr(self.revision.specification, name) is not None for name in numeric_fields)
        self.detail.setText(f"{self.product.code} · {self.revision.revision_label} · {self.revision.lifecycle_status}\nWorkspace: {path}\nSpecification: {supplied}/7 common numeric fields supplied · not an approval\nModules: NOT IMPLEMENTED · Validation: {validation} · Last run: none\nNext action: review specifications and manual evidence; engineering review remains required.")
        self.specification.setPlainText(json.dumps(self.revision.specification.model_dump(), indent=2))
        self.specification.setReadOnly(self.revision.lifecycle_status != "draft")
        if hasattr(self, "validation_panel"):
            self.validation_panel.set_revision(self.revision)
            self.reports_panel.set_revision(self.revision)
            self.simulation_panel.set_revision(self.revision)
            self.knowledge_panel.set_revision(self.revision)
            if hasattr(self, "transformer_ws"):
                self.transformer_ws.set_revision(self.revision)
            if hasattr(self, "dcdc_ws"):
                self.dcdc_ws.set_revision(self.revision)
            if hasattr(self, "semiconductor_ws"):
                self.semiconductor_ws.set_revision(self.revision)
            locations = ["magnetics", "circuit", "circuit", "pcb", "simulations"]
            requirements = ["Core geometry and material sources, winding construction, Bmax, duty limits and insulation requirements.", "Topology, input/output range, switching frequency, control mode, ripple and efficiency targets.", "MOSFET/IGBT/BJT datasheet, voltage/current/SOA ratings, gate drive and thermal assumptions.", "Native KiCad files, ERC/DRC evidence, clearance assumptions and qualified HV isolation review.", "Verified tool version, model inputs, solver logs, raw outputs and independently checked reference case."]
            for label, folder, requirement in zip(self.module_pages, locations, requirements):
                label.setWordWrap(True)
                label.setText(f"{folder.upper()} workspace · {self.product.code} · {self.revision.revision_label}\n\nPath: {path / folder}\n\nEngineering execution: NOT IMPLEMENTED\nProduct evaluation: NOT_EVALUATED\n\nRequired inputs: {requirement}\n\nUse native files and record available evidence in Validation. No solver or calculation is executed.")

    def create_product(self):
        dialog = ProductDialog(self)
        if dialog.exec() == QDialog.Accepted:
            def action():
                self.product = self.service.create_product(dialog.code.text(), dialog.name.text(), dialog.category.currentText(), dialog.owner.text())
                self.refresh()
            self.guarded(action)

    def save(self):
        if not self.product or not self.revision:
            return
        def action():
            specification = Specification.model_validate_json(self.specification.toPlainText())
            self.product, self.revision = self.service.save_product_revision(self.product.product_id, self.revision.revision_id, self.name.text(), self.owner.text(), self.description.text(), specification)
            self.refresh()
        self.guarded(action)

    def new_revision(self):
        if not self.product:
            return
        label, accepted = QInputDialog.getText(self, "New revision", "Unique revision label (for example R002)")
        if accepted:
            def action():
                self.service.create_revision(self.product.product_id, label)
                self.refresh()
            self.guarded(action)

    def rename_revision(self):
        revision = self.require_revision()
        label, accepted = QInputDialog.getText(self, "Rename draft revision", "Revision label", text=revision.revision_label)
        if accepted:
            self.service.rename_revision(revision.revision_id, label)
            self.refresh()

    def toggle_review(self):
        revision = self.require_revision()
        self.service.set_revision_status(revision.revision_id, "in_review" if revision.lifecycle_status == "draft" else "draft")
        self.refresh()

    def export_specification(self):
        path = self.service.export_specification(self.require_revision().revision_id)
        self.statusBar().showMessage(f"Specification snapshot exported: {path}")

    def require_revision(self):
        if not self.revision:
            raise ValueError("Select a product revision first")
        return self.revision

    def open_vscode(self):
        result = self.service.open_in_vscode(self.require_revision().revision_id)
        self.statusBar().showMessage(f"VS Code launch requested: {result['workspace']}")

    def open_workspace(self):
        self.service.open_project_file(self.require_revision().revision_id)

    def open_file(self):
        revision = self.require_revision()
        workspace = self.service.workspace_path(revision)
        filename, _ = QFileDialog.getOpenFileName(self, "Open a file within this revision", str(workspace))
        if filename:
            path = Path(filename).resolve()
            if not path.is_relative_to(workspace):
                raise ValueError("Select a file inside this revision workspace")
            self.service.open_project_file(revision.revision_id, str(path.relative_to(workspace)))
