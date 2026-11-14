# Mendex engineering gaps and next steps

Audit-only assessment, 14 November 2026. See [readiness report](MENDEX_POWER_ELECTRONICS_END_TO_END_READINESS.md). No production implementation was performed during this audit. Estimates are planning ranges for experienced software/EDA engineers with power-electronics reviewers; they exclude purchasing/licensing and external laboratory/certification schedules.

Final preservation limitation: six source files changed during the audit, and baseline live file `engineering_designs/3b906923-74bb-488c-9855-248732c60e8d.json` was missing at final comparison. Exact before/after hashes are in `evidence/20261114-readiness/preservation.json`. The audit author did not edit production code or restore other writers' changes; attribution of the missing file is not established. Earlier native outputs do not certify later source changes. G20 must first establish a stable snapshot and investigate the missing file, then rerun affected checks.

## Priority order and first milestone

The first milestone is **one trustworthy, revision-linked 12 V to 5 V reference workflow**, using the current engines. It is complete only when the same graph survives IR -> native schematics -> simulation -> populated/routed board -> checked draft export, with truthful reports, preserved history and explicit human review. It is not a commercial design, hardware validation or manufacturing approval.

Final isolated regression result: **383 passed, one failed, exit 1**. The failing test is `tests/core/test_desktop_revision_isolation.py::test_desktop_designs_require_explicit_project_and_revision_link`: a project view included an additional design without the required explicit project/revision link. Track this confirmed defect under G01/G20 and add it to the first task's acceptance criteria. See `evidence/20261114-readiness/safe-pytest.xml` and its log; excluded and aborted runs are documented in the readiness report.

The next three specific development tasks are:

1. **G01/G03:** centralize draft/context/integrity guards for every native CAD mutation and export; remove the hidden DRC-force path and prove archived adapters are never called.
2. **G02/G14:** repair the buck graph mapping into KiCad and ASC, authoritative footprints and layout constraints. Compare native extracted netlists with IR and require zero critical ERC/DRC issues in the fixture. Fix the VOUT-triggered slot heuristic.
3. **G04/G07:** correct evidence/result interpretation in reports and waveforms. Nested ERC failures, empty FEMM JSON, stale records and truncated/nonuniform traces must not create positive engineering claims.

Do not begin these tasks as part of this audit. Existing manufacturing exports may remain draft evidence; no automatic release authority, hardware control, new CAD/simulation engine, CI/CD or deployment should be added.

## Implementation sequence and dependencies

- **Milestone 0 - Preserve and bound:** capture a reproducible checkout/environment, source hashes and test roots; resolve G20 test isolation and define baseline exit-code checks alongside G01 guards.
- **Milestone 1 - Truthful reference chain:** G01, G02, G03, G04, G07 and G14. First prove native equivalence and negative-evidence handling; then generate the checked draft reference package.
- **Milestone 2 - Qualified engineering inputs:** G05/G06/G08/G09/G10. Explicit physical parts, dimensioned coefficients, requirements/test links and applicability-qualified calculations; unsupported contexts remain NOT_EVALUATED.
- **Milestone 3 - Wider engineering coverage:** G11/G12/G13/G15/G16/G17/G23. Add independently qualified magnetics/control/protection/mechanical and external physical-test procedures one topology at a time.
- **Milestone 4 - Repeatable delivery:** G19/G21/G22/G24. Finish shared agent/UI parity, long-job behavior, installed desktop packaging and interactive acceptance. G18 review-policy clarity applies throughout.

Indicative minimum reference milestone: 15-30 engineer-days with overlapping software/EDA work and senior electrical review. A bounded engineering-ready platform is more plausibly an 8-16 week small-team effort after dependencies are available; physical qualification and certification are separate. Do not sum all gap ranges as a fixed-price estimate: several share the same underlying work, while per-topology and lab efforts repeat.

## Detailed gap register

### G01 - P0 - Native CAD mutations lack a shared revision-freeze gate

- **Root cause:** Desktop auto_route_pcb, schematic edits, slot/plane operations and render-on-read reach adapters directly.
- **Evidence:** boundary-results.json: archived adapter called; non-mutating spy kept bytes unchanged.
- **Affected modules:** src/mendex_core/desktop/service.py; integrations/adapters/copper_kicad_adapter.py
- **Engineering impact:** Archived design/evidence can be edited; historical review context can silently diverge.
- **Recommended fix:** Move mutation authorization into the shared service: draft-only, expected revision/spec/artifact hash, copy-on-write and recorded operation receipts. Make previews read-only caches outside baselines.
- **Estimated effort:** 3-5 engineer-days
- **Acceptance test:** For every mutator, archived/conflicting requests fail before adapter invocation; hash every baseline before/after; exercise retries and concurrent revision changes.
- **Dependencies:** None

### G02 - P0 - Generated electrical representations are not equivalent

- **Root cause:** Symbol-pin coordinates, labels and native ASC wiring do not preserve the simulated graph.
- **Evidence:** erc.json: 20 errors and 18 warnings; native-asc-netlisting.json: NC_01..NC_08 and no PWM drive. Direct SPICE buck still runs.
- **Affected modules:** design/generators/kicad_generator.py; ltspice_generator.py; design/ir.py
- **Engineering impact:** Simulation success does not validate the editable circuit delivered to the engineer.
- **Recommended fix:** Correct one canonical buck graph through KiCad and ASC; independently netlist both and compare connections/pin roles to IR. Resolve all ERC errors and dangling/off-grid wiring.
- **Estimated effort:** 5-10 engineer-days
- **Acceptance test:** Native KiCad and LTspice netlists match the selected IR; positive/negative fixtures detect omitted gate/load paths; the delivered schematic reproduces the reference simulation.
- **Dependencies:** G01

### G03 - P0 - Manufacturing export bypasses verification

- **Root cause:** Desktop export_gerbers passes force=True, which bypasses the lower-level DRC/routing gate.
- **Evidence:** desktop/service.py export_gerbers and lifecycle/kicad_service.py force branch; raw native exports succeeded despite two board errors.
- **Affected modules:** desktop/service.py; lifecycle/kicad_service.py
- **Engineering impact:** A downloadable fabrication ZIP can be mistaken for a reviewed package.
- **Recommended fix:** Remove hidden force bypass; distinguish unqualified draft exports from fabrication candidates and carry explicit ERC/DRC/integrity blockers. Do not implement manufacturing approval.
- **Estimated effort:** 2-3 engineer-days
- **Acceptance test:** Known failing/unrouted boards cannot be presented as fabrication-ready; explicit draft export is labeled and preserves its issue reports and revision digest.
- **Dependencies:** G01,G02

### G04 - P1 - Engineering dossiers manufacture positive verdicts

- **Root cause:** ERC reader ignores nested sheets; FEMM renderer fills missing evidence and uses a fixed PASS margin.
- **Evidence:** real-erc-dossier-card.html says Clean with native 20 errors; empty-femm-dossier-card.html says PASS (99.3% Margin) from {}.
- **Affected modules:** src/mendex_core/dossier_generator.py
- **Engineering impact:** Readers receive false engineering assurance even when the underlying raw evidence is absent or failing.
- **Recommended fix:** Use canonical strict parsers and effective evidence status; reject incomplete records; compute displayed margins from qualified inputs; never infer passing from missing keys.
- **Estimated effort:** 3-5 engineer-days
- **Acceptance test:** Feed nested ERC errors, malformed JSON, missing excitation, stale hashes and an explicit failure; UI/HTML/PDF/snapshot all retain FAIL or NOT_EVALUATED, never PASS.
- **Dependencies:** None

### G05 - P1 - BOM parts and simulation models are not qualified selections

- **Root cause:** Generated IR and the small sourced reference library do not establish exact model, footprint, temperature and SOA compatibility.
- **Evidence:** Fixture BOM includes generated/unqualified rows; library lookup is NOT_EVALUATED; 6 footprint-mismatch warnings.
- **Affected modules:** components; design/synthesis.py; bom_generator.py; Copper bridge
- **Engineering impact:** Parts can be numerically plausible yet physically unsuitable or connected to the wrong package pads.
- **Recommended fix:** Require exact MPN/order code, datasheet revision, conditions, model license/version/hash and reviewed pin/footprint mapping; retain unresolved items explicitly.
- **Estimated effort:** 4-8 engineer-days plus component engineering review
- **Acceptance test:** A real representative buck BOM resolves every populated footprint/model/pin map; missing model or rating blocks the affected verification claim.
- **Dependencies:** G02

### G06 - P1 - Specification coverage is narrower than the complete engineering brief

- **Root cause:** Typed Specification lacks first-class efficiency, ripple/regulation, mechanical, cooling, EMI, reliability, cost and manufacturing fields; generic requirement text can hold them but not automatically evaluate them.
- **Evidence:** models.Specification; engineering_records.models.Requirement; fixture persisted two measurable requirements only.
- **Affected modules:** models.py; engineering_records; engineering_reviews
- **Engineering impact:** Declared requirements may remain disconnected from measurable tests or authoritative constraints.
- **Recommended fix:** Define the minimum first-release requirement schema and explicit requirement-to-test links; retain sources, units, ranges, conflicts and accepted exclusions.
- **Estimated effort:** 4-7 engineer-days
- **Acceptance test:** Completeness and conflict tests cover all chosen fixture requirements; changed requirements invalidate affected calculations/reviews; every requirement has an explicit verification method and status.
- **Dependencies:** None

### G07 - P1 - Waveform windows and numerical summaries are inconsistent

- **Root cause:** Runner previews only the first 200 points; averages are sample-weighted on adaptive time; RPC ignores start/limit.
- **Evidence:** independent-waveform-check.json: 25,774 points / 5 ms versus 30 us preview; 4.8448 V sample mean versus 4.85705 V time-weighted; RPC limit 5 returns 1,031.
- **Affected modules:** design/ltspice_runner.py; desktop/service.py waveform; parsers/ltspice_parser.py
- **Engineering impact:** Startup previews can be mistaken for steady state; integration accuracy and API bounds are not reliable.
- **Recommended fix:** Use a declared settling/measurement window, time-weighted integration or named native measurements, full-domain decimation and enforced pagination/trace validation.
- **Estimated effort:** 3-5 engineer-days
- **Acceptance test:** Independent nonuniform-time vectors and real raw files agree within declared tolerance; zero tolerance remains zero; requested limits and windows are honored and reflected in reports.
- **Dependencies:** None

### G08 - P1 - Magnetic loss coefficient units differ across calculators

- **Root cause:** One path interprets frequency in Hz, another uses kHz and an extra 1000 factor; coefficient metadata is not dimensioned.
- **Evidence:** engineering-counterexamples.json; intelligence/calculations.py and integrations/calculations/power_losses.py.
- **Affected modules:** intelligence/calculations.py; integrations/calculations; material contracts
- **Engineering impact:** Identically named coefficient inputs can imply orders-of-magnitude different losses.
- **Recommended fix:** Declare coefficient units, fit frequency/flux/temperature/waveform domain and source data. Normalize only with explicit conversions and independent reference cases.
- **Estimated effort:** 3-5 engineer-days
- **Acceptance test:** All exposed paths reproduce the same qualified material loss benchmark and reject coefficients outside their declared units/domain.
- **Dependencies:** G05

### G09 - P1 - Thermal and trace-width labels overstate qualification

- **Root cause:** New models use defaults and empirical cooling factors; the trace equation is labeled IPC-2152 although the exposed power-law coefficients are associated with IPC-2221 references.
- **Evidence:** thermal_sizing.py; TI SNVA766; controller requires explicit values on its route, but lower-level defaults still exist.
- **Affected modules:** integrations/calculations/thermal_sizing.py; controller; thermal RPC/UI
- **Engineering impact:** A formula evaluation or PASS_DERATED label can be mistaken for qualified thermal/current capability.
- **Recommended fix:** Review units, thermal network and temperature-limit policy, remove unsupported normative labels, and validate against independently documented component and board examples.
- **Estimated effort:** 4-7 engineer-days
- **Acceptance test:** Analytical resistor-network checks plus independent device/heatsink and board-stackup cases; unknown airflow/contact/stackup remains unqualified.
- **Dependencies:** G05

### G10 - P1 - Duplicate Copper insulation rules undermine fail-closed core behavior

- **Root cause:** Copper creepage helper returns a numerical rule while ignoring material_group and accepting negative voltage by abs().
- **Evidence:** boundary-results.json: I/II/IIIa/IIIb all return 5 mm at 230 V; negative voltage accepted.
- **Affected modules:** integrations/adapters/copper_kicad_adapter.py; desktop plane/slot methods
- **Engineering impact:** Users can obtain confident distances through a second path even though the core reports no qualified ruleset.
- **Recommended fix:** Use one typed applicability service; refuse unsupported contexts, preserve NOT_EVALUATED and separate slot geometry operations from safety approval.
- **Estimated effort:** 2-4 engineer-days plus standards specialist review
- **Acceptance test:** Every UI/CLI/MCP/native adapter path shares identical context and unsupported-case behavior; no material/default/slot shortcut grants compliance.
- **Dependencies:** G01

### G11 - P1 - FEMM excitation and magnetic benchmarks remain incomplete

- **Root cause:** Generator and IR expose geometry/current fields, but defaults, material names, boundary and domain fidelity need independent qualification.
- **Evidence:** femm_generator.py; excited FEMM acceptance skip in prior runs; this nonisolated buck has no magnetic FEMM model.
- **Affected modules:** design/generators/femm_generator.py; femm_runner.py; magnetics calculators
- **Engineering impact:** A successful mesh/solver or near-zero B field is not validated transformer behavior.
- **Recommended fix:** Use a bounded excited reference with known ampere-turns, material, mesh convergence and analytical/integral comparison; document 2D/harmonic limits.
- **Estimated effort:** 5-10 engineer-days plus magnetics review
- **Acceptance test:** Nonzero excitation gives reproducible physically meaningful B/L; unexcited/missing-material/invalid-boundary cases cannot imply magnetic acceptance.
- **Dependencies:** G08,G05

### G12 - P1 - Converter control and protection coverage is incomplete

- **Root cause:** Native solver capabilities do not equal implemented feedback compensation, loop/FRA, startup/fault, short-circuit, inrush and thermal-protection workflows.
- **Evidence:** No qualified complete loop/protection workflow was demonstrated; fixture used fixed switching assumptions.
- **Affected modules:** design/synthesis.py; generators; engineering workflows
- **Engineering impact:** Nominal steady-state output does not establish line/load regulation or safe fault response.
- **Recommended fix:** Bound the first supported converter family and add existing-native-tool procedures/models for control, startup, sweeps and faults, with explicit external review.
- **Estimated effort:** 8-15 engineer-days per first qualified family
- **Acceptance test:** Deliver stable gain/phase evidence, line/load/startup/fault cases and requirements links; unsupported protections remain explicit.
- **Dependencies:** G02,G05,G07

### G13 - P1 - Topology names exceed demonstrated topology readiness

- **Root cause:** Buck, boost, flyback, push-pull, LLC and phase-shifted full-bridge builders exist; no comprehensive per-topology benchmark establishes correctness.
- **Evidence:** synthesis.py and Copper bridge tests; only buck executed end-to-end here.
- **Affected modules:** design/synthesis.py; topology generators; candidate selection
- **Engineering impact:** Heuristic efficiency/scores and fixed design margins may be interpreted as validated topology selection.
- **Recommended fix:** Publish an applicability matrix and qualify topology-specific equations, circuit graphs and native simulations incrementally. Keep other topologies unavailable or explicitly experimental.
- **Estimated effort:** 4-10 engineer-days per additional topology
- **Acceptance test:** Each supported topology has explicit domain, independent numeric and graph tests, real-model simulation and known negative cases.
- **Dependencies:** G02,G05,G12

### G14 - P1 - Power PCB generation/routing is not an engineering layout verification

- **Root cause:** Generic pad shapes differ from referenced footprints; slot insertion is triggered by a VOUT net name, even in a nonisolated buck. Routing success is true when any track is added.
- **Evidence:** drc-before/after.json; board-3d.png; boundary-results.json; kicad_pcb_generator.py has_hv condition.
- **Affected modules:** kicad_pcb_generator.py; Copper adapter; desktop route
- **Engineering impact:** Real native copper can still violate board edges, footprints, power-loop, thermal and isolation constraints.
- **Recommended fix:** Use authoritative library footprints; explicit board/layout constraints and topology domains; require zero unresolved connections and configured critical DRC errors before a ready claim.
- **Estimated effort:** 5-10 engineer-days plus layout review
- **Acceptance test:** Fixture has zero critical DRC/footprint mismatches, correct net graph and acceptable reviewed loops/returns; nonisolated fixture gets no invented HV slot.
- **Dependencies:** G01,G02,G05,G09

### G15 - P2 - 3D rendering is not mechanical verification

- **Root cause:** PNG and STEP are generated, but no enclosure/heatsink/connector/height/clearance collision acceptance was demonstrated.
- **Evidence:** board-3d.png and board.step generated; displayed model coverage is incomplete.
- **Affected modules:** Copper render; CAD preview; FreeCAD adapter
- **Engineering impact:** A visually plausible assembly does not prove mechanical fit or accessibility.
- **Recommended fix:** Track model coverage and validate explicit envelope/collision/height constraints with native CAD review.
- **Estimated effort:** 3-6 engineer-days plus mechanical review
- **Acceptance test:** Known-collision and known-clearance fixtures are detected; every missing 3D model is listed rather than omitted from acceptance.
- **Dependencies:** G05,G14

### G16 - P1 - EMI/EMC evidence chain needs external verification

- **Root cause:** No conducted/radiated measurement or qualified converter-specific EMI filter validation was executed.
- **Evidence:** Native fixture is idealized; workflow/document templates are not lab results.
- **Affected modules:** engineering-workflows; measurement/reporting modules
- **Engineering impact:** No credible EMC or final thermal qualification follows from nominal simulated waveforms.
- **Recommended fix:** Prepare revision-linked external test methods, limits, instrumentation and result ingestion with honest evidence classes.
- **Estimated effort:** 3-5 engineer-days software plus external lab schedule
- **Acceptance test:** Real independently supplied measurement files are linked and reviewed; absent tests never become simulated/measured equivalents.
- **Dependencies:** G06,G12

### G17 - P1 - Measurement recording does not establish physical-test authenticity

- **Root cause:** MeasurementRecord stores instruments/calibration/operator and values, but the application cannot establish their real-world origin.
- **Evidence:** measurements/models.py; manual prototype plan fixture was not executed.
- **Affected modules:** measurements; engineering_records; prototype stage
- **Engineering impact:** Software can store a measurement-shaped record without proving physical hardware passed.
- **Recommended fix:** Define an external human procedure/evidence policy and requirement links; retain raw originals, failures, revisions and explicit simulated/calculated/measured distinctions.
- **Estimated effort:** 3-5 engineer-days plus physical engineering work
- **Acceptance test:** No physical stage completes from simulation-only records; genuine measured evidence must meet the declared method and be independently reviewed.
- **Dependencies:** G06,G16

### G18 - P1 - Manual review is attribution, not a human-only security boundary

- **Root cause:** Names/comments and digests are intentionally accepted without identity/qualification proof; same-user software can call local APIs.
- **Evidence:** engineering_reviews.service manual mode; identity_authenticated=false; no approval tool in observed 62-tool MCP inventory.
- **Affected modules:** engineering_reviews; desktop transport; review policy
- **Engineering impact:** The platform cannot guarantee an AI agent cannot mimic a human reviewer name.
- **Recommended fix:** Preserve the requested lightweight workflow, document its trust boundary, exclude review decisions from agent transports, and require actual external human review/release authority.
- **Estimated effort:** 2-4 engineer-days policy/UI/integration tests
- **Acceptance test:** Automated interfaces cannot present declared attribution as authenticated or laboratory-qualified approval; safety decisions remain visibly human-supplied and context-bound.
- **Dependencies:** G04,G17

### G19 - P2 - Copper and new calculations lack full canonical agent parity

- **Root cause:** Copper runs via embedded registry and desktop methods; observed Mendex MCP has no Copper routing/render/export tools. New thermal controller calculations and the four-kind persisted record schema differ.
- **Evidence:** tool-names.json: 62 tools, no Copper-specific tools; CalculationWrite literal four versus seven controller calculators.
- **Affected modules:** mcp/server.py; cli.py; desktop/service.py; engineering_records/models.py
- **Engineering impact:** Agent and UI flows can have different validation, traceability and capabilities.
- **Recommended fix:** Expose narrowly typed operations through the existing shared core/registry and align calculator capability records, without creating a second engine.
- **Estimated effort:** 4-7 engineer-days
- **Acceptance test:** Same disposable operation via UI/core/CLI/MCP yields equivalent validation, revision links and evidence metadata.
- **Dependencies:** G01,G09

### G20 - P0 - Release-grade regression and test isolation are not established

- **Root cause:** Some new tests open the live root and hardcoded project; full Qt run ended in an access violation; broad audit tests include a failure and slow PDF paths.
- **Evidence:** test_emc100_lifecycle_progression.py; inherited priority1 regression log; audit safe-pytest artifacts.
- **Affected modules:** tests; report/PDF subprocess boundaries; Qt lifetime management
- **Engineering impact:** Tests can depend on workstation/project state and cannot currently establish a repeatable release baseline.
- **Recommended fix:** Move all live-coupled tests to explicit opt-in checks, use disposable roots and controlled process lifetimes, and preserve clean exit-code checks.
- **Estimated effort:** 3-6 engineer-days
- **Acceptance test:** Fresh bounded isolated regression exits zero twice; no live root access or background GUI creation; process teardown and native timeouts are tested.
- **Dependencies:** G04

### G21 - P0 - Standalone desktop and clean-install acceptance are blocked

- **Root cause:** Web assets build but native Cargo check cannot run with the configured toolchain; packaged Python/backend/dependency installation has not been demonstrated.
- **Evidence:** cargo.log; frontend build; Tauri config and Rust backend resolution.
- **Affected modules:** desktop/src-tauri; packaging scripts; Python environment
- **Engineering impact:** Source development mode is not a portable installed engineering application.
- **Recommended fix:** Repair existing native build/packaging and perform manual clean-Windows install, backend discovery, recovery/uninstall acceptance; do not add CI/CD or deployments.
- **Estimated effort:** 5-8 engineer-days
- **Acceptance test:** Installed app runs without checkout/venv assumptions and preserves data through restart/recovery; no missing-runtime silent fallback.
- **Dependencies:** G20

### G22 - P2 - Rendered interactive workflow acceptance is unavailable

- **Root cause:** The supported browser connection exposes no sessions; source/server-render or native CLI output does not prove UI behavior.
- **Evidence:** Browser bootstrap iab unavailable and browser list empty; no screenshots of the live end-to-end workflow were asserted.
- **Affected modules:** React/Tauri; polling and waveform/CAD views
- **Engineering impact:** Navigation, latency, errors and file-opening interactions remain unverified.
- **Recommended fix:** Run the documented open-Studio acceptance on a supported session using the disposable fixture and independently inspect every displayed status/result.
- **Estimated effort:** 2-4 engineer-days
- **Acceptance test:** Screens show the actual revision, failures and waveform domain; stale/out-of-order/error states and native opens are observed.
- **Dependencies:** G02,G04,G07,G21

### G23 - P1 - Lifecycle completion is process tracking, not comprehensive discipline acceptance

- **Root cause:** Default post-initialization stages principally require a named validation record plus review; documentation depends on verification, not physical-testing completion.
- **Evidence:** engineering-lifecycle.json; fixture starts calculations while requirements is in progress; no engineering stages were approved.
- **Affected modules:** engineering_lifecycle; engineering_records; release documentation
- **Engineering impact:** A recorded stage/document milestone cannot be equated with an electrically validated manufactured product.
- **Recommended fix:** Define measurable acceptance bundles for the bounded first-release workflow and distinguish draft documentation from an externally authorized final release package.
- **Estimated effort:** 4-7 engineer-days plus discipline reviewers
- **Acceptance test:** Negative evidence/missing physical tests cannot produce a final-ready claim; declared exemptions stay explicit with downstream restrictions.
- **Dependencies:** G04,G06,G17,G18

### G24 - P2 - Long native operations bypass consistent job/retry handling

- **Root cause:** Direct desktop CAD/routing/render/report calls can exceed UI transport deadlines and lack the same operation receipts as core record writes.
- **Evidence:** Direct adapter calls and automatic PDF/render-on-read source; routing and report steps execute synchronously.
- **Affected modules:** desktop/service.py; vite bridge; job service; dossier generator
- **Engineering impact:** A timeout can look like failure after a mutation already happened, encouraging duplicate actions.
- **Recommended fix:** Reuse the existing job service for bounded native operations, retain idempotency/context receipts and show uncertain outcomes without automatic mutation replay.
- **Estimated effort:** 3-5 engineer-days
- **Acceptance test:** Timeout/retry/cancellation scenarios preserve one identifiable outcome and every prior snapshot; UI observes completion without guessing.
- **Dependencies:** G01,G19

## First-milestone acceptance checklist

- Explicit sourced requirements, topology and fixture assumptions; no hidden ratings or limits.
- Native schematic netlists are equivalent to IR and to the circuit actually simulated.
- Zero critical ERC/DRC violations and no unintended unrouted nets or footprint/pad mismatches.
- Sourced representative parts/models, declared limitations and same-revision manifests.
- Independent waveform/quantity checks, proper time windows and reproducible negative tests.
- Every draft export lists its revision, inputs, hashes, software versions and unresolved checks.
- Old snapshots survive every edit/regeneration; archived requests are rejected before mutation.
- Human review is context-bound and visibly declared; physical testing remains NOT_EVALUATED until genuine measured evidence exists.
- A clean test exit and an observed native/interactive run, not only a successful frontend build.

No development starts under this audit-only instruction. The handover should include these reports, the captured raw evidence and the dirty-working-tree manifest rather than an assertion of manufacturing readiness.
