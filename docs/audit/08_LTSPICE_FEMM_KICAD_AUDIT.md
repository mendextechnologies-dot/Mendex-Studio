# 08 LTspice / FEMM / KiCad audit (2026-11-14)
Evidence is in evidence/tools_log.md.

## LTspice
The adapter exists and discovery works. Execution works: the RC reference .meas gave 6.3212 V, matching the expected value, and two runs produced identical raw hashes. Through the app path, the open-loop buck gave 11.71 V. Hand calculation: 12 V ideal, ripple 0.12 V, Ipk ≈ 2.25 A. The measured ripple was 0.114 V and Ipk 2.25 A, which matches. Gaps:
- The app path timed out twice at 60 s, then completed in 2.4 s. The cause was not determined.
- A broken netlist gives empty log_errors, so the error detail is lost.
- .meas results are not parsed.
- No ripple requirement is evaluated.
- The netlist hash is persisted only in controller.run_simulation.

## FEMM
The model has no winding excitation and no boundary conditions (femm_runner.py:107-125). The result is honestly reported as NOT_EVALUATED. The runner leaves femm.exe running after the run. The filelink files ifile/ofile are written into C:\femm42. run_script extracts nothing.

## KiCad
Discovery, ERC, DRC and gerber export run. The generated schematic has 6 symbols but 0 lib_symbols and 0 wires, and ERC reports 6 violations. The PCB has 6 footprints and 0 tracks: DRC reports 10 violations and 8 unconnected items. The gerbers are therefore not manufacturable. The BOM is empty.

## Display
desktop/service.py exposes job records only. pcb_checks and measurements are hard-coded to [] (lines 176-178).
