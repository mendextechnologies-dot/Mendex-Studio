from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
import pytest

from integrations.adapters.kicad import KiCadAdapter
from integrations.contracts import JobRequest, JobState, ToolState
from integrations.parsers.kicad_parser import parse_kicad_drc_json


def test_kicad_adapter_descriptor():
    adapter = KiCadAdapter()
    desc = adapter.descriptor
    assert desc.tool_id == "kicad"
    assert "KiCad" in desc.name
    assert desc.category == "core"
    assert "GPL" in desc.license_name
    assert "erc" in adapter.supported_operations()
    assert "drc" in adapter.supported_operations()
    assert "version" in adapter.supported_operations()

    # Truthful host check
    if adapter.descriptor.executable_path:
        assert desc.state in (ToolState.READY, ToolState.DETECTED)
        assert Path(desc.executable_path).exists()


def test_kicad_adapter_version_execution(tmp_path):
    adapter = KiCadAdapter()
    if not adapter.descriptor.executable_path or not Path(adapter.descriptor.executable_path).exists():
        pytest.skip("KiCad CLI not installed on this host")

    job_id = str(uuid4())
    req = JobRequest(
        job_id=job_id,
        workspace_id=str(uuid4()),
        tool_id="kicad",
        operation="version",
        workdir=str(tmp_path),
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.job_id == job_id
    assert res.status == JobState.SUCCEEDED
    assert res.exit_code == 0
    assert "10." in res.stdout or "8." in res.stdout or "7." in res.stdout


def test_kicad_drc_json_parser(tmp_path):
    report_file = tmp_path / "drc_report.json"
    dummy_report = {
        "$schema": "https://schemas.kicad.org/drc.v1.json",
        "violations": [
            {"description": "Clearance violation", "type": "clearance"},
            {"description": "Track width too narrow", "type": "width"},
        ],
        "unconnected": [
            {"description": "Unconnected pad 1 to pad 2"},
        ],
    }
    report_file.write_text(json.dumps(dummy_report), encoding="utf-8")

    parsed = parse_kicad_drc_json(report_file)
    assert parsed["violation_count"] == 2
    assert parsed["unconnected_count"] == 1
    assert parsed["total_issues"] == 3
