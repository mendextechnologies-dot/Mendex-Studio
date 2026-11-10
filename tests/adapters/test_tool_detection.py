import pytest
from integrations.contracts import ToolState, ToolKind
from integrations.adapters.registry import ToolRegistry


def test_registry_contains_all_18_entries():
    registry = ToolRegistry()
    assert registry.count() == 18

    expected_ids = {
        "ltspice", "python", "git", "kicad", "femm", "freecad",
        "qucs_s", "openmodelica", "jupyter", "switchloss_db",
        "magnet_dataset", "magnet_ml_benchmarks", "magnet_princeton",
        "plecs", "matlab", "ansys_maxwell", "ansys_icepak", "solidworks",
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
    missing_ids = ["kicad", "femm", "freecad", "qucs_s", "openmodelica", "jupyter"]

    for tool_id in missing_ids:
        desc = registry.get(tool_id).descriptor
        # Unless installed on this machine, must be NOT_INSTALLED
        assert desc.state in (ToolState.NOT_INSTALLED, ToolState.DETECTED)
        if desc.state == ToolState.NOT_INSTALLED:
            assert desc.executable_path is None
            assert "not installed" in desc.diagnostic.lower()


def test_commercial_tools_are_unlicensed_stubs():
    registry = ToolRegistry()
    commercial_ids = ["plecs", "matlab", "ansys_maxwell", "ansys_icepak", "solidworks"]

    for tool_id in commercial_ids:
        desc = registry.get(tool_id).descriptor
        assert desc.category == "optional"
        assert desc.state in (ToolState.OPTIONAL_UNLICENSED, ToolState.DETECTED)
