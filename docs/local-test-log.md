# Local verification — 10 November 2026 (Asia/Calcutta)

Milestone: Day 1 foundation, version 0.1.0.dev1.

Environment: Windows reports Windows 10 Home Single Language, 64-bit, version 2009. Python 3.13.7; Git 2.48.1.windows.1; VS Code CLI found under the user's Programs directory. Python dependencies installed inside `.venv`; exact resolved versions recorded in requirements-lock.txt. Editable package install succeeded.

`python -m pytest -q`: **10 passed**. Coverage includes SQLite creation/newer-version rejection, typed SI constraints, non-finite rejection, persistence after restart, revision copying and archived immutability, duplicate code/label handling, path traversal rejection, workspace failure rollback, and real-service PySide6 editor save/reopen. No external simulator required.

`python scripts/desktop_smoke.py`: passed. Screenshot visually inspected after explicitly loading Segoe UI for the offscreen Windows font backend. QA screenshot lives under ignored `.mendex/qa`; disposable demo data is removed after capture. Full interactive desktop/second-machine acceptance remains pending.

`python -m mendex_core.cli --help`: passed. Product create/list use the same tested application service. The documented module entry point was launched via a short timed smoke session and exited normally.

Preliminary native inventory: LTspice executable exists at `C:/Program Files/ADI/LTspice/LTspice.exe`; Windows file metadata reports 26.1.1.0. No simulation or benchmark run. FEMM default `C:/femm42/bin/femm.exe` absent; no KiCad CLI under `C:/Program Files/KiCad` or PATH. Discovery is incomplete until Day 2 configurable registry is implemented. No tools installed or global PATH changed.

Release gates outstanding: Day 2/3 functionality, fresh-machine install reproduction, native tool qualification and second-engineer acceptance. No release tag, signed installer, remote repository or CI/CD created.

## Day 2 milestone — 10 November 2026 (Asia/Calcutta)

Version 0.1.0.dev2. SQLite schema v2 adds persisted executable settings, validation records and report indexes. The v1 migration preservation test passes. No dependency changes.

`python -m pytest -q`: **17 passed**. Additional tests cover missing/configured/disappearing binaries, duplicate plugin registration, disabled solver execution, unevaluated records surviving restart, rejection of PASS without evidence or matching numerical criteria, SQL append-only protection, independent evidence copies, tampering detection, stale specifications, intentional numerical FAIL, archived-baseline protection, failed attachment rollback, escaped HTML, and real desktop validation/report views.

`python -m mendex_core.cli --root .mendex/qa/day2-tools tools`: passed. LTspice FOUND_UNVERIFIED; FEMM/KiCad NOT_INSTALLED in searched locations. All reported versions and compatibility remain unknown; no solver or native installer executed.

`python scripts/desktop_smoke.py`: passed with disposable demo data, a NOT_EVALUATED record and a draft dossier. Six screen captures generated and visually inspected for local QA. No actual calculation/simulation/measurement evidence is created by the demo.

Editable installation refreshed successfully to 0.1.0.dev2 using the documented isolated-build install. A trial with `--no-build-isolation` failed because setuptools is not installed in the runtime venv; the standard documented command succeeded. Build isolation remains required for this setup.

Remaining release gates: Day 3 integration and doctor/diagnostic export, clean-machine/second-engineer qualification, native benchmark verification, optional manual packaging. No release tag or manufacturing approval.
