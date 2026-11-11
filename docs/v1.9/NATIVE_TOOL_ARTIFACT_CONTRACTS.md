# MENDEX ENGINEERING STUDIO v1.9 — NATIVE TOOL ARTIFACT CONTRACTS

## 1. Native Tool Compilers

The Studio compiles Design IR into validated native EDA and CAD files:

| Artifact Type | Generator | Output File | Verification Rule |
|---|---|---|---|
| **LTspice Netlist** | `LTspiceNetlistGenerator` | `<topology>_circuit.net` | Valid SPICE syntax, `.tran` statement, valid pin mappings |
| **KiCad Schematic** | `KiCadSchematicGenerator` | `<title>.kicad_sch` | KiCad 9 S-expression syntax, passes `kicad-cli sch erc` |
| **KiCad Project** | `KiCadSchematicGenerator` | `<title>.kicad_pro` | Valid JSON settings, track width and clearance definitions |
| **FEMM Script** | `FEMMMagneticGenerator` | `magnetic_simulation.lua` | Lua batch script, material parameters, boundary mesh commands |
| **FreeCAD 3D CAD** | `generate_freecad_bobbin_script` | `bobbin.step` | ISO 10303 STEP solid, valid watertight solid geometry |
