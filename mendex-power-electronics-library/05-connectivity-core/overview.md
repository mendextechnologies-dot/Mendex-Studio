# Mendex Connectivity Core (MCCN) Platform Overview

**Document ID:** MPECL-DOC-MCN-001  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Scope & Communication Abstraction Architecture

The **Mendex Connectivity Core (MCCN)** establishes a standardized, galvanically isolated communication and telemetry architecture across all Mendex power conversion platforms.

To eliminate custom protocol implementations in every new power supply or charger, MCCN defines a **Common Communication Abstraction Layer (CCAL)**. The core controller application interacts with a uniform parameter table (Object Dictionary) regardless of whether data is transported over CAN-FD, Modbus RTU, USB-SCPI, or Ethernet.

```mermaid
graph TD
    subgraph Host_Clients ["External Host & User Interface Plane"]
        STUDIO["Mendex Studio (Orchestration & Automated DVP)"]
        PLC["Industrial PLC / SCADA (Modbus RTU / TCP)"]
        EV_BMS["EV Battery Management System (CAN-FD)"]
        LAB_PC["Lab Automation / LabVIEW (SCPI over USB)"]
        LOCAL_HMI["Local HMI Panel (MHM-100: OLED / Rotary)"]
    end

    subgraph Physical_Transceivers ["Physical Transceiver Plane (MCM-100 Card)"]
        PHY_CAN["Isolated CAN-FD Transceiver (ISO1042 / TJA1052)"]
        PHY_RS485["Isolated RS485 Transceiver (MAX14840E / ADM2483)"]
        PHY_USB["Isolated USB 2.0 Full-Speed Isolator (ADuM4160)"]
        PHY_ETH["Ethernet PHY (LAN8720) + Magnetic Isolation"]
    end

    subgraph CCAL_Engine ["Common Communication Abstraction Layer (MDC-100 MCU)"]
        OBJ_DICT["Standardized Parameter Object Dictionary<br/>(Telemetry, Setpoints, Calibration, Trip History)"]
        PARSER["Unified Command & Telemetry Dispatcher"]
    end

    STUDIO <--> PHY_USB
    STUDIO <--> PHY_ETH
    PLC <--> PHY_RS485
    EV_BMS <--> PHY_CAN
    LAB_PC <--> PHY_USB
    LOCAL_HMI <--> CCAL_Engine

    PHY_CAN <--> PARSER
    PHY_RS485 <--> PARSER
    PHY_USB <--> PARSER
    PHY_ETH <--> PARSER

    PARSER <--> OBJ_DICT
```

---

## 2. Galvanic Isolation Mandate for External Interfaces

In industrial environments and high-power DC systems ($> 60\text{ V}$), ground potential differences between the power converter chassis and external PLCs, computers, or vehicle battery packs can reach hundreds of volts, especially during ground faults or lightning surges.

> [!IMPORTANT]
> **Mandatory Isolation Rule:** All communication ports routed outside the converter chassis (CAN-FD, RS485, USB, Ethernet) **must be galvanically isolated** with a minimum isolation rating of **$\ge 2.5\text{ kV}_{RMS}$ (1 minute)** and common-mode transient immunity (CMTI) of **$\ge 50\text{ kV/}\mu\text{s}$**. Direct unisolated connection of host USB or RS485 ground to power ground (PGND) is strictly prohibited.
