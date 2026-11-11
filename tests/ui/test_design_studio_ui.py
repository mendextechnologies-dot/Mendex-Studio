"""Unit and integration tests for Design Studio UI and tool launch input validation."""
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_core.launch import launch_tool, open_native
from mendex_ui.design_studio_panel import NewEngineeringDesignDialog, EngineeringDesignStudioPanel


def test_tool_launch_rejects_incompatible_inputs(tmp_path):
    step_file = tmp_path / "bobbin.step"
    step_file.write_text("ISO-10303-21; HEADER;", encoding="utf-8")

    # 1. KiCad Schematic Editor must reject .step files
    with pytest.raises(ValueError, match="KiCad Schematic Editor requires a schematic file"):
        launch_tool("kicad_sch", step_file)

    # 2. KiCad PCB Editor must reject .step files
    with pytest.raises(ValueError, match="KiCad PCB Editor requires a board layout file"):
        launch_tool("kicad_pcb", step_file)

    # 3. KiCad Project Manager must reject .step files
    with pytest.raises(ValueError, match="KiCad Project Manager requires a project file"):
        launch_tool("kicad", step_file)

    # 4. LTspice must reject .step files
    with pytest.raises(ValueError, match="LTspice requires a SPICE schematic"):
        launch_tool("ltspice", step_file)

    # 5. FEMM must reject .step files
    with pytest.raises(ValueError, match="FEMM 4.2 requires a finite element magnetics model"):
        launch_tool("femm", step_file)

    # 6. OpenModelica must reject .step files
    with pytest.raises(ValueError, match="OpenModelica OMEdit requires a Modelica model"):
        launch_tool("omedit", step_file)


def test_open_native_rejects_unrecognized_file_types(tmp_path):
    weird_file = tmp_path / "unknown_artifact.xyz"
    weird_file.write_text("random bytes", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported or unrecognized engineering file type"):
        open_native(weird_file)


def test_design_studio_dialog_and_panel_ui(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)

    # Create dialog and apply Buck preset
    dlg = NewEngineeringDesignDialog(service, current_workspace_id="default")
    dlg._apply_buck_preset()
    assert dlg.txt_vin.text() == "24.0"
    assert dlg.txt_vout.text() == "5.0"
    assert dlg.txt_iout.text() == "4.0"

    reqs = dlg._validate_inputs()
    assert reqs is not None
    assert len(reqs) >= 5

    # Panel UI initialization
    panel = EngineeringDesignStudioPanel(service, lambda fn: fn())
    assert panel.tabs.count() == 4
    assert panel.btn_open_ltspice.text() == "📐 Open in LTspice"
    assert panel.btn_open_kicad_sch.text() == "🔌 Open Schematic in KiCad"
    assert panel.btn_open_kicad_pcb.text() == "🟩 Open PCB in KiCad"
    assert panel.btn_open_freecad.text() == "🧊 Open 3D CAD in FreeCAD"
