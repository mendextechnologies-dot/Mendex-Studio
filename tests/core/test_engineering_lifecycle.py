"""Lifecycle acceptance tests use disposable software fixtures, never live evidence."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mendex_core.engineering_lifecycle.models import LifecycleDefinition, StageCommand
from mendex_core.engineering_lifecycle import storage
from mendex_core.evidence import ManualCheck
from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def context(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("GENERIC", "Software fixture only", "pcb", "Test engineer")
    return service, product.active_revision_id


def enrollment(revision, **changes):
    return {"revision_id": str(revision), "source": "test-fixture", "reason": "Explicit test enrollment",
            "idempotency_key": "enroll", **changes}


def command(revision, action, stage="project_initialization", **changes):
    return {"revision_id": str(revision), "stage_id": stage, "action": action, "source": "test-fixture",
            "reason": "Disposable software fixture", "idempotency_key": str(uuid4()), **changes}


def custom(service, revision, *, review=False, optional=False, dependency=False):
    stages = [{"id": "check", "name": "Recorded check", "purpose": "Software acceptance fixture",
               "optional": optional, "review_required": review, "criteria": [
                   {"id": "value", "description": "Explicit numerical rule", "kind": "validation_record", "check_id": "fixture_check", "evidence_kind": "CALCULATED"}]}]
    if dependency:
        stages.append({"id": "dependent", "name": "Dependent", "purpose": "Dependency invalidation fixture",
                       "dependencies": ["check"], "review_required": False,
                       "criteria": [{"id": "context", "description": "Existing project", "kind": "project_context"}]})
    definition = {"id": "fixture", "version": "1.0.0", "name": "Software test lifecycle", "stages": stages}
    service.engineering_lifecycle.register_definition(definition, "test-fixture")
    return service.engineering_lifecycle.enroll(enrollment(revision, definition_id="fixture", version="1.0.0"))


def evidence(service, revision, tmp_path, *, passed=True, kind="CALCULATED", check_id="fixture_check"):
    path = tmp_path / (str(uuid4()) + ".txt")
    path.write_text("Synthetic software-test evidence, not an engineering or physical measurement", encoding="utf-8")
    check = ManualCheck(check_id=check_id, status="pass" if passed else "fail", reviewer="Test assertion only",
                        notes="Software fixture, not independently verified", evidence_kind=kind,
                        measured_value=1 if passed else 5, minimum=0, maximum=2, unit="V")
    return service.record_validation(revision, check, path)


def attach(service, revision, record, stage="check"):
    return service.engineering_lifecycle.apply(command(revision, "attach_evidence", stage, evidence_record_id=str(record.record_id)))


def test_default_configuration_and_no_startup_migration(context):
    service, revision = context
    definition = service.engineering_lifecycle.default_definition()
    assert len(definition.stages) == 9
    assert definition.stages[7].optional
    assert definition.stages[7].criteria[0].evidence_kind == "MEASURED"
    assert len(service.engineering_lifecycle.list_definitions()) == 1
    with service.connection() as db:
        assert not storage.installed(db)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
    with pytest.raises(StudioError, match="not been enrolled"):
        service.engineering_lifecycle.get(revision)


def test_enrollment_backup_restore_and_identity(context):
    service, revision = context
    original = service.get_revision(revision).model_dump_json()
    first = service.engineering_lifecycle.enroll(enrollment(revision))
    assert first == service.engineering_lifecycle.enroll(enrollment(revision))
    view = service.engineering_lifecycle.get(revision)
    assert all(s["status"] == "NOT_STARTED" for s in view["stages"])
    assert view["engineering_status"] == "NOT_EVALUATED"
    assert len(service.list_products()) == 1
    assert service.get_revision(revision).model_dump_json() == original
    with service.connection() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        backup = service.root / db.execute("SELECT backup_path FROM engineering_lifecycle_schema").fetchone()[0]
    manifest = json.loads((backup / "manifest.json").read_text())
    assert storage.file_hash(backup / "studio.sqlite3") == manifest["database_sha256"]
    restored_path = service.root / "restored.sqlite3"
    with sqlite3.connect(backup / "studio.sqlite3") as source, sqlite3.connect(restored_path) as restored:
        source.backup(restored)
        assert restored.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert restored.execute("SELECT payload FROM revisions WHERE id=?", (str(revision),)).fetchone()[0] == original
        assert not storage.installed(restored)
    with pytest.raises(StudioError, match="Idempotency"):
        service.engineering_lifecycle.enroll(enrollment(revision, reason="different request"))


def test_completion_idempotency_and_new_attempt(context):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    lifecycle.enroll(enrollment(revision))
    with pytest.raises(StudioError, match="Start/reopen"):
        lifecycle.apply(command(revision, "complete"))
    lifecycle.apply(command(revision, "start"))
    request = command(revision, "complete", expected_sequence=lifecycle.get(revision)["sequence"])
    first = lifecycle.apply(request)
    assert lifecycle.apply(request) == first
    assert first["status"] == "COMPLETED"
    assert lifecycle.get(revision)["approval_status"] == "UNAVAILABLE"
    lifecycle.apply(command(revision, "reopen"))
    assert lifecycle.get(revision)["stages"][0]["attempt"] == 2
    assert [e["action"] for e in lifecycle.history(revision)["events"]] == ["enroll", "start", "complete", "reopen"]


def test_completion_needs_intact_current_evidence_and_invalidates_dependents(context, tmp_path):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    custom(service, revision, dependency=True)
    lifecycle.apply(command(revision, "start", "check"))
    with pytest.raises(StudioError, match="NOT_EVALUATED"):
        lifecycle.apply(command(revision, "complete", "check"))
    record = evidence(service, revision, tmp_path)
    attach(service, revision, record)
    completed = lifecycle.apply(command(revision, "complete", "check"))
    lifecycle.apply(command(revision, "start", "dependent"))
    lifecycle.apply(command(revision, "complete", "dependent"))
    assert all(s["effective_status"] == "COMPLETED" for s in lifecycle.get(revision)["stages"])
    copied = service.root / record.evidence_uri
    copied.write_text("Altered disposable copied evidence", encoding="utf-8")
    states = lifecycle.get(revision)["stages"]
    assert all(s["effective_status"] == "BLOCKED" for s in states)
    assert states[0]["criteria"][0]["status"] == "NOT_EVALUATED"
    assert next(e for e in lifecycle.history(revision)["events"] if e["sequence"] == completed["sequence"])["status"] == "COMPLETED"


def test_wrong_kind_failed_and_stale_validation_cannot_clear_stage(context, tmp_path):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    custom(service, revision)
    lifecycle.apply(command(revision, "start", "check"))
    attach(service, revision, evidence(service, revision, tmp_path, kind="MEASURED"))
    with pytest.raises(StudioError, match="NOT_EVALUATED"):
        lifecycle.apply(command(revision, "complete", "check"))
    attach(service, revision, evidence(service, revision, tmp_path))
    attach(service, revision, evidence(service, revision, tmp_path, passed=False))
    assert lifecycle.get(revision)["stages"][0]["criteria"][0]["status"] == "FAIL"
    with pytest.raises(StudioError, match="FAIL"):
        lifecycle.apply(command(revision, "complete", "check"))
    service.update_specification(revision, Specification(vin_nom_v=12, source="Changed fixture"))
    assert lifecycle.get(revision)["stages"][0]["stale"]
    with pytest.raises(StudioError, match="Specification changed"):
        lifecycle.apply(command(revision, "complete", "check"))
    lifecycle.apply(command(revision, "reopen", "check"))
    assert lifecycle.get(revision)["stages"][0]["evidence_record_ids"] == []


def test_review_request_never_grants_approval(context, tmp_path):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    custom(service, revision, review=True)
    lifecycle.apply(command(revision, "start", "check"))
    attach(service, revision, evidence(service, revision, tmp_path))
    lifecycle.apply(command(revision, "request_review", "check"))
    assert lifecycle.get(revision)["stages"][0]["review_status"] == "REQUESTED"
    with pytest.raises(StudioError, match="Authorized human review"):
        lifecycle.apply(command(revision, "complete", "check"))
    with pytest.raises(ValidationError):
        StageCommand.model_validate(command(revision, "approve", "check"))


def test_optional_exemption_and_mandatory_rejection(context):
    service, revision = context
    custom(service, revision, optional=True)
    service.engineering_lifecycle.apply(command(revision, "not_applicable", "check", reason="Explicitly outside software-fixture scope"))
    assert service.engineering_lifecycle.get(revision)["stages"][0]["status"] == "NOT_APPLICABLE"
    service.engineering_lifecycle.apply(command(revision, "reopen", "check"))
    assert service.engineering_lifecycle.get(revision)["stages"][0]["attempt"] == 1


def test_mandatory_and_review_required_exemptions_rejected(context):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    lifecycle.enroll(enrollment(revision))
    with pytest.raises(StudioError, match="Mandatory"):
        lifecycle.apply(command(revision, "not_applicable"))
    with pytest.raises(StudioError, match="authorized review"):
        lifecycle.apply(command(revision, "not_applicable", "prototype_testing"))


def test_missing_evidence_and_old_specification_rejected_on_attachment(context, tmp_path):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    custom(service, revision)
    lifecycle.apply(command(revision, "start", "check"))
    record = evidence(service, revision, tmp_path)
    service.update_specification(revision, Specification(vin_nom_v=20, source="New fixture specification"))
    with pytest.raises(StudioError, match="stale"):
        attach(service, revision, record)
    new_record = evidence(service, revision, tmp_path)
    (service.root / new_record.evidence_uri).unlink()
    with pytest.raises(StudioError, match="missing"):
        attach(service, revision, new_record)


def test_block_fail_restart_and_specification_fields(context):
    service, revision = context
    definition = {"id": "context_fixture", "version": "1.0.0", "name": "Context fixture", "stages": [
        {"id": "context", "name": "Source", "purpose": "Sourced context", "review_required": False,
         "criteria": [{"id": "source", "description": "Sourced specification", "kind": "specification_fields", "fields": ["source", "standards_profile"]}]}]}
    lifecycle = service.engineering_lifecycle
    lifecycle.register_definition(definition, "Fixture policy")
    lifecycle.enroll(enrollment(revision, definition_id="context_fixture", version="1.0.0"))
    lifecycle.apply(command(revision, "start", "context"))
    with pytest.raises(StudioError, match="NOT_EVALUATED"):
        lifecycle.apply(command(revision, "complete", "context"))
    lifecycle.apply(command(revision, "block", "context", reason="Need specification source"))
    with pytest.raises(StudioError, match="blocked stage"):
        lifecycle.apply(command(revision, "complete", "context"))
    service.update_specification(revision, Specification(source="Software fixture only", standards_profile="Fixture profile; not standards compliance"))
    lifecycle.apply(command(revision, "start", "context"))
    lifecycle.apply(command(revision, "fail", "context", reason="Explicit failed attempt"))
    lifecycle.apply(command(revision, "start", "context"))
    lifecycle.apply(command(revision, "complete", "context"))
    assert lifecycle.get(revision)["stages"][0]["attempt"] == 3


def test_backup_failure_does_not_change_schema_or_evidence(context, monkeypatch):
    service, revision = context
    path = service.workspace_path(service.get_revision(revision)) / "requirements" / "original.txt"
    path.write_bytes(b"Original immutable fixture bytes")
    before = storage.file_hash(path)

    def fail_backup(_):
        raise OSError("Injected backup failure")

    monkeypatch.setattr(storage, "backup_before_migration", fail_backup)
    with pytest.raises(OSError, match="backup failure"):
        service.engineering_lifecycle.enroll(enrollment(revision))
    assert storage.file_hash(path) == before
    with service.connection() as db:
        assert not storage.installed(db)


def test_revision_isolation_and_frozen_history(context, tmp_path):
    service, revision = context
    custom(service, revision)
    service.engineering_lifecycle.apply(command(revision, "start", "check"))
    record = evidence(service, revision, tmp_path)
    product = service.get_revision(revision).product_id
    new = service.create_revision(product, "R002")
    assert service.engineering_lifecycle.get(revision)["stages"][0]["attempt"] == 1
    with pytest.raises(StudioError, match="draft revision"):
        attach(service, revision, record)
    with pytest.raises(StudioError, match="not been enrolled"):
        service.engineering_lifecycle.get(new.revision_id)
    custom(service, new.revision_id)
    service.engineering_lifecycle.apply(command(new.revision_id, "start", "check"))
    with pytest.raises(StudioError, match="not associated"):
        attach(service, new.revision_id, record)


def test_optimistic_conflict_and_history_pagination(context):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    event = lifecycle.enroll(enrollment(revision))
    lifecycle.apply(command(revision, "start", expected_sequence=event["sequence"]))
    with pytest.raises(StudioError, match="Lifecycle changed"):
        lifecycle.apply(command(revision, "complete", expected_sequence=event["sequence"]))
    page = lifecycle.history(revision, limit=1)
    assert len(page["events"]) == 1
    next_page = lifecycle.history(revision, after_sequence=page["next_after_sequence"], limit=1)
    assert next_page["events"][0]["action"] == "start"
    assert len(lifecycle.history(revision, stage_id="project_initialization")["events"]) == 1


def test_parallel_retries_commit_one_event(context):
    service, revision = context
    lifecycle = service.engineering_lifecycle
    lifecycle.enroll(enrollment(revision))
    request = command(revision, "start", idempotency_key="same-concurrent-request")
    with ThreadPoolExecutor(max_workers=2) as executor:
        events = list(executor.map(lambda _: lifecycle.apply(request), range(2)))
    assert events[0] == events[1]
    assert len(lifecycle.history(revision)["events"]) == 2


def test_append_only_definition_versions_and_future_schema(context):
    service, revision = context
    custom(service, revision)
    definition = service.engineering_lifecycle.definition("fixture", "1.0.0")
    definition["name"] = "Changed immutable version"
    with pytest.raises(StudioError, match="immutable"):
        service.engineering_lifecycle.register_definition(definition, "test")
    for table in (*storage.TABLES, "schema"):
        for operation in ("UPDATE", "DELETE"):
            with sqlite3.connect(service.database) as db, pytest.raises(sqlite3.IntegrityError, match="append-only"):
                statement = f"UPDATE engineering_lifecycle_{table} SET " + ({"definitions": "source=source", "assignments": "created_at=created_at", "events": "payload=payload", "schema": "version=version"}[table]) if operation == "UPDATE" else f"DELETE FROM engineering_lifecycle_{table}"
                db.execute(statement)
    # Future-version fixture bypasses the table constraint by replacing only a disposable schema marker.
    with sqlite3.connect(service.database) as db:
        db.execute("DROP TABLE engineering_lifecycle_schema")
        db.execute("CREATE TABLE engineering_lifecycle_schema(version INTEGER)")
        db.execute("INSERT INTO engineering_lifecycle_schema VALUES(2)")
    with pytest.raises(StudioError, match="Unsupported"):
        service.engineering_lifecycle.get(revision)


def test_migration_failure_rolls_back_and_old_data_survives(context, monkeypatch):
    service, revision = context
    original_connection = service.connection

    class FailingDB:
        def __init__(self, db):
            self.db = db

        def execute(self, statement, *args):
            if statement.startswith("CREATE TABLE engineering_lifecycle_events"):
                raise RuntimeError("Injected migration failure")
            return self.db.execute(statement, *args)

    @contextmanager
    def failing_connection():
        with original_connection() as db:
            yield FailingDB(db)

    monkeypatch.setattr(service, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="Injected"):
        service.engineering_lifecycle.enroll(enrollment(revision))
    with original_connection() as db:
        assert not storage.installed(db)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert db.execute("SELECT id FROM revisions WHERE id=?", (str(revision),)).fetchone()


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(command="python unsafe.py"),
    lambda d: d["stages"].append(d["stages"][0]),
    lambda d: d["stages"][0].update(dependencies=["missing"]),
    lambda d: d["stages"][0].update(dependencies=[d["stages"][0]["id"]]),
    lambda d: d["stages"][0]["criteria"][0].update(kind="eval"),
    lambda d: d["stages"][0]["criteria"][0].update(fields=["unknown"], kind="specification_fields"),
])
def test_configuration_rejects_code_and_invalid_graphs(mutate):
    definition = StudioService.__new__(StudioService)
    from mendex_core.engineering_lifecycle.service import EngineeringLifecycleService
    data = EngineeringLifecycleService(definition).default_definition().model_dump(mode="json")
    mutate(data)
    with pytest.raises(ValidationError):
        LifecycleDefinition.model_validate(data)
