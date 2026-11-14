"""CLI/MCP share typed record operations and observe each other's committed writes."""
import json
from uuid import uuid4

import pytest

from mendex_core.cli import main
from mendex_core.engineering_lifecycle.storage import file_hash
from mendex_core.engineering_records.api import OPERATIONS
from mendex_core.evidence import specification_hash
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.service import StudioService


def call(server, operation, request):
    response = server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": operation, "arguments": request}})["result"]
    return response["isError"], json.loads(response["content"][0]["text"])


@pytest.fixture
def clients(tmp_path):
    studio = StudioService(tmp_path)
    product = studio.create_product("AGENTS", "Generic agent software fixture", "pcb", "Fixture engineer")
    rid = str(product.active_revision_id)
    server = MendexMCPServer(tmp_path)
    server.controller.service.engineering_lifecycle.enroll({"revision_id": rid, "source": "Fixture", "reason": "Record fixture", "idempotency_key": "enroll"})
    server.controller.service.engineering_lifecycle.apply({"revision_id": rid, "source": "Fixture", "reason": "Begin fixture", "idempotency_key": "start", "action": "start", "stage_id": "project_initialization"})
    base = {"revision_id": rid, "stage_id": "project_initialization", "source": "Fixture", "reason": "Agent parity fixture",
            "expected_input_hash": specification_hash(studio.get_revision(rid).specification)}
    return studio, server, base


def cli(tmp_path, capsys, operation, request):
    path = tmp_path / (str(uuid4()) + ".json")
    path.write_text(json.dumps(request), encoding="utf-8")
    result = main(["--root", str(tmp_path), "engineering", operation, str(path)])
    output = capsys.readouterr()
    return result, json.loads(output.out if result == 0 else output.err)


def test_metadata_requirements_calculations_and_artifacts_share_records(clients, tmp_path, capsys):
    studio, server, base = clients
    error, metadata = call(server, "get_project_metadata", {"project_id": str(studio.get_revision(base["revision_id"]).product_id)})
    assert not error
    update = {"project_id": metadata["product_id"], "expected_updated_at": metadata["updated_at"], "name": "Agent-updated fixture",
              "owner": metadata["owner"], "description": "No duplicate authoring", "source": "Fixture", "reason": "Agent metadata",
              "idempotency_key": "metadata-once"}
    code, result = cli(tmp_path, capsys, "update_project_metadata", update)
    assert code == 0
    error, replay = call(server, "update_project_metadata", update)
    assert not error and replay == result
    requirements = {**base, "idempotency_key": "requirements-once", "requirements": [
        {"id": "context", "discipline": "mechanical", "description": "Engineer must supply envelope", "source": "Fixture"}]}
    code, saved = cli(tmp_path, capsys, "record_requirements", requirements)
    assert code == 0
    error, records = call(server, "list_requirements", {"revision_id": base["revision_id"]})
    assert not error and records["records"][0]["record_id"] == saved["record_id"]
    calculation = {**base, "idempotency_key": "calc-once", "calculation": "losses", "assumptions": ["Synthetic software values only"],
                   "parameters": {"part_number": "Fixture", "r_ds_on_ohm": 0.02, "i_rms_a": 2, "duty_cycle": 0.4, "e_on_j": 1e-6, "e_off_j": 2e-6, "frequency_hz": 100000}}
    error, computed = call(server, "record_calculation_run", calculation)
    assert not error and computed["status"] == "SUCCEEDED"
    code, listed = cli(tmp_path, capsys, "list_calculation_runs", {"revision_id": base["revision_id"]})
    assert code == 0 and listed["records"][0]["result"] == computed["result"]
    path = studio.workspace_path(studio.get_revision(base["revision_id"])) / "requirements" / "source.txt"
    path.write_text("Software-only artifact fixture")
    artifact = {**base, "idempotency_key": "artifact-once", "relative_path": "requirements/source.txt", "expected_sha256": file_hash(path), "classification": "documentation"}
    code, registered = cli(tmp_path, capsys, "register_engineering_artifact", artifact)
    assert code == 0
    error, read = call(server, "get_engineering_record", {"record_id": registered["record_id"]})
    assert not error and read["snapshot_integrity"] and read["original_integrity"]
    assert len(studio.list_products()) == 1


def test_validation_reports_and_export_share_core(clients, tmp_path, capsys):
    studio, server, base = clients
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("Disposable software fixture, not laboratory evidence")
    validation = {**base, "idempotency_key": "validation-once", "evidence_path": str(evidence), "expected_evidence_sha256": file_hash(evidence),
                  "check": {"check_id": "fixture", "status": "pass", "reviewer": "Unauthenticated test identity", "notes": "Rule fixture only", "evidence_kind": "CALCULATED", "measured_value": 1, "minimum": 0, "maximum": 2, "unit": "V"}}
    error, recorded = call(server, "record_validation_evidence", validation)
    assert not error
    code, results = cli(tmp_path, capsys, "get_validation_results", {"revision_id": base["revision_id"]})
    assert code == 0 and results["results"][0]["record"]["record_id"] == recorded["validation_record"]["record_id"]
    code, generated = cli(tmp_path, capsys, "generate_revision_report", {**base, "idempotency_key": "report-once"})
    assert code == 0
    error, reports = call(server, "list_revision_reports", {"revision_id": base["revision_id"]})
    assert not error and reports[0]["report"]["report_id"] == generated["report"]["report_id"]
    error, exported = call(server, "export_report_package", {"report_id": generated["report"]["report_id"], "source": "Fixture", "reason": "Export fixture", "idempotency_key": "export-once"})
    assert not error and (studio.root / exported["path"]).is_file()


def test_schema_discovery_strict_errors_and_legacy_compatibility(clients, tmp_path, capsys):
    studio, server, base = clients
    names = [tool["name"] for tool in server.tools_schema]
    assert len(names) == len(set(names)) and set(OPERATIONS).issubset(names)
    code = main(["--root", str(tmp_path), "engineering", "list_supported_calculations"])
    assert code == 0 and len(json.loads(capsys.readouterr().out)) >= 4
    error, result = call(server, "get_engineering_record", {"record_id": "invalid", "unknown": True})
    assert error and result["error"] == "INVALID_INPUT"
    code, result = cli(tmp_path, capsys, "record_requirements", {**base, "idempotency_key": "bad", "requirements": [], "approve": True})
    assert code == 1 and result["error"] == "INVALID_INPUT"
    error, projects = call(server, "list_projects", {})
    assert not error and len(projects) == 1
