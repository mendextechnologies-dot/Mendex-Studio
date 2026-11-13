"""Only disposable fixtures are archived; the live project root is never a test input."""
import importlib.util
import sqlite3
from pathlib import Path

import pytest

from mendex_core.evidence import ManualCheck
from mendex_core.models import Specification
from mendex_core.service import StudioService

spec = importlib.util.spec_from_file_location("archive_reset", Path(__file__).resolve().parents[2] / "scripts" / "remove_existing_products.py")
reset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reset)


def test_archive_preserves_frozen_revision_evidence_and_settings(tmp_path):
    studio = StudioService(tmp_path)
    product = studio.create_product("RESET", "Disposable reset fixture", "pcb", "Fixture")
    studio.update_specification(product.active_revision_id, Specification(source="Software fixture"))
    source = tmp_path / "source.txt"
    source.write_bytes(b"Disposable software evidence; not engineering evidence")
    validation = studio.record_validation(product.active_revision_id, ManualCheck(check_id="fixture", reviewer="Fixture", notes="Software-only check", measured_value=1, minimum=0, maximum=2, unit="V", status="pass"), source)
    relative = studio.workspace_path(studio.get_revision(product.active_revision_id)).relative_to(tmp_path)
    revision_bytes = (tmp_path / relative / "revision.json").read_bytes()
    studio.create_revision(product.product_id, "R002")
    with studio.connection() as db:
        db.execute("INSERT INTO tool_settings VALUES('fixture-tool','C:/fixture-tool.exe')")
    result = reset.archive_and_remove(tmp_path)
    assert result["status"] == "RESET_COMPLETE" and not result["originals_deleted"]
    assert result["counts_before"]["products"] == 1 and not any(result["counts_after"].values())
    archive = Path(result["archive"])
    assert reset.io_path(archive / "originals" / validation.evidence_uri).read_bytes() == source.read_bytes()
    assert reset.io_path(archive / "originals" / relative / "revision.json").read_bytes() == revision_bytes
    with sqlite3.connect(archive / "database-backup.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM validations")
    restarted = StudioService(tmp_path)
    assert restarted.list_products() == []
    with restarted.connection() as db:
        assert db.execute("SELECT path FROM tool_settings WHERE tool_id='fixture-tool'").fetchone()[0] == "C:/fixture-tool.exe"


def test_switch_failure_restores_originals(tmp_path, monkeypatch):
    studio = StudioService(tmp_path)
    product = studio.create_product("RESTORE", "Rollback fixture", "pcb", "Fixture")
    actual_move = reset.move
    failed_once = False

    def fail_once(source, destination, boundary):
        nonlocal failed_once
        if source.parent == tmp_path.resolve() and source.name == "products" and not failed_once:
            failed_once = True
            raise OSError("Injected directory switch failure")
        return actual_move(source, destination, boundary)

    monkeypatch.setattr(reset, "move", fail_once)
    with pytest.raises(OSError, match="Injected"):
        reset.archive_and_remove(tmp_path)
    assert StudioService(tmp_path).get_product(product.product_id).name == "Rollback fixture"
    assert (tmp_path / "products" / str(product.product_id)).exists()
    assert list((tmp_path / ".mendex-archives").glob("*/database-backup.sqlite3"))


def test_preview_no_mutation_and_running_job_guard(tmp_path):
    studio = StudioService(tmp_path)
    studio.create_product("PREVIEW", "Preview fixture", "pcb", "Fixture")
    before = (tmp_path / ".mendex" / "studio.sqlite3").read_bytes()
    assert reset.inspect(tmp_path)["counts"]["products"] == 1
    assert (tmp_path / ".mendex" / "studio.sqlite3").read_bytes() == before
    with studio.connection() as db:
        db.execute("INSERT INTO integration_workspaces(id,name) VALUES('fixture','fixture')")
        db.execute("INSERT INTO integration_jobs(id,workspace_id,status,payload) VALUES('fixture','fixture','RUNNING','{}')")
    with pytest.raises(ValueError, match="Running/queued"):
        reset.archive_and_remove(tmp_path)
    assert not (tmp_path / ".mendex-archives").exists()
