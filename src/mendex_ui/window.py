import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from mendex_core.models import Category, Specification


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
        split.addWidget(editor)
        split.setStretchFactor(1, 3)
        pane.addWidget(split)
        self.pages.addWidget(products)
        for title in ("Transformer", "DC–DC Converter", "Switching Devices", "PCB Workspace", "Simulations", "Validation", "Reports", "Tool Manager"):
            label = QLabel(f"{title}\n\nImplementation: NOT IMPLEMENTED\nProduct evaluation: NOT_EVALUATED\n\nFoundation workspace only. No calculation, tool execution or result is available.")
            label.setMargin(30)
            label.setAlignment(Qt.AlignTop)
            self.pages.addWidget(label)
        knowledge = QTextEdit()
        knowledge.setReadOnly(True)
        knowledge.setPlainText("Engineering guidelines · revision 0.1\n\nUse SI units and record sources and assumptions.\nMissing evidence is NOT_EVALUATED.\nSimulation does not establish compliance or physical safety.\nTransformer design requires material data, winding assumptions, duty limits and standards review.\nHV hardware requires qualified review and a separately authorized physical test plan.\nManufacturing approval is unavailable in v0.1.")
        self.pages.addWidget(knowledge)
        nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        nav.setCurrentRow(0)
        self.setStyleSheet("QMainWindow {background:#f3f6fa;} QListWidget {background:#142639;color:#ecf1f8;border:0;padding:10px;} QListWidget::item {padding:12px;} QListWidget::item:selected {background:#29628c;} QPushButton {padding:9px;} QTextEdit,QLineEdit,QComboBox {background:white;padding:6px;} QLabel {color:#172e44;}")
        self.statusBar().showMessage(f"Local data: {service.root} · Approval and simulation execution unavailable")
        self.refresh()

    def guarded(self, callback):
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, "Action could not be completed", str(exc))

    def refresh(self):
        selected = self.product.product_id if self.product else None
        self.items = self.service.list_products()
        self.products.clear()
        for product in self.items:
            self.products.addItem(f"{product.code}\n{product.name} · {product.owner}")
        self.dashboard.setText(f"Mendex Engineering Studio\n\nv0.1 · Day 1 foundation\n\n{len(self.items)} local products\n\nNext action: create a product, capture specifications, then save a revision.\n\nEngineering modules: framework only\nValidation: NOT_EVALUATED\nTool qualification: pending\n\nNo engineering results or approvals have been generated.")
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
        self.detail.setText(f"{self.product.code} · {self.revision.revision_label} · {self.revision.lifecycle_status}\nWorkspace: {path}\nModules: NOT IMPLEMENTED · Validation: NOT_EVALUATED · Last run: none\nNext action: complete specifications; engineering review remains required.")
        self.specification.setPlainText(json.dumps(self.revision.specification.model_dump(), indent=2))
        self.specification.setReadOnly(self.revision.lifecycle_status != "draft")

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
            self.service.update_specification(self.revision.revision_id, specification)
            self.product = self.service.update_product(self.product.product_id, self.name.text(), self.owner.text(), self.description.text())
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
