import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from mendex_core.adapters.registry import AdapterRegistry, DiscoveryAdapter
from mendex_core.evidence import ManualCheck
from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def studio(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("PILOT-1", "Illustrative pilot", "transformer", "Test engineer")
    return service, product.active_revision_id


def test_missing_and_configured_tool(tmp_path):
    registry = AdapterRegistry()
    registry.register(DiscoveryAdapter("test", "Test tool", [], [], "https://example.org"))
    service = StudioService(tmp_path, registry)
    assert service.list_tools()[0].state == "NOT_INSTALLED"
    with pytest.raises(StudioError):
        service.configure_tool("test", "relative.exe")
    executable = tmp_path / "test.exe"
    executable.write_bytes(b"fixture: never executed")
    executable.chmod(0o755)
    status = service.configure_tool("test", str(executable))
    assert status.detected and status.state == "FOUND_UNVERIFIED"
    assert status.compatibility == "unknown" and status.installed_version is None
    assert service.check_tool("test").configured_path == str(executable.resolve())
    with pytest.raises(NotImplementedError):
        registry.get("test").run()
    executable.unlink()
    assert not service.check_tool("test").detected
    with pytest.raises(ValueError):
        registry.register(registry.get("test"))


def test_v1_migration_preserves_products(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("OLD-1", "Existing product", "pcb", "Engineer")
    with sqlite3.connect(service.database) as db:
        db.execute("DROP TABLE reports")
        db.execute("DROP TABLE validations")
        db.execute("DROP TABLE tool_settings")
        db.execute("PRAGMA user_version=1")
    migrated = StudioService(tmp_path)
    assert migrated.get_product(product.product_id) == product
    assert migrated.list_validation(product.active_revision_id) == []


def test_unevaluated_persists_and_empty_report(studio):
    service, revision_id = studio
    report = service.generate_report(revision_id)
    assert any("NOT_EVALUATED" in warning for warning in report.warnings)
    service.record_validation(revision_id, ManualCheck(check_id="REQ-001", reviewer="Test reviewer", notes="No evidence available"))
    restarted = StudioService(service.root)
    records = restarted.list_validation(revision_id)
    assert records[0].check.status == "not_evaluated"
    assert restarted.list_reports(revision_id) == [report]


def test_pass_requires_rule_and_actual_evidence(studio):
    service, revision_id = studio
    with pytest.raises(ValidationError):
        ManualCheck(check_id="X", status="pass", reviewer="Reviewer", notes="No criterion")
    with pytest.raises(ValidationError):
        ManualCheck(check_id="X", status="pass", reviewer="Reviewer", notes="Contradiction", measured_value=30, unit="V", maximum=20)
    check = ManualCheck(check_id="X", status="pass", reviewer="Reviewer", notes="Illustrative fixture only", measured_value=10, unit="V", maximum=20)
    with pytest.raises(StudioError, match="evidence"):
        service.record_validation(revision_id, check)
    source = service.root / "fixture.txt"
    source.write_text("Illustrative test fixture; not an engineering result")
    record = service.record_validation(revision_id, check, source)
    assert service.validation_integrity(record)
    source.write_text("Changed original")
    assert service.validation_integrity(record)  # Copy preserved independently.
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM validations")
    report = service.generate_report(revision_id)
    snapshot = json.loads((service.root / report.report_path).with_name("snapshot.json").read_text())
    assert snapshot["validation"][0]["effective_status"] == "pass"
    assert snapshot["validation"][0]["record"]["provenance"].startswith("Manually supplied")
    (service.root / record.evidence_uri).write_bytes(b"tampered")
    altered = service.generate_report(revision_id)
    assert any("integrity failure" in w for w in altered.warnings)
    assert "evidence missing or altered" in (service.root / altered.report_path).read_text(encoding="utf-8")
    assert altered.report_path != report.report_path


def test_stale_evidence_archived_baseline_and_no_fake_runs(studio):
    service, revision_id = studio
    service.record_validation(revision_id, ManualCheck(check_id="X", reviewer="Reviewer", notes="No evidence"))
    service.update_specification(revision_id, Specification(vin_nom_v=24))
    report = service.generate_report(revision_id)
    assert any("different specification" in warning for warning in report.warnings)
    assert service.list_runs(revision_id) == []
    product = service.get_revision(revision_id).product_id
    new = service.create_revision(product, "R002")
    assert service.list_validation(new.revision_id) == []
    with pytest.raises(StudioError, match="archived"):
        service.record_validation(revision_id, ManualCheck(check_id="X", reviewer="Reviewer", notes="No evidence"))


def test_deliberate_failure_and_stale_pass_are_never_presented_as_pass(studio):
    service, revision_id = studio
    source = service.root / "illustrative-fixture.txt"
    source.write_text("Test fixture only; contains no actual engineering result")
    failed = ManualCheck(check_id="DELIBERATE-FAIL", status="fail", reviewer="Test reviewer", notes="Intentional regression fixture", measured_value=30, unit="V", maximum=20)
    service.record_validation(revision_id, failed, source)
    passed = ManualCheck(check_id="STALE-CHECK", status="pass", reviewer="Test reviewer", notes="Numerical fixture only", measured_value=10, unit="V", maximum=20)
    service.record_validation(revision_id, passed, source)
    assert service.validation_summary(revision_id)[0]["effective_status"] == "fail"
    assert service.validation_summary(revision_id)[1]["effective_status"] == "pass"
    service.update_specification(revision_id, Specification(vout_v=48))
    assert all(row["effective_status"] == "not_evaluated" for row in service.validation_summary(revision_id))
    report = service.generate_report(revision_id)
    snapshot = json.loads((service.root / report.report_path).with_name("snapshot.json").read_text())
    assert all(row["effective_status"] == "not_evaluated" for row in snapshot["validation"])


def test_invalid_evidence_rolls_back_and_html_escapes(studio):
    service, revision_id = studio
    check = ManualCheck(check_id="<script>alert(1)</script>", reviewer="Reviewer", notes="<b>fixture</b>")
    with pytest.raises(StudioError):
        service.record_validation(revision_id, check, Path("relative.txt"))
    assert service.list_validation(revision_id) == []
    folder = service.workspace_path(service.get_revision(revision_id)) / "validation"
    assert not list(folder.iterdir())
    service.record_validation(revision_id, check)
    report = service.generate_report(revision_id)
    assert "<script>" not in (service.root / report.report_path).read_text(encoding="utf-8")
