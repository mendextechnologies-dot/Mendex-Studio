"""Synthetic analytical benchmarks, not semiconductor qualification or live product data."""
import copy
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mendex_core.power_analysis import AnalysisRequest, analyze_power_thermal, import_loss_csv
from mendex_core.service import StudioError, StudioService


def inputs():
    return {
        "assumptions": ["Synthetic independent rectangular-current switch, complete-path RC; software benchmark only"],
        "devices": [{"name": "SYNTHETIC-NOT-A-PART", "source": "Analytical software benchmark, not a datasheet",
                     "gate_conditions": "Synthetic fixed gate conditions", "loss_scope": "Conduction and Eon/Eoff only; no recovery, gate or Coss losses",
                     "reference_voltage_v": 100.0, "frequency_min_hz": 1000.0, "frequency_max_hz": 1000000.0,
                     "max_junction_temp_c": 150.0, "boundary": "ambient", "thermal_source": "Synthetic complete junction-ambient one-pole model",
                     "foster": [{"resistance_k_w": 2.0, "tau_s": 1.0}],
                     "loss_points": [{"current_a": i, "junction_temp_c": t, "on_voltage_v": i / 10,
                                      "e_on_j": i / 10 * 1e-5, "e_off_j": i / 10 * 1e-5}
                                     for i in (0.0, 10.0, 20.0) for t in (0.0, 150.0)]}],
        "operating_point": {"voltage_v": 100.0, "gate_conditions": "Synthetic fixed gate conditions", "current_a": 10.0, "output_power_w": 100.0, "duty_cycle": 0.5,
                            "frequency_hz": 100000.0, "boundary_temp_c": 25.0, "other_losses_w": 1.0, "quantity": 2},
        "sweeps": {"load_factors": [0.5, 1.0, 3.0], "frequencies_hz": [50000.0, 100000.0, 200000.0], "boundary_temperatures_c": [25.0, 50.0]},
        "load_cycle": [{"duration_s": 1.0, "current_a": 10.0, "output_power_w": 100.0,
                        "frequency_hz": 100000.0, "duty_cycle": 0.5, "other_losses_w": 1.0}],
    }


def test_steady_benchmark_losses_efficiency_and_ranges():
    report = analyze_power_thermal(inputs())
    point = report["devices"][0]["operating_point"]
    assert point["conduction_w"] == pytest.approx(5)
    assert point["switching_w"] == pytest.approx(2)
    assert point["junction_temp_c"] == pytest.approx(39)
    assert point["represented_system_loss_w"] == pytest.approx(15)
    assert point["efficiency_pct"] == pytest.approx(10000 / 115)
    assert report["evaluation_status"] == "NOT_EVALUATED"
    sweep = report["devices"][0]["load_sweep"]
    assert sweep[0]["device_loss_w"] == pytest.approx(2.25)
    assert sweep[-1]["status"] == "NOT_EVALUATED"
    assert "device_loss_w" not in sweep[-1]  # No fake zero or extrapolated graph point.


def test_foster_step_matches_closed_form_and_time_endpoint():
    report = analyze_power_thermal(inputs())["devices"][0]
    points = report["load_cycle"]["points"]
    assert points[0]["junction_temp_c"] == 25
    assert points[-1]["time_s"] == pytest.approx(1)
    assert points[-1]["junction_temp_c"] == pytest.approx(25 + 14 * (1 - math.exp(-1)))
    z = report["thermal_impedance"]
    assert z[0]["impedance_k_w"] == 0
    assert all(a["impedance_k_w"] <= b["impedance_k_w"] for a, b in zip(z, z[1:]))


def test_temperature_dependent_loss_feedback_is_solved():
    req = inputs()
    # Von = I * 0.1 * (1 + 0.002*T). Pcond=5+0.01*T, Psw=2.
    for p in req["devices"][0]["loss_points"]:
        p["on_voltage_v"] *= 1 + 0.002 * p["junction_temp_c"]
    point = analyze_power_thermal(req)["devices"][0]["operating_point"]
    assert point["junction_temp_c"] == pytest.approx(39 / 0.98)


def test_gate_mismatch_and_thermal_runaway_never_create_curves():
    req = inputs()
    req["operating_point"]["gate_conditions"] = "Different driver and resistance"
    d = analyze_power_thermal(req)["devices"][0]
    assert d["operating_point"]["status"] == "NOT_EVALUATED"
    assert "gate" in d["operating_point"]["reason"]
    req = inputs()
    for p in req["devices"][0]["loss_points"]:
        p["on_voltage_v"] *= 1 + 0.2 * p["junction_temp_c"]
    assert analyze_power_thermal(req)["devices"][0]["operating_point"]["status"] == "NOT_EVALUATED"


def test_cold_start_and_repeated_profile_not_falsely_periodic():
    req = inputs(); req["repeat_cycles"] = 2
    result = analyze_power_thermal(req)["devices"][0]["load_cycle"]
    assert result["points"][-1]["time_s"] == pytest.approx(2)
    assert result["points"][-1]["junction_temp_c"] == pytest.approx(25 + 14 * (1 - math.exp(-2)))
    assert "not periodic" in result["note"]


@pytest.mark.parametrize("change", ["voltage", "frequency", "hot", "no_root"])
def test_unsupported_points_are_unevaluated(change):
    req = inputs()
    if change == "voltage": req["operating_point"]["voltage_v"] = 99.0
    if change == "frequency":
        req["operating_point"]["frequency_hz"] = 2e6
        req["load_cycle"][0]["frequency_hz"] = 2e6
    if change == "hot": req["operating_point"]["boundary_temp_c"] = 160.0
    if change == "no_root": req["devices"][0]["foster"][0]["resistance_k_w"] = 1000.0
    d = analyze_power_thermal(req)["devices"][0]
    assert d["operating_point"]["status"] == "NOT_EVALUATED"
    assert d["load_cycle"]["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("change", ["nan", "infinity", "negative", "no_source", "duplicate", "missing_grid", "unknown_field", "too_many", "budget", "boolean"])
def test_invalid_inputs_rejected(change):
    req = inputs(); d = req["devices"][0]
    if change == "nan": req["operating_point"]["current_a"] = float("nan")
    if change == "infinity": d["foster"][0]["tau_s"] = float("inf")
    if change == "negative": d["loss_points"][0]["e_on_j"] = -1.0
    if change == "no_source": d["source"] = " "
    if change == "duplicate": d["loss_points"].append(copy.deepcopy(d["loss_points"][0]))
    if change == "missing_grid": d["loss_points"].pop()
    if change == "unknown_field": req["compliant"] = True
    if change == "too_many": req["devices"] *= 6
    if change == "budget": req["load_cycle"] *= 200; req["repeat_cycles"] = 10
    if change == "boolean": req["operating_point"]["current_a"] = True
    with pytest.raises(ValidationError): analyze_power_thermal(req)


def test_device_comparison_preserves_separate_sources_and_models():
    req = inputs(); second = copy.deepcopy(req["devices"][0]); second["name"] = "SECOND-SYNTHETIC"
    for p in second["loss_points"]: p["e_on_j"] *= 2; p["e_off_j"] *= 2
    req["devices"].append(second)
    out = analyze_power_thermal(req)["devices"]
    assert out[0]["operating_point"]["switching_w"] == pytest.approx(2)
    assert out[1]["operating_point"]["switching_w"] == pytest.approx(4)


def test_fatigue_explicit_source_conditions_and_missing_models():
    req = inputs()
    assert analyze_power_thermal(req)["devices"][0]["lifetime"]["status"] == "NOT_EVALUATED"
    req["devices"][0]["fatigue"] = {"source": "Synthetic N=4e7/deltaT^2 benchmark only", "conditions": "Synthetic package/process",
        "mean_temp_min_c": 25.0, "mean_temp_max_c": 100.0, "heating_time_min_s": 1.0, "heating_time_max_s": 100.0,
        "curve": [{"delta_t_k": 20.0, "cycles_to_failure": 100000.0}, {"delta_t_k": 80.0, "cycles_to_failure": 6250.0}]}
    req["thermal_cycles"] = [{"delta_t_k": 40.0, "mean_temp_c": 50.0, "heating_time_s": 10.0, "count": 250.0, "conditions": "Synthetic package/process"}]
    with pytest.raises(ValidationError): analyze_power_thermal(req)
    req["cycle_count_source"] = "Externally supplied synthetic counted cycles"
    life = analyze_power_thermal(req)["devices"][0]["lifetime"]
    assert life["damage_fraction"] == pytest.approx(0.01)
    assert life["equivalent_profile_blocks_to_damage_one"] == pytest.approx(100)
    req["thermal_cycles"][0]["conditions"] = "Different package"
    assert analyze_power_thermal(req)["devices"][0]["lifetime"]["status"] == "NOT_EVALUATED"


def test_csv_strict_si_import():
    text = "current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j\n10,25,1,0.00001,0.00002\n"
    assert import_loss_csv(text)[0]["current_a"] == 10
    for malformed in ("", text.replace("current_a", "current_ma"), text.replace(",25,", ",nan,"), text + "10,25,1,2,3,4\n"):
        with pytest.raises(ValueError): import_loss_csv(malformed)


def test_context_cli_desktop_and_mcp_share_same_engine(tmp_path, capsys):
    from mendex_core.cli import main
    from mendex_core.desktop.service import DesktopService
    from mendex_core.mcp.server import MendexMCPServer
    studio = StudioService(tmp_path)
    product = studio.create_product("POWER-TEST", "Power analytical fixture", "dc_dc_converter", "Software fixture")
    rid = product.active_revision_id
    expected = studio.analyze_power_thermal(inputs(), rid)
    actual = DesktopService(studio).dispatch("analyze_power_thermal", {"revision_id": str(rid), "parameters": inputs()})
    assert actual == expected
    mcp = MendexMCPServer(tmp_path)
    assert "power_thermal" in json.dumps(mcp.tools_schema)
    response = mcp.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                 "params": {"name": "run_engineering_calculations", "arguments": {"calc_type": "power_thermal", "params": inputs()}}})
    assert not response.get("error"), response
    assert not response["result"].get("isError"), response
    assert expected["request_sha256"] in json.dumps(response)
    from mendex_core.controller import MendexEngineeringController
    assert MendexEngineeringController(service=studio).run_calculation("power_thermal", inputs())["request_sha256"] == expected["request_sha256"]
    path = tmp_path / "inputs.json"; path.write_text(json.dumps(inputs()), encoding="utf-8")
    assert main(["--root", str(tmp_path), "power-analysis", str(path), "--revision", str(rid)]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    with pytest.raises(StudioError): studio.analyze_power_thermal(inputs(), uuid4())


def test_guarded_record_persistence_and_archived_rejection(tmp_path):
    from mendex_core.evidence import specification_hash
    studio = StudioService(tmp_path)
    product = studio.create_product("POWER-RECORD", "Power record fixture", "pcb", "Software fixture")
    rid = product.active_revision_id
    definition = {"id": "power_fixture", "version": "1.0.0", "name": "Software only", "stages": [
        {"id": "work", "name": "Recorded work", "purpose": "Test records", "review_required": False,
         "criteria": [{"id": "context", "description": "Process only", "kind": "project_context"}]}]}
    studio.engineering_lifecycle.register_definition(definition, "Software fixture")
    common = {"revision_id": str(rid), "source": "Software fixture", "reason": "Software only"}
    studio.engineering_lifecycle.enroll({**common, "definition_id": "power_fixture", "version": "1.0.0", "idempotency_key": "enroll"})
    studio.engineering_lifecycle.apply({**common, "stage_id": "work", "action": "start", "idempotency_key": "start"})
    req = {**common, "stage_id": "work", "expected_input_hash": specification_hash(studio.get_revision(rid).specification),
           "idempotency_key": "analysis-1", "calculation": "power_thermal", "parameters": inputs(), "assumptions": ["Synthetic software only"]}
    record = studio.engineering_records.run_calculation(req)
    assert studio.engineering_records.run_calculation(req) == record
    assert "power_thermal_analysis" in json.dumps(record)
    from mendex_core.desktop.service import DesktopService
    assert DesktopService(studio).dispatch("record_power_thermal", req) == record
    studio.create_revision(product.product_id, "R002")
    with pytest.raises(StudioError): studio.engineering_records.run_calculation({**req, "idempotency_key": "archived"})
    with pytest.raises(StudioError): DesktopService(studio).dispatch("record_power_thermal", {**req, "idempotency_key": "archived-desktop"})


def test_actual_cli_subprocess(tmp_path):
    path = tmp_path / "inputs.json"; path.write_text(json.dumps(inputs()), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    process = subprocess.run([sys.executable, "-m", "mendex_core.cli", "--root", str(tmp_path / "isolated"), "power-analysis", str(path)],
                             capture_output=True, text=True, env=env, timeout=30)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["devices"][0]["operating_point"]["junction_temp_c"] == pytest.approx(39)


def test_actual_mcp_and_desktop_stdio_subprocesses(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    request = {"jsonrpc": "2.0", "id": 42, "method": "tools/call", "params": {
        "name": "run_engineering_calculations", "arguments": {"calc_type": "power_thermal", "params": inputs()}}}
    mcp = subprocess.run([sys.executable, "-m", "mendex_core.mcp", "--root", str(tmp_path / "mcp")], input=json.dumps(request) + "\n",
                         capture_output=True, text=True, env=env, timeout=30)
    assert mcp.returncode == 0, mcp.stderr
    response = json.loads(mcp.stdout)
    assert response["id"] == 42 and not response.get("error")
    assert not response["result"].get("isError")
    assert analyze_power_thermal(inputs())["request_sha256"] in json.dumps(response)
    studio = StudioService(tmp_path / "desktop")
    p = studio.create_product("STDIO-POWER", "Isolated stdio fixture", "pcb", "Software fixture")
    query = {"protocol_version": "3.1.0", "id": "power-stdio", "method": "analyze_power_thermal",
             "params": {"revision_id": str(p.active_revision_id), "parameters": inputs()}}
    process = subprocess.run([sys.executable, "-m", "mendex_core.desktop", "--root", str(tmp_path / "desktop")],
                             input=json.dumps(query) + "\n", capture_output=True, text=True, env=env, timeout=30)
    assert process.returncode == 0, process.stderr
    output = json.loads(process.stdout)
    assert output["id"] == "power-stdio" and not output.get("error")
    assert output["result"]["devices"][0]["operating_point"]["junction_temp_c"] == pytest.approx(39)
