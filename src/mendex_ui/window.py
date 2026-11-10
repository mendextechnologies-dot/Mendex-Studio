import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap
from .resources import LOGO_PATH, SHIELD_PATH, ICON_PATH, SHIELD_TRANSPARENT_PATH
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QFileDialog,
    QFrame, QCompleter,
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
from .theme import DARK_THEME_QSS, LIGHT_THEME_QSS
from .v17_panels import EnterpriseDashboardPanel
from .workflow_canvas import WorkflowStudioPanel


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
        self.setWindowTitle("Mendex Engineering Studio v1.9 · Enterprise Edition")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1380, 880)

        # Central Root Container
        root_container = QWidget()
        self.setCentralWidget(root_container)
        root_layout = QVBoxLayout(root_container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Global Enterprise Top Header Bar
        self.top_header = QFrame()
        self.top_header.setObjectName("top_header")
        header_layout = QHBoxLayout(self.top_header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)

        if SHIELD_TRANSPARENT_PATH.exists():
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(SHIELD_TRANSPARENT_PATH)).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setToolTip("Mendex Technologies — Engineering Studio")
            header_layout.addWidget(logo_label)

        brand_title = QLabel("MENDEX STUDIO v1.9")
        brand_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #89b4fa; letter-spacing: 0.5px;")
        header_layout.addWidget(brand_title)

        ws_label = QLabel("Active Workspace:")
        ws_label.setStyleSheet("color: #a6adc8; font-weight: 500;")
        header_layout.addWidget(ws_label)

        self.workspace_selector = QComboBox()
        self.workspace_selector.setMinimumWidth(220)
        self.workspace_selector.currentIndexChanged.connect(self._on_workspace_selected_header)
        header_layout.addWidget(self.workspace_selector)

        btn_new_ws = QPushButton("+ New Workspace")
        btn_new_ws.clicked.connect(self._create_header_workspace)
        header_layout.addWidget(btn_new_ws)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tools, activities, waveforms, jobs... (Ctrl+K)")
        self.search_box.setMinimumWidth(260)
        header_layout.addWidget(self.search_box)

        # Command Palette / Shortcut
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self._focus_search)
        self.search_box.returnPressed.connect(self._on_search_submitted)
        self._init_search_completer()

        self.solver_badge = QLabel("● Solvers Status Loading...")
        self.solver_badge.setStyleSheet("background-color: #1c3b2b; color: #a6e3a1; border: 1px solid #2d5a3f; border-radius: 4px; padding: 4px 8px; font-weight: 600; font-size: 11px;")
        header_layout.addWidget(self.solver_badge)

        header_layout.addStretch()

        self._dark_theme = True
        self.btn_theme_toggle = QPushButton("🌙 Dark")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        root_layout.addWidget(self.top_header)

        # 2. Main Work Area (Sidebar Navigation + Stacked Pages)
        work_area = QWidget()
        layout = QHBoxLayout(work_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(220)
        sidebar_container.setObjectName("sidebar_container")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Branded Header in Sidebar
        brand_card = QFrame()
        brand_card.setObjectName("sidebar_brand")
        brand_card.setStyleSheet("background-color: #11111b; border-bottom: 1px solid #313244; padding: 12px 14px;")
        b_layout = QHBoxLayout(brand_card)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(10)

        if SHIELD_TRANSPARENT_PATH.exists():
            s_label = QLabel()
            s_label.setPixmap(QPixmap(str(SHIELD_TRANSPARENT_PATH)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            b_layout.addWidget(s_label)

        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        t1 = QLabel("MENDEX")
        t1.setStyleSheet("font-weight: 800; font-size: 13px; color: #cdd6f4; letter-spacing: 1px;")
        t2 = QLabel("TECHNOLOGIES")
        t2.setStyleSheet("font-size: 9px; font-weight: 600; color: #a6e3a1; letter-spacing: 0.5px;")
        t_box.addWidget(t1)
        t_box.addWidget(t2)
        b_layout.addLayout(t_box)
        b_layout.addStretch()

        sidebar_layout.addWidget(brand_card)

        nav = QListWidget()
        self.navigation = nav
        nav.setObjectName("nav_sidebar")
        nav.setFixedWidth(220)
        nav.addItems(["Dashboard", "Products", "Transformer", "DC–DC Converter", "Switching Devices", "PCB Workspace", "Simulations", "Validation", "Reports", "Tool Manager", "Knowledge Center"])
        sidebar_layout.addWidget(nav, 1)

        self.pages = QStackedWidget()
        layout.addWidget(sidebar_container)
        layout.addWidget(self.pages, 1)
        root_layout.addWidget(work_area, 1)

        # Page 0: Enterprise Dashboard
        dash_container = QWidget()
        dash_layout = QVBoxLayout(dash_container)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        self.enterprise_dashboard = EnterpriseDashboardPanel(service)
        self.enterprise_dashboard.navigate_requested.connect(self._handle_dashboard_navigate)
        dash_layout.addWidget(self.enterprise_dashboard)

        # Preserved legacy dashboard label for backwards compatibility
        self.dashboard = QLabel()
        self.dashboard.setMargin(30)
        self.dashboard.setAlignment(Qt.AlignTop)
        self.dashboard.setVisible(False)
        dash_layout.addWidget(self.dashboard)

        self.pages.addWidget(dash_container)

        # Page 1: Products
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

        # Pages 2-5: Engineering Workspaces
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

        # Pages 6-10: Simulations, Validation, Reports, Tools, Knowledge
        self.simulation_panel = SimulationPanel(service, self.guarded)
        self.pages.addWidget(self.simulation_panel)
        self.validation_panel = ValidationPanel(service, self.guarded)
        self.reports_panel = ReportsPanel(service, self.guarded)
        self.tool_panel = ToolPanel(service, self.guarded)
        for panel in (self.validation_panel, self.reports_panel, self.tool_panel):
            self.pages.addWidget(panel)
        self.knowledge_panel = KnowledgePanel(service, self.guarded)
        self.pages.addWidget(self.knowledge_panel)

        # Pages 11-13: Tools & Integrations, Jobs & Results, Dataset Catalog
        self.tool_center = ToolCenter(service, self.guarded)
        self.jobs_panel = JobsPanel(service, self.guarded)
        self.dataset_panel = DatasetPanel(service, self.guarded)
        for title, panel in [("Tools & Integrations", self.tool_center), ("Jobs & Results", self.jobs_panel), ("Dataset Catalog", self.dataset_panel)]:
            nav.addItem(title)
            self.pages.addWidget(panel)

        # Page 14: Visual Workflow Studio
        self.workflow_studio = WorkflowStudioPanel(service)
        nav.addItem("Workflow Studio")
        self.pages.addWidget(self.workflow_studio)

        nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        nav.setCurrentRow(0)

        # Apply Enterprise Dark Design System
        self.setStyleSheet(DARK_THEME_QSS)

        self.statusBar().showMessage(f"Local data: {service.root} · Approval and simulation execution unavailable")
        try:
            from integrations.v15_connector import V15ConnectorRegistry
            for connector in V15ConnectorRegistry.all():
                if connector.descriptor.tool_id not in self.service.integrations.adapters:
                    self.service.integrations.register_reviewed_adapter(connector)
        except Exception:
            pass
        self._update_solver_badge()
        self.refresh()
        self._load_preferences()

    def _update_solver_badge(self):
        ready_solvers = 0
        total_solvers = len(self.service.integrations.list_tools())
        for tid in ("ltspice", "kicad", "femm", "freecad", "qucs-s", "openmodelica"):
            try:
                h = self.service.integrations.verify(tid)
                st = h.state.value if hasattr(h.state, "value") else str(h.state)
                if st == "READY":
                    ready_solvers += 1
            except Exception:
                pass
        self.solver_badge.setText(f"● {ready_solvers} Solvers READY · {total_solvers} Catalog")

    def _focus_search(self):
        self.search_box.setFocus()
        self.search_box.selectAll()

    def _init_search_completer(self):
        items = []
        try:
            from .v17_panels import INVENTORY_DEFINITIONS
            for res in INVENTORY_DEFINITIONS:
                items.append(f"Resource: {res['name']} ({res['status']})")
        except Exception:
            pass

        items.extend([
            "View: Dashboard",
            "View: Tools & Integrations",
            "View: Jobs & Simulations",
            "View: Research Datasets",
            "View: Knowledge Center",
            "View: Workflow Studio",
            "Action: + New Visual Workflow",
            "Action: + New Engineering Workspace",
            "Action: Toggle Dark / Light Theme",
        ])
        self.search_completer = QCompleter(items, self)
        self.search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.search_completer.setFilterMode(Qt.MatchContains)
        self.search_completer.activated.connect(self._on_search_item_activated)
        self.search_box.setCompleter(self.search_completer)

    def _on_search_submitted(self):
        text = self.search_box.text().strip()
        if text:
            self._on_search_item_activated(text)

    def _on_search_item_activated(self, text: str):
        lower = text.lower()
        if "workspace" in lower and "action" in lower:
            self._create_header_workspace()
        elif "theme" in lower:
            self.toggle_theme()
        elif any(k in lower for k in ("tool", "ltspice", "kicad", "femm", "freecad", "openmodelica", "ngspice")):
            self.navigation.setCurrentRow(11)  # Tools & Integrations
        elif any(k in lower for k in ("job", "simulation")):
            self.navigation.setCurrentRow(12)  # Jobs & Results
        elif any(k in lower for k in ("dataset", "research")):
            self.navigation.setCurrentRow(13)  # Dataset Catalog
        elif "knowledge" in lower:
            self.navigation.setCurrentRow(10)  # Knowledge Center
        elif "workflow" in lower:
            self.navigation.setCurrentRow(14)  # Workflow Studio
        elif "dashboard" in lower:
            self.navigation.setCurrentRow(0)
        self.search_box.clear()

    def _pref_file(self) -> Path:
        return self.service.root / ".mendex" / "ui_preferences.json"

    def _load_preferences(self):
        pfile = self._pref_file()
        if pfile.exists():
            try:
                import json as _json
                data = _json.loads(pfile.read_text(encoding="utf-8"))
                if "width" in data and "height" in data:
                    self.resize(int(data["width"]), int(data["height"]))
                if "is_dark" in data and not data["is_dark"]:
                    self.toggle_theme()
            except Exception:
                pass

    def _save_preferences(self):
        try:
            import json as _json
            pfile = self._pref_file()
            pfile.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "width": self.width(),
                "height": self.height(),
                "is_dark": self._dark_theme,
                "current_nav_row": self.navigation.currentRow(),
            }
            pfile.write_text(_json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def toggle_theme(self):
        self._dark_theme = not self._dark_theme
        if self._dark_theme:
            self.setStyleSheet(DARK_THEME_QSS)
            self.btn_theme_toggle.setText("🌙 Dark")
        else:
            self.setStyleSheet(LIGHT_THEME_QSS)
            self.btn_theme_toggle.setText("☀️ Light")

    def _handle_dashboard_navigate(self, target: int):
        mapping = {1: 12, 2: 11, 3: 6, 4: 10, 5: 13, 6: 14}
        dest = mapping.get(target, 0)
        self.navigation.setCurrentRow(dest)

    def _on_workspace_selected_header(self, index: int):
        pass

    def _create_header_workspace(self):
        name, accepted = QInputDialog.getText(self, "New Engineering Workspace", "Workspace Name:")
        if accepted and name.strip():
            ws = self.service.integrations.create_workspace(name=name.strip(), description="General engineering study")
            self.refresh_workspace_selector()
            self.enterprise_dashboard.refresh_metrics()
            self.statusBar().showMessage(f"Created workspace: {ws['name']}")

    def refresh_workspace_selector(self):
        self.workspace_selector.blockSignals(True)
        self.workspace_selector.clear()
        workspaces = self.service.integrations.list_workspaces()
        for ws in workspaces:
            self.workspace_selector.addItem(f"📁 {ws.get('name', 'Workspace')}", ws.get("workspace_id"))
        if not workspaces:
            self.workspace_selector.addItem("No workspaces yet", None)
        self.workspace_selector.blockSignals(False)

    def guarded(self, callback):
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, "Action could not be completed", str(exc))

    def closeEvent(self, event):
        self._save_preferences()
        self.jobs_panel.timer.stop()
        self.service.integrations.shutdown()
        super().closeEvent(event)

    def refresh(self):
        selected = self.product.product_id if self.product else None
        self.items = self.service.list_products()
        self.products.clear()
        for product in self.items:
            self.products.addItem(f"{product.code}\n{product.name} · {product.owner}")
        self.dashboard.setText(f"Mendex Engineering Studio\n\nv1.7 · Integrated foundation\n\n{len(self.items)} local products\n\nNext action: select a product, review specifications, open its workspace, discover tools, and record manual evidence.\n\nEngineering modules: framework only\nValidation: manual records available per revision\nTool qualification: pending · discovery and doctor available\n\nNo automated engineering results or approvals are generated.")
        index = next((i for i, p in enumerate(self.items) if p.product_id == selected), 0)
        if self.items:
            self.products.setCurrentRow(index)
        self.refresh_workspace_selector()
        if hasattr(self, "enterprise_dashboard"):
            self.enterprise_dashboard.refresh_metrics()

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
