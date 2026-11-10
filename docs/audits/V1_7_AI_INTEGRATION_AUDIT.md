# MENDEX ENGINEERING STUDIO v1.7 — AI INTEGRATION AUDIT REPORT

**Date:** 10 November 2026  
**Auditor:** Independent AI Integration Specialist & Systems Architect  
**Scope:** AI Architecture, Context Boundaries, Safety Guardrails, and Provider Integration Status  

---

## 1. Executive Summary

The AI integration inside Mendex Engineering Studio v1.7 was audited against two fundamental engineering constraints:
1. **The Safety & Veracity Constraint:** Mendex Engineering Studio prohibits AI models from fabricating engineering calculations, silently executing native solvers, altering frozen evidence baselines, or approving design dossiers without human sign-off.
2. **The Operational Assistance Objective:** The AI Assistant must provide contextual engineering assistance, explain SPICE/FEA convergence issues, guide parameter formulation, and assist engineers with complex multi-physics calculations.

### Audit Verdict: **CONDITIONALLY READY (LOCAL HEURISTICS PASS / LIVE CLOUD BLOCKED)**
- **Local Domain Heuristics:** **FUNCTIONAL & PASS**. The UI assistant provides deterministic, validated engineering formula guidance for high-frequency transformer design (Dowell model), CCM flyback converter sizing, and SiC MOSFET loss estimation.
- **Backend Safety Boundary:** **VERIFIED & PASS**. The core service strictly enforces an immutable read-only protocol via `UnavailableAIService` to prevent untracked network egress.
- **Live Cloud Provider Integration:** **BLOCKED**. External API keys (e.g. OpenAI, Anthropic, Google Gemini) are not stored or connected in this release.

---

## 2. Core Service Implementation (`src/mendex_core/ai.py`)

### 2.1 Pydantic Contracts
```python
class AIRequest(Model):
    revision_id: UUID
    question: str = Field(min_length=1, max_length=8000)
    context: dict = Field(default_factory=dict)

class AIResponse(Model):
    status: Literal["unavailable", "needs_review"]
    provider: str
    text: str
    limitations: list[str]

class AIService(Protocol):
    def advise(self, request: AIRequest) -> AIResponse: ...
```

### 2.2 Safety Guardrails
- **Read-Only Interface:** `AIResponse.limitations` explicitly includes:
  `"Read-only advice interface only; no design edits, tool execution, evidence approval or release authority."`
- **Zero Silent Tool Execution:** The AI service has no access to `SafeSubprocessRunner` or adapter execution methods. No solver or external script can be launched autonomously by AI.
- **Evidence Immutability:** AI responses cannot be stored directly into `validations` or `reports` without explicit reviewer review and manual entry.

---

## 3. UI Assistant Implementation (`AIAssistantPanel`)

In `src/mendex_ui/v17_panels.py`, `AIAssistantPanel` provides:
1. **Interactive Prompt Input:** `QLineEdit` with Enter-key submission and Send button.
2. **Contextual Suggestion Chips:**
   - *Calculate Transformer Dowell AC Factor*
   - *Optimize Flyback Primary Inductance*
   - *Explain SPICE Convergence Error*
   - *Lookup SiC MOSFET Switching Loss*
3. **Deterministic Formula Formulation:**
   - Dowell's analytical model formulation:
     $$F_R = \xi \left[ \frac{\sinh(2\xi) + \sin(2\xi)}{\cosh(2\xi) - \cos(2\xi)} + \frac{2(m^2 - 1)}{3} \frac{\sinh(\xi) - \sin(\xi)}{\cosh(\xi) + \cos(\xi)} \right]$$
   - Primary inductance for CCM Flyback:
     $$L_p = \frac{V_{in}^2 D^2}{2 P_{out} f_{sw} K_{RF}}$$

---

## 4. Live Cloud Provider Verification Status

| Check Item | Status | Verification Evidence |
|---|---|---|
| AI Assistant Page / Panel | **PASS** | `AIAssistantPanel` in `v17_panels.py`, tested in smoke suite |
| Contextual Suggestion Chips | **PASS** | Interactive buttons trigger engineering formula guidance |
| Local Calculation Guidance | **PASS** | Dowell, Flyback, and SiC formulas rendered in HTML |
| Read-Only Protocol Enforcement | **PASS** | `UnavailableAIService` returns status `unavailable` |
| Live OpenAI / Claude / Gemini API Connection | **BLOCKED** | No live API credentials configured on workstation |
| Encrypted API Key Storage (Vault) | **MISSING** | Keys cannot yet be securely stored via Windows DPAPI |
| Automatic Netlist Generation by AI | **BLOCKED** | Prohibited by engineering safety rules without manual review |

---

## 5. Corrective Action Plan for v1.8

1. **Implement Local Credential Vault:** Add a secure credential configuration dialog in Settings using Windows DPAPI (`crypt32.dll` via ctypes) to safely store user-supplied API keys for Anthropic, OpenAI, or Google Gemini.
2. **Add Connection Diagnostic:** Provide a "Test Connection" button that issues a lightweight health-check ping to the configured AI endpoint.
3. **Implement Workspace-Aware RAG:** Pass active workspace netlist files and simulation log snippets into the AI prompt context as read-only attachments.
