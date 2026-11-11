# 05 Engineering Projects Audit (independent)

Method: live runs through MendexEngineeringController against %TEMP%\mendex-audit\core (script core_probe.py).

## Concept
- "Engineering Project" is NOT the user-facing concept. The nav item is "Engineering Workspaces" (window.py:155-163). The same page also has "Create New Product", revision controls and a 12-stage lifecycle overview. The command palette says "Open Engineering Workspaces" (window.py:394).

## Stores and duplication
- **Products, revisions, validations, reports and runs** are kept in SQLite (.mendex/studio.sqlite3, service.py:30) plus files under products/<id>/revisions/<rid>/.
- **Workspaces** are kept in the integration_workspaces table plus workspaces/<id>/ folders.
- **Designs** are kept as engineering_designs/<uuid>.json, flat at the data root, outside any product or workspace folder.
- **Lifecycle approvals** are kept in the lifecycle_approvals table.
- **P1:** Workspace and Product are two parallel "project" concepts. They are linked only by an optional product_id (controller.py:124). delete_product just sets the workspace link to NULL (service.py:276), which leaves orphaned workspaces. I did not find the same record duplicated across stores. The risk is conceptual duplication and weak linkage.

## Live operations (temp root)
- Worked: create_workspace, list_workspaces, create_product (auto-creates revision R001), get_workspace_status and list_design_artifacts (both empty), validate_specification (rejects a bad spec), and generate_report.
- Path traversal is blocked (controller.py:75, live ValueError).
- run_calculation('buck_inductor') fails: unsupported type.
- Designs and simulations end-to-end: NOT VERIFIED (solvers out of scope).

## Existing repo data
- Contents: workspaces/ (default, 4f7a9de8-...), products/ (empty), engineering_designs/ (2 JSON files).
- Loadability: NOT VERIFIED. The data was not copied or loaded, to keep the repo read-only.
