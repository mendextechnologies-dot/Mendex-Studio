# Actionable Implementation Plan & Backlog • Studio v1.5 Handover

**Date:** 10 November 2026  
**Auditor:** Senior Software Architect & Platform Auditor  
**Scope:** Dependency-ordered implementation roadmap for Agent 1 (Codex) and Agent 2 (Antigravity).

---

## 1. Dependency-Ordered Execution Phases

```mermaid
flowchart TD
    subgraph Phase A ["Phase A: Integration & Merge (Immediate)"]
        A1["Agent 1: Merge 'antigravity/v1.5-integrations' into 'codex/v1.5-integration'"]
        A2["Agent 1: Add pythonpath = ['src'] to pyproject.toml"]
        A3["Agent 1: Register V15ConnectorRegistry.all() in IntegrationService"]
        A1 --> A2 --> A3
    end

    subgraph Phase B ["Phase B: Tool Onboarding & Environment Qualification"]
        B1["Admin: Install KiCad, FEMM 4.2, and FreeCAD binaries on workstation"]
        B2["Agent 2: Run non-destructive smoke tests with installed executables"]
        B3["Agent 1: Verify Tool Center updates from NOT_INSTALLED to READY"]
        B1 --> B2 --> B3
    end

    subgraph Phase C ["Phase C: Workspace & UI Enhancements (Parallel)"]
        C1["Agent 1: Build graphical parameter forms for Transformer and DC-DC modules"]
        C2["Agent 2: Build analytical winding loss & thermal calculation models"]
        C3["Agent 1: Implement PDF / DOCX report export engine"]
    end

    subgraph Phase D ["Phase D: Final Release & Pilot Acceptance"]
        D1["QA / Peer Engineer: Execute clean-machine reproduction on secondary PC"]
        D2["Engineering Lead: Sign-off v1.5 release dossier"]
    end

    Phase A --> Phase B
    Phase B --> Phase C
    Phase C --> Phase D
```

---

## 2. Agent 1 (Codex) Immediate Backlog

### Task 1.1 — Merge Agent 2 Integrations Branch (P0)
- **Action:** Merge `antigravity/v1.5-integrations` into `codex/v1.5-integration`.
- **Pre-conditions:** Both worktrees currently pass automated tests with 0 regressions.
- **Verification:** Run pytest across full merged repository.

### Task 1.2 — Connect `V15ConnectorRegistry` to `IntegrationService` (P1)
- **Action:** In `src/mendex_core/integration_service.py`:
  ```python
  from integrations.v15_connector import V15ConnectorRegistry
  # Inside IntegrationService.__init__:
  for connector in V15ConnectorRegistry.all():
      if connector.descriptor.tool_id not in self.adapters:
          self.register_reviewed_adapter(connector)
  ```
- **Verification:** Launch Tool Center; verify that `ltspice`, `python`, and `git` transition from `DETECTED` to `READY` automatically.

### Task 1.3 — Configure Pytest `pythonpath` (P1)
- **Action:** In `pyproject.toml`, add:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["src"]
  ```
- **Verification:** `pytest` succeeds in any worktree without requiring explicit `PYTHONPATH` shell variables.

---

## 3. Agent 2 (Antigravity) Immediate Backlog

### Task 2.1 — Standby for Binary Installation Smoke Runs (P0)
- **Action:** Once system administrator installs KiCad 8/9, FEMM 4.2, and FreeCAD:
  1. Update configured executable paths.
  2. Execute native smoke tests using `src/integrations/generators/` scripts.
  3. Publish real execution traces and artifact hashes in `docs/ADAPTER_TEST_EVIDENCE.md`.

### Task 2.2 — High-Frequency Transformer Winding Loss Calculator (P2)
- **Action:** Implement Dowell's equation analytical model for transformer AC winding resistance and proximity/skin effect losses in `src/integrations/calculations/winding_losses.py`.
- **SI Units:** Frequencies ($f$), conductor diameter ($d$), layer count ($m$), skin depth ($\delta$).

---

## 4. Parallel Work Stream Summary

| Stream | Agent 1 (Codex) | Agent 2 (Antigravity) |
|---|---|---|
| **Immediate (Day 4)** | Branch merge, `IntegrationService` wiring, UI job refresh | CAD fixture verification, Dowell winding calculations |
| **Next (Day 5)** | PDF/DOCX exporter, graphical bobbin/core entry forms | KiCad DRC parsing test with real synthetic PCB layout |
| **Release Gate** | Packaging & final changelog | Pilot evidence audit and report sign-off assistance |
