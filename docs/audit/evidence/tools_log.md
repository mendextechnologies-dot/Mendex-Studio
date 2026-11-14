# Tools audit log (2026-11-14)
Scratch scripts are in %TEMP%\mendex-audit3\scripts (tools_audit.py, b2.py, b3.py). Data root is %TEMP%\mendex-audit3\tools\root.
- LTspice: C:\Program Files\ADI\LTspice\LTspice.exe. RC reference: .meas v1ms=6.32120362947 V (expected 6.3212). Two runs, identical raw sha256 prefix ab6813961a844f3b. The runner's vout_mean=8.1391 comes from its last-30% window. The runner does not parse .meas.
- Broken netlist (X1 with an undefined subckt): exit 1, SOLVER_FAILED/FAILED, log_errors=[] ("Output raw missing").
- Buck via EngineeringDesignService.run_ltspice_simulation: runs 1 and 2 both returned TIMED_OUT at 60 s. A direct CLI run of the same netlist took 2 s (exit 0, 13.6 MB raw), and the runner on a copy took 2.28 s. Run 3 of the app path took 2.37 s: Vout_mean 11.7114 V, ripple 0.114 V, Ipk 2.2524 A, vout PASSED (2.4%).
- KiCad (kicad-cli 10.0): the schematic has 6 symbols, 0 lib_symbols and 0 wires. ERC: 6 violations (3 label_dangling, 3 pin_not_connected). The PCB has 6 footprints, 14 pads and 0 tracks. DRC: 10 violations (4 clearance, 6 lib_footprint_mismatch) and 8 unconnected. Gerbers: 13 files. BOM CSV: header only.
- FEMM: ETD34/N87 filelink run gave NOT_EVALUATED (zero field). femm.exe PID 13348 was left running after the run and was killed manually.
