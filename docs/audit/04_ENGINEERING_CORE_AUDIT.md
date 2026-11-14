# 04 — Engineering Core Audit (independent, 2026-11-14)

Scope: `src/mendex_core` + `src/integrations/calculations`. Audit only; no source changed.
All live runs used disposable roots under `%TEMP%\mendex-audit3\core`; scratch scripts in `%TEMP%\mendex-audit3\scripts`
(`calc.py`, `ctl.py`, `db2.py`, `conc.py`, `run_kill.sh`, `mig.py`). Python: `.venv\Scripts\python.exe`, `PYTHONPATH=src`.
Solvers (LTspice/FEMM/KiCad) were NOT run.

Test run: `pytest -q tests/core tests/adapters/test_calculations.py tests/adapters/test_magnetics.py` -> **243 passed in 69 s**.

## 1. Severity-ranked findings

| # | Sev | Finding | Evidence |
|---|-----|---------|----------|
| C1 | HIGH | `DeterministicCalculationService.calculate_flyback_sizing` ripple is wrong by a factor 1/D: `delta_il = krf*i_in_avg*2` uses input average current instead of the on-time pedestal `I_edc = P_in/(V_in*D)`. L_p is 2.22x too large, peak current understated. | `intelligence/calculations.py:301-306`. Ref (85 V,12 V,2 A,100 kHz,K_RF 0.4, eta 0.88): I_edc = 27.27/(85*0.45)=0.713 A, dI = 2*0.4*0.713 = 0.570 A, L = 38.25/(0.570*1e5) = **670.6 uH**, I_pk = **0.998 A**. Code: **1490.2 uH**, **0.841 A**. |
| C2 | HIGH | Silent defaults regress on the workflow path: `workflows/nodes/calculations.py:201-238` `_get(key, default)` fabricates Vin=100 V, Vout=24 V, Iout=2 A, f=100 kHz, `vin_nom = vin*1.2` (invented), Steinmetz B=0.1 T/V=1e-5 m3, L=15 uH/C=100 nF, and Dowell uses a hard-coded 0.2 mm skin depth. Reachable from the Qt workflow canvas (`mendex_ui/workflow_canvas/*`). | file:line above |
| C3 | HIGH | Two inconsistent implementations of the same physics: (a) losses — `integrations/.../power_losses.py:50` uses `I_rms^2*R*D`, `intelligence/calculations.py:380` uses `I_rms^2*R` (5 A,0.1 Ohm,D=0.5: 1.25 W vs 2.50 W); (b) Steinmetz — `power_losses.py:82` `k*(f/1k)^a*B^b*1000` vs `calculations.py:354` `k*f^a*B^b` (same k=1,a=1.5,b=2.5,100 kHz,0.1 T: 3 162 W/m3 vs 1.0e5 W/m3); (c) flyback — diode 0.7 V vs 1.0 V, K_RF 0.4 vs hard-coded 0.8. UI panels mix both. If `I_rms` is the switch RMS, the extra `*D` double-counts duty. | `power_losses.py:50,82`; `calculations.py:354,380`; `transformer_design.py:40,76` |
| C4 | HIGH | Flyback transformer `b_max_t` is applied to the flux *swing* (`Np = Vin*D/(B*Ae*f)`), not peak flux. Reference run (Ae=52 mm2, B=0.25 T): Np=30, B_pk = Lm*I_pk/(Np*Ae) = 3.353e-4*1.283/(30*52e-6) = **0.276 T > 0.25 T** — the stated limit is silently exceeded; turns rounding (n 5.35 -> 5.0) is not fed back into D/V_or. | `transformer_design.py:62-70` |
| C5 | MED | `DeterministicCalculationService` hides material/default assumptions: Steinmetz Cm/alpha/beta defaults (16.9/1.25/2.35 vs 16.7/1.35/2.40 in two methods), `b_sat_t=0.40`, `r_dc_ohm=0.05`, `efficiency=0.88`; `integrations` flyback still has defaults `frequency_hz=1e5, d_max=0.45, b_max_t=0.25, core_ae_mm2=125, v_diode_drop_v=1.0`. CLI/MCP path (`controller.py:646-723`) requires all except `v_diode_drop_v` (silently 1.0 V). | `calculations.py:205-216,341-348,118-125`; `transformer_design.py:35-40`; `controller.py:722` |
| C6 | MED | Boundary handling in `intelligence/calculations.py`: NaN passes every `<= 0` guard (skin depth, Steinmetz returned NaN); `inf` L gives f0=0; `efficiency=0` -> ZeroDivisionError, `efficiency=2` accepted; T=-300 C -> "math domain error"; `vin_nom < vin_min` accepted. Controller path: `i_rms_a=-5` accepted (squared), `layers=2.7` truncated to 2, porosity 5 silently clamped to 1.0, NaN surfaces as a pydantic error on the *output*. The engineering-records path (`engineering_records/calculations.py`, strict pydantic + `canonical()`) rejects these correctly. | `calc.py`, `ctl.py` outputs |
| C7 | MED | FEMM "B_max" is a single `mo_getpointvalues(0,0)` sample, not a maximum; labelled `b_max_tesla`. Fabrication fix is in place (zero/none -> NOT_EVALUATED). | `design/femm_runner.py:130-168` |
| C8 | MED | Design synthesis heuristics: buck L sized at `vin_nom` (worst-case ripple is at Vin_max); `constraints_satisfied=True` and feasibility scores 0.95/0.90/0.85 are hard-coded; ripple defaults to 1 % Vout when absent; push-pull `d_nom` 0.40 vs 0.45 in its ratio; IR title hard-coded "Buck 12V". | `design/synthesis.py:73-160` |
| C9 | LOW | `calculate_magnetic_core_sizing_and_loss` turns use B_peak as the swing (unipolar assumption, undocumented); saturation margin clamps to 0 when B_pk>B_sat (no negative margin shown). | `calculations.py:224-235` |
| C10 | LOW | 66 bare `except Exception:` blocks in `src/mendex_core`; no `logging` in `service.py`/`controller.py`. Error codes are mis-mapped: every `sqlite3.IntegrityError` becomes `CONFLICT "Product code or revision label already exists"` (`service.py:119-120`) — observed for an FK failure on an approval and for a blocked delete. |

## 2. Hand-checked formulas (reference vs code)

| Formula | Inputs | Hand reference | Code | Verdict |
|---|---|---|---|---|
| Skin depth (rho_100C = 1.68e-8*(1+0.00393*80)=2.208e-8) | 100 kHz | sqrt(2.208e-8/(pi*1e5*4pi e-7)) = 0.2365 mm | 0.23650 mm (both impls) | PASS |
| Dowell F_R | xi=1, m=3 | 1.0857 + 0.8543 = 1.940 | 1.93996 | PASS |
| Dowell F_R | xi=2, m=1 | 2*0.9489 = 1.898 | 1.89781 | PASS |
| Dowell analysis | d=0.5 mm, eta=0.85 | h=0.4431, xi=0.4431/0.2365*0.922=1.727 | 1.7274, F_r 7.42 (both impls agree) | PASS |
| Steinmetz (intelligence) | 100 kHz,0.1 T,1e-5 m3 | 16.7*10^6.75*0.1^2.4 = 3.739e5 W/m3 | 373 866 | PASS (arith.) |
| Steinmetz (integrations) | k=1,a=1.5,b=2.5 | 1*100^1.5*0.1^2.5*1000 = 3 162 | 3 162.28 | PASS (convention differs, C3) |
| Flyback Lm (integrations, AN4137 form, K_RF=0.8) | 85/12 V,2 A,eta .88,D .45 | (38.25)^2/(2*27.27*1e5*0.8)=335.3 uH; dI=1.141 A; I_pk=1.283; I_rms=sqrt(.45*(.508+.108))=0.527; gap=mu0*900*52e-6/Lm=0.1754 mm | identical | PASS (but C4) |
| Flyback (intelligence) | same, K_RF .4 | 670.6 uH / 0.998 A | 1490 uH / 0.841 A | **FAIL** (C1) |
| Core turns | 85 V,D .45,Ae 52,B .2 | 38.25/(1e5*52e-6*0.2)=36.8 | 36.8 | PASS |
| Semiconductor loss (intelligence) | 5 A,0.1,1 uJ+1 uJ,100 kHz | 2.5+0.2 = 2.7 W | 2.7 | PASS |
| LC | 1 uH,1 uF | 159 155 Hz, 1 Ohm | same | PASS |
| Buck (synthesis, inspection) | 12->5 V,2 A,500 kHz | D=.4167, dI=.6, L=9.72 uH, C=.6/(8*5e5*.05)=3 uF | formula matches | PASS by inspection (NOT executed) |

Reproducibility: pure functions, deterministic. Engineering-records path stores implementation SHA-256 + Python version (`engineering_records/service.py:168-189`) — good. Precision: integrations results rounded to 3-6 dp at output (`transformer_design.py:94+`), adequate.

## 3. Previous (Nov 11) fixes — re-verification

| Item | Status |
|---|---|
| Silent calc defaults | FIXED on CLI/MCP (`controller.py:663-683`, "No defaults are assumed") and records path; **NOT fixed** on workflow node (C2) and `v_diode_drop_v` default (C5). |
| Invented Vin range | FIXED: `design/synthesis.py:49-62` falls back to vin_nom, validates order/finite. |
| Unguarded delete_product | FIXED for runs/validations/reports/approvals/measurements/ECRs/non-draft (`service.py:289-329`); but engineering-record entries are not pre-checked -> misleading CONFLICT (see DB audit D3). |
| Fabricated FEMM flux | FIXED (`femm_runner.py:147-167`); label issue C7. |

## 4. Subsystem matrix

| Subsystem | Impl | Reachable (CLI/MCP/desktop) | Tests | Notes |
|---|---|---|---|---|
| Projects/products | Yes `service.py:266-380` | CLI `cli.py:469`, MCP `mcp/server.py:170`, desktop `project` | test_service, test_v21_* | Persists; conflict-safe under 2 writers |
| Specifications | Yes, draft-only edit `service.py:382-428` | CLI/MCP/desktop | test_service, test_v21_engineering_projects | Spec edits after IN_REVIEW->DRAFT do not invalidate approvals (DB D4) |
| Lifecycle | Two systems: `lifecycle/engine.py` (mutable approvals) and `engineering_lifecycle/` (append-only) | both | test_product_lifecycle, test_engineering_lifecycle | Duplicate concepts |
| Calculations | 3 code paths (C3) | CLI/MCP `controller.run_calculation`; desktop via records | test_intelligence, test_v21_controller, test_engineering_records | see §1 |
| Design artifacts / synthesis | `design/` | Qt UI, controller | test_v19_design_synthesis | heuristics C8 |
| Simulation orchestration | `integration_service.py`, `service.request_simulation` | CLI/MCP/desktop `job` | test_v20/v21 | Solvers NOT VERIFIED here |
| Validation/evidence | `service.record_validation`, append-only triggers | all | test_service | Missing file -> integrity False, effective NOT_EVALUATED (verified) |
| Component library | `components/` | UI, MCP | test_component_reference_library | not deep-audited |
| Revisions | `create_revision` `service.py:784` | all | test_desktop_revision_isolation | |
| Artifact storage | file tree under data root + sha256 | all | test_bom_export_integrity | killed writes leave orphan dirs (DB D6) |
| Reports | `generate_report` `service.py:585-780` | desktop `export_report`, CLI | test_service | Not immutable in DB (DB D2) |
| Approvals | `lifecycle_approvals` + `engineering_reviews` | desktop `approval_status`, MCP | test_engineering_reviews | `set_revision_status` refuses APPROVED ("not implemented", `service.py:477`) |
| Error handling / logging | StudioError codes | — | partial | C10 |
