"""Regression guards for the independent-audit P0/P1 fixes (docs/independent-audit/16_CRITICAL_GAPS_AND_FIX_PLAN.md).

Each test pins an engineering-integrity rule from AGENTS.md / docs/engineering-rules.md:
evidence is immutable, calculations never run on invented inputs, missing checks are NOT_EVALUATED.
"""
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.models import Requirement
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.models import Category
from mendex_core.service import StudioError, StudioService


def _complete_buck(**overrides):
    values = {"vin_nom": 12.0, "vout": 5.0, "iout": 2.0, "fsw": 500000.0}
    values.update(overrides)
    return [Requirement(parameter=k, target_value=v, unit="") for k, v in values.items()]


# --- Evidence immutability -------------------------------------------------------------

def test_delete_blocked_once_revision_leaves_draft(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("GUARD-1", "Guard", Category.DC_DC, "Engineer")
    service.set_revision_status(product.active_revision_id, "in_review")
    with pytest.raises(StudioError) as exc:
        service.delete_product(product.product_id)
    assert exc.value.code == "DELETE_BLOCKED"
    assert service.get_product(product.product_id).product_id == product.product_id


def test_delete_blocked_when_evidence_recorded(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("GUARD-2", "Guard", Category.DC_DC, "Engineer")
    service.request_simulation(product.active_revision_id, service.registry.list()[0].tool_id)
    with pytest.raises(StudioError, match="recorded evidence"):
        service.delete_product(product.product_id)


def test_mcp_delete_cannot_destroy_evidence(tmp_path):
    server = MendexMCPServer(tmp_path)
    product = server.controller.service.create_product("GUARD-3", "Guard", Category.DC_DC, "Engineer")
    server.controller.service.set_revision_status(product.active_revision_id, "in_review")
    response = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                      "params": {"name": "delete_product", "arguments": {"product_id": str(product.product_id)}}})
    assert response["result"]["isError"] is True
    assert server.controller.service.get_product(product.product_id)


def test_empty_draft_project_can_still_be_deleted(tmp_path):
    service = StudioService(tmp_path)
    product = service.create_product("GUARD-4", "Guard", Category.DC_DC, "Engineer")
    assert service.delete_product(product.product_id) is True


# --- No invented engineering inputs -----------------------------------------------------

@pytest.mark.parametrize("missing", ["vout", "iout", "fsw"])
def test_synthesis_refuses_missing_critical_requirement(missing):
    reqs = [r for r in _complete_buck() if r.parameter != missing]
    with pytest.raises(ValueError, match="Missing required design requirement"):
        CandidateSynthesisEngine.synthesize_candidates(reqs)


@pytest.mark.parametrize("field,value", [("vout", -5.0), ("fsw", 0.0), ("iout", 0.0), ("vin_nom", float("nan"))])
def test_synthesis_rejects_non_physical_inputs(field, value):
    with pytest.raises(ValueError, match="finite positive"):
        CandidateSynthesisEngine.synthesize_candidates(_complete_buck(**{field: value}))


def test_synthesis_honours_input_range_and_ripple():
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V", min_value=18.0, max_value=30.0),
        Requirement(parameter="vout", target_value=5.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
        Requirement(parameter="fsw", target_value=200000.0, unit="Hz"),
        Requirement(parameter="ripple", target_value=0.02, max_value=0.02, unit="V"),
    ]
    buck = next(c for c in CandidateSynthesisEngine.synthesize_candidates(reqs) if "buck" in c.topology.lower())
    # Switch stress derives from the stated 30 V maximum, not an invented +20 % (28.8 V)
    assert buck.calculated_metrics["switch_voltage_stress_v"] == pytest.approx(30.0 * 1.25)
    # C = dIL / (8 fsw dV) with dIL = 0.3 * 2 A and dV = 20 mV  ->  18.75 uF
    c_out = next(c for c in buck.ir_snapshot.components if c.designator in ("C", "C1"))
    assert c_out.value == pytest.approx(0.6 / (8 * 200000.0 * 0.02))


def test_input_range_rejected_when_inconsistent():
    reqs = _complete_buck()
    reqs[0] = Requirement(parameter="vin_nom", target_value=12.0, unit="V", min_value=14.0, max_value=16.0)
    with pytest.raises(ValueError, match="Input range invalid"):
        CandidateSynthesisEngine.synthesize_candidates(reqs)


@pytest.mark.parametrize("calc", ["dowell", "losses", "steinmetz", "flyback"])
def test_calculations_never_use_silent_defaults(tmp_path, calc):
    with pytest.raises(ValueError, match="No defaults are assumed"):
        MendexEngineeringController(tmp_path).run_calculation(calc, {})


# --- Filesystem confinement ------------------------------------------------------------

def test_open_tool_file_confined_to_data_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.net"
    outside.write_text("* outside\n.end\n", encoding="utf-8")
    controller = MendexEngineeringController(root)
    for path in (str(outside), "../outside.net"):
        with pytest.raises(ValueError, match="outside the Mendex data root"):
            controller.open_tool_file("ltspice", path)


def test_simulation_refuses_to_guess_between_netlists(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    ws_id = controller.create_workspace("Ambiguous")["workspace_id"]
    ws_dir = tmp_path / "workspaces" / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "a.net").write_text("* a\n.end\n", encoding="utf-8")
    (ws_dir / "b.net").write_text("* b\n.end\n", encoding="utf-8")
    with pytest.raises(StudioError, match="specify the registered relative path") as exc:
        controller.run_simulation(ws_id, tool="ltspice")
    assert exc.value.code == "CONFLICT"


# --- Honest solver verdicts --------------------------------------------------------------

def test_ltspice_log_parser_flags_floating_nodes_as_errors(tmp_path):
    from mendex_core.design.ltspice_runner import LTspiceRunner
    log = tmp_path / "x.log"
    log.write_bytes("WARNING: Node gate is floating.\nTotal elapsed time: 0.1 seconds.\n".encode("utf-16"))
    errors, warnings = LTspiceRunner._parse_log(log)
    assert errors == ["WARNING: Node gate is floating."]
    assert warnings == []


def test_femm_result_defaults_are_not_evaluated():
    from mendex_core.design.femm_runner import FEMMSimulationResult
    result = FEMMSimulationResult(success=False)
    assert result.summary_verdict == "NOT_EVALUATED" and result.solver_status == "NOT_EVALUATED"


def test_flyback_netlist_drives_its_gate():
    from mendex_core.design.generators.ltspice_generator import LTspiceNetlistGenerator as LTspiceGenerator
    reqs = _complete_buck(vin_nom=48.0, vout=12.0, iout=3.0, fsw=100000.0) + [
        Requirement(parameter="isolation_v", target_value=1500.0, unit="V")]
    flyback = next(c for c in CandidateSynthesisEngine.synthesize_candidates(reqs) if "flyback" in c.topology.lower())
    netlist = LTspiceGenerator.generate_netlist(flyback.ir_snapshot)
    mosfet = next(line for line in netlist.splitlines() if line.startswith("M_"))
    gate_net, source_net = mosfet.split()[2], mosfet.split()[3]
    assert any(line.startswith("V_G") and line.split()[1] == gate_net and line.split()[2] == source_net
               for line in netlist.splitlines())
    assert "D_FW" not in netlist  # buck freewheel diode must not be injected into a flyback
