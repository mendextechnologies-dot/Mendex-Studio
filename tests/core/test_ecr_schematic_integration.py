"""Tests for ECR schematic modification integration and lifecycle auditing."""
from __future__ import annotations

from pathlib import Path
import pytest

from copper_kicad.mcp.registry import call_tool
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
from mendex_core.lifecycle.ecr import ECRStatus
from mendex_core.service import StudioService


def test_ecr_schematic_change_lifecycle(tmp_path):
    """Verifies that an approved ECR applies schematic operations and updates audit state."""
    service = StudioService(tmp_path)

    # 1. Setup a test schematic in a mock revision
    product = service.create_product(
        code="POC-100",
        name="Proof of Concept",
        category="dc_dc_converter",
        owner="Engineer",
        description="ECR test product",
    )
    rev = service.create_revision(product.product_id, "REV_A")
    rev_dir = service.workspace_path(rev)
    pcb_dir = rev_dir / "pcb"

    # Synthesize native KiCad 10 reference divider project & schematic
    call_tool("project_create", {
        "name": "pcb",
        "dir": str(rev_dir),
        "board_size": [50.0, 35.0],
        "fab": "jlcpcb",
    })
    init_ops = [
        {"op": "place", "ref": "J1", "lib_id": "Connector:Conn_01x02_Pin", "value": "Vin_In", "at": [100.0, 95.0]},
        {"op": "place", "ref": "R1", "lib_id": "Device:R", "value": "10k 0805", "at": [100.0, 110.0]},
        {"op": "place", "ref": "R2", "lib_id": "Device:R", "value": "10k 0805", "at": [100.0, 125.0]},
        {"op": "place", "ref": "J2", "lib_id": "Connector:Conn_01x02_Pin", "value": "Vout_Out", "at": [100.0, 140.0]},
        {"op": "connect", "net": "Vin", "pin": "J1.1"},
        {"op": "connect", "net": "Vin", "pin": "R1.1"},
        {"op": "connect", "net": "Vdiv", "pin": "R1.2"},
        {"op": "connect", "net": "Vdiv", "pin": "R2.1"},
        {"op": "connect", "net": "Vdiv", "pin": "J2.1"},
        {"op": "connect", "net": "GND", "pin": "R2.2"},
        {"op": "connect", "net": "GND", "pin": "J1.2"},
        {"op": "connect", "net": "GND", "pin": "J2.2"},
        {"op": "pwr_flag", "net": "Vin", "at": [90.0, 95.0]},
        {"op": "pwr_flag", "net": "GND", "at": [90.0, 125.0]},
    ]
    call_tool("sch_apply", {"project": str(pcb_dir), "ops": init_ops, "verify": True})
    sch_file = pcb_dir / "pcb.kicad_sch"
    assert sch_file.exists()

    # 2. Create ECR with schematic change operations
    ecr = service.ecr.create_ecr(
        title="Upgrade Voltage Divider Resistor R1",
        description="Change R1 from 10k to 20k 0.1% for higher accuracy",
        reason="Improve ADC measurement precision by 50%",
        impact_analysis="Affects voltage divider ratio and feedback voltage",
        requested_by="Lead EE",
        affected_stages=["CIRCUIT_DESIGN", "SCHEMATIC_CAPTURE"],
        product_id=product.product_id,
        revision_id=rev.revision_id,
        schematic_ops=[
            {"op": "set_field", "ref": "R1", "field": "Value", "value": "20k 0.1%"},
            {"op": "set_field", "ref": "R1", "field": "MPN", "value": "ERA-6AEB203V"},
        ],
    )

    assert ecr.status == ECRStatus.DRAFT
    assert ecr.schematic_ops is not None
    assert len(ecr.schematic_ops) == 2

    # 3. Attempt to apply while still DRAFT - should be blocked
    with pytest.raises(ValueError, match="must be APPROVED before implementation"):
        service.ecr.apply_schematic_change(ecr.ecr_id)

    # 4. Review and approve the ECR
    reviewed = service.ecr.review_ecr(
        ecr_id=ecr.ecr_id,
        reviewer="Principal Engineer",
        status=ECRStatus.APPROVED,
        review_notes="Approved after tolerance verification.",
    )
    assert reviewed.status == ECRStatus.APPROVED

    # 5. Apply the approved ECR to schematic
    result = service.ecr.apply_schematic_change(
        ecr_id=ecr.ecr_id,
        implemented_by="Automation Agent",
    )

    assert result["success"] is True
    assert result["status"] == "IMPLEMENTED"
    assert result["ops_applied"] == 2
    assert result["checkpoint"] is not None
    assert result["erc"].get("errors", 0) == 0

    # 6. Verify persisted state in database
    updated_ecr = service.ecr.get_ecr(ecr.ecr_id)
    assert updated_ecr is not None
    assert updated_ecr.status == ECRStatus.IMPLEMENTED
    assert updated_ecr.applied_at is not None
    assert updated_ecr.applied_checkpoint == result["checkpoint"]
    assert "Implemented by Automation Agent" in updated_ecr.review_notes

    # 7. Verify the schematic file was actually modified
    content = sch_file.read_text(encoding="utf-8")
    assert "20k 0.1%" in content
    assert "ERA-6AEB203V" in content


def test_desktop_service_ecr_rpc_routes(tmp_path):
    """Verifies that DesktopService exposes typed ECR RPC routes."""
    from mendex_core.desktop.service import DesktopService, ROUTES
    from mendex_core.service import StudioService

    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    assert "list_ecrs" in ROUTES
    assert "create_ecr" in ROUTES
    assert "review_ecr" in ROUTES
    assert "apply_ecr_schematic" in ROUTES

    # 1. Create ECR via dispatch
    create_res = desktop.dispatch("create_ecr", {
        "title": "GaN Switch Upgrade",
        "description": "Switch from SiC to EPC GaN",
        "reason": "Lower RDS(on)",
        "impact_analysis": "Reduces thermals",
        "requested_by": "Power EE",
        "workspace_id": "ws-1",
        "schematic_ops": [{"op": "set_field", "ref": "Q1", "field": "Value", "value": "EPC2019"}],
    })
    assert create_res["ecr_number"].startswith("ECR-")
    assert create_res["status"] == "DRAFT"
    ecr_id = create_res["ecr_id"]

    # 2. List ECRs via dispatch
    list_res = desktop.dispatch("list_ecrs", {"workspace_id": "ws-1"})
    assert len(list_res) == 1
    assert list_res[0]["ecr_id"] == ecr_id

    # 3. Review ECR via dispatch
    review_res = desktop.dispatch("review_ecr", {
        "ecr_id": ecr_id,
        "reviewer": "Reviewing Lead",
        "status": "APPROVED",
        "review_notes": "All checks verified",
    })
    assert review_res["status"] == "APPROVED"
    assert review_res["approved_by"] == "Reviewing Lead"
