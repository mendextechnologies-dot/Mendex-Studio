# Local verification — 10 November 2026 (Asia/Calcutta)

Milestone: Day 1 foundation, version 0.1.0.dev1.

Environment: Windows reports Windows 10 Home Single Language, 64-bit, version 2009. Python 3.13.7; Git 2.48.1.windows.1; VS Code CLI found under the user's Programs directory. Python dependencies installed inside `.venv`; exact resolved versions recorded in requirements-lock.txt. Editable package install succeeded.

`python -m pytest -q`: **10 passed**. Coverage includes SQLite creation/newer-version rejection, typed SI constraints, non-finite rejection, persistence after restart, revision copying and archived immutability, duplicate code/label handling, path traversal rejection, workspace failure rollback, and real-service PySide6 editor save/reopen. No external simulator required.

`python scripts/desktop_smoke.py`: passed. Screenshot visually inspected after explicitly loading Segoe UI for the offscreen Windows font backend. QA screenshot lives under ignored `.mendex/qa`; disposable demo data is removed after capture. Full interactive desktop/second-machine acceptance remains pending.

`python -m mendex_core.cli --help`: passed. Product create/list use the same tested application service. The documented module entry point was launched via a short timed smoke session and exited normally.

Preliminary native inventory: LTspice executable exists at `C:/Program Files/ADI/LTspice/LTspice.exe`; Windows file metadata reports 26.1.1.0. No simulation or benchmark run. FEMM default `C:/femm42/bin/femm.exe` absent; no KiCad CLI under `C:/Program Files/KiCad` or PATH. Discovery is incomplete until Day 2 configurable registry is implemented. No tools installed or global PATH changed.

Release gates outstanding: Day 2/3 functionality, fresh-machine install reproduction, native tool qualification and second-engineer acceptance. No release tag, signed installer, remote repository or CI/CD created.
