import json
import sqlite3

import pytest
from pydantic import ValidationError

from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService
from mendex_core.evidence import ManualCheck


def product(service):
    return service.create_product("DEMO", "Illustrative software fixture", "transformer", "Test engineer")


def test_rules_and_persisted_unavailable_simulation(tmp_path):
    service = StudioService(tmp_path)
    demo = product(service)
    rules = service.list_rules(demo.active_revision_id)
    assert any(rule.missing_fields for rule in rules)
    assert all(rule.status in ("not_evaluated", "physical_verification_required") for rule in rules)
    # The built-in AI advisor was retired: Core exposes no AI provider surface
    assert not hasattr(service, "ai_advice") and not hasattr(service, "ai_copilot")
    run = service.request_simulation(demo.active_revision_id, "ltspice")
    restarted = StudioService(tmp_path)
    assert restarted.list_runs(demo.active_revision_id) == [run]
    assert run.status == "not_supported" and run.started_at is None
    assert run.artifacts == [] and run.log_path is None
    report = service.generate_report(demo.active_revision_id)
    snapshot = json.loads((tmp_path / report.report_path).with_name("snapshot.json").read_text())
    assert snapshot["simulation_requests"][0]["status"] == "not_supported"
    assert snapshot["engineering_rules"]


def test_data_plugin_discovery_and_atomic_rejection(tmp_path):
    folder = tmp_path / ".mendex" / "plugins"
    folder.mkdir(parents=True)
    manifest = {"plugin_id": "fixture-plugin", "version": "0.1.0", "adapters": [{"tool_id": "fixture-tool", "display_name": "Not installed fixture", "official_url": "https://example.org/"}], "rules": []}
    (folder / "a-fixture.json").write_text(json.dumps(manifest))
    conflict = {**manifest, "plugin_id": "bad-plugin", "adapters": [manifest["adapters"][0], {"tool_id": "partial-tool", "display_name": "Must never register", "official_url": "https://example.org/"}]}
    (folder / "b-conflict.json").write_text(json.dumps(conflict))
    (folder / "c-code.json").write_text(json.dumps({**manifest, "python_module": "not.allowed"}))
    duplicate = {**manifest, "adapters": [{**manifest["adapters"][0], "tool_id": "duplicate-plugin-tool"}]}
    (folder / "d-duplicate.json").write_text(json.dumps(duplicate))
    service = StudioService(tmp_path)
    assert [status["status"] for status in service.list_plugins()] == ["loaded", "rejected", "rejected", "rejected"]
    assert service.check_tool("fixture-tool").state == "NOT_INSTALLED"
    assert "partial-tool" not in [a.tool_id for a in service.registry.list()]
    assert "duplicate-plugin-tool" not in [a.tool_id for a in service.registry.list()]


def test_atomic_edit_lifecycle_label_and_snapshot(tmp_path):
    service = StudioService(tmp_path)
    demo = product(service)
    with pytest.raises(ValidationError):
        service.save_product_revision(demo.product_id, demo.active_revision_id, "Name", "", "", Specification(vin_nom_v=24))
    assert service.get_revision(demo.active_revision_id).specification.vin_nom_v is None
    renamed = service.rename_revision(demo.active_revision_id, "DRAFT-02")
    assert renamed.revision_label == "DRAFT-02"
    path = service.export_specification(renamed.revision_id)
    assert json.loads(path.read_text())["revision"]["revision_label"] == "DRAFT-02"
    service.set_revision_status(renamed.revision_id, "in_review")
    with pytest.raises(StudioError):
        service.update_specification(renamed.revision_id, Specification(vin_nom_v=24))
    with pytest.raises(StudioError):
        service.set_revision_status(renamed.revision_id, "approved")
    service.set_revision_status(renamed.revision_id, "draft")
    service.create_revision(demo.product_id, "R003")
    with pytest.raises(StudioError):
        service.set_revision_status(renamed.revision_id, "draft")


def test_v2_migration_preserves_evidence_and_rejects_empty_pass(tmp_path):
    service = StudioService(tmp_path)
    demo = product(service)
    record = service.record_validation(demo.active_revision_id, ManualCheck(check_id="MISSING", reviewer="Test", notes="No evidence available"))
    with sqlite3.connect(service.database) as db:
        db.execute("DROP TABLE runs")
        db.execute("PRAGMA user_version=2")
    restarted = StudioService(tmp_path)
    assert restarted.list_validation(demo.active_revision_id) == [record]
    source = tmp_path / "empty.txt"
    source.touch()
    passed = ManualCheck(check_id="EMPTY", reviewer="Test", notes="Fixture", status="pass", measured_value=1, unit="V", maximum=2)
    with pytest.raises(StudioError, match="nonempty"):
        restarted.record_validation(demo.active_revision_id, passed, source)
    assert len(restarted.list_validation(demo.active_revision_id)) == 1


def test_adapter_contract_never_produces_metrics(tmp_path):
    service = StudioService(tmp_path)
    adapter = service.registry.get("ltspice")
    assert not adapter.capabilities().execution_enabled
    assert adapter.self_test().status == "not_evaluated"
    assert adapter.validate(Specification()).status == "not_evaluated"
    with pytest.raises(NotImplementedError):
        adapter.prepare(Specification(), tmp_path)
    assert adapter.parse(None).metrics == {}


def test_invalid_model_instance_and_evidence_manifest_name(tmp_path):
    service = StudioService(tmp_path)
    demo = product(service)
    invalid = Specification.model_construct(vin_nom_v=-24)
    with pytest.raises(ValidationError):
        service.update_specification(demo.active_revision_id, invalid)
    source = tmp_path / "manifest.json"
    source.write_text('{"fixture":"software evidence only"}')
    record = service.record_validation(demo.active_revision_id, ManualCheck(check_id="MANIFEST", reviewer="Test", notes="Unevaluated fixture"), source)
    assert service.validation_integrity(record)
    assert (tmp_path / record.evidence_uri).parent.name == "raw"
