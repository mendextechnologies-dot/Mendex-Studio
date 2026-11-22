"""Unit tests for the 4 turnkey industrial engineering modules:
1. Thermal Fit & Tolerance Stack Engine (Resolution of D09)
2. 1 MHz Coupled SPICE Subcircuit Generator
3. Cleanroom Assembly SOP & Fastener Torque Engine (SOP-HFT-000)
4. Factory Acceptance Testing (FAT / SAT) Protocol Engine (FAT-HFT-000)
"""
from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.evidence import specification_hash
from mendex_core.design.thermal_fit_engine import ThermalFitEngine
from mendex_core.design.spice_subcircuit_generator import SpiceSubcircuitGenerator
from mendex_core.design.assembly_sop_generator import AssemblySOPGenerator
from mendex_core.design.fat_protocol_generator import FATProtocolGenerator


@pytest.fixture
def core_setup(tmp_path):
    s = StudioService(tmp_path)
    p = s.create_product('HFT-TEST', 'Turnkey Test Product', 'transformer', 'QA Engineer')
    old = s.get_revision(p.active_revision_id)
    source = s.workspace_path(old) / 'mechanical/source.STEP'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'Solid dummy')
    req = dict(
        revision_id=str(old.revision_id),
        revision_label='REV-001',
        expected_input_hash=specification_hash(old.specification),
    )
    result = s.core_assembly.create_revision(req)
    rev = s.get_revision(result['revision']['revision_id'])
    return s, rev


def test_thermal_fit_engine_evaluates_d09_and_springs(core_setup):
    s, rev = core_setup
    engine = ThermalFitEngine(s)
    report = engine.evaluate_core_assembly(rev.revision_id)

    assert report["status"] == "EVALUATED_ANALYTICAL"
    assert report["temperatures"]["delta_t_k"] == 60.0

    # Fit conflict D09 verified
    radial = report["radial_interference_analysis"]
    assert radial["fit_conflict_id"] == "D09"
    assert radial["interference_hazard_detected"] is True
    assert radial["as_drawn_clearance_at_85c_worst_mm"] < 0

    # Engineered skimmed mandrel resolves conflict
    engineered = radial["engineered_solution"]
    assert engineered["recommended_mandrel_od_mm"] <= 63.0
    assert engineered["safe_clearance_at_85c_worst_mm"] >= 0.25

    # Belleville disc spring sizing
    belleville = report["axial_tolerance_stack"]["belleville_spring_pre_load"]
    assert "DIN 2093" in belleville["standard"]
    assert belleville["nominal_pre_load_n"] == 280.0

    # Report saved to workspace
    ws_dir = s.workspace_path(rev)
    report_file = ws_dir / "reports" / "HFT-000-Thermal-and-Tolerance-Stack-Analysis.json"
    assert report_file.exists()


def test_spice_subcircuit_generator_creates_netlist(core_setup):
    s, rev = core_setup
    gen = SpiceSubcircuitGenerator(s)
    res = gen.generate_subcircuit(rev.revision_id, turns_per_limb=16, rated_current_rms=15.0)

    assert res["status"] == "GENERATED_SUCCESS"
    params = res["parameters"]
    assert params["magnetizing_inductance_per_limb_uh"] > 1000.0  # >1 mH
    assert params["inter_limb_coupling_factor_k"] == 0.085
    assert params["ac_resistance_1mhz_per_limb_ohm"] > 0
    assert params["core_damping_resistance_rp_megohm"] > 1.0  # >1 MOhm

    # Netlist files generated
    ws_dir = s.workspace_path(rev)
    subckt_path = ws_dir / "simulations" / "spice" / "HFT_000_1MHZ.subckt"
    testbench_path = ws_dir / "simulations" / "spice" / "HFT_000_testbench.cir"
    assert subckt_path.exists()
    assert testbench_path.exists()

    content = subckt_path.read_text(encoding="utf-8")
    assert ".SUBCKT HFT_000_1MHZ" in content
    assert "K12 L1_MAG L2_MAG 0.0850" in content


def test_assembly_sop_generator_generates_manual(core_setup):
    s, rev = core_setup
    gen = AssemblySOPGenerator(s)
    res = gen.generate_sop(rev.revision_id)

    assert res["status"] == "GENERATED_SUCCESS"
    assert res["fastener_torque_nm"] == 12.5
    assert "Helicoil" in res["thread_inserts"]
    assert res["cleanroom_class"] == "ISO Class 8"

    ws_dir = s.workspace_path(rev)
    html_file = ws_dir / "reports" / "HFT-000-Manufacturing-Assembly-SOP.html"
    assert html_file.exists()
    assert "SOP-HFT-000" in html_file.read_text(encoding="utf-8")


def test_fat_protocol_generator_generates_tender_matching_doc(core_setup):
    s, rev = core_setup
    gen = FATProtocolGenerator(s)
    res = gen.generate_fat_protocol(rev.revision_id)

    assert res["status"] == "GENERATED_SUCCESS"
    assert res["spare_ferrites_verified"] == 24
    assert res["installed_ferrites"] == 48
    assert res["hi_pot_test_kv"] == 5.0
    assert "final_specs_307" in res["acceptance_criteria"]

    ws_dir = s.workspace_path(rev)
    html_file = ws_dir / "reports" / "HFT-000-Factory-Acceptance-Test-Protocol.html"
    assert html_file.exists()
    assert "FAT-HFT-000" in html_file.read_text(encoding="utf-8")
