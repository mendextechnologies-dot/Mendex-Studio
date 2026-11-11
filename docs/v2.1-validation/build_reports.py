"""Build the independent report set from retained execution evidence."""
from pathlib import Path
from collections import Counter
import hashlib, json, xml.etree.ElementTree as ET
D=Path(__file__).parent;E=D/'evidence';R=D.parents[1]
p=json.loads((E/'probes.json').read_text());x=json.loads((E/'extended.json').read_text());u=json.loads((E/'ui.json').read_text());r=json.loads((E/'results.json').read_text())
def write(name,title,body):
    (D/name).write_text('# '+title+'\n\nDate: 11 November 2026 (Asia/Calcutta). Independent audit of the existing working tree; no application repairs.\n\n'+body.strip()+'\n',encoding='utf-8')
def source(path,symbol):
    lines=(R/path).read_text(encoding='utf-8').splitlines()
    n=next((i+1 for i,line in enumerate(lines) if symbol in line),1)
    return f'[{path}:{n}](../../{path}#L{n})'
common='Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.\n\n'
findings=[
('F01','P0','Root confinement fails','MCP lists artifacts outside root using absolute and traversal workspace IDs; core generation also writes outside root.','probes.json: mcp_outside_root_read, mcp_traversal_read; extended.json: outside_root_generate','Validate UUID existence and resolved containment before every read/write/launch, including symlink/junction resolution.'),
('F02','P0','Unsubstantiated engineering evidence','FEMM runner substitutes constant 0.285 T for solver output; fresh desktop workspace claims PCB dimensions, HV clearance and compliance without artifacts.','src/mendex_core/design/femm_runner.py:130; ui-page-1.png; src/mendex_ui/product_lifecycle_panel.py:449','Remove fabricated claims; parse preserved solver output and retain NOT_EVALUATED when unavailable. Do not rewrite historical evidence.'),
('F03','P0','Public simulations cannot execute','LTspice run_transient and FEMM run_script do not exist; both actual AI clients independently hit LTspice failure.','probes.json: cli_simulation_ltspice, mcp_simulation; extended.json: femm_public_dispatch; agent transcripts','Reconcile runner interfaces and result fields through the core; exercise actual CLI/MCP/UI native runs.'),
('F04','P0','Results are not authoritative jobs','Controller returns a new UUID without persisting a job. Lower-core real LTspice produces raw/log files while list_simulations remains empty.','controller.py: run_simulation; probes.json: simulations_after_real_lower_core; results.json','Persist queued/running/terminal jobs and frozen inputs, design/revision IDs, logs and result manifests before returning.'),
('F05','P0','Numerical current extraction is wrong','LTspice parser selects V(vin) as input current and reports 24 A from a 24 V trace.','results.json: raw_variables, current_peaks_by_signal_a; ltspice_runner.py: v_in_idx','Parse exact named current signals and units; reject missing/corrupt signals without success.'),
('F06','P1','Native CAD is not qualified','Generated PCB fails KiCad syntax loading; generated LTspice schematic opens with disconnected components and zero-valued MOSFET labels.','extended.json: real_kicad_drc; native-kicad-drc/kicad_drc.log; native-window-1.png','Validate native schemas/connectivity and compare schematic-derived netlists with the simulated circuit.'),
('F07','P1','Revision/report identity is split','Generated design revisions are JSON IDs; MCP revision/spec/report tools require independent product revision IDs. There is no MCP product-creation tool.','controller.py: generate_design/list_revisions/generate_report; claude-stdout.jsonl','Provide a coherent existing service association before claiming one end-to-end engineering record.'),
('F08','P1','MCP validation summary is broken','Even a valid product revision fails because validation_summary returns a list and controller calls model_dump on it.','probes.json: mcp_validation','Honor the core return contract; verify empty and populated validation histories.'),
('F09','P1','Cleanup is only partial','Workflow canvas/design studio are still constructed; AI chat, providers and obsolete search routes remain.','source-search.txt; cleanup-search.txt; ui.json: obsolete_instantiated/search_navigation','Analyze dependencies, remove obsolete presentation/provider modules and retire unused schema additively without deleting engineering data.'),
('F10','P1','Readiness metrics are partly static','Dashboard counts VERIFIED OPERATIONAL from catalog constants; Settings says MCP ACTIVE & READY without a connection check.','ui-page-0.png; ui-page-6.png; v17_panels.py: refresh_metrics','Derive readiness from persisted operation-specific verification, and display unknown states honestly.'),
('F11','P1','Cross-client state becomes stale','Existing design service misses CLI-created design; new controller sees it. Simulation selector misses external workspace until restart.','probes.json: cache_existing_controller_after_cli/cache_new_controller_after_cli; ui.json','Refresh shared records and define concurrency/notification ownership, avoiding multiple stale design caches.'),
('F12','P1','Malformed MCP can terminate server','Valid JSON arrays and non-object params cause process exit 1 instead of JSON-RPC invalid-request responses; extra tool arguments are ignored.','probes.json: stdio_invalid_envelope, stdio_invalid_params, mcp_unknown_argument','Validate envelopes and advertised schemas before dispatch; return bounded structured errors and keep serving.'),
('F13','P1','CLI validation/errors inconsistent','Negative specification returns valid:false with exit 0; voltage-order validation produces an unserializable ValueError and traceback.','probes.json: cli_spec_invalid, cli_spec_order_invalid','Define validation-failure exit semantics and serialize Pydantic error contexts safely.'),
('F14','P1','UI execution blocks main thread','Simulation button calls synchronous controller execution directly; current public failure prevents a meaningful successful long-run responsiveness acceptance.','simulation_center_panel.py: _run_simulation','Use existing shared asynchronous job services and observe Qt responsiveness during a real job.'),
('F15','P2','Assumptions and calculation provenance incomplete','Empty calculation params run built-in defaults; outputs lack workspace/design/revision association and durable audit records.','controller.py: run_calculation; agent transcripts; probes.json: database_summary','Require or disclose inputs/material provenance; persist engineering calculation records through the shared service.'),
('F16','P1','New clients misclassify live jobs as interrupted','While a synthetic software job is RUNNING, constructing a second StudioService persists FAILED/INTERRUPTED; the original worker later writes SUCCEEDED.','recovery.json: before_second_client, after_second_client, eventual_state; integration_service.py: _recover_interrupted_jobs','Use durable worker ownership/leases and distinguish startup recovery from concurrent client attachment; retain truthful terminal transitions.'),
]
write('01_ARCHITECTURE_AUDIT.md','Architecture audit',common+f'''
**Status: FAIL.** The intended facade exists, but the final command-center architecture is not complete.

CLI and MCP both instantiate `MendexEngineeringController`; that controller calls `StudioService`, `EngineeringDesignService`, synthesis and calculation modules. This is genuine shared code, not separate agent-specific engines. The desktop uses `StudioService` and several independently constructed design/controller instances. `StudioService` itself creates `self.design`, while the controller creates another design service. Each loads a JSON cache only at construction. Existing UI research calculations also contain their own formulas (`ResearchCenterPanel.query_magnet`); not all engineering logic flows through one authoritative service path.

Source: {source('src/mendex_core/controller.py','def __init__')}; {source('src/mendex_core/cli.py','def execute')}; {source('src/mendex_core/mcp/server.py','def _dispatch_tool')}; {source('src/mendex_core/service.py','self.design =')}; {source('src/mendex_ui/v17_panels.py','def query_magnet')}.

Persistence is split among SQLite product/integration metadata, JSON designs under `engineering_designs/`, `workspaces/<integration-id>/generated_artifacts/`, and product revision directories under `products/`. Separate stores can be intentional, but there is no consistent end-to-end identity/result association. F03/F04/F07/F11 prevent authoritative execution and synchronization.

The initial working tree was already dirty. [git_before](evidence/probes.json) preserves its status. No pre-existing source/test/configuration changes were reverted. Foundational `docs/architecture.md` and `contracts/README.md` still describe unavailable execution, whereas newer modules claim real solvers, making documentation version ownership ambiguous. New schema columns/tables are applied while user_version stays 4 (`integration_store.migrate_v5`), so schema version alone cannot identify the actual layout.

Live desktop, CLI/MCP and real agent/native probes are independently retained in [evidence](evidence/). Existing-production database inspection used a read-only SQLite URI; see [results.json](evidence/results.json). No commercial product was developed. No CI/CD, deployment, hardware control or manufacturing approval was added.
''')
cleanup=[
('Built-in AI Copilot','FAIL','service.py constructs AICopilotGateway; ai/gateway.py and ai/models.py remain','Preserve deterministic shared calculations; remove obsolete provider execution separately.'),
('Internal AI chat','FAIL','ai_interactive.py; v17_panels.py still defines AI-facing panels; dashboard Ask AI Assistant button visible','Hidden navigation is not removal.'),
('Unused AI providers/settings','FAIL','ai/config.py, ai_config_dialog.py, provider branches and AI configuration remain','No removal performed; analyze references to read-only availability contracts first.'),
('Visual workflow builder/canvas','FAIL','window.py imports and constructs WorkflowStudioPanel; workflow_canvas package remains','Core workflows may still be shared by tests/jobs; do not delete them wholesale.'),
('Duplicate design editors/generation','FAIL','window.py constructs EngineeringDesignStudioPanel; header/dashboard New Engineering Design actions remain','Native generation functionality must survive a presentation cleanup.'),
('Unnecessary design screens','FAIL','Legacy panels are instantiated outside the seven-page navigation','Runtime ui.json confirms object existence.'),
('Unused external integrations','NOT VERIFIED','18 catalog entries plus separate ngspice inventory; commercial stubs and research registrations remain','Purpose/classification below; no proof all are required.'),
('Obsolete backend services','FAIL','AI gateway and workflow storage/execution are initialized on every StudioService','Dependency review required before safe retirement.'),
('Obsolete navigation/settings','FAIL','Search selects rows 10–15 despite seven-item navigation; Settings still titled AI Integration','Reproduced selected_row=-1 for four searches.'),
('Unused packages/dependencies','NOT VERIFIED','pyproject.toml only declares Pydantic/PySide6 and pytest dev; installed inventory in probes.json runtime','No new unused cloud SDK dependencies declared; complete installed-package necessity not established.'),
('Obsolete database structures','NOT VERIFIED','workflows/workflow_runs/lifecycle_approvals tables remain in readonly inventory','Retire only by tested additive migration; do not delete engineering histories.'),
('Broken imports/startup','PASS (bounded)','On-screen Windows Qt application started, seven pages loaded and restart preserved specification','Does not validate every action or hidden feature.'),
('Existing engineering data preserved','PASS (bounded)','Hash comparison of products/workspaces/designs/reports and top-level .mendex files: no added/removed/modified entries','Historical .mendex/qa/backups subtrees not exhaustively rehashed; no audit writes target them.'),
]
write('02_APPLICATION_CLEANUP_AUDIT.md','Application cleanup audit',common+'''
**Status: FAIL.** Primary navigation was simplified, but obsolete functionality was hidden or retained.

Searches: `rg -n 'ai_copilot|AIInteractive|AICopilot|AIKeySetup|WorkflowStudioPanel|EngineeringDesignStudioPanel|generate_design|calculate_|VERIFIED OPERATIONAL|IPC-2221B|ACTIVE & READY' src pyproject.toml` and repository cleanup search for provider, Supabase, workflow and editor references. Exact matches are retained in [source-search.txt](evidence/source-search.txt) and [cleanup-search.txt](evidence/cleanup-search.txt). Historical documents/tests are evidence of old scope, not proof of active code; source construction/imports distinguish active retention.

| Feature/check | Outcome | Actual evidence | Dependency/data disposition |
|---|---|---|---|
'''+''.join('| '+' | '.join(row)+' |\n' for row in cleanup)+'''
The audit removed no application modules, dependencies, database structures or engineering records. Runtime imports and the existing regression suite are tested separately. Supabase is not a declared dependency and none of the executed local workflows required it. This does not establish an exhaustive disconnected-network qualification.
''')
write('03_UI_VALIDATION.md','Desktop UI validation',common+f'''
**Status: FAIL.** Actual Windows Qt platform `{u['platform']}`, native window ID `{u['native_window_id']}`, visible desktop window; not the offscreen test platform. [ui_probe.py](ui_probe.py) launched the application, selected every main page, captured widget text/buttons/tabs, exercised stale search routing, created an external workspace and reopened the application. See [ui.json](evidence/ui.json) and screenshots [0](evidence/ui-page-0.png), [1](evidence/ui-page-1.png), [2](evidence/ui-page-2.png), [3](evidence/ui-page-3.png), [4](evidence/ui-page-4.png), [5](evidence/ui-page-5.png), [6](evidence/ui-page-6.png).

| Check | Status | Observation |
|---|---|---|
| Seven primary navigation labels | PASS | Dashboard, Engineering Workspaces, Simulation Center, Component Library, Engineering Tools, Reports & Evidence, Settings |
| Seven primary pages select/load | PASS | Rows 0–6 match current page; no captured exception |
| Required workspace information architecture | FAIL | Engineering Workspaces is still product catalog + 12-stage lifecycle and specification editor, not nine requested workspace sections |
| Obsolete controls removed | FAIL | Ask AI Assistant and New Engineering Design remain; legacy workflow/design panels still constructed |
| Search navigation | FAIL | LTspice/jobs/workflow/design select row -1; old rows 10–15 remain in source |
| Evidence accuracy | FAIL | Empty generic workspace displays fixed PCB dimensions, HV clearance and safety compliance; F02 |
| Tool/MCP status accuracy | FAIL | Fixed operational catalog and ACTIVE & READY labels; F10 |
| External state updates | FAIL | Simulation workspace selector remains at 2 after new external workspace, reaches 3 on restart (includes product workspace) |
| Dashboard workspace count | PASS after explicit refresh | 1 before external creation; remains stale, then becomes 2 after Refresh Status |
| Restart persistence | PASS (bounded) | One product, two integration workspaces and stored 24 V/5 V/4 A specification survive reopening |
| Long-job responsiveness | NOT_EVALUATED | Successful public run is blocked by F03; source calls solver synchronously on GUI thread (F14) |
| All action buttons | NOT_EVALUATED | Visible controls inventoried, not every modal/export/edit/approval action executed |
| Real raw waveform loading | PASS (bounded) | [results.json](evidence/results.json), [waveform screenshot](evidence/ui-real-waveforms.png); manual file load is not persisted job synchronization |

Visual inspection also found clipped lifecycle action labels and crowded horizontal stage/tab content. The generated native LTspice drawing opens as disconnected components, retained separately in [native-window-1.png](evidence/native-window-1.png).
''')
write('04_ENGINEERING_CORE_VALIDATION.md','Engineering Core validation',common+f'''
**Status: FAIL overall; meaningful local capabilities work.** [probes.json](evidence/probes.json), [extended.json](evidence/extended.json), [results.json](evidence/results.json) and source references below are the basis.

| Capability | Result | Evidence/limitation |
|---|---|---|
| Workspace creation/list/persistence | PASS | CLI/MCP + 8 concurrent creations and restart |
| Specification schema/save | PASS (bounded) | Typed positive/negative SI validation; product revision hash retained; ordering error serialization fails at CLI boundary |
| Four deterministic calculations | PASS for execution | Dowell, semiconductor losses, Steinmetz, flyback; defaults/material assumptions and durable provenance incomplete |
| Supported buck synthesis | PASS for generation only | JSON design, candidates and four native artifacts exist; solver voltage requirement fails and CAD validity is incomplete |
| Unsupported type/workspace rejection | FAIL | Nonexistent workspace and category UNSUPPORTED_CATEGORY are accepted as SYNTHESIZED |
| Component library | NOT VERIFIED | Shared component service/UI inventory exists; complete persistence/edit provenance not exercised |
| Public simulations/results | FAIL | Missing runner methods, no persisted public jobs/results |
| Lower-level LTspice | Executes, design validation FAIL | 14,236 real raw points; mean {r['independent_vout_mean_v']:.6f} V, ripple {r['independent_vout_ripple_v']:.6f} V, target 5 V ±5% |
| Lower-level FEMM adapter | PASS for recorded reference | Native .fem/.ans/results.txt, real inductance; separate design FEMM runner fabricates B (F02) |
| Product revision preservation | PASS (bounded) | R001 archived, R2 draft, archived modification rejected |
| Design/product revision consistency | FAIL | F07 |
| Validation summary facade | FAIL | Valid product revision yields list.model_dump exception |
| Draft report generation | PASS (bounded) | Actual HTML/JSON reports exist with hashes; not evidence of executed design qualification |
| Product approval assignment | Correctly unavailable | APPROVED transition rejected; no manufacturing approval implemented |
| Lifecycle reviewer authentication | NOT VERIFIED | record_stage_approval accepts caller-supplied identity with no authentication; no audit approval granted |

Core source: {source('src/mendex_core/controller.py','def run_calculation')}; {source('src/mendex_core/design/service.py','def _persist')}; {source('src/mendex_core/design/ltspice_runner.py','v_in_idx =')}; {source('src/mendex_core/design/femm_runner.py','b_measured =')}; {source('src/mendex_core/service.py','def set_revision_status')}. Synthesis estimates such as fixed efficiency/feasibility are heuristics, not verified numerical evidence. The UI research panel still contains its own Steinmetz expression and fixed dataset claims.
''')
clirows=[]
for name,entry in p.items():
    if name.startswith('cli_') and name!='cli_help':
        v=entry.get('returned',{});stdout=v.get('stdout','');stderr=v.get('stderr','')
        try:json.loads(stdout);structured='JSON stdout'
        except Exception:
            try:json.loads(stderr);structured='JSON stderr'
            except Exception:structured='no structured JSON' if not stdout else 'non-JSON stdout'
        clirows.append((name,str(v.get('exit_code','harness exception')),structured))
write('05_CLI_VALIDATION.md','CLI validation',common+'''
**Status: FAIL.** CLI is genuinely executable without the desktop, and many operations persist real data. Every command and full stdout/stderr/exit code below is in [probes.json](evidence/probes.json). Each subprocess used `.venv/Scripts/python.exe -m mendex_core.cli --root <isolated-audit-root> ...`; available commands are preserved in `cli_help`.

The supported v2.1 groups are workspace (list/create/status), specification (validate/save), design (generate/show/candidates), calculate (dowell/losses/steinmetz/flyback), simulation (run/list), artifact (list/open), tool (list/check/open). Legacy product creation/list, report, validation, diagnostics, rules/plugins, simulation-availability and PCB commands also remain. There is **no CLI revision-create/history command** and no separate real-result retrieval command; list_simulations reads integration_jobs, which public run does not populate.

| Executed case | Process exit | Output shape |
|---|---|---|
'''+''.join('| '+' | '.join(row)+' |\n' for row in clirows)+'''
Valid/invalid cases cover all new groups and legacy validation/report. Negative voltage produces valid:false but exit 0. Reversed input voltage order crashes JSON serialization with TypeError. Simulation's nonexistent runner produces a traceback, not the documented JSON error. Unknown workspace status returns success and a fabricated path/state envelope instead of NOT_FOUND. Invalid solver choice is rejected by argparse with exit 2 and plain usage text even with JSON mode; `--json` is not a universal structured-error guarantee.

Persistence is demonstrated across independent CLI subprocesses and new core instances. Product revision association works for specification/report operations but is absent from generic calculation output and public simulation jobs. No audit log records calculations/simulation dispatch failures (`activities=0`, `integration_jobs=0` in the snapshot). Isolation fails through shared controller path handling; see report 11.

Unexecuted legacy leaves (including all variants of PCB import/notes/check/open, availability/export/open-file commands) remain NOT_EVALUATED at the independent per-command level; existing automated coverage is reported separately. Launch success was tested via the shared native core in report 09, not represented as every CLI launch command passing.
''')
tools=p['mcp_tool_schemas']['returned']
write('06_MCP_VALIDATION.md','MCP validation',common+f'''
**Status: FAIL overall.** Real stdio initialization, initialized notification, tools/list and tools/call succeed. Actual Codex and Claude clients also connect with temporary settings, which is stronger evidence than direct Python unit calls. Server advertises protocol 2024-11-05 and **{len(tools)} tools**: {', '.join('`'+t['name']+'`' for t in tools)}.

[probes.json](evidence/probes.json) preserves exact stdio requests/responses and exit codes, input schemas and controlled tool cases. [audit_probe.py](audit_probe.py) is reproducible against fresh audit data. Core delegation: {source('src/mendex_core/mcp/server.py','def _dispatch_tool')}. MCP contains dispatch, not its own formulas.

| Check | Result |
|---|---|
| Startup, discovery, valid invocation | PASS |
| Text containing structured JSON result | PASS; no outputSchema or structuredContent supplied by server |
| Syntactically invalid JSON | PASS: -32700 parse response, process stays available until EOF |
| Valid JSON array as envelope | FAIL: AttributeError, exit 1 |
| tools/call params as array | FAIL: AttributeError, exit 1 |
| Missing/wrong-type tool arguments | Error text returned, no prior schema validation |
| Unknown argument | FAIL: ignored, workspace created |
| Invalid/nonexistent workspace | FAIL: status accepted; design generation accepted |
| Workspace/filesystem containment | FAIL: outside-root artifact disclosure and core generation writes |
| Unknown destructive tool | Rejected; no delete tool exists |
| Arbitrary calculation shell type | Rejected; shell file opening also rejected by native extension filter |
| Archived revision update | Rejected by StudioService |
| Sensitive native launch approval | NOT VERIFIED; no server-side authorization layer apparent |
| Long-running job protocol/result retrieval | FAIL: synchronous public dispatch, no job persistence |
| Revision/report/validation workflow | FAIL overall: split identity and broken summary facade |
| Durable operation audit log | FAIL for tested generic operations: no activities/jobs written |

Version negotiation/compatibility beyond the actual connected clients is NOT_EVALUATED. Tool calls before initialize are accepted in direct dispatch; lifecycle enforcement is minimal. Errors include internal exception details. This is a local client bridge, not an OS-level filesystem security boundary; nevertheless the requested permitted-root restriction demonstrably fails.
''')
for agent,filename,title in [('codex','07_CODEX_INTEGRATION.md','Codex integration'),('claude','08_CLAUDE_CODE_INTEGRATION.md','Claude Code integration')]:
    transcript='codex-retry-stdout.jsonl' if agent=='codex' else 'claude-stdout.jsonl'
    write(filename,title,common+f'''
**Status: FAIL for the required workflow; actual CLI MCP connectivity verified. VS Code agent-session execution NOT_EVALUATED.** Version: {'codex-cli 0.167.0-alpha.4.1' if agent=='codex' else 'Claude Code 2.1.284'}.

Before the audit, `{'codex mcp list' if agent=='codex' else 'claude mcp list'}` did not contain Mendex. `.vscode/mcp.json` and `mcp_config.json` existed but did not establish this client's connection. Audit-specific absolute executable/root/PYTHONPATH settings were passed only to a child process. Saved client settings were not changed. Commands, exit codes, timing and prompts are in [agents.json](evidence/agents.json){' and [codex-retry.json](evidence/codex-retry.json)' if agent=='codex' else ''}. Full actual tool-call/response evidence: [{transcript}](evidence/{transcript}).

Executed independently: discover MCP engineering tools, list native tools/workspaces, create dedicated workspace, schema-validate 24 V → 5 V at 4 A, synthesize buck + native artifacts, retrieve design/candidates, execute losses calculation, request actual LTspice simulation, retrieve empty history. Simulation returns `LTspiceRunner has no attribute run_transient`. No raw results were invented or substituted. Design/product IDs do not support the required complete revision/report sequence from this generic MCP-created workspace. Calculation output with params {{}} is default-based and not bound to that design.

{'The first Codex attempt connected/discovered tools but calls were rejected by the client tool-approval policy. A second process explicitly approved only the listed isolated audit tools using per-server settings; calls then executed. Both attempts are retained. This was a client policy barrier, not an automatic-review rejection or application repair. See [official MCP configuration](https://learn.chatgpt.com/docs/extend/mcp) for the config/approval boundaries.' if agent=='codex' else 'Claude independently returned a design revision ID and then received Revision not found from validation summary, demonstrating the design/product revision mismatch. No product revision was fabricated to bypass that blocker.'}

Both clients use the same server/controller without agent-specific core changes. Both return losses of conduction 0.18 W, switching 2.5 W, total 2.68 W for identical default inputs. This establishes one deterministic comparison only, not correctness of unsupplied material or design assumptions. Agent-independent solver, revision and report acceptance remains incomplete.

VS Code was already running on this repository. An attempted reuse-window launch returned 9 under the inherited environment; a visible repository VS Code window remained. Neither CLI transcript proves execution inside the VS Code extension/interactive terminal. That specific requested acceptance remains NOT_EVALUATED.
''')
write('09_ENGINEERING_TOOLS_VALIDATION.md','Engineering tools validation',common+f'''
**Status: FAIL for integrated engineering qualification.** Executables are installed, and real lower-layer outputs were obtained. They do not repair the public CLI/MCP/UI workflow.

| Tool/path | Actual execution evidence | Outcome |
|---|---|---|
| LTspice 26.1.1.0, Program Files/ADI/LTspice | Lower-core real batch run; preserved .net/.raw/.op.raw/.log; 14,236 points; native GUI screenshot | Solver executed. 5 V requirement FAIL; public dispatch FAIL; current metric wrong |
| FEMM, C:/femm42/bin/femm.exe, file version 1.0.0.1 | Separate existing adapter executed native .fem/.ans, results.txt and runner log | Reference inductance {x['real_femm_adapter']['returned']['metrics'].get('primary_inductance_h')} H. This is not B-max qualification, and public dispatch FAIL |
| KiCad CLI 10.0.7.51283, Program Files/KiCad/10.0/bin | Real ERC invocation and populated generated-board DRC | ERC exceeded 40 s bound; adapter surfaced FAILED after timeout. DRC exit 3: invalid net syntax |

Evidence: [probes.json](evidence/probes.json) `real_ltspice_lower_core`; [results.json](evidence/results.json) independently parses the raw file; [extended.json](evidence/extended.json); [native-femm](evidence/native-femm/); [native-kicad-erc](evidence/native-kicad-erc/); [native-kicad-drc](evidence/native-kicad-drc/). Initial native adapter probe construction omitted required JobRequest fields and failed in the audit harness before dispatch; corrected real requests are retained in extended.json. Those initial harness errors are not application defects or solver evidence.

LTspice mean output {r['independent_vout_mean_v']:.6f} V and ripple {r['independent_vout_ripple_v']:.6f} V agree with preserved waveform samples. The claimed current 24 A is actually V(vin); independent named-current peaks are in results.json. The generated `.asc` native GUI displays separated, unconnected components, unlike the independently generated simulated `.net`. A file opening is not a valid circuit. Source `generate_asc_schematic` needs native netlist/connectivity qualification.

FEMM's existing integration adapter returns real current/flux linkage/inductance through results.txt. In contrast, the design runner calls `mo_getpointvalues` but discards its response and returns fixed 0.285 T. These paths must not be conflated. No magnetic saturation or isolation compliance is granted.

Native launch requests for LTspice, eeschema and pcbnew returned PIDs. Only LTspice document visibility was confirmed in the retained window inventory/screenshot; successful KiCad document loading remains NOT_EVALUATED and PCB loading is independently known to fail. ERC/DRC success is not inferred from a file or from empty-board tests.

Other integrations: `src/mendex_core/config/integration_catalog.json` documents intended purposes. FreeCAD, Qucs-S, OpenModelica, Python/Jupyter and Git are optional for this target command center; discovery/static inventory alone is configured-but-unverified for independent current workflow qualification. MagNet/SwitchLossDB/benchmark/Princeton entries are optional metadata/research resources, not installed solver proof; unresolved data/license provenance remains unsupported for engineering claims. PLECS, MATLAB/Simulink, Maxwell, Icepak and SolidWorks are optional commercial stubs requiring entitlement/connector verification, unsupported in this acceptance. ngspice is an additional optional adapter outside the primary catalog. No integration was removed; dependency/use evidence is insufficient to call all remaining entries necessary. Installed-package necessity remains NOT VERIFIED.
''')
write('10_WORKSPACE_SYNC_VALIDATION.md','Workspace synchronization validation',common+f'''
**Status: FAIL.** Shared SQLite alone does not produce shared authoritative engineering state.

CLI-created and MCP-created workspaces persist in the same isolated root and are visible to new core instances. Eight concurrent workspace creations succeed; integrity_check is `ok`. A reopened Windows desktop preserves its product specification and sees newly added workspaces. Actual agent tests intentionally use separate roots to prevent cross-agent record contamination; deterministic output comparison does not prove those sessions operated one simultaneously shared root.

Reproduced cache failure: a controller created before a separate CLI design generation returns NOT_FOUND for that design; a newly constructed controller reads the persisted JSON design correctly. `EngineeringDesignService._load_all` only runs at construction. The controller and StudioService construct independent instances. Evidence: [probes.json](evidence/probes.json), keys `cache_existing_controller_after_cli`, `cache_new_controller_after_cli`; source {source('src/mendex_core/design/service.py','def _load_all')}.

Live UI: selector count 2 before and after external workspace creation, 3 after restart; product/integration workspace identities are mixed. Dashboard count updates only with explicit refresh. [ui.json](evidence/ui.json). Generated integration-workspace designs are not automatically associated with the product revision directories displayed by the lifecycle panel. F07 prevents consistent design/revision/report/evidence association.

Hash tracker checks on a disposable copied audit input return UP_TO_DATE → MODIFIED_EXTERNALLY → MISSING; original raw/frozen inputs were not used for the mutation. [extended.json](evidence/extended.json). This validates the hash primitive, not automatic desktop reconciliation or immutable native-file snapshots.

Public and lower-core simulations produce no persisted integration job records for this workflow. Consequently running/completed/failed counts, result notifications and restart recovery cannot be accepted for these runs. Recovery software-fixture evidence is in [recovery.json](evidence/recovery.json); its outcome is discussed in report 11 and is not a real engineering solver test.

Agent transcripts use MCP only; no direct SQLite writes were requested or observed. Main audit snapshots use core services and a read-only URI for existing data. Comprehensive multi-process JSON design-write conflict handling and sustained database-lock behavior remain NOT_EVALUATED.
''')
recovery=json.loads((E/'recovery.json').read_text()) if (E/'recovery.json').exists() else {}
write('11_SECURITY_AND_RECOVERY.md','Security, offline operation and recovery',common+'''
**Status: FAIL.** Controlled canaries were created solely beneath audit evidence, outside the configured audit-data root, to establish the boundary failure without touching unrelated user files.

| Test | Observed outcome |
|---|---|
| Absolute workspace path outside permitted root | Artifact enumeration succeeds and discloses canary path/hash |
| Relative ../../ traversal | Same disclosure |
| Outside-root generation | Four native artifacts written outside configured data root |
| Invalid workspace/category | Accepted as SYNTHESIZED |
| Missing/wrong-type MCP args | Error text; no schema-first validation |
| Unknown MCP arg | Ignored and workspace created |
| Malformed JSON | Parse error returned |
| Malformed JSON-RPC envelope/params | Server process crashes |
| Archived revision modification | IMMUTABLE rejection |
| APPROVED product transition | Rejected, unavailable |
| Unknown destructive MCP tool | Rejected |
| Shell calculation type / .cmd artifact | Rejected; no arbitrary shell executed |
| Invalid executable configuration | Rejected by StudioService |
| Runner constructed with nonexistent explicit executable | Silently discovers installed fallback; not a missing-tool test |
| Missing native input | FileNotFoundError |
| Real LTspice timeout | TIMED_OUT / FAILED, no success; failure absent from persisted job history |
| Corrupt raw output | NOT_EVALUATED as a full native runner scenario; source RAW_EMPTY branch incorrectly sets success=True |
| Missing/externally changed artifact hash | MISSING/MODIFIED_EXTERNALLY primitive detected |
| SQLite integrity | ok for audit and existing read-only DB |
| Sustained lock/interrupted real job/app restart mid-solver | NOT_EVALUATED; successful public real job blocked by dispatch failure |
| Agent connection recovery | Initial Codex policy rejection retained; temporary narrowed policy permits actual calls; no saved config changed |

Exact requests and failures: [probes.json](evidence/probes.json), [extended.json](evidence/extended.json), [recovery.json](evidence/recovery.json). The separate recovery fixture uses `studio-demo`, explicitly synthetic software evidence. No synthetic result is engineering evidence. Recovery outcome: `'''+str({k:(v.get('status') if isinstance(v,dict) else v) for k,v in recovery.items() if k in ['before_second_client','after_second_client','eventual_state','executor_still_running']})+'''`. Initial recovery harness used a nonexistent getter; that harness mistake is separately retained and corrected, not attributed to the application.

Offline operation: Python socket connections were denied within the audit process; persisted workspace reads, deterministic losses and draft report generation succeeded. No Supabase dependency was required. This is bounded evidence only: the workstation network was not disconnected, native child-process networking was not blocked, and complete disconnected UI/native-tool acceptance remains **NOT_EVALUATED**. No firewall/global network setting was altered.

Local core lifecycle approvals accept caller-supplied reviewer text; authenticated reviewer permissions are not established. No engineering/manufacturing approval was granted in the audit. MCP should not gain implicit approval merely because client tool calls are allowed. Production readiness must remain unavailable.
''')
def test_summary():
    path=E/'pytest.xml'
    if not path.exists():return None
    xml=ET.parse(path).getroot();suites=list(xml.iter('testsuite'));cases=list(xml.iter('testcase'))
    totals={'collected_in_report':len(cases),'passed':0,'failed':0,'errors':0,'skipped':0,'duration_s':sum(float(s.attrib.get('time',0)) for s in suites)}
    groups={}
    failures=[]
    for case in cases:
        kind='errors' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        totals[kind]+=1;group=case.attrib.get('classname','').split('.')[1] if '.' in case.attrib.get('classname','') else 'unknown'
        groups.setdefault(group,Counter())[kind]+=1
        if kind in ['failed','errors']:failures.append({'test':case.attrib.get('classname','')+'::'+case.attrib.get('name',''),'detail':(case.find('failure') if kind=='failed' else case.find('error')).text})
    return {'totals':totals,'groups':groups,'failures':failures}
t=test_summary()
(E/'test-summary.json').write_text(json.dumps(t,indent=2),encoding='utf-8')
write('12_AUTOMATED_TEST_RESULTS.md','Automated test results',common+'''
Command: `.venv/Scripts/python.exe -m pytest -q --junitxml=docs/v2.1-validation/evidence/pytest.xml`, all existing tests, no deselection/test edits. Console log: [pytest.log](evidence/pytest.log); machine results: [pytest.xml](evidence/pytest.xml), [test-summary.json](evidence/test-summary.json).

'''+('Full execution still pending; no final suite PASS assigned.' if t is None else 'Final recorded totals:\n\n```json\n'+json.dumps(t['totals'],indent=2)+'\n```\n\nBy repository test group:\n\n```json\n'+json.dumps(t['groups'],indent=2)+'\n```')+'''

Test groups distinguish core/unit/contracts, adapter tests (mixed pure/mocked/real execution), integration tests (mixed software fixtures and native execution), and desktop UI tests (existing tests use offscreen Qt). A directory name is not proof of a real native run. Actual Windows UI tests are separately retained in ui.json/results.json; actual Codex/Claude CLI MCP tests are separately retained in transcripts, outside pytest counts. No pytest test executes a complete VS Code dual-agent acceptance.

The v2.1 E2E test does NOT run a simulation: it generates files/calculations then creates an unrelated product and report. It cannot qualify the requested end-to-end acceptance. The existing FEMM design-runner test accepts the hardcoded B value. Empty-board DRC tests cannot qualify PCB completion. Existing legacy cleanup tests still rely on hidden workflow/design panels. Passing tests do not supersede these source/native failures.

Audit probes are retained as reproducible scripts rather than altering existing tests to pass. Harness mistakes and initial agent client-policy rejection are retained separately. Blocked manual acceptance scenarios are listed in report 13; they are not mislabeled as pytest skips. Fresh regression failures/details, when present, are retained in test-summary.json and raw JUnit XML.
''')
write('13_END_TO_END_EVIDENCE.md','End-to-end acceptance evidence',common+'''
**Status: FAIL.** Two actual CLI agent sessions used independent generic 24 V → 5 V, 4 A references and the same MCP/core; neither completed engineering acceptance. Lower-core solver diagnostics do not substitute for a blocked public step.

| Required step | Codex | Claude Code | Actual evidence / blocker |
|---|---|---|---|
| 1 Open VS Code | Visible existing repository window; relaunch failed | Same workstation | extended.json window inventory; reuse-window exit 9 |
| 2 Connect selected agent in VS Code | NOT_EVALUATED | NOT_EVALUATED | Actual tested sessions are CLI MCP clients, not extension GUI sessions |
| 3 Create workspace | PASS via MCP | PASS via MCP | Actual client transcripts and separate persisted audit roots |
| 4 Record specifications | Partial: requirements in design, not product spec save | Same | Workspace has no product revision needed by save_specification |
| 5 Validate specifications | PASS schema validation | PASS schema validation | Same explicit 24/5/4 inputs |
| 6 Generate supported design | PASS for candidate creation | PASS for candidate creation | Buck design with IDs and requirements persisted |
| 7 Execute deterministic calculations | PASS for generic default inputs | PASS, identical output | 0.18 W conduction + 2.5 W switching = 2.68 W; not design-bound loss evidence |
| 8 Native artifacts | Created, qualification FAIL | Same | Four native artifacts per agent; diagnostic generated PCB invalid, ASC disconnected |
| 9 Actual supported public simulation | FAIL | FAIL | Missing LTspiceRunner.run_transient |
| 10 Capture public solver results | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | No job/result returned |
| 11 Display associated results in Studio | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | Manual lower-core raw viewing separately verified, no persisted public job |
| 12 Open correct native design | NOT_EVALUATED in agent flow | NOT_EVALUATED in agent flow | Separate lower-core LTspice GUI opens but circuit is disconnected; KiCad generated PCB rejects syntax |
| 13 Modify parameter | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | Do not continue an unqualified end-to-end design |
| 14 New design revision | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | MCP product revisions do not address design revision IDs |
| 15 Repeat public simulation | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | Same public dispatch blocker |
| 16 Compare revisions | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | Product revision preservation separately tested, not this complete design flow |
| 17 Engineering report | BLOCKED / NOT_EVALUATED | BLOCKED / NOT_EVALUATED | No valid product revision from generic MCP workflow; unrelated draft report is not substituted |
| 18 Review validation | BLOCKED / NOT_EVALUATED | FAIL / NOT_EVALUATED | Claude gets Revision not found for design ID; separate valid product summary also broken |

Evidence: [Codex transcript](evidence/codex-retry-stdout.jsonl), [Claude transcript](evidence/claude-stdout.jsonl), [probes](evidence/probes.json), [extended](evidence/extended.json), [raw verification and Studio manual view](evidence/results.json). Separate lower-core LTspice raw/log and FEMM results are real, but their tests are diagnostic partial engineering checks, not successful completion of either agent acceptance sequence. No approval, mock waveform, or commercial design project replaced a failed step.
''')
write('14_REMAINING_GAPS.md','Prioritized remaining gaps and remediation plan',common+'''
**Audit-only plan; no repairs automatically applied.** P0 blocks release because it concerns evidence integrity, security or essential execution. P1 blocks requested v2.1 acceptance. P2 improves completeness after those gates.

| ID | Priority | Finding | Reproduction/evidence | Required remediation |
|---|---|---|---|---|
'''+''.join('| '+' | '.join([id,priority,title+': '+detail,evidence,fix])+' |\n' for id,priority,title,detail,evidence,fix in findings)+'''
Sequence: first contain root access and stop unsubstantiated evidence claims; then reconcile real runner APIs, typed results and persisted job identity; validate generated native CAD and numerical parsers; unify design/product revision/report associations; fix synchronization/recovery and invalid-request handling; complete dependency-led cleanup and UI navigation. Finally run the unchanged suite plus targeted regressions and both full VS Code agent workflows with real solvers. Preserve frozen baselines and raw evidence throughout. Do not implement manufacturing approval, automatic deployment, CI/CD or hardware control.

Additional qualification gaps: true disconnected network operation; authenticated lifecycle review; controlled lock and real-job interruption/restart; corruption/missing-result failures; all visible action buttons; per-command validation of unexecuted legacy leaves; independent optional-tool/dataset licensing and operation verification; native schematic netlist equivalence and populated-board ERC/DRC. Each remains NOT_EVALUATED until evidence exists.
''')
score=[
('Application cleanup','FAIL','02_APPLICATION_CLEANUP_AUDIT.md','Legacy AI/workflow/design code still initialized'),
('Simplified UI','FAIL','03_UI_VALIDATION.md','Seven labels work; stale search and retained obsolete actions/workspace structure'),
('Engineering Core','FAIL','04_ENGINEERING_CORE_VALIDATION.md','Real primitives work; evidence/result/identity defects'),
('CLI','FAIL','05_CLI_VALIDATION.md','Simulation crashes and inconsistent structured validation'),
('MCP server','FAIL','06_MCP_VALIDATION.md','Containment bypass, malformed-request crashes, broken operations'),
('Codex integration','FAIL','07_CODEX_INTEGRATION.md','Actual CLI MCP works partially; full workflow fails; VS Code NOT VERIFIED'),
('Claude Code integration','FAIL','08_CLAUDE_CODE_INTEGRATION.md','Independent CLI MCP works partially; full workflow fails; VS Code NOT VERIFIED'),
('LTspice','FAIL','09_ENGINEERING_TOOLS_VALIDATION.md','Real lower-core solver runs; public dispatch, current metric and ASC connectivity fail'),
('FEMM','FAIL','09_ENGINEERING_TOOLS_VALIDATION.md','Real adapter inductance exists; design B fabricated, public dispatch fails'),
('KiCad','FAIL','09_ENGINEERING_TOOLS_VALIDATION.md','Generated board rejects syntax; ERC times out'),
('Workspace synchronization','FAIL','10_WORKSPACE_SYNC_VALIDATION.md','Stale design cache/UI selectors; missing jobs'),
('Dashboard accuracy','FAIL','03_UI_VALIDATION.md','Static operational/compliance claims; workspace count needs refresh'),
('Revision management','FAIL','04_ENGINEERING_CORE_VALIDATION.md','Product archive works, design revision/report association incomplete'),
('Validation and approvals','FAIL','11_SECURITY_AND_RECOVERY.md','Product approval rejected correctly; summary broken, reviewer permissions unverified'),
('Offline operation','NOT VERIFIED','11_SECURITY_AND_RECOVERY.md','Python socket-denied subset passes; OS disconnected acceptance NOT_EVALUATED'),
('End-to-end engineering workflow','FAIL','13_END_TO_END_EVIDENCE.md','Both actual agent workflows stop before simulation/results/revisions/report'),
]
write('15_FINAL_INDEPENDENT_SIGNOFF.md','Final independent signoff',common+'''
**Classification: NOT READY.** Critical engineering evidence integrity, filesystem confinement and public simulation execution requirements fail. The application has working local foundations and partial agent connectivity; neither dual-agent VS Code acceptance nor production engineering readiness is established.

| Area | Status | Evidence | Remaining issues |
|---|---|---|---|
'''+''.join('| '+area+' | '+status+' | ['+file+']('+file+') | '+issues+' |\n' for area,status,file,issues in score)+'''
Acceptance is denied by reproduced failures, independently of the final automated-test count. Full test statistics are in [report 12](12_AUTOMATED_TEST_RESULTS.md). Detailed P0/P1/P2 work and retest gates are in [report 14](14_REMAINING_GAPS.md). No engineering or manufacturing signoff is granted by this software audit.

Audit changes are limited to this report/evidence/probe directory and an appended implementation-checklist milestone. No application fixes, baseline changes, raw-evidence edits, dependency cleanup or saved agent settings were intentionally made. Existing data hashes compared at the main-probe boundary are unchanged. Historical QA/backups were not exhaustively rehashed. Actual native test evidence is retained rather than overwritten to hide a failure. Any unperformed/unavailable check remains NOT_EVALUATED; a successful lower-layer test does not override a failed public workflow.
''')
# Source identity index makes findings reviewable even if a line link moves later.
paths=list((R/'src').rglob('*.py'))+[R/'pyproject.toml',R/'.vscode/mcp.json',R/'mcp_config.json']
(E/'source-hashes.json').write_text(json.dumps({str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths if f.exists()},indent=2),encoding='utf-8')
print('Built 15 independent reports; test summary:',None if t is None else t['totals'])
