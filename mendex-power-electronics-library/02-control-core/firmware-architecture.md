# MPECL Firmware Architecture & Abstraction Specification

**Document ID:** MPECL-DOC-MCC-004  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Multi-Target Firmware Layering

The MCC firmware architecture enforces a strict four-layer separation to ensure portability across STMicroelectronics (STM32G474) and Texas Instruments (TMS320F280039C) silicon targets:

```mermaid
graph TD
    subgraph Layer_4 ["Application Layer"]
        APP_CVCC["CV / CC Controller"]
        APP_PROT["Fault History & Blackbox Logger"]
        APP_SCPI["SCPI / Modbus Command Parser"]
    end

    subgraph Layer_3 ["Mendex Control Engine (Platform Agnostic)"]
        ENG_FSM["System State Machine"]
        ENG_RAMP["Soft-Start / S-Curve Ramp Generator"]
        ENG_COMP["2P2Z / 3P3Z Discrete Math Blocks"]
    end

    subgraph Layer_2 ["Hardware Abstraction Layer (HAL API)"]
        HAL_PWM["hal_pwm_set_duty(), hal_pwm_set_phase(), hal_pwm_trip_enable()"]
        HAL_ADC["hal_adc_read_raw(), hal_adc_get_calibrated_si()"]
        HAL_CMP["hal_comparator_set_threshold(), hal_comparator_enable()"]
        HAL_COM["hal_uart_send(), hal_can_transmit(), hal_spi_transfer()"]
    end

    subgraph Layer_1 ["Target-Specific Silicon Drivers"]
        DRV_ST["STM32G4 LL (Low-Layer) & HRTIM Driver Engine"]
        DRV_TI["C2000Ware Driverlib & CLA Assembly Routines"]
    end

    Layer_4 --> Layer_3
    Layer_3 --> Layer_2
    Layer_2 --> DRV_ST
    Layer_2 --> DRV_TI
```

---

## 2. Real-Time Interrupt & Priority Hierarchy

To guarantee zero timing jitter in high-frequency power conversion, MCU hardware interrupt priorities are configured in strict hierarchical order:

| Interrupt Vector | Trigger Source | Frequency / Rate | Execution Latency Limit | Priority (Cortex-M4 / C28x) | Function |
|---|---|---|---|---|---|
| **TRIP_ZONE_IRQ** | Hardware Comparator / External Trip Pin | Asynchronous Event | $< 500\text{ ns}$ | **Level 0 (Highest)** | Emergency PWM shutdown, hardware latch capture, fault log trigger |
| **ADC_CONV_IRQ** | PWM Timer Midpoint Trigger | $100\text{ kHz} - 300\text{ kHz}$ | $\le 2.5\,\mu\text{s}$ | **Level 1** | Read ADC registers, execute inner current loop 2P2Z, update PWM compare registers |
| **VOLT_LOOP_IRQ** | General Hardware Timer | $10\text{ kHz}$ | $\le 12\,\mu\text{s}$ | **Level 2** | Execute outer voltage regulation loop, CV/CC clamping, update current reference |
| **CAN_RX_TX_IRQ** | CAN-FD Controller | Asynchronous / Up to 1 Mbps | $\le 5\,\mu\text{s}$ | **Level 3** | Ingest incoming vehicle/PLC frame into ring buffer |
| **UART_DMA_IRQ** | UART DMA Complete (Modbus/SCPI)| Up to 115.2 kbps | $\le 20\,\mu\text{s}$ | **Level 4** | Notify background task of received command packet |
| **SYSTICK_IRQ** | System Tick Timer | $1\text{ kHz}$ | $\le 25\,\mu\text{s}$ | **Level 5** | Increment system uptime, trigger 100 ms HMI refresh, run cooperative background loop |

---

## 3. Blackbox Pre-Fault Ring Buffer Logging

When an overcurrent, overvoltage, or short-circuit event occurs, post-mortem analysis requires knowing the exact system state preceding the failure.

The MCC firmware maintains a **circular pre-fault ring buffer** in high-speed internal SRAM:
* **Buffer Depth:** 64 consecutive switching cycles.
* **Captured Channels:**
  - $V_{in}$ (Raw ADC & Calibrated SI Volts)
  - $V_{out}$ (Raw ADC & Calibrated SI Volts)
  - $I_{inductor}$ (Raw ADC & Calibrated SI Amps)
  - Computed Duty Cycle ($d$)
  - System State Variable
* **Freeze Trigger:** Asserted on `TRIP_ZONE_IRQ` entry.
* **Storage:** Upon hardware shutdown, the 64-sample snapshot is written to non-volatile EEPROM/Flash along with a 64-bit UTC timestamp and fault code, enabling deep post-mortem diagnostics in Mendex Studio.

---

## 4. Bootloader & In-Field Firmware Update Standard

MPECL controllers support in-field firmware updates over CAN-FD or isolated RS485 without opening the physical enclosure:

```mermaid
graph TD
    RESET["MCU Power On / Hardware Reset"] --> BL_CHECK{"Bootloader Key Valid &<br/>Magic Word != REPROGRAM?"}
    BL_CHECK -->|Yes| JUMP_APP["Jump to Main Application (Bank 0 / Bank 1)"]
    BL_CHECK -->|No / Reprogram Flag Set| BL_MODE["Enter MPECL Secure Bootloader"]

    BL_MODE --> BL_COMMS["Listen on CAN-FD (1 Mbps) or UART (115200 bps)"]
    BL_COMMS --> BL_AUTH["Verify Mendex RSA/ECDSA Firmware Signature"]
    BL_AUTH -->|Valid| BL_FLASH["Erase Target Flash Sector & Stream S-Records"]
    BL_AUTH -->|Invalid / Tampered| BL_ABORT["Abort & Send Error Receipt"]
    BL_FLASH --> BL_CRC["Verify Complete Image SHA-256 Checksum"]
    BL_CRC -->|Pass| BL_ACTIVATE["Mark Active Bank & Reset MCU"]
    BL_CRC -->|Fail| BL_RETRY["Keep Old Image Active & Log Integrity Error"]
```

* **Dual-Bank Flash Memory Architecture:** Flash memory is partitioned into two identical operational banks (Bank 0 and Bank 1).
* **Zero Bricking Guarantee:** A new firmware image is completely written and verified via SHA-256 checksum in the inactive bank before switching the boot vector. If verification fails or power drops during flashing, the controller continues booting from the intact original bank.
