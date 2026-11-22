"""First-party layout tests use synthetic native CAD and disposable data roots."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from copper_kicad import sexpr
from mendex_core.cli import main
from mendex_core.desktop.service import DesktopService
from mendex_core.pcb_layout import LayoutPlan
from mendex_core.service import StudioError, StudioService


BOARD = '''(kicad_pcb (version 20250114)
 (net 0 "") (net 1 "SIGNAL") (net 2 "GND")
 (gr_rect (start 0 0) (end 50 40) (layer "Edge.Cuts"))
 (footprint "Test:IC" (layer "F.Cu") (at 10 20 90)
  (fp_rect (start -1 -1) (end 1 1) (layer "F.CrtYd"))
  (property "Reference" "U1") (property "Value" "Synthetic IC")
  (pad "1" smd rect (at 1 0) (size 1 2) (layers "F.Cu") (net 1 "SIGNAL"))
  (pad "2" smd rect (at 0 1) (size 1 2) (layers "F.Cu") (net 2 "GND")))
 (footprint "Test:R" (layer "F.Cu") (at 30 20)
  (fp_rect (start -0.5 -0.5) (end 0.5 0.5) (layer "F.CrtYd"))
  (fp_text reference "R1") (fp_text value "1k")
  (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1 "SIGNAL")))
 (footprint "Test:Connector" locked (layer "F.Cu") (at 40 20)
  (fp_rect (start -1 -1) (end 1 1) (layer "F.CrtYd"))
  (property "Reference" "J1")
  (pad "1" thru_hole circle (at 0 0) (size 2 2) (net 2 "GND"))))'''


@pytest.fixture
def layout(tmp_path):
    studio = StudioService(tmp_path / "studio")
    product = studio.create_product("LAYOUT-TEST", "Synthetic fixture", "pcb", "Test")
    rev = studio.get_revision(product.active_revision_id)
    pcb = studio.workspace_path(rev) / "pcb"
    (pcb / "test.kicad_pcb").write_text(BOARD, encoding="utf-8")
    (pcb / "test.kicad_pro").write_text('{"fixture":true}')
    yield studio, rev, pcb
    studio.integrations.shutdown()


def plan(studio, rev, moves=None):
    a = studio.pcb_layout.analyze(rev.revision_id, "pcb/test.kicad_pcb")
    return {"relative_path": a["source"], "expected_context_sha256": a["context_sha256"],
            "moves": moves or [], "rationale": "Synthetic placement experiment"}


def test_analysis_extracts_real_connectivity_si_rotation_and_locks(layout):
    studio, rev, pcb = layout
    before = {p.name: p.read_bytes() for p in pcb.iterdir()}
    result = studio.pcb_layout.analyze(rev.revision_id, "pcb/test.kicad_pcb")
    assert result["populated"] and result["evaluation_status"] == "NOT_EVALUATED"
    u, r, j = result["components"]
    assert u["x_m"] == .01 and u["pads"][0]["y_m"] == pytest.approx(.019)
    assert u["pads"][1]["x_m"] == pytest.approx(.011)
    assert r["reference"] == "R1" and r["value"] == "1k" and j["locked"]
    signal = next(n for n in result["nets"] if n["name"] == "SIGNAL")
    assert signal["pads"] == [{"reference": "U1", "pad": "1"}, {"reference": "R1", "pad": "1"}]
    assert result["edge_cuts"][0]["points_m"]["end"] == [.05, .04]
    assert before == {p.name: p.read_bytes() for p in pcb.iterdir()}


def test_candidate_preserves_sources_dependencies_and_only_moves_requested_footprint(layout):
    studio, rev, pcb = layout
    before = {p.name: p.read_bytes() for p in pcb.iterdir()}
    request = plan(studio, rev, [{"reference": "R1", "x_m": .012, "y_m": .021}])
    result = studio.pcb_layout.create_candidate(rev.revision_id, request)
    assert result["integrity"] and not result["stale"] and result["status"] == "DRAFT_CANDIDATE"
    assert result["evaluation_status"] == "NOT_EVALUATED"
    source = sexpr.loads(BOARD)
    candidate = sexpr.loads(Path(result["board_path"]).read_text())
    fps = sexpr.find_all(candidate, "footprint")
    assert sexpr.find(fps[1], "at")[1:3] == ["12", "21"]
    assert sexpr.find_all(source, "footprint")[0] == fps[0]
    sexpr.set_value(fps[1], "at", sexpr.Sym("30"), sexpr.Sym("20"))
    assert source == candidate  # all other native content preserved semantically
    folder = Path(result["folder"])
    assert (folder / "inputs/test.kicad_pcb").read_bytes() == before["test.kicad_pcb"]
    assert (folder / "output/test.kicad_pro").read_bytes() == before["test.kicad_pro"]
    assert before == {p.name: p.read_bytes() for p in pcb.iterdir()}
    assert not studio.list_validation(rev.revision_id)
    assert not studio.lifecycle.get_stage_approvals(rev.revision_id)
    assert studio.pcb_layout.list_candidates(rev.revision_id)[0]["candidate_id"] == result["candidate_id"]


@pytest.mark.parametrize("reference", ["J1", "UNKNOWN"])
def test_reject_locked_or_unknown_moves(layout, reference):
    studio, rev, _ = layout
    with pytest.raises(StudioError, match="Unknown or locked"):
        studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev, [{"reference": reference, "x_m": .02, "y_m": .02}]))


@pytest.mark.parametrize("copper", ['(segment (start 1 1) (end 2 2))', '(via (at 2 2))',
                                     '(arc (start 1 1) (mid 2 2) (end 3 1))', '(zone (net 2))'])
def test_reject_moves_on_existing_copper_but_allow_byte_exact_snapshot(layout, copper):
    studio, rev, pcb = layout
    path = pcb / "test.kicad_pcb"
    path.write_text(BOARD[:-1] + copper + ')')
    with pytest.raises(StudioError, match="unrouted"):
        studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev, [{"reference": "R1", "x_m": .02, "y_m": .02}]))
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    assert Path(result["board_path"]).read_bytes() == path.read_bytes()


def test_stale_request_and_candidate_follow_dependency_and_specification_changes(layout):
    studio, rev, pcb = layout
    request = plan(studio, rev)
    result = studio.pcb_layout.create_candidate(rev.revision_id, request)
    (pcb / "test.kicad_pro").write_text('{"changed":true}')
    with pytest.raises(StudioError, match="context changed"):
        studio.pcb_layout.create_candidate(rev.revision_id, request)
    stale = studio.pcb_layout.read_candidate(rev.revision_id, result["candidate_id"])
    assert stale["integrity"] and stale["stale"] and stale["status"] == "NOT_EVALUATED"
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    studio.update_specification(rev.revision_id, rev.specification.model_copy(update={"source": "changed"}))
    assert studio.pcb_layout.read_candidate(rev.revision_id, result["candidate_id"])["stale"]


@pytest.mark.parametrize("damage", ["change", "remove", "extra"])
def test_tampered_candidates_never_remain_current(layout, damage):
    studio, rev, _ = layout
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    board = Path(result["board_path"])
    if damage == "change":
        board.write_text('(kicad_pcb)')
    elif damage == "remove":
        board.unlink()
    else:
        (board.parent / "unexpected.kicad_dru").write_text("unexpected rule")
    read = studio.pcb_layout.read_candidate(rev.revision_id, result["candidate_id"])
    assert not read["integrity"] and read["status"] == "NOT_EVALUATED"


def test_archived_analysis_allowed_candidate_write_rejected(layout):
    studio, rev, _ = layout
    request = plan(studio, rev)
    studio.create_revision(rev.product_id, "NEXT")
    assert studio.pcb_layout.analyze(rev.revision_id, request["relative_path"])["populated"]
    with pytest.raises(StudioError, match="draft revision"):
        studio.pcb_layout.create_candidate(rev.revision_id, request)


@pytest.mark.parametrize("text", ['(kicad_pcb', '(kicad_pcb)(kicad_pcb)', BOARD.replace('"R1"', '"U1"'),
                                  BOARD.replace('(at 30 20)', '(at nan 20)'), BOARD.replace('(net 1 "SIGNAL")', '(net 1 "OTHER")', 1)])
def test_malformed_ambiguous_or_nonfinite_geometry_rejected(layout, text):
    studio, rev, pcb = layout
    (pcb / "test.kicad_pcb").write_text(text)
    with pytest.raises(StudioError):
        studio.pcb_layout.analyze(rev.revision_id, "pcb/test.kicad_pcb")


def test_empty_board_and_path_escape_rejected(layout):
    studio, rev, pcb = layout
    for path in ["../test.kicad_pcb", str(pcb / "test.kicad_pcb")]:
        with pytest.raises(StudioError):
            studio.pcb_layout.analyze(rev.revision_id, path)
    (pcb / "test.kicad_pcb").write_text('(kicad_pcb)')
    with pytest.raises(StudioError, match="populated"):
        studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))


def test_plan_rejects_duplicate_moves_nonfinite_and_unknown_fields(layout):
    studio, rev, _ = layout
    request = plan(studio, rev)
    move = {"reference": "R1", "x_m": .01, "y_m": .02}
    for updates in [{"moves": [move, move]}, {"moves": [{**move, "x_m": float("nan")}]}, {"approved": True}]:
        with pytest.raises(ValidationError):
            LayoutPlan.model_validate({**request, **updates})


def test_kicad_name_only_nets_and_keepouts(layout):
    studio, rev, pcb = layout
    text = BOARD.replace('(net 1 "SIGNAL")', '(net "SIGNAL")').replace('(net 2 "GND")', '(net "GND")')
    # KiCad 10 name-only pad nets do not need a board-level numeric table.
    text = text.replace('(net "SIGNAL") (net "GND")', '')
    text = text[:-1] + '(zone (keepout (tracks not_allowed)) (polygon (pts (xy 1 2) (xy 3 4) (xy 5 6)))))'
    (pcb / "test.kicad_pcb").write_text(text)
    a = studio.pcb_layout.analyze(rev.revision_id, "pcb/test.kicad_pcb")
    assert {n["name"] for n in a["nets"]} == {"SIGNAL", "GND"}
    assert a["keepouts"][0]["polygons"][0]["points_m"]["vertices"][0] == [.001, .002]


def test_cli_and_desktop_use_same_core(layout, tmp_path, capsys):
    studio, rev, _ = layout
    prefix = ["--root", str(studio.root), "pcb-layout"]
    assert main(prefix + ["analyze", "--revision", str(rev.revision_id), "--path", "pcb/test.kicad_pcb"]) == 0
    analysis = json.loads(capsys.readouterr().out)
    desktop = DesktopService(studio)
    query = {"revision_id": str(rev.revision_id)}
    assert desktop.dispatch("pcb_layout_analyze", {**query, "relative_path": "pcb/test.kicad_pcb"}) == analysis
    assert desktop.dispatch("pcb_layout_files", query)["files"][0]["path"] == "pcb/test.kicad_pcb"
    request = plan(studio, rev)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(request))
    assert main(prefix + ["create", "--revision", str(rev.revision_id), "--request", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    read = desktop.dispatch("pcb_layout_read", {**query, "candidate_id": result["candidate_id"]})
    assert read == result
    assert main(prefix + ["read", "--revision", str(rev.revision_id), "--candidate", result["candidate_id"]]) == 0
    assert json.loads(capsys.readouterr().out) == read
    assert desktop.dispatch("pcb_layout_candidates", query) == [read]
    assert desktop.dispatch("pcb_layout_create", {**query, **request})["integrity"]


def test_concurrent_input_change_leaves_only_unevaluated_incomplete_candidate(layout, monkeypatch):
    import mendex_core.pcb_layout as module
    studio, rev, pcb = layout
    request = plan(studio, rev)
    original_copy = module.shutil.copyfile

    def change_during_copy(src, dest, *args, **kwargs):
        result = original_copy(src, dest, *args, **kwargs)
        if Path(dest).parent.name == "inputs":
            (pcb / "test.kicad_pro").write_text('{"concurrent_change":true}')
        return result

    monkeypatch.setattr(module.shutil, "copyfile", change_during_copy)
    with pytest.raises(StudioError, match="changed"):
        studio.pcb_layout.create_candidate(rev.revision_id, request)
    history = studio.pcb_layout.list_candidates(rev.revision_id)
    assert len(history) == 1 and not history[0]["integrity"]
    assert history[0]["status"] == "NOT_EVALUATED"


def test_removed_manifest_and_unrelated_directories_do_not_hide_candidate(layout):
    studio, rev, _ = layout
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    folder = Path(result["folder"])
    (folder / "manifest.sha256").unlink()
    (folder.parent / "unrelated").mkdir()
    history = studio.pcb_layout.list_candidates(rev.revision_id)
    assert len(history) == 1 and history[0]["candidate_id"] == result["candidate_id"]
    assert not history[0]["integrity"]


def test_nested_board_and_append_only_candidates(layout):
    studio, rev, pcb = layout
    nested = pcb / "sub"
    nested.mkdir()
    (nested / "nested.kicad_pcb").write_text(BOARD)
    a = studio.pcb_layout.analyze(rev.revision_id, "pcb/sub/nested.kicad_pcb")
    request = {"relative_path": a["source"], "expected_context_sha256": a["context_sha256"], "rationale": "Nested fixture"}
    first = studio.pcb_layout.create_candidate(rev.revision_id, request)
    before = {str(p.relative_to(first["folder"])): p.read_bytes() for p in Path(first["folder"]).rglob('*') if p.is_file()}
    second = studio.pcb_layout.create_candidate(rev.revision_id, request)
    assert first["candidate_id"] != second["candidate_id"]
    assert Path(first["board_path"]).read_text() == BOARD
    assert before == {str(p.relative_to(first["folder"])): p.read_bytes() for p in Path(first["folder"]).rglob('*') if p.is_file()}


def test_other_revision_cannot_read_candidate(layout):
    studio, rev, _ = layout
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    other = studio.create_revision(rev.product_id, "NEXT")
    with pytest.raises(StudioError, match="not found"):
        studio.pcb_layout.read_candidate(other.revision_id, result["candidate_id"])


def test_context_mutation_during_analysis_is_a_conflict(layout, monkeypatch):
    import mendex_core.pcb_layout as module
    studio, rev, pcb = layout
    original = module.analyze_tree

    def mutate(tree):
        result = original(tree)
        (pcb / "new.kicad_dru").write_text('(version 1)')
        return result

    monkeypatch.setattr(module, "analyze_tree", mutate)
    with pytest.raises(StudioError, match="changed during analysis"):
        studio.pcb_layout.analyze(rev.revision_id, "pcb/test.kicad_pcb")


def test_checked_in_request_schema_matches_core_contract():
    schema = Path(__file__).resolve().parents[2] / "contracts/pcb-layout/LayoutPlan.schema.json"
    assert json.loads(schema.read_text(encoding="utf-8")) == LayoutPlan.model_json_schema()


def test_preview_and_create_reject_outside_and_overlap_without_writing(layout):
    studio, rev, pcb = layout
    before = {p.name: p.read_bytes() for p in pcb.iterdir()}
    for x, expected in [(.06, "board_containment"), (.01, "courtyard_overlap")]:
        request = plan(studio, rev, [{"reference": "R1", "x_m": x, "y_m": .02}])
        preview = studio.pcb_layout.preview_plan(rev.revision_id, request)
        assert not preview["can_create"]
        assert preview["placement_constraints"]["checks"][expected]["status"] == "ISSUES_FOUND"
        assert not studio.pcb_layout.list_candidates(rev.revision_id)
        with pytest.raises(StudioError, match="Placement constraints"):
            studio.pcb_layout.create_candidate(rev.revision_id, request)
    assert before == {p.name: p.read_bytes() for p in pcb.iterdir()}


def test_missing_courtyard_blocks_moves_but_snapshots_remain_available(layout):
    studio, rev, pcb = layout
    path = pcb / "test.kicad_pcb"
    path.write_text(BOARD.replace('(fp_rect (start -0.5 -0.5) (end 0.5 0.5) (layer "F.CrtYd"))', ''))
    request = plan(studio, rev, [{"reference": "R1", "x_m": .025, "y_m": .02}])
    preview = studio.pcb_layout.preview_plan(rev.revision_id, request)
    assert not preview["can_create"] and preview["placement_constraints"]["status"] == "NOT_EVALUATED"
    with pytest.raises(StudioError, match="NOT_EVALUATED"):
        studio.pcb_layout.create_candidate(rev.revision_id, request)
    result = studio.pcb_layout.create_candidate(rev.revision_id, {**request, "moves": []})
    assert result["integrity"] and result["effective_constraint_status"] == "NOT_EVALUATED"


def test_explicit_fixed_references_are_validated_and_recorded(layout):
    studio, rev, _ = layout
    request = {**plan(studio, rev), "fixed_references": ["R1"]}
    preview = studio.pcb_layout.preview_plan(rev.revision_id, request)
    assert preview["placement_constraints"]["fixed_references"] == ["J1", "R1"]
    result = studio.pcb_layout.create_candidate(rev.revision_id, request)
    assert result["plan"]["fixed_references"] == ["R1"]
    for method in (studio.pcb_layout.preview_plan, studio.pcb_layout.create_candidate):
        with pytest.raises(StudioError, match="fixed component cannot move"):
            method(rev.revision_id, {**request, "moves": [{"reference": "R1", "x_m": .025, "y_m": .02}]})
        with pytest.raises(StudioError, match="Unknown fixed"):
            method(rev.revision_id, {**request, "fixed_references": ["UNKNOWN"]})


def test_keepout_only_zone_allows_clear_move_but_blocks_entry(layout):
    studio, rev, pcb = layout
    path = pcb / "test.kicad_pcb"
    path.write_text(BOARD[:-1] + '''(zone (layer "F.Cu")
       (keepout (footprints not_allowed)) (polygon (pts (xy 20 10) (xy 25 10) (xy 25 30) (xy 20 30)))))''')
    request = plan(studio, rev, [{"reference": "R1", "x_m": .015, "y_m": .02}])
    preview = studio.pcb_layout.preview_plan(rev.revision_id, request)
    assert preview["can_create"] and not preview["analysis"]["copper_counts"]["zone"]
    result = studio.pcb_layout.create_candidate(rev.revision_id, request)
    assert result["effective_constraint_status"] == "CLEAR"
    blocked = {**request, "moves": [{"reference": "R1", "x_m": .023, "y_m": .02}]}
    assert studio.pcb_layout.preview_plan(rev.revision_id, blocked)["placement_constraints"]["checks"]["footprint_keepouts"]["status"] == "ISSUES_FOUND"
    with pytest.raises(StudioError, match="ISSUES_FOUND"):
        studio.pcb_layout.create_candidate(rev.revision_id, blocked)


def test_preview_cli_and_rpc_match_core_and_stale_geometry_is_unevaluated(layout, tmp_path, capsys):
    studio, rev, pcb = layout
    request = plan(studio, rev, [{"reference": "R1", "x_m": .015, "y_m": .02}])
    expected = studio.pcb_layout.preview_plan(rev.revision_id, request)
    desktop = DesktopService(studio)
    assert desktop.dispatch("pcb_layout_preview", {"revision_id": str(rev.revision_id), **request}) == expected
    path = tmp_path / "preview.json"
    path.write_text(json.dumps(request))
    assert main(["--root", str(studio.root), "pcb-layout", "preview", "--revision", str(rev.revision_id), "--request", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    candidate = studio.pcb_layout.create_candidate(rev.revision_id, request)
    (pcb / "changed.kicad_dru").write_text('(version 1)')
    read = studio.pcb_layout.read_candidate(rev.revision_id, candidate["candidate_id"])
    assert read["placement_constraints"]["status"] == "CLEAR"  # historical bytes retained
    assert read["effective_constraint_status"] == "NOT_EVALUATED"


def test_archived_preview_is_read_only_and_disallows_create(layout):
    studio, rev, _ = layout
    request = plan(studio, rev)
    studio.create_revision(rev.product_id, "NEXT")
    preview = studio.pcb_layout.preview_plan(rev.revision_id, request)
    assert not preview["can_create"]
    assert not studio.pcb_layout.list_candidates(rev.revision_id)


def test_moving_a_footprint_cannot_move_the_board_outline_constraint(layout):
    studio, rev, pcb = layout
    path = pcb / "test.kicad_pcb"
    path.write_text(BOARD.replace('(fp_text reference "R1")', '(fp_rect (start -2 -2) (end 2 2) (layer "Edge.Cuts")) (fp_text reference "R1")'))
    request = plan(studio, rev, [{"reference": "R1", "x_m": .015, "y_m": .02}])
    with pytest.raises(StudioError, match="Board-outline component"):
        studio.pcb_layout.preview_plan(rev.revision_id, request)


def test_historical_candidate_without_geometry_report_is_not_silently_qualified(layout):
    from mendex_core.pcb import file_hash
    studio, rev, _ = layout
    result = studio.pcb_layout.create_candidate(rev.revision_id, plan(studio, rev))
    folder = Path(result["folder"])
    metadata_path = folder / "candidate.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.pop("placement_constraints")
    metadata["analysis"].pop("placement_constraints")
    metadata_path.write_text(json.dumps(metadata))
    manifest = folder / "manifest.json"
    artifacts = json.loads(manifest.read_text())
    artifacts["candidate.json"] = file_hash(metadata_path)
    manifest.write_text(json.dumps(artifacts))
    (folder / "manifest.sha256").write_text(file_hash(manifest))
    before = {str(p): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    read = studio.pcb_layout.read_candidate(rev.revision_id, result["candidate_id"])
    assert read["integrity"] and not read["stale"]
    assert read["effective_constraint_status"] == "NOT_EVALUATED"
    assert before == {str(p): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
