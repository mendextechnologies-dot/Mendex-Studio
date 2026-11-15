# Report 4 — Manufacturing File Inventory

**Assessment date:** 15 November 2026, Asia/Calcutta. **Revision:** AUDIT-1. **Scope:** generic framework, evaluation only. No product development or manufacturing authorization.

Read this with [method and evidence](README.md). “Verified” means the explicitly described software behavior was inspected or executed; it never means an entire hardware design is qualified. Missing engineering acceptance stays **NOT_EVALUATED / Not Verified**. Synthetic audit files and mocked test files are not hardware evidence.

**Verification:** the initial selected regression run was 153 passed / 4 failed (157 total). Two contextual failures passed targeted retests; the live-product-dependent test was not rerun against live data, and a waveform expectation/window mismatch remains unresolved. See E06 for precise results and the final supplementary regression. Native buck ERC had zero violations; routed DRC had zero errors/unconnected items and 16 warnings. This is a narrow idealized reference, not a qualified product envelope.

**Changing-workspace limit:** source and live artifacts changed concurrently outside this audit. Findings are tied to captured source hashes and execution times; [closing-source addendum](09_CLOSING_SOURCE_ADDENDUM.md) documents new enclosure/TIM code and integrity-banner findings. Those additions are not silently treated as fully verified.

The linked CSV contains every requested inventory field for every deliverable, including input data, generation procedure, output location, validation, mandatory/optional disposition, revision, responsible/receiving teams, export and approvals. Names below are standardized recommendations; actual names are taken from returned paths or E04. No product revision or approval has been invented.

**Availability legend:** Available = code path/native format generation exists with relevant local evidence; still conditional on valid inputs and test limitations. Partial = a draft, subset or unqualified approximation exists. Manual = complete content must be authored/obtained externally; studio may store it. External = physical activity or accountable external decision, unavailable to automatic software. None means a complete accepted product file was established.

Actual default workspace uses `StudioService.workspace_path(revision)`, normally `products/<product_uuid>/revisions/<revision_uuid>/`. Generated design snapshots may live outside it at `.mendex/ga/<uuid>/`; protected ERC/DRC evidence lives under `.mendex/pcb-checks/`; report output is indexed separately. Therefore a workspace-only scan is not a complete engineering inventory.

## A. Electrical design

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| A01 | product-requirements.md / specification.json | Product requirements specification | Core specification + manual requirements document; Sourced operating and acceptance requirements | export_specification plus reviewed authored specification; requirements/ | Partial |
| A02 | electrical-architecture.md | Electrical system architecture | Human engineer + candidate/IR context; Topology, power/ground/isolation/protection partition | Author and review architecture; attach controlled document; electrical/ | Manual |
| A03 | circuit.kicad_sch | Complete circuit schematic | KiCad/Copper generator/editor; Reviewed IR, symbols/pin maps and circuitry | Generate/import then complete native schematic; run ERC; pcb/ or registered .mendex/ga/<uuid>/kicad/ | Partial |
| A04 | circuit.kicad_pro | Native schematic project | KiCad generator/editor; Project rules, schematic and board | Export project and retain libraries/rules alongside native files; pcb/ or .mendex/ga/<uuid>/kicad/ | Available |
| A05 | sizing.json / electrical-calculations.csv | Electrical calculations | Shared calculator registry; Explicit sourced SI inputs and equation conventions | Execute calculator and export recorded input/output; calculations/ | Available |
| A06 | component-datasheets/*.pdf | Exact component datasheets | Supplier/manufacturer documents; Exact MPN and revision/source/license | Obtain authoritative supplied PDFs, record source/date/hash; component_data/ | Manual |
| A07 | design-assumptions.md | Design assumptions | Specification assumptions + engineer; Model approximations, ambient, load, derating choices | Export assumptions and review against each calculation/model; electrical/ | Partial |
| A08 | electrical-verification.json / .html / .pdf | Electrical verification report | Core/dossier report; Requirement mapping and actual effective evidence | generate_report then independent check of stated results; reports/ / registered report path | Partial |
| A09 | circuit-netlist.net / constraints.json | Layout netlist and constraints | KiCad/Copper + engineer; Reviewed schematic and footprint/current/isolation constraints | Native netlist/forward annotation; author reviewed layout constraints; pcb/ | Partial |

## B. Simulation

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| B01 | converter.asc / converter.net | LTspice editable simulation and deck | LTspice generator; Reviewed IR, exact models and stimuli | Generate, native-netlist ASC and compare connectivity to deck; .mendex/ga/<uuid>/ / simulations/ | Available |
| B02 | models/*.lib / *.sub / *.asy | Simulation model and symbol dependencies | Component supplier + LTspice; Exact model release, pin order, temperature/voltage applicability | Preserve licensed dependencies and hashes with deck; simulations/models/ | Manual |
| B03 | simulation-config.json | Solver/stimulus/configuration | Runner/job request + engineer; Analysis, solver options, windows and sweep matrix | Export exact request/settings and executable version; simulations/ | Partial |
| B04 | transient-report.json / .pdf | Transient analysis report | LTspice runner + dossier; Intact transient raw/log/deck and explicit limits | Execute transient; inspect waveforms/metrics and link source; simulations/ / reports/ | Partial |
| B05 | ac-analysis.json / bode.csv / bode.pdf | AC/loop analysis report | Analytical helper; external/native AC setup; Linearization point, injection/model and loop definition | Run qualified AC or record analytical approximation distinctly; simulations/ac/ | Partial |
| B06 | efficiency.csv / loss-budget.json | Efficiency and power-loss analysis | Shared losses + engineer/native measurements; Valid power integrals and part/core loss data | Build sourced loss budget and validate energy balance; calculations/ / simulations/ | Partial |
| B07 | thermal-analysis.json / .pdf | Thermal analysis and cooling report | Explicit calculators; PCB heatmap estimate; Sourced losses/resistances/ambient/cooling geometry | Run explicit sizing; label heatmap assumptions; review uncertainty; simulations/thermal/ | Partial |
| B08 | wcca_analysis.json / stress-corners.csv | Tolerance/stress/worst-case report | WCCA engine + engineering sweep work; Actual tolerance models and explicit acceptance bands | Current analytical run exists; replace fixed assumptions before acceptance; simulations/wcca/ | Partial |
| B09 | converter.raw / converter.log | Native waveforms and solver log | LTspice runner; Native simulation deck, models, solver | Run solver and retain original binary/text outputs and exact version; simulations/ / native output path | Available |
| B10 | waveforms/*.svg / *.png / *.csv | Waveform plots and exported samples | Dossier/waveform parser; Raw trace identity, units, windows and decimation | Export views/data; link to original raw by hash; simulations/waveforms/ | Partial |
| B11 | simulation-validation-summary.md / .json | Simulation validation summary | Engineer + effective core evidence; All analyses/model limits/requirement acceptance | Reconcile matrix, attach evidence and explicitly retain unevaluated tests; simulations/ | Partial |

## C. PCB manufacturing

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| C01 | board-F_Cu.gbr / board-B_Cu.gbr / board-InN_Cu.gbr | Gerber copper for every actual layer | KiCad CLI; Controlled PCB, actual layer map | export_gerbers; inspect every copper layer; pcb/gerbers/ | Available |
| C02 | board-PTH.drl / board-NPTH.drl | Plated/nonplated NC drill | KiCad CLI; Same PCB, drill/plating/slot definitions | export_drill and validate hole table/origin/units; pcb/gerbers/ | Available |
| C03 | board-Edge_Cuts.gbr / board-outline.pdf | PCB outline/dimensions | KiCad + reviewed fabrication drawing; Closed board outline, slots, dimensions and datum | Export outline; add toleranced drawing; pcb/gerbers/ / fabrication/ | Partial |
| C04 | stackup.json / stackup.pdf | PCB layer stackup | Engineer/fabricator; native stackup; Dielectrics, copper, impedance, total thickness | Agree stackup with fabricator and export controlled table; fabrication/ | Manual |
| C05 | copper-thickness.md | Copper thickness requirements | PCB/manufacturing engineer; Finished/base copper weight per layer and plating | Author controlled fabrication requirements; fabrication/ | Manual |
| C06 | board-material.md | Board material specifications | PCB/manufacturing engineer; Laminate grade, Tg/CTI, dielectric and safety needs | Agree qualified material and substitutions with fabricator; fabrication/ | Manual |
| C07 | surface-finish.md | Surface finish requirements | PCB/manufacturing engineer; Finish type/thickness/flatness and process needs | Specify exact finish and acceptance with manufacturer; fabrication/ | Manual |
| C08 | board-F_Mask.gbr / board-B_Mask.gbr | Solder-mask layers | KiCad CLI; Mask openings and registration rules | Export layers and verify pad clearances/alignment; pcb/gerbers/ | Available |
| C09 | board-F_Silkscreen.gbr / board-B_Silkscreen.gbr | Silkscreen layers | KiCad CLI; Refdes/polarity/legends and readable placements | Export and inspect clipping/text/orientation; pcb/gerbers/ | Available |
| C10 | fabrication-drawing.pdf | Fabrication drawing | PCB/manufacturing engineer; Board datum/holes/tolerances/material/stackup | Produce reviewed fab drawing from controlled PCB; fabrication/ | Manual |
| C11 | manufacturing-notes.md | Manufacturing notes | Manufacturing engineer; Process constraints, acceptance and deviations | Author notes; fabricator confirms interpretation; fabrication/ | Manual |
| C12 | drc.json / drc.log | Design rule checking report | KiCad PCB workspace; Actual PCB plus exact rules/version | run_check drc or native check; retain context/hash manifest; .mendex/pcb-checks/<revision>/<run>/ | Available |
| C13 | erc.json / erc.log | Electrical rule checking report | KiCad PCB workspace; Actual schematic plus rules/version | run_check erc; inspect nested errors/warnings; .mendex/pcb-checks/<revision>/<run>/ | Available |
| C14 | board.d356 | Bare-board electrical test netlist | KiCad CLI; Controlled PCB net connectivity | export_ipcd356; reconcile native nets and CAM results; pcb/gerbers/ | Available |
| C15 | board-job.gbrjob / board_stats.json | Layer job and board metadata | KiCad CLI; Actual exported layers/board | Export and compare layer/material/count metadata; pcb/gerbers/ | Partial |

## D. PCB assembly

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| D01 | bom.json / bom.csv | Complete BOM with MPNs/refdes/quantities | Explicit BOM export; Supplied complete same-revision rows | generate_bom from bom/bom.json; validate all entries; bom/ and unique bom export directory | Partial |
| D02 | approved-component-list.csv | Approved MPNs, variants and sources | Electrical + procurement; Exact manufacturer parts, ratings, datasheets, approved suppliers | Review procurement/part list; estimator is not a quote; bom/ | Manual |
| D03 | board_cpl.csv / board-pos.csv | Placement/centroid/pick-and-place | KiCad CLI; Same PCB, origin, mm/rotation/side convention | export_pos; validate every fitted refdes and bottom-side convention; pcb/gerbers/ | Available |
| D04 | assembly-top.pdf / assembly-bottom.pdf | Assembly drawings | KiCad views + manufacturing engineer; Controlled PCB with fitted/DNP/orientation notes | Create readable reviewed board views and part orientation; assembly/ | Partial |
| D05 | soldering-instructions.md | Soldering instructions | SMT manufacturing engineer; Paste alloy/profile/finish/MSL/part limits | Define approved profile/handling and process-specific instructions; assembly/ | Manual |
| D06 | polarity-orientation.pdf | Polarity/orientation instructions | Electrical + SMT engineer; Pin 1, cathodes, connector keys, electrolytic orientation | Annotate exact drawings/parts and reconcile CPL rotations; assembly/ | Manual |
| D07 | special-assembly.md | Special assembly requirements | Manufacturing engineer; Magnetics, press fits, adhesives, heat sinks, cleaning/coating | Author part/process-specific instructions and inspection points; assembly/ | Manual |
| D08 | approved-substitutions.csv | Component substitution rules | Electrical + procurement + QA; Qualified alternates and restrictions | Record approved exact alternates and change-control requirement; bom/ | Manual |
| D09 | assembly-inspection-checklist.md | Assembly inspection checklist | Manufacturing + QA; Product/class/process risks and acceptance plan | Author inspection and traceability checklist; assembly/ | Manual |
| D10 | board-F_Paste.gbr / board-B_Paste.gbr | Paste/stencil data | KiCad export + stencil supplier; SMT apertures and stencil/process constraints | Export actual required paste layers; approve stencil modifications; pcb/gerbers/ | Partial |

## E. Mechanical / mounting

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| E01 | pcb-dimensions.pdf | PCB mechanical dimensions | Native board + mechanical engineer; Board geometry/datum/thickness/tolerance | Dimension controlled outline and verify STEP/native equality; mechanical/ | Partial |
| E02 | mounting-hole-table.csv / mounting.pdf | Mounting-hole locations | Mechanical engineer/native PCB geometry; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Hole XY/diameter/plating/keepouts and datums | Export/check hole positions; produce mounting drawing; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E03 | pcb-assembly.step | 3D PCB assembly model / STEP | KiCad CLI; Board plus exact part 3D models | export_cad_step; verify model coverage and units; pcb/ or registered artifact path | Partial |
| E04 | enclosure.FCStd / enclosure.step | Enclosure design files | External/manual FreeCAD; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Interfaces, access, cooling, materials, tolerances | Create enclosure model and export controlled STEP; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E05 | mechanical-assembly.pdf | Mechanical assembly drawings | Mechanical CAD + engineer; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Enclosure/PCB/hardware/heat sink and datums | Generate exploded/detail drawings, dimensions and tolerances; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E06 | connector-locations.csv / connector-pinouts.pdf | Connector positions/pinouts | Electrical + mechanical engineer; Reference, XYZ/orientation, mating part, pin functions | Export coordinates and author reviewed mating/wiring map; mechanical/ / integration/ | Partial |
| E07 | heatsink-cooling.pdf | Heat sink and cooling requirements | Thermal calculator + mechanical engineer; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Loss/temperature budget and actual sink/airflow/interface | Size cooling then draw interfaces and required performance; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E08 | fasteners.csv / mounting-spec.md | Fastener/mounting specifications | Mechanical engineer; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Part/thread/length/washers/torque/insulation and loads | Author hardware BOM, torque and assembly requirements; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E09 | mechanical-tolerances.pdf | Mechanical tolerances | Mechanical engineer; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Datum scheme, production process and tolerance stack | Complete dimensioned drawing and fit review; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; mechanical/ | Partial |
| E10 | installation-instructions.md / wiring.pdf | Final installation/wiring instructions | Hardware integration engineer; concurrent enclosure_generator.py supplies default draft SVG/script/TIM text; Pinouts/harness/earthing/clearance/cooling/service constraints | Author controlled installation and inspection procedure; closing source contains a draft template, but required exact fit/tolerances/parts/safe instructions still need manual engineering; integration/ | Partial |

## F. Testing / quality / release

| ID | File / format | Purpose | Generator and input | Procedure / location | Availability |
| --- | --- | --- | --- | --- | --- |
| F01 | design-verification-plan.md | Design verification plan | QA + requirements matrix; All requirements, risks, methods, environments and owners | Author requirement-specific test matrix and approvals; testing/ | Partial |
| F02 | simulation-test-results.json | Simulation test results | Core solver/evidence; Intact decks/raw/logs and acceptance requirements | Export only actual effective results and evidence links; simulations/ / testing/ | Partial |
| F03 | laboratory_test_plan.json / .md / .html | Prototype bring-up and electrical/thermal test procedures | Current laboratory-plan generator + qualified engineer; Actual topology, hazards, limits, calibration and evidence plan | Generate draft then replace hardcoded assumptions and independently review; testing/ (actual returned relative paths) | Partial |
| F04 | safety-isolation-test-requirements.md | Safety and isolation tests | Qualified compliance engineer / lab; Applicable product/insulation standard/edition and hazard analysis | Determine applicability/limits with qualified specialist; author controlled procedure; testing/ | Manual |
| F05 | functional-test-procedure.md | Functional/production test procedure | Electrical + test engineering; Functional modes, interfaces, stimulus and golden limits | Specify repeatable tests and evidence collection; testing/ | Manual |
| F06 | test-acceptance-criteria.csv | Test acceptance criteria | Requirements + qualified QA; Explicit sourced limits, uncertainty and decision rule | Map every criterion to requirement, setup and method; testing/ | Partial |
| F07 | test-report-template.md / scorecard.json | Test report templates | Laboratory-plan generator + QA; DUT/revision/instruments/operator/setup and results fields | Generate/review template; leave unexecuted results pending; testing/ | Partial |
| F08 | raw-measurements/*.csv / *.png / *.pdf | Raw measured data and instrument evidence | External calibrated lab, studio intake; Actual DUT measurements and setup/calibration identity | Export instrument raw files; preserve hashes and original provenance; measurements/ / registered evidence path | External |
| F09 | inspection-checklist.md | Incoming/final inspection checklist | QA/manufacturing engineer; Critical workmanship/dimensional/marking/traceability criteria | Author and execute actual inspection plan; quality/ | Manual |
| F10 | final-quality-approval.pdf | Final quality approval | Authorized QA/engineering organization; Accepted physical/quality evidence, deviations and approvals | Obtain accountable external approval; no automatic studio authorization; approvals/ | External |
| F11 | compliance-reports/*.pdf | Applicable laboratory/certification reports | Accredited/qualified external lab as applicable; Applicable standards, controlled test articles and lab scope | Obtain and review actual reports and certificates; quality/ | External |
| F12 | release_manifest.json | Release inventory/checksums/identity/status | Current packager; controlled manifest requires extension; All files/revisions/hashes, project and approval metadata | Build candidate then independently complete missing fields and validate; release_package/ | Partial |
| F13 | PRODUCT_REV_Complete_Manufacturing_Release.zip | Engineering handover archive | Current packager + manual controlled completion; Complete reviewed workspace deliverables and actual decisions | Build candidate; supplement excluded files; validate independently; release_package/ | Partial |
| F14 | team-handover.md / transmittal.csv | Team file handover instructions/receipt | Document control; Team bundles, manifests, revision and recipient records | Use Report 5 procedure; record each delivery/acknowledgment; handover/ | Manual |
| F15 | revision-history.md / approval-records.json | Revision history and approval records | Core history + external responsible leads; Actual changes, evidence digests, decisions and identity scope | Export history; retain explicit MANUALLY_DECLARED attribution limitations; approvals/ | Partial |


## Existing output inventory and manufacturing readability

E04 inventories 658 relevant files across live products/designs/workspaces/reports and the prior isolated native exercise, including 77 schematics, 69 boards, 7 drill files, 5 STEP files, 7 RAW files and 17 ZIPs. Counts include historical copies/fixtures and are not a unique final release inventory. Each row records exact path, size and SHA-256. A `.pdf` extension or byte count alone does not prove a readable/complete engineering document.

Native KiCad production of Gerber/Excellon/CPL/D356 and parser/export tests provide format-level evidence summarized in E06. Independent fabrication CAM opening, layer alignment and manufacturer DFM acceptance are **Not Verified / NOT_EVALUATED** unless explicitly listed in E06. No manufacturer was contacted and no fabrication order was placed. Existing historical Gerber files cannot qualify a current board revision. Exact layer coverage depends on board stackup; mask/paste/silkscreen, PTH/NPTH and slots must be checked individually.

PDF page-by-page visual QA and native mechanical-model fit were not performed in this Markdown/CSV audit. Do not infer document layout quality, enclosure fit or assembly completeness from existence. Reports preserve the distinction between draft documents available today and reviewed manufacturing instructions still required.

**Final cutoff correction (14:40:18 Asia/Calcutta):** concurrent source now includes standalone STEP/SVG/mechanical files in packaging and adds enclosure RPC/client routes. The initial STEP omission is historical. The final probe still excludes simulations/requirements and reports READY for incomplete/corrupt archives. See [closing addendum](09_CLOSING_SOURCE_ADDENDUM.md) and [cutoff evidence](evidence/final-cutoff-probe.json). Changes after this cutoff are outside this audit.
