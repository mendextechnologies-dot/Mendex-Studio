# Component and materials reference library

Updated 13 November 2026. This is a reference catalog, not engineering qualification or a comprehensive manufacturer database.

## Corrections

The React screen previously requested fields absent from the shared-core payload (`part_number`, `package_type`, `parameters`, `material_family`, `initial_permeability`, and renamed core dimensions). Numerical fallbacks then displayed identical material properties and core dimensions. The typed client and view now consume canonical `mpn`, `package`, individual rating fields, `material_type`, `initial_permeability_ui`, `saturation_flux_t`, `curie_temp_c`, `ae_mm2`, `le_mm`, and `ve_mm3`. Null means Unknown; there are no numerical substitutes.

N87 and N97 permeability and flux density are transcribed from TDK material sheets, with temperature, applied field, frequency, tolerance and Curie-temperature lower-bound notation retained. 3F36 flux density is recorded at 100 degrees C, not conflated with the TDK 25-degree values. KoolMu is a family with multiple permeability grades. 3C90 numeric seed data is withdrawn pending a material-specific source review. Legacy shape-only core names remain visible, with dimensions withdrawn pending exact manufacturer/order-code/core-set identification. No previously saved engineering evidence or frozen revision is rewritten.

Unsupported Steinmetz coefficients and uninstalled CAD/SPICE associations have been removed. The legacy Qt estimators and comparator retain NOT_EVALUATED when exact geometry or loss-fit parameters are missing; copying does not generate a calculated candidate from these records. The onsemi diode rating is 10 A per leg at the stated case temperature, with 20 A total distinguished in the conditions. The Wolfspeed device is labeled NRND according to its manufacturer page.

## Coverage and use

The packaged catalog has 20 component references (17 added), five material references and five geometry-only references. Thirty categories are supported: power semiconductors, controllers/drivers, sensing/isolation, passives/magnetics, protection/filtering, thermal and interconnect. Categories without sourced entries explicitly show zero; this is not a claim that every category has parts or that all power-electronics components are included.

Search part/family, manufacturer or description; filter by category and exact-part reference versus product family. Expand Conditions & models for limitations, missing footprints/symbols/models and rating conditions. Manufacturer links open separately. Family records require package, grade and ordering-suffix selection. Even part references require application review, thermal/SOA/derating checks and model qualification.

All qualification statuses remain NOT_EVALUATED. Source consultation is not independent verification, availability confirmation, safety certification or a design approval. Catalog metadata is packaged in `src/mendex_core/config/component_library.json`; `StudioService.components` loads it for the existing desktop transport and other core consumers. Stable UUIDs are derived from record kind, manufacturer and reference name. No schema migration or project import is performed. Restart the running app/backend to reload changes to this packaged catalog.

## Manufacturer sources

- [TDK N87 material sheet](https://www.tdk-electronics.tdk.com/download/528882/990c299b916e9f3eb7e44ad563b7f0b9/pdf-n87.pdf)
- [TDK N97 material sheet](https://www.tdk-electronics.tdk.com/download/187242/81166f0de556e5b6a94db7793daed936/pdf-n97.pdf)
- [Ferroxcube 3F36](https://www.ferroxcube.com/en-global/download/download/99)
- [Magnetics KoolMu family](https://www.mag-inc.com/products/powder-cores/kool-mu-cores)
- [Infineon BSC026N08NS5](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bsc026n08ns5-datasheet-en.pdf)
- [Wolfspeed C3M0065090D](https://www.wolfspeed.com/products/power/sic-mosfets/900v-silicon-carbide-mosfets/c3m0065090d/)
- [onsemi MBR20100CT](https://www.onsemi.com/pdf/datasheet/mbr20100ct-d.pdf)
- New records carry their own manufacturer URLs in the catalog and UI (TI, Infineon, Vishay, TDK, Coilcraft, Littelfuse, Schaffner, Wakefield Thermal and Phoenix Contact).

## Validation

The focused Python regression covers wire-field semantics, distinct material values/conditions, nullable properties, source links, stable identifiers, per-leg diode current, family and lifecycle labels, invalid/non-finite ratings, and legacy Qt behavior. The React server-render smoke script uses the actual core payload to render all three views and checks unknown values, manufacturer/status labels, missing geometry, and loading/error/empty/stale states. It disables Vite application configuration and never starts the Python bridge. Server rendering does not verify browser layout, interactions or external-link reachability.

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/core/test_component_reference_library.py tests/core/test_v19_design_synthesis.py::test_component_library_queries tests/ui/test_step4_magnetics.py tests/ui/test_switchloss_ui.py
# Working directory: desktop
node scripts/verify-component-library.mjs ../docs/v3.1/verification/component-library-20261113/payload.json
npm.cmd run build
```

Evidence: `docs/v3.1/verification/component-library-20261113/`. Rendered browser visual acceptance remains NOT_EVALUATED because the attached browser runtime reported no available browsers. The earlier whole-app recheck completed with 358 passed, 7 failed, 1 skipped and 1 teardown error; those unrelated failures are not a green application acceptance result (see `app-recheck-20261113-current.xml`). This catalog change does not claim to resolve them.
