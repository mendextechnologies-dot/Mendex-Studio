# CAD panel control verification

**Date:** 15 November 2026, Asia/Calcutta. **Scope:** controls in the supplied CAD-panel screenshot and their related schematic/3D/layer-inspector actions. Evaluation only; no application fixes applied by this audit.

## Main finding: routing works, preview does not reliably show it

The original SV1000 board contains **145 native copper segments, 24 vias, 32 footprints and 81 pads**. An isolated copy deliberately stripped of segments/vias was sent through the same `auto_route_pcb` RPC used by the button. It generated **145 segments and 24 vias**, with zero reported unconnected items. This verifies real copper creation, not just a success message.

However, the current PCB preview raises `UnboundLocalError: cannot access local variable 'content' where it is not associated with a value`. In `src/mendex_core/desktop/service.py:cad_preview`, the PCB branch now obtains geometry from a helper but still uses the removed local `content` variable for layer/zone detection. The four failing regression tests reproduce this exception.

There is a second, independent problem: the geometry helper and Gerber inspector require `(net <integer>)` on segments. The actual KiCad 10 board uses quoted names such as `(net "/GATE")`. Those real tracks are omitted even if the exception is corrected. The footer infers “Placement Only (Unrouted)” from the preview's track array, so this label is not trustworthy evidence of native connectivity.

Evidence and visual outputs:

- [Route from zero, native counts and native DRC](evidence/route-from-zero.json)
- [Original/after-route board and RPC results](evidence/results.json)
- [Independent native DRC JSON](evidence/route-from-zero-drc.json)
- [Actual track geometry, independently extracted SVG](evidence/actual-routed-tracks.svg) — diagnostic drawing, not a screenshot of the app
- [Fresh KiCad raytraced image](evidence/native-render.png)
- [Fault-injection and current-preview diagnostics](evidence/diagnostics.json)

The original board directory's monitored file hashes were identical before/after the main native probe (`source_changes_during_check=[]`). All routing, plane, slot, export and render operations used disposable copies under this audit folder. Native editor and Explorer launch endpoints were checked with the final launch action intercepted; no real user editor was opened by those checks.

## Control-by-control results

“Backend verified” means the operation ran against isolated files; it does not mean a browser click/download completed. The browser runtime returned no available browsers, so interactive end-to-end UI acceptance remains **Not Verified**. Source wiring and backend results are distinguished below.

| Control | Result | What was checked / remaining problem |
| --- | --- | --- |
| Tool qualification badge | Informational; not a button | Header renders a div with no click handler. Navigate using Engineering Tools in the application navigation. |
| Refresh polling (4s) badge | Informational; not a toggle | `usePolling` serially refreshes project data. CAD preview has separate local state and does not subscribe to every project poll. |
| Header Refresh | Source-wired; partial verification | Increments refresh key and refreshes project data. It cannot repair a failed CAD parser. Browser click not tested. |
| 2D PCB Layout | **Fails current backend preview** | Unbound `content`; helper also rejects quoted-net segments. |
| Schematic Diagram | Backend available; UI transition not verified | Native schematic preview returned available=true. Because `loadData` uses Promise.all for all three previews, a failed PCB read can prevent newly fetched schematic/3D state from being committed. |
| Raytraced 3D View | Backend verified | Actual KiCad image generation succeeded. 27/32 footprints have associated 3D models; missing bodies and cached images limit completeness. Tab click not tested. |
| Panel Refresh | **Fails current PCB refresh path** | Calls the same Promise.all loader; one failed PCB request rejects the entire update. Does not independently refresh an already-mounted Gerber inspector or invalidate thermal calculations. |
| Thermal Heatmap | Backend calculations run; behavior inconsistent | Panel hardcodes 2 oz in thermal requests even when the selector shows 1 oz. Overlay data can survive route/revision changes without invalidation. A visible overlay is not qualified thermal evidence. |
| 1 oz / 2 oz Heavy | Partial | Selector changes routing widths/spokes and later plane-operation parameters. It does not immediately edit actual stackup copper thickness, nor does it control the hardcoded thermal copper input. |
| 4-Layer Active / 4-Layer Planes | Native operation verified; status defective | Real In1/In2 pours succeeded on a copy. Failure injection nevertheless returned success=true when both pours and DRC failed. UI reads `res.drc.errors` while response nests actual counts at `res.drc.drc.errors`, defaulting missing counts to zero. Main 2D canvas does not draw actual filled-zone polygons. |
| Mill Isolation Slot | Native CAD operation verified; display/status defective | Generated a 2.5 × 45.5 mm Edge.Cuts slot on a copy. It edits CAD geometry, not physical hardware. Nested DRC count path is wrong in UI; refresh also hits the preview exception. No insulation qualification inferred. |
| Auto-Route Board | **Real routing verified; preview and failure handling defective** | Zero → 145 tracks / 24 vias. Current UI cannot reliably display them. Adapter treats missing/failed DRC output as zero errors; injected failed pour/DRC still produced success=true. UI unconditionally claims ground fill in its success text. |
| Inspect Layers | Opens same inspector in source; geometry incomplete | Backend returns success, but its independent track regex returns zero segments for the quoted-net board. Inspector previews native PCB-derived geometry, not a full CAM rendering of exported Gerber contents. |
| Gerber & Drill Inspector tab | Same limitation as Inspect Layers | Layer file inventory and drill/placement metadata exist; that does not validate visual copper coverage or file-set completeness. Auto-export can write files when none exist. |
| Download Gerbers | ZIP payload verified; browser save unverified | Decoded payload opens, CRC passes and SHA-256 matches. File set is incomplete for four-layer fabrication: In1.Cu/In2.Cu absent. UI initiates browser download and immediately claims downloaded/verified without observing disk completion. |
| In Explorer | **Fails with export-returned path** | Export returns data-root-relative `products/.../pcb/gerbers/...zip`; reveal endpoint expects revision-workspace-relative path. Reproduced rejection. Correct `pcb/gerbers` resolves when launch is intercepted. |
| Re-Export Gerbers | Exports native files; **four-layer completeness fails** | Export succeeds but explicit default layer list excludes In1.Cu/In2.Cu. Actual archive contains F/B copper only. Required drill/CPL/stats export failures are swallowed. No package completeness claim justified. |
| Open in KiCad PCB | Launch routing verified; actual window unverified | Correct copied PCB path reaches intercepted `open_native`. Existing launch-preservation tests pass. Actual GUI interaction not tested. |
| Dismiss status (×) | Source-wired only | Clears the local status message. It does not cancel a native job, refresh files or clear persisted check results. |

## Related controls within the alternate views

| Group | Assessment |
| --- | --- |
| 3D Generate Render | Correct RPC is `render_3d_pcb`. Native rerender produced a real 640 × 480 PNG. Initial probe used incorrect method `render_3d`; that error was an audit-harness mistake, corrected in the diagnostic probe, not a broken UI route. |
| Export STEP | Native export returned a nonempty STEP (~1.39 MB for the tested copy). Native model existence/export does not establish enclosure fit or complete body coverage. |
| Open STEP in FreeCAD / native 3D | Source-wired; not actually launched. UI model opening should be separately verified once browser/desktop interaction is available. |
| 3D view-angle selection | Source requests corresponding view. Backend may fall back to generic existing isometric image if a requested-angle file is missing; selecting Top/Bottom can therefore display a cached different angle. Fresh full per-angle UI verification remains outstanding. |
| 3D orbit/reset/zoom and schematic zoom/view modes | Source-wired local state only; no browser interaction verification. Orbit view is not evidence of actual mechanical collision/fit analysis. |
| Inspector layer visibility/solo/presets | Source-wired local state. Copper render loop handles F.Cu/B.Cu only; full arbitrary inner-layer/mask/paste rendering was not established. Some opacity expressions use `value || default`, so a zero-opacity selection falls back to visible opacity. |
| Inspector refresh/re-export | Calls backend again, but does not fix quoted-net parsing or prove archive freshness/content equivalence. |
| Inspector caliper/snapping/differential tools | Source implementation exists. Compliance messages are derived from local heuristic rules and even filename-derived voltage presets; do not treat them as standards approval. Interaction/measurement accuracy Not Verified. |
| Download Turnkey | ZIP transport/CRC/hash verified, but archive has the same contents as Gerber ZIP for this fixture and no BOM. “Turnkey” does not prove assembly completeness. |
| CPL/component highlights and drill schedule | Backend data and source controls present; native coordinate/rotation/layer interpretation and clicks still need interactive acceptance. |

## DRC interpretation

The actual routing response reports zero errors, zero unconnected items and **52 warnings** when schematic-parity findings are included. An independent native DRC report lists **16 warnings**, zero unconnected items, and no error-severity violations. Its stricter “all issues” service verdict is FAILED because warnings remain. These are different scopes, not proof the board is warning-free.

Warnings include footprint/schematic mismatches and net-name conflicts in Copper's parity checks. The UI's green “PASS” is limited to its selected numerical checks and may read an old `drc_report.json` without source-hash freshness validation. It is not manufacturing, electrical or safety approval.

## Priority fixes recommended

1. Restore the PCB branch's `content` handling and replace regex-only geometry extraction with the existing structural/native parser. Support both numeric and quoted nets, segment/arc/via geometry, real layer maps and filled zones. Add a saved KiCad-10 quoted-net regression.
2. Return source board hash and authoritative routing/connectivity/check availability with the preview. Derive visible status from actual effective results; expose native versus displayed segment counts and reject missing DRC evidence.
3. Export all enabled copper layers from the native board, validate the required layer/drill set, and reject incomplete exports. Treat ancillary export failures explicitly.
4. Normalize all file paths to one documented revision-relative contract. Invalidate cached Gerber/download/3D/thermal state on source hash or revision changes.
5. Flatten/type DRC responses consistently. Report actual warnings/unconnected counts, pour outcomes and NOT_EVALUATED status when checks fail or are unavailable. Do not manufacture zero errors.
6. Distinguish copper routing settings from fabrication copper thickness. Use the selected, sourced copper value consistently for thermal estimates and persist actual stackup changes only through the shared core.
7. Add proper browser acceptance once the browser connection is available: click every shown control, inspect request/response, compare native board hash/counts with SVG tracks, verify downloads on disk and test native-window opens on disposable files.

No fixes were applied during this checking task. Existing concurrent application changes were preserved. Do not mark all buttons working based on these results.

## Verification and reproducibility

- [Selected tests](evidence/pytest.log): **26 passed, 4 failed**. All four failures reproduce the `cad_preview` unbound-content exception. [JUnit](evidence/pytest.xml).
- TypeScript `tsc --noEmit`: exit 0; [log](evidence/typescript.log). Static typing does not detect Python preview failures or quoted-net omissions.
- [Native-copy probe](probe_controls.py), [diagnostic/fault probe](diagnose_controls.py), [zero-track routing probe](route_from_zero.py).
- [Launch endpoint routing with final actions intercepted](evidence/launch-routing.json).
- [Source snapshot and hashes](evidence/diagnostics.json), [captured files](evidence/source-snapshot/). Some application files were already dirty and changed concurrently; results are tied to these captured implementations. The first probe attempt failed because its own setup called mkdir on an already-created isolated PCB directory; only that audit harness was corrected.
- Browser setup returned “Browser is not available: iab”, and browser discovery returned an empty list. No fallback browser automation was used. UI-only and disk-download behavior remains explicitly unverified.
