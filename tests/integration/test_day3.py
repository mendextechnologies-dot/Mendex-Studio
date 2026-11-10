import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mendex_core import launch
from mendex_core.cli import main
from mendex_core.evidence import ManualCheck
from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


def test_end_to_end_with_shell_free_editor_handoff(tmp_path, monkeypatch, capsys):
    service = StudioService(tmp_path)
    product = service.create_product("MC-100", "Illustrative pilot", "transformer", "Test engineer")
    service.update_specification(product.active_revision_id, Specification(vin_nom_v=24, source="Illustrative fixture only"))
    revision = service.create_revision(product.product_id, "R002")
    editor = tmp_path / "Code.exe"
    editor.write_bytes(b"mock executable; never executed")
    monkeypatch.setattr(launch, "find_vscode", lambda: editor)
    requests = []
    def spawn(argv, **kwargs):
        requests.append((argv, kwargs))
        return SimpleNamespace(pid=1234)
    monkeypatch.setattr(launch.subprocess, "Popen", spawn)
    result = service.open_in_vscode(revision.revision_id)
    assert result["pid"] == 1234
    assert requests[0][1]["shell"] is False
    assert requests[0][0] == [str(editor), "--new-window", str(service.workspace_path(revision))]
    assert service.list_tools()
    evidence = tmp_path / "fixture.txt"
    evidence.write_text("Automated regression fixture only. Not an engineering measurement.")
    check = ManualCheck(check_id="INTENTIONAL-FAIL", status="fail", reviewer="Test engineer", notes="Deliberate failure fixture", measured_value=30, maximum=20, unit="V")
    service.record_validation(revision.revision_id, check, evidence)
    report = service.generate_report(revision.revision_id)
    assert "fail" in (service.root / report.report_path).read_text(encoding="utf-8")
    assert main(["--root", str(tmp_path), "validation", "--revision", str(revision.revision_id)]) is None
    assert json.loads(capsys.readouterr().out)[0]["effective_status"] == "fail"
    restarted = StudioService(tmp_path)
    assert restarted.get_product(product.product_id).active_revision_id == revision.revision_id
    assert restarted.list_reports(revision.revision_id) == [report]


def test_launch_paths_and_missing_editor(tmp_path, monkeypatch):
    service = StudioService(tmp_path)
    product = service.create_product("MC-100", "Pilot", "pcb", "Engineer")
    revision = service.get_revision(product.active_revision_id)
    monkeypatch.setattr(launch, "find_vscode", lambda: None)
    with pytest.raises(StudioError, match="VS Code not found"):
        service.open_in_vscode(revision.revision_id)
    for path in ("../outside.txt", str(tmp_path / "outside.txt"), "missing.txt"):
        with pytest.raises(StudioError):
            service.open_project_file(revision.revision_id, path)
    script = service.workspace_path(revision) / "unsafe.ps1"
    script.write_text("# never executed")
    with pytest.raises(StudioError, match="file type"):
        service.open_project_file(revision.revision_id, "unsafe.ps1")
    document = service.workspace_path(revision) / "requirements" / "spec.json"
    document.write_text("{}")
    opened = []
    monkeypatch.setattr(launch, "open_native", opened.append)
    service.open_project_file(revision.revision_id, "requirements/spec.json")
    assert opened == [document.resolve()]
    report = service.generate_report(revision.revision_id)
    service.open_report(report.report_id)
    assert opened[-1] == (service.root / report.report_path).resolve()
    def fail_open(path):
        raise OSError("No file association")
    monkeypatch.setattr(launch, "open_native", fail_open)
    with pytest.raises(StudioError, match="file association"):
        service.open_project_file(revision.revision_id, "requirements/spec.json")


def test_windows_code_command_uses_executable_not_batch_file(tmp_path, monkeypatch):
    install = tmp_path / "VS Code with spaces"
    (install / "bin").mkdir(parents=True)
    executable = install / "Code.exe"
    executable.write_bytes(b"mock executable")
    monkeypatch.setattr(launch.shutil, "which", lambda command: str(install / "bin" / "code.cmd"))
    assert launch.find_vscode() == executable.resolve()


def test_doctor_export_and_cli_errors(tmp_path, capsys):
    service = StudioService(tmp_path)
    diagnostic = service.diagnostics()
    assert diagnostic["framework_ready"]
    assert diagnostic["status"] == "PARTIAL"
    exported = service.export_diagnostics()
    assert json.loads(exported.read_text())["framework_ready"]
    assert main(["doctor", "--root", str(tmp_path), "--export"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PARTIAL"
    assert main(["--root", str(tmp_path), "validation", "--revision", "invalid"]) == 1
    error = json.loads(capsys.readouterr().err)
    assert error["error"] == "INVALID_INPUT"
