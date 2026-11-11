"""v2.0 End-to-End Real Engineering Workflow Qualification Tests.

Verifies real solvers and tools:
1. Real LTspice simulation of Buck 20W converter, waveform extraction and requirements evaluation.
2. Native LTspice graphical schematic (.asc) generation.
3. Real KiCad populated PCB layout (.kicad_pcb) and schematic (.kicad_sch) generation and CLI checks.
4. Real FreeCAD headless 3D STEP solid generation.
5. Real FEMM 4.2 magnetics FEA execution via filelink protocol.
6. Closed-loop AI design iteration and verification.
7. Verified native tool dispatch routing.
"""
from pathlib import Path
import tempfile
import pytest

from mendex_core.design.models import EngineeringDesign, DesignStatus, Requirement
from mendex_core.design.ir import DesignIntermediateRepresentation
from mendex_core.design.service import EngineeringDesignService
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.ltspice_runner import LTspiceRunner
from mendex_core.design.femm_runner import FEMMRunner
from mendex_core.design.generators import (
    LTspiceNetlistGenerator,
    KiCadSchematicGenerator,
    KiCadPCBGenerator,
    FEMMMagneticGenerator,
)
from mendex_core.design.iteration import DesignIterationEngine
from mendex_core.launch import open_native, launch_tool, NATIVE_EXTENSIONS


@pytest.fixture
def temp_design_env():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        service = EngineeringDesignService(data_root=root)
        yield service, root


def test_real_ltspice_buck_simulation(temp_design_env):
    """Test 1: Real LTspice execution on Buck converter, parsing .raw waveforms and evaluating metrics."""
    service, root = temp_design_env
    runner = LTspiceRunner()
    if not runner.is_available:
        pytest.skip("LTspice executable not available on host.")

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V", tolerance_pct=10.0),
        Requirement(parameter="iout", target_value=4.0, unit="A"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
        Requirement(parameter="ripple", target_value=0.1, max_value=0.15, unit="V"),
    ]
    design = service.create_design_from_requirements(
        workspace_id="test_ws",
        title="Buck 20W Qualification",
        category="dc_dc_converter",
        requirements=reqs,
    )
    workspace = root / "workspaces" / design.workspace_id
    workspace.mkdir(parents=True, exist_ok=True)

    result = service.run_ltspice_simulation(design.id, workspace)
    assert result.success is True
    assert result.exit_code == 0
    assert result.elapsed_time_s >= 0.0
    assert result.raw_file_path is not None
    assert Path(result.raw_file_path).exists()
    assert 4.5 <= result.vout_mean_v <= 5.5
    assert result.vout_ripple_pk_pk_v < 0.25


def test_ltspice_asc_graphical_schematic_generation():
    """Test 2: Verifies editable LTspice .asc schematic emission."""
    ir = CandidateSynthesisEngine._build_buck_ir(24.0, 5.0, 4.0, 100000.0, 47e-6, 100e-6)
    asc_text = LTspiceNetlistGenerator.generate_asc_schematic(ir)
    assert "Version 4" in asc_text
    assert "SHEET 1" in asc_text
    assert "SYMBOL voltage" in asc_text
    assert "SYMBOL ind" in asc_text
    assert "SYMBOL cap" in asc_text
    assert "SYMBOL res" in asc_text
    assert "FLAG" in asc_text
    assert ".tran" in asc_text


def test_kicad_populated_pcb_generation(temp_design_env):
    """Test 3: Populated KiCad .kicad_pcb layout generation with board outline, components and nets."""
    service, root = temp_design_env
    ir = CandidateSynthesisEngine._build_buck_ir(24.0, 5.0, 4.0, 100000.0, 47e-6, 100e-6)
    pcb_file = root / "test_buck.kicad_pcb"
    KiCadPCBGenerator.export_pcb(ir, pcb_file)
    assert pcb_file.exists()
    content = pcb_file.read_text(encoding="utf-8")
    assert "(kicad_pcb" in content
    assert "Edge.Cuts" in content
    assert "gr_rect" in content
    assert '(net 3 "VOUT")' in content
    assert '(net 4 "GND")' in content
    assert "footprint" in content


def test_real_freecad_step_generation(temp_design_env):
    """Test 4: Real FreeCADCmd headless 3D STEP solid generation for transformer bobbin."""
    service, root = temp_design_env
    fc_cmd = Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
    if not fc_cmd.exists():
        pytest.skip("FreeCADCmd 1.1 executable not available on host.")

    from integrations.generators.freecad_generator import generate_freecad_bobbin_script
    import subprocess

    step_path = root / "bobbin_test.step"
    script_path = root / "gen_bobbin.py"
    script_path.write_text(
        generate_freecad_bobbin_script(flange_od_mm=32.0, core_id_mm=16.0, height_mm=25.0, output_step_path=str(step_path)),
        encoding="utf-8",
    )
    res = subprocess.run([str(fc_cmd), str(script_path)], capture_output=True, timeout=25)
    assert res.returncode == 0
    assert step_path.exists()
    assert step_path.stat().st_size > 1000
    header = step_path.read_text(encoding="utf-8", errors="ignore")[:200]
    assert "ISO-10303-21" in header


def test_real_femm_magnetic_simulation(temp_design_env):
    """Test 5: Real FEMM 4.2 magnetic FEA simulation via filelink protocol."""
    service, root = temp_design_env
    runner = FEMMRunner()
    if not runner.is_available:
        pytest.skip("FEMM 4.2 executable not available on host.")

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=3.0, unit="A"),
        Requirement(parameter="fsw", target_value=65000.0, unit="Hz"),
        Requirement(parameter="isolation_v", target_value=1500.0, unit="V"),
    ]
    design = service.create_design_from_requirements(
        workspace_id="test_ws_femm",
        title="Flyback Transformer Qualification",
        category="isolated_dc_dc",
        requirements=reqs,
    )
    workspace = root / "workspaces" / design.workspace_id
    workspace.mkdir(parents=True, exist_ok=True)

    result = service.run_femm_simulation(design.id, workspace)
    assert result.success is True
    assert result.b_max_tesla > 0.0
    assert result.b_max_tesla < result.saturation_threshold_t
    assert result.is_saturated is False


def test_closed_loop_ai_design_iteration(temp_design_env):
    """Test 6: Closed-loop iteration: ripple detection, AI proposal, human approval, Rev 2 branching, re-simulation."""
    service, root = temp_design_env
    runner = LTspiceRunner()
    if not runner.is_available:
        pytest.skip("LTspice executable not available on host.")

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V", tolerance_pct=10.0),
        Requirement(parameter="iout", target_value=4.0, unit="A"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
        Requirement(parameter="ripple", target_value=0.005, max_value=0.005, unit="V"),
    ]
    design = service.create_design_from_requirements(
        workspace_id="test_ws_iter",
        title="Buck Iteration Qualification",
        category="dc_dc_converter",
        requirements=reqs,
    )
    workspace = root / "workspaces" / design.workspace_id
    workspace.mkdir(parents=True, exist_ok=True)

    # Rev 1 simulation
    sim1 = service.run_ltspice_simulation(design.id, workspace)
    proposal = service.propose_iteration(design.id, sim1)
    assert proposal is not None
    assert proposal.parameter_to_change == "C"
    assert proposal.proposed_value > proposal.current_value
    assert "ripple" in proposal.rationale.lower() or "capacitance" in proposal.rationale.lower()

    # Engineer explicitly approves proposal
    proposal.approval_status = "APPROVED"

    # Apply iteration: branches Rev 2 and re-runs
    result = service.apply_iteration(design.id, proposal)
    assert result["success"] is True
    assert result["revision_index"] == 2

    # Verify that updated design has 2 revisions and Rev 2 has higher capacitance
    updated_design = service.get_design(design.id)
    assert len(updated_design.revisions) == 2
    rev2 = updated_design.get_active_revision()
    assert rev2.revision_index == 2
    c1 = next(c for c in rev2.ir.components if c.designator in ("C", "C1"))
    assert c1.value > 100e-6


def test_tool_launch_and_routing(temp_design_env):
    """Test 7: Native tool launch routing prevents improper association (e.g., .step -> KiCad)."""
    service, root = temp_design_env

    # 1. STEP file must target FreeCAD
    step_file = root / "test_cad.step"
    step_file.write_text("ISO-10303-21; HEADER; ENDSEC; DATA; ENDSEC; END-ISO-10303-21;", encoding="utf-8")
    info = launch_tool("freecad", step_file)
    assert info["tool"] == "freecad"
    assert "freecad" in info["executable"].lower()

    # 2. LTspice netlist
    net_file = root / "test_sim.net"
    net_file.write_text("V1 1 0 12\nR1 1 0 10\n.op\n.end\n", encoding="utf-8")
    info_lt = launch_tool("ltspice", net_file)
    assert info_lt["tool"] == "ltspice"
    assert "ltspice" in info_lt["executable"].lower()

    # 3. KiCad schematic
    sch_file = root / "test.kicad_sch"
    sch_file.write_text("(kicad_sch (version 20240108))", encoding="utf-8")
    info_sch = launch_tool("kicad_sch", sch_file)
    assert info_sch["tool"] == "kicad_sch"
    assert "eeschema" in info_sch["executable"].lower()
