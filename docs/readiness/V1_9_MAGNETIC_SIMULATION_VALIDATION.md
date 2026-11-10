# v1.9 Readiness Gate — Test B: Magnetic Analysis (FEMM 4.2)

**Result: FAIL** — the Studio cannot execute FEMM through its core service (the service reports FEMM `NOT_INSTALLED` and rejects jobs as `UNSUPPORTED`, although FEMM 4.2 is installed at `C:\femm42\bin\femm.exe`). FEMM itself was exercised directly by QA. It produced accurate fields, but the convergence criterion fixed before the run was not met.

Evidence: `.mendex/qa/v19-readiness/test_b/` · harness `harness/test_b_femm.py`.

## 1. Reference model (generic)

Planar coaxial conductor, depth 1000 mm, DC (magnetostatic):

| Region | Radius (mm) | Material | Source |
|---|---|---|---|
| Inner conductor | 0–2 | Cu (μr = 1, σ = 58 MS/m) | +10 A (series circuit, 1 turn) |
| Gap | 2–4 | Air | — |
| Magnetic annulus | 4–8 | Linear iron, μr = 1000 (no saturation) | — |
| Gap | 8–10 | Air | — |
| Return shell | 10–12 | Cu | −10 A |
| Exterior | 12–30 | Air | Dirichlet A = 0 at r = 30 mm |

Exact reference (Ampère's law, linear media), 2 mm < r < 10 mm: **B(r) = μ0·μr(r)·I / (2πr)**. Flux check: A(3 mm) − A(9 mm) = ∫B dr = (μ0 I / 2π)[ln(4/3) + μr ln 2 + ln(9/8)] = 1.387105e-3 Wb/m. The enclosed current outside the return shell is zero, so the A = 0 outer boundary is exact rather than an approximation.

Assumptions: linear, isotropic materials; no eddy currents (DC); 1° arc discretisation for all circles; probe points at 0°, 45° and 120° at r = 3, 5, 6, 7, 9 mm.

Acceptance (fixed before execution): |B| error ≤ 0.5 % at all probes on the finest mesh; ΔA error ≤ 0.5 %; change between the two finest meshes ≤ 0.5 %. Justification: first-order triangles give piecewise-constant B, so point errors scale with element size relative to r; a wrong μr, current or unit would cause errors ≥ 100 %.

## 2. Execution

`femm.exe -lua-script=<coax.lua> -windowhide`, three runs with block mesh sizes 1.0 / 0.5 / 0.25 mm (exterior 2.0 mm). Lua errors were routed to a file through `_ERRORMESSAGE`.

| Mesh (mm) | Exit | Elements | Nodes | max \|B\| err | ΔA err | Bitmap |
|---|---|---|---|---|---|---|
| 1.0 | 3221226356 (0xC0000374 at FEMM exit; results already written) | 29296 | 14829 | 0.5549 % | −0.1326 % | yes |
| 0.5 | 0 | 29452 | 14907 | 0.5419 % | −0.1014 % | yes |
| 0.25 | 0 | 34140 | 17251 | 0.5000 % | −0.0370 % | yes |

| r (mm) @ angle | Region | B_ref (T) | B 1.0 mm | err % | B 0.5 mm | err % | B 0.25 mm | err % |
|---|---|---|---|---|---|---|---|---|
| 3.0 @ 0° | air | 6.66667e-04 | 6.66723e-04 | +0.008 | 6.66690e-04 | +0.003 | 6.66646e-04 | -0.003 |
| 3.0 @ 45° | air | 6.66667e-04 | 6.66587e-04 | -0.012 | 6.66703e-04 | +0.005 | 6.67417e-04 | +0.112 |
| 3.0 @ 120° | air | 6.66667e-04 | 6.64052e-04 | -0.392 | 6.64146e-04 | -0.378 | 6.70000e-04 | +0.500 |
| 5.0 @ 0° | iron μr=1000 | 4.00000e-01 | 3.97780e-01 | -0.555 | 3.97832e-01 | -0.542 | 4.00257e-01 | +0.064 |
| 5.0 @ 45° | iron μr=1000 | 4.00000e-01 | 3.99520e-01 | -0.120 | 3.99681e-01 | -0.080 | 3.98972e-01 | -0.257 |
| 5.0 @ 120° | iron μr=1000 | 4.00000e-01 | 3.99073e-01 | -0.232 | 3.99647e-01 | -0.088 | 4.00302e-01 | +0.075 |
| 6.0 @ 0° | iron μr=1000 | 3.33333e-01 | 3.31833e-01 | -0.450 | 3.33564e-01 | +0.069 | 3.32928e-01 | -0.122 |
| 6.0 @ 45° | iron μr=1000 | 3.33333e-01 | 3.33925e-01 | +0.177 | 3.33220e-01 | -0.034 | 3.33221e-01 | -0.034 |
| 6.0 @ 120° | iron μr=1000 | 3.33333e-01 | 3.32813e-01 | -0.156 | 3.33443e-01 | +0.033 | 3.32849e-01 | -0.145 |
| 7.0 @ 0° | iron μr=1000 | 2.85714e-01 | 2.86001e-01 | +0.100 | 2.85860e-01 | +0.051 | 2.86089e-01 | +0.131 |
| 7.0 @ 45° | iron μr=1000 | 2.85714e-01 | 2.84847e-01 | -0.303 | 2.86307e-01 | +0.207 | 2.86008e-01 | +0.103 |
| 7.0 @ 120° | iron μr=1000 | 2.85714e-01 | 2.85848e-01 | +0.047 | 2.86237e-01 | +0.183 | 2.86081e-01 | +0.128 |
| 9.0 @ 0° | air | 2.22222e-04 | 2.21449e-04 | -0.348 | 2.21488e-04 | -0.330 | 2.21514e-04 | -0.319 |
| 9.0 @ 45° | air | 2.22222e-04 | 2.21711e-04 | -0.230 | 2.21748e-04 | -0.214 | 2.21925e-04 | -0.134 |
| 9.0 @ 120° | air | 2.22222e-04 | 2.22541e-04 | +0.143 | 2.22511e-04 | +0.130 | 2.22333e-04 | +0.050 |

Change between the 0.5 mm and 0.25 mm meshes at each probe (%): −0.007, 0.107, **0.874**, **0.606**, −0.178, 0.164, −0.191, 0.0, −0.179, 0.08, −0.104, −0.054, 0.012, 0.08, −0.08.

**Tool-level outcome:** field magnitudes in both air and the μr = 1000 region match the exact solution to ≤ 0.5 %, and the integral flux check (ΔA) converges monotonically to −0.037 %. The point-wise convergence criterion failed (max 0.87 %). Two causes were identified and are recorded, not used to relax the criterion. First, the 1° arc discretisation already forces a fine mesh, so the "1.0 mm" and "0.5 mm" meshes are nearly identical (29.3 k vs 29.5 k elements) and the study is not a real three-level refinement. Second, point-sampled B from first-order elements is noisy. A future rerun should use integral quantities (block-averaged B, energy, inductance) with a genuinely graded mesh.

## 3. Studio integration

| Path | Observed |
|---|---|
| Core service (`StudioService.integrations`, used by UI) | `verify("femm")` → `NOT_INSTALLED`, "FEMM is not installed on this machine." `submit()` → `StudioError UNSUPPORTED`. Cause: `V15ConnectorRegistry` registers FEMM as `UninstalledToolV15Connector`, whose `execute()` always raises. |
| Adapter layer (`integrations.adapters.FEMMAdapter`) | Not wired to `StudioService`. When called directly with the QA Lua script it ran FEMM (exit 0) but returned `metrics: {}`; its parser expects the format of its own generator, so nothing was extracted. |
| v1.9 workflow node `femm_analysis` (commit `dc21aa9`) | Without a service: returns status `COMPLETED` with `inductance_h = turns²·1.2e-7` and a heuristic B, with no solver run. With a service: raises `UNSUPPORTED`. When a service job does exist, the code falls back to hard-coded `45e-6 H` / `0.28 T` defaults (`nodes/tools.py`). |
| Field visualisation | Not available in the Studio. FEMM's own `mo_savebitmap` produced `bmag.bmp` per run (QA evidence). |

| # | Requirement | Result |
|---|---|---|
| 1–4 | Geometry, materials, boundaries, mesh | Tool-level PASS (QA Lua); Studio: not supported |
| 5 | Actual FEMM solver execution via Studio | **FAIL** |
| 6 | B extraction | Tool-level PASS; Studio FAIL |
| 7 | Field visualisation in Studio | FAIL |
| 8 | Independent reference comparison | Tool-level PASS (accuracy), convergence criterion FAIL |
| 9 | Model/result storage | QA directory only; Studio stores nothing |
| 10 | Engineering report | FAIL |

Test-procedure note: the first QA script used `opendocument`, `mo_getb` and `mo_geta`, which do not exist in FEMM 4.2 Lua; this raised an on-screen FEMM error dialog. The script was corrected to `open` and `mo_getpointvalues`. Those were QA harness errors, not Studio defects.
