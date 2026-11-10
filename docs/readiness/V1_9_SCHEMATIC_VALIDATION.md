# v1.9 Readiness Gate — Test C: Schematic & Electrical Rule Validation (KiCad 10.0.7)

**Result: FAIL** — KiCad itself correctly separates the valid and invalid schematics, but the Studio cannot run KiCad through its core service. Both of the Studio's other KiCad code paths report a **clean pass for a schematic that has two ERC errors**.

Evidence: `.mendex/qa/v19-readiness/pinned_dc21aa9/test_c/` (and first pass in `test_c/`) · harness `harness/test_c_kicad.py`, `harness/test_d_workflow_backend.py`.

## 1. Reference schematics (generic)

Both use the stock library symbol `Device:R` (embedded verbatim from `KiCad/10.0/share/kicad/symbols/Device.kicad_sym`), with two 10 kΩ resistors R1 and R2.

| Case | Topology | Expected |
|---|---|---|
| `valid.kicad_sch` | R1 ∥ R2: pin 1 to pin 1, pin 2 to pin 2 (closed loop) | 0 ERC errors; 2 nets |
| `invalid.kicad_sch` | Same, bottom wire removed | `pin_not_connected` on R1 pin 2 and R2 pin 2 |

## 2. Execution (real KiCad CLI)

```
kicad-cli sch erc --format json --severity-all --exit-code-violations --output erc.json <sch>
kicad-cli sch export netlist --format kicadsexpr --output netlist.net <sch>
```

| Case | ERC exit | ERC errors | Violations (KiCad report) | Netlist nets | Studio parser on same `erc.json` |
|---|---|---|---|---|---|
| valid | 0 | 0 | — | `Net-(R1-Pad1)`, `Net-(R1-Pad2)` | 0 violations |
| invalid | 5 | 2 | `pin_not_connected`: Symbol R1 Pin 2; `pin_not_connected`: Symbol R2 Pin 2 | `Net-(R1-Pad1)`, `unconnected-(R1-Pad2)`, `unconnected-(R2-Pad2)` | **0 violations** |

Library references: the netlist `libsource` is `(lib "Device") (part "R")` for both components. Netlist node lists show R1/R2 pins mapped as designed.

Tool-level valid vs invalid discrimination: **PASS**.

## 3. Studio integration

| Path | Observed | Severity |
|---|---|---|
| Core service (UI path) | `verify("kicad")` → `NOT_INSTALLED`; `submit(operation="erc")` → `UNSUPPORTED`. KiCad is registered as `UninstalledToolV15Connector`. | Blocking |
| Adapter layer `integrations.adapters.KiCadAdapter` (not wired to the service) | Runs real `kicad-cli sch erc`, but for the **invalid** schematic returns `status SUCCEEDED`, `violation_count 0`. Cause: `parsers/kicad_parser.py` reads top-level `violations`, while KiCad ERC JSON nests them in `sheets[].violations`. The adapter also omits `--exit-code-violations` and maps status only from the exit code. | **Critical — false clean result** |
| v1.9 workflow node `kicad_check` (commit `dc21aa9`) | Given `invalid.kicad_sch`, returns `status COMPLETED`, `violations_count 0`, `passed True` **without running KiCad** (`nodes/tools.py`, `KiCadCheckNode.execute` returns constants). | **Critical — fabricated pass** |

| # | Requirement | Result |
|---|---|---|
| 1 | Schematic creation/import | Tool-level PASS (QA-authored file); Studio: attach only |
| 2 | Component and net connectivity | Tool-level PASS |
| 3 | Library references | Tool-level PASS |
| 4 | ERC | Tool-level PASS |
| 5 | KiCad CLI execution via Studio | **FAIL** (core service UNSUPPORTED) |
| 6 | ERC report generation | Tool-level PASS |
| 7 | Netlist export | Tool-level PASS; Studio has no netlist operation |
| 8 | Result capture inside Studio | **FAIL** (misparsed / fabricated) |
| 9 | Evidence and report storage | FAIL (no Studio job could be created) |
| — | Distinguish valid and invalid | **FAIL in Studio**, PASS in KiCad |

Test-procedure notes: the first netlist check used a single-line string match that does not fit KiCad's multi-line S-expressions and reported 0 nets. It was replaced by a whitespace-tolerant regex, and the correction is recorded in `result.json` (`qa_note`). The first workflow-node call omitted the required `FileReference.filename`; it was rerun correctly. Both were QA harness errors.
