# MPECL Compliance & Regulatory Traceability Matrix

**Document ID:** MPECL-DOC-RSK-002  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Regulatory Traceability by Product Domain

| Product Family | Applicable Safety Standard | Applicable EMC Standard | National Indian Standards (BIS / ARAI) | Required Laboratory Qualification | Current Verified Status |
|---|---|---|---|---|---|
| **Tier 1: DC-DC Converters (100W–500W)** | IEC 62368-1 (SELV) | CISPR 32 Class B (Residential) | IS 13252 (Part 1) | In-house DVP + Pre-compliance chamber | **NOT_EVALUATED** (Pending Phase 3 hardware) |
| **Tier 1: Solar MPPT Converters** | IEC 62109-1 / IEC 62109-2 | CISPR 32 Class A (Industrial) | IS 16221 (Part 1 & 2) / IS 16169 | Accredited NABL test report for BIS registration | **NOT_EVALUATED** (Pending Phase 3 hardware) |
| **Tier 2: Industrial Power Supplies** | IEC 62368-1 / IEC 61010-1 | EN 55032 Class A / EN 61000-6-2 | IS 13252 / CE Declaration | Dielectric withstand ($4\text{ kV}_{RMS}$), surge immunity | **NOT_EVALUATED** (Pending Phase 5 hardware) |
| **Tier 2: EV Battery Chargers (1kW–3kW)** | IEC 61851-1 / IEC 61851-21-2 | CISPR 25 / CISPR 32 Class B | AIS-138 (Part 1) / AIS-156 | Automotive EMI/EMC chamber + RDC-DD 6mA trip | **NOT_EVALUATED** (Pending Phase 5 hardware) |
| **Tier 3: Programmable Power (15kW)** | IEC 62477-1 / IEC 61010-1 | EN 61326-1 / CISPR 11 Group 1 | Industrial Machinery Directive / CE | 3-phase grid power quality, harmonic emissions | **NOT_EVALUATED** (Pending Phase 6 hardware) |

---

## 2. Unresolved Regulatory Questions & Gap Register

The following compliance questions represent active engineering gaps that require resolution during Phase 2 and 3 architecture freezes:

| Gap ID | Standard / Authority | Regulatory Description | Engineering Impact | Assigned Owner | Target Closure Phase |
|---|---|---|---|---|---|
| **GAP-01** | Bureau of Indian Standards (BIS) | Clarify whether programmable laboratory DC power supplies fall under compulsory registration scheme (CRS) under IS 13252. | Affects whether commercial units require BIS registration marking prior to domestic Indian sale. | Compliance Lead | Phase 2 Milestone |
| **GAP-02** | AIS-138 Part 1 (ARAI) | Confirm whether DC off-board chargers $< 3.3\text{ kW}$ require mandatory CCS-2 / Type 2 communication controllers or standard proprietary protocol. | Determines whether MCM-100 must integrate HomePlug Green PHY powerline communication (PLC). | Communications Lead | Phase 4 Milestone |
| **GAP-03** | CE Mark / EU RoHS | Determine whether lead-free high-temperature solder alloy (SAC305) is mandatory for power semiconductor thermal pads under RoHS Directive 2011/65/EU. | Affects manufacturing reflow thermal profile and component moisture sensitivity level (MSL). | Manufacturing Lead | Phase 3 Milestone |
| **GAP-04** | Central Electricity Authority (CEA) | Validate low-voltage ride-through (LVRT) reactive current injection requirements for solar string converters $\le 5\text{ kW}$. | Firmware control loop must be capable of dynamic reactive power injection during grid voltage dips. | Controls Lead | Phase 5 Milestone |
