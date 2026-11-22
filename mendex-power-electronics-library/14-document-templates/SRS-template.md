# System Requirements Specification (SRS) Template

**Document ID:** MPECL-SRS-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**System Title:** `[Insert System Title]`  
**Lead Systems Engineer:** `[Name / Title]`  

---

## 1. System Scope & Architecture Overview
* Technical description of how the system fulfills parent PRD requirements.
* Top-level functional block diagram linking power, control, safety, and connectivity platforms.

---

## 2. Quantitative Electrical Requirements (SI Units)
All electrical specifications must be declared in standard SI units with explicit tolerance bounds:

| Req ID | Parameter Name | Field Key (SI) | Min | Nominal | Max | Unit | Verification Method |
|---|---|---|---|---|---|---|---|
| `SRS-E-01` | Input Voltage DC | `voltage_in_v` | 18.0 | 48.0 | 75.0 | V | Test Procedure 1 |
| `SRS-E-02` | Output Voltage DC | `voltage_out_v`| 23.76| 24.00 | 24.24 | V | DVP Test 02 |
| `SRS-E-03` | Continuous Current | `current_out_a`| 0.0 | 20.0 | 25.0 | A | Test Procedure 2 |
| `SRS-E-04` | Full-Load Efficiency| `efficiency_pct`| 95.5 | 96.5 | - | % | Precision Power Analyzer |
| `SRS-E-05` | Output Voltage Ripple| `ripple_v_pkpk` | - | 35.0 | 50.0 | mV | Coaxial Scope Probe |

---

## 3. Dynamic Performance & Control Specifications
* **Crossover Frequency ($f_c$):** Target bandwidth in kHz.
* **Phase Margin (PM):** Minimum degrees ($^\circ$).
* **Load Step Recovery:** Maximum $\Delta V_{out}$ and settling time ($t_s$) for $20\% \to 80\%$ step.

---

## 4. Hardware Safety & Protection Thresholds
* **Overvoltage Trip Threshold:** $V_{ovp\_trip}$ in Volts ($< 2\,\mu\text{s}$ latency).
* **Overcurrent Trip Threshold:** $I_{ocp\_trip}$ in Amperes ($< 750\text{ ns}$ latency).
* **Thermal Shutdown:** $T_{otp\_trip}$ in $^\circ\text{C}$.

---

## 5. Traceability Matrix to Parent PRD
| SRS Req ID | Parent PRD Req ID | Verification Method (DVP Gate) | Effective Status |
|---|---|---|---|
| `SRS-E-01` | `PRD-F-01` | DVP-GATE-01 | NOT_EVALUATED |
| `SRS-E-02` | `PRD-F-02` | DVP-GATE-02 | NOT_EVALUATED |
