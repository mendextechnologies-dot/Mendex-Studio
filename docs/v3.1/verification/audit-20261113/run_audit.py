"""Disposable verification harness; no application source changes or live data access."""
import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

OUT = Path(__file__).resolve().parent
OUT = OUT / "attempt3"
OUT.mkdir(exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix="mendex-v31-audit-"))
EVENTS = []


class Client:
    def __init__(self, module, name):
        self.name = name
        self.stderr = (OUT / (name + "-stderr.log")).open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-u", "-m", module, "--root", str(ROOT)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, encoding="utf-8", env={**os.environ, "MENDEX_DATA_ROOT": str(ROOT)},
        )
        self.lines = queue.Queue()
        def read():
            for line in self.process.stdout:
                self.lines.put(line)
        threading.Thread(target=read, daemon=True).start()

    def request(self, method, params=None):
        ident = str(len(EVENTS) + 1)
        request = ({"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}
                   if self.name == "mcp" else
                   {"protocol_version": "3.1.0", "id": ident, "method": method, "params": params or {}})
        start = time.perf_counter()
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        response = json.loads(self.lines.get(timeout=100))
        EVENTS.append({"transport": self.name, "request": request, "response": response,
                       "elapsed_ms": round((time.perf_counter() - start) * 1000, 3)})
        return response

    def tool(self, name, arguments=None, allow_error=False):
        response = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        result = response["result"]
        if result.get("isError"):
            if allow_error:
                return result
            raise RuntimeError(result)
        return json.loads(result["content"][0]["text"])

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        self.stderr.close()


def main():
    # Attempt 2 retained a simultaneous-first-start database creation race.
    # Seed this disposable database serially so remaining operations can be audited.
    from mendex_core.service import StudioService
    StudioService(ROOT)
    mcp = Client("mendex_core.mcp", "mcp")
    desktop = Client("mendex_core.desktop", "desktop")
    summary = {"isolated_root": str(ROOT), "ui_observation": "NOT VERIFIED: in-app browser unavailable"}
    try:
        mcp.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "Codex audit harness", "version": "1"}})
        tools = mcp.request("tools/list")["result"]["tools"]
        summary["mcp_tool_count"] = len(tools)
        desktop.request("handshake")
        assert desktop.request("projects")["result"] == []
        project = mcp.tool("create_project", {"name": "Disposable generic reference", "code": "AUDIT-REF", "owner": "Software audit fixture", "description": "Synthetic software reference, no engineering approval", "category": "dc_dc_converter"})
        pid, rid = project["project_id"], project["revision_id"]
        spec = {"vin_min_v": 18, "vin_nom_v": 24, "vin_max_v": 30, "vout_v": 5, "iout_a": 2, "switching_frequency_hz": 100000}
        mcp.tool("save_project_specification", {"project_id": pid, "spec_data": spec})
        base = {"revision_id": rid, "source": "Codex disposable audit", "reason": "Software reference only"}
        mcp.tool("enroll_lifecycle", {**base, "idempotency_key": "enroll"})
        stage = {**base, "stage_id": "project_initialization"}
        mcp.tool("apply_lifecycle_stage", {**stage, "action": "start", "idempotency_key": "start"})
        shash = mcp.tool("get_project_specifications", {"project_id": pid})["input_hash"]
        calc = {**stage, "expected_input_hash": shash, "idempotency_key": "calc", "calculation": "losses", "assumptions": ["Software fixture, supplied synthetic device parameters"], "parameters": {"part_number": "AUDIT-FIXTURE", "r_ds_on_ohm": 0.02, "i_rms_a": 2, "duty_cycle": 0.4, "e_on_j": 1e-6, "e_off_j": 2e-6, "frequency_hz": 100000}}
        computed = mcp.tool("record_calculation_run", calc)
        assert computed == mcp.tool("record_calculation_run", calc)
        summary["calculation_status"] = computed["status"]
        summary["design"] = mcp.tool("generate_design", {"workspace_id": pid, "product_id": pid, "title": "Generic reference buck", "category": "dc_dc_converter", "vin_min": 18, "vin_nom": 24, "vin_max": 30, "vout": 5, "iout": 2, "fsw_hz": 100000, "ripple_v": 0.1})
        observer = desktop.request("project", {"project_id": pid})["result"]
        summary["observer_before_revision"] = {"projects": len(desktop.request("projects")["result"]), "calculations": len(observer["calculations"]["records"]), "designs": len(observer["designs"]), "files": len(observer["files"])}
        summary["revision"] = mcp.tool("create_revision", {"product_id": pid, "label": "AUDIT-R002"})
        rid = summary["revision"]["revision_id"]
        # New revisions intentionally start with no copied native designs. Use an explicit
        # benign RC reference input in the new draft, never execute archived inputs in place.
        from mendex_core.service import StudioService
        service = StudioService(ROOT)
        workspace = service.workspace_path(service.get_revision(rid))
        net = workspace / "rc_reference.net"
        net.write_text("* Disposable RC software reference\nV1 in 0 PULSE(0 10 0 1n 1n 10m 20m)\nR1 in out 1k\nC1 out 0 1u\n.tran 0 5m 0 10u\n.end\n", encoding="utf-8")
        base = {**base, "revision_id": rid}
        stage = {**base, "stage_id": "project_initialization"}
        mcp.tool("enroll_lifecycle", {**base, "idempotency_key": "enroll-2"})
        mcp.tool("apply_lifecycle_stage", {**stage, "action": "start", "idempotency_key": "start-2"})
        shash = mcp.tool("get_project_specifications", {"project_id": pid})["input_hash"]
        attributed = {**stage, "expected_input_hash": shash}
        summary["artifact"] = mcp.tool("register_engineering_artifact", {**attributed, "idempotency_key": "artifact", "relative_path": net.name, "expected_sha256": hashlib.sha256(net.read_bytes()).hexdigest(), "classification": "netlist"}, allow_error=True)
        summary["simulation"] = mcp.tool("run_simulation", {"workspace_id": pid, "tool": "ltspice", "netlist_name": net.name, "duration_s": 0.005})
        job = summary["simulation"]["job_id"]
        summary["simulation_inspection"] = mcp.tool("get_simulation_results", {"job_id": job})
        summary["simulation_logs"] = mcp.tool("get_simulation_logs", {"job_id": job})
        summary["report"] = mcp.tool("generate_revision_report", {**attributed, "idempotency_key": "report"})
        summary["missing_evidence_completion"] = mcp.tool("apply_lifecycle_stage", {**base, "stage_id": "verification", "action": "complete", "idempotency_key": "blocked"}, allow_error=True)
        summary["self_approval"] = mcp.tool("apply_lifecycle_stage", {**base, "stage_id": "verification", "action": "approve", "idempotency_key": "approve"}, allow_error=True)
        detail = desktop.request("project", {"project_id": pid})["result"]
        summary["observer_after_revision"] = {"revisions": len(detail["revisions"]), "reports": len(detail["reports"]), "simulations": detail["simulations"], "files": len(detail["files"]), "lifecycle": detail["lifecycle"]}
        cli = subprocess.run([sys.executable, "-m", "mendex_core.cli", "--root", str(ROOT), "lifecycle", "show", rid], capture_output=True, text=True, encoding="utf-8", timeout=30)
        (OUT / "cli-lifecycle.json").write_text(cli.stdout, encoding="utf-8")
        summary["cli_exit"] = cli.returncode
        summary["waveform"] = desktop.request("waveform", {"revision_id": rid, "relative_path": "rc_reference.raw", "traces": ["V(out)"], "limit": 10})
        with sqlite3.connect(ROOT / ".mendex" / "studio.sqlite3") as db:
            summary["sqlite_integrity"] = db.execute("PRAGMA integrity_check").fetchall()
            summary["sqlite_foreign_keys"] = db.execute("PRAGMA foreign_key_check").fetchall()
        summary["completed"] = True
    except Exception as exc:
        summary["error"] = repr(exc)
        summary["completed"] = False
    finally:
        mcp.close()
        desktop.close()
        (OUT / "transcript.json").write_text(json.dumps(EVENTS, indent=2), encoding="utf-8")
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k in ("isolated_root", "completed", "error", "mcp_tool_count", "calculation_status", "observer_before_revision", "sqlite_integrity", "cli_exit")}, indent=2))


if __name__ == "__main__":
    main()
