# v3 UI feature inventory

Source inventory, 12 November 2026. Classification applies to observed feature families,
including hidden/legacy UI. Removal requires reachability review and acceptance evidence.
Migrate means preserve supported behavior behind the core; it does not certify that
the present implementation meets engineering or security requirements.

| Existing UI/source | Features | Disposition | Target / condition |
|---|---|---|---|
| window.py | Seven primary routes; project context; catalog; search; preferences; themes | Migrate | React application shell, project routes and local appearance preferences |
| v17_panels.EnterpriseDashboardPanel | Tool/resource inventory, filters, summary and navigation | Consolidate | Dashboard persisted-record summary; discovery inventory in Engineering Tools |
| window.ProductDialog and editor | Product creation, metadata, specifications, workspace creation, revision selection/save/rename/new revision | Migrate | Engineering Projects; service validates edits and immutable revisions |
| product_lifecycle_panel | Stage overview, review/approvals, calculations, simulations, PCB, BOM, mechanical, benchmarks, gates, evidence | Consolidate | Project detail tabs; backend effective states only; no manufacturing approval |
| pcb_panel | File import/open, notes, ERC/DRC worker, check history and evidence | Migrate | Engineering Files / Validation; same PCBWorkspaceService |
| simulation_center_panel | Project/solver selection, execution worker, logs, metrics, waveforms | Migrate | Simulation Center monitoring first; execution stays on existing supported core paths |
| waveform_viewer | Native raw import, multiple traces, zoom/pan, trace metrics, cursors, export | Migrate | Plotly view of backend-supplied samples/units/provenance; computed metrics stay Python |
| waveform_viewer | Synthetic benchmarks, implicit FFT resampling | Defer | Do not include in engineering result views; any future tutorial/derived analysis must be explicit and isolated |
| component_library_panel | Semiconductor and magnetic records, filters, research provenance, loss estimator | Consolidate | Read-only component/dataset browser; calculation display via shared Python service |
| integration_panels.ToolCenter; panels.ToolPanel | Discovery/configuration/verification | Consolidate | Engineering Tools; show detected/configured/tested independently |
| integration_panels.JobsPanel | Job tables, status, logs, evidence and actions | Consolidate | Simulation list/detail; retain backend status and supported cancellation/retry |
| integration_panels.DatasetPanel | Dataset inventory and provenance | Migrate | Component Library provenance views |
| reports_evidence_panel; panels.ReportsPanel/ValidationPanel/ValidationDialog | Generate/list/open reports, append manual numerical validation, evidence audit | Consolidate | Reports & Evidence and project Validation, preserving exact historical/effective status distinction |
| settings_panel | Theme, tool paths, connection instructions, MCP status text | Migrate | Settings; replace static readiness claims with observed state or NOT_EVALUATED |
| command_palette; notification_center | Navigation/actions, notices and search | Migrate | Functional keyboard commands and backend/UI errors; no invented activity feed |
| engineering_guide_dialog; first_run_wizard | Tool guidance, external-agent prompts/connections, review checklist, onboarding | Consolidate | Help/onboarding and Settings; no embedded AI provider |
| product_wizard_dialog | Guided identity/envelope/components/sizing and native artifact scaffolding | Retain in backend only | Extract reusable operations behind core before any React exposure; retain Qt until parity; no new design development |
| tradeoff_comparator_dialog | Device comparison and frequency/loss/thermal sweeps | Retain in backend only | Existing calculations must become shared Python operations; React can later display persisted/explicitly requested results |
| magnetic_comparator_dialog; dowell_visualizer_dialog | Core comparison, winding/core loss analysis | Retain in backend only | Same extraction requirement; interactive analysis outside initial monitoring scope |
| revision_diff_dialog | Specification, sizing, BOM, lifecycle comparison | Migrate | Read-only revision comparison with both record identifiers and source values |
| design_studio_panel | Requirement entry, synthesis, candidates, iteration, artifact views | Consolidate | Existing design/iteration execution remains CLI/MCP/core; migrate design records and artifact inspection |
| workspace_panels | Transformer, converter and semiconductor workspaces | Consolidate | Existing calculations/results under project tabs; unavailable work remains NOT_EVALUATED |
| v17_panels.EngineeringWorkspaceManagerPanel | Model/netlist editing and execution console | Defer | Retain Qt for parity review; native editors remain the authoring path |
| v17_panels.SimulationLabPanel | Generic tool/operation execution, console, plots | Consolidate | Supported recorded jobs in Simulation Center; no generic shell bridge |
| v17_panels.ResearchCenterPanel/ResultsReportsPanel | Dataset exploration and reports | Consolidate | Component Library / Reports & Evidence |
| panels.SimulationPanel | Availability-request archive and older simulation lab | Consolidate | Preserve NOT_SUPPORTED historical requests separately from actual solver jobs |
| workflow_canvas/* | Canvas nodes/edges, properties, templates, execution/logs/waveforms | Defer | Keep existing backend/Qt workflow behavior; no new React workflow editor in initial migration |
| theme.py; resources/* | QSS themes and brand icons | Migrate | Retain image assets; translate visual tokens, not Qt widget code |
| window.py compatibility attributes, hidden labels/panels and duplicate launcher | Test compatibility / possible obsolete paths | Remove after verification | No deletion authorized by this audit; establish usage and parity first |

Backend-only classification concerns ownership of engineering execution, not deletion
of existing user access. Deferred Qt features remain reachable through their existing
entry points where supported. A full parity matrix must enumerate individual actions,
enabled states and test fixtures before any legacy retirement.
