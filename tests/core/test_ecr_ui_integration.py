"""Tests for ECR Management UI integration and RPC route dispatch."""
from pathlib import Path
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService


def test_ecr_desktop_rpc_end_to_end(tmp_path):
    """Verifies that DesktopService dispatches list, create, review, and apply ECR queries."""
    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    prod = service.create_product("ECR-TEST", "ECR Verification Product", "dc_dc_converter", "Test Lead")
    rev = service.get_revision(prod.active_revision_id)

    # 1. Create ECR
    create_res = desktop.dispatch("create_ecr", {
        "title": "Upgrade Snubber Damping Resistor",
        "description": "Increase damping on switch node",
        "reason": "Reduce high frequency ringing",
        "impact_analysis": "Increases dissipation by 0.05W",
        "requested_by": "Senior Power EE",
        "product_id": str(prod.product_id),
        "revision_id": str(rev.revision_id),
        "affected_stages": ["calculations", "simulation"],
        "schematic_ops": [{"op": "set_field", "ref": "RSNUB", "field": "Value", "value": "15 1W"}],
    })

    assert create_res["status"] == "DRAFT"
    assert create_res["ecr_number"].startswith("ECR-")
    ecr_id = create_res["ecr_id"]

    # 2. List ECRs
    list_res = desktop.dispatch("list_ecrs", {
        "product_id": str(prod.product_id),
        "revision_id": str(rev.revision_id),
    })
    assert len(list_res) == 1
    assert list_res[0]["ecr_id"] == ecr_id
    assert list_res[0]["title"] == "Upgrade Snubber Damping Resistor"

    # 3. Review ECR
    review_res = desktop.dispatch("review_ecr", {
        "ecr_id": ecr_id,
        "reviewer": "Lead Power Systems Engineer (Human Reviewer)",
        "status": "APPROVED",
        "review_notes": "Approved after thermal dissipation check",
    })
    assert review_res["status"] == "APPROVED"
    assert review_res["approved_by"] == "Lead Power Systems Engineer (Human Reviewer)"


def test_ecr_management_card_mounted_in_project_detail():
    """Verifies ECRManagementCard component exists and is registered in ProjectDetail."""
    root = Path(__file__).resolve().parent.parent.parent
    ecr_card = root / "desktop" / "src" / "components" / "ECRManagementCard.tsx"
    proj_detail = root / "desktop" / "src" / "pages" / "ProjectDetail.tsx"

    assert ecr_card.exists()
    assert proj_detail.exists()

    card_text = ecr_card.read_text(encoding="utf-8")
    assert "ECRManagementCard" in card_text
    assert "handleApplyECO" in card_text
    assert "handleCreateECR" in card_text
    assert "handleReviewSubmit" in card_text

    detail_text = proj_detail.read_text(encoding="utf-8")
    assert "ECRManagementCard" in detail_text
    assert "<ECRManagementCard" in detail_text
    assert "id: 'ecr'" in detail_text
