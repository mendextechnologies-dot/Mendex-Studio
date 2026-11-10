"""Evidence/failure tests for shared PCB operations; fixtures are synthetic CAD."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from integrations.parsers.kicad_parser import parse_kicad_drc_json
from mendex_core.cli import main
from mendex_core.pcb import native_structure
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def studio(tmp_path):
    service = StudioService(tmp_path / "studio")
    product = service.create_product("PCB-TEST", "Synthetic PCB test", "pcb", "Test fixture")
    revision = service.get_revision(product.active_revision_id)
    pcb = service.workspace_path(revision) / "pcb"
    schematic = pcb / "test.kicad_sch"
    schematic.write_text('(kicad_sch (version 20250114) (symbol (lib_id "Device:R")))', encoding="utf-8")
    board = pcb / "test.kicad_pcb"
    board.write_text('(kicad_pcb (footprint "Test" (pad "1" smd rect)) (segment (start 0 0)))', encoding="utf-8")
    return service, product, revision, pcb


def fake_checker(monkeypatch, service, issues=0):
    tool = service.lifecycle.kicad
    monkeypatch.setattr(tool, "is_available", lambda:True)
    tool.kicad_cli = Path("test-kicad.exe")
    monkeypatch.setattr("mendex_core.pcb.subprocess.run", lambda *a, **k:SimpleNamespace(returncode=0, stdout="fixture version", stderr=""))

    def check(source, output):
        assert "inputs" in source.parts
        assert source.is_file()
        output.write_text(json.dumps({"violations":[{"type":"fixture"}] * issues}), encoding="utf-8")
        return {"exit_code":0,"parsed":parse_kicad_drc_json(output),"stdout":"fixture stdout", "stderr":"", "command":["fixture-only"]}

    monkeypatch.setattr(tool,"run_erc",check)
    monkeypatch.setattr(tool,"run_drc",check)


def test_empty_design_and_library_symbols_cannot_clear(studio,monkeypatch):
    service,_,revision,pcb=studio
    path=pcb/"empty.kicad_sch"
    path.write_text('(kicad_sch (lib_symbols (symbol "R")) (text "(symbol fake)"))')
    assert not native_structure(path)["populated"]
    monkeypatch.setattr(service.lifecycle.kicad,"run_erc",lambda *a:pytest.fail("Empty design reached KiCad"))
    result=service.pcb.run_check(revision.revision_id,"pcb/empty.kicad_sch","erc")
    assert result["effective_status"]=="NOT_EVALUATED"
    assert "No placed symbols" in result["diagnostic"]
    board=pcb/"empty.kicad_pcb"
    board.write_text('(kicad_pcb (gr_rect (start 0 0) (end 50 32)))')
    assert not native_structure(board)["populated"]


def test_snapshot_persistence_and_context_changes(studio,monkeypatch):
    service,product,revision,pcb=studio
    fake_checker(monkeypatch,service)
    original=(pcb/"test.kicad_sch").read_bytes()
    result=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_sch","erc")
    assert result["status"]==result["effective_status"]=="CLEAR"
    assert result["integrity"] and not result["stale"]
    assert result["product_evaluation"]=="NOT_EVALUATED"
    assert (pcb/"test.kicad_sch").read_bytes()==original
    run=Path(result["evidence_folder"])
    assert (run/"inputs/test.kicad_sch").read_bytes()==original
    opened=[]
    monkeypatch.setattr("mendex_core.launch.open_native",lambda path:opened.append(path))
    assert Path(service.pcb.open_check_evidence(revision.revision_id,result["run_id"]))==run
    assert opened==[run]
    assert not list(pcb.glob("*erc*.json"))
    service2=StudioService(service.root)
    assert service2.pcb.list_checks(revision.revision_id)[0]["effective_status"]=="CLEAR"
    (pcb/"test.kicad_pro").write_text('{"fixture":"changed context"}')
    changed=service2.pcb.read_check(revision.revision_id,result["run_id"])
    assert changed["status"]=="CLEAR" and changed["effective_status"]=="NOT_EVALUATED"
    assert changed["stale"]
    assert not service.lifecycle.get_stage_approvals(revision.revision_id)
    assert not service.list_validation(revision.revision_id)


def test_tamper_detection(studio,monkeypatch):
    service,_,revision,_=studio
    fake_checker(monkeypatch,service)
    result=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_pcb","drc")
    (Path(result["evidence_folder"])/"drc.json").write_text('{}')
    read=service.pcb.read_check(revision.revision_id,result["run_id"])
    assert not read["integrity"] and read["effective_status"]=="NOT_EVALUATED"


def test_missing_tool_and_timeout_are_not_clean(studio,monkeypatch):
    service,_,revision,_=studio
    monkeypatch.setattr(service.lifecycle.kicad,"is_available",lambda:False)
    result=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_sch","erc")
    assert result["effective_status"]=="NOT_EVALUATED" and "unavailable" in result["diagnostic"]
    fake_checker(monkeypatch,service)
    def timeout(*a):
        raise subprocess.TimeoutExpired("fixture",60)
    monkeypatch.setattr(service.lifecycle.kicad,"run_erc",timeout)
    result=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_sch","erc")
    assert result["effective_status"]=="ERROR" and "timed out" in result["diagnostic"]


def test_issues_and_cli_use_same_service(studio,monkeypatch,capsys):
    service,_,revision,_=studio
    fake_checker(monkeypatch,service,issues=2)
    monkeypatch.setattr("mendex_core.cli.StudioService",lambda root:service)
    exit_code=main(["--root",str(service.root),"pcb-check","--revision",str(revision.revision_id),"--kind","erc","pcb/test.kicad_sch"])
    result=json.loads(capsys.readouterr().out)
    assert exit_code==1 and result["effective_status"]=="ISSUES_FOUND"
    assert result["parsed"]["total_issues"]==2


def test_import_preserves_files_and_archives(studio,tmp_path):
    service,product,revision,pcb=studio
    source=tmp_path/"import.kicad_sch"
    source.write_text('(kicad_sch)')
    service.pcb.import_file(revision.revision_id,source)
    with pytest.raises(StudioError,match="already exists"):
        service.pcb.import_file(revision.revision_id,source)
    assert (pcb/source.name).read_bytes()==source.read_bytes()
    service.create_revision(product.product_id,"NEXT")
    with pytest.raises(StudioError,match="draft"):
        service.pcb.import_file(revision.revision_id,source)
    with pytest.raises(StudioError,match="draft"):
        service.pcb.save_review_notes(revision.revision_id,"new notes")
    with pytest.raises(StudioError,match="editing"):
        service.pcb.open_file(revision.revision_id,"pcb/test.kicad_sch")


def test_paths_and_check_types_are_validated(studio):
    service,_,revision,_=studio
    for path,kind in [("../../outside.kicad_sch","erc"),("pcb/test.kicad_pcb","erc"),("pcb/test.kicad_sch","export")]:
        with pytest.raises(StudioError):
            service.pcb.run_check(revision.revision_id,path,kind)


def test_notes_and_spec_changes_invalidate_existing_result(studio,monkeypatch):
    service,_,revision,_=studio
    fake_checker(monkeypatch,service)
    result=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_sch","erc")
    service.pcb.save_review_notes(revision.revision_id,"Clearance review unresolved")
    assert service.pcb.review_notes(revision.revision_id)=="Clearance review unresolved"
    assert service.pcb.read_check(revision.revision_id,result["run_id"])["stale"]
    fresh=service.pcb.run_check(revision.revision_id,"pcb/test.kicad_sch","erc")
    assert not fresh["stale"]
    spec=revision.specification.model_copy(deep=True)
    spec.assumptions.append("Changed test requirement")
    service.update_specification(revision.revision_id,spec)
    assert service.pcb.read_check(revision.revision_id,fresh["run_id"])["effective_status"]=="NOT_EVALUATED"


@pytest.mark.parametrize("content",['not json','{}','{"violations":null}','{"sheets":[4]}'])
def test_malformed_reports_never_clean(tmp_path,content):
    path=tmp_path/"erc.json";path.write_text(content)
    with pytest.raises(ValueError):
        parse_kicad_drc_json(path)


def test_real_report_arrays_all_counted(tmp_path):
    path=tmp_path/"drc.json"
    path.write_text(json.dumps({"violations":[],"unconnected_items":[{}],"schematic_parity":[{}],
                                "sheets":[{"violations":[{}],"sheets":[{"violations":[{}]}]}]}))
    assert parse_kicad_drc_json(path)["total_issues"]==4


def test_low_level_preserves_reports_and_rejects_malformed(studio,tmp_path,monkeypatch):
    service,_,_,pcb=studio
    tool=service.lifecycle.kicad
    monkeypatch.setattr(tool,"is_available",lambda:True)
    report=tmp_path/"erc.json"
    report.write_text('{"violations":[]}')
    with pytest.raises(FileExistsError):
        tool.run_erc(pcb/"test.kicad_sch",report)
    report2=tmp_path/"new.json"
    def bad_run(*a,**k):
        report2.write_text("not a report")
        return SimpleNamespace(returncode=0,stdout="",stderr="")
    monkeypatch.setattr("mendex_core.lifecycle.kicad_service.subprocess.run",bad_run)
    result=tool.run_erc(pcb/"test.kicad_sch",report2)
    assert not result["passed"] and not result["parsed"]
