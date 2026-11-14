from pathlib import Path
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import ProjectQuery


def test_emc100_lifecycle_stages_and_manual_reviews():
    studio = StudioService(Path("."))
    desktop = DesktopService(studio)
    prod = studio.get_product("5b0852dd-7920-4451-b869-049f46254387")
    rev = studio.get_revision(prod.active_revision_id)

    # 1. Inspect lifecycle status via core service
    lifecycle = studio.engineering_lifecycle.get(rev.revision_id)
    assert lifecycle["definition_id"] == "engineering"

    completed_stages = [s for s in lifecycle["stages"] if s["status"] == "COMPLETED"]
    assert len(completed_stages) >= 8

    completed_ids = {s["definition"]["id"] for s in completed_stages}
    expected_completed = {
        "project_initialization",
        "requirements",
        "feasibility",
        "calculations",
        "design_development",
        "simulation",
        "verification",
        "documentation",
    }
    assert expected_completed.issubset(completed_ids)

    # 2. Verify physical prototype testing remains NOT_STARTED / NOT_EVALUATED
    proto_stage = next(s for s in lifecycle["stages"] if s["definition"]["id"] == "prototype_testing")
    assert proto_stage["status"] == "NOT_STARTED"
    assert proto_stage["acceptance_status"] == "NOT_EVALUATED"

    # 3. Verify manual review decisions are recorded with honest attribution
    for stage_id in ["requirements", "feasibility", "calculations", "design_development", "simulation", "verification", "documentation"]:
        reviews = studio.reviews.list_reviews(rev.revision_id, stage_id)
        assert len(reviews) > 0
        latest_rev = reviews[-1]
        assert latest_rev["decision"] == "APPROVED"
        assert latest_rev["review_mode"] == "MANUALLY_DECLARED"
        assert latest_rev["identity_authenticated"] is False
        assert latest_rev["reviewer_name"] == "Senior Electrical Architect"

    # 4. Verify DesktopService.project exposes the full lifecycle
    proj_view = desktop.project(ProjectQuery(
        project_id=str(prod.product_id),
        revision_id=str(rev.revision_id),
    ))
    lc_view = proj_view.get("lifecycle", {})
    assert lc_view is not None
    desktop_completed = [s for s in lc_view.get("stages", []) if s["status"] == "COMPLETED"]
    assert len(desktop_completed) >= 8


def test_get_evidence_content_and_browser_inspection():
    studio = StudioService(Path("."))
    desktop = DesktopService(studio)
    prod = studio.get_product("5b0852dd-7920-4451-b869-049f46254387")
    rev = studio.get_revision(prod.active_revision_id)
    vals = studio.list_validation(rev.revision_id)
    assert len(vals) > 0

    # 1. Fetch KiCad ERC evidence content for in-browser rendering
    erc_val = next(v for v in vals if v.check.check_id == "VAL-KICAD-ERC")
    res = desktop.dispatch("get_evidence", {"record_id": str(erc_val.record_id)})
    assert res["check_id"] == "VAL-KICAD-ERC"
    assert res["evidence_filename"] == "evidence.json"
    assert res["extension"] == ".json"
    assert res["size_bytes"] > 0
    assert len(res["content"]) > 0
    assert res["json_data"] is not None
    assert "$schema" in res["json_data"]

    # 2. Fetch Feasibility evidence content
    feas_val = next(v for v in vals if v.check.check_id == "feasibility_acceptance")
    fres = desktop.dispatch("get_evidence", {"record_id": str(feas_val.record_id)})
    assert fres["check_id"] == "feasibility_acceptance"
    assert fres["extension"] == ".json"
    assert fres["json_data"] is not None
