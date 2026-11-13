# v3 migration risks and staged plan

Audit date: 12 November 2026. No implementation or legacy retirement is approved by
this document. The supplied migration prompt requires approval of major architecture
decisions before implementation.

| Risk | Severity | Required mitigation / acceptance evidence |
|---|---|---|
| Data or immutable evidence mutation | Critical | No migration-time rewrites; test using isolated copies, hash manifests and backend integrity APIs; never use live evidence as a writable test fixture |
| Engineering logic embedded in Qt | High | Extract existing operations into shared Python services with equivalence tests before exposing them to React; never port calculations to TS/Rust |
| Multiple project/workspace/design identities | High | Carry explicit project/revision/workspace/design IDs and source record type; preserve older independent workspaces; no forced conversion |
| Historical requests mistaken for successful runs | High | Separate SimulationRun NOT_SUPPORTED availability records from actual JobRecord execution and engineering evaluation |
| Synchronous controller execution vs IntegrationService jobs | High | Monitor persisted jobs first; only advertise progress/cancellation where genuinely supported; do not automatically rerun after crash |
| Sidecar startup mutates runtime state | High | Core initialization creates directories and IntegrationService performs job recovery. Establish one owned desktop backend and test concurrent CLI/MCP use; never call startup read-only |
| Stale design cache across agent/UI processes | High | Define refresh semantics for JSON design records; prove agent-created/updated records appear without stale cache or overwrite |
| Schema/document drift | High | Preserve schema version behavior; fresh/older database fixtures and migration regression tests before any separate schema fix |
| Synthetic traces or hidden derived transforms | High | Result views require recorded data/provenance; defer benchmark traces and implicit FFT resampling; display source units and exact samples |
| Static readiness / unproven library claims | High | MCP liveness and tool qualification need actual checks; seed data is not manufacturer verification; unavailable checks stay NOT_EVALUATED |
| Native launch / webview bridge abuse | High | Narrow command allowlist, validated IDs/relative paths, core launchers, no arbitrary shell or frontend filesystem/database access |
| Frozen Python packaging incomplete | High | Existing setup script relies on Python; qualify packaged runtime and resources on a clean Windows machine, offline WebView2 policy and uninstall data preservation |
| Dependencies undeclared or incompatible | Medium | NumPy and other runtime imports need audit; verify frontend peer/engine ranges before installing, pin lockfiles, scan licenses/vulnerabilities |
| Existing dirty working tree | High | Preserve current edits; capture starting status; avoid resets, archive replacement and unrelated refactors |
| Hidden UI removed prematurely | High | Action-level parity and regression gate before retirement; this audit authorizes no deletions |

## Recommended implementation sequence and effort

Indicative engineering effort for one experienced implementer; not a delivery promise.
Ranges include implementation and local verification, but exclude engineering model
development, purchasing certificates and external clean-machine scheduling.

| Stage | Deliverable and gate | Estimate |
|---|---|---|
| 0/1 | Source audit, feature families, risks, architecture decision review; focused baseline completed, full baseline still needed | 2–4 days total |
| 2 | Narrow Python stdio adapter, Tauri lifecycle, React shell, themes, error/reconnection states and contract tests | 4–7 days |
| 3 | Real dashboard/project list/detail, external-agent refresh parity | 3–5 days |
| 4 | Specification/design/calculation display, files and component provenance; required Python extraction | 4–8 days |
| 5 | Persisted simulation/job views, logs, waveform contract, Plotly sample display/export/comparison | 5–9 days |
| 6 | Revision comparison, effective validation, reports/evidence, action parity | 4–7 days |
| 7 | Native launch/dialogs, frozen Python bundle, WebView2 and Windows installer | 4–8 days |
| 8 | Full regressions, performance measurements, clean-machine/offline qualification and acceptance report | 4–7 days |
| 9 | Only verified obsolete Qt retirement; otherwise retain both entry points | 1–3 days |

Estimated total: 31–58 engineering days, with refinement after the first packaged
sidecar proof. Deferred interactive workflow/editor features may extend parity work.
No performance improvements or package-size targets are claimed without measurements.

## Decisions requiring approval

1. Approve additive Tauri 2 + React/TypeScript frontend alongside unchanged Qt entry
   points, with the navigation and scope mapping in `02_UI_FEATURE_INVENTORY.md`.
2. Approve private JSON-lines request/response IPC over a Tauri-owned Python process,
   initially narrow read operations, instead of adding an HTTP server.
3. Approve a frozen Python sidecar packaging proof before relying on release builds;
   development may use an explicitly configured interpreter, never an implicit PATH lookup.
4. Confirm deferred interactive engineering/editor features remain in Qt/CLI/native
   tools until their parity disposition is accepted. Legacy retirement needs a later gate.

Rust/MSVC/WebView2 readiness, package compatibility and clean-machine testing are
dependencies to verify, not reasons to label this audit a v3 release.
