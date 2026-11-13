# v3.1 feature retention and removal matrix

Audit disposition, 12 November 2026. No listed code has been removed. The finalized
agent-first responsibility split changes the v3 proposal: presentation of engineering
records moves to React; engineering initiation stays in core/MCP/CLI/native tools.
Legacy Qt remains usable until replacement and agent coverage are verified.

| Existing feature/source | Core/backend disposition | Target Studio disposition | Retirement prerequisite |
|---|---|---|---|
| Project catalog/search (`window.py`) | Retain existing project IDs/services | Migrate viewing/search/filter/open | Existing and agent-created projects visible automatically |
| Project metadata creation/editor | Retain; complete metadata API | Remove duplicate authoring forms after parity | CLI/MCP create/update, revision guards and idempotency verified |
| Specification/revision JSON editor | Retain specification validation/save and revisions | Read-only Specifications and comparison | Agent writes appear with exact units/hash; frozen revisions unchanged |
| ProductDesignWizardDialog | Extract existing orchestration/direct filesystem writes to core where supported | Retire guided engineering wizard after agent parity | No calculation rewrite; correct parameter/provenance persistence and agent generation coverage |
| EnterpriseDashboardPanel | Reuse inventory/record services, remove presentation calculations from new UI | Real project/lifecycle/job summaries | No fabricated counts, no static readiness |
| ProductEngineeringOverviewPanel | Retain domain records; replace heuristics for new lifecycle with explicit gate service | Project Overview/Lifecycle/Designs/Calculations/Validation | New nine-stage enrollment and legacy history both understandable |
| Existing 12/15-stage assessments | Preserve historical behavior/contracts during transition | Label legacy assessment separately; no automatic conversion | Approved record mapping; new stages never inherit old PASS without criteria/evidence |
| Stage review/PASS forms | Preserve historical entries; no new agent approval capability | Review requests/status; human decision only if backend authorization exists | Authorization/integrity reviewed; caller-supplied name is insufficient |
| SimulationCenterPanel run form/worker | Reuse existing solver services; expose jobs through common facade | Read-only history/detail/logs/metrics/waveforms | Agent simulation execution/status/failure paths verified |
| JobsPanel and SimulationLabPanel | Retain supported job submit/cancel/retry/log/evidence services | Consolidate monitoring into Simulation Center | Capability/ownership-aware cancellation and unavailable state coverage |
| Legacy SimulationPanel availability archive | Preserve historical NOT_SUPPORTED requests | Display separately from executed solver jobs | No availability request rendered as a completed simulation |
| WaveformViewerWidget | Keep supported Python parsing/metrics; extract UI-only calculations if retained | Plotly samples, traces, pan/zoom, units, inspection, compatible comparison/export | Real file fixtures, units and no hidden transform; large-data behavior verified |
| Synthetic waveform examples/implicit FFT resampling | Do not use as evidence; preserve current Qt while parity work runs | Exclude from engineering result views | Explicit later analysis contract needed for derived transforms/tutorials |
| Component/material/core browser | Retain seeded/data services with provenance caveats | Read-only searchable details and source references | No invented vendor specs, stock or verification claims |
| SwitchLossDB/MagNet research browser | Retain datasets and provenance | Consolidate under Component Library | Research/illustrative vs manufacturer/measured provenance clear |
| SemiconductorTradeoffComparatorDialog | Preserve calculation methods; expose supported core operations/results | Retire calculation execution UI; display resulting records | Inputs/assumptions/formulas persisted, equivalent outputs verified |
| MagneticCoreLossComparatorDialog/DowellWindingLossDialog | Same supported Python methods, no new design engine | Retire interactive engineering execution dialogs after parity | Agent capability discovery and result records tested |
| Transformer/DC-DC/semiconductor workspace panels | Retain supported existing calculations/native files | Consolidate read-only results under project | No loss of artifacts/record history |
| EngineeringDesignStudioPanel iteration/synthesis | Retain design/candidate/revision/iteration services | Designs/artifacts viewer; no generation or built-in AI iteration workflow | External-agent support and freshness/conflict handling verified |
| EngineeringWorkspaceManagerPanel netlist editor | Preserve native files/core operations | Remove custom engineering editor after parity | Open in native/editor paths verified |
| workflow_canvas visual builder | Retain backend graph executor for compatibility | Do not migrate canvas/authoring | Callers inventoried; underlying calculations/adapters remain usable |
| PCBWorkspacePanel import/notes/check controls | Reuse core PCB snapshot/integrity service and expose via MCP | Read-only Engineering Files/Validation; safe native opens | Agent import/check/notes and immutable revision behavior verified |
| Lifecycle-panel alternate ERC/DRC/Gerber paths | Consolidate shared services; preserve existing evidence | Inspect/open/export supported records, no manufacturing approval | Native checks and evidence integrity tests; no evidence deletion |
| IEC/derating audit buttons in Qt | Existing calculation functions retained; authority/provenance needs review | Display attributed calculations, never unproven compliance badge | Rule/source/scope validation and no approval inference |
| RevisionDiffDialog | Retain underlying product/design history | Revision timeline and comparison | Old/new specification/calculation/BOM sources and identifiers preserved |
| ValidationDialog/ValidationPanel | Retain append-only checks and effective summaries | View results/evidence/open issues; no duplicate manual stage updates | Agent evidence/criterion submissions validated centrally |
| Measurement service / CSV traces | Retain real measurement records/import/comparison | Prototype/physical evidence display | MCP/CLI entry points and actual lab evidence semantics verified |
| ReportsEvidencePanel and dossier actions | Preserve generators; extract UI-only orchestration | List/open/export reports/evidence | Agent generation/listing and frozen report source checks |
| Engineering tools panels/settings | Retain discovery/configuration/diagnostics/launch methods | Display configured/detected/tested separately; safe opens and diagnostics refresh | No executable-exists => operational claim |
| MCP ACTIVE/22-tool text | Replace unsupported presentation claim, preserve connection configuration | Observed integration diagnostics or NOT_EVALUATED | Live health/schema counts, no static liveness assertion |
| Command palette/search | Retain useful navigation/native open actions | Navigation/search, no hidden authoring commands | Keyboard/accessibility tests and truthful action availability |
| Notification center | Retain actual notices/errors | Show real backend events/errors, no fabricated activity | External updates and recovery covered |
| Engineering guide/prompts/onboarding | Reuse useful text; separate agent prompts from UI | Help/setup links and connection instructions | Generic stage prompt library matches actual callable contracts |
| Themes/assets/preferences | Reuse brand assets, preserve preferences where feasible | Semantic dark/light tokens, density/sidebar/window preferences | Visual/keyboard/contrast verification |
| Hidden compatibility panels/duplicate launcher paths | Retain until usage/tests established | No additional React routes | Action-level parity, caller inventory and regression gate |
| Built-in AI provider/copilot | Already retired at core contract boundary | Do not add | External agents remain independent |
| Hardware control/manufacturing approval/CI/CD/deployment | Out of authorized scope | No controls | Not part of v3.1 implementation |

Removal means a later verified UI retirement, not deleting services, persisted
history, raw files or frozen baselines. UI simplification must not precede the agent
operations needed to replace a working manual action. Existing destructive commands
must not be invoked as cleanup or included in generic lifecycle prompts.
