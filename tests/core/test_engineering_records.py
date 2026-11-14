"""Phase 2 records use disposable software data, not engineering qualification."""
import json
import sqlite3
import zipfile
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mendex_core.controller import MendexEngineeringController
from mendex_core.engineering_lifecycle.storage import file_hash
from mendex_core.engineering_records import storage
from mendex_core.evidence import specification_hash
from mendex_core.integration_contracts import JobRequest
from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def context(tmp_path):
    studio = StudioService(tmp_path)
    product = studio.create_product("RECORDS", "Generic software fixture", "pcb", "Fixture engineer")
    definition = {"id": "records_fixture", "version": "1.0.0", "name": "Software process only", "stages": [
        {"id": "work", "name": "Recorded work", "purpose": "Exercise record APIs", "review_required": False,
         "criteria": [{"id": "context", "description": "Process identity only", "kind": "project_context"}]}]}
    studio.engineering_lifecycle.register_definition(definition, "Software fixture")
    rid = str(product.active_revision_id)
    studio.engineering_lifecycle.enroll({"revision_id": rid, "definition_id": "records_fixture", "version": "1.0.0",
                                         "source": "Fixture", "reason": "Explicit enrollment", "idempotency_key": "enroll"})
    studio.engineering_lifecycle.apply({"revision_id": rid, "stage_id": "work", "action": "start", "source": "Fixture",
                                        "reason": "Begin software fixture", "idempotency_key": "start"})
    return studio, rid


def request(context, **changes):
    studio, rid = context
    return {"revision_id": rid, "stage_id": "work", "expected_input_hash": specification_hash(studio.get_revision(rid).specification),
            "source": "Software fixture", "reason": "Traceable test, not engineering approval", "idempotency_key": str(uuid4()), **changes}


def metadata(studio, rid, **changes):
    product = studio.get_product(studio.get_revision(rid).product_id)
    return {"project_id": str(product.product_id), "expected_updated_at": product.updated_at.isoformat(), "name": "Updated fixture",
            "owner": "Other fixture engineer", "description": "Metadata test", "source": "Fixture", "reason": "Recorded metadata change",
            "idempotency_key": str(uuid4()), **changes}


PARAMETERS = {
    "dowell": {"frequency_hz": 100000, "layers": 2, "conductor_diameter_mm": 0.4, "layer_porosity_factor": 0.85, "r_dc_ohm": 0.05, "temperature_c": 100},
    "losses": {"part_number": "SOFTWARE-FIXTURE", "r_ds_on_ohm": 0.02, "i_rms_a": 2, "duty_cycle": 0.4, "e_on_j": 1e-6, "e_off_j": 2e-6, "frequency_hz": 100000},
    "steinmetz": {"material": "UNQUALIFIED SOFTWARE FIXTURE", "k": 1, "alpha": 1.3, "beta": 2.5, "frequency_hz": 100000, "b_peak_t": 0.1, "core_volume_m3": 1e-5},
    "flyback": {"vin_min_v": 18, "vin_nom_v": 24, "vout_v": 12, "iout_a": 1, "frequency_hz": 100000, "d_max": 0.4, "efficiency": 0.85, "b_max_t": 0.2, "core_ae_mm2": 125, "v_diode_drop_v": 0.5},
    "semiconductor_thermal": {"part_number": "FIXTURE-MOSFET", "p_loss_w": 2.5, "t_ambient_c": 25.0, "t_j_max_c": 150.0, "derating_factor": 0.80, "r_th_jc_c_w": 1.5, "r_th_cs_c_w": 0.5, "r_th_sa_c_w": 5.0},
    "magnetic_thermal": {"component_name": "T1-FIXTURE", "p_core_w": 0.5, "p_winding_w": 0.5, "surface_area_cm2": 45.0, "t_ambient_c": 25.0, "t_class_max_c": 130.0, "insulation_class": "Class B (130°C)"},
    "ipc2152_thermal": {"current_a": 5.0, "target_delta_t_c": 10.0, "copper_thickness_oz": 1.0, "is_internal": False, "layer_name": "F.Cu"},
}


def test_discovery_does_not_install_records_schema(tmp_path):
    studio = StudioService(tmp_path)
    capabilities = studio.engineering_records.calculation_capabilities()
    assert {c["calculation"] for c in capabilities} == set(PARAMETERS)
    assert all(c["input_schema"]["additionalProperties"] is False for c in capabilities)
    with studio.connection() as db:
        assert not storage.installed(db)


def test_metadata_concurrency_and_idempotency(context):
    studio, rid = context
    req = metadata(studio, rid)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: studio.engineering_records.update_project(req), range(2)))
    assert results[0] == results[1]
    assert studio.get_product(req["project_id"]).name == "Updated fixture"
    with pytest.raises(StudioError, match="Idempotency"):
        studio.engineering_records.update_project({**req, "name": "Changed request"})
    with pytest.raises(StudioError, match="metadata changed"):
        studio.engineering_records.update_project({**req, "idempotency_key": "different"})


def test_structured_requirements_history_and_coverage(context):
    studio, rid = context
    service = studio.engineering_records
    assert service.missing_requirements(rid)["record_id"] is None
    req = request(context, requirements=[{"id": "input_range", "discipline": "electrical", "description": "Sourced input requirement",
                                         "source": "Software fixture", "specification_field": "vin_nom_v"}])
    first = service.save_requirements(req)
    assert service.save_requirements(req) == first
    coverage = service.missing_requirements(rid)
    assert any("acceptance criterion missing" in item for item in coverage["missing"])
    assert any("specification field missing" in item for item in coverage["missing"])
    req["requirements"][0]["acceptance_criterion"] = "Engineer must supply explicit acceptance bounds"
    second = service.save_requirements({**req, "idempotency_key": "requirements-v2"})
    assert second["requirements_version"] == 2 and second["supersedes_record_id"] == first["record_id"]
    studio.update_specification(rid, Specification(source="Updated fixture", vin_nom_v=24))
    assert any("older specification" in item for item in service.missing_requirements(rid)["missing"])
    assert service.get_record(first["record_id"])["stale"]
    assert len(service.list_records("requirements", {"revision_id": rid})["records"]) == 2


@pytest.mark.parametrize("calculation", list(PARAMETERS))
def test_calculation_matches_existing_core_and_preserves_provenance(context, calculation):
    studio, rid = context
    controller = MendexEngineeringController(service=studio)
    assert controller.service is studio and controller.design_service is studio.design
    expected = controller.run_calculation(calculation, PARAMETERS[calculation])
    req = request(context, calculation=calculation, parameters=PARAMETERS[calculation], assumptions=["Software regression fixture; no engineering validity asserted"])
    record = studio.engineering_records.run_calculation(req)
    assert record["result"] == expected and record["status"] == "SUCCEEDED"
    assert record["engineering_status"] == "NOT_EVALUATED"
    assert len(record["implementation_sha256"]) == 64 and record["warnings"]
    assert studio.engineering_records.run_calculation(req) == record
    assert studio.engineering_records.get_record(record["record_id"])["result"] == expected
    assert len(studio.engineering_records.list_records("calculation", {"revision_id": rid})["records"]) == 1


@pytest.mark.parametrize("change", [{"layers": 1.5}, {"layers": True}, {"layer_porosity_factor": 0.01}, {"frequency_hz": float("nan")}, {"unknown": 2}])
def test_no_silent_coercion_clamping_or_nonfinite_inputs(context, change):
    studio, _ = context
    with pytest.raises(ValidationError):
        studio.engineering_records.run_calculation(request(context, calculation="dowell", parameters={**PARAMETERS["dowell"], **change}, assumptions=["Fixture only"]))


def test_numerical_execution_failure_is_recorded_as_failed(context):
    studio, _ = context
    record = studio.engineering_records.run_calculation(request(context, calculation="dowell", parameters={**PARAMETERS["dowell"], "conductor_diameter_mm": 1e300}, assumptions=["Out-of-range software stress fixture"]))
    assert record["status"] == "FAILED" and record["result"] is None and record["error"]


def test_artifact_snapshot_integrity_and_paths(context):
    studio, rid = context
    revision = studio.get_revision(rid)
    original = studio.workspace_path(revision) / "requirements" / "fixture.txt"
    original.write_text("Original disposable software artifact", encoding="utf-8")
    req = request(context, relative_path="requirements/fixture.txt", expected_sha256=file_hash(original), classification="documentation")
    record = studio.engineering_records.register_artifact(req)
    stored = studio.root / record["snapshot_path"]
    assert stored.read_bytes() == original.read_bytes()
    assert studio.engineering_records.get_record(record["record_id"])["original_integrity"]
    original.write_text("Changed disposable working file")
    assert studio.engineering_records.register_artifact(req) == record  # Receipt is frozen; read checks current integrity.
    current = studio.engineering_records.get_record(record["record_id"])
    assert current["snapshot_integrity"] and not current["original_integrity"]
    assert current["effective_status"] == "NOT_EVALUATED"
    stored.unlink()
    assert not studio.engineering_records.get_record(record["record_id"])["snapshot_integrity"]
    with pytest.raises((ValueError, ValidationError)):
        studio.engineering_records.register_artifact({**req, "relative_path": "../escape.txt", "idempotency_key": "escape"})


def test_stage_and_specification_guards(context):
    studio, rid = context
    req = request(context, calculation="losses", parameters=PARAMETERS["losses"], assumptions=["Fixture only"])
    studio.update_specification(rid, Specification(source="Changed fixture"))
    with pytest.raises(StudioError, match="Specification changed"):
        studio.engineering_records.run_calculation(req)
    with pytest.raises(StudioError, match="current stage"):
        studio.engineering_records.run_calculation({**req, "expected_input_hash": specification_hash(studio.get_revision(rid).specification)})


def validation_request(context):
    studio, rid = context
    source = studio.root / "software-evidence.txt"
    source.write_text("Synthetic software fixture; not physical evidence")
    return request(context, evidence_path=str(source), expected_evidence_sha256=file_hash(source),
                   check={"check_id": "software_fixture", "status": "pass", "reviewer": "Unauthenticated fixture identity",
                          "notes": "Numerical software rule only", "evidence_kind": "CALCULATED", "measured_value": 1,
                          "minimum": 0, "maximum": 2, "unit": "V"})


def test_validation_uses_existing_core_integrity(context):
    studio, rid = context
    req = validation_request(context)
    entry = studio.engineering_records.record_validation(req)
    assert studio.engineering_records.record_validation(req) == entry
    assert len(studio.list_validation(rid)) == 1
    result = studio.engineering_records.validation_results(rid)["results"][0]
    assert result["effective_status"] == "pass"
    assert entry["validation_record"]["record_id"] == result["record"]["record_id"]
    (studio.root / result["record"]["evidence_uri"]).write_text("Changed disposable evidence")
    assert studio.engineering_records.validation_results(rid)["results"][0]["effective_status"] == "not_evaluated"


def test_receipt_failure_rolls_back_core_write_and_cleans_only_new_evidence(context):
    studio, rid = context
    studio.engineering_records.update_project(metadata(studio, rid))
    before = studio.get_product(studio.get_revision(rid).product_id)
    with sqlite3.connect(studio.database) as db:
        db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON engineering_records_receipts BEGIN SELECT RAISE(ABORT,'Injected receipt failure'); END")
    with pytest.raises(StudioError):
        studio.engineering_records.update_project(metadata(studio, rid, name="Must roll back"))
    assert studio.get_product(before.product_id) == before
    req = validation_request(context)
    source_bytes = (studio.root / "software-evidence.txt").read_bytes()
    with pytest.raises(StudioError):
        studio.engineering_records.record_validation(req)
    assert studio.list_validation(rid) == []
    assert (studio.root / "software-evidence.txt").read_bytes() == source_bytes
    assert not list((studio.workspace_path(studio.get_revision(rid)) / "validation").iterdir())


def test_report_generation_export_tamper_and_no_missing_input_fabrication(context):
    studio, rid = context
    service = studio.engineering_records
    req = request(context)
    entry = service.generate_report(req)
    assert service.generate_report(req) == entry
    report_id = entry["report"]["report_id"]
    metadata_result = service.report_metadata(report_id)
    assert metadata_result["integrity"] == "INTACT"
    html = (studio.root / entry["report"]["report_path"]).read_text(encoding="utf-8")
    assert "NOT_EVALUATED" in html
    assert "3000 V RMS / 5.0 mm clearance" not in html
    assert "1000 V" not in html and "24.0 V" not in html and "100 kHz" not in html
    assert "Authorized for Fabrication" not in html
    export_request = {"report_id": report_id, "source": "Fixture", "reason": "Review original report", "idempotency_key": "export-once"}
    exported = service.export_report(export_request)
    assert service.export_report(export_request) == exported
    archive_path = studio.root / exported["path"]
    assert file_hash(archive_path) == exported["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {"report.html", "snapshot.json", "manifest.json"}
        assert archive.read("report.html") == (studio.root / entry["report"]["report_path"]).read_bytes()
    (studio.root / entry["report"]["report_path"]).write_text("Tampered disposable report")
    assert service.report_metadata(report_id)["integrity"] == "FAILED"
    with pytest.raises(StudioError, match="missing or modified"):
        service.export_report({**export_request, "idempotency_key": "export-new"})


def test_live_job_not_recovered_by_observer_and_foreign_cancellation_rejected(tmp_path):
    owner = StudioService(tmp_path)
    engine = owner.integrations
    workspace = engine.create_workspace("Disposable synthetic job")
    job = engine.submit(JobRequest(workspace_id=workspace["workspace_id"], tool_id="studio-demo", operation="synthetic-echo",
                                   parameters={"steps": 1000, "delay_s": 0.01}, provenance="SYNTHETIC SOFTWARE TEST ONLY"))
    try:
        observer = StudioService(tmp_path)
        assert observer.integrations.job(job.request.job_id).status.value in ("QUEUED", "RUNNING")
        assert not observer.engineering_records.job_detail(job.request.job_id)["cancellation_supported"]
        cancel = {"job_id": str(job.request.job_id), "source": "Fixture", "reason": "Cancellation test", "idempotency_key": "cancel-once"}
        with pytest.raises(StudioError, match="does not own"):
            observer.engineering_records.cancel_job(cancel)
        assert owner.engineering_records.job_detail(job.request.job_id)["cancellation_supported"]
        receipt = owner.engineering_records.cancel_job(cancel)
        assert owner.engineering_records.cancel_job(cancel) == receipt
        completed = engine.wait(job.request.job_id)
        assert completed.status.value == "CANCELLED"
        assert owner.engineering_records.job_results(job.request.job_id)["result"]["status"] == "CANCELLED"
        assert "CANCELLED" in owner.engineering_records.job_logs(job.request.job_id)["text"]
    finally:
        engine.shutdown()


def test_record_migration_rollback_preserves_lifecycle_and_backup(context, monkeypatch):
    studio, rid = context
    original_connection = studio.connection
    before = studio.engineering_lifecycle.history(rid)

    class Fault:
        def __init__(self, db):
            self.db = db

        def execute(self, sql, *args):
            if sql.startswith("CREATE TABLE engineering_records_entries"):
                raise RuntimeError("Injected records migration failure")
            return self.db.execute(sql, *args)

    @contextmanager
    def failing_connection():
        with original_connection() as db:
            yield Fault(db)

    monkeypatch.setattr(studio, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="records migration"):
        studio.engineering_records.update_project(metadata(studio, rid))
    with original_connection() as db:
        assert not storage.installed(db)
    assert studio.engineering_lifecycle.history(rid) == before
    assert list((studio.root / ".mendex" / "backups").glob("*/manifest.json"))


def test_immutable_record_tables_and_future_component_rejection(context):
    studio, rid = context
    studio.engineering_records.save_requirements(request(context, requirements=[
        {"id": "fixture", "description": "Context only", "discipline": "standards", "source": "Fixture"}]))
    for table in (*storage.TABLES, "engineering_records_schema"):
        with sqlite3.connect(studio.database) as db, pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(f"DELETE FROM {table}")
    with sqlite3.connect(studio.database) as db:
        db.execute("DROP TABLE engineering_records_schema")
        db.execute("CREATE TABLE engineering_records_schema(version INTEGER)")
        db.execute("INSERT INTO engineering_records_schema VALUES(999)")
    with pytest.raises(StudioError, match="Unsupported"):
        studio.engineering_records.list_records("requirements", {"revision_id": rid})


def test_legacy_report_export_is_explicitly_unverified(context):
    studio, rid = context
    report = studio.generate_report(rid)
    metadata_result = studio.engineering_records.report_metadata(report.report_id)
    assert metadata_result["available"] and metadata_result["integrity"] == "UNVERIFIED_LEGACY"
    result = studio.engineering_records.export_report({"report_id": str(report.report_id), "source": "Fixture",
                                                      "reason": "Preserve legacy report", "idempotency_key": "legacy-export"})
    assert result["integrity"] == "UNVERIFIED_LEGACY"


def test_record_context_rejects_archived_revision(context):
    studio, rid = context
    req = request(context, calculation="losses", parameters=PARAMETERS["losses"], assumptions=["Fixture only"])
    studio.create_revision(studio.get_revision(rid).product_id, "R002")
    with pytest.raises(StudioError, match="draft revision"):
        studio.engineering_records.run_calculation(req)
