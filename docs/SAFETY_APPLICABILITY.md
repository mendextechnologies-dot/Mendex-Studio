# Priority 1: safety applicability and truthful verdicts

Implemented 14 November 2026. This resolves audit A12 by failing closed when qualified rule data is unavailable. It does not implement or certify a numerical IEC/IPC rules engine.

## Core contract

`DeterministicCalculationService.calculate_iec_creepage_clearance()` returns a typed `SafetyAssessment`. `verified` is constrained to false and `evaluation_status` to NOT_EVALUATED. Required distances and a `compliant` Boolean are absent. Context includes supplied working RMS/peak voltage, pollution degree, material group, insulation type, slot width, altitude, impulse voltage, frequency and standard/edition. Unspecified fields remain null and appear in missing_inputs. Values must be finite and within the structural input domain; invalid enums, Boolean-as-number, negative distances and non-positive voltage/frequency inputs are rejected. Valid contexts outside implemented capabilities remain NOT_EVALUATED rather than inheriting a PD2 table or arbitrary multiplier.

No qualified numerical ruleset is installed, so even completely supplied context cannot produce a compliance verdict. A slot width alone does not identify the actual air/surface paths; DC output magnitude is not automatically a working RMS/peak/impulse voltage. Measurement/path geometry and a qualified ruleset remain explicit blockers.

`calculate_component_derating()` retains operating/rated arithmetic and rating-headroom outputs for explicit finite nonnegative stress values. It no longer chooses 60/80-percent limits from a component name or claims an IPC/NAVSEA profile. An optional explicit max_allowed_ratio plus nonempty limit_source enables WITHIN_SUPPLIED_LIMIT or EXCEEDS_SUPPLIED_LIMIT, with engineering evaluation still NOT_EVALUATED. Missing limit/source produces no comparison verdict. Supplied values must use comparable quantities/units; units and temperature/model applicability are not independently qualified by this arithmetic helper.

Canonical output schema: contracts/v3.1/SafetyAssessment.schema.json. Existing general CalculationResult behavior and unrelated calculator equations are unchanged. Old numerical safety output keys were intentionally removed; current callers are updated. Historical records/evidence are not migrated, rewritten or re-certified.

## Presentation changes

- Legacy insulation action shows missing context and ruleset availability, with no assumed 1000 V, 5 mm slot, environment or material.
- Wizard preview retains unrelated sizing behavior but no longer prints invented required distances or a slot PASS.
- DRC remains a separate software check. A report cannot grant HV insulation compliance; missing violation/unconnected lists do not become a zero-violation pass.
- Removed fixed PCB safety/withstand guidelines from the legacy results summary.
- Legacy BOM comparison reads actual CSV rows. It computes no stress from a designator and does not replace an exceeded limit with PASS because the ratio happens to be below 85 percent. Operating/rated values need explicitly matching units. Missing/invalid data stays Unknown / NOT_EVALUATED.

For BOM arithmetic, use CSV fields designator, operating_value, rated_value, component_type, unit (or operating_unit and rated_unit), max_allowed_ratio and limit_source. These fields are supplied engineering context, not automatic qualification. Existing generic BOM exports without stress data remain readable but unassessed.

## Sources and qualification boundary

The [IEC publication description](https://webstore.iec.ch/en/publication/59671) identifies the scope of insulation coordination, clearance, creepage and solid insulation. [TI's insulation training](https://www.ti.com/video/6146024211001) describes the roles of voltage, material classification, altitude and pollution conditions. These public references justify collecting applicability context; they do not supply qualified numerical tables for this implementation. No distances, scaling factors or legal compliance recommendations were inferred from them.

A future numerical rules engine needs an identified standard/edition and amendments, applicable equipment/insulation conditions, reviewed rule data with traceable provenance, bounded applicability, independent benchmark cases and geometry/evidence validation. None of those checks may be replaced by a successful arithmetic regression or by the presence of a PCB slot.

## Verification

Focused regression: 40 tests passed, including all 16 pollution-degree/material-group combinations, malformed inputs, no-default behavior, sourced-limit arithmetic, two DRC cases, absent BOM stresses and exceeded-limit presentation. The formerly production-root-dependent safety UI tests now use only tmp_path fixtures; the live app is not used by them.

Evidence: docs/v3.1/verification/priority1-safety-20261114/. The broader isolated regression and final preservation results are recorded in its RESULTS.md. The localhost/browser-coupled command-center module remains excluded. Native hardware operation, engineering approval and manufacturing authorization are outside this change.
