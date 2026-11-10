# v1.9 Readiness Gate — Test G: Engineering Intelligence Validation

**Result: FAIL** — the deterministic numerical core is correct and reproducible, and all three built-in benchmarks pass against independent recomputation. However, the documented "unit-aware / dimensionally consistent" behaviour does not exist, the reasoning layer does not perform the calculations it routes, and some provenance claims are unsubstantiated.

Evidence: `.mendex/qa/v19-readiness/pinned_dc21aa9/test_g/result.json` · harness `harness/test_g_intelligence.py`.

## 1. What the implementation actually is

| Question | Finding |
|---|---|
| Deterministic calculations? | **Yes** — closed-form Python (`intelligence/calculations.py`) |
| Local rule-based reasoning? | **Yes** — keyword routing in `LocalRuleEngineBackend` (`intelligence/models.py`), `mode: deterministic_local_rules`, `network_required: false` |
| External AI models? | **No** — no network/LLM client imports in `intelligence/*` (the only `requests` hit is a docstring word). `mendex_core/ai.py` exposes `UnavailableAIService` ("No AI provider is configured"). |
| Trained Mendex models? | **No.** No training code, weights, datasets or training logs exist in the repository. The backend named `Mendex-RuleEngine-v1.8` is a rule engine. **There is no proprietary trained foundation model**, and none should be claimed. |

## 2. Closed-form benchmarks: independent recomputation

Recomputed from first principles in the harness (not by calling the Studio):

| Case | Implementation | Independent | Stored ground truth | impl vs indep | GT vs indep | Case tolerance |
|---|---|---|---|---|---|---|
| BM-SKIN-100KHZ (Cu, 100 kHz, 100 °C) | 0.236504 mm | 0.236504 mm | 0.237 mm | 0 | 0.21 % | 3 % |
| BM-DOWELL-2LAYER (m = 2, ξ = 1) | 1.406009 | 1.406009 | 1.406 | 0 | 6.5e-4 % | 5 % |
| BM-LC-RESONANCE (10 µH, 100 nF) | 159 154.943 Hz | 159 154.943 Hz | 159 155 Hz | 0 | 3.6e-5 % | 1 % |

Additional closed-form checks: semiconductor loss (10 A, 50 mΩ, 50 + 30 µJ, 100 kHz) = 13.0 W (independent 13.0 W). Flyback sizing (85 V min, 12 V / 2 A, 100 kHz): V_R = 69.545 V, L_p = 1.490 mH, I_pk = 0.841 A, all matching an independent evaluation **of the code's own definitions**. Steinmetz (100 kHz, 0.1 T, 10 cm³): 373.9 kW/m³ (independent identical). Reproducibility: five repeated evaluations gave identical outputs.

Benchmark coverage note: the suite has 3 cases. The v1.8 checklist describes Steinmetz and CCM benchmarks and "MAPE ≤ 5 %", but no Steinmetz or flyback benchmark case exists.

## 3. Unit awareness and dimensional consistency

| Probe | Observed | Expected for a unit-aware system |
|---|---|---|
| `calculate_skin_depth(100)`, user meaning 100 kHz | Accepted; returns **7.479 mm** with `verified: True` and no warning | Rejection, or a unit-bearing input |
| `calculate_lc_resonance(10, 100)`, user meaning µH / nF | Accepted; returns **0.00503 Hz** with `verified: True` | Same |
| Negative frequency | Rejected ("Frequency must be strictly positive.") | ✔ |
| Unit library (pint / Quantity) | None; units are descriptive strings only | — |

Every `CalculationResult` defaults to `verified = True`, whether or not the inputs are sensible. The workflow layer's `QuantityValue` has a small prefix converter, but the calculation service does not use it. **Unit-aware calculation and dimensional consistency: FAIL.**

## 4. Knowledge, provenance and reasoning

| Item | Finding |
|---|---|
| Formula records | 5 records (Dowell, skin depth, flyback L_p, Steinmetz, LC). `EQ-SEMI-LOSS-01`, which the calculation service uses, has **no knowledge record**. |
| Reference consistency | Skin depth cites *Jordan & Balmain* in the calculation output but *Jackson* in the knowledge record. |
| Unsubstantiated claim | Steinmetz is described as "validated against Princeton MagNet dataset", but no MagNet data, comparison or evidence exists in the repository (the MagNet connector is metadata-only, NOT_CONFIGURED). |
| Material/standard data | N87, C3M0065090D, IEC 62368-1 and IPC-2221B excerpts are stored as constants with source names. Values were not verified against the datasheets/standards in this gate, so they remain **NOT_EVALUATED**. |
| Reasoning: "skin depth of copper at 200 kHz?" | No calculation is run; a generic module list is returned with **confidence 0.98** |
| Reasoning: "inductance of my magnetic core gap" | Answered with the **flyback** sizing formula (wrong topic). The quoted formula L_p = V²D²/(2·P·f·K_RF) also differs from the calculation service's L_p = V·D/(ΔI·f). Recommends FEMM, which the Studio cannot execute. |
| Confidence values | Hard-coded constants (0.92 / 0.95 / 0.98), not computed |
| Result-origin classification | `origin="calculated"` is set on calculation records ✔; reasoning replies carry no origin |
| Flyback ripple definition | Code defines ΔI = 2·K_RF·I_in,avg, while the result note says "40 % inductor current ripple"; the two do not agree under common definitions |

## 5. Verdict per item

| Item | Result |
|---|---|
| Knowledge retrieval | PASS (records retrievable) |
| Formula provenance | PARTIAL (one missing record, one inconsistent citation, one unsubstantiated validation claim) |
| Unit-aware calculations | **FAIL** |
| Dimensional consistency | **FAIL** |
| Reasoning orchestration | FAIL (routing only, misroutes, does not invoke calculations) |
| Tool recommendations | PARTIAL (recommends tools the Studio cannot run) |
| Result explanations | PARTIAL |
| Validation warnings | FAIL (nonsensical inputs are flagged `verified`) |
| Result origin classification | PARTIAL |
| Deterministic numerical correctness | **PASS** |
