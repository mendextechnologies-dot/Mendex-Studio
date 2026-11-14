"""Unit and integration tests for Incremental Schematic ECR -> PCB Forward Annotation (ECO Engine)."""
from __future__ import annotations

import pytest
from pathlib import Path

from copper_kicad.mcp.registry import call_tool
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
from mendex_core.desktop.service import DesktopService, ROUTES
from mendex_core.lifecycle.ecr import ECRStatus
from mendex_core.service import StudioService, StudioError


def test_forward_annotate_pcb_incremental_ecr(tmp_path):
    """Verifies that an approved ECR applies schematic changes and incrementally forward-annotates to PCB layout."""
    service = StudioService(tmp_path)

    # 1. Setup a test project in a mock draft revision
    product = service.create_product(
        code="ECO-100",
        name="ECO Proof of Concept",
        category="dc_dc_converter",
        owner="Hardware Engineer",
        description="Forward annotation test product",
    )
    rev = service.create_revision(product.product_id, "REV_A")
    rev_dir = service.workspace_path(rev)
    pcb_dir = rev_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # 2. Synthesize initial KiCad project and layout
    call_tool("project_create", {
        "name": "pcb",
        "dir": str(pcb_dir),
        "board_size": [50.0, 35.0],
        "fab": "jlcpcb",
    })
    sch_file = pcb_dir / "pcb.kicad_sch"
    pcb_file = pcb_dir / "pcb.kicad_pcb"

    init_ops = [
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
    call_tool("sch_apply", {"project": str(pcb_dir), "ops": init_ops, "verify": True})
    call_tool("pcb_sync", {"project": str(pcb_dir)})
    adapter = CopperKiCadAdapter()
    adapter.place_pcb(pcb_file, auto=True)
    route_res = adapter.route_pcb(pcb_file, pour_ground=True, ground_net="GND")
    assert route_res.get("tracks", 0) > 0

    # Read state before ECO
    read_before = call_tool("pcb_read", {
        "project": str(pcb_dir),
        "what": ["summary", "footprints", "tracks", "zones"],
    })
    sc_before = read_before.get("structuredContent") or {}
    fps_before = {f["ref"]: f for f in sc_before.get("footprints", [])}
    tracks_before = sc_before.get("tracks", 0)
    outline = sc_before.get("outline") or {}

    assert "R1" in fps_before
    assert "R2" in fps_before
    assert fps_before["R1"]["value"] == "10k 1%"

    # 3. Create ECR with value upgrade and new decoupling capacitor
    ecr = service.ecr.create_ecr(
        title="Upgrade Voltage Divider Resistor & Add Bypass Capacitor",
        description="Change R1 to 20k 0.1% and add C1 100nF bypass capacitor on Vin",
        reason="Improve divider accuracy and attenuate switching ripple",
        impact_analysis="Reduces Vin noise and recalibrates output scaling",
        requested_by="Principal EE",
        affected_stages=["CIRCUIT_DESIGN", "PCB_DESIGN"],
        product_id=product.product_id,
        revision_id=rev.revision_id,
        schematic_ops=[
            {"op": "set_field", "ref": "R1", "field": "Value", "value": "20k 0.1%"},
            {"op": "place", "lib_id": "Device:C", "ref": "C1", "value": "100nF", "footprint": "Capacitor_SMD:C_0805_2012Metric"},
            {"op": "connect", "pin": "C1.1", "net": "Vin"},
            {"op": "connect", "pin": "C1.2", "net": "GND"},
        ],
    )

    # 4. Review and approve ECR
    service.ecr.review_ecr(
        ecr_id=ecr.ecr_id,
        reviewer="Engineering Director",
        status=ECRStatus.APPROVED,
        review_notes="Approved for incremental implementation.",
    )

    # 5. Apply schematic change with forward annotation enabled
    result = service.ecr.apply_schematic_change(
        ecr_id=ecr.ecr_id,
        implemented_by="Automated ECO Engine",
        forward_annotate=True,
    )

    assert result["success"] is True
    assert result["status"] == "IMPLEMENTED"
    assert result["eco"] is not None
    assert result["eco"]["success"] is True
    assert result["eco"]["added_count"] == 1
    assert "C1" in result["eco"]["added_refs"]
    assert result["eco"]["tracks_preserved"] is True

    # 6. Read state after ECO and verify physical layout invariants
    read_after = call_tool("pcb_read", {
        "project": str(pcb_dir),
        "what": ["summary", "footprints", "tracks", "zones"],
    })
    sc_after = read_after.get("structuredContent") or {}
    fps_after = {f["ref"]: f for f in sc_after.get("footprints", [])}
    tracks_after = sc_after.get("tracks", 0)

    # Verification A: Newly added component C1 exists on board
    assert "C1" in fps_after, "Newly added C1 missing from PCB after ECO forward annotation"
    assert fps_after["C1"]["value"] == "100nF"

    # Verification B: C1 is placed inside board bounding box (not left unplaced at 0, 0)
    bbox = outline.get("bbox", [100.0, 100.0, 150.0, 135.0])
    c1_pos = fps_after["C1"]
    assert bbox[0] <= c1_pos["x"] <= bbox[2], f"C1 x ({c1_pos['x']}) outside board bounds ({bbox})"
    assert bbox[1] <= c1_pos["y"] <= bbox[3], f"C1 y ({c1_pos['y']}) outside board bounds ({bbox})"

    # Verification C: Modified component R1 has updated value in layout
    assert fps_after["R1"]["value"] == "20k 0.1%", "R1 value not updated in PCB layout"

    # Verification D: Pre-existing placed components remained fixed in place
    assert fps_before["R1"]["x"] == fps_after["R1"]["x"], "R1 x position was shifted!"
    assert fps_before["R1"]["y"] == fps_after["R1"]["y"], "R1 y position was shifted!"
    assert fps_before["R2"]["x"] == fps_after["R2"]["x"], "R2 x position was shifted!"
    assert fps_before["R2"]["y"] == fps_after["R2"]["y"], "R2 y position was shifted!"

    # Verification E: Pre-existing routed copper tracks were preserved
    assert tracks_after >= tracks_before, f"Routed tracks lost! before={tracks_before}, after={tracks_after}"

    # Verification F: Persisted database record contains complete ECO manifest
    updated_ecr = service.ecr.get_ecr(ecr.ecr_id)
    assert updated_ecr is not None
    assert updated_ecr.eco_result is not None
    assert updated_ecr.eco_result["success"] is True
    assert updated_ecr.eco_result["tracks_preserved"] is True


def test_forward_annotate_pcb_desktop_rpc(tmp_path):
    """Verifies that DesktopService exposes forward_annotate_pcb and respects revision state boundaries."""
    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    assert "forward_annotate_pcb" in ROUTES

    product = service.create_product(
        code="RPC-100",
        name="RPC Test Product",
        category="dc_dc_converter",
        owner="Engineer",
        description="RPC testing",
    )
    rev = service.create_revision(product.product_id, "REV_A")
    rev_dir = service.workspace_path(rev)
    pcb_dir = rev_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Calling forward_annotate_pcb when no PCB exists raises StudioError NOT_FOUND
    with pytest.raises(StudioError) as exc_no_pcb:
        desktop.dispatch("forward_annotate_pcb", {
            "revision_id": str(rev.revision_id),
        })
    assert exc_no_pcb.value.code == "NOT_FOUND"

    # 2. Setup project and PCB
    call_tool("project_create", {
        "name": "pcb",
        "dir": str(pcb_dir),
        "board_size": [40.0, 30.0],
        "fab": "jlcpcb",
    })
    ops = [
        {"op": "place", "lib_id": "Device:R", "ref": "R1", "value": "10k", "footprint": "Resistor_SMD:R_0805_2012Metric"},
    ]
    call_tool("sch_apply", {"project": str(pcb_dir), "ops": ops})
    call_tool("pcb_sync", {"project": str(pcb_dir)})

    # 3. Call forward_annotate_pcb via DesktopService dispatch on draft revision
    res_eco = desktop.dispatch("forward_annotate_pcb", {
        "revision_id": str(rev.revision_id),
        "remove_extra": True,
        "auto_place_new": True,
        "refill_zones": False,
    })
    assert res_eco.get("success") is True
    assert "summary" in res_eco
    assert res_eco.get("tracks_preserved") is True

    # 4. Freeze revision and verify IMMUTABLE boundary
    service.set_revision_status(rev.revision_id, "in_review")
    with pytest.raises(StudioError) as exc_frozen:
        desktop.dispatch("forward_annotate_pcb", {
            "revision_id": str(rev.revision_id),
        })
    assert exc_frozen.value.code == "IMMUTABLE"
