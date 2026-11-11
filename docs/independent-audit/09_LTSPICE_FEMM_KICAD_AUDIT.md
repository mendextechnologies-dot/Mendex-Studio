# 09 — LTspice / FEMM / KiCad Integration Audit (Independent)

Date: 2026-11-11 · Branch `v2.0-engineering-qualification` (working tree, uncommitted changes included)
Method: live runs through the app's own code path (`MendexEngineeringController`, `EngineeringDesignService`, `LTspiceRunner`, `FEMMRunner`) with data roots under `%TEMP%\mendex-audit\tools\*`. Scratch scripts in `%TEMP%\mendex-audit\scripts\a1..a7_*.py`. Raw command output: `evidence/tools_and_calcs_log.md`. Prior V20/V21 reports were not used as evidence.

## 1. Tool detection

| Tool | Path found on disk | Real version | App detection (`controller.list_tools()`) |
|---|---|---|---|
| LTspice | `C:\Program Files\ADI\LTspice\LTspice.exe` | 26.1.1 (log header "LTspice 26.1.1 for Windows") | `FOUND_UNVERIFIED`, 26.1.1.0 — correct |
| FEMM | `C:\femm42\bin\femm.exe` | 4.2 21Apr2019 (`C:\femm42\readme.txt`) | `FOUND_UNVERIFIED`, version **"1.0.0.1"** — wrong (PE file version, not FEMM version) |
| KiCad | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | 10.0.7 (`kicad-cli version`) | `FOUND_UNVERIFIED`, 10.0.7.51283 — correct |

Notes: `LTspiceRunner.DEFAULT_PATHS` hard-codes a user-specific path `C:\Users\Sagar\...` (ltspice_runner.py:70-74). `FEMMRunner.DEFAULT_BIN` is hard-coded to `C:\femm42\bin\femm.exe` (femm_runner.py:41) and does not use the adapter registry detection. Detection is "file exists", not a functional probe — `FOUND_UNVERIFIED` is an honest label.

## 2. LTspice

### 2.1 What genuinely ran
Buck design via `controller.generate_design(vin_nom=12, vout=5, iout=2, fsw_hz=500e3, ripple_v=0.05)` → `controller.run_simulation(tool="ltspice")`.
- Generated netlist `buck_circuit.net` (sha256 `1185e672…04f3a`): V1 12 V, two VDMOS switches, L1 = 9.72222 µH, C1 = 3 µF, R_LOAD = 2.5 Ω, open-loop PULSE gate drive, `.tran 0 0.005 0 10u`.
- **LTspice 26.1.1 really executed** in batch mode (`LTspice.exe -b -ascii`): exit 0, wall 3.82 s; log: "Direct Newton iteration succeeded… Total elapsed time: 1.774 seconds. Total iterations: 145230". `buck_circuit.raw` = 18,456,453 bytes, ASCII, 20 variables, 37,555 points (sha256 `96abdff5…094d`).

### 2.2 Numeric results vs. analytical expectation

| Quantity | App-reported | Independent re-parse of same .raw (time-weighted, last 0.5 ms) | Analytical (ideal) |
|---|---|---|---|
| Vout mean | 4.7521 V | 4.7558 V | 5.000 V (D = 0.4167, lossless) |
| Vout ripple p-p | 47.5 mV | 47.5 mV | ΔI/(8·f·C) = 0.6/(8·500k·3µ) = 50.0 mV |
| IL ripple p-p | not reported | 0.598 A | 0.600 A |
| IL steady-state max | — | 2.201 A | 2.30 A (at 5 V; ~2.20 A at 4.75 V) |
| "i_peak_a" | **3.4039 A** | 3.404 A occurs at t = 10.85 µs (start-up inrush) | — |
| Efficiency | — | Pout 9.05 W / Pin 9.63 W = 0.939 | app candidate claims 0.94 (hard-coded) |

The simulator results are physically consistent with the analytical design. Vout is 4.96 % low because duty is open-loop `Vout/Vin` with no compensation for Rds(on)/diode drops; the ±5 % requirement therefore passes by 0.04 % margin — a fragile pass.

### 2.3 Parser / result-handling defects
- **i_peak is start-up inrush, not steady state** (ltspice_runner.py:189 uses `max(iin_vals)` over the whole run; iin is actually `I(L1)` chosen by substring match at :292-296). Reported 3.40 A vs steady-state 2.20 A. P1.
- **Steady-state window is by sample index, not time** (:181-183, "last 30 %"); with variable time step this started at t = 3.498 ms of 5 ms. Works here by luck; mean is not time-weighted. P2.
- **Requested duration ignored**: `run_simulation(stop_time_s=…)` never edits the netlist; controller `duration_s=0.002` → netlist still runs `.tran … 0.005`. P1 (recorded job parameter `duration_s` is false provenance).
- **`elapsed_time_s` / `execution_time_s` always 0.0** (never assigned). P2.
- **Log never parsed**: warnings like "Node gate is floating" are ignored; `convergence_status` is hard-coded `"CONVERGED"` (:230). P1.
- **No requirements ⇒ "PASSED"**: `all_passed` starts True (:194); controller path passes no requirements, so any run returns `summary_verdict="PASSED"` (see flyback below). P0 together with 2.4.
- `RAW_EMPTY` returns `success=True` (:171-179). P2.
- Waveforms: only the first 200 points are kept in the result (`time_trace[:200]`, :223) — that is the first ~µs of start-up, not representative. Stale `.raw` is not deleted before a run; failures were nonetheless caught in my test because LTspice exit code ≠ 0.

### 2.4 Flyback LTspice — simulation "succeeds" with a non-functional circuit (P0)
Flyback design (24→12 V, 1 A, 100 kHz, isolation 1500 V) netlist: `M_Q1 DRAIN GATE 0 0 …` but drive sources are `V_G1 GATE_HI SW …`, `V_G2 GATE_LO 0 …`, plus `D_FW 0 SW` (ltspice_generator.py:174-183, emitted for every topology with a switch). The flyback gate net `GATE` has no driver. LTspice log: **"WARNING: Node gate is floating."** Result: `success=True, exit_code=0, vout_mean_v=0.0, ripple 0.0, convergence_status=CONVERGED, summary_verdict=PASSED`. A dead converter is reported as a passing simulation. The secondary ground is tied to node 0 (no isolation modelled).

### 2.5 Failure handling (tested)
- Broken netlist (`R1 VIN`): exit 1, `SOLVER_FAILED`, log path returned; log text "Expected node name here." — correct.
- Same-name re-run with broken netlist after a good run: `success=False, exit_code=1` — correct (exit code guards stale .raw).
- Timeout (`.tran 2s` with 10 ns step, `timeout_s=3`): `TIMED_OUT` after 3.03 s; `tasklist` shows no LTspice child left from this run (subprocess.run kills it). One pre-existing LTspice GUI (PID 30444, started 20:11 with `%TEMP%\tmp1rx__wqx\test_sim.net`, parent not the audit) was left running by an earlier session/test — not killed by me.

### 2.6 Revision association
`controller.run_simulation` picks `ws_dir.glob("**/*.net")[0]` (controller.py:~478) — arbitrary when several revisions/topologies exist; the job record stores workspace id and input path only, no design id/revision id or netlist hash. `EngineeringDesignService.run_ltspice_simulation` (service.py:270) is revision-scoped but is not what CLI/MCP call. P1.

### 2.7 Native-file opening (code inspection only)
`service.open_artifact` → `mendex_core.launch.open_native(path)` after an existence check (service.py:335-360). `.asc` generator (ltspice_generator.py:15-88) places symbols on a grid with net FLAGs at guessed pin offsets and no wires; the `nmos` symbol pin geometry/flags were not verified and the `.asc` was not opened. The `.asc` and `.net` are generated independently, so they can diverge. Treat `.asc` editability as UNVERIFIED.

## 3. FEMM

### 3.1 Adapter readiness vs. solver readiness
Two separate, divergent FEMM paths exist:
1. `FEMMRunner.run_magnetic_analysis` (femm_runner.py:52-196): filelink (`femm.exe -filelink -windowhide`, `ifile.txt`/`ofile.txt` written into **`C:\femm42\bin`**, outside the data root).
2. `FEMMRunner.run_script` (femm_runner.py:202-234), used by `controller.run_simulation(tool="femm")`: `femm.exe -lua-script=…` without `-windowhide` and without `quit()`.
3. (`src/integrations/adapters/femm.py` uses a third, richer transformer script and appends `quit()`; not exercised by the controller.)

### 3.2 What genuinely ran
- Filelink path: FEMM **did run** (0.96 s), produced `etd34_core.fem` (1302 B) and `etd34_core.ans` (442,046 B). Result returned: `success=True, b_max_tesla=0.285, SOLVED_CONVERGED, PASSED`.
- **0.285 T is a hard-coded fallback, not a solver result (P0).** The model is a single N87 rectangle with no coil, no circuit property, no current and no boundary condition (femm_runner.py:107-118), so the field is identically zero. When |B| < 1e-6 the code substitutes `getattr(geometry, "b_max_estimate", 0.285)` (:141-142); `IRMagneticGeometry` has no `b_max_estimate`, so the constant 0.285 is returned and labelled "SOLVED_CONVERGED/PASSED". The returned value is exactly 0.285 — this is fabricated evidence.
- `run_script` path: FEMM opened, solved the Lua (wrote `temp_mag.fem`, `temp_mag.ans` and a 1.97 MB `core_analysis.ans.bmp` into the **workspace root**, not the artifacts folder — relative paths in femm_generator.py), then stayed open (no `quit()`) until the 60 s timeout killed it → `FAILED`, `b_max_tesla=0.0`. No result extraction exists in this path; if FEMM did exit 0 it would report `SOLVED_CONVERGED/PASSED` with no measurement.
- Material permeability differs between paths (2200 in runner vs 2500 in generator). Geometry (ETD34, AL 210 nH, Np = 14) is hard-coded and inconsistent with the computed Lm (14²·210 nH = 41.2 µH vs Lm 27.4 µH).

### 3.3 Stray `femm_in.tmp` (repo root)
16 bytes, content `flput(create(0))`, mtime 2026-11-11 20:54; untracked. It matches the `_call_femm` command format but no current `src/` code writes this filename — it is residue of an earlier filelink experiment/test run executed with cwd = repo root. Not touched.

## 4. KiCad

Generated for the buck design: `auditbuck.kicad_sch` (2684 B), `auditbuck.kicad_pcb` (4852 B), `.kicad_pro`.
- **Schematic is effectively empty (P0).** It contains 6 `(symbol (lib_id …))` instances but no `lib_symbols` section, no wires, no labels on pins; "Value" fields hold descriptions ("Power Inductor"), no footprints. `kicad-cli 10.0.7 sch export netlist` → `(components)` and `(nets)` **empty**. ERC (`kicad-cli sch erc`, exit 0): 6 violations, all on 3 dangling hierarchical labels — ERC "passes" only because KiCad sees no components. Any ERC-based gate on this file is meaningless.
- **PCB is a placeholder (P1).** Edge.Cuts rectangle 60×45 mm, 6 footprints, 15 pads, nets assigned to pads, **0 tracks, 0 zones, 0 vias**. Every part — including MOSFETs, a 2 A inductor and the V1 source — uses `Resistor_SMD:R_0805_2012Metric`; 3-pin parts get a third pad overlapping the 0805 pads. DRC (`kicad-cli pcb drc`, exit 0): 10 violations (4 clearance **errors** 0.102 mm < 0.2 mm on Q1/Q2 pads, 6 `lib_footprint_mismatch`), 8 unconnected items.
- File-format versions 20231120/20240108 (KiCad 8 era) while artifacts are named "KiCad 9"; KiCad 10 loads them.
- The app has a kicad-cli ERC/DRC adapter (src/integrations/adapters/kicad.py:62-69) but `generate_native_artifacts` does not run it.

## 5. Findings summary

| ID | Sev | Finding | Evidence |
|---|---|---|---|
| T1 | P0 | FEMM B_max 0.285 T is a hard-coded fallback reported as SOLVED/PASSED | femm_runner.py:107-142; live result |
| T2 | P0 | Flyback LTspice netlist has floating gate; Vout 0 V reported success/PASSED | ltspice_generator.py:174-183; LTspice log warning |
| T3 | P0 | KiCad schematic has no lib_symbols/wires → KiCad sees 0 components; ERC vacuous | kicad-cli netlist export empty |
| T4 | P1 | i_peak = start-up inrush (3.40 A vs 2.20 A) | ltspice_runner.py:189 |
| T5 | P1 | duration_s/stop_time_s ignored; provenance records wrong value | ltspice_runner.py:111-140 |
| T6 | P1 | LTspice log not parsed; convergence status hard-coded | ltspice_runner.py:230 |
| T7 | P1 | PCB is placeholder: all 0805 resistor footprints, no tracks, DRC clearance errors | .kicad_pcb, drc.json |
| T8 | P1 | Controller sim selects first `*.net` in workspace; no revision/design binding | controller.py run_simulation |
| T9 | P1 | FEMM run_script never quits, no extraction, writes outputs to workspace root; filelink writes into C:\femm42\bin | femm_runner.py:202-234, :71-72 |
| T10 | P2 | execution_time_s always 0; FEMM version misreported "1.0.0.1"; hard-coded user path | — |

Genuine capability: LTspice batch execution and ASCII .raw parsing for the buck reference design work, and the numbers agree with first-principles values (ripple 47.5 mV vs 50 mV, ΔIL 0.598 A vs 0.600 A, Vout 4.75 V vs ideal 5 V with expected loss droop).
