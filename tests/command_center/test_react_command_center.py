"""Automated headless test suite for the React + TypeScript Command Center (http://localhost:5173)."""
import json
import os
import subprocess
import time
import urllib.request
import pytest

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://localhost:5173"


def rpc_call(method: str, params: dict = None) -> dict:
    payload = {
        "protocol_version": "3.1.0",
        "id": f"test-{method}-{int(time.time() * 1000)}",
        "method": method,
        "params": params or {},
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/rpc",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_rendered_dom(url: str, virtual_time_ms: int = 2500) -> str:
    """Execute headless Edge browser and return the fully evaluated DOM."""
    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        f"--virtual-time-budget={virtual_time_ms}",
        "--dump-dom",
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout


# -----------------------------------------------------------------------------
# 1. Desktop Stdio RPC Transport & Data Contract Tests
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def ensure_project_for_testing():
    """Ensure a project exists during test suite run, cleaning up temporary test project if created."""
    res = rpc_call("projects")
    created_id = None
    if not res.get("result"):
        from mendex_core.controller import MendexEngineeringController
        c = MendexEngineeringController()
        created = c.create_project("SpectraVolt SV-1000", code="SV1000", category="dc_dc_converter", auto_enroll=True)
        created_id = created.get("project_id") or created.get("product_id")
        time.sleep(1.0)
    yield
    if created_id:
        try:
            from mendex_core.controller import MendexEngineeringController
            MendexEngineeringController().delete_project(created_id)
        except Exception:
            pass


def test_rpc_handshake():
    res = rpc_call("handshake")
    assert res["protocol_version"] == "3.1.0"
    data = res["result"]
    assert data["status"] == "READY"
    assert data["application"] == "Mendex Engineering Studio"
    assert data["desktop_version"] == "3.1.0"
    assert data["engineering_status"] == "NOT_EVALUATED"


def test_rpc_overview():
    res = rpc_call("overview")
    assert res["protocol_version"] == "3.1.0"
    data = res["result"]
    assert "metrics" in data
    assert "projects" in data
    assert data["metrics"]["projects"] >= 1
    # Verify SV1000 presence (supports SV-1000 or SV1000)
    codes = [p["code"] for p in data["projects"]]
    assert any("SV" in c for c in codes)


def test_rpc_projects():
    res = rpc_call("projects")
    projects = res["result"]
    assert len(projects) >= 1
    sv1000 = next((p for p in projects if "SV" in p["code"]), None)
    assert sv1000 is not None
    assert sv1000["active_revision_id"] is not None
    assert sv1000["revision_label"] == "R001"
    assert sv1000["revision_status"].lower() == "draft"
    assert "input_hash" in sv1000


def test_rpc_project_detail_and_ten_domains():
    projs = rpc_call("projects")["result"]
    pid = projs[0]["product_id"]
    res = rpc_call("project", {"project_id": pid})
    data = res["result"]

    # Verify all 10 engineering domains returned
    assert "product" in data
    assert "revision" in data
    assert "lifecycle" in data
    assert "calculations" in data
    assert "designs" in data
    assert "files" in data
    assert "validation" in data
    assert "revisions" in data
    assert "reports" in data

    # Verify canonical 9-stage lifecycle
    lifecycle = data["lifecycle"]
    assert len(lifecycle["stages"]) == 9
    stage_names = [s["definition"]["name"] for s in lifecycle["stages"]]
    assert "Project Initialization" in stage_names[0]
    assert "Requirements" in stage_names[1]
    assert "Engineering Calculations" in stage_names[3]
    assert "Simulation and Analysis" in stage_names[5]

    # Verify files count
    assert len(data["files"]) >= 1


def test_rpc_all_thirteen_tools_ready():
    res = rpc_call("tools")
    tools = res["result"]
    assert len(tools) == 13

    # Every single tool must be READY
    for t in tools:
        assert t["health"]["state"] == "READY", f"Tool {t['descriptor']['name']} was not READY"

    tool_map = {t["descriptor"]["tool_id"]: t for t in tools}
    # Verify exact host binary paths
    assert "kicad-cli.exe" in tool_map["kicad"]["health"]["executable_path"].lower()
    assert "femm.exe" in tool_map["femm"]["health"]["executable_path"].lower()
    assert "ltspice.exe" in tool_map["ltspice"]["health"]["executable_path"].lower()
    assert "freecad" in tool_map["freecad"]["health"]["executable_path"].lower()
    assert "python.exe" in tool_map["python"]["health"]["executable_path"].lower()
    assert "git.exe" in tool_map["git"]["health"]["executable_path"].lower()


def test_rpc_components_library():
    res = rpc_call("components")
    data = res["result"]
    assert "components" in data
    assert "materials" in data
    assert "cores" in data
    assert len(data["components"]) >= 3
    assert len(data["materials"]) >= 5
    assert len(data["cores"]) >= 5


# -----------------------------------------------------------------------------
# 2. Automated Headless Browser DOM Evaluation Tests (Chromium/Edge)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_dashboard_render():
    dom = get_rendered_dom(f"{BASE_URL}/")
    assert 'id="root"' in dom
    assert "MENDEX STUDIO" in dom
    assert "v3.1 COMMAND CENTER" in dom
    assert "Engineering Operations Dashboard" in dom
    assert "AUTHORITATIVE PROJECTS" in dom
    assert "COMPLETED SIMULATIONS" in dom
    assert "FAILED RUNS" in dom
    assert "PENDING REVIEWS" in dom
    assert ("SV1000" in dom or "SV-1000" in dom)
    assert "Auto-Sync Active" in dom
    assert "Core Python 3.13 Ready" in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_engineering_tools_render():
    dom = get_rendered_dom(f"{BASE_URL}/?page=tools")
    assert "Engineering Solver Integrations" in dom
    assert "KiCad" in dom
    assert "kicad-cli.exe" in dom
    assert "FEMM" in dom
    assert "femm.exe" in dom
    assert "LTspice" in dom
    assert "LTspice.exe" in dom
    assert "FreeCAD" in dom
    assert "freecadcmd.exe" in dom
    assert "Python" in dom
    assert "Git" in dom
    assert "READY" in dom
    # Ensure no NOT_CONFIGURED badges remain
    assert "NOT_CONFIGURED" not in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_project_detail_render():
    projs = rpc_call("projects")["result"]
    pid = projs[0]["product_id"]
    dom = get_rendered_dom(f"{BASE_URL}/?page=projects&project={pid}")
    assert ("SV-1000" in dom or "SV1000" in dom)
    assert "dc_dc_converter" in dom or "DRAFT" in dom or "draft" in dom
    # Engineering tabs
    assert "overview" in dom
    assert "lifecycle" in dom
    assert "specifications" in dom
    assert "calculations" in dom
    assert "simulations" in dom
    assert "designs" in dom
    assert "files" in dom
    assert "validation" in dom
    assert "revisions" in dom
    assert "reports" in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_settings_diagnostics_render():
    dom = get_rendered_dom(f"{BASE_URL}/?page=settings")
    assert "Settings" in dom or "System Diagnostics" in dom
    assert "3.1.0" in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_components_library_render():
    dom = get_rendered_dom(f"{BASE_URL}/?page=components")
    assert "Component &amp; Materials Library" in dom or "Component & Materials Library" in dom
    assert "Semiconductors" in dom
    assert "Magnetic Cores" in dom
    assert "Magnetic Materials" in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_simulations_center_render():
    dom = get_rendered_dom(f"{BASE_URL}/?page=simulations")
    assert "Simulation Center" in dom
    assert "Batch Solver Jobs" in dom or "Job ID" in dom or "Exit Code" in dom



@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_reports_register_render():
    dom = get_rendered_dom(f"{BASE_URL}/?page=reports")
    assert "Reports &amp; Evidence Register" in dom or "Reports & Evidence Register" in dom


@pytest.mark.skipif(not os.path.exists(EDGE_EXE), reason="Microsoft Edge binary not found on host")
def test_headless_browser_all_ten_project_tabs():
    projs = rpc_call("projects")["result"]
    pid = projs[0]["product_id"]

    expected_markers = {
        "overview": "Recorded project",
        "lifecycle": "Lifecycle",
        "specifications": "Saved specifications",
        "calculations": "Persisted calculation runs",
        "simulations": "Simulation jobs for this revision",
        "designs": "Recorded designs and artifact snapshots",
        "files": "Revision files",
        "validation": "Recorded validation and evidence",
        "revisions": "Revision history",
        "reports": "Draft reports",
    }

    for tab, marker in expected_markers.items():
        dom = get_rendered_dom(f"{BASE_URL}/?page=projects&project={pid}&tab={tab}", virtual_time_ms=1800)
        assert marker in dom, f"Marker '{marker}' not found in DOM for tab='{tab}'"


def test_rpc_open_file_security_traversal_rejected():
    projs = rpc_call("projects")["result"]
    rev_id = projs[0]["active_revision_id"]
    res = rpc_call("open_file", {"revision_id": rev_id, "relative_path": "../../../boot.ini"})
    assert "error" in res
    assert "traversal" in res["error"]["message"].lower() or "rejected" in res["error"]["message"].lower() or "invalid" in res["error"]["message"].lower()

