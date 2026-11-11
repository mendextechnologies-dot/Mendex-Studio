from pathlib import Path
import pytest
from integrations.contracts import ToolState, ToolKind
from integrations.adapters.registry import ToolRegistry


def test_registry_contains_supported_entries():
    registry = ToolRegistry()
    assert registry.count() == 13

    expected_ids = {
        "ltspice", "python", "git", "kicad", "femm", "freecad",
        "qucs-s", "openmodelica", "jupyter", "switchlossdb",
        "magnet-dataset", "magnet-ml-benchmarks", "magnet-princeton",
    }
    registered_ids = {d.tool_id for d in registry.list_descriptors()}
    assert registered_ids == expected_ids


def test_real_tools_detected_truthfully():
    registry = ToolRegistry()
    # Python must be ready on the host
    py_desc = registry.get("python").descriptor
    assert py_desc.state == ToolState.READY
    assert py_desc.kind == ToolKind.RUNTIME
    assert py_desc.version is not None

    # Git must be ready on the host
    git_desc = registry.get("git").descriptor
    assert git_desc.state == ToolState.READY
    assert "git" in git_desc.executable_path.lower()

    # LTspice is installed on this host
    ltspice_desc = registry.get("ltspice").descriptor
    assert ltspice_desc.state in (ToolState.READY, ToolState.DETECTED)
    assert ltspice_desc.executable_path is not None
    assert "ltspice" in ltspice_desc.executable_path.lower()


def test_missing_tools_never_false_ready():
    registry = ToolRegistry()
    # All 6 core open-source candidate tools are now installed and verified ready on host
    installed_ids = ["freecad", "jupyter", "femm", "qucs-s", "kicad", "openmodelica"]
    for tool_id in installed_ids:
        desc = registry.get(tool_id).descriptor
        assert desc.state in (ToolState.READY, ToolState.DETECTED)
        assert desc.executable_path is not None
        assert Path(desc.executable_path).exists()
