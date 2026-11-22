# Engineering Change Request & Order (ECR / ECO) Template

**Document ID:** MPECL-ECO-XXX-001  
**ECR Number:** `ECR-YYYY-XXXX`  
**ECO Number:** `ECO-YYYY-XXXX`  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED | IMPLEMENTED  
**Target Organization:** Mendex Electronics LLP  
**Originator:** `[Name / Title]`  
**Impacted Module / Product:** `[Module ID / Name]`  

---

## 1. Problem Description & Root Cause
* **Detailed Problem Statement:** Explanation of the defect, compliance failure, thermal violation, or component obsolescence requiring change.
* **Root Cause Analysis (5-Whys / Fishbone):** Technical analysis proving root cause of the issue.

---

## 2. Proposed Engineering Change
* **Description of Change:** Exact schematic, PCB layout, BOM, or firmware modifications.
* **Component Interchangeability:**
  - Form: Yes / No
  - Fit: Yes / No
  - Function: Yes / No
* **Disposition of Existing Inventory:**
  - Scrap existing stock / Rework existing stock / Use-as-is until depleted.

---

## 3. Impact Assessment
| Discipline | Impact Level (High / Med / Low / None) | Specific Impact & Necessary Action |
|---|---|---|
| **Hardware Schematics & PCB** | Medium | Update KiCad schematic and re-route gate drive traces |
| **Firmware Codebase** | Low | Update dead-time constant in `hal_pwm.h` |
| **Bill of Materials (BOM)** | Medium | Replace obsolete gate driver IC with approved pin-compatible alternate |
| **Manufacturing Tooling** | None | Stencil and pick-and-place files regenerated |
| **Safety & Compliance** | None | Creepage distances preserved |

---

## 4. Verification & Validation Plan
* List of mandatory DVP regression tests required to validate this change before release.

---

## 5. Formal Approvals & ECO Authorization
| Role | Approver Name | Signature | Decision (APPROVED / REJECTED) | Date |
|---|---|---|---|---|
| Lead Hardware Architect | `[Name]` | `[Signature]` | APPROVED | YYYY-MM-DD |
| Firmware Lead | `[Name]` | `[Signature]` | APPROVED | YYYY-MM-DD |
| Manufacturing / Ops Lead | `[Name]` | `[Signature]` | APPROVED | YYYY-MM-DD |
| Quality Assurance Lead | `[Name]` | `[Signature]` | APPROVED | YYYY-MM-DD |
