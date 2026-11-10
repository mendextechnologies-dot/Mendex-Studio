# Implementation Gaps & Action Backlog • Mendex Engineering Studio

**Audit Baseline:** v1.3 Foundation, v1.4 Scope, v1.5 Two-Agent Delivery Model  
**Auditor:** Senior Software Architect & Platform Auditor  
**Date:** 10 November 2026

---

## 1. Priority Taxonomy

- **P0 — Critical Blocker:** Prevents end-to-end simulation or release acceptance for the core engineering pilot.
- **P1 — Essential Functionality:** Necessary for multi-engineer handoff, automated execution, or complete tool integration.
- **P2 — Important Improvement:** User experience, reporting fidelity, or workflow productivity enhancements.
- **P3 — Optional Enhancement:** Future platform capabilities deferred to post-pilot phases.

---

## 2. Itemized Implementation Gaps

| Gap ID | Priority | Description | Assigned Agent | Root Cause / Impact | Required Remediation |
|---|---|---|---|---|---|
| **GAP-01** | **P0** | **KiCad CLI, FEMM, and FreeCAD missing on Host Workstation** | **Human Lead / System Admin** | Workstation does not have native EDA binaries installed. Connectors report `NOT_INSTALLED`. | Install official KiCad 8/9, FEMM 4.2, and FreeCAD 0.21+ packages; record paths in Tool Settings. |
| **GAP-02** | **P0** | **Branch Handoff & Merge from `antigravity/v1.5-integrations` to `main`** | **Agent 1 (Codex)** | Two-agent worktrees are unmerged; Codex must merge Agent 2's adapters, tests, and evidence into `codex/v1.5-integration` / `main`. | Perform clean Git fast-forward or merge commit of `antigravity/v1.5-integrations`. |
| **GAP-03** | **P1** | **Wire `V15ConnectorRegistry` into Codex `IntegrationService`** | **Agent 1 (Codex)** | `IntegrationService` currently only has `SyntheticAdapter("studio-demo")` attached by default. | Add loop in `IntegrationService.__init__` registering `V15ConnectorRegistry.all()`. |
| **GAP-04** | **P1** | **Sub-worktree `PYTHONPATH` Resolution in Virtualenv** | **Agent 1 (Codex)** | Secondary worktrees (`codex-v1.5`) require `PYTHONPATH=src` because `.venv` is bound to primary worktree root. | Add `.env` file or configure pytest `pythonpath = ["src"]` in `pyproject.toml`. |
| **GAP-05** | **P1** | **Independent Clean-Machine Pilot Qualification** | **Human Lead / QA** | Release gate 23 requires a second independent engineer to follow README from scratch. | Perform clean-machine clone, dependency install, and reference run on a separate test PC. |
| **GAP-06** | **P2** | **Category-Specific Guided Parameter Entry Forms** | **Agent 1 (Codex)** | Specifications and checks currently rely on generic typed JSON inputs rather than visual winding/core forms. | Implement interactive PySide6 input widgets for transformer bobbins, turns ratio, and DC-DC corners. |
| **GAP-07** | **P2** | **Native PDF and Word (.docx) Report Dossier Generation** | **Agent 1 (Codex)** | Reports currently export draft HTML and frozen JSON manifests only. | Implement report generation export to standalone PDF / DOCX with embedded waveform plots. |
| **GAP-08** | **P2** | **FEMM & KiCad Reference Benchmark Netlist/Board Fixtures** | **Agent 2 (Antigravity)** | Real smoke tests require verified reference `.kicad_pcb` and `.fem` files once binaries are installed. | Commit canonical reference flyback board and transformer geometry fixtures once binaries exist. |
| **GAP-09** | **P3** | **Live Instrument Automation (PyVISA / sigrok)** | **Agent 2 (Antigravity)** | Lab instruments remain mock-only; no physical hardware control is implemented. | Develop safe VISA device discovery behind human safety interlocks during Phase 6. |
| **GAP-10** | **P3** | **Advanced Waveform Vector Processing (NumPy/SciPy raw)** | **Agent 2 (Antigravity)** | LTspice ASCII raw is parsed via string headers; binary raw parsing with vectorized FFT is deferred. | Request `numpy` and `scipy` dependency approval in `docs/DEPENDENCY_REQUESTS.md`. |

---

## 3. Allocation by Agent

### Codex Responsibilities (Frontend, Application & Merge)
- **GAP-02 (P0):** Merge Agent 2 branch `antigravity/v1.5-integrations`.
- **GAP-03 (P1):** Hook `V15ConnectorRegistry.all()` into `IntegrationService`.
- **GAP-04 (P1):** Configure `pythonpath = ["src"]` in `pyproject.toml`.
- **GAP-06 (P2):** Build dedicated graphical parameter forms for Transformer and Converter workspaces.
- **GAP-07 (P2):** Implement PDF/DOCX report formatting.

### Agent 2 (Antigravity) Responsibilities (Adapters, Run-Engine & Validation)
- **GAP-08 (P2):** Supply verified reference CAD models once tools are installed.
- **GAP-09 (P3):** Lab instrument VISA backend mock/testing.
- **GAP-10 (P3):** Vectorized waveform processor when approved.
