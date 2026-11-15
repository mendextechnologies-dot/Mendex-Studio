# Report 5 — Team-Wise File Sharing and Handover Guide

**Assessment date:** 15 November 2026, Asia/Calcutta. **Revision:** AUDIT-1. **Scope:** generic framework, evaluation only. No product development or manufacturing authorization.

Read this with [method and evidence](README.md). “Verified” means the explicitly described software behavior was inspected or executed; it never means an entire hardware design is qualified. Missing engineering acceptance stays **NOT_EVALUATED / Not Verified**. Synthetic audit files and mocked test files are not hardware evidence.

**Verification:** the initial selected regression run was 153 passed / 4 failed (157 total). Two contextual failures passed targeted retests; the live-product-dependent test was not rerun against live data, and a waveform expectation/window mismatch remains unresolved. See E06 for precise results and the final supplementary regression. Native buck ERC had zero violations; routed DRC had zero errors/unconnected items and 16 warnings. This is a narrow idealized reference, not a qualified product envelope.

**Changing-workspace limit:** source and live artifacts changed concurrently outside this audit. Findings are tied to captured source hashes and execution times; [closing-source addendum](09_CLOSING_SOURCE_ADDENDUM.md) documents new enclosure/TIM code and integrity-banner findings. Those additions are not silently treated as fully verified.

File IDs resolve exactly to Report 4 and its CSV; the source inventory records actual paths. “Approved” below means a real organizational engineering decision, never the presence of a local READY label. No files were sent to anyone by this audit. Automatic external team sharing is **Not Verified**; delivery is manual controlled transfer through the organization’s existing repository/document share or secure manufacturer portal.

## Electrical Engineering

| Field | Required information |
| --- | --- |
| Team | Electrical Engineering |
| Deliverables | A01–A09, B01–B11, C12–C13, F01–F02 |
| Format | md/json/csv/pdf/kicad_sch/kicad_pro/asc/net/raw/log |
| Purpose | Validate architecture, circuitry, ratings and models |
| Source | Core exports, .mendex/ga, native workspace, indexed reports |
| Procedure | Export specification/calculation/evidence records; copy exact native inputs and solver dependencies |
| Validation | Traceable requirements, component ratings, native graph equivalence, solver acceptance and integrity |
| Approval | Electrical lead + independent design reviewer |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Review limits/control/protection; close electrical/model gaps |

## PCB Design

| Field | Required information |
| --- | --- |
| Team | PCB Design |
| Deliverables | A01–A03, A06–A09, C04–C07, E01–E02, E06 |
| Format | kicad_sch/kicad_pro/net/json/pdf/csv/md |
| Purpose | Implement approved circuitry and layout constraints |
| Source | Reviewed schematic/project, part library, mechanical interface |
| Procedure | Export native project/netlist/footprints and explicit board/stackup/clearance constraints |
| Validation | Symbol-to-footprint pin map, exact MPN, netlist revision and mechanical datums |
| Approval | Electrical + PCB + mechanical leads |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Place/route with power-loop, thermal, return path and isolation review |

## PCB Fabrication Manufacturer

| Field | Required information |
| --- | --- |
| Team | PCB Fabrication Manufacturer |
| Deliverables | C01–C15, relevant E01–E02, F12 and F15 |
| Format | gbr/gtl/gbl/gm1/drl/d356/gbrjob/json/pdf/md/zip |
| Purpose | Fabricate bare board to exact accepted material/process/dimensions |
| Source | KiCad fabrication exports plus manually reviewed fab docs |
| Procedure | CAD preview Export Gerbers; independently add fabrication drawing/stackup/notes; validate manifest |
| Validation | Independent CAM opens all layers/drills; same origin/units; plated holes/slots; DFM acceptance and no unexplained DRC issues |
| Approval | PCB/manufacturing lead + QA; fabricator confirms feasibility |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Return DFM queries/approved deviations before manufacturing |

## PCB Assembly / SMT

| Field | Required information |
| --- | --- |
| Team | PCB Assembly / SMT |
| Deliverables | D01–D10, C04–C07, E03, F09, F12 |
| Format | csv/json/pdf/md/gbr/step/zip |
| Purpose | Populate correct components with unambiguous orientation/process |
| Source | BOM export, CPL/native PCB, assembly/process docs |
| Procedure | Download candidate turnkey ZIP; add approved drawings/polarity/solder/special process/alternates documents manually |
| Validation | BOM-CPL-fitted-PCB exact refdes/DNP/MPN/quantity agreement; origin/side/rotation; stencil/profile and orientation review |
| Approval | Electrical + SMT manufacturing + procurement + QA |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Confirm data completeness, approved sources and first-article inspection plan |

## Mechanical Engineering

| Field | Required information |
| --- | --- |
| Team | Mechanical Engineering |
| Deliverables | E01–E10, C03–C04, B06–B07 |
| Format | step/stp/FCStd/pdf/csv/md/json |
| Purpose | Design fit, enclosure, mounting, connector and cooling interfaces |
| Source | Native PCB/STEP/model coverage and actual loss/thermal budget |
| Procedure | CAD preview Export STEP; provide exact board and supplied mechanical constraints/models |
| Validation | Model completeness, datums, collision/tolerance/access/thermal review; no preview-as-acceptance |
| Approval | Mechanical + electrical leads |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Complete enclosure, hardware, heat sink, dimensions and tolerance stack |

## Hardware Integration

| Field | Required information |
| --- | --- |
| Team | Hardware Integration |
| Deliverables | D04–D09, E01–E10, F03–F09 |
| Format | pdf/md/csv/step/json |
| Purpose | Assemble/mount/wire safely and consistently |
| Source | Reviewed mechanical and assembly package, wiring/pinout, test prerequisites |
| Procedure | Manually copy controlled installation/wiring/mounting/torque and integration checklist; add external build deviations |
| Validation | Mating connectors/pinouts/earthing, hardware torque, accessibility and separately authorized testing prerequisites |
| Approval | Mechanical + electrical + integration lead + safety/QA where applicable |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Verify installation and integration; record deviations and serial/build identity |

## Testing and Quality Assurance

| Field | Required information |
| --- | --- |
| Team | Testing and Quality Assurance |
| Deliverables | A01, A07–A08, B03–B11, C12–C13, F01–F11, F15 |
| Format | md/csv/json/html/pdf/raw/log/png |
| Purpose | Execute requirement-specific verification and assess evidence |
| Source | Effective lifecycle/validation records plus lab/test documents and raw measurement files |
| Procedure | Export evidence with frozen inputs, exact hashes, instrument/setup/operator/calibration metadata; independently revise generic laboratory plan |
| Validation | Every critical requirement has a method/limit, calibrated instrumentation and actual results; uncertainty/context/freshness checked |
| Approval | Test lead + independent QA + qualified safety/compliance reviewer |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Approve safe plan externally, execute actual tests and resolve failed/missing evidence |

## Project Management and Documentation

| Field | Required information |
| --- | --- |
| Team | Project Management and Documentation |
| Deliverables | F01, F09–F15 plus complete controlled discipline bundles |
| Format | json/md/csv/pdf/zip |
| Purpose | Control revision, release status, risks, approvals and team receipts |
| Source | All engineering sources, reports, lifecycle/review histories and complete inventory |
| Procedure | Use release card for candidate ZIP/sidecar then apply manual completeness/revision/integrity audit and team transmittals |
| Validation | No missing critical documents, mismatched baselines, stale/corrupt evidence or unqualified readiness claims |
| Approval | All accountable discipline leads + QA/document control; final authority external to this audit |
| Delivery | Read-only, access-controlled team folder/archive plus manifest/checksums, revision/date, transmittal and recipient acknowledgment; secure manufacturer portal when applicable |
| Next action | Maintain release/risk register, route actual approvals, distribute controlled copies and collect acknowledgments |


## Exact implemented UI/API export paths

Source verification: `desktop/src/pages/ProjectDetail.tsx`, `RevisionEngineeringPanel.tsx`, `CADPreviewCanvas.tsx`, `GerberLayerInspector.tsx`, `ReleaseHandoverCard.tsx`, `LaboratoryTestPlanCard.tsx`, `desktop/src/api/client.ts`, and Python desktop dispatch. These are source-confirmed controls/API paths, not a fresh interactive browser acceptance test.

| Location | Action / operation | Output and limitation |
| --- | --- | --- |
| Project detail → Reports section | Compile Complete Dossier (PDF); core generate_report / desktop generate_report | Indexed draft HTML/JSON; PDF conditional on renderer. Preserve all warnings and source snapshots. |
| Revision engineering → BOM & Documents / BOM controls | Generate / Rebuild BOM; Open PDF BOM; Open Word BOM | Requires supplied bom/bom.json; unique draft exports, conditional PDF. Does not resolve supplier approval. |
| Revision CAD preview / PCB toolbar | Export Gerbers; desktop export_gerbers | pcb/gerbers output, ZIP/data URI and receipt. Export may route mutable draft board; inspect request and subsequent board hash. |
| CAD preview → Gerber Layer Inspector | Layer inspection and package download; inspect_gerber_layers / download_gerbers | data:application/zip;base64 payload; package_type gerber or turnkey. Existing archive reuse is not a freshness/completeness check. |
| CAD preview / PCB toolbar | Export STEP; export_cad_step | STEP path/hash/size; optional open_native launches a viewer. Rendering alone does not prove fit. |
| Project detail → Reports → Release handover card | Build package; reveal folder; get_release_package / build_release_package / reveal_release_package | Workspace release_package/<code>_<revision>_Complete_Manufacturing_Release.zip and sidecar release_manifest.json. ZIP presence can yield READY without valid engineering data. Copy the sidecar separately. |
| Project detail → laboratory plan card | Generate/view plan; generate_laboratory_test_plan / get_laboratory_test_plan | JSON/Markdown/HTML draft; missing-spec crash and fixed circuitry/limits need qualified revision before use. |
| Core service | export_specification, engineering_records report/evidence APIs, open_project_file/reveal_project_file | Use actual returned revision-relative or registered paths; do not guess UUID paths. No external delivery implied. |

New features do not automatically have full CLI/MCP parity. Consult current CLI help and MCP tool schema; the regression suite verifies named exposed operations, not every desktop-only feature. Python core entry points generate_release_package/get_release_package/reveal_release_package exist. Do not expose manufacturing approvals as agent tools.

## Step-by-step controlled delivery

1. Identify the product UUID, exact core revision UUID/label and workspace using the project detail/core service response. List registered design artifacts, report paths, protected PCB check runs and measurement evidence as well as workspace files. Read operations such as current thermal/WCCA getters may generate outputs; do not use them on frozen baselines for inspection.
2. Freeze the delivery selection in a separate staging directory. Copy files; never edit raw evidence or an archived revision. Retain exact model/library dependencies, relative references and licenses. If a required file is absent, put it in the missing-deliverables register and mark its check NOT_EVALUATED.
3. Export with the corresponding control/API above only for an authorized editable draft. Preserve output paths/receipts and source board hash before/after routing or export. Use new controlled revisions for corrections; do not silently substitute a different board, older BOM or newer document.
4. Open native schematics/boards in the matching KiCad version, and simulate only a deliberate isolated input copy when revalidation is authorized. Independently inspect every fabrication layer/drill set in CAM, match outline/units/origin/plating, and compare BOM/CPL/refdes/DNP/MPNs against the same PCB revision. Review all failure reports, not just command return codes.
5. Review assembly, polarity, soldering, special handling, mounting, pinout, fastener, cooling and installation instructions for actual parts/topology. Review laboratory documents for actual requirements/hazards and authorized limits. The generic generated protocol is not an executable authorization.
6. Organize the reviewed copies into the 14 folders in Report 6. Generate a machine-readable manifest with each relative path, bytes, SHA-256, file/design revisions, generating tool/version, owner and actual approval/evaluation status. Keep an explicit exceptions/missing-files list.
7. Validate every staged file against manifest hashes; open documents and native/CAM files using appropriate receiving tools; ensure links/models resolve from the staged package. Validate archive extraction/CRC and recompute hashes after extraction. An archive checksum proves bytes only. The current get_release_package response does not perform these checks.
8. Obtain actual discipline/QA/document-control approval through the organization’s authorized human process. State “engineering review candidate — manufacturing release NOT_EVALUATED” until that process and required physical evidence are complete. Never invent signers or approvals.
9. Create a ZIP per team or a shared full release with team index; send through an existing access-controlled document share or secure supplier portal manually. Include manifest, transmittal, revision, superseded-package notice, outstanding risks and recipient-specific instructions. Do not send only the current packager ZIP: it still excludes important simulation and other engineering inputs (STEP inclusion was added at the final cutoff).
10. Ask each receiving team to verify the archive hash and acknowledge revision/data sufficiency; retain DFM/assembly questions, deviations, acknowledgments and delivery log. Any design-impacting response reopens change control and invalidates affected acceptance evidence.

**Final cutoff correction (14:40:18 Asia/Calcutta):** concurrent source now includes standalone STEP/SVG/mechanical files in packaging and adds enclosure RPC/client routes. The initial STEP omission is historical. The final probe still excludes simulations/requirements and reports READY for incomplete/corrupt archives. See [closing addendum](09_CLOSING_SOURCE_ADDENDUM.md) and [cutoff evidence](evidence/final-cutoff-probe.json). Changes after this cutoff are outside this audit.
