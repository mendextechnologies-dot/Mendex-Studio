# Mendex Engineering Studio v0.1 — Day 2 framework

Local Python/PySide6 desktop with SQLite products, typed specifications, immutable previous revisions, filesystem workspaces, native-tool discovery, manual evidence records and draft reports. No engineering calculations or simulation results are produced by the application.

## Install and run (PowerShell)

Tested Python runtime: 3.13.7 x64. The development host reports Windows 10 Home; other machines and Windows 11 are not yet qualified.

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

## Day 2 workflow

1. Select a product and revision in Products. Engineering module screens show its native-file folders and required inputs.
2. Open Tool Manager. Use discovery or browse to an installed executable and Save path. FOUND_UNVERIFIED means compatibility and benchmarks are pending, not ready to simulate. Unknown versions remain unknown. No native tool is launched.
3. Open Validation and record a manual check. The default NOT_EVALUATED entry needs a check ID, reviewer and notes. To record PASS/FAIL, attach an actual evidence file (up to 50 MiB), supply a value and SI unit, and enter minimum and/or maximum. The requested status must match that inclusive numerical criterion. All values, evidence classifications and reviewer identities are manually supplied.
4. Open Reports, Generate draft dossier, select it and Open selected report. The HTML and `snapshot.json` contain frozen specifications, validation history, hashes, tool inventory and warnings. No released status is available.

Evidence copies and metadata are append-only through the service. If specifications change, existing check records remain historical and their effective status becomes NOT_EVALUATED. Missing/modified evidence also becomes NOT_EVALUATED on recheck. Creating a new revision starts a new validation history. Reports do not infer an overall approval from historical PASS entries.

```powershell
.venv\Scripts\python -m mendex_core.cli validation --revision <revision-uuid>
.venv\Scripts\python -m mendex_core.cli report --revision <revision-uuid>
.venv\Scripts\python scripts/desktop_smoke.py
```

Database schema v2 migrates existing v1 data automatically. Before upgrading, close Studio and back up `.mendex` and `products` together. To roll back the application, restore the matching pre-upgrade backup; do not open v2 data with the Day 1 build. HTML/JSON are the supported draft formats; Word/PDF export remains unavailable.

See [implementation checklist](docs/implementation-checklist.md), [architecture](docs/architecture.md) and [known limitations](docs/known-limitations.md). No CI/CD or deployments are configured.
