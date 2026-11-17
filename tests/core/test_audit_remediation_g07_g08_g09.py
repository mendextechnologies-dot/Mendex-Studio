"""Tests for Audit Remediation G07 (Sourcing Truthfulness), G08 (Manufacturing Exports), and G09 (Assembly Reconciliation)."""
import json
from unittest.mock import patch
import pytest
from pathlib import Path
from mendex_core.models import Category
from mendex_core.service import StudioService
from mendex_core.design.assembly_reconciliation import reconcile_assembly
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService


def test_g07_unsourced_mpns_never_receive_invented_procurement_facts(tmp_path):
    """G07: Unknown or unsourced components receive UNSOURCED lifecycle and NOT_EVALUATED risk."""
    service = StudioService(tmp_path)
    product = service.create_product("BOM-01", "Sourcing Test", Category.DC_DC, "Procurement Engineer")
    rev = service.get_revision(product.active_revision_id)
    ws_dir = service.workspace_path(rev)

    # Create BOM with an unknown/custom MPN
    bom_dir = ws_dir / "bom"
    bom_dir.mkdir(parents=True, exist_ok=True)
    custom_bom = [
        {
            "reference": "R99",
            "value": "10k",
            "footprint": "Resistor_SMD:R_0805",
            "description": "Custom Pullup",
            "manufacturer": "CustomCorp",
            "mpn": "CUSTOM-XYZ-999",
            "quantity": 1,
            "dnp": False,
        }
    ]
    (bom_dir / "bom.json").write_text(json.dumps(custom_bom, indent=2), encoding="utf-8")

    schedule = service.generate_bom_pricing_schedule(rev.revision_id)
    assert schedule["success"] is True
    lines = schedule["items"]
    assert len(lines) == 1
    item = lines[0]
    assert item["mpn"] == "CUSTOM-XYZ-999"
    assert item["distributor"] is None
    assert item["lead_time_weeks"] is None
    assert item["lifecycle"] == "UNSOURCED"
    assert item["sourcing_risk"] == "NOT_EVALUATED"
    assert item["price_source"] == "PARAMETRIC_MODEL"


def test_g08_kicad_exports_raise_on_empty_files(tmp_path):
    """G08: KiCad export routines fail-closed and raise RuntimeError if output file is 0 bytes or missing."""
    kicad = KiCadLifecycleService()
    fake_pcb = tmp_path / "test.kicad_pcb"
    fake_pcb.touch()

    # Mock subprocess.run so it succeeds without creating the expected non-zero file
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        # Output file does not exist -> must raise RuntimeError
        with pytest.raises(RuntimeError, match="empty or missing output file"):
            kicad.export_pos(fake_pcb, tmp_path / "missing_pos.csv")

        with pytest.raises(RuntimeError, match="empty or missing output file"):
            kicad.export_ipcd356(fake_pcb, tmp_path / "missing_ipc.d356")

        with pytest.raises(RuntimeError, match="empty or missing output file"):
            kicad.export_stats(fake_pcb, tmp_path / "missing_stats.json")

        # Output file exists but is 0 bytes -> must raise RuntimeError
        empty_out = tmp_path / "zero_bytes.csv"
        empty_out.touch()
        with pytest.raises(RuntimeError, match="empty or missing output file"):
            kicad.export_pos(fake_pcb, empty_out)


def test_g09_assembly_reconciliation_detects_mismatches_and_dnp_conflicts():
    """G09: Cross-file semantic gate catches unplaced BOM parts, unlisted CPL parts, and erroneous DNP."""
    bom_items = [
        {"ref": "R1", "mpn": "RC0805FR-0710KL", "package": "R_0805", "dnp": False},
        {"ref": "R2", "mpn": "RC0805FR-0710KL", "package": "R_0805", "dnp": True},  # DNP
        {"ref": "C1", "mpn": "CL21B104KBCNNNC", "package": "C_0805", "dnp": False},
        {"ref": "U1", "mpn": "LM5116MH", "package": "HTSSOP-20", "dnp": False},  # In BOM, not in CPL
    ]

    cpl_items = [
        {"Ref": "R1", "PosX": 10.0, "PosY": 20.0, "Rot": 0.0, "Side": "top", "Package": "R_0805"},
        {"Ref": "R2", "PosX": 15.0, "PosY": 20.0, "Rot": 90.0, "Side": "top", "Package": "R_0805"},  # In CPL but marked DNP in BOM!
        {"Ref": "C1", "PosX": 20.0, "PosY": 20.0, "Rot": 0.0, "Side": "top", "Package": "C_0603"},  # Package mismatch (0805 vs 0603)
        {"Ref": "D1", "PosX": 30.0, "PosY": 20.0, "Rot": 0.0, "Side": "top", "Package": "SMA"},  # In CPL, not in BOM!
    ]

    pcb_footprints = [
        {"ref": "R1", "name": "R_0805"},
        {"ref": "R2", "name": "R_0805"},
        {"ref": "C1", "name": "C_0603"},
        {"ref": "D1", "name": "SMA"},
    ]

    res = reconcile_assembly(bom_items, cpl_items, pcb_footprints)
    assert res["reconciliation_status"] == "DISCREPANCIES_FOUND"
    assert res["is_matched"] is False
    assert "U1" in res["unplaced_bom_parts"]
    assert "D1" in res["unlisted_cpl_parts"]
    assert "R2" in res["erroneous_dnp_in_cpl"]
    assert any(m["ref"] == "C1" for m in res["package_mismatches"])
