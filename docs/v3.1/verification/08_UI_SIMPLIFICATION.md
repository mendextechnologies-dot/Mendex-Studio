# 08. UI Simplification Audit

**Target:** Removal of Obsolete / Duplicate Interactive Forms  
**Status:** **PARTIAL**

---

## 1. Observed State vs. Target State

The v3.1 target specifies:
> *"Mendex Studio should be primarily a viewing and monitoring application. Remove duplicate design editors, visual workflow builder, and manual specification-entry forms."*

### Current State:
- **Visual Workflow Builder**: Obsolete node-graph builder (`src/mendex_ui/workflow_studio_panel.py`) still exists in source, though hidden from primary sidebar navigation.
- **Interactive Forms**: PySide6 still contains interactive calculation wizards, BOM derating calculators, and PCB check buttons.
- **Help Icon Cleanup**: At the user's explicit request, the `❓ Help & AI Prompts` top-header button and `💡 Design Guide` banner button were removed cleanly in favor of the offline training handbook.

### Assessment:
Because the UI migration to the read-only Tauri command center was not implemented, the PySide6 UI retains its interactive engineering capabilities. This is beneficial for users who want desktop autonomy, but represents an architectural divergence from the strict "Codex-First / Read-Only Studio" target.
