"""Unit and integration tests for Mendex MCP Server v2.1."""
import io
import json
import pytest

from mendex_core.mcp.server import MendexMCPServer


@pytest.fixture
def mcp_server(tmp_path):
    return MendexMCPServer(data_root=tmp_path)


def test_mcp_initialize(mcp_server):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    resp = mcp_server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "mendex-engineering-mcp"
    assert "tools" in resp["result"]["capabilities"]


def test_mcp_ping(mcp_server):
    req = {"jsonrpc": "2.0", "id": 42, "method": "ping"}
    resp = mcp_server.handle_request(req)
    assert resp["id"] == 42
    assert resp["result"] == {}


def test_mcp_tools_list(mcp_server):
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = mcp_server.handle_request(req)
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    assert len(tools) >= 18
    tool_names = {t["name"] for t in tools}
    assert "list_workspaces" in tool_names
    assert "create_workspace" in tool_names
    assert "generate_design" in tool_names
    assert "run_engineering_calculations" in tool_names
    assert "run_simulation" in tool_names
    assert "list_tools" in tool_names
    assert "generate_engineering_report" in tool_names


def test_mcp_tool_call_calculations(mcp_server):
    # Test Dowell calculation via MCP
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "run_engineering_calculations",
            "arguments": {
                "calc_type": "dowell",
                "params": {
                    "frequency_hz": 120000.0,
                    "layers": 3,
                    "conductor_diameter_mm": 0.4,
                    "layer_porosity_factor": 0.85,
                    "r_dc_ohm": 0.05,
                    "temperature_c": 100.0,
                },
            },
        },
    }
    resp = mcp_server.handle_request(req)
    assert resp["id"] == 10
    assert resp["result"]["isError"] is False
    content_text = resp["result"]["content"][0]["text"]
    calc_data = json.loads(content_text)
    assert calc_data["calculation"] == "dowell_ac_winding_factor"
    assert calc_data["f_r"] >= 1.0


def test_mcp_workflow_call(mcp_server, tmp_path):
    # 1. Create workspace
    req_ws = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {
            "name": "create_workspace",
            "arguments": {"name": "MCP Converter WS"},
        },
    }
    resp_ws = mcp_server.handle_request(req_ws)
    assert resp_ws["result"]["isError"] is False
    ws_data = json.loads(resp_ws["result"]["content"][0]["text"])
    ws_id = ws_data["workspace_id"]

    # 2. Synthesize Design
    req_gen = {
        "jsonrpc": "2.0",
        "id": 21,
        "method": "tools/call",
        "params": {
            "name": "generate_design",
            "arguments": {
                "workspace_id": ws_id,
                "title": "MCP Buck 24V-5V",
                "vin_nom": 24.0,
                "vout": 5.0,
                "iout": 4.0,
            },
        },
    }
    resp_gen = mcp_server.handle_request(req_gen)
    assert resp_gen["result"]["isError"] is False
    gen_data = json.loads(resp_gen["result"]["content"][0]["text"])
    assert gen_data["status"] == "SYNTHESIZED"

    # 3. Check Workspace Status
    req_st = {
        "jsonrpc": "2.0",
        "id": 22,
        "method": "tools/call",
        "params": {
            "name": "get_workspace_status",
            "arguments": {"workspace_id": ws_id},
        },
    }
    resp_st = mcp_server.handle_request(req_st)
    st_data = json.loads(resp_st["result"]["content"][0]["text"])
    assert st_data["design_count"] == 1


def test_mcp_stdio_stream(mcp_server):
    # Simulate a full stdio conversation: initialize -> ping -> tools/list
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    ]
    input_str = "\n".join(json.dumps(m) for m in messages) + "\n"
    in_stream = io.StringIO(input_str)
    out_stream = io.StringIO()

    mcp_server.run_stdio(input_stream=in_stream, output_stream=out_stream)

    lines = [json.loads(line) for line in out_stream.getvalue().strip().split("\n") if line]
    assert len(lines) == 2  # initialize response and ping response (notification produces no response)
    assert lines[0]["id"] == 1
    assert lines[1]["id"] == 2
