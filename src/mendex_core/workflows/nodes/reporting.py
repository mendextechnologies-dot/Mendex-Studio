"""Reporting nodes: evidence aggregation, dossier compilation, and artifact export."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, ValidationResultData, SimulationResultData, ArtifactData
from ..registry import BaseNode, ExecutionContext, NodeRegistry


@NodeRegistry.register
class EvidenceAggregationNode(BaseNode):
    node_type = "evidence_aggregation"
    category = NodeCategory.REPORTING
    title = "Evidence Aggregation"
    description = "Collects validation checks, simulation metrics, and calculations into a sealed manifest."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="check1", display_name="Check 1", data_type=PortDataType.VALIDATION_RESULT, required=False),
            PortDefinition(name="check2", display_name="Check 2", data_type=PortDataType.VALIDATION_RESULT, required=False),
            PortDefinition(name="sim_result", display_name="Sim Result", data_type=PortDataType.SIM_RESULT, required=False),
            PortDefinition(name="calculation", display_name="Calculation", data_type=PortDataType.ANY, required=False),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="manifest", display_name="Manifest", data_type=PortDataType.ANY),
            PortDefinition(name="manifest_sha256", display_name="SHA256", data_type=PortDataType.STRING),
            PortDefinition(name="all_passed", display_name="All Passed", data_type=PortDataType.BOOLEAN),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        manifest_data = {
            "workflow_run_id": context.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provenance": "Mendex Evidence Aggregator",
            "validations": [],
            "simulations": [],
            "calculations": [],
        }

        all_passed = True
        validation_count = 0
        for key in ("check1", "check2"):
            chk = inputs.get(key)
            if chk:
                validation_count += 1
                if isinstance(chk, ValidationResultData):
                    manifest_data["validations"].append(chk.model_dump())
                    if not chk.passed or getattr(chk, "status", None) == "NOT_EVALUATED":
                        all_passed = False
                elif isinstance(chk, dict):
                    manifest_data["validations"].append(chk)
                    if not chk.get("passed", False) or chk.get("status") == "NOT_EVALUATED":
                        all_passed = False

        if validation_count == 0:
            all_passed = False

        sim = inputs.get("sim_result")
        if sim:
            if isinstance(sim, SimulationResultData):
                manifest_data["simulations"].append(sim.model_dump())
            elif isinstance(sim, dict):
                manifest_data["simulations"].append(sim)

        calc = inputs.get("calculation")
        if calc:
            manifest_data["calculations"].append(calc)

        raw_json = json.dumps(manifest_data, sort_keys=True)
        sha = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        return {
            "manifest": manifest_data,
            "manifest_sha256": sha,
            "all_passed": all_passed,
        }


@NodeRegistry.register
class ReportExportNode(BaseNode):
    node_type = "report_export"
    category = NodeCategory.REPORTING
    title = "Report Export"
    description = "Exports a formal HTML/JSON engineering dossier to the workspace reports directory."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="manifest", display_name="Manifest", data_type=PortDataType.ANY, required=True),
        ]

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="report_path", display_name="Report Path", data_type=PortDataType.STRING),
            PortDefinition(name="report_artifact", display_name="Artifact", data_type=PortDataType.ARTIFACT),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        manifest = inputs.get("manifest", {})
        title = config.get("report_title", "Engineering Workflow Dossier")

        # Determine output location
        out_dir = Path("reports")
        if context.workspace_path:
            out_dir = Path(context.workspace_path) / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)

        report_file = out_dir / f"workflow_report_{context.run_id[:8]}.html"

        html_content = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 30px auto; padding: 20px; color: #222; }}
    h1 {{ color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
    .badge-pass {{ background: #dcfce7; color: #15803d; padding: 4px 8px; border-radius: 4px; font-weight: 600; }}
    .badge-fail {{ background: #fee2e2; color: #b91c1c; padding: 4px 8px; border-radius: 4px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }}
    th {{ background: #f1f5f9; }}
    pre {{ background: #f8fafc; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><b>Run ID:</b> {context.run_id} | <b>Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
  <p><b>Provenance:</b> Deterministic Mendex Engineering Workflow Studio</p>

  <h2>Validation Summary</h2>
  <table>
    <tr><th>Requirement</th><th>Status</th><th>Actual</th><th>Expected</th><th>Message</th></tr>
"""
        for v in manifest.get("validations", []):
            passed = v.get("passed", False)
            badge = '<span class="badge-pass">PASS</span>' if passed else '<span class="badge-fail">FAIL</span>'
            html_content += f"<tr><td>{v.get('check_id')}</td><td>{badge}</td><td>{v.get('actual_value')}</td><td>{v.get('expected_value')}</td><td>{v.get('message')}</td></tr>\n"

        html_content += """
  </table>

  <h2>Execution Manifest Snapshot</h2>
  <pre>""" + json.dumps(manifest, indent=2) + """</pre>
</body>
</html>
"""
        report_file.write_text(html_content, encoding="utf-8")
        sha = hashlib.sha256(html_content.encode("utf-8")).hexdigest()

        artifact = ArtifactData(
            path=str(report_file),
            artifact_type="html_report",
            sha256=sha,
            metadata={"run_id": context.run_id},
        )
        return {
            "report_path": str(report_file),
            "report_artifact": artifact,
        }
