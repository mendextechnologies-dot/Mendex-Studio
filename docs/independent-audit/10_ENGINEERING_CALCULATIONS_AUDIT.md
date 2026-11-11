# 10 — Engineering Calculations Audit (Independent)

Date: 2026-11-11. Script: `%TEMP%\mendex-audit\scripts\a6_calc.py` (calls `CandidateSynthesisEngine.synthesize_candidates` and `MendexEngineeringController.run_calculation` with data root `%TEMP%\mendex-audit\tools\calc`). Full output in `evidence/tools_and_calcs_log.md`.

## 1. Inventory

| Location | Topology / calculation | Equations implemented |
|---|---|---|
| design/synthesis.py:50-79 | Synchronous buck (non-isolated, only if `vin_min > vout`) | D = Vo/Vin_nom; ΔIL = 0.3·Io; L = (Vin_nom−Vo)·D/(f·ΔIL); C = ΔIL/(8·f·0.01·Vo); Vstress = 1.25·Vin_max; Ipk = Io+ΔIL/2; efficiency **constant 0.94** |
| synthesis.py:81-116 | Flyback (always offered) | Vor = Vin_min·Dmax/(1−Dmax), Dmax = 0.45 fixed; n = Vor/(Vo+0.7); Lm = (Vin_min·Dmax)²/(2·Pin·f) (BCM/DCM boundary); Ipk = 2·Pin/(Vin_min·Dmax); Vds = Vin_max+Vor+50; η constant 0.88; Cout fixed 100 µF |
| synthesis.py:118-138 | Push-pull | n = (Vo+0.7)/(2·Vin_min·0.45); Vstress = 2.2·Vin_max; Ipk = Pin/Vin_min; **no IR, no netlist** (`ir_snapshot=None`) |
| calculations/transformer_design.py | Flyback transformer (CCM, K_RF = 0.8) | n, Np = Vin_min·D/(Bmax·Ae·f), Ns, Lm = (Vin·D)²/(2·Pin·f·K_RF), ΔI, Ipk, Irms pri/sec, lg = µ0·Np²·Ae/Lm |
| calculations/power_losses.py | MOSFET losses | Pcond = Irms²·Rds·D; Psw = (Eon+Eoff)·f |
| power_losses.py | Core loss | Pv = k·(f/1 kHz)^α·B^β·1000 (W/m³) |
| calculations/winding_losses.py | Skin depth, Dowell FR | δ = √(ρ/(π µ0 f)), ρ(T) = 1.68e-8·(1+0.00393·(T−20)); Dowell 1-D FR with round-wire equivalent h = 0.886·d and porosity |
| design/iteration.py:49-80 | Ripple iteration | C_new = C·max(1.25·ripple_ratio, 1.5) |
| design/parametric.py | User expressions | AST safe_eval; division by zero returns `inf` silently (:20) |

**Not implemented:** boost, buck-boost, SEPIC, forward, half/full-bridge, LLC, PFC; thermal (Tj, Rθ, heatsink); tolerance/worst-case/Monte-Carlo; protection (OCP/OVP/UVLO, snubber/clamp design); capacitor RMS current/ESR; control-loop/compensation. No thermal function exists in `src/` (grep for thermal/junction/Rth hits only models/UI labels).

## 2. Hand-reference verification

### Buck 12 V → 5 V, 2 A, 500 kHz
| Quantity | App | Hand calc | Verdict |
|---|---|---|---|
| D | 0.41667 | 5/12 = 0.4167 | correct (ideal, lossless) |
| L (30 % ripple) | 9.7222 µH | 7·0.4167/(500e3·0.6) = **9.72 µH** | correct. Note: the brief's "≈5.83 µH" corresponds to ΔI = 1.0 A (50 %), not 30 % — the brief's reference was wrong, the app is right. |
| C | 3.0 µF | 0.6/(8·500e3·0.05) = 3.0 µF | correct for 1 % Vout, but see B2 |
| Ipk | 2.3 A | 2 + 0.3 = 2.3 A | correct |
| LTspice cross-check | — | ΔIL sim 0.598 A, ripple 47.5 mV, Vout 4.756 V | consistent (doc 09) |

### Flyback (run_calculation "flyback": Vin_min 18, Vo 12, Io 3, 100 kHz, Dmax 0.45, η 0.88, Bmax 0.25 T, Ae 125 mm²)
App: Pin 40.909 W, Np = 3, Ns = 3, n = 1.0, Lm = 10.02 µH, Ipk 9.091 A, Irms_pri 3.732 A, Isec_pk 9.091 A, Irms_sec 4.40 A, gap 0.141 mm.
Hand: n_design = 18/13·0.818 = 1.133; Np_raw = 8.1/(0.25·125e-6·1e5) = 2.59 → 3; Ns = round(2.65) = 3; Lm = 65.61/(2·40.909·1e5·0.8) = 10.02 µH ✔; Iedc = 5.05 A, ΔI = 8.08 A, Ipk = 9.09 A ✔; Irms_pri = √(0.45·(5.05²+8.08²/12)) = 3.73 A ✔; lg = µ0·9·125e-6/10.02e-6 = 0.141 mm ✔.
Arithmetic is correct, but:
- **F1 (P1) Np sized for ΔB, not B_peak.** Np = Vin·D/(Bmax·Ae·f) sets the *flux swing* to Bmax; with the fixed K_RF = 0.8, Ipk/ΔI = 1.125, so B_pk = 1.125·Bmax·Np_raw/Np — up to 12.5 % above the user's Bmax (here 0.243 T only because of ceil 2.59→3). No B_pk = Lm·Ipk/(Np·Ae) check is performed.
- **F2 (P1) Rounding changes turns ratio (1.133 → 1.0) but D, currents and secondary RMS are not recomputed** for the actual ratio; secondary currents assume D = Dmax. Reflected voltage and switch stress are not reported.
- F3: `vin_nom_v` is accepted and unused; vin_min 30 > vin_nom 24 accepted silently. Gap formula ignores core reluctance and fringing (acceptable first-order, but unstated).
- Synthesis flyback (24→12 V, 1 A): Vor 15.71 V, n 1.237, Lm 27.37 µH, Ipk 3.157 A — formulas correct for BCM; but the IR magnetic geometry uses hard-coded ETD34/AL 210 nH/Np = int(12·n) = 14 → 41.2 µH ≠ 27.4 µH and turns ratio 1.167 ≠ 1.237 (F4, P1).

### Losses / magnetics
- Semiconductor: Rds 25 mΩ, Irms 4 A, D 0.45, Eon 15 µJ, Eoff 10 µJ, 100 kHz → Pcond 0.18 W, Psw 2.5 W ✔ arithmetic. **F5 (P1)** `Irms²·Rds·D` is only correct if `i_rms` means the *load/inductor* current; if it is the switch RMS (as named), multiplying by D under-states conduction loss by 1/D. No Rds(on) temperature derating; Eon/Eoff not scaled to operating V/I. Negative `i_rms` accepted (−4 A gives the same loss as +4 A); negative Rds gives a raw pydantic ValidationError.
- Core loss: k 1.5, α 1.3, β 2.5, 100 kHz, 0.15 T, 15 cm³ → 5203.79 W/m³, 0.0781 W ✔ arithmetic. **F6 (P1)** The ×1000 assumes k in mW/cm³ with f in kHz, but the result's `method` string says `Pv = k·f^α·B^β` (different units). Defaults are labelled "N87" and the docstring claims "verified MagNet material datasets", but N87 at 100 kHz/150 mT is on the order of 10⁵ W/m³ — the default yields ~5 kW/m³ (≈20–30× low). No source for k/α/β; sinusoidal-only (no iGSE for PWM waveforms).
- Dowell: 100 kHz, 0.5 mm, 2 layers, η 0.85, 100 °C → δ 0.2365 mm, ξ 1.7274, FR 3.7791; independent re-implementation FR = 3.7792 ✔. Formula, round-wire equivalence and porosity are standard. Temperature > 250 °C → raw ValidationError.

## 3. Input validation (synthesis path used by CLI/MCP `generate_design`)

| Input | Result |
|---|---|
| fsw = 0 | uncaught `ZeroDivisionError` |
| Iout = 0 | uncaught `ZeroDivisionError` |
| Vout = −5 | Buck "feasible" score 0.95 with **L = −23.6 µH, C = −3 µF, D = −0.417** |
| Vin = −12 | Flyback with turns ratio −1.378, Ipk −5.26 A |
| Vin_min = 4 V < Vout = 5 V (buck) | **ignored** — buck still selected (B1) |
| 5 V → 12 V (boost case) | No boost; only flyback offered (Lm 0.24 µH, Ipk 15.2 A at 500 kHz, score 0.80) |

- **B1 (P1)** `synthesize_candidates` reads `req_map["vin_min"]` (synthesis.py:36-37) but the controller sends vin_min/vin_max as `min_value`/`max_value` of the `vin_nom` requirement (controller.py:242). User Vin range is always replaced by ±20 % of nominal. Buck feasibility, stress (1.25·Vin_max) and flyback Vor/Lm use the wrong range.
- **B2 (P1)** Ripple requirement ignored in sizing: C is always sized for 1 % of Vout (ripple 10 mV vs 50 mV → identical C = 3 µF). L is sized at Vin_nom, not Vin_max (ΔIL at 14.4 V = 0.671 A, 34 %).
- **B3 (P0 for an engineering tool)** No validation of sign/zero/physical ranges in synthesis; negative component values are produced and passed to artifact generation.

## 4. Assumptions, losses, thermal, tolerance, protection
Efficiencies (0.94, 0.88, 0.91), Dmax 0.45, ripple 30 %, 1 % voltage ripple, diode drop 0.7 V, +50 V leakage margin, MOSFET models (`VDMOS Rg=1 Vto=3 Rd=0.015`), and all FEMM geometry are fixed constants. None are stored as named assumptions with the result. No loss budget feeds the efficiency number. No thermal, tolerance or protection calculations exist.

## 5. Determinism
Two runs with identical inputs: `parameters` and `calculated_metrics` identical; IR component values identical; candidate and component UUIDs differ (expected; not content-addressed). All four `run_calculation` types returned byte-identical dicts on repeat. Deterministic: yes.

## 6. Traceability
- Candidates store numeric `parameters`/`calculated_metrics` and a free-text `rationale`, but **no formula, formula version, input set or assumption list**.
- `run_calculation` results echo only some inputs (losses: duty, f — not Rds, Irms, Eon, Eoff; Steinmetz: not k/α/β; flyback: not Vin, Vout, Iout, η, Dmax, Ae is echoed). Results cannot be re-derived from the stored record. No units on synthesis outputs beyond key suffixes.
- The netlist duty is recomputed independently in the generator (`d = Vout/Vin`, ltspice_generator.py:166) rather than read from the candidate, so the "same" D exists in two places.

## 7. Findings summary
| ID | Sev | Finding |
|---|---|---|
| B3 | P0 | No physical validation: negative/zero inputs give negative L/C or crashes |
| B1 | P1 | User Vin_min/Vin_max silently ignored (±20 % substituted) |
| B2 | P1 | Ripple requirement not used to size C; L sized at Vin_nom |
| F1 | P1 | Flyback Np from ΔB, B_pk can exceed Bmax by up to 12.5 %; no saturation check |
| F2 | P1 | Turns rounding changes ratio without recomputing D/currents |
| F4 | P1 | FEMM/IR magnetic geometry hard-coded, inconsistent with computed Lm/n |
| F5 | P1 | Conduction-loss formula ambiguous (I_rms² ·R·D) |
| F6 | P1 | Steinmetz defaults labelled N87 are unsourced and ~20–30× low; unit description inconsistent |
| T | P1 | No formula/assumption/input traceability in stored results |
| G | P2 | Missing topologies (boost etc.), no thermal/tolerance/protection; efficiencies are constants |

Formula arithmetic that does exist (buck L/C/D, flyback CCM set, Dowell, skin depth, losses) is numerically correct versus hand calculations.
