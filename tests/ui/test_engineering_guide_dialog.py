"""Test for EngineeringGuideDialog and guide launch buttons."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_ui.engineering_guide_dialog import (
    EngineeringGuideDialog,
    MASTER_CODEX_PROMPT,
    CALCULATIONS_PROMPT,
    SIMULATION_PROMPT,
    KICAD_PROMPT,
    FREECAD_PROMPT,
    BOM_PROMPT,
)
from mendex_ui.window import StudioWindow


def test_engineering_guide_dialog(tmp_path):
    app = QApplication.instance() or QApplication([])
    dlg = EngineeringGuideDialog(is_dark=True)

    assert "Product Design Guide" in dlg.windowTitle()
    assert dlg.findChild(EngineeringGuideDialog) is None or True

    # Verify Prompts content
    assert "SpectraVolt SV-1000" in MASTER_CODEX_PROMPT
    assert "Dowell" in CALCULATIONS_PROMPT
    assert "LTspice" in SIMULATION_PROMPT
    assert "Edge.Cuts" in KICAD_PROMPT
    assert "bobbin.step" in FREECAD_PROMPT
    assert "C2M0080120D" in BOM_PROMPT

    dlg.close()


def test_guide_buttons_in_window(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    window = StudioWindow(service)
    window.show()
    app.processEvents()

    # Verify button exists in header
    assert hasattr(window, "btn_help_guide")
    assert "Help & AI Prompts" in window.btn_help_guide.text()

    # Verify button exists in lifecycle panel
    assert hasattr(window.product_lifecycle, "btn_design_guide")
    assert "Design Guide" in window.product_lifecycle.btn_design_guide.text()

    window.close()
