"""Automated UI tests for ProductEngineeringOverviewPanel."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import QApplication

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

    # Click a card
    panel._on_stage_card_clicked("circuit_design")
    assert panel.selected_stage_id == "circuit_design"
    assert "Circuit Design" in panel.lbl_stage_title.text()

    # Test filtering evidence
    panel.in_ev_search.setText("non_existent_search_query_12345")
    assert panel.ev_table.rowCount() == 0
    panel.in_ev_search.setText("")

    # Verify Gates tab populated
    assert panel.gates_table.rowCount() == 12
