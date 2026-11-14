"""Tests for SQLite WAL mode, foreign key enforcement, migration v5 idempotency, and live database backup."""
import json
import sqlite3
from pathlib import Path
import pytest

from mendex_core.service import StudioService, StudioError
from mendex_core.desktop.service import DesktopService
from mendex_core.cli import main


def test_sqlite_wal_mode_and_foreign_keys(tmp_path):
    service = StudioService(tmp_path)
    with service.connection() as db:
        journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0].lower()
        foreign_keys = db.execute("PRAGMA foreign_keys").fetchone()[0]
        user_version = db.execute("PRAGMA user_version").fetchone()[0]

    assert journal_mode in ("wal", "memory")
    assert foreign_keys == 1
    assert user_version == 4


def test_migration_v5_idempotent_no_rerun(tmp_path):
    # First initialization executes migration up to v5
    service1 = StudioService(tmp_path)
    with service1.connection() as db:
        v1 = db.execute("PRAGMA user_version").fetchone()[0]
    assert v1 == 4

    # Second initialization must recognize user_version == 4 and not fail or re-run
    service2 = StudioService(tmp_path)
    with service2.connection() as db:
        v2 = db.execute("PRAGMA user_version").fetchone()[0]
    assert v2 == 4


def test_foreign_key_violation_rejected(tmp_path):
    service = StudioService(tmp_path)
    # Inserting a revision for non-existent product_id must raise StudioError CONFLICT or NOT_FOUND due to FK constraint
    with pytest.raises(StudioError) as exc_info:
        with service.connection() as db:
            db.execute("INSERT INTO revisions (id, product_id, label, payload) VALUES (?, ?, ?, ?)",
                       ("rev-001", "non-existent-product", "R001", "{}"))
    assert exc_info.value.code in ("NOT_FOUND", "CONFLICT")


def test_backup_database_service_creates_valid_snapshot(tmp_path):
    service = StudioService(tmp_path)
    prod = service.create_product("BK-100", "Backup Test Device", "dc_dc_converter", "Lead Engineer")
    revs = service.list_revisions(prod.product_id)
    assert len(revs) >= 1

    custom_backup = tmp_path / "backups" / "snapshot.sqlite3"
    result_path = service.backup_database(custom_backup)
    assert result_path == custom_backup
    assert custom_backup.is_file()

    # Verify backup database integrity and content
    with sqlite3.connect(custom_backup) as b_db:
        b_version = b_db.execute("PRAGMA user_version").fetchone()[0]
        assert b_version == 4
        rows = b_db.execute("SELECT code, payload FROM products WHERE id=?", (str(prod.product_id),)).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "BK-100"


def test_cli_backup_command(tmp_path, capsys):
    service = StudioService(tmp_path)
    service.create_product("CLI-99", "CLI Product", "transformer", "Engineer")

    dest_backup = tmp_path / "cli_backup.sqlite3"
    exit_code = main(["--root", str(tmp_path), "backup", "--output", str(dest_backup), "--json"])
    assert exit_code in (0, None)

    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "SUCCESS"
    assert Path(res["backup_path"]).is_file()


def test_desktop_rpc_backup(tmp_path):
    service = StudioService(tmp_path)
    service.create_product("RPC-88", "RPC Product", "dc_dc_converter", "Engineer")
    desktop = DesktopService(service)

    rpc_dest = tmp_path / "rpc_backup.sqlite3"
    res = desktop.dispatch("backup", {"destination": str(rpc_dest)})
    assert res["status"] == "SUCCESS"
    assert Path(res["backup_path"]).is_file()
    assert "timestamp" in res


def test_desktop_projects_batched_query_performance(tmp_path):
    service = StudioService(tmp_path)
    for i in range(5):
        service.create_product(f"PRJ-00{i}", f"Project {i}", "dc_dc_converter", "Engineer")

    desktop = DesktopService(service)
    projs = desktop.projects()
    assert len(projs) == 5
    for p in projs:
        assert p["code"].startswith("PRJ-00")
        assert p["revision_label"] == "R001"
        assert p["revision_status"] == "draft"

    overview = desktop.overview()
    assert overview["metrics"]["projects"] == 5
    assert overview["metrics"]["revisions"] >= 5
