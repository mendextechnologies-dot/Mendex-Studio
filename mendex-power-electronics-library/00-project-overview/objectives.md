# MPECL Strategic Objectives & Key Results (OKRs)

**Document ID:** MPECL-DOC-OVR-002  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Primary Engineering Objectives

The strategic intent of MPECL is translated into measurable engineering and business objectives:

### Objective 1: Dramatically Reduce New Product Design Cycles
* **Baseline:** Current ground-up converter development cycle at Mendex is 12 to 14 months from concept to pilot production.
* **Target:** Achieve a design-to-prototype cycle of **$\le 4\text{ months}$** for Tier 1 products (100 W – 500 W) and **$\le 7\text{ months}$** for Tier 2 products (1 kW – 3 kW) by reusing pre-verified control, auxiliary, sensing, and firmware blocks.

### Objective 2: Establish a Unified Multi-Target Digital Control Core
* **Target:** Develop a universal digital controller daughtercard specification (**MDC-100**) with a standardized 120-pin / 200-pin edge connector interface that supports both:
  - **Variant A:** STMicroelectronics STM32G474 (ARM Cortex-M4F with 184 ps HRTIM, targeted for low-cost, high-volume products).
  - **Variant B:** Texas Instruments C2000 TMS320F280039C (High-performance C28x DSP with CLA and HRPWM, targeted for multi-loop resonant and high-reliability systems).
* **Firmware Portability:** Maintain a clean Hardware Abstraction Layer (HAL) allowing control loop algorithms (PID, 2P2Z) to execute interchangeably with minimal target-specific driver modifications.

### Objective 3: Institutionalize Safety & Hardware Fault Protection
* **Target:** Implement a sub-microsecond ($< 1\,\mu\text{s}$) autonomous hardware trip mechanism across all power stages.
* **Separation of Concerns:** Hardware comparators must trigger immediate PWM disable (latched) independently of microcontroller firmware execution, preventing catastrophic shoot-through or thermal runaway under firmware hang conditions.

### Objective 4: Standardize Manufacturing & BOM Sourcing for India
* **BOM Commonality:** Ensure that $\ge 70\%$ of active ICs, passive resistors/capacitors, and standard semiconductor footprints are shared across the Mendex product portfolio.
* **Supply Chain Redundancy:** Every critical component (gate drivers, current sense amps, MOSFETs, LDOs, DC-DC aux switchers) must have at least two pin-compatible or drop-in alternate part numbers vetted for stocking in Indian distribution hubs (Bengaluru, Pune, Delhi/NCR).

---

## 2. Engineering Key Performance Indicators (KPIs)

| Metric | Current State | Target State under MPECL v1.0 | Verification Method |
|---|---|---|---|
| **Firmware Code Reuse** | $< 15\%$ across projects | **$\ge 75\%$** common core code | Git repository line-of-code audit across products |
| **Control Board Redesign** | New PCB per converter | **Zero redesign**; 100% reuse of MDC-100 | Hardware BOM and schematic audit |
| **BOM Part Number Count** | High sprawl (>500 SKUs) | Rationalized passives and standard semiconductors | ERP / Mendex Studio BOM analysis |
| **Short-Circuit Trip Latency** | Firmware-dependent (10–100 µs) | **$\le 750\text{ ns}$** hardware autonomous | Oscilloscope capture during DVP short-circuit test |
| **Pre-compliance Pass Rate** | ~40% on first test pass | **$\ge 80\%$** first-pass EMC/EMI compliance | Certified chamber testing (CISPR 32 Class A/B) |

---

## 3. Scope Boundaries & Non-Goals

To maintain strict technical feasibility, the following non-goals are established for MPECL v1.0:

* **Non-Goal 1: Universal Physical Power Card:** We explicitly reject the concept of a single physical "universal power stage card" that plugs into a 100 W or 15 kW system. Power stages are design IP blocks.
* **Non-Goal 2: In-House ASIC / Silicon Development:** MPECL relies strictly on commercially available, proven COTS (Commercial Off-The-Shelf) power semiconductors and controller ICs.
* **Non-Goal 3: Automated Manufacturing Approval:** In compliance with Mendex core rules, MPECL documentation and simulation models do not replace physical laboratory design verification or qualification testing.
