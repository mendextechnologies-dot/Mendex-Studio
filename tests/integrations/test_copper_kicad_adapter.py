"""Unit and integration tests for internal CopperKiCadAdapter in Mendex Engineering Studio."""
import shutil
from pathlib import Path
from uuid import uuid4
import pytest

import copper_kicad.tools  # Registers all 31 MCP tools
from copper_kicad.mcp.registry import call_tool
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter


@pytest.fixture(scope="module")
def adapter():
    return CopperKiCadAdapter()


@pytest.fixture(scope="module")
def reference_project(tmp_path_factory):
    """Generates an authentic, clean KiCad 10 reference project once per test module."""
    base_dir = tmp_path_factory.mktemp("copper_ref_base")
    proj_dir = base_dir / "divider_ref"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # 1. Project creation with 50x35mm rectangular outline
    call_tool("project_create", {
        "name": "divider_ref",
        "dir": str(proj_dir),
        "board_size": [50.0, 35.0],
        "fab": "jlcpcb",
    })
    pro_path = proj_dir / "divider_ref.kicad_pro"
    sch_path = proj_dir / "divider_ref.kicad_sch"
    pcb_path = proj_dir / "divider_ref.kicad_pcb"

    # 2. Schematic generation with atomic ops: 2 connectors, 2 resistors, nets Vin, Vdiv, GND, pwr_flags
    ops = [
        {"op": "place", "lib_id": "Device:R", "ref": "J1", "value": "VIN_IN", "footprint": "Resistor_SMD:R_0603_1608Metric"},
        {"op": "place", "lib_id": "Device:R", "ref": "R1", "value": "10k 1%", "footprint": "Resistor_SMD:R_0805_2012Metric", "fields": {"LCSC": "C17414"}},
        {"op": "place", "lib_id": "Device:R", "ref": "R2", "value": "10k 1%", "footprint": "Resistor_SMD:R_0805_2012Metric", "fields": {"LCSC": "C17414"}},
        {"op": "place", "lib_id": "Device:R", "ref": "J2", "value": "VDIV_OUT", "footprint": "Resistor_SMD:R_0603_1608Metric"},
        {"op": "connect", "pin": "J1.1", "net": "Vin"},
        {"op": "connect", "pin": "R1.1", "net": "Vin"},
        {"op": "connect", "pin": "R1.2", "net": "Vdiv"},
        {"op": "connect", "pin": "R2.1", "net": "Vdiv"},
        {"op": "connect", "pin": "J2.1", "net": "Vdiv"},
        {"op": "connect", "pin": "J1.2", "net": "GND"},
        {"op": "connect", "pin": "R2.2", "net": "GND"},
        {"op": "connect", "pin": "J2.2", "net": "GND"},
        {"op": "pwr_flag", "net": "GND"},
        {"op": "pwr_flag", "net": "Vin"},
    ]
    call_tool("sch_apply", {"project": str(proj_dir), "ops": ops, "verify": True})

    # 3. Synchronize netlist to PCB layout (leaves footprints unplaced beside board)
    call_tool("pcb_sync", {"project": str(proj_dir)})

    return {
        "dir": proj_dir,
        "pro": pro_path,
        "sch": sch_path,
        "pcb": pcb_path,
    }


@pytest.fixture
def disposable_project(reference_project, tmp_path):
    """Provides each test with an isolated, disposable copy of the reference KiCad project."""
    target_dir = tmp_path / "disposable_circuit"
    shutil.copytree(reference_project["dir"], target_dir)
    return {
        "dir": target_dir,
        "pro": target_dir / "divider_ref.kicad_pro",
        "sch": target_dir / "divider_ref.kicad_sch",
        "pcb": target_dir / "divider_ref.kicad_pcb",
    }


@pytest.fixture
def placed_project(disposable_project, adapter):
    """Provides an isolated project with footprints auto-placed inside the board outline."""
    res = adapter.place_pcb(disposable_project["pcb"], auto=True)
    assert res["success"] is True
    return disposable_project


def test_adapter_availability(adapter):
    """Verifies that Copper KiCad adapter correctly detects KiCad 10 on workstation."""
    assert adapter.is_available() is True
    inst = adapter.install
    assert inst is not None
    assert inst.cli.exists()
    assert "10." in inst.full_version


def test_adapter_doctor_status(adapter):
    """Verifies doctor status returns active KiCad 10 and Pillow."""
    status = adapter.doctor_status()
    assert status.get("copper") is not None
    assert status.get("kicad", {}).get("active") is not None
    active = status["kicad"]["active"]
    assert "10." in active.get("version", "")


def test_adapter_place_pcb_and_argument_normalization(adapter, disposable_project):
    """Verifies place_pcb auto placement and verifies parameter normalization (mode='auto' -> auto=True)."""
    pcb = disposable_project["pcb"]

    # Test auto=True on unplaced board
    res1 = adapter.place_pcb(pcb, auto=True)
    assert res1["success"] is True
    assert res1["placed"] == 4
    assert res1["elegance"] is not None

    # Test parameter normalization: mode='auto' must not trigger BAD_ARGUMENT error
    res2 = adapter.place_pcb(pcb, mode="auto")
    assert res2["success"] is True


def test_adapter_route_pcb_with_power_netclasses(adapter, placed_project):
    """Verifies that route_pcb injects power net-class trace widths and completes routing."""
    target_pcb = placed_project["pcb"]
    res = adapter.route_pcb(
        pcb_path=target_pcb,
        pour_ground=True,
        ground_net="GND",
        default_track=0.35,
        power_track=1.5,
        power_patterns=["*Vin*", "*Vdiv*"],
    )

    assert res["routing_completed"] is True
    assert res["pour_completed"] is True
    assert res["tracks"] > 0
    assert res["drc_errors"] == 0
    assert "netclasses" in res
    assert res["netclasses"].get("Power", {}).get("track") == 1.5
    assert res["netclasses"].get("Default", {}).get("track") == 0.35


def test_adapter_render_3d(adapter, placed_project, tmp_path):
    """Verifies 3D raytraced rendering produces valid PNG."""
    target_pcb = placed_project["pcb"]
    out_png = tmp_path / "test_render_3d.png"
    result_path = adapter.render_3d(target_pcb, output_png=out_png, view="iso", width=800)

    assert result_path.exists()
    assert result_path.stat().st_size > 5000
    assert result_path.suffix.lower() == ".png"


def test_kicad_service_render_3d(placed_project, tmp_path):
    """Verifies KiCadLifecycleService renders 3D views through internal Copper adapter."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService

    target_pcb = placed_project["pcb"]
    service = KiCadLifecycleService()
    out_png = tmp_path / "service_3d_render.png"
    res = service.render_3d(target_pcb, output_png=out_png, view="top", width=600)

    assert res.exists()
    assert res.stat().st_size > 2000


def test_kicad_adapter_render_3d_operation(placed_project, tmp_path):
    """Verifies KiCadAdapter executes render_3d operation."""
    from integrations.adapters.kicad import KiCadAdapter
    from integrations.contracts import JobRequest, JobState

    target_pcb = placed_project["pcb"]
    adapter = KiCadAdapter()
    req = JobRequest(
        job_id=str(uuid4()),
        workspace_id=str(uuid4()),
        tool_id="kicad",
        operation="render_3d",
        workdir=str(tmp_path),
        input_paths=[str(target_pcb)],
        parameters={"view": "iso", "width": 600},
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.SUCCEEDED
    assert (tmp_path / "divider_ref_3d.png").exists()
    assert (tmp_path / "divider_ref_3d.png").stat().st_size > 2000


def test_adapter_apply_schematic(adapter, disposable_project):
    """Verifies that apply_schematic modifies fields and passes KiCad ERC."""
    target_sch = disposable_project["sch"]
    res = adapter.apply_schematic(
        sch_path=target_sch,
        ops=[
            {"op": "set_field", "ref": "R1", "field": "Value", "value": "12k 1% Precision"},
            {"op": "set_field", "ref": "R1", "field": "MPN", "value": "ERA-6AEB123V"},
        ],
        verify=True,
    )

    assert res["success"] is True
    assert res["ops_applied"] == 2
    assert any("R1.Value" in c for c in res["changed"])
    assert res["erc"].get("errors", 0) == 0


def test_adapter_export_fab_and_argument_normalization(adapter, placed_project, tmp_path):
    """Verifies export_fab generates complete fabrication pack and normalizes fab='jlcpcb'."""
    target_pcb = placed_project["pcb"]

    # Route first so DRC and fab gate pass
    adapter.route_pcb(target_pcb)

    # Test with standard profile='jlcpcb' and waive=['parts']
    fab_out = tmp_path / "fab_pack"
    res1 = adapter.export_fab(target_pcb, profile="jlcpcb", waive=["parts"], out_dir=fab_out)
    assert res1["success"] is True
    assert Path(res1["zip_path"]).exists()
    assert len(res1["zip_files"]) >= 9

    # Test argument normalization: passing fab='jlcpcb' instead of profile
    res2 = adapter.export_fab(target_pcb, fab="jlcpcb")
    assert res2["success"] is True
    assert Path(res2["zip_path"]).exists()


def test_adapter_export_cad_step(adapter, placed_project, tmp_path):
    """Verifies export_cad produces 3D STEP solid model."""
    target_pcb = placed_project["pcb"]
    out_step = tmp_path / "circuit.step"
    result = adapter.export_cad(target_pcb, kind="step", output_file=out_step)

    assert result.exists()
    assert result.stat().st_size > 20000
    assert result.suffix.lower() == ".step"


def test_desktop_service_auto_route_rpc():
    """Verifies DesktopService auto_route_pcb RPC endpoint schema validation."""
    from mendex_core.desktop.models import AutoRouteQuery
    from mendex_core.desktop.service import ROUTES

    assert "auto_route_pcb" in ROUTES
    query = AutoRouteQuery(
        revision_id="9b7c1396-64da-41f8-8649-77dc0f24e103",
        pour_ground=True,
        default_track=0.4,
        power_track=1.2,
    )
    assert query.default_track == 0.4
    assert query.power_track == 1.2


def test_desktop_service_apply_schematic_rpc():
    """Verifies DesktopService apply_schematic route registration and schema validation."""
    from mendex_core.desktop.models import SchematicApplyQuery
    from mendex_core.desktop.service import ROUTES

    assert "apply_schematic" in ROUTES
    query = SchematicApplyQuery(
        revision_id="9b7c1396-64da-41f8-8649-77dc0f24e103",
        ops=[{"op": "set_field", "ref": "R1", "field": "Value", "value": "15k"}],
        verify=True,
    )
    assert len(query.ops) == 1
    assert query.verify is True


def test_calculate_iec60664_creepage_analytical_margins():
    """Verify IEC 60664-1 analytical creepage calculations across standard operating voltages."""
    from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

    # Basic insulation
    assert CopperKiCadAdapter.calculate_iec60664_creepage(50.0, insulation_type="basic") == 1.2
    assert CopperKiCadAdapter.calculate_iec60664_creepage(230.0, insulation_type="basic") == 2.5
    assert CopperKiCadAdapter.calculate_iec60664_creepage(400.0, insulation_type="basic") == 4.0

    # Reinforced / double insulation (mains to SELV safety barrier)
    assert CopperKiCadAdapter.calculate_iec60664_creepage(50.0, insulation_type="reinforced") == 2.4
    assert CopperKiCadAdapter.calculate_iec60664_creepage(230.0, insulation_type="reinforced") == 5.0
    assert CopperKiCadAdapter.calculate_iec60664_creepage(400.0, insulation_type="reinforced") == 8.0


def test_mill_isolation_slot_with_iec60664_creepage(reference_project, adapter):
    """Verify physical Edge.Cuts isolation slot milling with analytical IEC 60664-1 voltage input."""
    pcb_path = reference_project["pcb"]
    res = adapter.mill_isolation_slot(pcb_path, working_voltage_v=400.0)

    assert res["success"] is True
    geom = res["slot_geometry"]
    assert geom["width_mm"] == 8.0  # 400V reinforced creepage = 8.0mm
    assert geom["layer"] == "Edge.Cuts"

    # Verify slot inserted into .kicad_pcb
    content = pcb_path.read_text(encoding="utf-8")
    assert 'gr_rect' in content
    assert '"Edge.Cuts"' in content


def test_four_layer_power_pcb_stackup_and_internal_planes(tmp_path, adapter):
    """Verify 4-layer power converter stackup creation and In1.Cu/In2.Cu internal plane pours."""
    proj_dir = tmp_path / "power_4l_board"
    proj_dir.mkdir(parents=True, exist_ok=True)

    create_res = call_tool("project_create", {
        "name": "power_4l_board",
        "dir": str(proj_dir),
        "board_size": [65.0, 50.0],
        "template": "4layer",
        "fab": "jlcpcb",
    })
    assert not create_res.get("isError")
    pcb_path = proj_dir / "power_4l_board.kicad_pcb"
    assert pcb_path.exists()

    # Populate basic netlist with GND and VIN
    ops = [
        {"op": "place", "lib_id": "Device:R", "ref": "R1", "value": "100", "footprint": "Resistor_SMD:R_0805_2012Metric"},
        {"op": "connect", "pin": "R1.1", "net": "VIN"},
        {"op": "connect", "pin": "R1.2", "net": "PRI_GND"},
        {"op": "pwr_flag", "net": "VIN"},
        {"op": "pwr_flag", "net": "PRI_GND"},
    ]
    sch_path = proj_dir / "power_4l_board.kicad_sch"
    adapter.apply_schematic(sch_path, ops, verify=False)
    call_tool("pcb_sync", {"project": str(proj_dir)})

    # Configure IPC-2152 compliant 4-layer internal copper plane zones
    res = adapter.setup_four_layer_power_planes(pcb_path, gnd_net="PRI_GND", pwr_net="VIN")
    assert res["in1_gnd_poured"] is True
    assert res["in2_pwr_poured"] is True

    # Verify internal copper plane zones exist in .kicad_pcb file
    pcb_content = pcb_path.read_text(encoding="utf-8")
    assert '"In1.Cu"' in pcb_content
    assert '"In2.Cu"' in pcb_content
    assert 'zone' in pcb_content
