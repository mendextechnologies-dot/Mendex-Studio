# MENDEX ENGINEERING STUDIO v2.0 — INTELLIGENCE READINESS SPECIFICATION

## 1. Principles of Engineering Intelligence

Mendex Engineering Studio v2.0 treats Engineering Intelligence as an engineering decision-support system, not a replacement for deterministic physics. The system operates under strict governance rules:

1. **Zero Hallucination / Zero Fabrication**: The intelligence engine never invents simulation numbers, component datasheets, or pass/fail verdicts.
2. **Deterministic Physics First**: All magnetic, thermal, and electrical calculations are rooted in peer-reviewed analytical models (Steinmetz equation, Dowell eddy-current model, area-product method).
3. **Traceability**: Every intelligence recommendation links directly to its underlying equations, dataset references, and input assumptions.

---

## 2. Integrated Intelligence Capabilities

### 2.1 Area Product Sizing & Transformer Design
- Computes core size $A_p$ based on switching frequency, flux density limit, current density, and power throughput.
- Selects optimal standard core geometries (e.g. EE, ETD, PQ, RM) with physical constraint validation.

### 2.2 Dowell AC Resistance & Proximity Effect
- Evaluates frequency-dependent AC resistance factor $F_R = R_{\text{ac}} / R_{\text{dc}}$ for multi-layer foil and round-wire windings.
- Recommends interleaving or Litz wire configurations when $F_R$ exceeds acceptable thresholds.

### 2.3 Steinmetz Core Loss Analysis
- Integrates with MagNet and MagNet ML Benchmark datasets to calculate volumetric core losses:
  $$P_v = C_m \cdot f^\alpha \cdot B_{\max}^\beta$$
- Validates temperature coefficient and frequency boundary limits.

### 2.4 Semiconductor Switching Loss Extrapolation
- Queries SwitchLossDB for turn-on energy ($E_{\text{on}}$), turn-off energy ($E_{\text{off}}$), and reverse recovery ($E_{\text{rr}}$).
- Extrapolates total semiconductor loss as a function of junction temperature and drain/collector current.

---

## 3. Engineering Advisory Sentinel

- **Design Review Sentinel**: Scans active workspace parameters and flags common power electronics pitfalls (e.g., flux walking in push-pull converters, excessive duty cycles, inadequate gate drive impedance).
- **Stale Evidence Sentinel**: Automatically detects when upstream circuit parameters or component values change after a simulation or PCB export was run, prompting the engineer to re-verify.
