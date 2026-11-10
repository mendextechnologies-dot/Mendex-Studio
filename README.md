# Mendex Engineering Studio v0.1 — Day 1 foundation

Local Python/PySide6 desktop with SQLite products, typed specifications, immutable previous revisions and filesystem workspaces. No engineering calculations or simulation results are produced.

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
```

Create products in Products, edit the typed JSON specification, save, then create R002 to preserve R001. Null fields mean unspecified; SI field names carry units. Revision snapshots copy specifications only; native CAD files are not automatically copied. Archived specifications cannot be edited.

See [implementation checklist](docs/implementation-checklist.md), [architecture](docs/architecture.md) and [known limitations](docs/known-limitations.md). No CI/CD or deployments are configured.
