"""Test verifying legacy help, guide, and handbook dialogs/buttons are removed from the UI."""
from __future__ import annotations

import os
from PySide6.QtWidgets import QApplication

from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow


def test_engineering_guide_dialog_removed():
    """Verify EngineeringGuideDialog file has been removed as per the new tool design."""
    dialog_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "src",
        "mendex_ui",
        "engineering_guide_dialog.py",
    )
    assert not os.path.exists(dialog_file), "engineering_guide_dialog.py should be removed"


def test_guide_buttons_in_window(tmp_path):
    """Verify help, guide, and prompts buttons are completely absent from window and panels."""
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    window = StudioWindow(service)
    window.show()
    app.processEvents()

    # Verify all legacy help and guide buttons are cleanly removed
    assert not hasattr(window, "btn_help_guide")
    assert not hasattr(window.product_lifecycle, "btn_design_guide")
    assert not hasattr(window.product_lifecycle, "btn_prompts")
    assert not hasattr(window.product_lifecycle, "_open_ai_prompts_dialog")

    window.close()
