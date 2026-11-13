# 12. Engineering Calculations Validation

**Target:** Deterministic Physics Calculations (`DeterministicCalculationService`)  
**Status:** **PASS**

---

## 1. Analytical Formulations Audited

| Calculation Model | Governing Physical Formula | Input Parameters | Unit Validation |
|---|---|---|---|
| **Faraday Turns Ratio** | $N = \frac{N_s}{N_p} = \frac{V_{out}(1 - D_{max})}{V_{in,min} \cdot D_{max}}$ | $V_{in}, V_{out}, D$ | Strict SI Units ($V, \text{ratio}$) |
| **Primary Inductance** | $L_p = \frac{V_{in}^2 \cdot D^2}{2 \cdot P_{out} \cdot f_{sw}}$ | $V_{in}, P_{out}, f_{sw}$ | Strict SI Units ($H, \mu\text{H}$) |
| **Air Gap Length** | $l_g = \frac{\mu_0 \cdot N_p^2 \cdot A_e}{L_p}$ | $A_e, N_p, L_p, \mu_0$ | Strict SI Units ($m, \text{mm}$) |
| **Dowell 1D HF AC Resistance** | $F_r = \xi \left[\frac{\sinh 2\xi + \sin 2\xi}{\cosh 2\xi - \cos 2\xi} + \frac{2(m^2-1)}{3}\frac{\sinh\xi - \sin\xi}{\cosh\xi + \cos\xi}\right]$ | $f_{sw}, h, m, T, \sigma_{Cu}$ | Skin depth $\delta$, normalized $\xi$, $F_r$ ratio |
| **Steinmetz Core Loss** | $P_{core} = C_m f^\alpha B^\beta \cdot V_e$ | $f, B, V_e, C_m, \alpha, \beta$ | Volumetric & total dissipation ($W$) |
| **IEC 60664-1 Clearances** | Tabular lookup with altitude factor $k_d$ up to $5000\text{ m}$ | Voltage, Pollution Degree, Overvoltage Cat | Clearances in mm |
| **IPC-9592B Derating** | Percentage of rated voltage, current, and junction temp | $V_{applied}, V_{rated}, T_j$ | Stress percentage $\le$ limit |

All formulas operate deterministically without heuristic guessing. Zero simulated fabrication.
