"""Unit and integration test suite for v1.9 Specification-to-Design Synthesis."""
from __future__ import annotations

import math
from pathlib import Path
import pytest

from mendex_core.service import StudioService
from mendex_core.design.models import (
    Requirement,
    EngineeringDesign,
    DesignStatus,
    CandidateApprovalStatus,
    ArtifactKind,
)
from mendex_core.design.ir import (
    DesignIntermediateRepresentation,
    IRComponent,
    IRPin,
    IRParameter,
    ComponentType,
)
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.parametric import ParametricDesignEngine, safe_eval
from mendex_core.design.generators import (
    LTspiceNetlistGenerator,
    KiCadSchematicGenerator,
    FEMMMagneticGenerator,
)
from mendex_core.design.sync import CrossToolSyncService, SyncStatus


def test_candidate_synthesis_non_isolated_buck():
    """Verify synthesis engine selects Buck converter for non-isolated step-down."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vin_min", target_value=18.0, unit="V"),
        Requirement(parameter="vin_max", target_value=30.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
        Requirement(parameter="frequency_hz", target_value=200000.0, unit="Hz"),
        Requirement(parameter="isolation", target_value=0.0, unit="V"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    assert len(candidates) >= 1
    top = candidates[0]
    assert "Buck" in top.topology
    assert top.constraints_satisfied is True
    assert top.status == CandidateApprovalStatus.SELECTED
    assert top.ir_snapshot is not None
    assert top.ir_snapshot.get_component("Q1") is not None
    assert top.ir_snapshot.get_component("L1") is not None


def test_candidate_synthesis_non_isolated_boost():
    """Verify synthesis engine selects Boost converter for non-isolated step-up."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=12.0, unit="V"),
        Requirement(parameter="vin_min", target_value=10.0, unit="V"),
        Requirement(parameter="vin_max", target_value=14.0, unit="V"),
        Requirement(parameter="vout", target_value=24.0, unit="V"),
        Requirement(parameter="iout", target_value=1.5, unit="A"),
        Requirement(parameter="frequency_hz", target_value=150000.0, unit="Hz"),
        Requirement(parameter="isolation", target_value=0.0, unit="V"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    assert len(candidates) >= 1
    top = candidates[0]
    assert "Boost" in top.topology
    assert top.constraints_satisfied is True
    assert top.status == CandidateApprovalStatus.SELECTED
    assert top.ir_snapshot is not None
    assert top.ir_snapshot.get_component("Q1") is not None
    assert top.ir_snapshot.get_component("L1") is not None
    assert top.ir_snapshot.get_component("D1") is not None
    assert top.ir_snapshot.get_component("C1") is not None


def test_candidate_synthesis_isolated_flyback():
    """Verify synthesis engine selects Flyback for isolated converter."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=48.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="pout", target_value=36.0, unit="W"),
        Requirement(parameter="isolation", target_value=1500.0, unit="V"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    assert len(candidates) >= 1
    # Flyback should be top choice for isolated 36W
    assert any("Flyback" in c.topology for c in candidates)
    flyback = [c for c in candidates if "Flyback" in c.topology][0]
    assert flyback.ir_snapshot is not None
    assert flyback.ir_snapshot.magnetic_geometry is not None
    assert flyback.ir_snapshot.get_component("T1") is not None

    assert any("Push-Pull" in c.topology for c in candidates)
    pp = [c for c in candidates if "Push-Pull" in c.topology][0]
    assert pp.ir_snapshot is not None
    assert pp.ir_snapshot.get_component("T1") is not None
    assert pp.ir_snapshot.get_component("D2") is not None
    assert pp.ir_snapshot.get_component("L1") is not None


def test_parametric_design_engine_propagation():
    """Verify safe AST evaluation, parameter dependency propagation, and change impact analysis."""
    ir = DesignIntermediateRepresentation(
        title="Parametric Test",
        parameters={
            "fsw": IRParameter(name="fsw", value=100000.0, unit="Hz"),
            "omega": IRParameter(name="omega", expression="2 * pi * fsw", value=0.0, unit="rad/s"),
            "period": IRParameter(name="period", expression="1 / fsw", value=0.0, unit="s"),
        },
    )
    engine = ParametricDesignEngine(ir)
    evaluated = engine.evaluate_all()

    assert math.isclose(evaluated["omega"], 628318.53, rel_tol=1e-3)
    assert math.isclose(evaluated["period"], 1e-5, rel_tol=1e-6)

    # Change impact analysis
    impact = engine.analyze_impact("fsw", 200000.0)
    assert impact.changed_parameter == "fsw"
    assert math.isclose(impact.recalculated_parameters["omega"], 1256637.06, rel_tol=1e-3)

    # Parameter sweep
    sweep = engine.generate_sweep("fsw", 50000.0, 150000.0, 3)
    assert len(sweep) == 3
    assert math.isclose(sweep[0]["fsw"], 50000.0)
    assert math.isclose(sweep[2]["fsw"], 150000.0)


def test_native_artifact_generation(tmp_path):
    """Verify generation of LTspice, KiCad, and FEMM native files from Design IR."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    ir = candidates[0].ir_snapshot
    assert ir is not None

    # LTspice Netlist
    net_str = LTspiceNetlistGenerator.generate_netlist(ir)
    assert "* MENDEX ENGINEERING STUDIO" in net_str
    assert ".tran" in net_str
    assert ".end" in net_str

    # KiCad Schematic
    kicad_sch = KiCadSchematicGenerator.generate_schematic_sexpr(ir)
    assert "(kicad_sch" in kicad_sch
    assert "(title" in kicad_sch

    # KiCad Project Export
    kicad_dir = tmp_path / "kicad_proj"
    res = KiCadSchematicGenerator.export_project(ir, kicad_dir)
    assert res["schematic"].exists()
    assert res["project"].exists()

    # FEMM Lua
    if ir.magnetic_geometry:
        femm_lua = FEMMMagneticGenerator.generate_lua_script(ir.magnetic_geometry)
        assert "mi_probdef" in femm_lua
        assert "mi_analyze" in femm_lua


def test_cross_tool_sync_and_external_edits(tmp_path):
    """Verify detection of external edits and immutable revision branching."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Sync_WS")
    ws_dir = tmp_path / "workspaces" / ws["workspace_id"]
    ws_dir.mkdir(parents=True, exist_ok=True)

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
    ]
    design = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Sync Test Design",
        category="dc_dc_converter",
        requirements=reqs,
    )
    assert design.status == DesignStatus.SYNTHESIZED
    assert len(design.revisions) == 1

    # Generate artifacts
    artifacts = service.design.generate_native_artifacts(design.id, ws_dir)
    assert len(artifacts) >= 2

    # Verify initially UP_TO_DATE
    active_rev = design.get_active_revision()
    mods_before = CrossToolSyncService.detect_modifications(active_rev, service.root)
    assert len(mods_before) == 0

    # Simulate engineer editing schematic externally in KiCad
    sch_art = [a for a in active_rev.artifacts if a.kind == ArtifactKind.KICAD_SCH][0]
    sch_file = service.root / sch_art.path
    sch_file.write_text(sch_file.read_text(encoding="utf-8") + "\n; Engineer manual annotation", encoding="utf-8")

    # Detect modification
    mods_after = CrossToolSyncService.detect_modifications(active_rev, service.root)
    assert len(mods_after) == 1
    assert mods_after[0]["status"] == SyncStatus.MODIFIED_EXTERNALLY.value

    # Reconcile into new Revision 2
    new_rev = CrossToolSyncService.reconcile_and_branch_revision(
        design=design,
        root_dir=service.root,
        engineer_notes="Updated schematic symbols in KiCad Eeschema",
    )
    assert new_rev.revision_index == 2
    assert design.active_revision_id == new_rev.id
    assert len(design.revisions) == 2


def test_component_library_queries(tmp_path):
    """Verify Component and Material Library queries."""
    service = StudioService(tmp_path)
    mosfets = service.components.list_components(category="mosfet")
    assert len(mosfets) >= 2
    assert any(m.mpn == "BSC026N08NS5" for m in mosfets)

    mat = service.components.get_material("N87")
    assert mat is not None
    assert mat.saturation_flux_t == 0.49


def test_design_synthesis_with_invalid_characters_and_newlines(tmp_path: Path):
    """Verify synthesis and artifact export succeed with newlines, arrows, and special characters in title."""
    service = StudioService(tmp_path)
    messy_title = "buck_converter_(e.g._24v_dc_in_\n→\n_5v_dc_@_5a,_25w,_200_khz)"
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vin_min", target_value=18.0, unit="V"),
        Requirement(parameter="vin_max", target_value=32.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V"),
        Requirement(parameter="iout", target_value=4.0, unit="A"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
        Requirement(parameter="ripple", target_value=0.05, unit="V"),
    ]
    design = service.design.create_design_from_requirements(
        workspace_id="test_ws",
        title=messy_title,
        category="dc_dc_converter",
        requirements=reqs,
    )
    assert design.id is not None

    # Generating native artifacts must not raise Errno 22
    ws_dir = tmp_path / "workspaces" / "test_ws"
    ws_dir.mkdir(parents=True, exist_ok=True)
    artifacts = service.design.generate_native_artifacts(design.id, ws_dir)
    assert len(artifacts) >= 3

    # Check generated files exist on disk
    sch_files = [tmp_path / a.path for a in artifacts if a.path.endswith(".kicad_sch")]
    assert len(sch_files) == 1
    assert "\n" not in str(sch_files[0])
    assert "→" not in str(sch_files[0])
    assert sch_files[0].exists()

    pcb_files = [tmp_path / a.path for a in artifacts if a.path.endswith(".kicad_pcb")]
    assert len(pcb_files) == 1
    assert pcb_files[0].exists()



def test_kicad_pcb_generator_copper_track_routing(tmp_path: Path):
    """Verify KiCadPCBGenerator emits 45-degree chamfered copper tracks when route_tracks=True."""
    from mendex_core.design.generators.kicad_pcb_generator import KiCadPCBGenerator
    from mendex_core.design.ir import DesignIntermediateRepresentation, IRComponent, ComponentType, IRNet, IRNetPinRef

    ir = DesignIntermediateRepresentation(
        design_id="test_routing",
        name="Test Routed PCB",
        components=[
            IRComponent(id="J1", name="Terminal", designator="J1", type=ComponentType.CONNECTOR, footprint="TerminalBlock:TerminalBlock_bornier-2_P5.08mm"),
            IRComponent(id="Q1", name="MOSFET", designator="Q1", type=ComponentType.SWITCH_SIC, footprint="Package_TO_SOT_SMD:TO-252-2"),
        ],
        nets=[
            IRNet(name="VIN_PWR", is_power=True, connections=[
                IRNetPinRef(component_id="J1", pin_id="1"),
                IRNetPinRef(component_id="Q1", pin_id="2"),
            ]),
            IRNet(name="GND_RET", is_ground=True, connections=[
                IRNetPinRef(component_id="J1", pin_id="2"),
                IRNetPinRef(component_id="Q1", pin_id="3"),
            ]),
        ],
    )
    pcb_file = tmp_path / "routed.kicad_pcb"
    KiCadPCBGenerator.export_pcb(ir, pcb_file, route_tracks=True)
    assert pcb_file.exists()
    content = pcb_file.read_text(encoding="utf-8")
    assert "(segment " in content
    assert 'layer "F.Cu"' in content
    assert 'layer "B.Cu"' in content
    assert 'width 1.00' in content  # Power net width
    assert "Routed Hardware Design" in content
