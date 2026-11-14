from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.lifecycle.engine import LifecycleStage, ProductLifecycleEngine
from mendex_core.measurements.service import MeasurementService
from mendex_core.models import Category, Lifecycle, Specification
from mendex_core.service import StudioError, StudioService


def _init_test_env(tmp_path: Path):
    service = StudioService(tmp_path)
    product = service.create_product("TEST-PROD", "Test DC-DC Converter", Category.DC_DC, "Engineer")
    rev = service.list_revisions(product.product_id)[0]
    return service, product, rev


def test_lifecycle_approvals_immutability_triggers(tmp_path):
    service, product, rev = _init_test_env(tmp_path)
    engine = ProductLifecycleEngine(service)

    # 1. Attempting empty reviewer must raise ValueError
    with pytest.raises(ValueError, match="Reviewer identity is required and cannot be empty"):
        engine.record_stage_approval(rev.revision_id, LifecycleStage.REQUIREMENTS, "", True, "Note")

    with pytest.raises(ValueError, match="Reviewer identity is required and cannot be empty"):
        engine.record_stage_approval(rev.revision_id, LifecycleStage.REQUIREMENTS, "   ", True, "Note")

    # 2. Record valid approval
    engine.record_stage_approval(rev.revision_id, LifecycleStage.REQUIREMENTS, "Alice Engineer", True, "Signed off")
    approvals = engine.get_stage_approvals(rev.revision_id)
    assert LifecycleStage.REQUIREMENTS.value in approvals
    app = approvals[LifecycleStage.REQUIREMENTS.value]
    assert app["reviewer"] == "Alice Engineer"
    assert app["passed"] is True
    assert app["stale"] is False

    # 3. Raw UPDATE via SQLite must be blocked by trigger
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Lifecycle approval records are append-only"):
            db.execute("UPDATE lifecycle_approvals SET passed=0 WHERE revision_id=?", (str(rev.revision_id),))

    # 4. Raw DELETE via SQLite must be blocked by trigger
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Lifecycle approval records are append-only"):
            db.execute("DELETE FROM lifecycle_approvals WHERE revision_id=?", (str(rev.revision_id),))


def test_approval_becomes_stale_when_specification_changes(tmp_path):
    service, product, rev = _init_test_env(tmp_path)
    engine = ProductLifecycleEngine(service)

    # Set initial spec
    spec1 = Specification(vin_nom_v=48.0, vout_v=12.0, iout_a=5.0)
    service.update_specification(rev.revision_id, spec1)

    # Record approval for REQUIREMENTS
    engine.record_stage_approval(rev.revision_id, LifecycleStage.REQUIREMENTS, "Chief Engineer Bob", True, "Approved spec")
    approvals = engine.get_stage_approvals(rev.revision_id)
    assert approvals[LifecycleStage.REQUIREMENTS.value]["passed"] is True
    assert approvals[LifecycleStage.REQUIREMENTS.value]["stale"] is False

    # Edit specification
    spec2 = Specification(vin_nom_v=60.0, vout_v=12.0, iout_a=6.0)
    service.update_specification(rev.revision_id, spec2)

    # Approval should now be marked stale and passed=False
    approvals_after = engine.get_stage_approvals(rev.revision_id)
    assert approvals_after[LifecycleStage.REQUIREMENTS.value]["stale"] is True
    assert approvals_after[LifecycleStage.REQUIREMENTS.value]["passed"] is False


def test_reports_table_immutability_triggers(tmp_path):
    service, product, rev = _init_test_env(tmp_path)
    rep = service.generate_report(rev.revision_id)

    # Raw UPDATE on reports must fail
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Report records are append-only"):
            db.execute("UPDATE reports SET payload='{}' WHERE id=?", (str(rep.report_id),))

    # Raw DELETE on reports must fail
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Report records are append-only"):
            db.execute("DELETE FROM reports WHERE id=?", (str(rep.report_id),))


def test_measurements_table_immutability_triggers(tmp_path):
    service, product, rev = _init_test_env(tmp_path)
    meas_service = MeasurementService(service)
    mid = str(uuid4())

    with service.connection() as db:
        db.execute(
            """
            INSERT INTO measurements (measurement_id, revision_id, test_name, measured_parameter, measured_value, pass_fail, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, str(rev.revision_id), "Ripple Test", "Vout_ripple", 0.045, "PASS", "{}", "2026-11-14T00:00:00Z"),
        )

    # Raw UPDATE must fail
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Measurement records are append-only"):
            db.execute("UPDATE measurements SET measured_value=0.1 WHERE measurement_id=?", (mid,))

    # Raw DELETE must fail
    with service.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="Measurement records are append-only"):
            db.execute("DELETE FROM measurements WHERE measurement_id=?", (mid,))


def test_delete_product_blocked_by_evidence(tmp_path):
    service, product, rev = _init_test_env(tmp_path)
    engine = ProductLifecycleEngine(service)

    # Record an approval
    engine.record_stage_approval(rev.revision_id, LifecycleStage.REQUIREMENTS, "QA Engineer", True, "Approved")

    # Deleting product must be blocked with DELETE_BLOCKED (not CONFLICT)
    with pytest.raises(StudioError) as exc_info:
        service.delete_product(product.product_id)
    assert exc_info.value.code == "DELETE_BLOCKED"
    assert "recorded evidence" in str(exc_info.value)
