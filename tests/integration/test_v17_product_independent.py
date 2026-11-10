from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.models import EngineeringWorkspace, EngineeringActivity, Category
from mendex_core.integration_contracts import JobRequest, ToolConfiguration


def test_create_engineering_workspace_without_product(tmp_path):
    service = StudioService(tmp_path)
    # 1. Engineer launches Studio and creates workspace with NO product
    ws = service.integrations.create_workspace(
        name="HighFrequency-Magnetic-Study",
        description="Power electronics transformer and inductor optimization",
        owner="Principal Engineer",
    )

    assert ws["name"] == "HighFrequency-Magnetic-Study"
    assert ws["description"] == "Power electronics transformer and inductor optimization"
    assert ws["owner"] == "Principal Engineer"
    assert ws["product_id"] is None
    assert Path(service.integrations.workspace_path(ws["workspace_id"])).exists()

    # 2. Workspace lists correctly
    workspaces = service.integrations.list_workspaces()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "HighFrequency-Magnetic-Study"
    assert workspaces[0]["product_id"] is None


def test_engineering_activity_and_job_lifecycle_without_product(tmp_path):
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Converter Simulation Lab")
    ws_id = ws["workspace_id"]

    # Create engineering activity without product
    act = service.integrations.create_activity(
        workspace_id=ws_id,
        name="Flyback Transient Analysis",
        activity_type="simulation",
        tool_id="studio-demo",
        parameters={"steps": 2, "delay_s": 0, "echo": "BENCHMARK_OK"},
    )

    assert act["name"] == "Flyback Transient Analysis"
    assert act["tool_id"] == "studio-demo"
    assert act["product_id"] is None

    # Submit simulation job linked to activity
    job_req = JobRequest(
        schema_version="1.5.0",
        job_id=uuid4(),
        workspace_id=ws_id,
        tool_id="studio-demo",
        operation="synthetic-echo",
        parameters={"steps": 2, "delay_s": 0, "echo": "BENCHMARK_OK"},
        timeout_s=15,
        provenance="Test suite",
    )

    job_rec = service.integrations.submit(job_req)
    service.integrations.wait(job_req.job_id)

    # Verify execution finished successfully without any product
    completed = service.integrations.job(job_req.job_id)
    assert completed.status.value == "SUCCEEDED"
    assert completed.result.exit_code == 0
    assert len(completed.result.outputs) > 0


def test_optional_product_association_downstream(tmp_path):
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Unassigned Resonant Converter Study")
    act = service.integrations.create_activity(
        workspace_id=ws["workspace_id"],
        name="CLLC Tank Sizing",
        activity_type="calculation",
        tool_id="python",
    )

    # Engineering was completed without a product.
    # Later, product management establishes a product and associates this workspace:
    prod = service.create_product(
        code="MNDX-CLLC-01",
        name="10kW High Voltage CLLC Resonant Converter",
        category="dc_dc_converter",
        owner="Product Manager",
    )

    service.integrations.associate_product(ws["workspace_id"], prod.product_id)

    # Verify association was recorded without invalidating workspace or activity
    updated_ws = service.integrations.get_workspace(ws["workspace_id"])
    assert updated_ws["product_id"] == str(prod.product_id)

    activities = service.integrations.list_activities(ws["workspace_id"])
    assert len(activities) == 1
    assert activities[0]["product_id"] == str(prod.product_id)
