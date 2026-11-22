# Core and support assembly workflow

Implemented 18 November 2026. This workflow covers ferrite cores, mechanical supports,
spacers, fasteners, supply quantities, dimensional requirements and document review.
It does not include windings, PCB design, power converter synthesis or manufacturing
approval. Missing inspection/qualification evidence remains NOT_EVALUATED.

## Application use

On a current draft project, use **Project workflow → Use core and support assembly
workflow**, supplying a new revision label. The application archives the former
revision and creates a draft with the separate, versioned seven-stage definition:

1. Project setup.
2. Assembly requirements.
3. Materials and supplier documentation.
4. Mechanical design and STEP parts.
5. Fit and tolerance review.
6. Dimensional inspection planning.
7. Assembly document review.

Only administrative setup is completed automatically. Every subsequent stage
requires recorded human review through the existing local attribution service;
review identity remains unauthenticated. Stage reviews do not approve a product or
authorize manufacturing. The review package omits irrelevant electronics voltage
and HV isolation checks for the explicit core profile. Missing assembly records or
undisposed fit decisions block the applicable mechanical/document reviews.

The dedicated project view has Overview, Requirements, Mechanical design, Fit
decisions, Inspection, Lifecycle and Files sections. It does not mount circuit,
PCB, Gerber, semiconductor, enclosure-synthesis or converter simulation controls.
Mechanical design supports sourced parts, quantities, material requirements,
native CAD links and dimensional limits. Dimensions display in mm and persist in m.
Fit decisions accept a user clarification and owner; this records a disposition,
not a passed physical check. Inspection documents open through the shared native
file launcher. Native STEP viewing uses the configured external CAD application;
an embedded STEP renderer is not implemented.

Saving creates a unique design JSON file and append-only artifact snapshot. Saves
require a current in-progress stage, expected specification hash, current design
digest, explicit source and reason. Linked CAD must be confined to the revision and
its hashes are bound to that design record. Missing/changed CAD or damaged snapshots
are reported by the design integrity view; engineering status remains NOT_EVALUATED.
An optimistic design digest prevents concurrent edits from overwriting each other.

## Shared core and contracts

`StudioService.core_assembly` owns `create_revision`, `overview` and `save_design`.
Desktop and CLI delegate to that service. `Specification.workflow_profile` is
`electronics` by default or explicitly `core_assembly`. Omitting the default profile
from specification hashing preserves all existing electronics evidence hashes.
The lifecycle assignment is immutable; selecting this workflow creates another
revision rather than changing a stored definition or historical events.

Workflow revision creation copies source files, retains the older revision, clears
requirement verification to NOT_EVALUATED, and records copied requirements in the new
context. A subsequent core revision carries its design definition but never inherits
review acceptance. Copy errors roll back the new revision and archival transaction.
Confined paths reject symlinks/junctions. The workflow itself requires a current draft
and matching specification context. No database schema migration was introduced.

CLI requests are JSON files, through the same service:

```powershell
mendex core-assembly show show-request.json
mendex core-assembly create-revision revision-request.json
mendex core-assembly save-design design-request.json
```

`show` takes `revision_id`; revision selection takes `revision_id`, `revision_label`
and `expected_input_hash`; design saving takes the strict `AssemblyWrite` contract.
Desktop methods are `core_assembly`, `create_core_assembly_revision`,
`save_core_assembly` and shared `apply_stage`. Additive schemas, current Specification
schema and the packaged lifecycle definition are under `contracts/core-assembly/`.
Regenerate/check with `scripts/export_core_assembly_contracts.py [--check]`.
Legacy checked-in schemas and raw evidence were not regenerated or rewritten.

## HFT-000 activation and verification

Active revision R002: `61f3fd21-5ada-4223-8d7b-14d8b0eb2ba6`. R001 remains archived
with its previous lifecycle and all 32 files unchanged. A SQLite online backup was
taken before activation. R002 includes eight supply lines, 21 sourced requirements,
nine recorded decisions, 23 sourced part dimensions and the four supplied linked
STEP parts. Spacer quantities remain 45 installed plus 10 spare. There are 48
installed ferrites plus 24 spare ferrites.

The earlier generic UI had also generated three enclosure STEP files. They remain
historical/inherited files, with explicit corrective provenance records; they are
not linked as the supplied transformer assembly geometry. All supplied source
PDFs/STEPs and earlier baseline files were preserved. No fit, material or inspection
decision was supplied by the implementation.

Validation: 94 tests passed across core assembly, service, engineering records,
lifecycle, reviews and desktop revision isolation. The TypeScript/Vite production
build and eight additive contract checks passed. The running localhost desktop RPC
returned R002, the seven-stage lifecycle and the intact design with four CAD hashes.
In-app browser discovery returned no browsers; interactive/visual verification was
unavailable. No native installer was rebuilt or deployed.
