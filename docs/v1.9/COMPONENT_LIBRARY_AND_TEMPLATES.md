# MENDEX ENGINEERING STUDIO v1.9 — COMPONENT LIBRARY & DESIGN TEMPLATES

## 1. Verified Component Library

The component library manages vetted hardware parts:

- **MOSFETs**: Rated by $V_{ds,\max}$, $I_{d,\max}$, $R_{ds(\text{on})}$, SPICE model, and KiCad footprint.
- **Diodes**: Rated by forward drop $V_f$, reverse voltage $V_r$, and current rating.
- **Magnetic Materials**: Rated by saturation flux density $B_{sat}$, initial permeability $\mu_i$, Curie temperature $T_c$, and Steinmetz coefficients ($C_m$, $\alpha$, $\beta$).

---

## 2. Reusable Design Templates

- **Non-Isolated Synchronous Buck**: Standard point-of-load converter with synchronous rectification.
- **Isolated Discontinuous Flyback**: Single-switch flyback with coupled inductor and snubbers.
- **Push-Pull Converter**: Center-tapped high-voltage isolated topology.
