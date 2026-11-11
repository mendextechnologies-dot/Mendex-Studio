# MENDEX ENGINEERING STUDIO v1.9 — CROSS-TOOL REVISION SYNCHRONIZATION

## 1. External Modification Tracking

When an engineer opens an artifact in an external CAD/EDA application (KiCad Eeschema, KiCad Pcbnew, LTspice XVII, FreeCAD):

1. **Fingerprint Capture**: At generation time, the artifact's SHA-256 digest is stored.
2. **On-Return Sentinel**: When the user returns to Mendex Studio, `CrossToolSyncService` recalculates on-disk hashes.
3. **External Edit Detection**:
   - If hash differs: Marked as `MODIFIED_EXTERNALLY`.
   - Generates notification and diff preview.
4. **Reconciliation**:
   - Reconciles modifications into a new immutable `DesignRevision` (incrementing revision index).
   - Flags all downstream simulation results and gate evaluations as `STALE`.
