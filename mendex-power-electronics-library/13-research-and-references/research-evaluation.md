# MPECL Research, Technology Evaluation & References

**Document ID:** MPECL-DOC-RES-001  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Manufacturer Reference Design Evaluation

The following industrial reference designs were reviewed to extract best practices in topology selection, gate drive layout, and digital control:

### Reference 1: Texas Instruments TIDM-1000 / TIDA-01604 (10 kW SiC Active Front End & LLC Converter)
* **Publisher:** Texas Instruments, USA (Rev. B, March 2021)
* **URL:** `https://www.ti.com/tool/TIDA-01604`
* **Technical Details:** Three-phase active front end (AFE) paired with a 10 kW isolated LLC resonant DC-DC converter utilizing 1200V SiC MOSFETs switching at 100 kHz. Controlled via a single TMS320F28379D dual-core C2000 DSP. Implements hybrid resonant modulation and synchronous rectification.
* **Licensing / Restrictions:** TI Reference Design License (Schematics and firmware freely reusable on TI silicon; prohibited on non-TI hardware).
* **Suitability for Mendex:** Highly suitable architectural reference for **Phase 5 & 6 (Tier 2 & 3 MPS-300 and 15 kW platforms)**. Confirms validity of using C2000 DSP for simultaneous PFC and resonant DC-DC control.
* **Verification Status:** Architectural concept confirmed from official TI lab report; physical prototype at Mendex is **NOT_EVALUATED**.

### Reference 2: STMicroelectronics STEVAL-DPSLLC160 (1.6 kW Telecom LLC Converter)
* **Publisher:** STMicroelectronics, Europe (Rev. 1, November 2022)
* **URL:** `https://www.st.com/en/evaluation-tools/steval-dpsllc160.html`
* **Technical Details:** 1.6 kW full-bridge LLC resonant converter stepping down 400V DC to 48V DC. Controlled digitally via an STM32G474RE microcontroller using the High-Resolution Timer (HRTIM). Achieves 97.5% peak efficiency with zero-voltage switching (ZVS).
* **Licensing / Restrictions:** Permissive ST Evaluation License (Open schematics and firmware libraries in STM32CubeG4).
* **Suitability for Mendex:** **Extremely High.** Directly proves that the lower-cost STM32G474 microcontroller possesses sufficient timer resolution (184 ps) and ADC bandwidth to control a multi-kilowatt resonant converter without requiring a costly dual-core DSP.
* **Verification Status:** Published manufacturer bench measurements confirmed; Mendex implementation remains **NOT_EVALUATED**.

### Reference 3: Wolfspeed CRD-06600DD065N (6.6 kW High-Power Bi-Directional OBC)
* **Publisher:** Wolfspeed (Cree), USA (Rev. 2, May 2020)
* **URL:** `https://www.wolfspeed.com/tools-and-support/power/crd-06600dd065n/`
* **Technical Details:** 6.6 kW bidirectional EV on-board charger featuring a Dual Active Bridge (DAB) DC-DC stage paired with an active totem-pole PFC. Utilizes 650V 67 mΩ SiC MOSFETs in TO-247-4L packages with isolated gate drivers.
* **Licensing / Restrictions:** Proprietary hardware reference design; public technical documentation for implementation guidance.
* **Suitability for Mendex:** Serves as the primary reference for **MPS-300-DAB bidirectional power flow equations** and Kelvin-source PCB layout techniques.
* **Verification Status:** Confirmed manufacturer data; Mendex physical prototype **NOT_EVALUATED**.

---

## 2. Open-Source Hardware Projects & Ecosystems

### Reference 4: Libre Solar (Open-Source Renewable Energy Electronics)
* **Lead Organization:** Libre Solar Project (CC-BY-SA 4.0 / CERN Open Hardware Licence)
* **URL:** `https://libre.solar`
* **Technical Details:** Open-source DC-DC solar MPPT charge controllers (20A and 40A models) and battery management systems utilizing STM32 microcontrollers and Zephyr RTOS. Implements perturb-and-observe MPPT algorithms, high-side P-FET reverse-polarity protection, and CAN-bus telemetry.
* **Suitability for Mendex:** Valuable peer benchmark for **Tier 1 (MPS-100 / MPS-200) MPPT software state machines** and low-cost 48V battery interface circuitry. Commercial productization requires clean-room schematic capture to avoid viral copyleft licensing entanglements.
* **Verification Status:** Open hardware repository verified; firmware benchmarks reviewed.

---

## 3. Indian Sourcing & Supply Chain Analysis

To avoid project paralysis caused by 26-to-52-week global component allocation lead times, all MPECL BOMs prioritize components with verified Indian stocking channels:

| Component Category | Recommended Primary Part | Recommended Second-Source Part | Indian Stocking Hub Availability | Local Distributor Channel |
|---|---|---|---|---|
| **Digital Controller** | STM32G474RET6 (ST) | TMS320F280039CPN (TI) | High volume in Bengaluru / Pune hubs | Arrow Electronics India, Element14, Mouser |
| **Gate Driver (LV)** | UCC27282DR (TI) | DGD05473FN-7 (Diodes Inc) | Stocked across major distributors | Avnet India, DigiKey India, local brokers |
| **Gate Driver (HV Isolated)**| UCC21520DW (TI) | Si82394CD-IS (Skyworks) | Moderate stocking; 2-4 week lead time | Arrow India, Mouser India |
| **Current Sense Amp** | INA240A2PWR (TI) | AD8418AWBRZ (Analog Devices) | Consistently stocked in India | Element14, Arrow India |
| **Isolated Current Amp**| AMC1301DWVR (TI) | Si8920BD-IS (Silicon Labs) | Moderate stocking | Mouser India, DigiKey India |
| **Power MOSFETs (100V)**| BSC035N10NS5 (Infineon) | PSMN4R2-100YSFX (Nexperia) | Readily available | Arrow India, Avnet India |
| **SiC MOSFETs (650V/1200V)**| C3M0065090D (Wolfspeed) | SCT3030KL (STMicroelectronics) | Stocked for EV / solar development | Arrow India, Mouser India |
| **Sendust Powder Cores**| Magnetics Inc (Kool Mµ) | Chang Sung Corp (CSC High-Flux) | Stocked locally in India | CTR Manufacturing, Cosmo Ferrites, local winders |
