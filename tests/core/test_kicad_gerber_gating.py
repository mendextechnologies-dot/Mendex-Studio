from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from integrations.adapters.kicad import KiCadAdapter
from integrations.contracts import JobRequest, JobState
from mendex_core.design.generators.kicad_pcb_generator import KiCadPCBGenerator
from mendex_core.design.ir import (
    ComponentType,
    DesignIntermediateRepresentation,
    IRComponent,
    IRNet,
    IRNetPinRef,
    IRPin,
)
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
from mendex_core.pcb import native_structure


def _create_placement_only_pcb(pcb_path: Path):
    """Creates an unrouted board with 2 footprints and 0 copper tracks."""
    ir = DesignIntermediateRepresentation(
        design_id="test_design",
        name="Test Unrouted Board",
        components=[
            IRComponent(
                id="R1",
                designator="R1",
                name="10k",
                type=ComponentType.RESISTOR,
                footprint="Resistor_SMD:R_0805_2012Metric",
                pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            ),
            IRComponent(
                id="R2",
                designator="R2",
                name="20k",
                type=ComponentType.RESISTOR,
                footprint="Resistor_SMD:R_0805_2012Metric",
                pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            ),
        ],
        nets=[
            IRNet(name="NET1", connections=[IRNetPinRef(component_id="R1", pin_id="1"), IRNetPinRef(component_id="R2", pin_id="1")]),
        ],
    )
    KiCadPCBGenerator.export_pcb(ir, pcb_path)
    return pcb_path


def test_generated_pcb_is_labeled_placement_only(tmp_path):
    pcb_file = tmp_path / "board.kicad_pcb"
    _create_placement_only_pcb(pcb_file)

    text = pcb_file.read_text(encoding="utf-8")
    assert "Placement Only - Unrouted" in text
    assert "Routing & DRC Required Before Fabrication" in text

    struct = native_structure(pcb_file)
    assert struct["footprint"] == 2
    assert struct["segment"] == 0
    assert struct["arc"] == 0


def test_kicad_service_refuses_gerber_export_on_unrouted_board(tmp_path):
    pcb_file = tmp_path / "board.kicad_pcb"
    _create_placement_only_pcb(pcb_file)

    service = KiCadLifecycleService()
    # Should raise ValueError before even calling kicad-cli
    with pytest.raises(ValueError, match="board has 0 routed copper tracks"):
        service.export_gerbers(pcb_file)

    with pytest.raises(ValueError, match="board has 0 routed copper tracks"):
        service.export_drill(pcb_file)


def test_kicad_adapter_blocks_gerber_export_for_unrouted_board(tmp_path):
    pcb_file = tmp_path / "board.kicad_pcb"
    _create_placement_only_pcb(pcb_file)

    adapter = KiCadAdapter()
    job_id = str(uuid4())
    req = JobRequest(
        job_id=job_id,
        workspace_id=str(uuid4()),
        tool_id="kicad",
        operation="export_gerber",
        workdir=str(tmp_path),
        input_paths=[str(pcb_file)],
    )

    result = adapter.execute(req, workdir=tmp_path)
    assert result.status == JobState.FAILED
    assert result.exit_code == 1
    assert "0 routed tracks" in result.stderr
    assert len(result.artifacts) == 0
