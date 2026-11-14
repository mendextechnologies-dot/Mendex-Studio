# 03 Codebase Quality
Static analysis only; commands run from repo root or `src`. Tests not executed (pass/fail NOT VERIFIED).

## Size (Python LOC, `find|xargs cat|wc -l`)
| Package / file | LOC |
|---|---|
| mendex_ui (legacy PySide6) | 12,327 |
| integrations | 3,278 |
| mendex_core/design | 2,841 |
| mendex_core/workflows | 2,422 |
| mendex_core/lifecycle | 1,729 |
| mendex_core/controller.py | 1,186 |
| mendex_core/intelligence | 857 |
| mendex_core/launch.py | 839 |
| mendex_core/service.py | 823 |
| mendex_core/engineering_reviews | 801 |
| mendex_core/mcp | 751 |
| mendex_core/engineering_records | 705 |
| mendex_core/integration_service.py | 654 |
| mendex_core/engineering_lifecycle | 599 |
| mendex_core/cli.py | 527 |
| mendex_core/desktop | 524 |
Legacy UI is the largest package (~38% of src Python).

## Duplication
- Calculation libraries (4): `mendex_core/intelligence/calculations.py` (496), `mendex_core/workflows/nodes/calculations.py` (298), `mendex_core/engineering_records/calculations.py` (73), `src/integrations/calculations/` (power_losses, transformer_design, winding_losses). Numerical divergence NOT VERIFIED; no single source of truth.
- Lifecycle systems (3): `lifecycle/` (used by service.py, pcb.py, mendex_ui), `engineering_lifecycle/` (cli, controller, desktop, mcp, records, reviews), `workflows/` (only service.py and mendex_ui/workflow_canvas).
- Facades (3): `StudioService` (47 defs), `MendexEngineeringController` (38 defs), `DesktopService` (12 defs); see 02 section 5.
- `main.py` and `src/main.py` are near-identical PySide6 launchers.

## Dead / weakly-used code (regex import grep over `src`; dynamic imports not traced)
- `integration_cli.py`: no importer, no console script; only `python -m`.
- `doctor.py`: imported only by `mendex_ui/panels.py`.
- `bom_generator.py`: only `desktop/service.py`.
- `workflows/`: only service.py + legacy UI.
- `intelligence/`: only workflows/nodes + legacy UI.
- `demo_adapter.py`: imported by integration_service.py (demo code in production path; INVESTIGATE).

## Error handling
- Lines matching `except:` or bare `except Exception:` in `src`: 98.
- `except ...:` immediately followed by `pass`: 77 (grep -A1 count). Silent swallowing conflicts with "never fabricate evidence / NOT_EVALUATED" rules (P2); sites not individually reviewed.
- TODO/FIXME in src: 0.

## Typing
- 253 of 589 `def` in mendex_core have return annotations (~43%). Pydantic models used (models.py, integration_contracts.py). No mypy/pyright config in pyproject.toml. TS client uses `(window as any)` (desktop/src/api/client.ts:24).

## Tests
72 `test_*.py` under tests/{core,integration,ui,adapters,contracts,command_center}; 32 files reference `mendex_ui` (legacy UI still heavily tested). Five root `test_*.py` (`test_eeschema_lifecycle.py`, `test_existing_activation.py`, `test_force_foreground.py`, `test_force_pcb.py`, `test_launch_speed.py`) lie outside `testpaths=["tests"]` and are never collected.

## Root-level scratch / hygiene (P3)
`check_windows.py`, `list_all_windows.py`, `list_visible_windows.py`, 5 root `test_*.py`, `drc_test.json`, `erc_test.json`, `edge_snap.png`, `temp_femm_test/` (empty), `sv1000.pdf`, root `__pycache__/`, `build/`, `docs/~$ndex_Developer_Prompt_Handbook.docx` (untracked Office lock file). `git ls-files` shows `drc_test.json`, `edge_snap.png`, `sv1000.pdf` are tracked.
Docs sprawl: >35 version-specific reports in docs/ (V1_8, V1_9, V20_*, V21_*, IMPLEMENTATION_STATUS_V1_7.md) plus `docs/chats/`.
