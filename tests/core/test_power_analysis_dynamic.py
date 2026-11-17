"""Dynamic voltage interpolation and revision-component bindings; synthetic data only."""
import copy
import json

import pytest
from pydantic import ValidationError

from mendex_core.desktop.service import DesktopService
from mendex_core.power_analysis import analyze_power_thermal, import_loss_csv
from mendex_core.service import StudioError, StudioService
from test_power_thermal_analysis import inputs


def voltage_inputs():
    data = inputs()
    grid = data["devices"][0]["loss_points"]
    data["devices"][0]["loss_points"] = [dict(p, voltage_v=v, e_on_j=p["e_on_j"] * v / 100,
        e_off_j=p["e_off_j"] * v / 100) for v in (100.0, 200.0) for p in grid]
    return data


def test_voltage_changes_losses_and_feedback_without_voltage_scaling_assumptions():
    request = voltage_inputs()
    request["operating_point"]["voltage_v"] = 150.0
    point = analyze_power_thermal(request)["devices"][0]["operating_point"]
    assert point["conduction_w"] == pytest.approx(5)
    assert point["switching_w"] == pytest.approx(3)
    assert point["junction_temp_c"] == pytest.approx(41)
    request["operating_point"]["voltage_v"] = 200.0
    assert analyze_power_thermal(request)["devices"][0]["operating_point"]["switching_w"] == pytest.approx(4)


def test_trilinear_voltage_current_temperature_against_analytical_balance():
    request = voltage_inputs()
    for p in request["devices"][0]["loss_points"]:
        p["on_voltage_v"] *= 1 + 0.002 * p["junction_temp_c"]
        p["e_on_j"] *= 1 + 0.001 * p["junction_temp_c"]
        p["e_off_j"] *= 1 + 0.001 * p["junction_temp_c"]
    request["operating_point"].update(voltage_v=150.0, current_a=5.0)
    assert analyze_power_thermal(request)["devices"][0]["operating_point"]["junction_temp_c"] == pytest.approx(30.5 / 0.992)


@pytest.mark.parametrize("voltage", [99.0, 201.0])
def test_voltage_extrapolation_is_not_evaluated(voltage):
    request = voltage_inputs(); request["operating_point"]["voltage_v"] = voltage
    assert analyze_power_thermal(request)["devices"][0]["operating_point"]["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("change", ["incomplete", "mixed", "duplicate"])
def test_invalid_three_dimensional_tables_rejected(change):
    request = voltage_inputs(); grid = request["devices"][0]["loss_points"]
    if change == "incomplete": grid.pop()
    if change == "mixed": grid[0].pop("voltage_v")
    if change == "duplicate": grid.append(copy.deepcopy(grid[0]))
    with pytest.raises(ValidationError): analyze_power_thermal(request)


def test_voltage_csv_and_legacy_csv_are_both_supported():
    text = "voltage_v,current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j\n100,10,25,1,0.00001,0.00002\n"
    assert import_loss_csv(text)[0]["voltage_v"] == 100
    assert import_loss_csv(text.replace("voltage_v,", "", 1).replace("100,10,", "10,"))[0]["voltage_v"] is None


@pytest.fixture
def bound(tmp_path):
    studio = StudioService(tmp_path)
    product = studio.create_product("DYNAMIC-POWER", "Isolated power fixture", "pcb", "Software test")
    revision = studio.get_revision(product.active_revision_id)
    bom = studio.workspace_path(revision) / "bom" / "bom.json"
    bom.parent.mkdir(parents=True, exist_ok=True)
    def write(mpn):
        bom.write_text(json.dumps([{"designator": "Q1", "mpn": mpn, "manufacturer": "Synthetic"}]), encoding="utf-8")
    write("MODEL-A")
    request = inputs()
    model = request["devices"][0]
    model.update(mpn="MODEL-A", manufacturer="Synthetic", component_reference="Q1")
    replacement = copy.deepcopy(model)
    replacement.update(name="SYNTHETIC-B", mpn="MODEL-B", component_reference=None)
    for p in replacement["loss_points"]:
        p["e_on_j"] *= 2; p["e_off_j"] *= 2
    request["model_library"] = [replacement]
    return studio, revision, request, write, bom


def test_bom_replacement_automatically_selects_exact_sourced_model(bound):
    studio, revision, request, write, _ = bound
    first = studio.analyze_power_thermal(request, revision.revision_id)
    write("MODEL-B")
    current = studio.analyze_power_thermal(request, revision.revision_id)
    assert current["inputs"]["devices"][0]["mpn"] == "MODEL-B"
    assert current["devices"][0]["name"] == "Q1: MODEL-B"
    assert first["devices"][0]["operating_point"]["device_loss_w"] == pytest.approx(7)
    assert current["devices"][0]["operating_point"]["device_loss_w"] == pytest.approx(9)
    assert first["component_context"]["component_hash"] != current["component_context"]["component_hash"]
    assert DesktopService(studio).dispatch("power_analysis_context", {"revision_id": str(revision.revision_id)})["components"][0]["mpn"] == "MODEL-B"


def test_stale_context_cannot_be_recorded_or_used_for_preview(bound):
    studio, revision, request, write, _ = bound
    prior = studio.analyze_power_thermal(request, revision.revision_id)
    write("MODEL-B")
    with pytest.raises(StudioError, match="Components changed"):
        studio.analyze_power_thermal(prior["inputs"], revision.revision_id)


def test_missing_replacement_never_reuses_old_model(bound):
    studio, revision, request, write, _ = bound
    write("UNMODELED-PART")
    row = studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]
    assert row["operating_point"]["status"] == "NOT_EVALUATED"
    assert "old model is not reused" in row["operating_point"]["reason"]
    assert not row["load_sweep"] and not row["thermal_impedance"]


def test_removed_or_malformed_component_data_invalidates_binding(bound):
    studio, revision, request, _, bom = bound
    bom.unlink()
    assert studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]["operating_point"]["status"] == "NOT_EVALUATED"
    bom.write_text("{bad", encoding="utf-8")
    assert studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]["operating_point"]["status"] == "NOT_EVALUATED"


def test_standalone_bound_calculation_cannot_claim_current_component(bound):
    _, _, request, _, _ = bound
    assert analyze_power_thermal(request)["devices"][0]["operating_point"]["status"] == "NOT_EVALUATED"


def test_foreign_design_is_excluded_and_conflicting_saved_design_blocks(bound):
    from mendex_core.design.ir import DesignIntermediateRepresentation, IRComponent, ComponentType
    from mendex_core.design.models import DesignRevision, EngineeringDesign
    studio, revision, request, _, _ = bound
    foreign = studio.create_product("FOREIGN-DYNAMIC", "Foreign fixture", "pcb", "Test")
    ir = DesignIntermediateRepresentation(components=[IRComponent(designator="Q1", name="Synthetic B", type=ComponentType.SWITCH_MOSFET, mpn="MODEL-B", manufacturer="Synthetic")])
    design = EngineeringDesign(workspace_id=str(foreign.active_revision_id), product_id=str(foreign.product_id), core_revision_id=str(foreign.active_revision_id),
                               revisions=[DesignRevision(design_id="fixture", ir=ir)])
    studio.design._persist(design)
    assert studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]["operating_point"]["status"] == "COMPUTED"
    design.product_id = str(revision.product_id); design.core_revision_id = str(revision.revision_id)
    studio.design._persist(design)
    row = studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]
    assert row["operating_point"]["status"] == "NOT_EVALUATED"
    assert "inconsistent" in row["operating_point"]["reason"]


def test_ambiguous_replacement_is_not_arbitrarily_selected(bound):
    studio, revision, request, write, _ = bound
    another = copy.deepcopy(request["model_library"][0]); another["name"] = "DIFFERENT-DATASET"
    request["model_library"].append(another)
    write("MODEL-B")
    point = studio.analyze_power_thermal(request, revision.revision_id)["devices"][0]["operating_point"]
    assert point["status"] == "NOT_EVALUATED" and "ambiguous" in point["reason"]


def test_canonical_embedded_model_updates_even_when_part_number_is_unchanged(bound):
    studio, revision, request, _, bom = bound
    model = copy.deepcopy(request["devices"][0])
    model["name"] = "UPDATED-CANONICAL-MODEL"
    for p in model["loss_points"]:
        p["e_on_j"] *= 3; p["e_off_j"] *= 3
    bom.write_text(json.dumps([{"designator": "Q1", "mpn": "MODEL-A", "manufacturer": "Synthetic", "power_thermal_model": model}]), encoding="utf-8")
    result = studio.analyze_power_thermal(request, revision.revision_id)
    assert result["devices"][0]["name"] == "Q1: MODEL-A"
    assert result["devices"][0]["operating_point"]["switching_w"] == pytest.approx(6)


def test_component_changes_mark_history_stale_and_reject_recording_old_preview(bound):
    from mendex_core.evidence import specification_hash
    studio, revision, request, write, _ = bound
    definition = {"id": "binding_fixture", "version": "1.0.0", "name": "Software only", "stages": [
        {"id": "work", "name": "Recorded work", "purpose": "Software only", "review_required": False,
         "criteria": [{"id": "context", "description": "Process only", "kind": "project_context"}]}]}
    studio.engineering_lifecycle.register_definition(definition, "Software fixture")
    base = {"revision_id": str(revision.revision_id), "source": "Synthetic test", "reason": "Software only"}
    studio.engineering_lifecycle.enroll({**base, "definition_id": "binding_fixture", "version": "1.0.0", "idempotency_key": "enroll"})
    studio.engineering_lifecycle.apply({**base, "stage_id": "work", "action": "start", "idempotency_key": "start"})
    preview = studio.analyze_power_thermal(request, revision.revision_id)
    record_request = {**base, "stage_id": "work", "idempotency_key": "record", "expected_input_hash": specification_hash(revision.specification),
                      "calculation": "power_thermal", "parameters": preview["inputs"], "assumptions": request["assumptions"]}
    record = studio.engineering_records.run_calculation(record_request)
    before = studio.engineering_records.get_record(record["record_id"])
    assert not before["stale"]
    write("MODEL-B")
    after = studio.engineering_records.get_record(record["record_id"])
    assert after["stale"] and after["component_context_stale"] and after["effective_status"] == "NOT_EVALUATED"
    assert before["result"] == after["result"]  # Historical raw result stays unchanged.
    with pytest.raises(StudioError, match="Components changed"):
        studio.engineering_records.run_calculation({**record_request, "idempotency_key": "stale-record"})


def test_scoped_mcp_and_cli_use_current_revision_bindings(bound, capsys):
    from mendex_core.cli import main
    from mendex_core.mcp.server import MendexMCPServer
    studio, revision, request, write, bom = bound
    write("MODEL-B")
    mcp = MendexMCPServer(studio.root)
    context = mcp.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "get_power_analysis_context", "arguments": {"revision_id": str(revision.revision_id)}}})
    assert not context.get("error") and not context["result"].get("isError")
    assert 'MODEL-B' in json.dumps(context)
    response = mcp.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "run_engineering_calculations", "arguments": {"calc_type": "power_thermal", "params": request, "revision_id": str(revision.revision_id)}}})
    assert not response.get("error") and not response["result"].get("isError")
    result = json.loads(response["result"]["content"][0]["text"])
    assert result["inputs"]["devices"][0]["mpn"] == "MODEL-B"
    assert main(["--root", str(studio.root), "power-components", str(revision.revision_id)]) == 0
    assert json.loads(capsys.readouterr().out)["components"][0]["mpn"] == "MODEL-B"
    path = bom.parent / "analysis-inputs.json"; path.write_text(json.dumps(request), encoding="utf-8")
    assert main(["--root", str(studio.root), "power-analysis", str(path), "--revision", str(revision.revision_id)]) == 0
    assert json.loads(capsys.readouterr().out)["inputs"]["devices"][0]["mpn"] == "MODEL-B"


def test_same_part_at_two_references_has_stable_distinct_result_labels(bound):
    studio, revision, request, _, bom = bound
    bom.write_text(json.dumps([{"designator": "Q1,Q2", "mpn": "MODEL-A", "manufacturer": "Synthetic"}]), encoding="utf-8")
    second = copy.deepcopy(request["devices"][0]); second.update(name="SECOND-POSITION", component_reference="Q2")
    request["devices"].append(second)
    result = studio.analyze_power_thermal(request, revision.revision_id)
    assert [d["name"] for d in result["devices"]] == ["Q1: MODEL-A", "Q2: MODEL-A"]
    repeated = studio.analyze_power_thermal(result["inputs"], revision.revision_id)
    assert result["request_sha256"] == repeated["request_sha256"]
