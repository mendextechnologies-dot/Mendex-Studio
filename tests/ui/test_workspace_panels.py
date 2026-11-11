import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from mendex_core.models import Specification
from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow
from mendex_ui.workspace_panels import (
    TransformerWorkspacePanel,
    SemiconductorWorkspacePanel,
    DCDCWorkspacePanel,
)


def test_transformer_workspace_panel(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    header = QLabel("Transformer Header")
    panel = TransformerWorkspacePanel(service, lambda fn: fn(), header)
    panel._suppress_dialogs = True

    # 1. Default calculation
    design, dowell = panel.calculate()
    assert design.primary_turns > 0
    assert design.secondary_turns > 0
    assert dowell.skin_depth_mm > 0
    assert "TRANSFORMER ANALYTICAL SIZING" in panel.results_box.toPlainText()
    assert "DOWELL HIGH-FREQUENCY WINDING LOSS" in panel.results_box.toPlainText()

    # 2. Export FEMM script
    femm_path = tmp_path / "test_trans.lua"
    femm_script = panel.export_femm_script(target_path=femm_path)
    assert femm_path.exists()
    assert "newdocument(0)" in femm_script

    # 3. Export FreeCAD script
    fc_path = tmp_path / "test_bobbin.py"
    fc_script = panel.export_freecad_script(target_path=fc_path)
    assert fc_path.exists()
    assert "Part.makeCylinder" in fc_script

    # 3b. Generate FreeCAD 3D STEP
    step_target = tmp_path / "panel_bobbin.step"
    generated_step = panel.generate_freecad_step(target_path=step_target)
    if generated_step:
        assert step_target.exists()
        assert step_target.stat().st_size > 0

    # 4. set_revision test
    product = service.create_product("TX-001", "Transformer Test", "transformer", "Engineer")
    revision = service.get_revision(product.active_revision_id)
    service.save_product_revision(
        product.product_id,
        revision.revision_id,
        product.name,
        product.owner,
        product.description,
        Specification(vin_min_v=36.0, vin_nom_v=48.0, vout_v=400.0, iout_a=0.5, switching_frequency_hz=150000.0),
    )
    updated_rev = service.get_revision(revision.revision_id)
    panel.set_revision(updated_rev)
    assert panel.vin_min.text() == "36.0"
    assert panel.vout.text() == "400.0"
    assert panel.iout.text() == "0.5"
    assert panel.freq_khz.text() == "150.0"


def test_semiconductor_workspace_panel(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    header = QLabel("Semiconductor Header")
    panel = SemiconductorWorkspacePanel(service, lambda fn: fn(), header)
    panel._suppress_dialogs = True

    # 1. Device picker selection
    if panel.device_picker.count() > 0:
        panel.device_picker.setCurrentIndex(0)
        assert panel.part_number.text() != ""

    # 2. Calculate loss
    loss = panel.calculate()
    assert loss.p_conduction_w > 0
    assert loss.p_switching_w > 0
    assert loss.p_total_w == loss.p_conduction_w + loss.p_switching_w
    assert "Conduction Loss (P_cond):" in panel.loss_results.toPlainText()

    # 3. set_revision test
    product = service.create_product("SEMI-001", "Device Test", "power_semiconductor", "Engineer")
    revision = service.get_revision(product.active_revision_id)
    service.save_product_revision(
        product.product_id,
        revision.revision_id,
        product.name,
        product.owner,
        product.description,
        Specification(vin_nom_v=24.0, iout_a=15.0, switching_frequency_hz=80000.0),
    )
    updated_rev = service.get_revision(revision.revision_id)
    panel.set_revision(updated_rev)
    assert panel.i_rms.text() == "15.0"
    assert panel.f_sw_khz.text() == "80.0"


def test_dcdc_workspace_panel(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    header = QLabel("DCDC Header")
    panel = DCDCWorkspacePanel(service, lambda fn: fn(), header)
    panel._suppress_dialogs = True

    # 1. Export Modelica script
    mos_path = tmp_path / "test_flyback.mos"
    mos_script = panel.export_script(target_path=mos_path)
    assert mos_path.exists()
    assert "simulate(FlybackConverter" in mos_script

    # 2. set_revision test
    product = service.create_product("DC-001", "DCDC Test", "dc_dc_converter", "Engineer")
    revision = service.get_revision(product.active_revision_id)
    service.save_product_revision(
        product.product_id,
        revision.revision_id,
        product.name,
        product.owner,
        product.description,
        Specification(vin_nom_v=48.0, vout_v=24.0, iout_a=2.0, switching_frequency_hz=120000.0),
    )
    updated_rev = service.get_revision(revision.revision_id)
    panel.set_revision(updated_rev)
    assert panel.vin.text() == "48.0"
    assert panel.vout.text() == "24.0"
    assert panel.fsw.text() == "120.0"
    assert panel.rload.text() == "12.0"


def test_window_integration_with_workspace_panels(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    prod = service.create_product("PSU-200", "High Voltage PSU", "transformer", "Lead Dev")
    rev = service.get_revision(prod.active_revision_id)
    service.save_product_revision(
        prod.product_id,
        rev.revision_id,
        prod.name,
        prod.owner,
        prod.description,
        Specification(vin_min_v=18.0, vin_nom_v=24.0, vout_v=1000.0, iout_a=0.1, switching_frequency_hz=100000.0),
    )

    window = StudioWindow(service)
    window.show()
    app.processEvents()

    assert window.pages.count() == 7
    assert not hasattr(window, "design_studio")
    assert not hasattr(window, "workflow_studio")
    assert hasattr(window, "transformer_ws")
    assert hasattr(window, "dcdc_ws")
    assert hasattr(window, "semiconductor_ws")

    # Verify parameters were populated into panels from the specification
    assert window.transformer_ws.vin_min.text() == "18.0"
    assert window.transformer_ws.vout.text() == "1000.0"
    assert window.transformer_ws.iout.text() == "0.1"
    assert window.dcdc_ws.vin.text() == "24.0"
    assert window.semiconductor_ws.i_rms.text() == "0.1"

    window.close()
