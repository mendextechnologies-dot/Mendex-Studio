# 14. Revision Management & Engineering Approvals

**Target:** Immutability, Revision Branching & Human Review Gates  
**Status:** **PASS**

---

## 1. Revision Lifecycle

- **Baseline Immutability**: When a revision is baselined, its specifications, evidence records, and calculation snapshots cannot be altered.
- **Branching**: `StudioService.create_revision()` allows branching new exploratory revisions (e.g. `R002`) preserving historical records intact.
- **Side-by-Side Diff Viewer**: `RevisionDiffDialog` compares any two revisions across Specs, Sizing, BOM, and Lifecycle Gates.
- **Human Authority**: AI agents cannot self-approve engineering gates. Stages requiring review remain in `AWAITING_REVIEW` until an authenticated human engineer supplies an explicit review record.
