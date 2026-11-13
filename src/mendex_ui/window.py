import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap
from .resources import LOGO_PATH, SHIELD_PATH, ICON_PATH, SHIELD_TRANSPARENT_PATH
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QFileDialog,
    QFrame, QCompleter, QTabWidget,
)

from mendex_core.models import Category, Specification
from mendex_core.knowledge import GUIDELINES, GUIDELINES_REVISION
from .panels import ToolPanel, ValidationPanel, ReportsPanel, SimulationPanel
from .integration_panels import ToolCenter, JobsPanel, DatasetPanel
from .workspace_panels import (
    TransformerWorkspacePanel,
    DCDCWorkspacePanel,
    SemiconductorWorkspacePanel,
)
from .theme import DARK_THEME_QSS, LIGHT_THEME_QSS
from .v17_panels import EnterpriseDashboardPanel
from .product_lifecycle_panel import ProductEngineeringOverviewPanel
from .pcb_panel import PCBWorkspacePanel
from .command_palette import CommandPaletteDialog
from .notification_center import NotificationCenterDialog
from .settings_panel import SettingsPanel
from .simulation_center_panel import SimulationCenterPanel
from .component_library_panel import ComponentLibraryPanel
from .reports_evidence_panel import ReportsEvidencePanel


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
        self.setWindowTitle("Mendex Engineering Studio v2.1")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1380, 880)

        # Initialize Command Palette & Notification Center
        self.command_palette = CommandPaletteDialog(self)
        self.notification_center = NotificationCenterDialog(self)
        self._init_command_palette_actions()

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

        brand_title = QLabel("MENDEX STUDIO v2.1")
        brand_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #89b4fa; letter-spacing: 0.5px;")
        header_layout.addWidget(brand_title)

        ws_label = QLabel("Active Project:")
        ws_label.setStyleSheet("color: #a6adc8; font-weight: 500;")
        header_layout.addWidget(ws_label)

        self.workspace_selector = QComboBox()
        self.workspace_selector.setMinimumWidth(220)
        self.workspace_selector.currentIndexChanged.connect(self._on_workspace_selected_header)
        header_layout.addWidget(self.workspace_selector)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tools, activities, waveforms, jobs... (Ctrl+K)")
        self.search_box.setMinimumWidth(240)
        header_layout.addWidget(self.search_box)

        # Global Command Palette Shortcuts (Ctrl+K and Ctrl+P)
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self.command_palette.show_palette)
        self.search_shortcut_p = QShortcut(QKeySequence("Ctrl+P"), self)
        self.search_shortcut_p.activated.connect(self.command_palette.show_palette)
        self.search_box.returnPressed.connect(self.command_palette.show_palette)
        self._init_search_completer()

        self.solver_badge = QLabel("● Solvers Status Loading...")
        self.solver_badge.setStyleSheet("background-color: #1c3b2b; color: #a6e3a1; border: 1px solid #2d5a3f; border-radius: 4px; padding: 4px 8px; font-weight: 600; font-size: 11px;")
        header_layout.addWidget(self.solver_badge)

        header_layout.addStretch()

        self.btn_notices = QPushButton("🔔 Notices")
        self.btn_notices.setStyleSheet("font-weight: 600; color: #89b4fa;")
        self.btn_notices.clicked.connect(self.notification_center.exec)
        header_layout.addWidget(self.btn_notices)


        self._dark_theme = True
        self.btn_theme_toggle = QPushButton("☀️ Light")
        self.btn_theme_toggle.setToolTip("Switch to Light Theme")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        root_layout.addWidget(self.top_header)

        # 2. Main Work Area (Sidebar Navigation + Stacked Pages)
        work_area = QWidget()
        work_area.setObjectName("work_area")
        layout = QHBoxLayout(work_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(220)
        sidebar_container.setObjectName("sidebar_container")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        nav = QListWidget()
        self.navigation = nav
        nav.setObjectName("nav_sidebar")
        nav.setFixedWidth(220)
        nav.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav.addItems([
            "Dashboard",
            "Engineering Projects",
            "Simulation Center",
            "Component Library",
            "Engineering Tools",
            "Reports & Evidence",
            "Settings",
        ])
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
        products.setObjectName("products_container")
        pane = QVBoxLayout(products)
        pane.setContentsMargins(12, 12, 12, 12)
        pane.setSpacing(10)

        workspace_actions = QHBoxLayout()
        workspace_actions.addWidget(QLabel("Engineering Projects"))
        workspace_actions.addStretch()
        self.btn_new_workspace = QPushButton("+ New Project")
        self.btn_new_workspace.setObjectName("create_workspace")
        self.btn_new_workspace.clicked.connect(lambda: self.guarded(self._create_workspace))
        workspace_actions.addWidget(self.btn_new_workspace)
        pane.addLayout(workspace_actions)

        split = QSplitter()
        split.setObjectName("products_splitter")

        # Left Column: Styled Catalog Sidebar
        catalog_card = QFrame()
        catalog_card.setObjectName("catalog_card")
        catalog_layout = QVBoxLayout(catalog_card)
        catalog_layout.setContentsMargins(12, 12, 12, 12)
        catalog_layout.setSpacing(10)

        cat_header = QHBoxLayout()
        cat_title = QLabel("📁 Project Catalog")
        cat_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        cat_header.addWidget(cat_title)
        cat_header.addStretch()
        self.lbl_product_count = QLabel("0 Projects")
        self.lbl_product_count.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;")
        cat_header.addWidget(self.lbl_product_count)
        catalog_layout.addLayout(cat_header)

        btn_row = QHBoxLayout()
        btn_new_prod = QPushButton("➕ New Project")
        btn_new_prod.setProperty("class", "primary_btn")
        btn_new_prod.clicked.connect(self.create_product)
        btn_row.addWidget(btn_new_prod, 1)

        btn_refresh_prod = QPushButton("🔄")
        btn_refresh_prod.setToolTip("Refresh projects")
        btn_refresh_prod.clicked.connect(self.refresh)
        btn_row.addWidget(btn_refresh_prod)

        self.btn_del_prod = QPushButton("🗑️")
        self.btn_del_prod.setToolTip("Delete selected project")
        self.btn_del_prod.clicked.connect(self.delete_current_product)
        btn_row.addWidget(self.btn_del_prod)
        catalog_layout.addLayout(btn_row)

        self.products = QListWidget()
        self.products.setObjectName("products_list")
        self.products.currentRowChanged.connect(self.select_product)
        catalog_layout.addWidget(self.products, 1)

        self.lbl_empty_catalog = QLabel("No engineering projects yet.\n\nUse Antigravity, Codex, or Claude Code to create designs.\nOr click '+ New Project' to define project specifications.")
        self.lbl_empty_catalog.setAlignment(Qt.AlignCenter)
        self.lbl_empty_catalog.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 30px 10px; line-height: 1.6;")
        catalog_layout.addWidget(self.lbl_empty_catalog)

        split.addWidget(catalog_card)

        # Right Column: Overview & Revisions
        editor = QWidget()
        editor.setObjectName("editor_container")
        form = QVBoxLayout(editor)

        top_editor_bar = QHBoxLayout()
        btn_back_to_overview = QPushButton("⬅ Back to 12-Stage Lifecycle Overview")
        btn_back_to_overview.clicked.connect(lambda: self.product_tabs.setCurrentIndex(0))
        top_editor_bar.addWidget(btn_back_to_overview)
        top_editor_bar.addStretch()
        form.addLayout(top_editor_bar)

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
        save = QPushButton("💾 Save draft specification")
        save.setProperty("class", "primary_btn")
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
        for title, callback in [("Open in VS Code", self.open_vscode), ("Open Project Folder", self.open_workspace), ("Open Project File", self.open_file)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, callback=callback: self.guarded(callback))
            handoff.addWidget(button)
        form.addLayout(handoff)

        self.product_tabs = QTabWidget()
        self.product_tabs.setObjectName("product_main_tabs")
        self.product_lifecycle = ProductEngineeringOverviewPanel(service)
        self.product_lifecycle.navigate_requested.connect(self._handle_overview_navigate)
        self.product_lifecycle.edit_specification_requested.connect(lambda: self.product_tabs.setCurrentIndex(1))
        self.product_lifecycle.create_product_requested.connect(self.create_product)
        self.product_tabs.addTab(self.product_lifecycle, "📊 12-Stage Project Lifecycle Overview")
        self.product_tabs.addTab(editor, "📝 Specifications & Revisions")

        split.addWidget(self.product_tabs)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 4)
        pane.addWidget(split)
        self.pages.addWidget(products)  # Page 1: Engineering Workspaces

        # Page 2: Simulation Center
        self.simulation_center = SimulationCenterPanel(service, self.guarded)
        self.pages.addWidget(self.simulation_center)

        # Page 3: Component Library
        self.component_library = ComponentLibraryPanel(service, self.guarded)
        self.pages.addWidget(self.component_library)

        # Page 4: Engineering Tools
        self.tool_center = ToolCenter(service, self.guarded)
        self.pages.addWidget(self.tool_center)

        # Page 5: Reports & Evidence
        self.reports_evidence = ReportsEvidencePanel(service, self.guarded)
        self.pages.addWidget(self.reports_evidence)

        # Page 6: Settings
        self.settings_panel = SettingsPanel(service, self.toggle_theme)
        self.settings_panel.apply_theme(self._dark_theme)
        self.pages.addWidget(self.settings_panel)

        # Preserved attributes for backward-compatible test access
        self.simulation_panel = SimulationPanel(service, self.guarded)
        self.reports_panel = self.reports_evidence.reports_panel
        self.validation_panel = self.reports_evidence.validation_panel
        self.tool_panel = ToolPanel(service, self.guarded)
        self.jobs_panel = JobsPanel(service, self.guarded)
        self.dataset_panel = self.component_library.dataset_panel

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
        self.pcb_ws = PCBWorkspacePanel(service, self.guarded)

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

    def _init_command_palette_actions(self):
        cp = self.command_palette
        cp.register_command("Open Engineering Projects", "view", "", lambda: self.navigation.setCurrentRow(1), "📐")
        cp.register_command("Open Simulation Center", "simulation", "Ctrl+Shift+S", lambda: self.navigation.setCurrentRow(2), "⚡")
        cp.register_command("Open Component Library", "view", "", lambda: self.navigation.setCurrentRow(3), "🧲")
        cp.register_command("Open Engineering Tools", "view", "", lambda: self.navigation.setCurrentRow(4), "🛠")
        cp.register_command("Open Reports & Evidence", "reports", "Ctrl+Shift+P", lambda: self.navigation.setCurrentRow(5), "📄")
        cp.register_command("Open Settings & Connections", "settings", "", lambda: self.navigation.setCurrentRow(6), "⚙️")
        cp.register_command("Run KiCad Schematic ERC", "pcb", "Ctrl+Shift+E", lambda: self.product_lifecycle._run_kicad_erc(), "⚡")
        cp.register_command("Run KiCad PCB DRC", "pcb", "Ctrl+Shift+D", lambda: self.product_lifecycle._run_kicad_drc(), "🛡️")
        cp.register_command("Export Manufacturing Gerbers", "pcb", "", lambda: self.product_lifecycle._export_gerbers(), "📦")
        cp.register_command("Export Engineering Verification Dossier", "reports", "", lambda: self.product_lifecycle._generate_dossier(), "📄")
        cp.register_command("Compare Product Revisions (Diff Viewer)", "diff", "Ctrl+D", self.open_revision_diff, "🔍")
        cp.register_command("Open Dowell HF Winding Loss Visualizer", "magnetics", "", self.open_dowell_visualizer, "🧲")
        cp.register_command("Open Magnetic Core Loss Comparator", "magnetics", "", self.open_magnetic_comparator, "⚖️")
        cp.register_command("Open FreeCAD 3D Bobbin Solid", "cad", "", lambda: self.product_lifecycle._open_step_model(), "📐")
        cp.register_command("Open Sizing & Calculations Inspector", "analysis", "", lambda: self.product_lifecycle.detail_tabs.setCurrentIndex(3), "🔬")
        cp.register_command("Open Bill of Materials (BOM)", "bom", "", lambda: self.product_lifecycle.detail_tabs.setCurrentIndex(2), "📋")
        cp.register_command("Toggle Dark / Light Theme", "view", "Ctrl+T", self.toggle_theme, "🌓")
        cp.register_command("Open Project Folder in Explorer", "workspace", "", lambda: self.product_lifecycle._open_workspace_folder(), "📂")
        cp.register_command("Re-Assess Engineering Lifecycle", "lifecycle", "F5", lambda: self.product_lifecycle.refresh_assessment(), "🔄")

    def _focus_search(self):
        self.search_box.setFocus()
        self.search_box.selectAll()

    def _init_search_completer(self):
        from .v17_panels import INVENTORY_DEFINITIONS
        items = [f"Resource: {resource['name']}" for resource in INVENTORY_DEFINITIONS]
        items.extend(f"View: {page}" for page in (
            "Dashboard", "Engineering Projects", "Simulation Center", "Component Library",
            "Engineering Tools", "Reports & Evidence", "Settings",
        ))
        items.append("Action: Toggle Dark / Light Theme")
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
        if "theme" in lower:
            self.toggle_theme()
        elif any(word in lower for word in ("dataset", "research", "component", "magnet", "switchloss")):
            self.navigation.setCurrentRow(3)
        elif any(word in lower for word in ("tool", "resource:", "ltspice", "kicad", "femm", "freecad", "openmodelica", "ngspice")):
            self.navigation.setCurrentRow(4)
        elif any(word in lower for word in ("job", "simulation", "waveform")):
            self.navigation.setCurrentRow(2)
        elif any(word in lower for word in ("report", "evidence", "validation")):
            self.navigation.setCurrentRow(5)
        elif any(word in lower for word in ("settings", "connection")):
            self.navigation.setCurrentRow(6)
        elif any(word in lower for word in ("project", "workspace", "design", "specification", "revision")):
            self.navigation.setCurrentRow(1)
        else:
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
                else:
                    if hasattr(self, "product_lifecycle"):
                        self.product_lifecycle.apply_theme(self._dark_theme)
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
            self.btn_theme_toggle.setText("☀️ Light")
            self.btn_theme_toggle.setToolTip("Switch to Light Theme")
        else:
            self.setStyleSheet(LIGHT_THEME_QSS)
            self.btn_theme_toggle.setText("🌙 Dark")
            self.btn_theme_toggle.setToolTip("Switch to Dark Theme")
        if hasattr(self, "product_lifecycle"):
            self.product_lifecycle.apply_theme(self._dark_theme)
        if hasattr(self, "settings_panel"):
            self.settings_panel.apply_theme(self._dark_theme)

    def _handle_dashboard_navigate(self, target: int):
        if 0 <= target < self.pages.count():
            self.navigation.setCurrentRow(target)





    def _handle_overview_navigate(self, target_name: str):
        mapping = {
            "Simulations": 2,  # Simulation Center
            "Transformer": 3,  # Component Library (Magnetics)
            "Component Library": 3,
            "SwitchLossDB": 3, # Component Library (SwitchLossDB tab)
            "DC-DC": 1,        # Engineering Workspaces
            "Validation": 5,   # Reports & Evidence
            "Reports": 5,      # Reports & Evidence
            "Tools": 4,        # Engineering Tools
            "Workflows": 1,    # Engineering Workspaces
            "Settings": 6,     # Settings
        }
        dest = mapping.get(target_name, 0)
        self.navigation.setCurrentRow(dest)
        if target_name == "SwitchLossDB" and hasattr(self, "component_library"):
            self.component_library.select_switchloss_tab()
        if target_name in ("Transformer", "Magnetics") and hasattr(self, "component_library"):
            self.component_library.select_magnetics_tab()

    def _on_workspace_selected_header(self, index: int):
        pass

    def _create_workspace(self):
        name, accepted = QInputDialog.getText(self, "New Engineering Workspace", "Workspace Name:")
        if accepted and name.strip():
            from mendex_core.controller import MendexEngineeringController
            ws = MendexEngineeringController(self.service.root).create_workspace(
                name=name.strip(), description="General engineering study"
            )
            self.refresh_workspace_selector()
            self.enterprise_dashboard.refresh_metrics()
            self.simulation_center._refresh_workspaces()
            self.statusBar().showMessage(f"Created workspace: {ws['name']}")

    def refresh_workspace_selector(self):
        self.workspace_selector.blockSignals(True)
        self.workspace_selector.clear()
        projects = self.service.list_products()
        workspaces = self.service.integrations.list_workspaces()
        for p in projects:
            self.workspace_selector.addItem(f"📁 {p.code} — {p.name}", str(p.product_id))
        for ws in workspaces:
            if not any(str(p.product_id) == ws.get("workspace_id") or str(p.product_id) == ws.get("product_id") for p in projects):
                self.workspace_selector.addItem(f"📁 {ws.get('name', 'Workspace')}", ws.get("workspace_id"))
        if self.workspace_selector.count() == 0:
            self.workspace_selector.addItem("No engineering projects yet", None)
        self.workspace_selector.blockSignals(False)

    def guarded(self, callback):
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, "Action could not be completed", str(exc))

    def closeEvent(self, event):
        if self.pcb_ws.is_running():
            self.statusBar().showMessage("A KiCad check is finishing. Close Studio after the check completes.")
            event.ignore()
            return
        self._save_preferences()
        if hasattr(self, 'jobs_panel') and hasattr(self.jobs_panel, 'timer'): self.jobs_panel.timer.stop()
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
            if hasattr(self, "lbl_empty_catalog"):
                self.lbl_empty_catalog.setVisible(False)
            self.products.setVisible(True)
            if hasattr(self, "lbl_product_count"):
                self.lbl_product_count.setText(f"{len(self.items)} Project{'s' if len(self.items) > 1 else ''}")
            self.products.setCurrentRow(index)
        else:
            self.products.setVisible(False)
            if hasattr(self, "lbl_empty_catalog"):
                self.lbl_empty_catalog.setVisible(True)
            if hasattr(self, "lbl_product_count"):
                self.lbl_product_count.setText("0 Projects")
            self.select_product(-1)
        self.refresh_workspace_selector()
        if hasattr(self, "enterprise_dashboard"):
            self.enterprise_dashboard.refresh_metrics()

    def select_product(self, row):
        if row < 0 or not self.items:
            self.product = None
            self.revision = None
            self.pcb_ws.set_revision(None)
            self.name.clear()
            self.owner.clear()
            self.description.clear()
            self.specification.clear()
            self.revisions.blockSignals(True)
            self.revisions.clear()
            self.revisions.blockSignals(False)
            self.detail.setText("Select or create a product to begin")
            if hasattr(self, "product_lifecycle"):
                self.product_lifecycle.set_product(None)
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
            if hasattr(self, "product_lifecycle") and self.product:
                self.product_lifecycle.set_product(self.product.product_id, self.revision.revision_id)
            if hasattr(self, "transformer_ws"):
                self.transformer_ws.set_revision(self.revision)
            if hasattr(self, "dcdc_ws"):
                self.dcdc_ws.set_revision(self.revision)
            if hasattr(self, "semiconductor_ws"):
                self.semiconductor_ws.set_revision(self.revision)
            self.pcb_ws.set_revision(self.revision)
            locations = ["magnetics", "circuit", "circuit", "pcb", "simulations"]
            requirements = ["Core geometry and material sources, winding construction, Bmax, duty limits and insulation requirements.", "Topology, input/output range, switching frequency, control mode, ripple and efficiency targets.", "MOSFET/IGBT/BJT datasheet, voltage/current/SOA ratings, gate drive and thermal assumptions.", "Native KiCad files, ERC/DRC evidence, clearance assumptions and qualified HV isolation review.", "Verified tool version, model inputs, solver logs, raw outputs and independently checked reference case."]
            for label, folder, requirement in zip(self.module_pages, locations, requirements):
                label.setWordWrap(True)
                label.setText(f"{folder.upper()} workspace · {self.product.code} · {self.revision.revision_label}\n\nPath: {path / folder}\n\nEngineering execution: NOT IMPLEMENTED\nProduct evaluation: NOT_EVALUATED\n\nRequired inputs: {requirement}\n\nUse native files and record available evidence in Validation. No solver or calculation is executed.")

    def open_dowell_visualizer(self):
        from .dowell_visualizer_dialog import DowellWindingLossDialog
        dlg = DowellWindingLossDialog(parent=self, is_dark=self._dark_theme)
        dlg.exec()

    def open_magnetic_comparator(self):
        from .magnetic_comparator_dialog import MagneticCoreLossComparatorDialog
        dlg = MagneticCoreLossComparatorDialog(parent=self, is_dark=self._dark_theme)
        dlg.exec()

    def open_revision_diff(self):
        if hasattr(self, "product_lifecycle") and self.product_lifecycle.current_product_id:
            self.product_lifecycle._open_revision_diff()
        else:
            prods = self.service.list_products()
            if prods:
                from .revision_diff_dialog import RevisionDiffDialog
                dlg = RevisionDiffDialog(self.service, prods[0].product_id, is_dark=self._dark_theme, parent=self)
                dlg.exec()
            else:
                QMessageBox.information(self, "No Projects", "Please create a project first.")

    def create_product(self):
        from .product_wizard_dialog import ProductDesignWizardDialog
        dialog = ProductDesignWizardDialog(self.service, is_dark=self._dark_theme, parent=self)
        if dialog.exec() == QDialog.Accepted and dialog.created_product:
            def action():
                self.product = dialog.created_product
                self.revision = dialog.created_revision
                self.refresh()
                if hasattr(self, "product_lifecycle") and self.product:
                    self.product_lifecycle.set_product(self.product.product_id, self.revision.revision_id if self.revision else None)
                self.statusBar().showMessage(f"Project '{self.product.code} - {self.product.name}' successfully created & synthesized.")
            self.guarded(action)

    def delete_current_product(self):
        if not self.product:
            QMessageBox.information(self, "No Product Selected", "Please select a product from the list to delete.")
            return
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete product '{self.product.code} - {self.product.name}'?\n\nThis will remove the product, all its revisions, and workspace files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            def action():
                self.service.delete_product(self.product.product_id)
                self.product = None
                self.revision = None
                self.refresh()
                self.statusBar().showMessage("Product successfully deleted.")
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
