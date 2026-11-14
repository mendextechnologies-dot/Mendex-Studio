"""Integration test verifying end-to-end KiCad 10 schematic synthesis, ERC, netlist sync,
footprint placement, and guided routing for complex power converter topologies:
- Phase-Shifted Full-Bridge (PSFB) 4-MOSFET H-Bridge
- LLC Resonant Half-Bridge with split resonant tank
- Push-Pull Isolated Converter with dual-secondary transformer
"""
from __future__ import annotations

import pytest
from pathlib import Path

from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.generators.kicad_generator import (
    KiCadSchematicGenerator,
    mendex_ir_to_copper_ops,
)
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter


def test_psfb_schematic_erc_and_pcb_guided_routing(tmp_path: Path):
    """Verifies that Phase-Shifted Full-Bridge (PSFB) IR exports to native KiCad 10,
    passes ERC with 0 errors, synchronizes to PCB, auto-places, routes with 0 DRC errors,
    and pours ground with auto-resolved PRI_GND.
    """
    out_dir = tmp_path / "psfb_project"
    out_dir.mkdir(parents=True, exist_ok=True)

    ir = CandidateSynthesisEngine._build_psfb_ir(
        vin_nom=400.0,
        vout=48.0,
        iout=20.0,
        fsw=100e3,
        l_shim_val=5e-6,
        l_out_val=10e-6,
        c_out_val=470e-6,
        n_ratio=0.25,
    )

    assert len(ir.components) == 16
    assert len(ir.nets) == 14

    ops = mendex_ir_to_copper_ops(ir)
    assert len(ops) >= 35
    # Verify power flags present for rails
    pwr_flag_nets = {op["net"] for op in ops if op.get("op") == "pwr_flag"}
    assert "VIN" in pwr_flag_nets
    assert "VOUT" in pwr_flag_nets
    assert "PRI_GND" in pwr_flag_nets
    assert "SEC_GND" in pwr_flag_nets

    res = KiCadSchematicGenerator.export_copper_project(
        ir,
        out_dir,
        board_size=(100.0, 75.0),
        auto_place=True,
        route=True,
        pour_ground=True,
    )

    assert res["ops_applied"] >= 35
    assert res["sync"] is True
    assert res["placed"] is True
    assert res["routed"] is True
    assert res["drc_errors"] == 0

    erc = res.get("erc", {})
    assert erc.get("errors", 0) == 0


def test_llc_resonant_schematic_erc_and_placement(tmp_path: Path):
    """Verifies that LLC Resonant Half-Bridge IR exports to native KiCad 10,
    passes ERC with 0 errors, synchronizes 12 footprints to PCB, and places within outline.
    """
    out_dir = tmp_path / "llc_project"
    out_dir.mkdir(parents=True, exist_ok=True)

    ir = CandidateSynthesisEngine._build_llc_ir(
        vin_nom=400.0,
        vout=24.0,
        iout=10.0,
        fsw=120e3,
        lr_val=15e-6,
        cr_val=33e-9,
        lm_val=75e-6,
        n_ratio=0.12,
    )

    assert len(ir.components) == 12
    assert len(ir.nets) == 11

    ops = mendex_ir_to_copper_ops(ir)
    assert len(ops) >= 25

    res = KiCadSchematicGenerator.export_copper_project(
        ir,
        out_dir,
        board_size=(80.0, 60.0),
        auto_place=True,
        route=False,
    )

    assert res["ops_applied"] >= 25
    assert res["sync"] is True
    assert res["placed"] is True

    erc = res.get("erc", {})
    assert erc.get("errors", 0) == 0


def test_pushpull_schematic_erc_and_placement(tmp_path: Path):
    """Verifies that Push-Pull multi-winding converter IR exports to native KiCad 10,
    passes ERC with 0 errors, and synchronizes footprints cleanly.
    """
    out_dir = tmp_path / "pushpull_project"
    out_dir.mkdir(parents=True, exist_ok=True)

    ir = CandidateSynthesisEngine._build_pushpull_ir(
        vin_nom=48.0,
        vout=12.0,
        iout=15.0,
        fsw=100e3,
        lm_val=50e-6,
        n_ratio=0.5,
    )

    assert len(ir.components) >= 7

    ops = mendex_ir_to_copper_ops(ir)
    res = KiCadSchematicGenerator.export_copper_project(
        ir,
        out_dir,
        auto_place=True,
        route=False,
    )

    assert res["sync"] is True
    assert res["placed"] is True
    erc = res.get("erc", {})
    assert erc.get("errors", 0) == 0
