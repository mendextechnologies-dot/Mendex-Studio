"""Independent audit cases: evidence preservation, explicit inputs and startup races."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.service import StudioService, StudioError


def values(workspace):
    return dict(workspace_id=workspace, title="Generic audit fixture", vin_min=18., vin_nom=24.,
                vin_max=30., vout=5., iout=2., fsw_hz=100000., ripple_v=0.1)


def test_generations_and_regeneration_preserve_registered_bytes(tmp_path):
    ctrl = MendexEngineeringController(tmp_path)
    wid = ctrl.create_workspace("Disposable fixture")["workspace_id"]
    first = ctrl.generate_design(**values(wid))
    originals = {a["path"]: (tmp_path / a["path"]).read_bytes() for a in first["generated_artifacts"]}
    second = ctrl.generate_design(**{**values(wid), "vout": 8.})
    regenerated = ctrl.design_service.generate_native_artifacts(first["design_id"], ctrl._resolve_workspace_dir(wid))
    assert not set(originals) & {a["path"] for a in second["generated_artifacts"]}
    assert not set(originals) & {a.path for a in regenerated}
    assert all((tmp_path / p).read_bytes() == data for p, data in originals.items())
    assert all(a["integrity"] for a in ctrl.list_design_artifacts(wid))


@pytest.mark.parametrize("missing", ["vin_nom", "vout", "iout", "fsw_hz", "ripple_v"])
def test_mcp_and_controller_reject_omitted_engineering_inputs(tmp_path, missing):
    server = MendexMCPServer(tmp_path)
    wid = server.controller.create_workspace("Fixture")["workspace_id"]
    args = values(wid)
    args.pop(missing)
    reply = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "generate_design", "arguments": args}})
    assert reply["result"]["isError"]
    with pytest.raises(ValueError):
        server.controller.generate_design(**args)
    assert server.controller.design_service.list_designs() == []


def test_linked_design_specification_preserves_provenance_and_rejects_conflict(tmp_path):
    ctrl = MendexEngineeringController(tmp_path)
    project = ctrl.create_project("Generic fixture", code="V31")
    pid = project["project_id"]
    ctrl.save_project_specification(pid, {"source": "Engineer supplied source", "assumptions": ["Fixture"]})
    result = ctrl.generate_design(**values(pid), product_id=pid)
    spec = ctrl.get_project_specifications(pid)["specification"]
    assert spec["vin_nom_v"] == 24 and spec["source"] == "Engineer supplied source"
    assert result["revision_id"] == project["revision_id"]
    with pytest.raises(StudioError, match="differs"):
        ctrl.generate_design(**{**values(pid), "vout": 8.}, product_id=pid)
    assert len(ctrl.design_service.list_designs()) == 1
    ctrl.create_revision(pid, "R002")
    with pytest.raises(StudioError, match="draft"):
        ctrl.generate_design(**values(project["revision_id"]))


def test_concurrent_processes_initialize_one_database_without_partial_schema(tmp_path):
    code = "from pathlib import Path; from mendex_core.service import StudioService; import sys; s=StudioService(Path(sys.argv[1])); print(len(s.list_products()))"
    processes = [subprocess.Popen([sys.executable, "-c", code, str(tmp_path)],
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
    for process in processes:
        stdout, stderr = process.communicate(timeout=45)
        assert process.returncode == 0, stderr
        assert stdout.strip() == "0"
    service = StudioService(tmp_path)
    with service.connection() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4


def test_native_run_snapshots_and_manifest_do_not_replace_originals(tmp_path):
    from mendex_core.design.ltspice_runner import LTspiceRunner
    if not LTspiceRunner().is_available:
        pytest.skip("LTspice unavailable; native execution remains NOT_EVALUATED")
    ctrl = MendexEngineeringController(tmp_path)
    project = ctrl.create_project("RC fixture", code="RC-REF")
    pid, rid = project["project_id"], project["revision_id"]
    root = ctrl._resolve_workspace_dir(pid)
    source = root / "reference.net"
    source.write_text("* Disposable RC\nV1 in 0 PULSE(0 10 0 1n 1n 10m 20m)\nR1 in out 1k\nC1 out 0 1u\n.tran 0 5m 0 10u\n.end\n")
    frozen = source.read_bytes()
    runs = [ctrl.run_simulation(pid, netlist_name=source.name) for _ in range(2)]
    assert all(r["status"] == "COMPLETED" for r in runs)
    assert runs[0]["raw_file"] != runs[1]["raw_file"]
    assert source.read_bytes() == frozen and not (root / "reference.raw").exists()
    for run in runs:
        job = ctrl.service.integrations.job(run["job_id"])
        assert job.request.parameters["revision_id"] == rid
        assert job.result.tool_version
        assert ctrl.service.integrations.evidence_integrity(run["job_id"])
        assert "Terminal software status" in ctrl.service.integrations.logs(run["job_id"])
        assert ctrl.service.integrations.evidence(run["job_id"]).engineering_status == "NOT_EVALUATED"
    with pytest.raises((StudioError, ValueError)):
        ctrl.run_simulation(pid, netlist_name="../reference.net")
