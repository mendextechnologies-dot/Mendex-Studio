"""Opening CAD must preserve editing locks and recoverable user documents."""
from pathlib import Path

import pytest

from mendex_core import launch


@pytest.mark.parametrize('tool', ['freecad', 'eeschema'])
def test_gui_launch_preserves_recovery_and_lock_files(tmp_path, monkeypatch, tool):
    monkeypatch.setenv('TEMP', str(tmp_path / 'temp'))
    recovery = tmp_path / 'temp/FreeCAD/v1-1/Cache/FreeCAD_recovery/session.fcstd'
    recovery.parent.mkdir(parents=True)
    recovery.write_bytes(b'unsaved recovery bytes')
    target = tmp_path / 'workspace/model.step'
    target.parent.mkdir()
    target.write_bytes(b'fixture; never opened by a real tool')
    lock = target.parent / 'active.lck'
    lock.write_bytes(b'active editor lock; no proof of staleness')
    calls = []
    def spawn(command, cwd, **kwargs):
        calls.append((command, cwd, kwargs))
        return 1234
    monkeypatch.setattr(launch, '_spawn_on_desktop', spawn)
    result = launch._spawn_gui(tmp_path / f'{tool}.exe', target)
    assert result['pid'] == 1234 and len(calls) == 1
    assert lock.exists(), 'Opening a file must not bypass another editor lock'
    assert recovery.exists(), 'Opening a model must not erase crash recovery'
    assert lock.read_bytes() == b'active editor lock; no proof of staleness'
    assert recovery.read_bytes() == b'unsaved recovery bytes'
