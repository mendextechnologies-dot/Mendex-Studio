import json
from zipfile import ZipFile

import pytest

from mendex_core import bom_generator
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def context(tmp_path, monkeypatch):
    studio = StudioService(tmp_path)
    product = studio.create_product('OTHER', 'Independent project', 'pcb', 'Fixture engineer')
    revision = studio.get_revision(product.active_revision_id)
    source = studio.workspace_path(revision) / 'bom/bom.json'
    monkeypatch.setattr(bom_generator, 'convert_docx_to_pdf_via_word_com', lambda *args: False)
    return studio, product, revision, source


@pytest.mark.parametrize('content', [None, 'not JSON', '[]', '[{"description":"incomplete"}]'])
def test_missing_or_malformed_bom_never_inserts_example_parts(context, content):
    studio, _, revision, source = context
    if content is not None:
        source.parent.mkdir()
        source.write_text(content)
    with pytest.raises(StudioError) as exc:
        bom_generator.generate_bom_deliverables(studio, revision.revision_id)
    assert exc.value.code == 'INVALID_INPUT'
    assert not (source.parent / 'exports').exists()
    assert source.read_text() == content if content is not None else not source.exists()


def test_exports_use_supplied_rows_and_preserve_every_previous_byte(context):
    pytest.importorskip('docx')
    studio, _, revision, source = context
    source.parent.mkdir()
    data = json.dumps([{'designator': 'R_EXPLICIT', 'quantity': 2,
                       'description': 'Supplied fixture resistor; not engineering evidence',
                       'mpn': 'FIXTURE-ONLY', 'source': 'Software test'}]).encode()
    source.write_bytes(data)
    a = bom_generator.generate_bom_deliverables(studio, revision.revision_id)
    root = studio.workspace_path(revision)
    originals = {p: (root / a[p]).read_bytes() for p in ('json_path', 'csv_path', 'docx_path')}
    b = bom_generator.generate_bom_deliverables(studio, revision.revision_id)
    assert a['docx_path'] != b['docx_path']
    assert source.read_bytes() == data
    assert all((root / a[p]).read_bytes() == value for p, value in originals.items())
    assert a['engineering_status'] == 'NOT_EVALUATED'
    assert a['pdf_path'] is None and a['pdf_available'] is False
    with ZipFile(root / a['docx_path']) as archive:
        xml = archive.read('word/document.xml').decode()
    assert 'R_EXPLICIT' in xml and 'FIXTURE-ONLY' in xml
    assert 'NOT_EVALUATED' in xml and 'Unknown' in xml
    assert 'Verified &amp; Approved' not in xml and 'SV1000' not in xml


def test_archived_revision_cannot_receive_bom_exports(context):
    studio, product, revision, source = context
    studio.create_revision(product.product_id, 'R002')
    with pytest.raises(StudioError) as exc:
        bom_generator.generate_bom_deliverables(studio, revision.revision_id)
    assert exc.value.code == 'IMMUTABLE'
    assert not source.parent.exists()


def test_emc100_reference_design_bom_compilation():
    from pathlib import Path
    from mendex_core.desktop.service import DesktopService
    studio = StudioService(Path("."))
    product = studio.get_product("5b0852dd-7920-4451-b869-049f46254387")
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    bom_file = ws_dir / "bom" / "bom.json"
    assert bom_file.exists()
    items = json.loads(bom_file.read_bytes())
    assert len(items) == 30
    assert all(item["quantity"] > 0 for item in items)
    designators = {item["designator"] for item in items}
    assert "Q1" in designators
    assert "U3" in designators
    assert "U2A" in designators
    assert "C4" in designators
    assert "D4" in designators

    desktop = DesktopService(studio)
    res = desktop.dispatch("generate_bom", {"revision_id": str(rev.revision_id)})
    assert res["success"] is True
    assert res["items_count"] == 30
    assert res["engineering_status"] == "NOT_EVALUATED"
    assert (ws_dir / res["docx_path"]).exists()
    assert (ws_dir / res["csv_path"]).exists()
    assert (ws_dir / res["json_path"]).exists()
    if res["pdf_available"]:
        assert (ws_dir / res["pdf_path"]).exists()
