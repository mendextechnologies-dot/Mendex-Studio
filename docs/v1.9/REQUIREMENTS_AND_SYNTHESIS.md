# MENDEX ENGINEERING STUDIO v1.9 — REQUIREMENTS & SYNTHESIS ENGINE

## 1. Specification & Requirements Engine

The requirements engine validates design inputs against strict physical boundary conditions before candidate generation:

1. **Validation Checks**:
   - $V_{in,\min} \le V_{in,\text{nom}} \le V_{in,\max}$ (Voltage consistency).
   - $V_{out} > 0$, $I_{out} > 0$, $P_{out} > 0$ (Physical non-negativity).
   - $f_{sw} \ge 10\,\text{kHz}$ (Frequency sanity).
2. **Missing Input Identification**:
   - Critical parameters missing from user input (e.g. unstated voltage rating or missing load requirements) are flagged as `MISSING` rather than invented.

---

## 2. Deterministic Candidate Synthesis

The `CandidateSynthesisEngine` screens topologies through analytical rules:

| Topology | Isolation | Voltage Range | Power Range | Screening Rule |
|---|---|---|---|---|
| **Synchronous Buck** | Non-isolated | $V_{in} > V_{out}$ | $1\,\text{W} - 1\,\text{kW}$ | Selected when isolation is not requested and $V_{in} > V_{out}$. |
| **Discontinuous Flyback** | Isolated | Wide range ($V_{in} \lessgtr V_{out}$) | $1\,\text{W} - 150\,\text{W}$ | Selected for galvanic isolation and medium-to-low power. |
| **Push-Pull / Forward** | Isolated | Medium/High input | $50\,\text{W} - 500\,\text{W}$ | Selected for higher power throughput and symmetrical core drive. |

### First-Order Design Calculations
For each candidate, the synthesis engine computes:
- Nominal and maximum duty cycle ($D$).
- Critical inductance ($L_{crit}$ or $L_m$).
- Peak switch voltage stress ($V_{ds,pk}$) and current stress ($I_{pk}$).
- Estimated converter efficiency ($\eta$) based on semiconductor and copper loss approximations.
