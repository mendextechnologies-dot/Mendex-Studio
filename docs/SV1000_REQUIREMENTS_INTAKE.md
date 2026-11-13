# SpectraVolt SV-1000 — Word-based requirements intake

Status: **DRAFT / NOT APPROVED — Stage 2 AWAITING_REVIEW.**

The existing project `8f697275-3a8d-456c-ae20-138a7698df61` and initial revision
`R001` / `9b7c1396-64da-41f8-8649-77dc0f24e103` were reused.

The user's latest instruction selects
`C:\projects\Power Electronics\SpectraVolt_SV1000_Handbook.docx` as the specification
authority. Its SHA-256 is
`65f6941b2d058b9178f3ed22f31dca25618100d9b4df488f9e91d48cb952c3ef`.
The Markdown sibling was inspected for context but **not merged into the requirements**.
The Word rating of **1 W / 1 mA continuous** supersedes the earlier 100 W brief.
The optional 5 W rating remains unapproved. Proposed typed specifications are
21/24/28 V input, 1000 V positive full-scale, 1 mA maximum and 100 kHz, with
negative-variant semantics retained separately in the ERS. None is measured evidence.

The review covered 84 body blocks, including 19 table/layout blocks, and the
embedded Figure 1.0 image. The concept image is not a hardware test or a toleranced
drawing. LibreOffice is unavailable; rendered page numbers and page layout were
not verified. References therefore use exact module/block/table-row locators.

The package is in the existing R001 workspace at
`requirements/word-v3-9a0d99a5/` and contains:

1. `01_Product_Requirements_Specification.md`
2. `02_Electrical_Requirements_Matrix.md`
3. `03_Mechanical_Requirements_Matrix.md`
4. `04_Safety_and_Insulation_Requirements.md`
5. `05_Control_and_Communication_Requirements.md`
6. `06_Engineering_Assumptions_Register.md`
7. `07_Requirements_Conflict_Register.md`
8. `08_Verification_and_Validation_Matrix.md`
9. `09_Preliminary_Feasibility_Report.md`
10. `10_Stage_by_Stage_Development_Plan.md`

`ERS.json` and `requirements.csv` include every requested field, source text,
classification, human-readable requirement ID and canonical core ID. The original
Word document, complete extracted blocks and core calculation execution are also
preserved. No existing source or evidence was overwritten.

| Measure | Actual result |
|---|---:|
| Source-backed statements | 102 |
| Explicit handbook requirements | 22 |
| Proposed design choices | 43 |
| Statements classified conflicting | 23 |
| Engineering assumptions / unsupported source assertions | 8 |
| Source statements classified open decisions | 6 |
| Identified missing-information entries | 27 |
| Total ERS entries | 129 |
| Open conflict groups | 8 |
| Open decisions/risks, including conflict groups | 17 |
| Approved requirements | 0 |
| Entries with proposed verification methods | 129 |
| Simulations / physical tests executed | 0 / 0 |

Major unresolved items: 2 versus 4 PCB layers, PCB versus enclosure dimensions,
2 versus 5 mm slots, 0–5 versus 0–2.5 V monitors, component rating discrepancies,
isolation architecture, exact multiplier/magnetics model, negative-variant sensing,
measurement conditions, thermal budget and qualified HV laboratory procedures.

Manufacturer cross-checks retain source claims unchanged while recording independent
discrepancies: [Vishay BYG23T document 89429](https://www.vishay.com/docs/89429/byg23t.pdf),
[Dow SYLGARD 184](https://www.dow.com/en-us/pdp.sylgard-184-silicone-elastomer-kit.01064291z.html),
[Analog Devices ADM2587E Rev.H](https://www.analog.com/ADM2587E/datasheet).
These checks do not approve replacement parts or insulation distances.

Eighteen preliminary calculations ran through the existing core workflow engine,
workflow `0b19f7de-4094-4ba2-afd3-c076835ece3d`, execution
`a0552d15-0890-4e71-9857-ee0336eef2f1`. Results include the 1 W endpoint,
5.25 W low-line input-power upper bound, >95.238% necessary total efficiency for
the optional 5 W rating at low line, and 5/4 mm PCB dimensional overhang relative
to the stated external footprint. All idealizations are explicit; these are not
native simulations or safety acceptance results.

The ERS was persisted through `record_requirements`, record
`b3854877-972d-4c90-b7c8-92efcf214dbe`, and 15 artifacts were registered through
`register_engineering_artifact`. Separate MCP and desktop-backend readers confirmed
129 requirement entries and all 15 original/snapshot hashes. Actual screen rendering
remains **NOT VERIFIED**. The current core's strict ID schema uses lowercase
underscore IDs; the ERS retains the requested uppercase hyphenated display IDs and
their one-to-one mapping.

Stage 1 was reopened and completed after the specification-context change, preserving
its previous event history. Stage 2 is AWAITING_REVIEW; all later stages remain
NOT_STARTED. Stage 3 progression/completion is **BLOCKED** until conflicts and missing
conditions are resolved and qualified human review is available. Mendex's current
backend cannot authenticate engineering approval. No manufacturing release or
prototype energization is authorized.

Verification: 51 relevant lifecycle/record/interface tests passed in 10.60 seconds.
The live-record readback is separate from these isolated software tests. Execution
transcript and independent checks are retained in
`.mendex/agent-requests/SV-1000-9b7c1396-64da-41f8-8649-77dc0f24e103/ers-intake/`.
