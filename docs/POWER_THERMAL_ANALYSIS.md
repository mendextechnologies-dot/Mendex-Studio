# Power loss and thermal analysis

Implemented 16 November 2026. Open a revision's **Calculations** or **Designs** section, then **Power Loss & Thermal Analysis**. This is an analytical comparison workflow, not an IPOSIM connector or an Infineon-qualified model library.

The light-theme workspace separates **Conditions**, **Devices**, **Sweeps** and **Advanced** settings. Start with Conditions, attach models under Devices, then set sweep ranges. The working-point summary and Calculate button stay beside the setup on wide screens and move below it on narrower panels. Import/export controls are in the toolbar; full JSON editing is under Advanced. Switching setup tabs preserves entered values.

## What is available

- Compare one to five explicitly sourced device models at one operating point.
- Per-device conduction/switching loss breakdown, represented-system efficiency, junction temperature and thermal margin.
- Load, switching-frequency and ambient/case boundary sweeps with efficiency, loss and temperature graphs.
- Complete-path Foster thermal impedance graphs and load-cycle temperature/loss graphs, repeated profiles and configurable time resolution.
- Zoom using axis bounds, two x cursors, nearest-sample inspection and individual SVG chart export.
- SI loss-table CSV import, complete request JSON import/export, result CSV and complete result JSON exports. Blank templates contain no invented semiconductor ratings.
- Conditional fatigue calculation using sourced power-cycling curves and externally counted thermal cycles. Missing or inapplicable lifetime data remains NOT_EVALUATED.
- Same core service from desktop, CLI and MCP; optional durable storage through the existing guarded calculation-record API.
- Automatic recalculation after 500 ms of input inactivity, with stale-response suppression and an optional manual mode.
- Voltage-dependent loss tables and exact part-number binding to saved revision BOM/core-design components.

## Dynamic updates and component replacements

**Automatically recalculate** is enabled by default. Complete the operating point, device models, assumptions and all three sweep lists first. Editing applied numeric/model inputs then recalculates the graphs after a 500 ms typing delay. Previous results clear when inputs change; an older response cannot overwrite a newer request. Raw JSON/CSV edits take effect after Apply/import. Previews never automatically create records, run native solvers or approve a design.

To follow a physical part, choose **Follow revision component**, and supply the model's exact mpn and manufacturer. Component identities are read only from bom/bom.json and active saved IR explicitly associated with that product/revision. Missing identities, disagreements between BOM and design, removed parts, missing models or ambiguous models remain NOT_EVALUATED; the old component's calculated values are not reused.

Use **Keep this model for component replacements**, the replacement-library JSON editor, or imported inputs to build model_library. Models require the same complete sourced electrical/thermal inputs as comparison devices. When the bound part changes, the core selects an exact matching model from that library. Explicit power_thermal_model data embedded in the current BOM row or IR component parameters takes precedence. Binding matches exact part numbers/manufacturers case-insensitively, never device families or descriptions. The UI labels bound models by reference and current part number.

Updates follow the application's existing revision refresh, not a new filesystem watcher. Changes made inside a native schematic editor must first be saved and imported/forward annotated into the core design/BOM. Unsaved or unimported KiCad edits are not observed. Switch current, switched voltage, duty, cooling and quantity remain explicit inputs: the application does not equate input voltage with device blocking voltage or infer switch current from output current.

The context includes source hashes, specification hash and binding-implementation hash. A changed component context invalidates a previous preview for recording; existing calculation history is marked effectively stale without rewriting its original inputs/results. Each reference can be bound only once per comparison. Preview and recording remain separate operations.

## Data that must be supplied

For each device, enter a name, source reference (datasheet revision/page or measured dataset), gate conditions and an explicit description of loss terms included/excluded. Enter reference switching voltage, valid frequency range and maximum junction temperature. Gate conditions must exactly match the operating point's gate_conditions; matching text is a caller declaration, not independent verification.

Legacy single-voltage loss CSV uses these headers:

```csv
current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j
```

Supply a complete current × temperature grid with at least two distinct currents and two temperatures, no duplicates, and nonnegative on-voltage/energies. Values are SI: amperes, Celsius, volts and joules. Use on-voltage versus current for MOSFETs, IGBTs or other explicitly characterized switches. Legacy tables use bilinear interpolation and remain valid only at their reference voltage.

For voltage-dependent results, add voltage_v to every CSV row (or every loss_points object). Supply a complete voltage × current × temperature grid, including at least two distinct voltages for interpolation. The service uses trilinear interpolation between supplied samples. Reference voltage must lie within the grid; mixed rows with/without voltage, incomplete grids and duplicates are rejected. No voltage extrapolation or gate-condition scaling is inferred. Out-of-range points are visibly NOT_EVALUATED and leave gaps in graphs. Changing operating voltage recomputes all applicable losses, efficiency, thermal balance and profile results using those tables.

Thermal branches are JSON objects with resistance_k_w and tau_s:

```json
[{"resistance_k_w": null, "tau_s": null}]
```

Replace nulls with sourced positive numbers. Supply thermal_source and select a fixed ambient or fixed case boundary. Branches must fit the **complete junction-to-that-boundary path**. Do not concatenate separate junction-case and heatsink Foster networks. Each compared device and each quantity instance has independent identical cooling; shared-heatsink and mutual heating are excluded.

The operating point requires voltage_v, gate_conditions, current_a, output_power_w, duty_cycle, frequency_hz, boundary_temp_c, other_losses_w and quantity. current_a is constant current **during the conduction interval**, not arbitrary output current or full-period RMS. Duty is strictly between zero and one; this workflow represents an actively switching device position. Zero switching frequency or disabled operation requires another model. other_losses_w must explicitly account for losses outside the modeled position, including magnetics, other switch positions, control and gate drive as applicable. It is held fixed during load sweeps; edit it or supply explicit profile segments when that assumption is unsuitable.

Sweeps require explicit lists: load_factors, frequencies_hz and boundary_temperatures_c. Load factors scale both modeled current and output power. Each chart labels the thermal boundary; comparing case-controlled and ambient-controlled models does not represent identical cooling conditions.

## Equations and numerical boundaries

For the stated constant-current approximation:

```text
Pcond = I × Von(V,I,Tj) × duty
Psw   = (Eon(V,I,Tj) + Eoff(V,I,Tj)) × frequency
Tj    = Tboundary + Pdevice × sum(Rbranch)
Ploss_represented = quantity × Pdevice + other_losses
efficiency = Pout / (Pout + Ploss_represented)
Zth(t) = sum(Rbranch × (1 - exp(-t/tau_branch)))
```

Steady-state thermal/loss feedback is solved within the provided temperature grid and junction limit. Unbounded, unstable or unsupported solutions are not returned as valid temperatures. The implementation conservatively rejects a model range containing nonnegative thermal-balance slopes.

Load-cycle models start cold at the fixed boundary and use loss-averaged steps with exponential Foster updates and implicit endpoint loss/temperature coupling. Increasing samples_per_segment checks convergence when losses vary with temperature. This is not switching-resolved temperature ripple, a circuit solver or a 3D thermal solution. The reported sampled_temperature_ripple_k is the entire cold-start profile span, not a claim of periodic steady-state ripple. A failing profile is marked NOT_EVALUATED rather than silently returning a successful prefix.

## Mission profiles and fatigue

The advanced request editor supports:

```json
{
  "load_cycle": [
    {"duration_s": null, "current_a": null, "output_power_w": null,
     "frequency_hz": null, "duty_cycle": null, "other_losses_w": null}
  ],
  "repeat_cycles": 1,
  "samples_per_segment": 10,
  "thermal_cycles": [],
  "cycle_count_source": null
}
```

Replace nulls with explicit operating data. Profiles support up to 200 segments, 10 repetitions and 50 samples per segment, capped at 5,000 samples per device. Mission conditions keep voltage, gate conditions and thermal boundary fixed. Time steps describe changing current, duty, output power, frequency and other losses. Supply the complete request rather than this partial fragment when importing JSON.

Each device may provide fatigue with source, conditions, mean_temp_min_c, mean_temp_max_c, heating_time_min_s, heating_time_max_s and curve. Curve entries contain delta_t_k and cycles_to_failure. Supply thermal_cycles separately: delta_t_k, mean_temp_c, heating_time_s, count and conditions, plus cycle_count_source. Conditions must match the fatigue model. The service checks temperature-swing bounds, mean-temperature/heating-time applicability and the device junction limit. It interpolates the curve in log-log space, computes Miner damage sum(count/Nfailure), and reports equivalent repeated supplied cycle blocks to damage one. It does not estimate calendar years or remaining life.

Automatic rainflow cycle counting, proprietary Infineon lifetime algorithms, device characterization, manufacturer model downloads and SPICE-to-PLECS model generation are not implemented by this feature. Existing LTspice waveforms remain available separately. A user-provided fatigue estimate remains CALCULATED and engineering NOT_EVALUATED.

## Interfaces and provenance

```powershell
mendex --root C:\path\to\disposable-data power-analysis C:\path\to\analysis.json --revision REVISION_UUID
```

Omit --revision for a standalone analytical run. CLI writes result JSON to stdout; errors return nonzero. The desktop routes analyze_power_thermal to StudioService.analyze_power_thermal. The read-only preview attaches revision ID and current specification hash but never silently substitutes project specifications for explicit analysis inputs. Preview/export does not write to frozen revisions or create engineering approval.

CLI `power-components REVISION_UUID`, MCP `get_power_analysis_context` and desktop `power_analysis_context` expose the same read-only component snapshot. MCP `run_engineering_calculations` additionally accepts revision_id for power_thermal previews. Standalone bound calculations without revision context remain NOT_EVALUATED. expected_component_hash is an optional optimistic-concurrency token in AnalysisRequest; resolved previews retain it for guarded recording. The additive model_library/component_reference/mpn/manufacturer/voltage_v fields preserve legacy single-voltage input compatibility.

MCP: run_engineering_calculations with calc_type=power_thermal and params equal to AnalysisRequest. Discover the full input schema through list_supported_calculations. For durable stage-bound records, use the existing engineering record_calculation_run operation with calculation=power_thermal, source/reason, assumptions, draft revision, stage, expected input hash and idempotency key. The desktop offers the same guarded append operation under **Record this calculation against a lifecycle stage**. Choose a current IN_PROGRESS stage and supply source/reason. The service retains canonical parameters, results, implementation hash, context and retry receipt, and rejects archived writes. Exported result files are user downloads; they are not automatically registered raw evidence. No lifecycle stages are automatically started or approved.

The request SHA-256 identifies canonical validated inputs. Model source strings are attribution, not proof of accuracy or manufacturer authorization. Output execution status COMPUTED is distinct from evaluation_status=NOT_EVALUATED. Missing values are never replaced by example component data.

## Validation and limits

Synthetic software benchmarks check 5 W conduction + 2 W switching, coupled temperature balance, complete-path first-order RC response, device comparisons, unsupported domains, invalid/NaN inputs, strict CSV parsing, conditional fatigue, CLI/desktop/MCP parity and archived-record rejection. These fixtures are explicitly synthetic and are not shipped as selectable parts. No physical semiconductor qualification was performed.

The implementation adds no dependencies and does not restore the retired PLECS integration. It supplies the requested five analysis/graph workflows using explicit analytical models. It does not claim complete IPOSIM topology coverage or vendor-dataset parity. Desktop transport retains its existing request-size limit; reduce large device grids or run the CLI for inputs exceeding that limit.

Validation on 16 November 2026: 59 selected tests passed, including genuine CLI, MCP stdio and desktop stdio subprocesses; TypeScript/Vite production build passed. Test results: docs/audit/evidence/power-thermal-20261116-tests.xml. The default system Python lacks pytest; use the existing project interpreter `.venv/Scripts/python.exe`. No installation was performed. Interactive browser verification was unavailable (browser discovery returned no sessions). No native desktop installation or interactive acceptance is claimed.

Dynamic-update milestone: **81 selected tests passed** and TypeScript/Vite build passed. Coverage adds voltage-interpolation numerical benchmarks, replacement/removal/conflict/ambiguity cases, foreign-revision isolation, current embedded-model selection, CLI/MCP scoped previews and stale-history/recording guards. Regression evidence: docs/audit/evidence/power-dynamic-20261116-tests.xml. Interactive debounce/refresh behavior has not been browser-observed because the supported browser runtime is unavailable.

The two changed/new contracts were checked against their canonical models. The broader pre-existing contract check reports unrelated drift in contracts/v3.1/records.Requirement.schema.json, which was preserved rather than overwritten. Vite also reports the existing bundle-size warning; build exit is zero.

Primary references: [Infineon IPOSIM guide](https://www.infineon.com/assets/row/public/documents/24/68/infineon-iposim-gettingstarted-en.pdf), [Infineon IGBT loss calculation](https://www.infineon.com/assets/row/public/documents/faq/igbt-power-losses-calculation-using-the-data-sheet-parameters.pdf), [thermal subsystem/Foster limitations](https://arxiv.org/abs/0801.0817).
