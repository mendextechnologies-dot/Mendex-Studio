# PCB layout experiments — milestones 1–2 (20 November 2026)

Mendex provides first-party structural board analysis, drawn-geometry placement
checks and isolated candidates through `StudioService.pcb_layout`. This implementation does not import
code, models or datasets from `Ssbullock/pcb-layout-llm`, install KiCadRoutingTools,
or change the existing Copper routing path. No AI provider was added to the core.

## Desktop

For an electronics revision, open **Designs → PCB layout experiments**. Select a
native board from that revision's `pcb/` directory, then **Analyze board**. Expand
components/connectivity to inspect actual reference names, positions and pad nets.

For a populated draft, enter a rationale and create a snapshot candidate. On a
board without tracks, track arcs, vias or copper zones, select an unlocked
component, enter target X/Y in millimetres and add/replace a move. Multiple moves
can be queued or removed before creating a moved candidate. Footprint keepout zones
are preserved and checked, rather than counted as routed copper. Coordinates sent to
the core are metres. Rotations and layers are preserved; rotation/side changes
are not implemented. Archived/review revisions can be analyzed but cannot create
candidates. The separate core/support assembly workspace does not mount this card.

Expand **Components and connectivity** and use **Keep fixed** to preserve supplied
connector or other component positions. Native locks and footprints carrying
Edge.Cuts geometry are automatically fixed and cannot be unchecked. No reference
name/connector heuristic is used. Fixing a component removes its queued move.
Choose **Check placement plan** after entering moves and a rationale. The desktop
shows per-check issues and missing geometry. Moved candidates require a complete
`CLEAR` geometry result, enforced again by the core, including the serialized output.
Changing moves or fixed selections invalidates the preview. An unavailable outline
or missing courtyard blocks moved candidates; unchanged snapshots remain possible.

Candidate history shows intact/stale/missing evidence and resulting component
positions. Candidate boards are stored outside product revisions. There is no
automatic application of a candidate to a design. A restart of the desktop bridge
is needed to load new RPC operations; use the updated frontend build as well.

## Shared service and CLI

- `analyze(revision_id, relative_path)`: read-only structural analysis, source hash,
  local PCB context hash and specification hash.
- `create_candidate(revision_id, LayoutPlan)`: draft-only candidate with mandatory
  expected context digest and rationale, unique component moves in SI units.
- `preview_plan(revision_id, LayoutPlan)`: read-only proposed positions and per-check
  geometry results, with `can_create`. Archived/review previews cannot create.
- `read_candidate(revision_id, candidate_id)`: recheck manifest, all stored bytes,
  unexpected files and current source context.
- `list_candidates(revision_id)`: revision-scoped history, including incomplete
  UUID-named runs as NOT_EVALUATED. Unrelated directories are ignored.

Desktop RPC methods `pcb_layout_files`, `pcb_layout_analyze`, `pcb_layout_create`,
`pcb_layout_preview`, `pcb_layout_candidates`, `pcb_layout_read` call these same core operations. The
existing Qt PCB workspace is unchanged at this milestone. No dedicated MCP
operations were added; external agents can use the CLI.

```powershell
.venv/Scripts/python.exe -m mendex_core.cli --root . pcb-layout analyze --revision REVISION_UUID --path pcb/board.kicad_pcb
.venv/Scripts/python.exe -m mendex_core.cli --root . pcb-layout preview --revision REVISION_UUID --request plan.json
.venv/Scripts/python.exe -m mendex_core.cli --root . pcb-layout create --revision REVISION_UUID --request plan.json
.venv/Scripts/python.exe -m mendex_core.cli --root . pcb-layout list --revision REVISION_UUID
.venv/Scripts/python.exe -m mendex_core.cli --root . pcb-layout read --revision REVISION_UUID --candidate CANDIDATE_UUID
```

Example `plan.json` structure (replace the digest with the current analysis result):

```json
{
  "relative_path": "pcb/board.kicad_pcb",
  "expected_context_sha256": "<context_sha256 from analyze>",
  "rationale": "Review an explicit component position on a disposable unrouted board",
  "moves": [{"reference": "R1", "x_m": 0.012, "y_m": 0.021}],
  "fixed_references": ["J1"]
}
```

An empty `moves` list produces a byte-exact board snapshot. Unknown fields,
duplicate moves, non-finite coordinates, unknown references and locked components
are rejected. Invalid inputs and conflicts return structured CLI errors. Successful
CLI exit means the requested software operation completed, never engineering PASS.
The canonical request schema is `contracts/pcb-layout/LayoutPlan.schema.json`.
`fixed_references` defaults to an empty list for earlier request compatibility.
Duplicate/unknown fixed references and moves of explicitly fixed or outline-carrying
footprints are rejected. A preview CLI exit of 0 means the preview completed; inspect
`can_create`, status and coverage before interpreting it. It does not mean PASS.

## Drawn-geometry checks

`pcb_placement.py` is the shared checker; no UI geometry rules or additional geometry
dependency is introduced. Analysis includes `placement_constraints`; previews evaluate
the proposed coordinates. Completed candidates store their own immutable report.

| Check | Supported scope |
|---|---|
| `board_outline` | One simple outer loop and disjoint, non-nested internal cutouts |
| `board_containment` | All drawn courtyard polygons strictly inside the outer loop and outside cutouts |
| `courtyard_overlap` | Intersections, enclosure and boundary touches between different components on each shared courtyard side |
| `footprint_keepouts` | Explicit `footprints not_allowed` areas on F.Cu/B.Cu or both-side wildcards, including footprint-local areas transformed with their owner |
| `fixed_components` | Source-relative position, rotation and layer preservation for native locks, outline owners and supplied fixed references |

Rectangles, straight polygons and closed unambiguous loops of line segments are
supported. Local courtyards and footprint-owned board edges/keepouts are transformed
by native rotation/translation. Footprint-owned keepouts exclude other footprints,
not the owner. Areas explicitly permitting footprints do not create component
restrictions. Courtyards on opposite sides do not collide under this 2D rule; that
does not establish a valid 3D assembly or through-hole clearance.

Touching a board edge, another same-side courtyard or a prohibited footprint area
is conservatively an issue. No positive electrical/mechanical clearance value is
invented. The 1e-12 m tolerance is numerical coincidence handling, not an engineering
clearance. Proposed positions use the native writer's 1e-9 m output resolution.

Open/branched/duplicate/self-intersecting/degenerate contours, disjoint outer boards,
nested cutouts, curves/circles/arcs, unrecognized keepout layers/rules and missing
same-side courtyards remain unavailable. Curved polygon edges are not flattened
silently. A polygon is bounded to 2000 vertices for this local implementation.
Known issues are retained even when coverage is incomplete. Aggregate status is
ISSUES_FOUND for known violations, otherwise NOT_EVALUATED for missing coverage,
otherwise CLEAR. Only a complete CLEAR report permits component moves.

`CLEAR` is scoped to the drawn geometry and rules above. Engineering evaluation,
electrical clearance, native DRC, routing, physical/3D verification and safety remain
NOT_EVALUATED. Legacy `checks.placement_clearance` stays NOT_EVALUATED; the new
`placement_constraints` report is separately labeled geometry. Source/evidence changes
force `effective_constraint_status=NOT_EVALUATED`; the stored report is historical.
Older candidates without this report are not recalculated or silently qualified.

## Extraction and integrity

The analyzer uses the existing local S-expression reader with explicit single-root,
size and structural guards. It reads modern properties and legacy `fp_text`
references; numeric-plus-name and KiCad 10 name-only pad nets; explicit positions,
pad dimensions, world pad centres, footprint locks, edge primitives, local courtyard
primitives and keepout polygons/rules/layers. Missing/duplicate references, missing
required positions/sizes, ambiguous nets and non-finite extracted geometry fail
explicitly. Footprints require unique references and pads require explicit local
positions and positive dimensions in this first version.

Candidate directories are unique:
`.mendex/pcb-layout/<revision UUID>/<candidate UUID>/`. They contain `inputs/`,
`output/`, `candidate.json`, `manifest.json` and `manifest.sha256`. All local
context files covered by the existing PCB service are copied, with hashes checked
before publication. Metadata preserves the plan, source/context/specification
hashes, specification snapshot, engine identifier and native format version.
Candidate creation holds the shared revision transaction and rechecks context;
concurrent file changes fail with CONFLICT. Failed partial runs are not presented
as completed candidates. Subsequent source/dependency/specification changes make
the historical candidate stale. Existing records are never overwritten.

The checksum scope detects added files as well as modifications/deletions.
**Native tools must run on further disposable working copies**, because even SVG
export can create a `.kicad_prl` beside its input. The native smoke script follows
this rule. Do not launch editors or solvers directly against stored candidates.
Direct filesystem access is not a security or authenticated signing boundary.

## Evaluation boundaries

Every candidate has `evaluation_status=NOT_EVALUATED`. DRC, routing and electrical
clearance checks remain explicitly NOT_EVALUATED. DRAFT_CANDIDATE is a software
artifact state. No validation PASS, lifecycle review, approval or release is created.

Connectivity is a pad-to-net inventory, not proof of routed connectivity. Supported
outlines must pass closed/simple contour checks before containment can be evaluated.
Existing copper is not moved or ripped up; explicit component moves on boards with
board-level copper or copper zones are rejected. No automated grouping, optimization, routing, routing-score
comparison, DRC execution, standards-based sizing or HV/isolation check is added.
External libraries/models remain unembedded and unqualified. No deployment,
hardware operation or manufacturing approval is involved.

## Milestone 1 verification (historical)

- Relevant regression: **62 passed in 19.80 s**, covering layout, existing PCB
  workspace, desktop revision isolation, core/support assembly and Qt PCB panel.
  This includes 28 first-party layout tests and the generated request-schema check.

- New synthetic fixtures cover SI geometry, rotated pads, lock handling, legacy
  references, name-only nets, keepouts, malformed/empty designs, source preservation,
  byte-exact snapshots, copper guards, concurrency, stale specifications/dependencies,
  manifest damage, nested boards, append-only runs, revision isolation and CLI/RPC parity.
- Native KiCad 10.0.7 read/plot smoke translated one unlocked component by 1 mm on
  a disposable fixture, then exported SVG successfully. Original source hash stayed
  unchanged and the stored candidate retained its integrity.
- Native artifacts: `.mendex/qa/pcb-layout-20261120-02/`. Earlier run `-01` is retained:
  direct plotting added `.kicad_prl` and correctly invalidated its candidate; the smoke
  was corrected to plot a separate working copy. No old evidence was deleted or repaired.
- In-app browser discovery returned no browsers; visual/click interaction remains
  unverified. TypeScript/Vite production build passed (existing bundle-size warning).

## Milestone 2 verification

- Relevant Python regression: **102 passed in 89.70 s**, covering placement geometry,
  layout services/CLI/RPC/schema, existing PCB workspace, desktop revision isolation,
  core/support assembly and Qt panel behavior.
- TypeScript/Vite production build passed; the existing bundle-size warning remains.
- `npm --prefix desktop run test:pcb-layout`: **6 checks passed** (one parent and five
  workflow subtests). A React test renderer uses the actual desktop client and real
  Python stdio bridge on disposable products. It covers source selection/analysis,
  blocked outside-board moves, fixed selections removing queued moves, clear candidate
  creation, source preservation/read-back, stale preview/history and revision switching.
- Workflow artifacts: `.mendex/qa/pcb-layout-constraints-ui-0f6f52b2-5975-4da0-93a5-0565d4600939/`.
- Native KiCad 10.0.7 smoke with complete CLEAR geometry, preserved explicit fixed
  references and isolated SVG export passed. Source unchanged, candidate integrity true.
  Artifacts: `.mendex/qa/pcb-placement-constraints-native-20261120-01/`.
- Browser discovery again returned no available browsers. React interaction logic and
  real RPC behavior are verified; browser appearance and physical desktop clicks remain
  unverified. No native DRC result or engineering approval is claimed.

Repeat the native smoke against a supplied board with supported complete geometry:

```powershell
.venv/Scripts/python.exe scripts/pcb_layout_smoke.py --source C:/fixtures/board.kicad_pcb --output .mendex/qa/unique-new-run
```

The source is only read. The script creates an unrouted disposable fixture while
retaining keepouts, then previews and checks a 1 mm move; that move must satisfy the
constraints. It does not force unsupported or colliding geometry to clear.

Next milestones: connectivity-based placement suggestions, then routing adapters and
independent native checks against disposable candidates with traceable comparisons.
