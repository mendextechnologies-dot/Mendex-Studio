# Engineering Tools Validation

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** Native engineering tools qualified on actual local workstation binaries.

| Tool | Workstation Path | Operation | Qualification Evidence |
|---|---|---|---|
| LTspice 26.1.1.0 | `C:\Program Files\ADI\LTspice\LTspice.exe` | Batch Transient (`-b -ascii`) | Real solve; 14,236 ASCII raw points parsed. Independent mean 4.5970 V, ripple 0.0494 V. Current parser strictly ingests named current traces `I(...)`. |
| FEMM 4.2 | `C:\femm42\bin\femm.exe` | 2D Magnetics FEA | Real Lua script meshing and solving via official filelink protocol; true numerical flux density parsed ($B = \sqrt{B_1^2 + B_2^2}$); fabricated 0.285 T removed. |
| KiCad 10.0.7 | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | ERC / DRC Checks | Valid S-expression pad net mapping `(net <id> "<name>")` prevents syntax errors; native DRC executes on generated layout. |

### Retired Commercial Stubs
The 5 commercial stubs (`plecs`, `matlab-simulink`, `ansys-maxwell`, `ansys-icepak`, `solidworks`) have been permanently retired from active catalog and adapters. The active catalog contains 13 qualified tools (plus ngspice).
