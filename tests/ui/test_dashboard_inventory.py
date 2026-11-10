import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.v17_panels import EnterpriseDashboardPanel, INVENTORY_DEFINITIONS


def test_dashboard_inventory_all_18_resources_plus_ngspice(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    panel = EnterpriseDashboardPanel(service)

    # 1. Verify 19 total inventory definitions
    assert len(INVENTORY_DEFINITIONS) == 19
    ids = {item["id"] for item in INVENTORY_DEFINITIONS}
    expected_18 = {
        "switchlossdb", "magnet-dataset", "magnet-ml-benchmarks", "kicad", "femm",
        "magnet-princeton", "ltspice", "plecs", "matlab-simulink", "ansys-maxwell",
        "ansys-icepak", "freecad", "qucs-s", "openmodelica", "python", "jupyter",
        "git", "solidworks",
    }
    assert expected_18.issubset(ids)
    assert "ngspice" in ids

    # 2. Table initial row count
    panel.refresh_metrics()
    assert panel.tools_table.rowCount() == 19

    # 3. Filter by category
    panel.category_filter.setCurrentText("Simulation Solvers")
    assert panel.tools_table.rowCount() == 5  # ltspice, femm, qucs-s, openmodelica, ngspice

    panel.category_filter.setCurrentText("CAD and PCB Tools")
    assert panel.tools_table.rowCount() == 2  # kicad, freecad

    panel.category_filter.setCurrentText("Commercial Integrations")
    assert panel.tools_table.rowCount() == 5  # plecs, matlab-simulink, ansys-maxwell, ansys-icepak, solidworks

    panel.category_filter.setCurrentText("Research Datasets")
    assert panel.tools_table.rowCount() == 3  # switchlossdb, magnet-dataset, magnet-princeton

    panel.category_filter.setCurrentText("Benchmark Resources")
    assert panel.tools_table.rowCount() == 1  # magnet-ml-benchmarks

    # 4. Filter by status
    panel.category_filter.setCurrentText("All Categories (19)")
    panel.status_filter.setCurrentText("LICENSE REQUIRED")
    assert panel.tools_table.rowCount() == 5

    panel.status_filter.setCurrentText("VERIFIED OPERATIONAL")
    assert panel.tools_table.rowCount() == 4  # ltspice, python, git, ngspice

    # 5. Search query filtering
    panel.status_filter.setCurrentText("All Statuses")
    panel.search_filter.setText("spice")
    assert panel.tools_table.rowCount() >= 2  # ltspice, ngspice

    panel.search_filter.setText("")
    assert panel.tools_table.rowCount() == 19
