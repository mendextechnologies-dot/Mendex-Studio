# MENDEX ENGINEERING STUDIO v1.9 — ENGINEERING LIFECYCLE & BOM

## 1. 15-Stage Engineering Lifecycle

1. `REQUIREMENTS`: Signed baseline specification.
2. `ARCHITECTURE`: Selected topology candidate.
3. `ELECTRICAL_DESIGN`: Circuit netlists and component ratings.
4. `ENGINEERING_CALCULATIONS`: Sizing, area product, Dowell, losses.
5. `CIRCUIT_SIMULATION`: Real solver execution, waveforms, ripple.
6. `MAGNETIC_ANALYSIS`: FEMM FEA, flux density, core loss.
7. `SCHEMATIC_VERIFICATION`: KiCad ERC findings and pin integrity.
8. `PCB_DESIGN`: KiCad PCB layout and layer stackup.
9. `PCB_VERIFICATION`: KiCad DRC design rules and clearances.
10. `THERMAL_MECHANICAL`: FreeCAD 3D CAD STEP solid.
11. `BOM_SOURCING`: Component MPNs, ratings, procurement lifecycle.
12. `ENGINEERING_VALIDATION`: Multiphysics verification matrix.
13. `PROTOTYPE_READINESS`: Formal gate review sign-off.
14. `PHYSICAL_TESTING`: Oscilloscope traces, calibration records, RMSE.
15. `ENGINEERING_RELEASE`: Final production release dossier.

---

## 2. Bill of Materials (BOM) Control

- Maintains exact manufacturer part numbers (MPNs), packages, tolerances, and voltage ratings.
- Traced directly to the active `DesignRevision` and `IRComponent` records.
