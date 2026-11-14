"""Safety presentation must not manufacture measurements or qualification."""
import os
import json
import pytest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from mendex_core.service import StudioService
from mendex_ui.product_lifecycle_panel import ProductEngineeringOverviewPanel

_KEEP_ALIVE = []


@pytest.mark.parametrize('report', [{}, {'violations': [], 'unconnected_items': []}])
def test_drc_file_cannot_grant_insulation_compliance(tmp_path, report):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    product = service.create_product('DRC', 'Separate software check', 'pcb', 'Fixture engineer')
    revision = service.get_revision(product.active_revision_id)
    workspace = service.workspace_path(revision)
    (workspace / 'pcb/fixture.kicad_pcb').write_text('(kicad_pcb)', encoding='utf-8')
    (workspace / 'pcb/fixture_drc.json').write_text(json.dumps(report), encoding='utf-8')
    panel = ProductEngineeringOverviewPanel(service)
    _KEEP_ALIVE.extend([app, panel])
    panel.set_product(product.product_id, product.active_revision_id)
    assert 'NOT_EVALUATED' in panel.lbl_s3.text()
    assert 'NOT_EVALUATED' in panel.lbl_s4.text()
    assert 'COMPLIANT' not in panel.lbl_s4.text()
    if not report:
        assert 'PASSED' not in panel.lbl_drc_badge.text()

def test_safety_ui_without_context_is_not_evaluated(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    product = service.create_product('UNQUALIFIED', 'No insulation intake', 'pcb', 'Fixture engineer')
    panel = ProductEngineeringOverviewPanel(service)
    _KEEP_ALIVE.extend([app, panel])
    panel.set_product(product.product_id, product.active_revision_id)
    panel._audit_iec_safety(quiet=True)
    assert 'NOT_EVALUATED' in panel.lbl_s3.text()
    assert 'NOT_EVALUATED' in panel.lbl_s4.text()
    assert '5.0 mm' not in panel.lbl_s3.text()
    assert 'COMPLIANT' not in panel.lbl_s4.text()


def test_bom_rows_do_not_receive_guessed_stresses_or_passes(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    product = service.create_product('BOM', 'Unknown stresses', 'pcb', 'Fixture engineer')
    revision = service.get_revision(product.active_revision_id)
    source = service.workspace_path(revision) / 'bom.csv'
    source.write_text('designator,part_number,description,qty\nQ1,Unknown,No supplied stress,1\n', encoding='utf-8')
    panel = ProductEngineeringOverviewPanel(service)
    _KEEP_ALIVE.extend([app, panel])
    panel.set_product(product.product_id, product.active_revision_id)
    panel._audit_bom_derating(quiet=True)
    assert panel.bom_table.rowCount() == 1
    assert panel.bom_table.item(0, 7).text() == 'Unknown'
    assert panel.bom_table.item(0, 8).text() == 'NOT_EVALUATED'
    assert 'NOT_EVALUATED' in panel.lbl_bom_summary.text()


def test_explicit_bom_comparison_never_overrides_exceeded_limit(tmp_path):
    app = QApplication.instance() or QApplication([])
    service = StudioService(tmp_path)
    product = service.create_product('LIMIT', 'Supplied comparison only', 'pcb', 'Fixture engineer')
    source = service.workspace_path(service.get_revision(product.active_revision_id)) / 'bom.csv'
    source.write_text('designator,operating_value,rated_value,unit,max_allowed_ratio,limit_source\nR1,8,10,W,0.6,Software fixture criterion\nR2,1,2,W,,\n', encoding='utf-8')
    panel = ProductEngineeringOverviewPanel(service)
    _KEEP_ALIVE.extend([app, panel])
    panel.set_product(product.product_id, product.active_revision_id)
    panel._audit_bom_derating(quiet=True)
    assert panel.bom_table.item(0, 8).text() == 'EXCEEDS_SUPPLIED_LIMIT'
    assert panel.bom_table.item(1, 8).text() == 'NOT_EVALUATED'
    assert 'NOT_EVALUATED' in panel.lbl_bom_summary.text()
