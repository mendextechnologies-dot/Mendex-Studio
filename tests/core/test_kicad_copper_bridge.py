"""Unit and integration tests for Mendex IR to Copper KiCad bridge."""
from pathlib import Path
import pytest

from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.generators.kicad_generator import (
    KiCadSchematicGenerator,
    mendex_ir_to_copper_ops,
    resolve_symbol_lib_id,
    resolve_footprint,
    normalize_pin_id,
)
from mendex_core.design.ir import ComponentType, IRComponent


def test_resolve_symbol_lib_id_and_footprint():
    """Verifies symbol library mappings and footprint resolutions for power components."""
    q_mos = IRComponent(designator="Q1", name="MOSFET", type=ComponentType.SWITCH_MOSFET)
    assert resolve_symbol_lib_id(q_mos) == "Device:Q_NMOS"
    assert resolve_footprint(q_mos) == "Package_TO_SOT_SMD:TO-252-2"

    t_xfmr = IRComponent(designator="T1", name="Flyback Transformer", type=ComponentType.TRANSFORMER)
    assert resolve_symbol_lib_id(t_xfmr) == "Device:Transformer_1P_1S"
    assert resolve_footprint(t_xfmr) == "Transformer_THT:Transformer_Breve_TEZ-22x24"

    d_rec = IRComponent(designator="D1", name="Diode", type=ComponentType.DIODE)
    assert resolve_symbol_lib_id(d_rec) == "Device:D"
    assert resolve_footprint(d_rec) == "Diode_SMD:D_SMA"

    v_src = IRComponent(designator="V1", name="DC Supply", type=ComponentType.VOLTAGE_SOURCE)
    assert resolve_symbol_lib_id(v_src) == "Connector:Conn_01x02_Pin"
    assert resolve_footprint(v_src) == "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"


def test_normalize_pin_id():
    """Verifies pin normalization across component types."""
    assert normalize_pin_id(ComponentType.VOLTAGE_SOURCE, "p") == "1"
    assert normalize_pin_id(ComponentType.VOLTAGE_SOURCE, "n") == "2"
    assert normalize_pin_id(ComponentType.SWITCH_MOSFET, "d") == "D"
    assert normalize_pin_id(ComponentType.SWITCH_MOSFET, "g") == "G"
    assert normalize_pin_id(ComponentType.SWITCH_MOSFET, "s") == "S"
    assert normalize_pin_id(ComponentType.DIODE, "a") == "A"
    assert normalize_pin_id(ComponentType.DIODE, "k") == "K"
    assert normalize_pin_id(ComponentType.TRANSFORMER, "pri_dot") == "1"
    assert normalize_pin_id(ComponentType.TRANSFORMER, "pri_undot") == "2"
    assert normalize_pin_id(ComponentType.TRANSFORMER, "sec_dot") == "3"
    assert normalize_pin_id(ComponentType.TRANSFORMER, "sec_undot") == "4"


def test_mendex_ir_to_copper_ops_buck():
    """Verifies that Buck converter IR translates into declarative Copper operations."""
    ir_buck = CandidateSynthesisEngine._build_buck_ir(
        vin_nom=24.0, vout=12.0, iout=3.0, fsw=100000.0, l_val=50e-6, c_val=100e-6
    )
    ops = mendex_ir_to_copper_ops(ir_buck)

    place_ops = [op for op in ops if op["op"] == "place"]
    connect_ops = [op for op in ops if op["op"] == "connect"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    assert len(place_ops) == len(ir_buck.components)
    assert any(op["ref"] == "Q1" for op in place_ops)
    assert any(op["ref"] == "L1" for op in place_ops)
    assert any(op["ref"] == "RLOAD" or op["ref"] == "R_LOAD" for op in place_ops)

    assert len(connect_ops) > 0
    assert any(op["net"] == "VIN" for op in connect_ops)
    assert any(op["net"] == "SW" for op in connect_ops)
    assert any(op["net"] == "VOUT" for op in connect_ops)
    assert any(op["net"] == "GND" for op in connect_ops)

    # Power flags automatically injected
    flagged_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in flagged_nets
    assert "VOUT" in flagged_nets
    assert "GND" in flagged_nets


def test_mendex_ir_to_copper_ops_flyback():
    """Verifies that Flyback converter IR translates into declarative Copper operations."""
    ir_fly = CandidateSynthesisEngine._build_flyback_ir(
        vin_nom=48.0, vout=5.0, iout=4.0, fsw=120000.0, lm_val=60e-6, n_ratio=4.0
    )
    ops = mendex_ir_to_copper_ops(ir_fly)

    place_ops = [op for op in ops if op["op"] == "place"]
    connect_ops = [op for op in ops if op["op"] == "connect"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    assert len(place_ops) == len(ir_fly.components)
    assert any(op["ref"] == "T1" for op in place_ops)
    assert any(op["ref"] == "Q1" for op in place_ops)
    assert any(op["ref"] == "D1" for op in place_ops)

    flagged_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in flagged_nets
    assert "VOUT" in flagged_nets
    assert "PRI_GND" in flagged_nets or "GND" in flagged_nets


def test_mendex_ir_to_copper_ops_boost():
    """Verifies that Boost converter IR translates into declarative Copper operations."""
    ir_boost = CandidateSynthesisEngine._build_boost_ir(
        vin_nom=12.0, vout=24.0, iout=1.5, fsw=150000.0, l_val=40e-6, c_val=47e-6
    )
    ops = mendex_ir_to_copper_ops(ir_boost)

    place_ops = [op for op in ops if op["op"] == "place"]
    connect_ops = [op for op in ops if op["op"] == "connect"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    assert len(place_ops) == len(ir_boost.components)
    assert any(op["ref"] == "L1" for op in place_ops)
    assert any(op["ref"] == "Q1" for op in place_ops)
    assert any(op["ref"] == "D1" for op in place_ops)
    assert any(op["ref"] == "C1" for op in place_ops)

    assert len(connect_ops) > 0
    assert any(op["net"] == "VIN" for op in connect_ops)
    assert any(op["net"] == "SW" for op in connect_ops)
    assert any(op["net"] == "VOUT" for op in connect_ops)
    assert any(op["net"] == "GND" for op in connect_ops)

    flagged_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in flagged_nets
    assert "VOUT" in flagged_nets
    assert "GND" in flagged_nets


def test_kicad_schematic_generator_export_copper_project_buck(tmp_path):
    """Verifies end-to-end native KiCad 10 project synthesis for Buck converter."""
    ir_buck = CandidateSynthesisEngine._build_buck_ir(
        vin_nom=24.0, vout=12.0, iout=3.0, fsw=100000.0, l_val=50e-6, c_val=100e-6
    )
    target_dir = tmp_path / "buck_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_buck,
        target_dir=target_dir,
        board_size=(55.0, 40.0),
        auto_place=True,
    )

    assert Path(res["project_dir"]).exists()
    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert Path(res["project"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True


def test_kicad_schematic_generator_export_copper_project_flyback(tmp_path):
    """Verifies end-to-end native KiCad 10 project synthesis for Flyback converter."""
    ir_fly = CandidateSynthesisEngine._build_flyback_ir(
        vin_nom=48.0, vout=5.0, iout=4.0, fsw=120000.0, lm_val=60e-6, n_ratio=4.0
    )
    target_dir = tmp_path / "flyback_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_fly,
        target_dir=target_dir,
        board_size=(65.0, 50.0),
        auto_place=True,
    )

    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True


def test_kicad_schematic_generator_export_copper_project_boost(tmp_path):
    """Verifies end-to-end native KiCad 10 project synthesis for Boost converter."""
    ir_boost = CandidateSynthesisEngine._build_boost_ir(
        vin_nom=12.0, vout=24.0, iout=1.5, fsw=150000.0, l_val=40e-6, c_val=47e-6
    )
    target_dir = tmp_path / "boost_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_boost,
        target_dir=target_dir,
        board_size=(55.0, 40.0),
        auto_place=True,
    )

    assert Path(res["project_dir"]).exists()
    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert Path(res["project"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True
    assert res["erc"].get("errors", 0) == 0


def test_kicad_schematic_generator_legacy_sexpr_compatibility(tmp_path):
    """Verifies backward compatibility of legacy string-based schematic generation."""
    ir_buck = CandidateSynthesisEngine._build_buck_ir(
        vin_nom=24.0, vout=12.0, iout=3.0, fsw=100000.0, l_val=50e-6, c_val=100e-6
    )
    sexpr = KiCadSchematicGenerator.generate_schematic_sexpr(ir_buck)
    assert "(kicad_sch" in sexpr
    assert "(symbol" in sexpr and "lib_id" in sexpr

    exported = KiCadSchematicGenerator.export_project(ir_buck, tmp_path / "legacy_out")
    assert exported["schematic"].exists()
    assert exported["project"].exists()


def test_mendex_ir_to_copper_ops_pushpull():
    """Verifies that Push-Pull multi-winding converter IR translates into declarative Copper operations."""
    ir_pp = CandidateSynthesisEngine._build_pushpull_ir(
        vin_nom=48.0, vout=12.0, iout=5.0, fsw=100000.0, lm_val=80e-6, n_ratio=0.5
    )
    ops = mendex_ir_to_copper_ops(ir_pp)

    place_ops = [op for op in ops if op["op"] == "place"]
    connect_ops = [op for op in ops if op["op"] == "connect"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    assert len(place_ops) == len(ir_pp.components)
    assert any(op["ref"] == "T1" for op in place_ops)
    t1_op = next(op for op in place_ops if op["ref"] == "T1")
    assert t1_op["lib_id"] == "Device:Transformer_1P_2S"

    assert any(op["ref"] == "D1" for op in place_ops)
    assert any(op["ref"] == "D2" for op in place_ops)
    assert any(op["ref"] == "L1" for op in place_ops)

    flagged_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in flagged_nets
    assert "VOUT" in flagged_nets
    assert "PRI_GND" in flagged_nets
    assert "SEC_GND" in flagged_nets
    assert "GATE" in flagged_nets


def test_kicad_schematic_generator_export_copper_project_pushpull(tmp_path):
    """Verifies end-to-end native KiCad 10 project synthesis for Push-Pull multi-winding converter."""
    ir_pp = CandidateSynthesisEngine._build_pushpull_ir(
        vin_nom=48.0, vout=12.0, iout=5.0, fsw=100000.0, lm_val=80e-6, n_ratio=0.5
    )
    target_dir = tmp_path / "pushpull_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_pp,
        target_dir=target_dir,
        board_size=(70.0, 50.0),
        auto_place=True,
    )

    assert Path(res["project_dir"]).exists()
    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert Path(res["project"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True
    assert res["erc"].get("errors", 0) == 0

def test_mendex_ir_to_copper_ops_llc():
    """Verifies that LLC Resonant Half-Bridge converter IR translates into declarative Copper operations."""
    ir_llc = CandidateSynthesisEngine._build_llc_ir(
        vin_nom=400.0, vout=12.0, iout=25.0, fsw=100000.0,
        lr_val=15e-6, cr_val=66e-9, lm_val=75e-6, n_ratio=16.67
    )
    ops = mendex_ir_to_copper_ops(ir_llc)

    place_ops = [op for op in ops if op["op"] == "place"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    assert len(place_ops) == len(ir_llc.components)
    assert any(op["ref"] == "Q1" for op in place_ops)
    assert any(op["ref"] == "Q2" for op in place_ops)
    assert any(op["ref"] == "CR1" for op in place_ops)
    assert any(op["ref"] == "LR1" for op in place_ops)
    assert any(op["ref"] == "T1" for op in place_ops)
    assert any(op["ref"] == "D1" for op in place_ops)
    assert any(op["ref"] == "D2" for op in place_ops)
    assert any(op["ref"] == "C1" for op in place_ops)
    assert any(op["ref"] == "RLOAD" for op in place_ops)

    t1_op = next(op for op in place_ops if op["ref"] == "T1")
    assert t1_op["lib_id"] == "Device:Transformer_1P_2S"

    flagged_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in flagged_nets
    assert "VOUT" in flagged_nets
    assert "PRI_GND" in flagged_nets
    assert "SEC_GND" in flagged_nets
    assert "GATE_HI" in flagged_nets
    assert "GATE_LO" in flagged_nets


def test_kicad_schematic_generator_export_copper_project_llc(tmp_path):
    """Verifies end-to-end native KiCad 10 project synthesis and 0-error ERC for LLC converter."""
    ir_llc = CandidateSynthesisEngine._build_llc_ir(
        vin_nom=400.0, vout=12.0, iout=25.0, fsw=100000.0,
        lr_val=15e-6, cr_val=66e-9, lm_val=75e-6, n_ratio=16.67
    )
    target_dir = tmp_path / "llc_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_llc,
        target_dir=target_dir,
        board_size=(75.0, 55.0),
        auto_place=True,
    )

    assert Path(res["project_dir"]).exists()
    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert Path(res["project"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True
    assert res["erc"].get("errors", 0) == 0



def test_mendex_ir_to_copper_ops_psfb():
    """Verify IR to Copper declarative ops conversion for Phase-Shifted Full-Bridge."""
    ir_psfb = CandidateSynthesisEngine._build_psfb_ir(
        vin_nom=400.0,
        vout=48.0,
        iout=20.0,
        fsw=100000.0,
        l_shim_val=15e-6,
        l_out_val=35e-6,
        c_out_val=220e-6,
        n_ratio=3.5,
    )

    ops = mendex_ir_to_copper_ops(ir_psfb)
    assert len(ops) > 0

    place_ops = [op for op in ops if op["op"] == "place"]
    connect_ops = [op for op in ops if op["op"] == "connect"]
    pwr_flags = [op for op in ops if op["op"] == "pwr_flag"]

    # 16 components
    assert len(place_ops) == 16
    refs = {op["ref"] for op in place_ops}
    assert "Q1" in refs
    assert "Q2" in refs
    assert "Q3" in refs
    assert "Q4" in refs
    assert "T1" in refs
    assert "LSHIM" in refs
    assert "LOUT" in refs
    assert "COUT" in refs
    assert "D1" in refs
    assert "D2" in refs

    # Transformer symbol resolution
    t1_op = next(op for op in place_ops if op["ref"] == "T1")
    assert t1_op["lib_id"] == "Device:Transformer_1P_2S"

    # Power flags
    pwr_nets = {op["net"] for op in pwr_flags}
    assert "VIN" in pwr_nets
    assert "PRI_GND" in pwr_nets
    assert "VOUT" in pwr_nets
    assert "SEC_GND" in pwr_nets
    assert "GATE_A_HI" in pwr_nets
    assert "GATE_B_LO" in pwr_nets


def test_kicad_schematic_generator_export_copper_project_psfb(tmp_path):
    """End-to-end integration: PSFB IR -> Copper ops -> native KiCad 10 project + ERC."""
    from mendex_core.design.generators.kicad_generator import KiCadSchematicGenerator

    ir_psfb = CandidateSynthesisEngine._build_psfb_ir(
        vin_nom=400.0,
        vout=48.0,
        iout=20.0,
        fsw=100000.0,
        l_shim_val=15e-6,
        l_out_val=35e-6,
        c_out_val=220e-6,
        n_ratio=3.5,
    )

    target_dir = tmp_path / "psfb_copper_project"
    res = KiCadSchematicGenerator.export_copper_project(
        ir=ir_psfb,
        target_dir=target_dir,
        board_size=(85.0, 65.0),
        auto_place=True,
    )

    assert Path(res["project_dir"]).exists()
    assert Path(res["schematic"]).exists()
    assert Path(res["pcb"]).exists()
    assert Path(res["project"]).exists()
    assert res["ops_applied"] > 0
    assert res["sync"] is True
    assert res["placed"] is True
    assert res["erc"].get("errors", 0) == 0
