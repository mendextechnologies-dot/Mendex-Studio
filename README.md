# Mendex Engineering Studio v0.1.0 — foundation

Local Python/PySide6 desktop with SQLite products, typed specifications, immutable previous revisions, filesystem workspaces, native-tool discovery, manual evidence records and draft reports. No engineering calculations or simulation results are produced by the application.

## Install and run (PowerShell)

Tested Python runtime: 3.13.7 x64. Runtime diagnostics report Windows 11 build 26300; the initial Windows marketing-name query returned Windows 10 Home. Only this development workstation has been tested; other machines remain unqualified.

Repository: https://github.com/mendextechnologies-dot/Mendex-Studio · working branch: `main`.

Clone and bootstrap (Git, Python 3.13 and VS Code must be separately installed):

```powershell
git clone https://github.com/mendextechnologies-dot/Mendex-Studio.git
cd Mendex-Studio
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
.venv\Scripts\python -m mendex_ui
```

The bootstrap sets up only this repository's virtual environment, runs local tests and Doctor, and never installs native engineering tools. `ExecutionPolicy Bypass` applies only to that PowerShell invocation; it does not change system policy.

Equivalent manual setup:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python -m pip install -e . --no-deps
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m mendex_ui
```

Use `--root C:\YourDataFolder` to select a different data directory. Both UI and CLI default to the current directory. Never delete `.mendex` to upgrade; back up `.mendex` and `products` together with the application closed.

```powershell
.venv\Scripts\python -m mendex_core.cli create MC-100 "Transformer pilot" --owner "Engineer"
.venv\Scripts\python -m mendex_core.cli products
.venv\Scripts\python -m mendex_core.cli tools
```

Create products in Products, edit the typed JSON specification, save, then create R002 to preserve R001. Null fields mean unspecified; SI field names carry units. Revision snapshots copy specifications only; native CAD files are not automatically copied. Archived specifications cannot be edited.

## Engineering workflow

1. Select a product and revision in Products. Engineering module screens show its native-file folders and required inputs.
2. Open Tool Manager. Use discovery or browse to an installed executable and Save path. FOUND_UNVERIFIED means compatibility and benchmarks are pending, not ready to simulate. Unknown versions remain unknown. No native tool is launched.
3. Open Validation and record a manual check. The default NOT_EVALUATED entry needs a check ID, reviewer and notes. To record PASS/FAIL, attach an actual evidence file (up to 50 MiB), supply a value and SI unit, and enter minimum and/or maximum. The requested status must match that inclusive numerical criterion. All values, evidence classifications and reviewer identities are manually supplied.
4. Open Reports, Generate draft dossier, select it and Open selected report. The HTML and `snapshot.json` contain frozen specifications, validation history, hashes, tool inventory and warnings. No released status is available.
5. In Products, use Open in VS Code to open the selected revision folder, Open workspace for File Explorer, or Open project file for an associated native application. Files must be inside that revision workspace and use a supported document/CAD extension. Scripts and executables cannot be opened through this action. VS Code, Windows associations and CAD applications must already be installed.
6. In Tool Manager, Run workstation doctor or Export diagnostics. Exports stay under `.mendex/diagnostics`; review environment paths before sharing.
7. In Knowledge Center, review category-specific Engineering rules, loaded/rejected Plugins and the AI interface's explicit availability response. No provider or network connection is configured; no AI-generated engineering answer is produced.
8. In Simulations, record an availability request. It persists the input snapshot and tool metadata as NOT_SUPPORTED, with no solver start or result. This is a job-model foundation, not a simulation runner.

Draft revisions can be renamed or placed In Review. Review locks specification edits until returned to Draft; archived baselines cannot be reopened. Neither state grants product approval. Export specification creates a new JSON snapshot under requirements/; the database remains canonical. Product and specification edits save atomically. Evidence files keep their original name in metadata and use compact internal paths; Open selected evidence checks the hash before invoking an allowed document association.

Evidence copies and metadata are append-only through the service. If specifications change, existing check records remain historical and their effective status becomes NOT_EVALUATED. Missing/modified evidence also becomes NOT_EVALUATED on recheck. Creating a new revision starts a new validation history. Reports do not infer an overall approval from historical PASS entries.

```powershell
.venv\Scripts\python -m mendex_core.cli validation --revision <revision-uuid>
.venv\Scripts\python -m mendex_core.cli report --revision <revision-uuid>
.venv\Scripts\python -m mendex_core.cli open-vscode --revision <revision-uuid>
.venv\Scripts\python -m mendex_core.cli open-file --revision <revision-uuid> requirements/spec.json
.venv\Scripts\python -m mendex_core.doctor --export
.venv\Scripts\python -m mendex_core.cli rules
.venv\Scripts\python -m mendex_core.cli plugins
.venv\Scripts\python -m mendex_core.cli request-simulation --revision <revision-uuid> --tool ltspice
.venv\Scripts\python -m mendex_core.cli runs --revision <revision-uuid>
.venv\Scripts\python scripts/desktop_smoke.py
```

Doctor returns exit code 0 when the Python/Qt/SQLite framework is usable. Its workstation status remains PARTIAL while native tools and benchmarks are unqualified. BLOCKED or invalid CLI operations return a nonzero exit code with actionable JSON diagnostics. A successful process handoff does not prove a CAD application opened or executed correctly.

To verify a non-editable wheel installation in a fresh environment on this workstation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_install.ps1
```

This retains the verification environment in ignored `.mendex/qa`; it does not replace a second-engineer clean-machine acceptance test. See [manual acceptance](docs/manual-acceptance.md) for the remaining release gates.

Database schema v3 migrates existing v1/v2 data automatically and preserves evidence. Before upgrading, close Studio and back up `.mendex` and `products` together. To roll back the application, restore the matching pre-upgrade backup; do not open v3 data with an older build. HTML/JSON are the supported draft formats; Word/PDF export remains a post-foundation enhancement.

Data-only plugins can extend discovery and rules using [the template](templates/plugins/example-discovery.json); see [configuration instructions](config/README.md). The loader rejects invalid/conflicting manifests without importing Python. Built-in metadata and rule resources ship inside the wheel. Tool versions are read from available Windows file metadata; runtime compatibility remains unqualified.

Manual primary-workstation handoff and packaging commands:

```powershell
.venv\Scripts\python scripts/interactive_acceptance.py --launch
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package.ps1
```

The first command opens actual VS Code, File Explorer and a harmless uniquely named text fixture, observes the matching windows and retains an acceptance record under ignored `.mendex/qa`. The second requires committed sources, runs local tests and produces a wheel/source archive/checksums under `dist`. Neither command runs a simulator, controls hardware or deploys software. The [v0.1 requirements matrix](docs/requirements-matrix.md) records what is implemented and what the final addendum explicitly excludes.

See [implementation checklist](docs/implementation-checklist.md), [architecture](docs/architecture.md) and [known limitations](docs/known-limitations.md). No CI/CD or deployments are configured.
