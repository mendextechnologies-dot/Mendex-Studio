# Product Requirements Document (PRD) Template

**Document ID:** MPECL-PRD-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Product Code:** `PRD-XXX`  
**Product Title:** `[Insert Commercial Product Name]`  
**Author / Product Manager:** `[Name / Title]`  
**Reviewer:** `[Name / Title]`  

---

## 1. Executive Summary & Market Justification
* **Product Vision:** Brief statement describing the target product and user problem solved.
* **Target Market & Geography:** Target industrial sectors (e.g., Indian solar, EV charging, lab automation).
* **Target Sales Volume:** Estimated 1-year and 3-year production volumes.
* **Target Unit Cost (COGS):** Target manufacturing cost in INR / USD at specified batch volume.

---

## 2. Product Feature Requirements
| Req ID | Feature Description | Priority (Must / Should / Could) | Target User Persona | Acceptance Metric |
|---|---|---|---|---|
| `PRD-F-01` | Continuous power output | Must Have | Industrial Operator | $\ge 500\text{ W}$ continuous at $50^\circ\text{C}$ |
| `PRD-F-02` | Output voltage adjustment | Must Have | Test Engineer | $10\text{ V} - 30\text{ V}$ via front-panel knob |
| `PRD-F-03` | Remote SCPI automation | Should Have | Automated Lab | Full command set over USB-C |

---

## 3. Physical & Environmental Constraints
* **Enclosure Size:** Target dimensions ($W \times H \times D$ in mm).
* **Cooling Method:** Natural convection / Forced-air / Liquid cooled.
* **Operating Temperature:** Minimum $-10^\circ\text{C}$, Maximum $+50^\circ\text{C}$ ambient.
* **Ingress Protection (IP):** IP20 / IP54.

---

## 4. Compliance & Regulatory Requirements
* **Safety:** IEC 62368-1 / IS 13252.
* **EMC:** CISPR 32 Class A / Class B.
* **Environmental:** RoHS 3 Directive (2015/863/EU) compliance.

---

## 5. Approval & Revision History
| Rev | Date | Author | Description of Change | Approval Status |
|---|---|---|---|---|
| v0.1 | YYYY-MM-DD | Name | Initial Draft | DRAFT |
