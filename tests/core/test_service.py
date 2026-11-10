import sqlite3

import pytest
from pydantic import ValidationError

from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


def test_product_revision_survives_restart(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("MC-100", "Pilot", "transformer", "Engineer")
    spec = Specification(vin_min_v=20, vin_nom_v=24, vin_max_v=30, source="Illustrative only", assumptions=["Not approved"])
    service.update_specification(product.active_revision_id, spec)
    restarted = StudioService(tmp_path)
    assert restarted.get_revision(product.active_revision_id).specification == spec
    assert restarted.list_products() == [product]
    revision = restarted.create_revision(product.product_id, "R002")
    assert revision.specification == spec
    assert restarted.get_product(product.product_id).active_revision_id == revision.revision_id
    assert (restarted.workspace_path(revision) / "magnetics").is_dir()
    with pytest.raises(StudioError, match="baseline"):
        restarted.update_specification(product.active_revision_id, spec)


def test_duplicate_code_and_revision_are_atomic(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("MC-100", "Pilot", "pcb", "Engineer")
    with pytest.raises(StudioError):
        service.create_product("mc-100", "Duplicate", "pcb", "Engineer")
    with pytest.raises(StudioError):
        service.create_revision(product.product_id, "R001")
    assert len(service.list_products()) == 1
    assert service.get_revision(product.active_revision_id).lifecycle_status == "draft"


@pytest.mark.parametrize("payload", [{"vin_nom_v": -1}, {"vin_min_v": 30, "vin_max_v": 20}, {"voltage": 24}, {"vout_v": float("nan")}])
def test_invalid_units_and_ranges(payload):
    with pytest.raises(ValidationError):
        Specification(**payload)


def test_path_traversal_and_missing_product(tmp_path):
    service = StudioService(tmp_path)
    with pytest.raises(ValidationError):
        service.create_product("../escape", "Bad", "pcb", "Engineer")
    assert not service.list_products()
    with pytest.raises(StudioError) as error:
        service.get_product("00000000-0000-0000-0000-000000000000")
    assert error.value.code == "NOT_FOUND"


def test_workspace_failure_rolls_back(tmp_path, monkeypatch):
    service = StudioService(tmp_path)
    def fail(revision):
        raise OSError("Disk unavailable")
    monkeypatch.setattr(service, "_workspace", fail)
    with pytest.raises(OSError):
        service.create_product("MC-100", "Pilot", "pcb", "Engineer")
    assert service.list_products() == []


def test_newer_database_rejected(tmp_path):
    service = StudioService(tmp_path)
    with sqlite3.connect(service.database) as db:
        db.execute("PRAGMA user_version=4")
    with pytest.raises(StudioError, match="newer"):
        StudioService(tmp_path)
