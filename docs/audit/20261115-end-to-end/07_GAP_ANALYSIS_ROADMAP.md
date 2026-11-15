# Report 7 — Gap Analysis and Implementation Roadmap

**Assessment date:** 15 November 2026, Asia/Calcutta. **Revision:** AUDIT-1. **Scope:** generic framework, evaluation only. No product development or manufacturing authorization.

Read this with [method and evidence](README.md). “Verified” means the explicitly described software behavior was inspected or executed; it never means an entire hardware design is qualified. Missing engineering acceptance stays **NOT_EVALUATED / Not Verified**. Synthetic audit files and mocked test files are not hardware evidence.

**Verification:** the initial selected regression run was 153 passed / 4 failed (157 total). Two contextual failures passed targeted retests; the live-product-dependent test was not rerun against live data, and a waveform expectation/window mismatch remains unresolved. See E06 for precise results and the final supplementary regression. Native buck ERC had zero violations; routed DRC had zero errors/unconnected items and 16 warnings. This is a narrow idealized reference, not a qualified product envelope.

**Changing-workspace limit:** source and live artifacts changed concurrently outside this audit. Findings are tied to captured source hashes and execution times; [closing-source addendum](09_CLOSING_SOURCE_ADDENDUM.md) documents new enclosure/TIM code and integrity-banner findings. Those additions are not silently treated as fully verified.

This is a recommendation register, not an implementation plan already executed. Prioritize trustworthy complete manufacturing documentation and preservation before adding product/topology breadth. No replacement of the existing stack is justified by the evidence. Complexity is relative engineering effort, not a promised schedule or cost.

## G01 — Release completeness (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Release completeness |
| Current implementation | Initial scan omitted STEP too; final cutoff adds STEP/SVG/mechanical files but still omits simulations, requirements and registered external artifacts |
| Expected capability | Complete revision-linked manifest and mandatory deliverables |
| Technical reason | Eligibility heuristics and workspace-only scope |
| Manufacturing impact | Manufacturer/teams receive missing design evidence |
| Priority | Critical |
| Recommended solution | Replace candidate scan with explicit artifact requirements and external path collection; show missing files |
| Available existing/free tools | Existing Python pathlib/zipfile/hashlib and core artifact registry |
| Integration requirements | Shared core collector exposed consistently to UI/CLI/MCP |
| Complexity | High |
| Dependencies | Agreed file taxonomy and artifact linkage |
| Verification method | Negative missing-file and external-snapshot fixtures; receiving-tool reopen |
| Acceptance criteria | All mandatory items collected or explicitly blocked; no incomplete package ready claim |

## G02 — Release integrity (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Release integrity |
| Current implementation | Corrupted ZIP still READY; digest trusted; sidecar excluded |
| Expected capability | Revalidated archive/contents and self-contained manifest |
| Technical reason | Existence-based get_release_package; no freshness/content validation |
| Manufacturing impact | Unusable or stale package can be delivered |
| Priority | Critical |
| Recommended solution | Rehash/reopen/check manifest and source revision; unique atomic packages and extraction verification |
| Available existing/free tools | Python zipfile/hashlib, SQLite receipts |
| Integration requirements | Core packaging and retrieval schemas |
| Complexity | Medium |
| Dependencies | G01 and source identities |
| Verification method | Corrupt, delete, mutate, stale and path traversal tests |
| Acceptance criteria | Any missing/corrupt/stale bytes fail closed with NOT_EVALUATED engineering status |

## G03 — New analysis immutability (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | New analysis immutability |
| Current implementation | Archived WCCA and packaging write successfully; getters auto-run/write |
| Expected capability | All frozen revisions/raw evidence immutable |
| Technical reason | New wrappers bypass common draft guard and reuse fixed output paths |
| Manufacturing impact | Baseline/evidence can change after review |
| Priority | Critical |
| Recommended solution | Apply existing revision guard; store append-only derived evidence outside baseline; make getters read-only |
| Available existing/free tools | Existing core guards and unique artifact store |
| Integration requirements | Service wrappers plus desktop/agent parity |
| Complexity | Medium |
| Dependencies | Existing lifecycle semantics |
| Verification method | Hash archived trees before/after all public methods including get |
| Acceptance criteria | No frozen-byte change; unavailable cached analysis remains unavailable |

## G04 — Thermal evidence (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Thermal evidence |
| Current implementation | Empty PCB PASS and standards flags; hardcoded part losses/Rth and refs |
| Expected capability | Sourced component/material/boundary-condition thermal assessment |
| Technical reason | Fixed Q1/T1/D1/RSNUB/DSNUB/RSENSE assumptions, no qualified field solver |
| Manufacturing impact | False margin/compliance and unsafe cooling decisions |
| Priority | Critical |
| Recommended solution | Require actual loss/material inputs; remove unsupported compliance; label approximate estimates; fail empty inputs |
| Available existing/free tools | Existing explicit thermal calculators; optional FEMM heat-flow model after qualification |
| Integration requirements | Shared core geometry extraction, versioned thermal inputs |
| Complexity | High |
| Dependencies | Exact BOM/loss budget/stackup and measured benchmark |
| Verification method | Empty/renamed refdes/device-change and analytical/physical benchmark |
| Acceptance criteria | No PASS/compliance without complete valid inputs and reviewed applicability |

## G05 — Tolerance/worst case (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Tolerance/worst case |
| Current implementation | Fixed divider/tolerances, 2% limits, corner PASS, fixed Pareto; production label |
| Expected capability | Actual topology/BOM-based tolerance/corner analysis |
| Technical reason | Analytical toy model disconnected from circuit/part data |
| Manufacturing impact | Unsupported yield/stress/production confidence |
| Priority | Critical |
| Recommended solution | Keep analytical scope explicit; require real limits and tolerances; run actual model sweeps; derive sensitivities/verdicts |
| Available existing/free tools | Existing LTspice batch; optional ngspice; NumPy statistics |
| Integration requirements | Revision-linked sweep service and evidence bundle |
| Complexity | High |
| Dependencies | Models, explicit limits, reproducible seeds and all raw trials |
| Verification method | Deliberately failing corner, changed tolerances/topology, golden sweep comparison |
| Acceptance criteria | No hardcoded PASS/production claim; every verdict reproducible from exact input/deck/output |

## G06 — Laboratory documents (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Laboratory documents |
| Current implementation | Empty-spec TypeError; default HV/circuit/hi-pot/probe/gate values |
| Expected capability | Requirement-specific safe draft and explicit missing fields |
| Technical reason | Formatting None plus hardcoded test template unrelated to future circuit |
| Manufacturing impact | Misleading or inapplicable test instructions |
| Priority | Critical |
| Recommended solution | Require sourced test limits/topology/testpoints; block unsupplied criteria; qualified reviewer authors safe plan |
| Available existing/free tools | Existing document templates/core evidence; no hardware-control integration |
| Integration requirements | Typed laboratory-plan request and human review record |
| Complexity | High |
| Dependencies | Risk assessment and qualified test author |
| Verification method | Empty and nonisolated/isolated/topology-specific documents independently reviewed |
| Acceptance criteria | No invented criteria; missing input NOT_EVALUATED; no plan represents energization authorization |

## G07 — Sourcing (High)

| Field | Assessment |
| --- | --- |
| Affected stage | Sourcing |
| Current implementation | Unknown MPN gets ACTIVE/distributor/lead time/LOW risk; disclaimer calls analytical estimate |
| Expected capability | Sourced part-specific quote/stock/lifecycle with dates and unknown handling |
| Technical reason | Category heuristics synthesize procurement fields |
| Manufacturing impact | Incorrect procurement/assembly planning |
| Priority | High |
| Recommended solution | Separate cost assumptions from verified procurement metadata; import real supplier quotes with provenance |
| Available existing/free tools | Existing CSV/JSON import and Python arithmetic; no new service required |
| Integration requirements | Typed quote/lifecycle source schema and BOM export |
| Complexity | Medium |
| Dependencies | Exact MPNs and authorized source data |
| Verification method | Unknown/obsolete/unquoted part tests and signed quote reconciliation |
| Acceptance criteria | Unsourced stock/lifecycle/lead-time null/NOT_EVALUATED; no fake distributor fact |

## G08 — PCB manufacturing outputs (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | PCB manufacturing outputs |
| Current implementation | Supplemental drill/CPL/D356/stats export errors swallowed; existing ZIP reuse |
| Expected capability | Explicit complete output validation tied to board revision |
| Technical reason | Broad exception pass and weak package reuse checks |
| Manufacturing impact | Missing holes/placement or stale manufacturing data |
| Priority | Critical |
| Recommended solution | Return per-export errors and block incomplete sets; verify source hash/layer/drill/BOM identities |
| Available existing/free tools | Existing KiCad CLI/export parsers |
| Integration requirements | Core export orchestrator and receipt |
| Complexity | Medium |
| Dependencies | Actual layer/material requirements |
| Verification method | Force drill/CPL failure, stale ZIP, multiple board ambiguity |
| Acceptance criteria | No success for missing required drill/layers/CPL; deterministic selected board and revision |

## G09 — Assembly (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Assembly |
| Current implementation | CPL/BOM outputs independent; full process/orientation docs incomplete |
| Expected capability | BOM-CPL-PCB reconciliation and assembly-ready instructions |
| Technical reason | No complete cross-file semantic gate or generic authored instructions |
| Manufacturing impact | Wrong/missing parts, rotation and process ambiguity |
| Priority | Critical |
| Recommended solution | Add reconciliation/explicit DNP and approved MPN checks; require reviewed assembly/polarity/stencil/process docs |
| Available existing/free tools | KiCad CPL/BOM/native board tools; CSV parsing |
| Integration requirements | Core validation plus manual manufacturing templates |
| Complexity | High |
| Dependencies | G08 and approved parts/process data |
| Verification method | Refdes/qty/DNP/side/rotation mismatch fixtures and assembler review |
| Acceptance criteria | All fitted parts match; receiving SMT team confirms sufficient data |

## G10 — Mechanical/mounting (High)

| Field | Assessment |
| --- | --- |
| Affected stage | Mechanical/mounting |
| Current implementation | STEP/preview/envelope only; no qualified enclosure/installation package |
| Expected capability | Complete toleranced enclosure/mounting/cooling/wiring documentation |
| Technical reason | Visualization/interchange does not check fits and interfaces |
| Manufacturing impact | Build cannot be mounted/connected reliably |
| Priority | High |
| Recommended solution | Use existing FreeCAD/manual mechanical workflow; retain full models/drawings/connector/fastener/tolerance review |
| Available existing/free tools | Installed FreeCAD + KiCad STEP (retain stack) |
| Integration requirements | Artifact registration and review criteria for mechanical files |
| Complexity | High |
| Dependencies | Complete part models, chassis requirements, G04 |
| Verification method | Native model reopen, collisions/tolerance review and prototype fit |
| Acceptance criteria | Complete documented interfaces and accepted fit; no visualization-only verification |

## G11 — Safety rules consistency (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Safety rules consistency |
| Current implementation | Legacy helper fails closed; Copper numerical IEC-named distances and heatmap true flags |
| Expected capability | Single explicit applicability boundary and qualified rules only |
| Technical reason | Independent heuristic rules bypass fail-closed context |
| Manufacturing impact | Unjustified insulation/compliance decisions |
| Priority | Critical |
| Recommended solution | Centralize safety context; label geometry heuristics; require qualified standard/edition and physical evidence |
| Available existing/free tools | Existing SafetyAssessment/Pydantic contracts |
| Integration requirements | Copper/core consumers and reporting schema |
| Complexity | High |
| Dependencies | Qualified safety owner and authorized standards references |
| Verification method | Cross-entry-point missing-context/invalid/unsupported cases |
| Acceptance criteria | No compliance, required safety distance or approval inferred without qualified basis |

## G12 — Model/design coverage (High)

| Field | Assessment |
| --- | --- |
| Affected stage | Model/design coverage |
| Current implementation | Buck narrow reference; other topologies experimental; ideal gate sources |
| Expected capability | Topology-specific tested full circuitry across operating envelope |
| Technical reason | Candidate/IR/native output generation is broader than qualified behavior |
| Manufacturing impact | A generated circuit may be incomplete or inapplicable |
| Priority | High |
| Recommended solution | Qualify existing topologies incrementally with exact controller/device models and independent golden graphs/sweeps |
| Available existing/free tools | Current KiCad/Copper/LTspice; optional ngspice |
| Integration requirements | Versioned topology qualification records |
| Complexity | High |
| Dependencies | Parts/models and explicit use envelope |
| Verification method | Native graph/ERC/DRC plus line/load/temp/fault/AC matrix |
| Acceptance criteria | Only proven envelopes labeled verified; others remain experimental/NOT_EVALUATED |

## G13 — Tool truthfulness (High)

| Field | Assessment |
| --- | --- |
| Affected stage | Tool truthfulness |
| Current implementation | Discovery READY for missing execute operations; research license/source conflicts |
| Expected capability | Separate found/available/executed/qualified and authoritative provenance |
| Technical reason | Base verification is file existence; metadata overclaims |
| Manufacturing impact | Operators assume unavailable engineering automation |
| Priority | High |
| Recommended solution | Report capability implementation separately; reconcile catalog/adapter source/license/version |
| Available existing/free tools | Existing tool descriptors/catalog and tests |
| Integration requirements | Shared tool registry and UI inventory |
| Complexity | Medium |
| Dependencies | Verified upstream references/release terms |
| Verification method | FreeCAD/Qucs-S unsupported-operation and research unknown-data tests |
| Acceptance criteria | No operational claim for inherited NotImplementedError or unqualified dataset |

## G14 — Physical/quality release (Critical)

| Field | Assessment |
| --- | --- |
| Affected stage | Physical/quality release |
| Current implementation | Measurement intake and local decisions exist; full actual lab/build evidence not independently established |
| Expected capability | Accountable prototype/physical/quality/compliance review |
| Technical reason | External manufacturing/instruments/people cannot be replaced by software |
| Manufacturing impact | No demonstrated production qualification |
| Priority | Critical |
| Recommended solution | Require actual prototype and qualified requirement-specific external evidence; preserve attribution limits |
| Available existing/free tools | Existing scope CSV/evidence intake; external calibrated lab |
| Integration requirements | Requirements-to-evidence traceability and manual external approval records |
| Complexity | High |
| Dependencies | G06, actual hardware, qualified lab and all discipline docs |
| Verification method | Independent raw evidence/calibration/DUT review and actual receiving-team audit |
| Acceptance criteria | All required physical checks accepted; no automatic manufacturing approval |

## G15 — Packaging/install/architecture (Medium)

| Field | Assessment |
| --- | --- |
| Affected stage | Packaging/install/architecture |
| Current implementation | NumPy imported but not declared; core thermal imports desktop; live-profile tests |
| Expected capability | Repeatable install, one-way core dependencies and isolated tests |
| Technical reason | Dependency/config/test assumptions drift |
| Manufacturing impact | Workstation success not reproducible across teams |
| Priority | Medium |
| Recommended solution | Declare proven runtime requirements in future phase; move geometry extraction to core; isolate live-profile tests |
| Available existing/free tools | Existing venv/pytest/TypeScript; no stack replacement |
| Integration requirements | Package manifests, core geometry, fixture policy |
| Complexity | Medium |
| Dependencies | Current tests and environment inventory |
| Verification method | Clean offline/controlled install and full isolated acceptance suite |
| Acceptance criteria | No undeclared required dependency; no live workspace writes by tests; UI/CLI share core |

## G16 — Integrity presentation (High)

| Field | Assessment |
| --- | --- |
| Affected stage | Integrity presentation |
| Current implementation | RecordFormView renders integrity verified unless snapshot_integrity is exactly false; current UI includes signature wording |
| Expected capability | Unknown integrity explicitly unevaluated; digest distinguished from signature/identity |
| Technical reason | Boolean false-only branch collapses absent/null into verified |
| Manufacturing impact | Receiving engineers can mistake unavailable checks or local attribution for assurance |
| Priority | High |
| Recommended solution | Use explicit true/false/unknown states from effective core result; label checksum and declared identity precisely |
| Available existing/free tools | Existing React/TypeScript and core integrity contracts |
| Integration requirements | All integrity badges, review cards and report views |
| Complexity | Medium |
| Dependencies | Shared canonical integrity and manual review metadata |
| Verification method | Render missing/null/true/false and unauthenticated review cases |
| Acceptance criteria | Unknown remains NOT_EVALUATED; no cryptographic identity/signature claim from plain hashes |

## G17 — Windows export and test portability (Medium)

| Field | Assessment |
| --- | --- |
| Affected stage | Windows export and test portability |
| Current implementation | Long audit path caused BOM DOCX FileNotFoundError; shorter-root rerun passed; tests also assume cwd/live UUID |
| Expected capability | Supported path handling and isolated repeatable regression |
| Technical reason | Deep UUID output paths plus Windows path boundary and repository-specific fixture assumptions |
| Manufacturing impact | Exports/tests can fail for receiving workspaces or mask missing evidence |
| Priority | Medium |
| Recommended solution | Define and validate supported output-path lengths; use isolated fixtures and explicit repository paths in future maintenance |
| Available existing/free tools | Existing pathlib/pytest/docx and source manifests |
| Integration requirements | BOM/export error reporting and test fixture policy |
| Complexity | Medium |
| Dependencies | Documented Windows support and representative paths |
| Verification method | Near-limit path and clean empty-profile test cases |
| Acceptance criteria | Supported paths export or return clear errors without partial success; tests need no live product IDs |


## Prioritized sequence

1. **Truthful evidence and preservation:** G03–G06, G11. Keep analysis/draft generation separate from engineering verdicts, eliminate unsourced acceptance and preserve frozen baselines.
2. **Complete manufacturing delivery:** G01–G02, G08–G09, G07. Explicit mandatory file registry, intact revision-linked exports, semantic BOM/CPL reconciliation, real procurement provenance and fail-closed package validation.
3. **Mechanical and laboratory completion:** G10, G14. Qualified human-authored mechanical/installation/test content and external prototype/physical evidence; explicit controlled human release process.
4. **Coverage and maintainability:** G12–G13, G15. Expand topology qualification and adapter parity after complete deliverable gates exist; clean runtime/test dependency boundaries.

Existing native path corrections should be retained: desktop CAD mutators now require draft revisions, export no longer hardcodes force=True, dossier handles empty FEMM/nested ERC, and waveform code has weighted-average fixes. Current tests verify only their covered cases; new analysis/packaging paths require the separate gaps above.

## Tool recommendations and sources

Retain KiCad/Copper for native schematic/board/CAM exchange; KiCad publishes separate PCB, Gerber Viewer and CLI manuals in its [official documentation](https://docs.kicad.org/). Use the installed FreeCAD path for manual enclosure/mechanical authoring after exact-version qualification; the [official FreeCAD site](https://www.freecad.org/) returned HTTP 403 during this audit, so current external feature/version details were not verified. Keep [FEMM](https://www.femm.info/doku/doku.php?id=start) for appropriately qualified magnetic/heat-flow modeling; its official site identifies magnetics, electrostatics, heat flow and current flow. Existing optional [ngspice](https://ngspice.sourceforge.io/) can support a separately qualified SPICE backend; its official site describes file/netlist simulation and external schematic interfaces. No new tools were installed and no unsupported compliance libraries are recommended.

Actual safety/compliance rules require an applicable authorized standards basis and qualified reviewer. Open-source geometry or simulator tools do not establish certified rules or physical qualification.

**Final cutoff correction (14:40:18 Asia/Calcutta):** concurrent source now includes standalone STEP/SVG/mechanical files in packaging and adds enclosure RPC/client routes. The initial STEP omission is historical. The final probe still excludes simulations/requirements and reports READY for incomplete/corrupt archives. See [closing addendum](09_CLOSING_SOURCE_ADDENDUM.md) and [cutoff evidence](evidence/final-cutoff-probe.json). Changes after this cutoff are outside this audit.
