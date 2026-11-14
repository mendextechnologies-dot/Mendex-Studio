import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import UUID, uuid4

from mendex_core.mcp.server import MendexMCPServer
from mendex_core.desktop.service import DesktopService
import json
from mendex_core.desktop.models import (
    AutoRouteQuery,
    Render3DQuery,
    GerberExportQuery,
    STEPExportQuery,
    ReportGenerateQuery,
    ThermalSizingQuery,
    TopologySynthesizeQuery,
    OperationReceiptQuery,
    IsolationSlotQuery,
    FourLayerPlanesQuery,
    GerberInspectQuery,
    CandidateSelectQuery,
)
from mendex_core.service import StudioService, StudioError
from mendex_core.controller import MendexEngineeringController as StudioController
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService


def _setup_disposable_project(tmp_path: Path):
    """Sets up an isolated, disposable project with valid specification and initial PCB."""
    controller = StudioController(tmp_path)
    proj = controller.create_project("Milestone 4 Delivery Verification", code="M4DELIV", auto_enroll=True)
    studio = controller.service
    from mendex_core.engineering_records.storage import initialize as init_records
    init_records(studio)
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Minimal kicad_pcb layout with outline and GND net
    pcb_content = """(kicad_pcb (version 20240108) (generator pcbnew)
  (general (thickness 1.6))
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (48 "Edge.Cuts" user)
  )
  (net 0 "")
  (net 1 "GND")
  (net 2 "VOUT")
  (gr_rect (start 0 0) (end 50 40) (stroke (width 0.1) (type default)) (layer "Edge.Cuts"))
  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (at 20 20)
    (property "Reference" "R1" (at 0 -1.5 0) (layer "F.SilkS"))
    (property "Value" "10k" (at 0 1.5 0) (layer "F.Fab"))
    (pad "1" smd roundrect (at -0.95 0) (size 1 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (net 1 "GND"))
    (pad "2" smd roundrect (at 0.95 0) (size 1 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (net 2 "VOUT"))
  )
)"""
    pcb_file = pcb_dir / "board.kicad_pcb"
    pcb_file.write_text(pcb_content, encoding="utf-8")

    return controller, studio, product, rev, pcb_dir, pcb_file


# ---------------------------------------------------------------------------
# G18: MCP Boundary Against Unaudited Human Reviews
# ---------------------------------------------------------------------------

def test_g18_mcp_tools_strictly_exclude_review_approval_operations():
    """Verifies that MCP tools catalog strictly omits human-only review and reviewer registration tools."""
    server = MendexMCPServer()
    tool_names = {t["name"] for t in server.tools_schema}

    # Agents MUST NOT be given approval or registration capabilities via tool catalog
    assert "record_human_review" not in tool_names
    assert "register_authorized_reviewer" not in tool_names

    # Read-only review visibility operations should be exposed safely
    assert "get_review_package" in tool_names
    assert "list_authorized_reviewers" in tool_names
    assert "get_stage_review_history" in tool_names


def test_g18_agent_attempt_to_execute_review_approval_is_forbidden(tmp_path: Path):
    """Verifies MCP server dispatch rejects any attempt to execute human approval operations."""
    server = MendexMCPServer(tmp_path)

    # Attempt to call record_human_review via MCP
    with pytest.raises(StudioError) as exc_info:
        server._dispatch_tool("record_human_review", {
            "revision_id": str(uuid4()),
            "stage_id": "requirements",
            "decision": "APPROVED",
        })
    assert exc_info.value.code == "FORBIDDEN"
    assert "cannot execute" in str(exc_info.value)


# ---------------------------------------------------------------------------
# G19: MCP Parity for Copper and New Calculations
# ---------------------------------------------------------------------------

def test_g19_mcp_exposes_copper_tools_and_all_seven_calculators():
    """Verifies MCP tools catalog includes Copper operations and supports all 7 calculation engines."""
    server = MendexMCPServer()
    tool_map = {t["name"]: t for t in server.tools_schema}

    # Verify Copper operations are exposed as tools
    assert "copper_route_pcb" in tool_map
    assert "copper_render_3d" in tool_map
    assert "copper_export_step" in tool_map
    assert "copper_export_gerbers" in tool_map
    assert "copper_drc_check" in tool_map
    assert "calculate_thermal_sizing" in tool_map
    assert "synthesize_topologies" in tool_map

    # Total tool inventory: 69 tools
    assert len(server.tools_schema) >= 69

    # Verify run_engineering_calculations supports all 7 calculators
    calc_tool = tool_map["run_engineering_calculations"]
    supported_calcs = set(calc_tool["inputSchema"]["properties"]["calc_type"]["enum"])
    expected_calcs = {
        "dowell", "losses", "steinmetz", "flyback",
        "semiconductor_thermal", "magnetic_thermal", "ipc2152_thermal"
    }
    assert expected_calcs.issubset(supported_calcs)


def test_g19_mcp_calculation_dispatch_executes_all_new_calculators(tmp_path: Path):
    """Verifies MCP server dispatches all 3 thermal calculators via shared core."""
    server = MendexMCPServer(tmp_path)

    # 1. Semiconductor thermal
    res_semi = server._dispatch_tool("run_engineering_calculations", {
        "calc_type": "semiconductor_thermal",
        "params": {
            "part_number": "IPD036N04L G",
            "p_loss_w": 2.0,
            "t_ambient_c": 30.0,
            "t_j_max_c": 175.0,
            "derating_factor": 0.8,
            "r_th_jc_c_w": 1.8,
            "r_th_cs_c_w": 0.5,
            "r_th_sa_c_w": 15.0,
        },
    })
    assert res_semi["calculation"] == "semiconductor_thermal_sizing"
    assert res_semi["status"] == "PASS_DERATED"
    assert res_semi["t_junction_c"] == pytest.approx(30.0 + 2.0 * (1.8 + 0.5 + 15.0), abs=0.1)

    # 2. Magnetic component thermal
    res_mag = server._dispatch_tool("run_engineering_calculations", {
        "calc_type": "magnetic_thermal",
        "params": {
            "component_name": "L1",
            "p_core_w": 0.5,
            "p_winding_w": 0.7,
            "surface_area_cm2": 25.0,
            "t_ambient_c": 25.0,
            "t_class_max_c": 130.0,
        },
    })
    assert res_mag["calculation"] == "magnetic_component_thermal"
    assert res_mag["delta_t_surface_c"] > 0
    assert res_mag["status"] == "PASS"

    # 3. IPC-2152 copper trace thermal
    res_trace = server._dispatch_tool("run_engineering_calculations", {
        "calc_type": "ipc2152_thermal",
        "params": {
            "current_a": 2.5,
            "target_delta_t_c": 10.0,
            "copper_thickness_oz": 1.0,
        },
    })
    assert res_trace["calculation"] == "ipc2152_trace_thermal_sizing"
    assert res_trace["min_trace_width_mm"] > 0
    assert res_trace["cross_sectional_area_mils2"] > 0


def test_g19_mcp_copper_tools_dispatch_via_desktop_service(tmp_path: Path):
    """Verifies MCP copper tools invoke shared DesktopService methods."""
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_disposable_project(tmp_path)
    server = MendexMCPServer(tmp_path)

    # Test copper_render_3d tool via MCP with mock KiCad render
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    def fake_render(pcb_path, output_png=None, view="iso", width=1200, height=900):
        out = output_png or (pcb_path.parent / f"board_3d_{view}.png")
        out.write_bytes(dummy_png)
        return out

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "render_3d", side_effect=fake_render):
        res = server._dispatch_tool("copper_render_3d", {
            "revision_id": str(rev.revision_id),
            "view": "iso",
        })

    assert res["success"] is True
    assert res["available"] is True
    assert "receipt" in res
    assert res["receipt"]["operation_type"] == "render_3d_pcb"
    assert res["receipt"]["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# G24: Consistent Operation Receipts & Idempotency
# ---------------------------------------------------------------------------

def test_g24_native_operations_return_receipts(tmp_path: Path):
    """Verifies that native operations return identifiable receipts with idempotency keys."""
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_disposable_project(tmp_path)
    desktop = DesktopService(studio)

    # 1. auto_route_pcb receipt
    idemp_key = "idemp_route_123"
    route_res = desktop.auto_route_pcb(AutoRouteQuery(
        revision_id=rev.revision_id,
        pour_ground=True,
        ground_net="GND",
        idempotency_key=idemp_key,
    ))
    assert "receipt" in route_res
    receipt = route_res["receipt"]
    assert receipt["operation_type"] == "auto_route_pcb"
    assert receipt["revision_id"] == str(rev.revision_id)
    assert receipt["idempotency_key"] == idemp_key
    assert "timestamp" in receipt
    assert "operation_id" in receipt

    # 2. export_gerbers receipt (mock kicad)
    def fake_export_gerbers(pcb_path, auto_route=True, check_drc=True, force=False):
        gdir = pcb_path.parent / "gerbers"
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "board-F_Cu.gbr").write_text("G04*", encoding="utf-8")
        return gdir

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "export_gerbers", side_effect=fake_export_gerbers), \
         patch.object(KiCadLifecycleService, "export_drill", return_value=pcb_dir / "gerbers"):
        gerber_res = desktop.export_gerbers(GerberExportQuery(
            revision_id=rev.revision_id,
            auto_route=False,
            check_drc=False,
            idempotency_key="idemp_gerber_456",
        ))
    assert "receipt" in gerber_res
    assert gerber_res["receipt"]["operation_type"] == "export_gerbers"
    assert gerber_res["receipt"]["status"] == "COMPLETED"
    assert gerber_res["receipt"]["idempotency_key"] == "idemp_gerber_456"


# ---------------------------------------------------------------------------
# G21: Windows Installer & CLI Packaging Verification
# ---------------------------------------------------------------------------

def test_g21_installer_script_and_entry_point():
    """Verifies that the standalone Windows installer script exists and entry-point is registered."""
    installer_script = Path("scripts/build_windows_installer.ps1")
    assert installer_script.exists()
    content = installer_script.read_text(encoding="utf-8")
    assert "mendex" in content.lower()
    assert "installer" in content.lower()

    # Verify pyproject.toml CLI entrypoint
    pyproject = Path("pyproject.toml")
    assert pyproject.exists()
    p_content = pyproject.read_text(encoding="utf-8")
    assert 'mendex = "mendex_core.cli:main"' in p_content


# ---------------------------------------------------------------------------
# G19 & G24: End-to-End MCP & CLI Parity + Idempotent Operation Receipts
# ---------------------------------------------------------------------------

def test_g19_mcp_all_new_engineering_tools_dispatch(tmp_path: Path):
    """Verifies MCP server dispatches all newly added tools: inspect_gerber_layers, mill_isolation_slot, setup_4layer_planes, synthesize_topologies, select_candidate, calculate_thermal_sizing, and get_operation_receipt."""
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_disposable_project(tmp_path)
    server = MendexMCPServer(tmp_path)

    # 1. mill_isolation_slot
    res_mill = server._dispatch_tool("mill_isolation_slot", {
        "revision_id": str(rev.revision_id),
        "slot_width": 2.5,
        "idempotency_key": "idemp_mcp_mill_1",
    })
    assert res_mill["success"] is True
    assert "slot_geometry" in res_mill
    assert "receipt" in res_mill
    assert res_mill["receipt"]["operation_type"] == "mill_isolation_slot"
    assert res_mill["receipt"]["idempotency_key"] == "idemp_mcp_mill_1"

    # 2. setup_4layer_planes
    res_4layer = server._dispatch_tool("setup_4layer_planes", {
        "revision_id": str(rev.revision_id),
        "gnd_net": "GND",
        "pwr_net": "VOUT",
        "idempotency_key": "idemp_mcp_4layer_1",
    })
    assert res_4layer["success"] is True
    assert res_4layer["in1_gnd_poured"] is True
    assert res_4layer["in2_pwr_poured"] is True
    assert "receipt" in res_4layer
    assert res_4layer["receipt"]["operation_type"] == "setup_4layer_planes"

    # 3. synthesize_topologies
    res_synth = server._dispatch_tool("synthesize_topologies", {
        "revision_id": str(rev.revision_id),
        "idempotency_key": "idemp_mcp_synth_1",
    })
    assert res_synth["success"] is True
    assert "candidates" in res_synth
    assert res_synth["count"] > 0
    candidate_id = res_synth["candidates"][0]["id"]

    # 4. select_candidate
    res_select = server._dispatch_tool("select_candidate", {
        "revision_id": str(rev.revision_id),
        "candidate_id": candidate_id,
        "auto_export_kicad": False,
    })
    assert res_select["success"] is True
    assert res_select["selected_candidate_id"] == candidate_id

    # 5. calculate_thermal_sizing
    res_therm = server._dispatch_tool("calculate_thermal_sizing", {
        "revision_id": str(rev.revision_id),
        "ambient_temp_c": 35.0,
        "p_switch_loss_w": 1.5,
        "derating_factor": 0.85,
        "idempotency_key": "idemp_mcp_therm_1",
    })
    assert res_therm["success"] is True
    assert "summary" in res_therm
    assert res_therm["ambient_temp_c"] == 35.0

    # 6. inspect_gerber_layers
    res_insp = server._dispatch_tool("inspect_gerber_layers", {
        "revision_id": str(rev.revision_id),
        "auto_export": False,
    })
    assert "board_name" in res_insp
    assert "layers" in res_insp

    # 7. get_operation_receipt
    res_rec = server._dispatch_tool("get_operation_receipt", {
        "idempotency_key": "idemp_mcp_mill_1",
        "revision_id": str(rev.revision_id),
    })
    assert res_rec["found"] is True
    assert res_rec["receipt"]["operation_type"] == "mill_isolation_slot"
    assert res_rec["receipt"]["idempotency_key"] == "idemp_mcp_mill_1"


def test_g19_cli_commands_parity(tmp_path: Path, capsys):
    """Verifies that all new engineering capabilities can be invoked directly from CLI with parity."""
    from mendex_core.cli import main
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_disposable_project(tmp_path)

    # 1. pcb mill-slot
    main(["--root", str(tmp_path), "pcb", "mill-slot", "--revision", str(rev.revision_id), "--width", "2.0", "--idempotency-key", "cli_mill_1"])
    out = capsys.readouterr().out
    res_mill = json.loads(out)
    assert res_mill["success"] is True
    assert res_mill["slot_geometry"]["width_mm"] == 2.0

    # 2. pcb setup-4layer
    main(["--root", str(tmp_path), "pcb", "setup-4layer", "--revision", str(rev.revision_id), "--gnd-net", "GND", "--pwr-net", "VOUT"])
    out = capsys.readouterr().out
    res_4layer = json.loads(out)
    assert res_4layer["success"] is True

    # 3. pcb inspect-gerber
    main(["--root", str(tmp_path), "pcb", "inspect-gerber", "--revision", str(rev.revision_id), "--no-export"])
    out = capsys.readouterr().out
    res_insp = json.loads(out)
    assert "layers" in res_insp

    # 4. thermal
    main(["--root", str(tmp_path), "thermal", "--revision", str(rev.revision_id), "--tamb", "30", "--p-loss", "2.0"])
    out = capsys.readouterr().out
    res_therm = json.loads(out)
    assert res_therm["success"] is True
    assert res_therm["ambient_temp_c"] == 30.0

    # 5. topologies synthesize
    main(["--root", str(tmp_path), "topologies", "synthesize", "--revision", str(rev.revision_id)])
    out = capsys.readouterr().out
    res_synth = json.loads(out)
    assert res_synth["success"] is True
    cand_id = res_synth["candidates"][0]["id"]

    # 6. topologies select
    main(["--root", str(tmp_path), "topologies", "select", "--revision", str(rev.revision_id), "--candidate", cand_id, "--no-export"])
    out = capsys.readouterr().out
    res_select = json.loads(out)
    assert res_select["success"] is True
    assert res_select["selected_candidate_id"] == cand_id

    # 7. receipt
    main(["--root", str(tmp_path), "receipt", "--key", "cli_mill_1"])
    captured = capsys.readouterr()
    if not captured.out.strip():
        raise RuntimeError(f"CLI receipt produced no stdout! STDERR: {captured.err}")
    res_rec = json.loads(captured.out)
    assert res_rec["found"] is True
    assert res_rec["receipt"]["operation_type"] == "mill_isolation_slot"


def test_g24_idempotent_receipt_lookup_and_deduplication(tmp_path: Path):
    """Verifies that calling operations twice with the same idempotency key returns the cached receipt without re-execution."""
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_disposable_project(tmp_path)
    desktop = DesktopService(studio)

    idemp_key = "idemp_test_repeat_999"

    # First call
    q1 = ThermalSizingQuery(
        revision_id=rev.revision_id,
        ambient_temp_c=25.0,
        p_switch_loss_w=1.2,
        idempotency_key=idemp_key,
    )
    res1 = desktop.calculate_thermal_sizing(q1)
    assert res1["success"] is True
    op_id = res1["receipt"]["operation_id"]

    # Second call with same idempotency key
    res2 = desktop.calculate_thermal_sizing(q1)
    assert res2["cached_receipt"] is True
    assert res2["receipt"]["operation_id"] == op_id
    assert res2["receipt"]["idempotency_key"] == idemp_key

    # Query receipt directly by idempotency_key
    q_rec = OperationReceiptQuery(idempotency_key=idemp_key)
    lookup_res = desktop.get_operation_receipt(q_rec)
    assert lookup_res["found"] is True
    assert lookup_res["receipt"]["operation_id"] == op_id

    # Query receipt directly by operation_id
    q_rec2 = OperationReceiptQuery(operation_id=UUID(op_id))
    lookup_res2 = desktop.get_operation_receipt(q_rec2)
    assert lookup_res2["found"] is True
    assert lookup_res2["receipt"]["idempotency_key"] == idemp_key
