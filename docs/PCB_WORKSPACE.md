# PCB workspace

The **PCB Workspace** navigation page now lists native KiCad files for the selected product revision, opens editable draft designs, imports files without overwriting existing names, runs ERC/DRC in the background, and displays persisted check history. Restart the desktop application after updating source to load this page.

## Using the desktop

1. Select a product and revision in **Products**, then select **PCB Workspace**.
2. Use **Import KiCad file** to copy a schematic, board, project or rules file into the draft's `pcb/` directory. Import companion files as required; preserve subdirectories for hierarchical projects using the workspace folder. Import does not invent a schematic, footprints or routing.
3. Select a `.kicad_sch` file and choose **Run ERC**, or select a `.kicad_pcb` and choose **Run DRC**. The selected file is explicit; another file is never silently chosen. KiCad is discovered through the existing lifecycle tool discovery (common Windows installation directories or PATH).
4. Read the result in **Check history and evidence**. **Open selected check evidence** opens that check's folder for inspection, including snapshots, native report, logs, command and tool version when execution occurred.
5. Use **Design and isolation notes** for board dimensions, stackup, clearance assumptions, sources and outstanding qualified review. Saving notes creates a new draft document. It does not record an engineering approval.

No product selected means no actions. Archived and review revisions cannot import/edit notes or open designs for editing through this screen. Checks on archived revisions use copies and store evidence outside the frozen revision. The desktop stays responsive during checks; if a check is still finishing, close Studio after it completes (native checks have a 60-second timeout plus version discovery).

## Results and limits

| Effective result | Meaning |
|---|---|
| `CLEAR` | KiCad produced an evaluable report with zero issues under its configured rules, on a file containing placed components/pads |
| `ISSUES_FOUND` | Native report contains rule violations, disconnected items or schematic-parity issues |
| `ERROR` | Process failed or timed out; inspect available diagnostics |
| `NOT_EVALUATED` | Empty/incomplete or malformed CAD, missing tool/report, malformed report, stale inputs/specification/notes, or missing/changed evidence |

These are **rule-check results**, not circuit correctness, HV isolation verification, prototype readiness or manufacturing approval. Product evaluation remains `NOT_EVALUATED` on this page. A schematic with no placed symbols, including a hierarchy-only root sheet, cannot yield `CLEAR` here. An outline without populated footprints/pads is likewise unevaluated. Select a populated sheet where appropriate; this guard is deliberately conservative. Remaining circuit defects and missing connections must still be assessed by KiCad and a qualified reviewer.

The JSON parser accepts recognized KiCad issue arrays, including nested schematic sheets, `unconnected_items` and `schematic_parity`; malformed JSON never falls back to zero issues. The current invocation uses KiCad's configured/default rules and reported issue categories; it does not enable all optional checks or prove standards compliance. Optional parity checking requires separate configuration/workflow work before making a parity-completeness claim.

Previous SV-1000 historical approvals are not rewritten by this feature. The separate lifecycle badge can still disagree with actual evidence; see [compact feasibility audit](audits/SV1000_COMPACT_FEASIBILITY_20261111.md). No new approval records or manual PASS entries are created by a PCB check.

## Shared service and evidence

Desktop and CLI both use `StudioService.pcb`. Each check copies local KiCad context from `pcb/` into a unique `.mendex/pcb-checks/<revision UUID>/<run UUID>/inputs/` directory. It never runs against the original design. Stored metadata includes the specification hash, hashes of local design/project/rule/library files and draft notes, timestamps, operation, exact command, tool version where available, process result and diagnostic text. Reports, logs, metadata and input snapshots are covered by a checksum manifest. Existing check artifacts are not reused or overwritten. There is no new database, migration, deployment or hardware operation.

Reading history verifies checksums and compares the current specification/local PCB context to the snapshot. Old results remain historical but become effectively `NOT_EVALUATED` when the context changes. Adding another design/context file also invalidates earlier checks conservatively. Local external library references, environment variables and separately installed library contents are not embedded or fully qualified; include dependencies locally and review them before making reproducibility claims. Checksums detect ordinary changes on subsequent reads; direct filesystem access is not a security boundary or authenticated signing system.

## CLI

Run from the same environment as the desktop. Replace `REVISION_UUID` with the actual selected revision.

```powershell
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-files --revision REVISION_UUID
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-import --revision REVISION_UUID C:\design\converter.kicad_sch
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-check --revision REVISION_UUID --kind erc pcb/converter.kicad_sch
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-check --revision REVISION_UUID --kind drc pcb/converter.kicad_pcb
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-checks --revision REVISION_UUID
.\.venv\Scripts\python.exe -m mendex_core.cli --root . pcb-notes --revision REVISION_UUID --file C:\design\review-notes.txt
```

`pcb-check` exits 0 for `CLEAR`, 1 for issues/process failure, and 2 for `NOT_EVALUATED`. Input errors return a structured error and nonzero exit. `pcb-open` opens an existing editable draft design through the same service; `pcb-notes` without `--file` reads notes.

## Local verification

Tests cover empty designs/library-only symbols, malformed reports, nested violations/disconnected/parity counts, unavailable tools, timeout, input snapshots and persistence, source/context/specification changes, evidence tampering, import conflicts, archived editing, path validation, CLI parity and asynchronous desktop behavior. Native KiCad 10.0.7 smoke on disposable fixtures reported zero issues for a clean schematic, two for an intentionally faulty schematic, and three for an unrouted board (including one disconnected item).

Final full suite: **159 passed in 81.74 s**, including 15 new PCB tests. Native artifacts and source hashes: `.mendex/qa/pcb-workspace-implementation-20261111/`. Final dark/light, notes and archived screenshots: `.mendex/qa/pcb-workspace-ui-20261111-final/`. Desktop screenshots use disposable empty CAD, never a claimed SV-1000 design. Reproduce desktop checks using:

```powershell
.\.venv\Scripts\python.exe scripts/pcb_workspace_smoke.py --output .mendex/qa/pcb-ui-new-run
```

Command syntax was checked against the [official KiCad 10 CLI documentation](https://docs.kicad.org/10.0/en/cli/cli.html). Native tool smoke and automated software tests are not engineering qualification of the converter.
