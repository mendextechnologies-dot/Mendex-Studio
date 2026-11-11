"""Automated UI tests for ProductEngineeringOverviewPanel."""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox

from mendex_core.lifecycle.models import LifecycleStage, StageStatus
from mendex_core.models import Category
from mendex_core.service import StudioService
from mendex_ui.product_lifecycle_panel import ProductEngineeringOverviewPanel


def test_product_engineering_overview_panel_ui(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)

    product = service.create_product(
        code="UI-TEST",
        name="UI LifeCycle Test Unit",
        category=Category.DC_DC,
        owner="UI Test Lead",
    )

    panel = ProductEngineeringOverviewPanel(service)
    panel.set_product(product.product_id)

    # Verify Header
    assert "UI-TEST" in panel.lbl_title.text()
    assert "PROTOTYPE BLOCKED" in panel.badge_readiness.text()

    # Verify 12 cards created
    assert len(panel.cards) == 12

    # Verify Tab 0 is Review & Approvals
    assert panel.detail_tabs.tabText(0) == "✍️ Review & Approvals"
    assert panel.detail_tabs.tabText(1) == "🔬 Calculations"

    # Tab 0 is active initially
    panel.detail_tabs.setCurrentIndex(0)

    # Click Card #2 (Electrical Architecture & Sizing)
    panel._on_stage_card_clicked("electrical_architecture")
    assert panel.selected_stage_id == "electrical_architecture"
    assert "Electrical Architecture" in panel.lbl_stage_title.text()
    # Stays on Tab 0 so the user can easily review and sign off!
    assert panel.detail_tabs.currentIndex() == 0

    # Test combo box stage selection
    idx = panel.combo_stage_select.findData("bom_review")
    panel.combo_stage_select.setCurrentIndex(idx)
    assert panel.selected_stage_id == "bom_review"
    assert "BOM" in panel.lbl_stage_title.text()

    # Test filtering evidence
    panel.in_ev_search.setText("non_existent_search_query_12345")
    assert panel.ev_table.rowCount() == 0
    panel.in_ev_search.setText("")

    # Verify Gates tab populated
    assert panel.gates_table.rowCount() == 12

    # Test theme switching
    panel.apply_theme(False)  # Light theme
    panel.apply_theme(True)   # Dark theme


def test_calculation_tab_and_direct_signoff(tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)

    product = service.create_product(
        code="SV-1000",
        name="SpectraVolt SV-1000",
        category=Category.DC_DC,
        owner="sagar jamage",
    )

    rev = service.get_revision(product.active_revision_id)
    ws_path = service.workspace_path(rev)
    calc_dir = ws_path / "calculations"
    calc_dir.mkdir(parents=True, exist_ok=True)

    # Write realistic sizing data
    calc_payload = {
        "flyback_design": {
            "primary_turns": 5,
            "secondary_turns": 306,
            "primary_inductance_uh": 4.46,
            "air_gap_mm": 0.72,
            "core_ae_mm2": 102.0,
            "b_max_t": 0.22,
        },
        "steinmetz_core_loss": {
            "material": "TDK N87",
            "total_core_loss_w": 1.16,
        },
        "dowell_winding_loss": {
            "frequency_hz": 100000.0,
            "skin_depth_mm": 0.2365,
            "f_r": 3.78,
            "r_dc_ohm": 0.045,
            "r_ac_ohm": 0.170,
        },
        "semiconductor_losses": {
            "part_number": "Wolfspeed C2M0080120D",
            "p_conduction_w": 0.83,
            "p_switching_w": 4.80,
            "p_total_w": 5.63,
        }
    }
    (calc_dir / "sv1000_sizing_analysis.json").write_text(json.dumps(calc_payload), encoding="utf-8")

    panel = ProductEngineeringOverviewPanel(service)
    panel.set_product(product.product_id)

    # Check Calculations tab text content
    calc_text = panel.txt_calc_details.toPlainText()
    assert "Primary Turns (Np): 5 turns" in calc_text
    assert "Secondary Turns (Ns): 306 turns" in calc_text
    assert "Dowell AC Factor (Fr = Rac / Rdc): 3.7800" in calc_text
    assert "Wolfspeed C2M0080120D" in calc_text
    assert "Total MOSFET Dissipation: 5.630 W" in calc_text

    # Record sign-off directly from calculations tab
    panel.in_calc_reviewer.setText("sagar jamage")
    panel.combo_calc_decision.setCurrentIndex(0)  # PASS
    panel._record_calc_stage_approval()

    # Verify stage #2 is now PASSED
    assessment = service.lifecycle.assess(product.product_id, product.active_revision_id)
    assert assessment.stages["electrical_architecture"].status == StageStatus.PASSED
