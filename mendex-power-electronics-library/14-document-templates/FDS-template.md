# Firmware Design Specification (FDS) Template

**Document ID:** MPECL-FDS-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Embedded Firmware Lead:** `[Name / Title]`  

---

## 1. Firmware Architecture & Target Hardware
* Target Silicon: STMicroelectronics STM32G474 / TI TMS320F280039C.
* Compiler / Toolchain: ARM GCC (STM32CubeIDE) / TI Clang (CCS).
* Real-Time Scheduling: Bare-metal cooperative scheduler with hardware ISR priority tiers.

---

## 2. Interrupt Service Routine (ISR) Timing Budgets
| Interrupt Name | Hardware Vector | Trigger Source | Rate / Frequency | Max Execution Budget | Priority Level |
|---|---|---|---|---|---|
| `TRIP_ZONE_ISR` | Vector 0 | Hardware Comparator Pin | Asynchronous | $< 500\text{ ns}$ | 0 (Highest) |
| `ADC_CONTROL_ISR`| Vector 1 | PWM Carrier Midpoint | $100\text{ kHz}$ | $\le 2.5\,\mu\text{s}$ | 1 |
| `VOLTAGE_LOOP_ISR`| Vector 2 | Timer 2 Overflow | $10\text{ kHz}$ | $\le 12\,\mu\text{s}$ | 2 |
| `COMM_UART_ISR` | Vector 3 | UART DMA Receive | Asynchronous | $\le 15\,\mu\text{s}$ | 3 |

---

## 3. Discrete Control Loop Algorithms (2P2Z / 3P3Z)
* Compensator coefficients ($b_0, b_1, b_2, a_1, a_2$) in Q24 fixed-point or IEEE-754 32-bit single-precision float.
* Anti-windup clamping logic and saturation boundaries.
* CV / CC seamless minimum duty selector logic:
  $$d(n) = \min\left(d_v(n), d_i(n)\right)$$

---

## 4. State Machine Definition
* UML Statechart diagram depicting transitions: `INIT`, `STANDBY`, `SOFT_START`, `RUN_CV`, `RUN_CC`, `FAULT_LATCH`.

---

## 5. Non-Volatile Memory Map & Calibration Storage
* EEPROM / Flash memory sector partitioning (Object Dictionary, Serial Number, Calibration Coefficients, Blackbox Ring Buffer).
