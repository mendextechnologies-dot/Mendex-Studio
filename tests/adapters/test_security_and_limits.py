from pathlib import Path
import pytest

from integrations.runners.safe_runner import SafeRunner


def test_command_validation_rejects_empty():
    runner = SafeRunner()
    with pytest.raises(ValueError, match="non-empty list"):
        runner.validate_command([])


def test_command_validation_rejects_non_strings():
    runner = SafeRunner()
    with pytest.raises(ValueError, match="must be strings"):
        runner.validate_command([123])  # type: ignore


def test_command_validation_rejects_missing_binary():
    runner = SafeRunner()
    with pytest.raises(FileNotFoundError):
        runner.validate_command(["arbitrary_unknown_binary_xyz123.exe"])


def test_runner_preserves_directory_isolation(tmp_path):
    runner = SafeRunner()
    sub_workdir = tmp_path / "isolated_dir"
    sub_workdir.mkdir()

    import sys
    cmd = [sys.executable, "-c", "import os; open('generated.txt', 'w').write('isolated')"]
    out = runner.run(cmd, cwd=sub_workdir, timeout_s=5)

    assert out.status.value == "SUCCEEDED"
    assert (sub_workdir / "generated.txt").exists()
    assert not (tmp_path / "generated.txt").exists()
