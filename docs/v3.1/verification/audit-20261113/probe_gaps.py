"""Non-destructive live-data audit: all writes confined to a new disposable root."""
import hashlib
import json
from pathlib import Path
import tempfile

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.ltspice_runner import LTspiceRunner
from mendex_core.intelligence.calculations import DeterministicCalculationService
from mendex_core.mcp.server import MendexMCPServer

out = Path(__file__).resolve().parent
root = Path(tempfile.mkdtemp(prefix="mendex-gap-probes-"))
ctrl = MendexEngineeringController(root)
project = ctrl.create_project("Disposable gap probes", code="GAP-PROBE")
pid = project["project_id"]
args = dict(workspace_id=pid, product_id=pid, title="Disposable design", vin_min=18, vin_nom=24, vin_max=30,
            vout=5, iout=2, fsw_hz=100000, ripple_v=0.1)
first = ctrl.generate_design(**args)
paths = {a["path"]: a["sha256"] for a in first["generated_artifacts"]}
second = ctrl.generate_design(**{**args, "vout": 8})
changed = [{"path": p, "original_sha256": h, "current_sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()}
           for p, h in paths.items() if hashlib.sha256((root / p).read_bytes()).hexdigest() != h]
server = MendexMCPServer(root)
missing = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
    "name": "generate_design", "arguments": {"workspace_id": pid, "title": "Missing operating inputs", "generate_artifacts": False}}})
calc = DeterministicCalculationService()
pd = {str(degree): calc.calculate_iec_creepage_clearance(1000, 1000, pollution_degree=degree, slot_width_mm=5).model_dump(mode="json") for degree in (1, 2, 3)}
exe = LTspiceRunner().exe_path
result = {"isolated_root": str(root), "first_design_id": first["design_id"], "second_design_id": second["design_id"],
          "overwritten_registered_artifacts": changed, "missing_design_inputs_mcp": missing,
          "spec_after_generation": ctrl.get_project_specifications(pid),
          "insulation_pollution_degree_probes": pd, "ltspice_executable": str(exe)}
(out / "gap-probes.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"overwritten_artifacts": len(changed), "missing_inputs_rejected": missing["result"]["isError"],
                  "ltspice_executable": str(exe), "isolated_root": str(root)}, indent=2))
