# Evidence log — tools and calculations (audit docs 09/10)

All runs: `PYTHONPATH=src C:/Python313/python %TEMP%\mendex-audit\scripts\<script>`; data roots under `%TEMP%\mendex-audit\tools\`. No files under src/, tests/ or config were written by this auditor.

## Detection
```
ls "C:/Program Files/ADI/LTspice"        -> LTspice.exe, ltspice-mcp-bridge.exe, ...
kicad-cli.exe version                    -> 10.0.7
C:/femm42/readme.txt                     -> "FEMM 4.2 21Apr2019"
a7_tools.py controller.list_tools():
 ltspice FOUND_UNVERIFIED C:\Program Files\ADI\LTspice\LTspice.exe 26.1.1.0
 femm    FOUND_UNVERIFIED C:\femm42\bin\femm.exe 1.0.0.1
 kicad   FOUND_UNVERIFIED C:\Program Files\KiCad\10.0\bin\kicad-cli.exe 10.0.7.51283
```

## LTspice buck (a1_ltspice.py, run1)
```
generate_design(vin_nom=12, vout=5, iout=2, fsw_hz=500000, ripple_v=0.05) -> topology Buck
buck_circuit.net sha256 1185e67226c01636db77244f0bcfe852f6013d244c7204e7ce1ef5ecc2a04f3a
run_simulation(tool=ltspice): status COMPLETED exit_code 0 execution_time_s 0.0 wall 3.82s
 steady_state_metrics: vout_mean_v 4.7521, ripple 0.0475, min 4.7305, max 4.7779, i_peak_a 3.4039
buck_circuit.raw 18,456,453 B, 20 vars, 37555 pts, sha256 96abdff5f883581ed8b41df23c214bc3ff79e0d2c8c6b32a04cbe2a14554094d
log: "LTspice 26.1.1 for Windows ... Direct Newton iteration succeeded ... Total elapsed time: 1.774 seconds. Total iterations: 145230"
a2_parse.py (independent): Tstop=0.005 last 0.5ms Vout_avg=4.7558 Vpp=0.0475 IL_avg=1.9023 IL_pp=0.5979 IL_max=2.2014 Pin=9.630 Pout=9.047 eff=0.939
 IL max whole run 3.4039 at t=1.085e-05 s; app index window starts t=3.498e-3 s
```

## LTspice failure handling (a3_fail.py)
```
BROKEN: success False exit 1 SOLVER_FAILED; log "broken.net(3): Expected node name here."
STALE-1 good: True 4.7521 ; STALE-2 broken same name: False exit 1 SOLVER_FAILED
TIMEOUT (.tran 2s, timeout_s=3): TIMED_OUT wall 3.03s; no LTspice child left from this run
(pre-existing LTspice PID 30444 started 20:11 on %TEMP%\tmp1rx__wqx\test_sim.net, not audit-owned, left untouched)
```

## LTspice flyback (a5_fly.py on run2 flyback_circuit.net)
```
M_Q1 DRAIN GATE 0 0 NMOS_DEFAULT_Q1 ; V_G1 GATE_HI SW PULSE(...) ; V_G2 GATE_LO 0 PULSE(...) ; D_FW 0 SW D_IDEAL
result: success True exit 0 vout_mean_v -0.0 ripple 0.0 convergence CONVERGED summary_verdict PASSED
log: "WARNING: Node gate is floating."
```

## FEMM (a4_femm.py, run2, flyback 24->12V 1A 100kHz iso 1500V)
```
GEOM ETD34 N87 Ae 97.1 al_nh 210 Np 14 Ns 12 gap 0.65
run_femm_simulation (filelink): 0.96s success True b_max_tesla 0.285 SOLVED_CONVERGED PASSED
 etd34_core.fem 1302 B, etd34_core.ans 442046 B exist
controller.run_simulation(tool=femm) (run_script): 60.06s FAILED "timed out after 60 seconds"
 side files in workspace root: temp_mag.fem 1642, temp_mag.ans 442386, core_analysis.ans.bmp 1972218
tasklist femm.exe afterwards: none
```
Repo-root `femm_in.tmp`: observed at start (16 B, "flput(create(0))", mtime 20:54); later observed absent. Not deleted by this auditor.

## KiCad (run1 buck)
```
kicad-cli sch erc --format json  -> exit 0, 6 violations (3 label_dangling, 3 pin_not_connected, all hierarchical labels)
kicad-cli pcb drc --format json  -> exit 0, 10 violations (4 clearance error 0.1021mm<0.2mm, 6 lib_footprint_mismatch), 8 unconnected
kicad-cli sch export netlist     -> exit 0, (components) empty, (nets) empty
.kicad_pcb: (segment count 0, footprint count 6, pad count 15), all footprints Resistor_SMD:R_0805_2012Metric
```

## Calculations (a6_calc.py)
```
BUCK 12->5 2A 500k: d 0.41667 L 9.72222uH C 3.0uF Ipk 2.3 stress 18.0 eff 0.94
BUCK ripple=10mV: identical (C 3.0uF)
BUCK vin_min=4: buck still selected, identical values
BOOST 5->12 1A: only Flyback, lm 0.2376uH Ipk 15.15A
NEG vin -12: flyback n -1.378 Ipk -5.26
ZERO fsw / ZERO iout: ZeroDivisionError
NEG vout: Buck score 0.95 d -0.41667 L -23.61uH C -3.0uF
FLYBACK synth 24->12 1A 100k: lm 27.37uH n 1.23694 Ipk 3.1566 Vds 94.51
DETERMINISM params equal True, metrics equal True, ids equal False
dowell 100k 0.5mm 2L 0.85 100C: delta 0.236504mm xi 1.7274 FR 3.7791 (independent 3.77923)
losses: Pcond 0.18 Psw 2.5 Ptot 2.68 ; i_rms=-4 accepted -> same 2.68
steinmetz k1.5 a1.3 b2.5 100k 0.15T 1.5e-5: 5203.79 W/m3, 0.0781 W
flyback calc: Np 3 Ns 3 n 1.0 Lm 10.02uH Ipk 9.091 Irms_pri 3.732 Isec_pk 9.091 Irms_sec 4.4 gap 0.141mm
flyback vin_min 30 > vin_nom 24: accepted
all run_calculation repeats identical: True
```
