# SV-1000 compact feasibility review

Date: 11 November 2026, Asia/Calcutta. Scope: existing product evidence, proposed space budget and sourced component candidates. **Verdict: compact design feasibility NOT YET ESTABLISHED; existing files are unsuitable for prototype fabrication.** Electrical, insulation and thermal performance remain **NOT_EVALUATED**.

The owner selected a smaller enclosure and authorized best-choice engineering proposals. The working target is 21–28 V DC input, positive adjustable output up to 1,000 V at a maximum 1 mA continuous, and a 45 × 28 × 13 mm external enclosure. The generic instrumentation load is provisional. The existing 1.10 mV peak-to-peak ripple requirement is retained, not claimed as achieved. This review does not change topology, create approvals or release manufacturing files.

## Evidence that changes the readiness conclusion

The repeatable audit is [scripts/sv1000_compact_feasibility.py](../../scripts/sv1000_compact_feasibility.py). Its outputs are in [reports/sv1000-compact-feasibility-20261111-verified](../../reports/sv1000-compact-feasibility-20261111-verified/). Product and revision IDs are retained in `application-assessment.json`.

| Item inspected | Observed result | Consequence |
|---|---|---|
| Existing KiCad board | Outer Edge.Cuts rectangle 50 × 32 mm; inner rectangle 5 × 28 mm; **0 footprints, 0 tracks, 0 vias** | Does not fit the external enclosure; is an outline, not an implemented converter layout |
| Existing KiCad schematic | **0 symbols, 0 wires** | A clean ERC report cannot demonstrate circuit correctness on this empty design |
| Existing STEP solid | Native FreeCAD read: **22 × 22 × 16 mm**, valid solid | The cylindrical bobbin is taller than the complete enclosure; valid CAD does not mean package fit |
| Circuit model | `V_OUT_IDEAL 11 0 DC 1000V`; **0 coupled-inductor statements, 0 diode statements** | Output is supplied by an ideal source, not the proposed transformer/multiplier; cannot establish conversion performance |
| Existing waveform, reused application parser | 22,363 points; V(11) mean 1,000 V and peak-to-peak 0 V; V(10) mean approximately 990.099 V | These are outputs of the ideal-source model. They do not verify a real converter or the claimed 0.85 mV ripple |
| Existing native simulation log | Reports ignored MOSFET model parameters | Replace with sourced appropriate device models before a representative solve |
| Shared core `validation_summary` | All **5** records return `not_evaluated`, stale specification and failed evidence integrity | Existing recorded PASS values are not effective validation evidence |
| Lifecycle assessment | Returns `prototype_ready=true` despite those five effective statuses | Lifecycle approvals currently override substantive evidence; the badge is not accepted by this independent audit |

The existing `scripts/unblock_sv1000.py` explains the mismatch: it writes the empty schematic and board, inserts an ideal output source, assigns validation values as literals (including 0.00085 V ripple) and records every stage approval with generic reviewer names. Its successful solver process is real, but its numerical PASS and reviewer claims are not derived from verified product engineering. **Do not rerun that script to establish readiness.** Its source is preserved and hashed by this review; no historic records or raw evidence were edited or deleted.

The record provenance must be reviewed with the owner. A later software correction should bind reviews to exact inputs/evidence and prevent stale or damaged evidence and empty CAD from yielding readiness. Such a correction is a separate application change; this report does not silently revoke or fabricate any reviewer's sign-off.

## Dimensioned packaging proposal

See [space concept SVG](../../reports/sv1000-compact-feasibility-20261111-verified/compact-space-concept.svg) and [rendered PNG](../../reports/sv1000-compact-feasibility-20261111-verified/compact-space-concept.png). The diagram represents geometric reservations, not a final footprint placement or verified HV barrier. Canonical budget values are in metres in `packaging-assumptions-si.json`; this table uses millimetres for reading.

| Budget | Proposed value | Basis / limit |
|---|---:|---|
| External enclosure | 45 × 28 × 13 mm | Owner-selected target |
| Wall thickness | 0.5 mm on each face | Planning assumption; enclosure not selected |
| Internal cavity | 44 × 27 × 12 mm | Outside minus two walls on each axis |
| Candidate PCB | **42 × 25 × 1.0 mm** | Leaves 1 mm mechanical gap to each internal side wall |
| Bottom mechanical allowance | 1.0 mm | Must accommodate insulation, mounting and trimmed leads; not yet verified |
| Top mechanical allowance | 1.0 mm | Includes mechanical/potting reservation only; not an approved electrical clearance |
| Component height above PCB | **9.0 mm maximum budget** | 12 − 1 bottom − 1 PCB − 1 top |
| Transformer study reservation | **21 × 17 × 8.5 mm** | Conservative provisional block for an EFD15-family study, not guaranteed assembled fit |
| PCB area | 1,050 mm² | 34.375% less than the existing 1,600 mm² outline |

With a 1.6 mm board instead of the proposed 1.0 mm board, component height falls to 8.4 mm. The 8.5 mm transformer reservation would then exceed that height budget. Manufacturing tolerances, clips, winding bulge, insulation tape, connector exits and potting must be included before finalizing the stack.

**The existing three-zone arrangement is not resolved by scaling the board down.** An illustrative side-by-side arrangement of a 21 mm transformer width, 5 mm continuous barrier band and a 10 mm HV region requires 36 mm, exceeding the 25 mm candidate board width. This disproves that specific arrangement, not every possible compact architecture. Longitudinal partitioning, a properly insulated transformer crossing a designed barrier, or another package must be evaluated. The owner's 5 mm slot proposal has not been silently waived. Neither that slot width nor the assumed wall gaps establish creepage, clearance or isolation compliance.

The drawing's small HV block is an unproven space allocation. It does not demonstrate enough room for the full eight-stage ladder, output filtering, feedback, discharge components and their separations. Do not use it as fabrication input.

## Component and architecture shortlist

These are **candidates for a trade study**, not a procurement BOM. Exact package, temperature grade, availability, models, derating and footprint still require checking. No purchasing was performed.

| Role | Candidate / disposition | Source-supported facts and remaining work |
|---|---|---|
| Regulated flyback controller | **ADI LT3751EUFD family**, study candidate | 4 × 5 mm QFN option; feedback regulation and no-load capability. Operating VCC 5–24 V requires an auxiliary rail for this 21–28 V source. Overall 1 kV regulation range, noise and minimum output remain unverified. [ADI](https://www.analog.com/en/products/lt3751.html) |
| Compact magnetic assembly | **TDK EFD15/8/5, N87**, B66413 core family with B66414 accessories, study candidate | Supplier offers gapped N87 options and SMD former B66414B6008T001. Family dimensions justify studying the small reservation; exact former/clip/cover/insulated winding fit remains open. A core alone is not a qualified 1 kV transformer. Gap, turns and winding construction are deliberately not selected from packaging alone. [TDK core/accessory datasheet](https://www.tdk-electronics.tdk.com/inf/80/db/fer/efd_15_8_5.pdf), [assembly selector](https://www.tdk-electronics.tdk.com/download/531634/93a453e1deebd4d66795abc4c18fd5c4/pdf-selectorguide.pdf) |
| Larger magnetic alternative | **TDK EFD20/10/7**, compare then likely exclude from this height stack | Selector assembly envelope about 24.3 × 22 × 10 mm above mounting plane; 10 mm exceeds the proposed 9 mm height budget. Alternative mounting would require a separate envelope. [TDK selector](https://www.tdk-electronics.tdk.com/download/531634/93a453e1deebd4d66795abc4c18fd5c4/pdf-selectorguide.pdf) |
| Controller auxiliary supply | **ADI LT3014**, conditional candidate | 3–80 V input, 20 mA output capability. Must first budget controller quiescent current and gate-charge current, check dissipation and transient current. It is not selected for the main 1 W power path. [ADI](https://www.analog.com/en/products/LT3014.html) |
| Precision feedback resistor family | **Vishay TNPV e3**, comparison candidate | Different packages have different operating-voltage limits; family resistance range does not supply a single 100 MΩ part. Divider current, high-value alternatives, voltage coefficient and series footprint must be evaluated before selection. [Vishay](https://www.vishay.com/en/product/28881/) |
| Existing rectifier | **BYG23T: reject the claimed 1.5 kV rating** | Current Vishay BYG23T-M3 documentation gives 1,300 V repetitive reverse rating and 75 ns maximum reverse recovery under stated conditions. The old E3 BOM designation must be checked against its exact datasheet. Neither rating establishes adequate reverse margin in the final circuit. [Vishay](https://www.vishay.com/docs/89429/byg23t.pdf) |
| Existing switch | **BSC014N04LS: do not carry forward by default** | Supplier lists 40 V VDS maximum and a 5 × 6 mm package. Input plus reflected transformer voltage and leakage transients must determine the required rating. Existing ideal/unsupported MOS model is not this device's validation. [Infineon](https://www.infineon.com/cms/en/product/power/mosfet/n-channel/bsc014n04ls/) |
| HV rectifier/capacitor final parts | **TBD after topology and stress budget** | Existing capacitor description ambiguously calls one part 4.7 nF / 10 nF; no primary-source evidence for that exact claimed 2 kV part was established. Do not reuse its rating or price as verified. Need working voltage, peak reverse stress, leakage, capacitance under DC bias, temperature, pad geometry and model provenance |
| Commercial benchmark | **XP Power CA10P**, benchmark only, not a drop-in fit | CA family package 44.45 × 28.29 × 12.70 mm already exceeds the external width target before enclosure clearance; uses 12 V nominal input. Published CA10P ripple class is <0.001%, not evidence of the project's 1.10 mV target. [XP Power datasheet](https://www.xppower.com/storage/portals/0/pdfs/SF_CA_Series.pdf) |

The lead custom candidate remains a **regulated flyback**, with driven push-pull plus a modest multiplier retained for the noise/turns-ratio comparison. Fixed 100 kHz ZVS, an eight-stage ladder, MCU and isolated RS-485 are existing requirements/proposals requiring review; this trade study has not removed them from the canonical specification. The first hardware architecture should prioritize power conversion, regulation and hardware protection; communications packaging can be budgeted separately without pretending it fits.

## Calculation and modelling work to complete next

1. Establish applicable working isolation, output reference, pollution/installation conditions and insulation construction. Do not infer these from “2.5 kV hipot” or an administrative sourcing-policy reference in the existing standards profile. Qualification remains unavailable until this is resolved.
2. Select a specific core/material, gap option, bobbin, insulated winding construction, allowable maximum duty and design temperature using traceable data. Obtain a dimensioned winding feasibility proposal. Project engineering rules require these inputs before transformer design execution.
3. Compare flyback and driven push-pull concepts on attainable turns, insulation volume, rectifier stress, output capacitance and feedback range. Reject unsupported “ZVS” or resonant-frequency claims rather than carrying literal values into approval records.
4. Build a complete connected model with sourced device data. Planned input corners: 21, 24 and 28 V; resistive load cases: no external load, 10 MΩ, 2 MΩ and 1 MΩ. These represent resistance, not constant 1 mA across the full setpoint range. Define load/cable capacitance sensitivity and setpoint/startup transients explicitly. No product simulation was run in this feasibility review.
5. Declare the ripple measurement bandwidth, settling window, sample resolution, load and probe network before judging the 1.10 mV target. A clean ideal-source waveform cannot satisfy that test. Include feedback, filter voltage drop and divider/discharge loading.
6. Generate a real schematic/BOM and reviewable footprint placement with the complete insulation geometry. Execute actual ERC/DRC only after the circuit and layout exist. Keep physical/HV testing separate from simulation; no prototype fabrication approval is implied.

## Preservation and verification

- Product-file SHA-256 inventories before and after the audit match. The existing raw data, archived baselines, drawings, validation records and approvals were preserved.
- Native FreeCAD read verified the existing solid's bounds; no CAD regeneration or editing occurred.
- Existing waveform data was parsed through the project parser; no simulator or hardware execution was performed.
- Application data was inspected through the shared core service. No alternate business-rule implementation was introduced in UI or CLI.
- Packaging arithmetic, SVG render and report consistency were checked. Relevant core and UI lifecycle tests: **7 passed in 2.75 s**. Results are also recorded in the implementation checklist. Software tests do not validate the converter.
- Reproduce with `.venv\Scripts\python.exe scripts/sv1000_compact_feasibility.py --output reports/<new-audit-folder>` from the repository root. Output must be a new report directory. Native STEP read remains NOT_EVALUATED if FreeCAD is unavailable or fails.

**Decision:** retain the compact external target for a bounded study, use the 42 × 25 mm candidate board and EFD15 family as starting reservations, and do not treat the current ready badge as product evidence. No final claim that a compliant, low-noise 1 W converter fits this enclosure is supported yet.
