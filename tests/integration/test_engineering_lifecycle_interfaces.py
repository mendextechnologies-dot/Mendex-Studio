"""Cross-client lifecycle records, retries and strict contracts."""
import json
from uuid import uuid4

from mendex_core.cli import main
from mendex_core.engineering_lifecycle.api import OPERATIONS
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.service import StudioService


def call(server, name, arguments):
    response = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                      "params": {"name": name, "arguments": arguments}})["result"]
    return response["isError"], json.loads(response["content"][0]["text"])


def test_cli_mcp_share_records_without_duplicate_projects(tmp_path, capsys):
    service = StudioService(tmp_path)
    product = service.create_product("INTERFACE", "Generic software fixture", "pcb", "Fixture engineer")
    rid = str(product.active_revision_id)
    # Start an observer before the other client changes anything.
    observer = MendexMCPServer(tmp_path)
    names = {tool["name"] for tool in observer.tools_schema}
    assert set(OPERATIONS).issubset(names)
    path = tmp_path / "request.json"
    request = {"revision_id": rid, "source": "CLI fixture", "reason": "Explicit enrollment", "idempotency_key": "enroll-once"}
    path.write_text(json.dumps(request), encoding="utf-8")
    assert main(["--root", str(tmp_path), "lifecycle", "enroll", str(path)]) == 0
    first = json.loads(capsys.readouterr().out)
    error, replay = call(observer, "enroll_lifecycle", request)
    assert not error and replay == first
    command = {"revision_id": rid, "stage_id": "project_initialization", "action": "start",
               "source": "MCP fixture", "reason": "Initialize project context", "idempotency_key": "start-once"}
    error, started = call(observer, "apply_lifecycle_stage", command)
    assert not error and started["status"] == "IN_PROGRESS"
    assert main(["--root", str(tmp_path), "lifecycle", "show", rid]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view["stages"][0]["status"] == "IN_PROGRESS"
    assert len(StudioService(tmp_path).list_products()) == 1
    assert main(["--root", str(tmp_path), "lifecycle", "history", rid, "--limit", "1"]) == 0
    assert len(json.loads(capsys.readouterr().out)["events"]) == 1


def test_strict_errors_and_no_agent_approval(tmp_path, capsys):
    server = MendexMCPServer(tmp_path)
    error, result = call(server, "get_project_lifecycle", {"revision_id": "not-a-uuid", "extra": True})
    assert error and result["error"] == "INVALID_INPUT"
    assert result["schema_version"] == "3.1.0"
    assert main(["--root", str(tmp_path), "lifecycle", "show", "not-a-uuid"]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "INVALID_INPUT"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"revision_id": str(uuid4()), "action": "approve", "stage_id": "verification",
                                "source": "Agent", "reason": "Untrusted self-approval", "idempotency_key": "bad"}))
    assert main(["--root", str(tmp_path), "lifecycle", "apply", str(path)]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "INVALID_INPUT"
    assert not any("approve" in name for name in OPERATIONS)


def test_definition_discovery_and_registration_through_both_clients(tmp_path, capsys):
    server = MendexMCPServer(tmp_path)
    assert main(["--root", str(tmp_path), "lifecycle", "definitions"]) == 0
    definitions = json.loads(capsys.readouterr().out)
    assert len(definitions[0]["stages"]) == 9
    error, definition = call(server, "get_lifecycle_definition", {})
    assert not error and definition == definitions[0]
    definition["id"] = "discipline_fixture"
    path = tmp_path / "definition.json"
    path.write_text(json.dumps({"definition": definition, "source": "Engineer-supplied test policy"}))
    assert main(["--root", str(tmp_path), "lifecycle", "register", str(path)]) == 0
    registered = json.loads(capsys.readouterr().out)
    error, data = call(server, "get_lifecycle_definition", {"definition_id": "discipline_fixture"})
    assert not error and registered["definition"] == data
    error, _ = call(server, "list_lifecycle_definitions", {"shell": "arbitrary"})
    assert error
