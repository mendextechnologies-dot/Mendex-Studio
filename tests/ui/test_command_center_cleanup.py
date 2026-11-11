"""Verify the agent-led desktop has clean project actions and working navigation."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QInputDialog

from mendex_core.service import StudioService
from mendex_core.controller import MendexEngineeringController
from mendex_ui.window import StudioWindow


def test_workspace_action_is_unique_and_persists_through_core(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = StudioWindow(StudioService(tmp_path))
    window.show()
    app.processEvents()
    try:
        for area in (window.top_header, window.enterprise_dashboard):
            labels = [button.text() for button in area.findChildren(QPushButton)]
            assert not any(word in text for text in labels for word in (
                "New Project", "New Workspace", "New Engineering Design", "Ask AI", "Launch Design Wizard",
            ))
        assert sum("New Project" in button.text() for button in window.findChildren(QPushButton)) >= 1
        assert not any(hasattr(window, name) for name in ("knowledge_panel", "design_studio", "workflow_studio"))
        assert not any("New Engineering Design" in cmd.title or "AI Integration" in cmd.title for cmd in window.command_palette.commands)

        window.navigation.setCurrentRow(1)
        app.processEvents()
        assert window.btn_new_workspace.isVisible()
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Agent-led reference", True))
        window.btn_new_workspace.click()
        workspaces = MendexEngineeringController(tmp_path).list_workspaces()
        assert len(workspaces) == 1
        workspace_id = workspaces[0]["workspace_id"]
        assert workspaces[0]["name"] == "Agent-led reference"
        assert (tmp_path / "workspaces" / workspace_id).is_dir()
        assert window.workspace_selector.findData(workspace_id) >= 0
        assert window.simulation_center.combo_ws.findData(workspace_id) >= 0
    finally:
        window.close()


def test_search_and_resource_navigation_use_current_pages(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = StudioWindow(StudioService(tmp_path))
    try:
        for term, page in [
            ("Dashboard", 0), ("Engineering Projects", 1), ("jobs", 2),
            ("Research Datasets", 3), ("LTspice", 4), ("Reports & Evidence", 5), ("Settings", 6),
        ]:
            window._on_search_item_activated(term)
            assert window.navigation.currentRow() == page
            assert window.pages.currentIndex() == page

        dashboard = window.enterprise_dashboard
        for row in range(dashboard.tools_table.rowCount()):
            name = dashboard.tools_table.item(row, 0).text()
            dashboard._on_table_item_double_clicked(dashboard.tools_table.item(row, 0))
            assert window.navigation.currentRow() == (3 if "MagNet" in name or "SwitchLoss" in name else 4)
        model = window.search_completer.model()
        completer_items = [model.data(model.index(i, 0)) for i in range(model.rowCount())]
        assert "View: Dashboard" in completer_items
        assert "View: Engineering Projects" in completer_items
        assert "View: Simulation Center" in completer_items
        assert "View: Component Library" in completer_items
        assert "View: Engineering Tools" in completer_items
        assert "View: Reports & Evidence" in completer_items
        assert "View: Settings" in completer_items
    finally:
        window.close()
