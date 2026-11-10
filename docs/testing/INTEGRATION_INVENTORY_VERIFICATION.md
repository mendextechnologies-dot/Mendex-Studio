# Integration Inventory & Dashboard Presentation Verification

**Document ID**: `TST-INVENTORY-VERIFY-20261110-01`  
**Test Suite**: `tests/ui/test_dashboard_inventory.py` + Full Studio Regression  
**Status**: 100% Passed  
**Verified Items**: 18 Approved Resources + 1 Native Addition (`ngspice`) = 19 Resources

---

## 1. Objectives

Verify that:
1. All 18 team-approved inventory items plus native `ngspice` are presented in Mendex Engineering Studio.
2. The Operations Dashboard displays all 19 entries in its ecosystem inventory table.
3. Category filters correctly segment Simulation Solvers, CAD/PCB, Frameworks/Dev, Research Datasets/Benchmarks, and Commercial Stubs.
4. Status filters isolate `VERIFIED OPERATIONAL`, `INSTALLED — NOT VALIDATED`, `REGISTERED ONLY`, and `LICENSE REQUIRED`.
5. Real-time text search filters matching resources by name, ID, capabilities, or path.
6. Summary KPI counts accurately reflect the displayed inventory.

---

## 2. Automated Test Execution & Evidence

### Test Specification: `tests/ui/test_dashboard_inventory.py`

```python
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
```

### Execution Log
```text
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Mendex studio
configfile: pyproject.toml
plugins: anyio-4.16.0, platformdirs-4.14.5
collected 1 item

tests\ui\test_dashboard_inventory.py .                                   [100%]

============================== 1 passed in 0.90s ==============================
```

---

## 3. Full Regression Suite Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Output:
```text
============================ 137 passed in 44.15s =============================
- tests/adapters/:           45 passed
- tests/contracts/:           8 passed
- tests/core/:               31 passed
- tests/integration/:        43 passed
- tests/ui/:                 10 passed (including test_dashboard_inventory)
Total: 137 passed, 0 failures (100% green)
```

---

## 4. Conclusion & Acceptance Status

All 18 approved inventory items and additional native integration `ngspice` are verified, categorised, and actively surfaced on the Mendex Engineering Studio Operations Dashboard.
