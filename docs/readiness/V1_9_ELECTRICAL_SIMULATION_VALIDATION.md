# v1.9 Readiness Gate — Test A: Electrical Circuit Simulation (LTspice)

**Result: FAIL** — the Studio executes a genuine LTspice solve and archives the files with hashes, but it does not extract, compare, visualise or report any numerical result. All numerical agreement shown below was obtained by the independent QA parser, not by the Studio.

Gate baseline: commit `dc21aa9` (frozen snapshot, see [V1_9_ENGINEERING_READINESS_GATE.md](V1_9_ENGINEERING_READINESS_GATE.md)). Evidence: `.mendex/qa/v19-readiness/pinned_dc21aa9/test_a/` (repeat of first pass in `.mendex/qa/v19-readiness/test_a/`, identical numerics).

## 1. Reference model and acceptance (fixed before execution)

| Item | Value |
|---|---|
| Circuit | `V1 in 0 PULSE(0 5 0 1n 1n 1 2)`, `R1 in out 1000`, `C1 out 0 1e-6 IC=0` |
| Analysis | `.tran 0 5m 0 1u UIC`, `.options plotwinsize=0 numdgt=15` (waveform compression off) |
| Solver (from LTspice log) | LTspice 26.1.1 for Windows, solver = Normal, method = trap, tnom/temp = 27 °C |
| Reference | V(t) = 5·(1 − e^(−t/τ)), I(t) = (5/1000)·e^(−t/τ), τ = RC = 1 ms |
| Check points | t = 0.1, 0.5, 1, 2, 3, 5 τ (linear interpolation between solver samples) |
| Tolerance | \|ΔV\| ≤ 1 mV (0.02 % of 5 V); \|ΔI\| ≤ 1 µA (0.02 % of 5 mA) |

Tolerance justification: with max step h = 1 µs = τ/1000, the trapezoidal local truncation error is of order (h/τ)²/12 ≈ 1e-7 relative; linear-interpolation error is ≤ h²·max|V''|/8 ≈ 0.6 µV; the 1 ns source edge shifts the response by ≤ 1e-6 τ. A 1 mV bound is therefore conservative while still catching wrong component values, units or node mapping (which would produce errors > 10 mV).

## 2. Execution path

Executed through the single core service, exactly as the UI registers connectors (`mendex_ui/window.py` → `V15ConnectorRegistry` → `StudioService.integrations`):

`attach_input()` → `submit(JobRequest(tool_id="ltspice", operation="batch_simulate"))` → `LTspiceV15Connector` → `LTspice.exe -b -ascii <netlist>` via `SafeRunner` → `manifest.json` with SHA-256 per artifact.

Harness: `.mendex/qa/v19-readiness/harness/test_a_ltspice.py`, `rc_job.py`, `qa_common.py` (independent ASCII `.raw` parser and analytic reference).

## 3. Results (pinned run)

Job `8c7e101d-749e-412d-b536-04c40029b72c` · status SUCCEEDED · exit 0 · 5024 solver points · signals `time, V(in), V(out), I(C1), I(R1), I(V1)`

| t/τ | t (ms) | V_sim (V) | V_ref (V) | ΔV (µV) | ΔV/V_ref | I_sim (mA) | I_ref (mA) | ΔI (nA) | Result |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 0.1 | 0.475810162 | 0.475812910 | -2.748 | -5.77e-04 % | 4.524189838 | 4.524187090 | +2.748 | PASS |
| 0.5 | 0.5 | 1.967344961 | 1.967346701 | -1.741 | -8.85e-05 % | 3.032655039 | 3.032653299 | +1.741 | PASS |
| 1.0 | 1.0 | 3.160601815 | 3.160602794 | -0.979 | -3.10e-05 % | 1.839398185 | 1.839397206 | +0.979 | PASS |
| 2.0 | 2.0 | 4.323323280 | 4.323323584 | -0.304 | -7.03e-06 % | 0.676676720 | 0.676676416 | +0.304 | PASS |
| 3.0 | 3.0 | 4.751064567 | 4.751064658 | -0.091 | -1.92e-06 % | 0.248935433 | 0.248935342 | +0.091 | PASS |
| 5.0 | 5.0 | 4.966310262 | 4.966310265 | -0.003 | -5.66e-08 % | 0.033689738 | 0.033689735 | +0.003 | PASS |

Maximum |ΔV| = 2.75 µV (limit 1 mV). Solver accuracy: **verified**.

Checksums: input `f66d47db79f7c1cd5451e72082a97f16c3db308c9cc382ee44ef622d3d193031`, raw `c0764077edebaeab2d2914fc45c3b72770f8e4f3fdffccff02cfcdc3499928d0`, LTspice log `69860297617dbe5060fd1ea737c505bbc88f16ed504981775e279615eb75355e`.

## 4. Step-by-step verdict

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Circuit input creation/import | PASS | `attach_input` stages netlist into workspace with hash |
| 2 | Model validation | FAIL | No pre-solve netlist validation; an invalid netlist is only detected by LTspice exit code, and the Studio job carries **no diagnostic text** (Test H) |
| 3 | Simulation configuration | PARTIAL | Only via raw netlist text; no Studio-level analysis settings |
| 4 | Actual LTspice execution | PASS | Real process, exit 0, LTspice log present |
| 5 | Genuine simulation files | PASS | `.raw` + `.log` listed in `manifest.json` with SHA-256 |
| 6 | Waveform extraction | **FAIL** | Studio `JobResult` exposes only file paths. `integrations/parsers/ltspice_parser.py` reads only the `.raw` header. No V/I samples are extracted by any Studio code path. |
| 7 | Comparison with analytical solution | **FAIL** | Not provided by the Studio; performed by QA harness only |
| 8 | Waveform viewer | **FAIL** | `SimulationLabPanel.run_simulation()` calls `waveform_viewer.load_benchmark_data(0)`, which plots a hard-coded analytic 10 V / 1 ms RC curve (`waveform_viewer.py:188-202`) regardless of the solver output. Additionally, `SimulationLabPanel` is not instantiated by `StudioWindow` at the gate baseline (Test I). |
| 9 | Results stored in workspace | PASS | `studio_root/.mendex/ij/<job>/` with manifest; integrity check `True` |
| 10 | Traceable engineering report | **FAIL** | `export_report()` produces a JSON dump labelled `engineering_status: NOT_EVALUATED` containing no numerical values, and its limitations state *"Synthetic outputs are software test fixtures"* even for this real LTspice run (Test E) |

Additional observation: the LTspice connector reports `version = "26.1.1.0"` from a hard-coded constant (`TESTED_VERSION`) rather than querying the binary. On this host it coincides with the file version (26.1.1.0), but the value is not measured.

## 5. Reproduce

```
cd ".mendex/qa/v19-readiness/harness"
set MENDEX_SRC=<repo>\.mendex\qa\v19-readiness\snapshot_dc21aa9\src
set QA_RUN_TAG=rerun
..\..\..\..\.venv\Scripts\python.exe test_a_ltspice.py
```
