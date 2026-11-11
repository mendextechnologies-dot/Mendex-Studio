import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.v17_panels import EnterpriseDashboardPanel, INVENTORY_DEFINITIONS


def test_dashboard_inventory_supported_resources_plus_ngspice(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = EnterpriseDashboardPanel(service)

    # 1. Verify 14 total inventory definitions
    assert len(INVENTORY_DEFINITIONS) == 14
    ids = {item["id"] for item in INVENTORY_DEFINITIONS}
    expected_supported = {
        "switchlossdb", "magnet-dataset", "magnet-ml-benchmarks", "kicad", "femm",
        "magnet-princeton", "ltspice",
        "freecad", "qucs-s", "openmodelica", "python", "jupyter",
        "git",
    }
    assert expected_supported.issubset(ids)
    assert "ngspice" in ids
    assert ids == {tool.tool_id for tool in service.integrations.list_tools()} | {"ngspice"}
    assert len(panel.scope_btns) == 4
    assert all("Commercial" not in panel.category_filter.itemText(i) for i in range(panel.category_filter.count()))
    assert all("LICENSE REQUIRED" != panel.status_filter.itemText(i) for i in range(panel.status_filter.count()))

    # 2. Table initial row count and column count (8 columns)
    panel.refresh_metrics()
    assert panel.tools_table.rowCount() == 14
    assert panel.tools_table.columnCount() == 8

    # 3. Scope Tab button filtering (Separating Datasets & Solvers)
    panel._on_scope_btn_clicked(1)  # Simulation Solvers & CAD
    assert panel.tools_table.rowCount() == 7  # ltspice, ngspice, femm, qucs-s, openmodelica, kicad, freecad

    panel._on_scope_btn_clicked(2)  # Frameworks & Dev
    assert panel.tools_table.rowCount() == 3  # python, git, jupyter

    panel._on_scope_btn_clicked(3)  # Research Datasets & Benchmarks
    assert panel.tools_table.rowCount() == 4  # switchlossdb, magnet-dataset, magnet-ml-benchmarks, magnet-princeton

    panel._on_scope_btn_clicked(0)  # All Resources
    assert panel.tools_table.rowCount() == 14

    # 4. Filter by category dropdown
    panel.category_filter.setCurrentText("Simulation Solvers")
    assert panel.tools_table.rowCount() == 5  # ltspice, femm, qucs-s, openmodelica, ngspice

    panel.category_filter.setCurrentText("CAD and PCB Tools")
    assert panel.tools_table.rowCount() == 2  # kicad, freecad

    panel.category_filter.setCurrentText("Research Datasets")
    assert panel.tools_table.rowCount() == 3

    panel.category_filter.setCurrentText("Benchmark Resources")
    assert panel.tools_table.rowCount() == 1

    # 5. Filter by status dropdown
    panel.category_filter.setCurrentText("All Categories (14)")
    panel.status_filter.setCurrentText("VERIFIED OPERATIONAL")
    # A fresh core with no reviewed connectors has no verified operations.
    assert panel.tools_table.rowCount() == 0

    # 6. Search query filtering
    panel.status_filter.setCurrentText("All Statuses")
    panel.search_filter.setText("spice")
    assert panel.tools_table.rowCount() >= 2  # ltspice, ngspice

    panel.search_filter.setText("")
    assert panel.tools_table.rowCount() == 14
