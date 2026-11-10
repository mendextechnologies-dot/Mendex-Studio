import json
import shutil

from mendex_core.models import Specification
from mendex_core.evidence import ManualCheck
from mendex_core.service import StudioService


def test_closed_database_and_evidence_backup_restore(tmp_path):
    original = StudioService(tmp_path / "original")
    product = original.create_product("RESTORE", "Software fixture", "pcb", "Test engineer")
    original.update_specification(product.active_revision_id, Specification(vout_v=12, source="Software fixture only"))
    file = tmp_path / "fixture.txt"
    file.write_text("Software fixture, not an actual engineering measurement")
    record = original.record_validation(product.active_revision_id, ManualCheck(check_id="REVIEW", reviewer="Test engineer", notes="Physical evidence unavailable", status="physical_verification_required"), file)
    report = original.generate_report(product.active_revision_id)
    # Service calls close their connections; copy metadata and evidence together.
    backup = tmp_path / "restored"
    shutil.copytree(original.root, backup)
    restored = StudioService(backup)
    assert restored.get_revision(product.active_revision_id).specification.vout_v == 12
    assert restored.validation_integrity(restored.list_validation(product.active_revision_id)[0])
    assert restored.list_validation(product.active_revision_id)[0] == record
    snapshot = json.loads((backup / report.report_path).with_name("snapshot.json").read_text())
    assert snapshot["validation"][0]["effective_status"] == "physical_verification_required"
    assert restored.diagnostics()["framework_ready"]
