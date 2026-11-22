# HFT-000 draft core assembly - 18 November 2026

Current update: **R002** is active with the dedicated core/support assembly
workflow; R001 below is preserved history. Current revision ID:
`61f3fd21-5ada-4223-8d7b-14d8b0eb2ba6`. See
`docs/CORE_ASSEMBLY_WORKFLOW.md` for the separate lifecycle, editable mechanical
definition and Fit decisions view. No electronics/PCB workflow is applied to R002.

Created through `StudioService` in the default local Mendex data root. Product ID
`6c7982ac-45e0-4f98-bb8a-9cc666ab84d8`; active draft R001 revision ID
`6ba0957a-4d2f-4bc8-9d5f-d3aa85edd363`.

User-confirmed scope is the core and PTFE support assembly only. Supply includes
48 installed ferrites and 24 spare ferrites; 55 PTFE spacers comprise 45 installed
and 10 spares. Windings and electrical transformer design are outside scope.

The revision workspace contains 21 sourced requirements, an eight-line JSON/CSV
supply BOM, six unchanged source PDFs with SHA-256 manifest, an open-issues list
and a draft dimensional/document inspection plan. These files appear through the
existing desktop project projection; no application code changes were required.
Thirteen current artifacts and a current requirements snapshot are registered
through the core engineering-record service. Earlier append-only snapshots remain
historical and correctly become stale after the user clarified the specification.
Only administrative project initialization is complete; requirements remain in
progress. All requirement verification remains NOT_EVALUATED.

Source directory: `C:\projects\Power Electronics\Transformer`. Original PDFs and
their revision copies were checked byte-for-byte by SHA-256. A SQLite online backup
was taken before product creation. Existing product baselines were not edited.

Pending inputs:

- Native STEP file, which the user will supply later.
- Exact ferrite manufacturer/part, dimensional tolerances, material certificate,
  and documented equivalence if the material is not Ferroxcube 3F4.
- PTFE grade, stainless steel fastener grade, controlled drawing revision and
  governing tolerance hierarchy.
- Retention/clearance decision: nominal stack is 415 mm, inferred support opening
  420 mm. The 5 mm residual is document arithmetic, not a qualified fit result.
- Responsible engineer and required customer inspection/documentation details.

Verification: desktop project read-back, requirement/BOM counts, current record
integrity and source hashes passed. Relevant local regression tests:
`tests/core/test_service.py`, `tests/core/test_engineering_records.py`, and
`tests/core/test_bom_export_integrity.py`: **42 passed in 23.30 s**. Desktop visual
interaction was not exercised. No solver runs, physical results or manufacturing
acceptance were created.

## Received STEP parts and datasheet - 18 November 2026

Imported four STEP parts and `data Sheet.pdf` as new hash-indexed sources, preserving
all 14 previously existing revision files. Ten new artifacts and a new requirements
snapshot were recorded through the core service and verified through desktop read-back.
The original BOM remains unchanged; the supplied datasheet documents reference
candidate Ferroxcube T107/65/25-3F4, without establishing actual supplied-lot identity.

Read-only FreeCAD 1.1.4 inspection imported each STEP as one valid solid. Checked
nominal envelopes, limb/spacer diameters and selected hole/seat locations agree with
the corresponding PDFs. Assembly STEP and ferrite geometry remain absent; full
assembly interference, thread engagement and physical fit are NOT_EVALUATED.

Two fit issues require resolution:

- Datasheet minimum ferrite bore is 63.7 mm; drawing limb OD is 63.9-64.0 mm.
  Minimum diametral clearance is -0.3 mm: interference is possible.
- Sixteen cores at 25 +/-0.75 mm plus fifteen nominal 1 mm spacers span 403-427 mm.
  Relative to the inferred nominal 420 mm support opening, clearance spans +17 to
  -7 mm before other tolerances. The nominal 5 mm allowance does not guarantee fit.

Detailed review, original source manifest, geometry extraction and inspection script
are in revision `validation/document-review-20261118/`. No original CAD was altered.
Certificate, actual ordered part, material grades, retention strategy and responsible
engineer remain outstanding. Requirement verification stays NOT_EVALUATED.
