"""Tests for Mendex Engineering Studio v2.1 Engineering Projects architecture."""
import json
import pytest
from pathlib import Path
from mendex_core.controller import MendexEngineeringController
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.cli import main as cli_main


@pytest.fixture
def proj_controller(tmp_path):
    return MendexEngineeringController(tmp_path)


def test_project_lifecycle_and_single_record(proj_controller, tmp_path):
    """Verifies that an engineering project provides a unified record without duplicate workspace entities."""
    # 1. Initially empty
    assert len(proj_controller.list_projects()) == 0

    # 2. Create project
    created = proj_controller.create_project(
        name="SpectraVolt SV1000",
        code="SV1000",
        category="dc_dc_converter",
        owner="Antigravity",
        description="Precision High Voltage Isolated DC-DC Converter",
    )
    assert created["status"] == "CREATED"
    assert created["code"] == "SV1000"
    pid = created["project_id"]
    assert created["workspace_id"] == pid  # Zero-duplication unified identity

    # 3. Verify exactly 1 project exists
    projects = proj_controller.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_id"] == pid
    assert projects[0]["code"] == "SV1000"
    assert projects[0]["owner"] == "Antigravity"

    # 4. Get comprehensive project dashboard
    dashboard = proj_controller.get_project(pid)
    assert dashboard["project_id"] == pid
    assert dashboard["code"] == "SV1000"
    assert dashboard["active_revision_label"] == "R001"
    assert len(dashboard["revisions"]) == 1
    assert dashboard["simulations_count"] == 0

    # 5. Save specifications to project
    spec_data = {
        "vin_min_v": 20.0,
        "vin_nom_v": 24.0,
        "vin_max_v": 28.0,
        "vout_v": 1000.0,
        "iout_a": 0.1,
        "switching_frequency_hz": 120000.0,
    }
    saved_spec = proj_controller.save_project_specification(pid, spec_data)
    assert saved_spec["status"] == "UPDATED"

    # 6. Retrieve project specifications
    retrieved_spec = proj_controller.get_project_specifications(pid)
    assert retrieved_spec["specification"]["vin_nom_v"] == 24.0
    assert retrieved_spec["specification"]["vout_v"] == 1000.0
    assert len(retrieved_spec["input_hash"]) == 64

    # 7. Generate design directly using project_id
    design = proj_controller.generate_design(
        workspace_id=pid,
        title="SV1000 Flyback Converter",
        vin_nom=24.0,
        vout=1000.0,
        iout=0.1,
        fsw_hz=120000.0,
        ripple_v=0.05,
    )
    assert design["status"] == "SYNTHESIZED"
    artifacts = proj_controller.list_design_artifacts(pid)
    assert len(artifacts) >= 1

    # 8. Clean project deletion
    del_res = proj_controller.delete_project(pid)
    assert del_res["status"] == "DELETED"
    assert len(proj_controller.list_projects()) == 0


def test_mcp_project_tools(tmp_path):
    """Verifies that Antigravity, Codex, and Claude Code can interact with projects via MCP."""
    server = MendexMCPServer(tmp_path)

    def call_tool(name, args):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }
        res = server.handle_request(req)
        assert "error" not in res, f"MCP tool error: {res.get('error')}"
        return json.loads(res["result"]["content"][0]["text"])

    # 1. List projects
    res = call_tool("list_projects", {})
    assert res == []

    # 2. Create project
    create_res = call_tool("create_project", {
        "name": "Micro Grid Inverter",
        "code": "MGI-500",
        "category": "dc_dc_converter",
        "owner": "Antigravity",
    })
    assert create_res["status"] == "CREATED"
    pid = create_res["project_id"]

    # 3. Get project
    proj_info = call_tool("get_project", {"project_id": pid})
    assert proj_info["code"] == "MGI-500"

    # 4. Save specification
    save_res = call_tool("save_project_specification", {
        "project_id": pid,
        "spec_data": {"vin_nom_v": 400.0, "vout_v": 230.0, "iout_a": 2.2},
    })
    assert save_res["status"] == "UPDATED"

    # 5. Delete project
    del_res = call_tool("delete_project", {"project_id": pid})
    assert del_res["status"] == "DELETED"


def test_cli_project_commands(tmp_path, capsys):
    """Verifies project commands via the standard CLI interface."""
    # List (empty)
    cli_main(["--root", str(tmp_path), "projects"])
    out = capsys.readouterr().out
    assert json.loads(out) == []

    # Create project
    cli_main(["--root", str(tmp_path), "create-project", "Test CLI Project", "--code", "CLI-01"])
    out_create = capsys.readouterr().out
    created = json.loads(out_create)
    assert created["status"] == "CREATED"
    pid = created["project_id"]

    # Show project
    cli_main(["--root", str(tmp_path), "project", "show", pid])
    out_show = capsys.readouterr().out
    show_data = json.loads(out_show)
    assert show_data["code"] == "CLI-01"

    # Delete project
    cli_main(["--root", str(tmp_path), "delete-project", pid])
    out_del = capsys.readouterr().out
    del_data = json.loads(out_del)
    assert del_data["status"] == "DELETED"
