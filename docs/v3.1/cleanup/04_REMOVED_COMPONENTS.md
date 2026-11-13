# 04 Removed Components Log — Mendex Engineering Studio v3.1

This log registers all obsolete, dead, or transient components that have been verified unused and safely removed from the repository.

---

## Removed Component Registry

### 1. `src/mendex_ui/first_run_wizard.py`
- **Original File Path**: `src/mendex_ui/first_run_wizard.py`
- **Component Name**: `FirstRunWizardDialog`
- **Reason for Removal**: Legacy v2.0 onboarding dialog. In the v3.1 Codex-first architecture, project initialization occurs headlessly through `engineering-workflows/stages/01_project_initialization.md` and CLI/MCP. Workspace and solver health are monitored via the modern React Command Center (`desktop/src/pages/Settings.tsx` & `EngineeringTools.tsx`).
- **Replacement**: React Command Center `Settings` and `EngineeringTools` pages.
- **Dependency Analysis**: Static grep confirmed 0 import statements across `src/`, `tests/`, and `scripts/`.
- **Tests Executed**: `pytest tests/ui/ -q` (34 tests collected and verified).
- **Result**: No failures, 100% pass.
- **Rollback Method**: `git checkout 72e5fb8c0878ca2a0dd222580ff2dab018582ea2 -- src/mendex_ui/first_run_wizard.py`.

---

### 2. Transient Root Debug Artifacts
- **Original File Paths**:
  - `dump.html`
  - `rendered_command_center.png`
  - `command_center_full_verified.png`
  - `engineering_tools_verified.png`
- **Reason for Removal**: Transient test captures and DOM dumps generated during local verification. Permanent visual evidence is preserved under the conversation artifacts directory.
- **Replacement**: Verified live rendered artifacts in artifact directory (`command_center_full_verified.png`, `engineering_tools_verified.png`).
- **Dependency Analysis**: Uncommitted untracked binaries. No code or test dependency.
- **Tests Executed**: `git status`.
- **Result**: Cleaned from working tree.
- **Rollback Method**: Re-run headless screenshot capture if local disk files are required.

---

### 3. Historical Abandoned Workspace Artifacts & Stale Temporary Designs
- **Original File Paths**:
  - `workspaces/4f7a9de8-de2a-44fd-8036-04e33e4b969c/generated_artifacts/rev_1/*`
  - `workspaces/default/generated_artifacts/rev_1/*`
  - `engineering_designs/39f88be3-e164-4471-aeef-314c5f4e5b53.json`
  - `engineering_designs/aa7816c1-9b09-45d0-adb6-fc27cf9f6d48.json`
  - `engineering_designs/e0902416-fff1-4294-8c48-e708a5f764d3.json`
  - `temp_femm_test/etd34_core.ans`, `temp_femm_test/etd34_core.fem`
- **Reason for Removal**: Obsolete test fixtures and transient simulation scratch outputs generated during early v1.9/v2.0 integration experiments.
- **Replacement**: Active authoritative project workspace in `products/fb64e927-56ee-4a0b-9b51-4fb6055bd932/revisions/85906dbc-0542-4c5c-bc7f-c56596f34beb/` (`SV-1000`).
- **Dependency Analysis**: Verified non-authoritative; no test in the 323 regression suite relies on these orphaned UUIDs.
- **Tests Executed**: Full regression test suite (`pytest -q`: 323 passed).
- **Result**: 100% green pass.
- **Rollback Method**: `git checkout 72e5fb8c0878ca2a0dd222580ff2dab018582ea2 -- workspaces/ engineering_designs/ temp_femm_test/`.


---

### 4. Legacy Handbooks, Playbooks & Offline Help Documents
- **Original File Paths**:
  - `docs/KC100_Product_Engineering_Handbook.docx`
  - `docs/KC100_Product_Engineering_Handbook.md`
  - `docs/KC100_Product_Engineering_Handbook.pdf`
  - `docs/Mendex_Studio_Team_Engineering_Playbook.docx`
  - `docs/Mendex_Studio_Team_Engineering_Playbook.pdf`
  - `docs/team-engineering-playbook.md`
  - `docs/Mendex_Engineering_Validation_Platform_Master_Guide_v1_3.docx`
  - `docs/Mendex_Engineering_Studio_Next_Steps_Specification_v1_4.docx`
  - `docs/V21_CODEX_INTEGRATION_GUIDE.md`
  - `docs/V21_ENGINEERING_WORKSPACE_GUIDE.md`
  - `docs/source-guide.txt`
- **Reason for Removal**: User-requested retirement of all legacy handbook and guide documentation. New documentation will be authored as per the modern Codex-first tool design and React Command Center architecture.
- **Replacement**: New documentation and user guides to be created under the modern tool design.
- **Dependency Analysis**: 0 code, test, or build references.
- **Tests Executed**: Full pytest suite (`tests/` and `tests/command_center/`).
- **Result**: 100% green pass.

---

### 5. In-App Help & Design Guide Dialog (`src/mendex_ui/engineering_guide_dialog.py`)
- **Original File Path**: `src/mendex_ui/engineering_guide_dialog.py`
- **Component Name**: `EngineeringGuideDialog`
- **Reason for Removal**: Legacy embedded PySide6 dialog containing hardcoded prompts and obsolete help tabs. Removed along with header button (`btn_prompts`) and navigation pill (`🤖 AI Prompts`) in `product_lifecycle_panel.py`.
- **Replacement**: New tool design guidelines and Codex-driven workflow prompts (`engineering-workflows/stages/`).
- **Dependency Analysis**: Removed callers from `product_lifecycle_panel.py`; updated `tests/ui/test_engineering_guide_dialog.py` to verify complete absence.
- **Tests Executed**: `pytest tests/ui/ -q` (34 passed), `pytest tests/command_center/ -q` (15 passed).
- **Result**: 100% green pass.
