# Local verification evidence

**Date:** 15 November 2026, Asia/Calcutta. No application code was fixed during this assessment.

## Initial selected run

[pytest.xml](pytest.xml), [pytest.log](pytest.log): **157 tests, 153 passed, 4 failed, 0 skipped**, about 423 seconds. Tests were selected from revision/export governance, coherent buck reference, truthful evidence/waveforms, agent parity, qualified inputs, wider engineering, release/turnkey packaging, WCCA, PCB thermal, scope correlation, BOM integrity, safety, engineering records, requirements traceability, LTspice/KiCad adapters and embedded Copper.

Execution used the existing Python 3.13 virtual environment, `-B`, `-p no:cacheprovider`, an audit-local basetemp and the evidence directory as cwd. Tests using `Path('.')` could not access the real root database. Existing real launch-boundary fixtures prevented user desktop editor launches; native solver/CAD subprocesses ran only on disposable fixtures. No packages were installed.

| Initial failure | Interpretation and follow-up |
| --- | --- |
| test_g21_installer_script_and_entry_point | Relative `scripts/...` lookup fails from isolated cwd. Read-only root-cwd targeted rerun passed. This does not qualify the installer; it only finds its source and entry point. |
| test_exports_use_supplied_rows_and_preserve_every_previous_byte | DOCX save failed with FileNotFoundError under deep Windows audit/UUID paths. Same test passed using a shorter temporary root. Export portability/path handling remains a limitation, G17. |
| test_emc100_reference_design_bom_compilation | Test uses StudioService(Path('.')) and a hardcoded live product UUID. Correctly absent from isolated root. Not rerun against the live product, to preserve the assessment boundary. Test must be isolated; no product-specific BOM qualification inferred. |
| test_ltspice_numpy_waveforms_parser | Two-sample fixture expects p2p=5 across the full record. Current default uses final 30% time window, containing one point and returning p2p=0. This is an unresolved test/metric semantic mismatch, not proof native SPICE execution failed. Single-point steady-state adequacy and unweighted RMS deserve explicit treatment. |

[targeted-retest.xml](targeted-retest.xml), [targeted-retest.log](targeted-retest.log): the first two contextual retests **2 passed**. No application changes were made to obtain them. They do not erase the initial log.

[close-regression.xml](close-regression.xml), [close-regression.log](close-regression.log): **56 passed in 34.73 s** for lifecycle, reviews, PCB workspace and current thermal tests, after the concurrent thermal/core source additions. These tests validate their assertions; thermal test success does not disprove the independently observed false PASS/compliance boundary.

## Actual native tool evidence

| Capability | Observed result | Evidence and limit |
| --- | --- | --- |
| KiCad CLI version | 10.0.7, successful version command | native-tools.json; Windows metadata additionally reports 10.0.7.51283 |
| LTspice | Executable metadata 26.1.1.0; native batch/netlisting tests passed | tool-discovery.json; actual disposable raw/log files in pytest-temp |
| Coherent buck ASC/netlist | Native ASC extraction passed pin/node expectations; nominal simulation passed 4.75–5.25 V and <=0.10 V ripple assertions | test_milestone2_coherent_buck_reference; 12 V → 5 V, 1 A, 100 kHz idealized reference only |
| Native buck ERC | Zero violations in emitted report | pytest-temp/test_kicad_schematic_erc_zero_0/kicad_buck/erc.json |
| Routed buck native DRC | Zero errors, zero unconnected items, **16 warnings** | pytest-temp/test_kicad_pcb_drc_and_no_isol0/drc.json; native-check-summary.json. The test does not require warning-free output. |
| Missing gate/load negative tests | Passed detection assertions | Selected coherent-reference tests; not complete topology fault coverage |
| Copper/native integration | Placement, routing, 3D PNG, STEP, fabrication export and four-layer tests passed | tests.integrations.test_copper_kicad_adapter in pytest.xml. Generated STEP existence/size is not independent enclosure-fit verification. |
| Turnkey native exports | CPL, D356, board stats and downloadable candidate archive tests passed | test_turnkey_manufacturing_package; fixture has a simple board and dummy BOM, no production acceptance |
| Core/evidence guards | Selected archived CAD guard, nested ERC, empty FEMM and waveform regressions passed | pytest.xml; new WCCA/package/enclosure paths have separate guard gaps |

The full raw native reports are retained under pytest-temp. Some tests use mocked/minimal data, notably release-package end-to-end tests. Do not classify mocked HTML/PDF/PNG fragments as usable manufacturing files. Native exported Gerber/Excellon format generation succeeded; **independent standard CAM viewing and manufacturer acceptance remain Not Verified**. No external fabricator or assembler was contacted.

## Static, isolated and environment checks

- `desktop/node_modules/.bin/tsc.cmd --noEmit` initially exited 0; [typescript.log](typescript.log) is empty on success. The final source check is [typescript-final.log](typescript-final.log), with exit status in [closing-checks.json](closing-checks.json). No bundle or installer was built.
- Read-only SQLite `integrity_check=ok`, user_version=4. E03 records table counts; no service was constructed against live root by audit probes.
- Initial negative probe confirms empty WCCA substitutes 1000 V / ±2% / fixed tolerances; empty thermal returns PASS/standards flags; unknown MPN gets category sourcing fields; incomplete/corrupted archive reports READY; simulations/standalone STEP omitted; archived WCCA/package writes allowed.
- Empty-specification laboratory-plan generation raises TypeError when formatting None. Source additionally embeds unqualified generic circuit/limit assumptions; the procedure must not be used as authorization to energize hardware.
- Final empty thermal/enclosure probes and source copies capture concurrent additions separately. New draft enclosure generation succeeded without native STEP; it returned fixed thermal values without actual loss inputs.
- Before/after monitored source/live-file changes are disclosed in preservation.json and closing addendum. The audit does not assert an unchanged global workspace; it intentionally wrote reports/probes only to audit paths, temporary test roots and the audit checklist entry.

No whole-product compliance, true measured hardware validation, final manufacturer CAM acceptance, complete assembly instructions, complete mechanical fit or production release was established. These remain **NOT_EVALUATED**.

Final-cutoff isolated packaging probe: STEP inclusion is corrected in concurrent source; simulation/requirements omissions and incomplete/corrupt READY behavior persist. The 56-test run predates that final patch; no broader regression claim is made for it. See final-cutoff-probe.json.
