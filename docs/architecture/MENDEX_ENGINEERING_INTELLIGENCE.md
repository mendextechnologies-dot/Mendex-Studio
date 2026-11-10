# Mendex Engineering Intelligence Foundation — Technical Specification

## 1. Overview & Objectives

The **Mendex Engineering Intelligence Foundation** (`src/mendex_core/intelligence/`) provides a robust, physics-grounded intelligence layer for Mendex Engineering Studio v1.8. 

Unlike conventional ungrounded LLM wrappers that hallucinate numerical equations or produce unverified engineering advice, Mendex Engineering Intelligence is built upon **five rigorous architectural pillars**:

1. **Engineering Knowledge Service**: Canonical, versioned repository of validated mathematical formulas, physical constants, standard engineering materials, and regulatory standards.
2. **Deterministic Calculation Service**: Unit-aware, dimensionally consistent analytical calculation engine. Every calculation produces an immutable provenance record with inputs, constants, and intermediate terms tagged with `origin="calculated"`.
3. **Model-Independent Interface**: An abstract backend protocol (`ModelBackend`) with a zero-network, zero-token `LocalRuleEngineBackend` that operates deterministically offline, plus a pluggable registry for external foundation models.
4. **Engineering Reasoning Orchestrator**: High-level orchestrator that parses user questions, resolves physical parameters, matches questions with domain solvers (e.g. recommending FEMM for proximity losses or LTspice for transient switching), evaluates analytical solutions, and formats structured advice with explicit limitations and safety disclaimers.
5. **Future Model Development & Benchmarks**: Ground-truth benchmark suite with quantitative tolerance verification (MAPE $\le 5\%$) and training dataset schemas for domain-specific fine-tuning.

---

## 2. Pillar 1: Engineering Knowledge Service (`knowledge.py`)

The `EngineeringKnowledgeService` acts as the single source of truth for engineering domain equations, material properties, and regulatory clearance tables.

### 2.1 Supported Canonical Formulas

| Formula ID | Name | Canonical Equation | Primary Application |
|---|---|---|---|
| `skin_depth` | AC Skin Depth | $\delta = \sqrt{\frac{\rho}{\pi f \mu_0 \mu_r}}$ | High-frequency conductor sizing |
| `dowell_factor` | Dowell AC Resistance Factor | $F_R = \xi \left[ \frac{\sinh(2\xi) + \sin(2\xi)}{\cosh(2\xi) - \cos(2\xi)} + \frac{2(m^2-1)}{3} \frac{\sinh(\xi) - \sin(\xi)}{\cosh(\xi) + \cos(\xi)} \right]$ | Multi-layer transformer winding AC resistance |
| `flyback_ccm_primary_inductance` | Flyback Primary Inductance (CCM) | $L_p = \frac{(V_{in,min} \cdot D_{max})^2}{2 P_{in} f_{sw} K_{RF}}$ | Flyback converter magnetic design |
| `steinmetz_core_loss` | Steinmetz Volumetric Core Loss | $P_v = C_m \cdot f^\alpha \cdot B_{pk}^\beta$ | Magnetic core loss estimation |
| `lc_resonance` | LC Resonant Frequency | $f_0 = \frac{1}{2\pi \sqrt{L C}}$ | Filter and resonant tank tuning |

### 2.2 Standard Material Database

Materials are modeled with strictly typed parameters including density, electrical resistivity, relative permeability, thermal conductivity, and maximum flux density ($B_{sat}$):

- **TDK N87 Ferrite**: MnZn power ferrite optimized for 25 kHz–500 kHz converters ($B_{sat} = 490\text{ mT}$ at $25^\circ\text{C}$, $390\text{ mT}$ at $100^\circ\text{C}$, $\mu_i = 2200$).
- **Wolfspeed C3M0065090D SiC MOSFET**: 900 V, 65 m$\Omega$ discrete device for high-efficiency power stages ($T_{j,max} = 175^\circ\text{C}$, $Q_g = 30\text{ nC}$).
- **Standard Copper (ETP CW004A)**: $\rho_{20} = 1.68 \times 10^{-8}\ \Omega\cdot\text{m}$, thermal coefficient $\alpha_{Cu} = 0.00393\ \text{K}^{-1}$.

### 2.3 Regulatory Standards Database

Provides automated clearance and creepage lookup tables according to:
- **IEC 62368-1**: Audio/video, information and communication technology equipment safety.
- **IPC-2221B**: Generic Standard on Printed Board Design.

---

## 3. Pillar 2: Deterministic Calculation Service (`calculations.py`)

The `DeterministicCalculationService` evaluates physical equations without stochastic deviation.

### 3.1 Key Capabilities

- **Temperature Correction**: Automatically adjusts electrical resistivity based on target operating temperature:
  $$\rho(T) = \rho_{20} \cdot \left[1 + \alpha_{Cu} (T - 20)\right]$$
- **Intermediate Term Transparency**: Records all sub-expressions (e.g. skin depth ratio $\xi = h/\delta$, layer factor term $2(m^2-1)/3$) to enable full engineering audits.
- **Dimensional Verification**: Enforces unit safety (Hz, m, H, F, T) and prevents nonsensical inputs (e.g. negative frequencies or non-physical duty cycles $D \ge 1$).
- **Provenance Sealing**: Outputs an immutable `CalculationRecord` with:
  - `origin`: Always set to `calculated`.
  - `formula_id`: Reference to the canonical formula.
  - `inputs_hash`: SHA-256 digest of input parameters.
  - `intermediate_terms`: Dictionary of calculated internal variables.
  - `result`: Primary numerical output with unit.

---

## 4. Pillar 3: Model-Independent Interface (`models.py`)

To ensure vendor neutrality and eliminate single-point-of-failure cloud dependencies, all AI capabilities implement the `ModelBackend` interface:

```python
class ModelBackend(Protocol):
    def generate_response(self, prompt: str, system_prompt: str | None = None) -> str: ...
    def classify_intent(self, text: str) -> str: ...
    def extract_parameters(self, text: str, schema: dict[str, Any]) -> dict[str, Any]: ...
```

### 4.1 LocalRuleEngineBackend
- Operates 100% locally with zero cloud API keys and zero network access.
- Uses deterministic regex parsing, token normalization, and intent classification.
- Directly routes calculations to `DeterministicCalculationService`.
- Guarantees instant sub-millisecond response latency.

### 4.2 Pluggable Model Registry
The `ModelRegistry` allows engineers or organizations to register external providers (such as Anthropic Claude, OpenAI, Google Gemini, or local Ollama instances) without altering Studio UI or core logic.

---

## 5. Pillar 4: Engineering Reasoning Orchestrator (`reasoning.py`)

The `EngineeringReasoningOrchestrator` provides the conversational intelligence inside `AIAssistantPanel`:

1. **Query Intent Classification**: Categorizes user requests into `calculation`, `tool_recommendation`, `knowledge_lookup`, or `general_engineering`.
2. **Context Resolution**: Injects current workspace active files, selected components, and design requirements into the context.
3. **Solver Routing**:
   - Recommends **LTspice** or **ngspice** for transient waveforms, ripple, and loop stability.
   - Recommends **FEMM** for winding proximity effect, leakage inductance, and flux fringing.
   - Recommends **KiCad** for clearance/creepage verification and PCB routing.
   - Recommends **FreeCAD** for 3D mechanical envelope and thermal heatsink packaging.
4. **Safety & Disclaimers**: Appends mandatory warnings that analytical approximations must be validated by full multi-physics simulation and laboratory bench testing before manufacturing.

---

## 6. Pillar 5: Benchmarks & Ground Truth (`benchmarks.py`)

To ensure analytical formulas remain true across releases, the `EngineeringBenchmarkRegistry` executes automated regression tests:

| Benchmark Case | Description | Analytical / Benchmark Target | Acceptance Metric |
|---|---|---|---|
| `dowell_two_layer` | 2-layer winding, $h/\delta = 1.0$ | $F_R = 1.4063$ | Relative error $\le 1.0\%$ |
| `skin_depth_100k` | Copper skin depth at 100 kHz ($20^\circ\text{C}$) | $\delta = 0.2062\text{ mm}$ | Relative error $\le 0.5\%$ |
| `flyback_ccm_50w` | 50 W, 100 kHz, $V_{in}=100\text{V}$, $D=0.45$ | $L_p = 182.25\ \mu\text{H}$ | Relative error $\le 0.5\%$ |
| `steinmetz_n87` | TDK N87 at 100 kHz, 100 mT ($100^\circ\text{C}$) | $P_v \approx 45.8\text{ kW/m}^3$ | Relative error $\le 5.0\%$ |

All benchmarks are continuously validated via pytest in `test_engineering_intelligence.py`.
