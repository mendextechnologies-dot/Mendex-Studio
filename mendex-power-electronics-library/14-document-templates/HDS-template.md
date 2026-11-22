# Hardware Design Specification (HDS) Template

**Document ID:** MPECL-HDS-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Hardware Design Lead:** `[Name / Title]`  

---

## 1. Circuit Topology & Sizing Calculations
* Detailed working schematic topology.
* Mathematical sizing formulas:
  - Inductor selection: $L = \frac{V_{out} \cdot (1 - D)}{r \cdot I_{out} \cdot f_{sw}}$
  - Capacitor selection: $C_{out} \ge \frac{\Delta I_L}{8 \cdot f_{sw} \cdot \Delta V_{out}}$
  - Switch power dissipation calculation: $P_{total} = P_{cond} + P_{sw,on} + P_{sw,off} + P_{gate}$

---

## 2. Component Selection & Stress Derating Audit
| Component Ref | MPN | Manufacturer | Absolute Rating | Applied Stress (Worst-Case) | Derating Factor | Compliance Status |
|---|---|---|---|---|---|---|
| `Q1` (High-Side FET) | BSC035N10NS5 | Infineon | $100\text{ V}, 100\text{ A}$ | $75\text{ V}, 22\text{ A}$ | $75\%$ Voltage, $22\%$ Current | PASS (Derated) |
| `C_out1-4` | 35SEF470M | Panasonic | $35\text{ V}, 4.2\text{ A}_{RMS}$ | $24\text{ V}, 2.1\text{ A}_{RMS}$ | $68\%$ Voltage, $50\%$ Ripple | PASS (Derated) |

---

## 3. PCB Layout Architecture & Layer Stackup
* Layer count, copper thickness, board material (FR4 / CTI 175).
* Loop area constraints and Kelvin sense routing verification.
* Creepage and clearance verification table (IEC 60664-1).

---

## 4. Heatsink & Thermal Dissipation Plan
* Calculated total full-load power dissipation: $P_{loss}$ in Watts.
* Thermal interface material (TIM) specification ($W/m\cdot K$).
* Heatsink thermal resistance ($R_{\theta,sa}$ in $^\circ\text{C}/W$) and required airflow (CFM).

---

## 5. Engineering Approvals & Signoffs
* Hardware Lead: `[Signature / Date]`
* Systems Architect: `[Signature / Date]`
