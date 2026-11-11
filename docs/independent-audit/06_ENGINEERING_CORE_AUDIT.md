# 06 Engineering Core Audit (independent)

Method: scratch scripts in %TEMP%\mendex-audit\scripts (core_probe.py, integ.py, conc.py, ui.py), data root %TEMP%\mendex-audit\core. `pytest tests/core` (.venv, PYTHONPATH=src) gave 85 passed in 23.2s. Solvers were NOT run because another auditor covers them.

| Capability | Location / interface | Evidence | Classification |
|---|---|---|---|
| Project mgmt | controller.py:95-170 (workspaces), :699-760 (products); service.py (SQLite .mendex/studio.sqlite3, service.py:30) | Live create/list of a workspace and a product worked | Implemented+verified (two parallel concepts, see 05) |
| Spec storage+validation | controller.py:172-219 | Live run rejected a bad spec (pydantic extra_forbidden) | Implemented+verified |
| Deterministic calcs | controller.py:350 run_calculation | Only 'dowell','losses','steinmetz','flyback' are supported; buck sizing is not exposed (ValueError in live run) | Partial |
| Design synthesis | controller.py:220 generate_design; design/service.py | tests/core/test_v19_design_synthesis.py | Implemented, not verified live |
| Component library | src/mendex_core/components/, UI ComponentLibraryPanel | Panel only registers files/metadata | Partial |
| Artifact generation | design/generators/*, design/service.py:147-173 (sha256) | Not run | Implemented, not verified |
| Simulation orchestration | controller.py:460 run_simulation, ltspice_runner.py, femm_runner.py | Out of scope | NOT VERIFIED |
| Native tool integration | controller.py:811-850 list/check/open tool | list_tools returned ltspice/femm/kicad DETECTED | Implemented+verified (detection only) |
| Result extraction | controller.py:604-672 | list_simulations is empty in a fresh root | NOT VERIFIED |
| Validation rules | rules.py; controller.py:762 | A fresh revision returned total_checks 0 | Implemented, not verified |
| Revisions | controller.py:673-698 | R001 is created automatically with the product | Implemented+verified |
| Evidence | evidence.py; pcb.py:243-248 manifest.sha256 | No verify path exists (see 11) | Partial |
| Reporting | controller.py:784 generate_report | report.html and snapshot.json were generated | Implemented+verified. Defect: when revision_id is None it silently uses the first product's first revision (controller.py:787-793) |
| Approvals | lifecycle/engine.py:94 record_stage_approval; lifecycle/ecr.py:166 | No approve tool in MCP or CLI (grep) | Partial |

## Independence
- mendex_core has no PySide6 imports (grep).
- **AI is coupled into the core:** service.py:14 has `from .ai import AIRequest, UnavailableAIService`, and service.py:98 uses AICopilotGateway. intelligence/models.py:243 has `import requests`, so there is network code inside the core package.

## AI and approvals
- ai/gateway.py:110-113 executes an action only if it is APPROVED; otherwise it marks it REJECTED. mcp/server.py has no approve tool.
- **P1:** approval_status is a plain mutable field (ai/models.py:70, design/iteration.py:31). No actor or role check controls who can set it.
- **P0: a destructive delete is exposed to AI.** mcp/server.py:98,489 exposes delete_product, which calls service.py:242-293. That code deletes revisions, validations, reports, runs, lifecycle_approvals, measurements and ECRs, then rmtree's products/<id>. It has no frozen-baseline check. This violates the AGENTS.md rule "never change frozen baselines or raw evidence". The same delete is also on the CLI (cli.py:359).

## NOT_EVALUATED
- There are 67 occurrences in mendex_core, and demo_adapter.py:40 labels its output NOT_EVALUATED.
- The status bar says approval and simulation execution are unavailable (window.py:367).
- Whether every unavailable-check path ends as NOT_EVALUATED is NOT VERIFIED.
