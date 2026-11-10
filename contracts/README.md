# Application service contract v0.1

Canonical Pydantic models: `src/mendex_core/models.py`, `src/mendex_core/evidence.py` and `src/mendex_core/adapters/registry.py`. Generated JSON schemas and an illustrative payload live here. UI and CLI use `StudioService(root)`.

Day 1 operations: create_product(code, name, category, owner, description), list_products(), get_product(id), get_revision(id), list_revisions(product_id), update_specification(revision_id, Specification), create_revision(product_id, label), create_workspace(revision_id), update_product(id, name, owner, description).

Day 2 operations: configure_tool(tool_id, path=None), list_tools(), check_tool(tool_id), list_runs(revision_id), record_validation(revision_id, ManualCheck, evidence_path=None), list_validation(revision_id), validation_summary(revision_id), validation_integrity(record), generate_report(revision_id), list_reports(revision_id).

Validation records are append-only. PASS/FAIL requires an evidence file and an evaluated inclusive numerical min/max rule. The reviewer supplies the value, criterion, evidence type and identity; Mendex does not authenticate them or authorize the threshold. Evidence is copied with SHA-256 and a frozen specification. `validation_summary` returns effective_status, stale and evidence_integrity separately from the original record; both desktop and CLI use this operation. Stale or damaged evidence is NOT_EVALUATED. Records are historical; no overall product approval is inferred. New revisions do not inherit validation.

Tools expose discovery only; detected executables remain FOUND_UNVERIFIED, versions unknown, self-tests NOT_EVALUATED. `AdapterRegistry.register()` accepts reviewed adapter objects, rejects duplicate IDs and allows extensions without core edits. Arbitrary third-party plugin loading is deliberately unavailable. SimulationRun is a typed future contract; list_runs returns an empty list and adapters reject run calls. Reports are draft HTML + frozen JSON, never RELEASED. VS Code launching/doctor remain Day 3 work.

Errors: `StudioError.code` is INVALID_INPUT, NOT_FOUND, CONFLICT, IMMUTABLE or STORAGE_ERROR. Pydantic rejects unknown fields and non-finite quantities. Registry misuse raises ValueError and disabled adapter execution raises NotImplementedError.
