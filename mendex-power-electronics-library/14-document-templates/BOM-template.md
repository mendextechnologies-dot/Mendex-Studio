# Master Bill of Materials (BOM) Template

**Document ID:** MPECL-BOM-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Hardware Lead:** `[Name / Title]`  

---

## 1. BOM Metadata & Sourcing Rules
* Standard SI units used for all component values.
* Minimum two authorized manufacturing sources required for every active semiconductor and specialized passive component.
* Sourcing verified against Indian distributor authorized channels (Arrow, Avnet, Element14, Mouser India).

---

## 2. Structured Bill of Materials Worksheet

| Item # | Reference Designator | Description & Key Parameters | Primary MPN | Primary Manufacturer | Secondary MPN | Secondary Manufacturer | Package Footprint | Qty per Board | Sourcing Lead Time (India) | Unit Cost Est. (1k Qty) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `U1` | Microcontroller ARM Cortex-M4F @ 170MHz | STM32G474RET6 | STMicroelectronics | STM32G474REI6 | STMicroelectronics | LQFP-64 | 1 | 2-4 Weeks | \$4.10 |
| 2 | `Q1, Q2` | Power MOSFET 100V 3.5mΩ Superjunction | BSC035N10NS5 | Infineon | PSMN4R2-100YSFX | Nexperia | SuperSO8 / TDSON-8 | 2 | 2-3 Weeks | \$1.25 |
| 3 | `L1` | Power Inductor 15µH 35A Sendust Core | WE-HCI 74435571500| Wurth Elektronik | Custom Sendust Toroid| CTR India | SMD / Toroid | 1 | 4 Weeks | \$3.80 |
| 4 | `C1-C4` | Aluminum Polymer Cap 470µF 35V ESR 10mΩ | 35SEF470M | Panasonic | PLV1V471MDL1TD | Nichicon | Radial Can 10x12.5mm | 4 | Stock | \$0.85 |
| 5 | `R_sense` | 4-Terminal Current Shunt 2mΩ 1% 3W | WSLP39212L000FEA | Vishay Dale | BVN-M-R002-1.0 | Isabellenhütte | SMD 3921 | 1 | 3 Weeks | \$1.10 |
| 6 | `U2` | Current Sense Amp 80dB CMRR @ 100kHz | INA240A2PWR | Texas Instruments | AD8418AWBRZ | Analog Devices | TSSOP-8 | 1 | 2 Weeks | \$1.35 |

---

## 3. Cost & Sourcing Summary
* Total Board Assembly BOM Cost (1,000 unit run): **`$XX.XX USD` / `₹XXXX INR`**.
* Single-Source Risk Items: `[List any components without an approved second source]`.
