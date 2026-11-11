"""Single source of truth for the Mendex data root.

Engineering data lives in the Mendex project root (the folder containing ``pyproject.toml``),
independent of the directory a CLI, MCP client or desktop launcher happens to start in.
``MENDEX_DATA_ROOT`` overrides this; an explicit ``--root`` argument overrides both.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "MENDEX_DATA_ROOT"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_data_root() -> Path:
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    if (PROJECT_ROOT / "pyproject.toml").exists():
        return PROJECT_ROOT
    # Installed outside a source checkout: never fall back to the current working directory.
    return (Path.home() / "Mendex Studio Data").resolve()
