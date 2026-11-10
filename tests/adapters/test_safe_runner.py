import os
import sys
import threading
import time
from pathlib import Path
import pytest

from integrations.contracts import JobState
from integrations.runners.safe_runner import SafeRunner, compute_sha256, manifest_directory


def test_safe_runner_valid_execution(tmp_path):
    runner = SafeRunner()
    log_file = tmp_path / "test.log"
    # Run python -c "print('hello from runner')"
    cmd = [sys.executable, "-c", "print('hello from runner')"]
    out = runner.run(command_args=cmd, cwd=tmp_path, timeout_s=5, log_file=log_file)

    assert out.status == JobState.SUCCEEDED
    assert out.exit_code == 0
    assert "hello from runner" in out.stdout
    assert log_file.exists()
    assert "hello from runner" in log_file.read_text(encoding="utf-8")


def test_safe_runner_invalid_command():
    runner = SafeRunner()
    with pytest.raises(ValueError):
        runner.run(command_args=[], cwd=Path.cwd())

    with pytest.raises(FileNotFoundError):
        runner.run(command_args=["nonexistent_solver_executable_xyz_123.exe"], cwd=Path.cwd())


def test_safe_runner_timeout(tmp_path):
    runner = SafeRunner()
    # Script that sleeps for 5 seconds with a 1 second timeout
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    start = time.time()
    out = runner.run(command_args=cmd, cwd=tmp_path, timeout_s=1)
    duration = time.time() - start

    assert out.status == JobState.TIMED_OUT
    assert duration < 4.0  # Must be killed quickly


def test_safe_runner_cancellation(tmp_path):
    runner = SafeRunner()
    cancel_event = threading.Event()

    def trigger_cancel():
        time.sleep(0.3)
        cancel_event.set()

    t = threading.Thread(target=trigger_cancel)
    t.start()

    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    out = runner.run(command_args=cmd, cwd=tmp_path, timeout_s=10, cancel_event=cancel_event)
    t.join()

    assert out.status == JobState.CANCELLED


def test_artifact_hashing_and_manifest(tmp_path):
    test_file = tmp_path / "artifact.dat"
    test_file.write_bytes(b"Mendex Engineering Studio Test Data")
    expected_hash = "f3a005772e10e5d564d42a0daf720c1c82888b6fb424abb9c9d6fa06c4558fb7"

    computed = compute_sha256(test_file)
    assert computed == expected_hash

    artifacts = manifest_directory(tmp_path, job_id="job_001")
    assert len(artifacts) == 1
    assert artifacts[0].relative_path == "artifact.dat"
    assert artifacts[0].sha256 == expected_hash
    assert artifacts[0].size_bytes == len(b"Mendex Engineering Studio Test Data")
    assert artifacts[0].source_job == "job_001"
