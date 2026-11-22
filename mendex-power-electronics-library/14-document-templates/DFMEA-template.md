# Design Failure Mode & Effects Analysis (DFMEA) Template

**Document ID:** MPECL-FMEA-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Quality & Reliability Lead:** `[Name / Title]`  

---

## 1. Scope & System Definition
* Definition of the module, circuit block, or assembly under analysis.
* Identification of interfaces, operating environment, and lifecycle boundaries.

---

## 2. DFMEA Worksheet

| Item / Function | Potential Failure Mode | Potential Failure Effect | $S$ (1-10) | Potential Cause / Mechanism | Current Prevention Controls | $O$ (1-10) | Current Detection Controls | $D$ (1-10) | $RPN$ ($S \times O \times D$) | Recommended Corrective Action | Target Completion Date | Action Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `[Component / Block]` | `[Failure Mode]` | `[Local / System Effect]` | `[1-10]` | `[Root Cause]` | `[Design Margins / Rules]` | `[1-10]` | `[Test / Inspection]` | `[1-10]` | `[Calc]` | `[Design Change / Redundancy]` | `[Date]` | `[Lead]` |

---

## 3. High Risk Action Items Summary ($RPN \ge 120$ or $S \ge 8$)
1. **Critical Safety Item 1:** Detailed description of mitigation and verification evidence.
2. **Critical Reliability Item 2:** Detailed description of mitigation and verification evidence.

---

## 4. Revision & Signoff
* Lead Hardware Architect: `[Signature / Date]`
* Quality Assurance Manager: `[Signature / Date]`
