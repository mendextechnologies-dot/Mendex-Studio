"""Suite-wide safety: tests must never open real desktop applications (LTspice, KiCad, FreeCAD, VS Code, Explorer).

Launch routing is still exercised; only the final process spawn is replaced by a recorder.
Tests that need to inspect launches can request the ``launched_processes`` fixture.
"""
from types import SimpleNamespace
import subprocess

import pytest

import mendex_core.launch as launch_module


class _FakeProcess:
    _next_pid = 900000

    def __init__(self, args, *unused_args, **unused_kwargs):
        _FakeProcess._next_pid += 1
        self.pid = _FakeProcess._next_pid
        self.args = args
        self.returncode = None

    def poll(self):
        return self.returncode


@pytest.fixture(autouse=True)
def launched_processes(monkeypatch):
    launched = []

    def fake_popen(args, *a, **k):
        launched.append(list(args) if isinstance(args, (list, tuple)) else [args])
        return _FakeProcess(args, *a, **k)

    # Replace only the launcher's view of subprocess; real subprocess.Popen stays intact for solver tests.
    proxy = SimpleNamespace(**{name: getattr(subprocess, name) for name in dir(subprocess) if not name.startswith("__")})
    proxy.Popen = fake_popen
    monkeypatch.setattr(launch_module, "subprocess", proxy)
    monkeypatch.setattr(launch_module.os, "startfile", lambda path, *a: launched.append(["startfile", str(path)]), raising=False)
    return launched
