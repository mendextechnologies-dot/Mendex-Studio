"""Unit tests for the internal CopperKiCadAdapter in Mendex Engineering Studio."""
import os
import shutil
from pathlib import Path
import pytest

from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter


@pytest.fixture
def adapter():
    return CopperKiCadAdapter()


def test_adapter_availability(adapter):
    """Verifies that Copper KiCad adapter correctly detects KiCad 10 on workstation."""
    assert adapter.is_available() is True
    inst = adapter.install
    assert inst is not None
    assert inst.cli.exists()
    assert "10." in inst.full_version


def test_adapter_doctor_status(adapter):
    """Verifies doctor status returns active KiCad 10 and Pillow."""
    status = adapter.doctor_status()
    assert status.get("copper") is not None
    assert status.get("kicad", {}).get("active") is not None
    active = status["kicad"]["active"]
    assert "10." in active.get("version", "")


def test_adapter_render_3d(adapter, tmp_path):
    """Verifies 3D raytraced rendering produces valid PNG."""
    # Use disposable PCB from scratch
    poc_pcb = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\6d7675c6-a711-4df0-a104-3720700b777f\scratch\poc_resistor_divider\divider_poc\divider_poc.kicad_pcb")
    if not poc_pcb.exists():
        pytest.skip("POC PCB not present on disk")

    out_png = tmp_path / "test_render_3d.png"
    result_path = adapter.render_3d(poc_pcb, output_png=out_png, view="iso", width=800)

    assert result_path.exists()
    assert result_path.stat().st_size > 5000
    assert result_path.suffix.lower() == ".png"


def test_kicad_service_render_3d(tmp_path):
    """Verifies KiCadLifecycleService renders 3D views through internal Copper adapter."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
    poc_pcb = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\6d7675c6-a711-4df0-a104-3720700b777f\scratch\poc_resistor_divider\divider_poc\divider_poc.kicad_pcb")
    if not poc_pcb.exists():
        pytest.skip("POC PCB not present on disk")

    service = KiCadLifecycleService()
    out_png = tmp_path / "service_3d_render.png"
    res = service.render_3d(poc_pcb, output_png=out_png, view="top", width=600)

    assert res.exists()
    assert res.stat().st_size > 2000


def test_kicad_adapter_render_3d_operation(tmp_path):
    """Verifies KiCadAdapter executes render_3d operation."""
    from uuid import uuid4
    from integrations.adapters.kicad import KiCadAdapter
    from integrations.contracts import JobRequest, JobState

    poc_pcb = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\6d7675c6-a711-4df0-a104-3720700b777f\scratch\poc_resistor_divider\divider_poc\divider_poc.kicad_pcb")
    if not poc_pcb.exists():
        pytest.skip("POC PCB not present on disk")

    adapter = KiCadAdapter()
    req = JobRequest(
        job_id=str(uuid4()),
        workspace_id=str(uuid4()),
        tool_id="kicad",
        operation="render_3d",
        workdir=str(tmp_path),
        input_paths=[str(poc_pcb)],
        parameters={"view": "iso", "width": 600},
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.SUCCEEDED
    assert (tmp_path / "divider_poc_3d.png").exists()
    assert (tmp_path / "divider_poc_3d.png").stat().st_size > 2000


def test_adapter_route_pcb_with_power_netclasses(adapter, tmp_path):
    """Verifies that route_pcb injects power net-class trace widths and completes routing."""
    poc_dir = Path(r"C:\Users\Sagar\.gemini\antigravity\brain\6d7675c6-a711-4df0-a104-3720700b777f\scratch\poc_resistor_divider\divider_poc")
    if not (poc_dir / "divider_poc.kicad_pcb").exists():
        pytest.skip("POC PCB not present on disk")

    # Copy to tmp_path
    for f in poc_dir.glob("divider_poc.*"):
        shutil.copy2(f, tmp_path / f.name)

    target_pcb = tmp_path / "divider_poc.kicad_pcb"
    res = adapter.route_pcb(
        pcb_path=target_pcb,
        pour_ground=True,
        ground_net="GND",
        default_track=0.35,
        power_track=1.5,
        power_patterns=["*Vin*", "*Vdiv*"],
    )

    assert res["routing_completed"] is True
    assert res["pour_completed"] is True
    assert res["tracks"] > 0
    assert res["drc_errors"] == 0
    assert "netclasses" in res
    assert res["netclasses"].get("Power", {}).get("track") == 1.5
    assert res["netclasses"].get("Default", {}).get("track") == 0.35


def test_desktop_service_auto_route_rpc(tmp_path):
    """Verifies DesktopService auto_route_pcb RPC endpoint."""
    from mendex_core.desktop.service import DesktopService, ROUTES
    from mendex_core.desktop.models import AutoRouteQuery
    from mendex_core.paths import default_data_root
    from mendex_core.service import StudioService

    root = default_data_root()
    studio = StudioService(root)
    desktop = DesktopService(studio)

    assert "auto_route_pcb" in ROUTES
    # Test dispatch schema validation
    query = AutoRouteQuery(
        revision_id="9b7c1396-64da-41f8-8649-77dc0f24e103",
        pour_ground=True,
        default_track=0.4,
        power_track=1.2,
    )
    assert query.default_track == 0.4
    assert query.power_track == 1.2
