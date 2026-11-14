"""Tests for Requirements Traceability Matrix (RTM) data model and desktop integration."""
from pathlib import Path
from uuid import uuid4
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.models import Specification
from mendex_core.evidence import specification_hash


def test_requirements_traceability_data_retrieval(tmp_path):
    """Verifies DesktopService provides requirements snapshots and linked specification fields."""
    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    # Create test product with specification
    prod = service.create_product(
        code="RTM-100",
        name="Traceability Test Unit",
        category="dc_dc_converter",
        owner="Test Lead",
    )
    rev = service.get_revision(prod.active_revision_id)
    spec = Specification(
        vin_nom_v=24.0,
        vout_v=100.0,
        iout_a=2.0,
        isolation_requirement="1500 Vrms",
        source="Test Spec",
    )
    service.update_specification(rev.revision_id, spec)

    # Enroll revision into lifecycle definition
    service.engineering_lifecycle.enroll({
        "revision_id": str(rev.revision_id),
        "source": "test-runner",
        "reason": "Lifecycle enrollment for RTM test",
        "idempotency_key": "enroll-rtm",
    })

    # Start requirements stage attempt
    service.engineering_lifecycle.apply({
        "schema_version": "3.1.0",
        "revision_id": str(rev.revision_id),
        "stage_id": "requirements",
        "action": "start",
        "source": "test-runner",
        "reason": "Start requirements stage",
        "idempotency_key": "start-reqs",
    })

    # Record requirements snapshot
    service.engineering_records.save_requirements({
        "revision_id": str(rev.revision_id),
        "stage_id": "requirements",
        "expected_input_hash": specification_hash(spec),
        "idempotency_key": str(uuid4()),
        "source": "System Requirements Document v1.0",
        "reason": "Initial baseline capture",
        "requirements": [
            {
                "id": "req_vout_reg",
                "discipline": "electrical",
                "description": "Nominal output voltage regulation",
                "specification_field": "vout_v",
                "target_value": 100.0,
                "unit": "V",
                "acceptance_criterion": "Output reaches 100V +/- 1V",
                "source": "SRD Section 3.1",
                "mandatory": True,
            },
            {
                "id": "req_isolation",
                "discipline": "safety",
                "description": "Galvanic isolation rating",
                "specification_field": "isolation_requirement",
                "target_value": None,
                "unit": "Vrms",
                "acceptance_criterion": "1500 Vrms dielectric withstand",
                "source": "IEC 61010-1",
                "mandatory": True,
            },
            {
                "id": "req_iout_cap",
                "discipline": "performance",
                "description": "Continuous output current capability",
                "specification_field": "iout_a",
                "target_value": 2.0,
                "unit": "A",
                "acceptance_criterion": "2.0A continuous into rated load",
                "source": "SRD Section 3.2",
                "mandatory": False,
            },
        ],
    })

    # Retrieve project data via DesktopService
    proj_data = desktop.dispatch("project", {
        "project_id": str(prod.product_id),
        "revision_id": str(rev.revision_id),
    })

    reqs_container = proj_data.get("requirements", {})
    records = reqs_container.get("records", []) if isinstance(reqs_container, dict) else reqs_container
    assert len(records) == 1

    snapshot = records[0]
    items = snapshot.get("requirements", [])
    assert len(items) == 3

    # Verify requirement item fields
    req1 = next(r for r in items if r["id"] == "req_vout_reg")
    assert req1["discipline"] == "electrical"
    assert req1["target_value"] == 100.0
    assert req1["unit"] == "V"
    assert req1["specification_field"] == "vout_v"
    assert req1["mandatory"] is True

    # Verify correlation against active specification
    spec_data = proj_data["revision"]["specification"]
    assert spec_data["vout_v"] == req1["target_value"]

    req2 = next(r for r in items if r["id"] == "req_isolation")
    assert req2["discipline"] == "safety"
    assert req2["mandatory"] is True

    req3 = next(r for r in items if r["id"] == "req_iout_cap")
    assert req3["discipline"] == "performance"
    assert req3["target_value"] == 2.0
    assert req3["mandatory"] is False


def test_requirements_traceability_matrix_card_mounting():
    """Verifies that RequirementsTraceabilityMatrixCard is exported and mounted in RevisionEngineeringPanel."""
    root = Path(__file__).resolve().parent.parent.parent
    rtm_card = root / "desktop" / "src" / "components" / "RequirementsTraceabilityMatrixCard.tsx"
    panel = root / "desktop" / "src" / "components" / "RevisionEngineeringPanel.tsx"

    assert rtm_card.exists()
    assert panel.exists()

    card_content = rtm_card.read_text(encoding="utf-8")
    assert "RequirementsTraceabilityMatrixCard" in card_content
    assert "handleExportCSV" in card_content
    assert "handleCopyMarkdown" in card_content
    assert "filteredRequirements" in card_content

    panel_content = panel.read_text(encoding="utf-8")
    assert "RequirementsTraceabilityMatrixCard" in panel_content
    assert "<RequirementsTraceabilityMatrixCard" in panel_content
