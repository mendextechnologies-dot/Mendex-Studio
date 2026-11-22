# Mendex Control Core (MCC) Platform Overview

**Document ID:** MPECL-DOC-MCC-001  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Scope & Architectural Mandate

The **Mendex Control Core (MCC)** governs all embedded real-time intelligence, digital control loop computation, PWM modulation, system sequencing, and supervisory communications across Mendex power conversion products.

The fundamental objective of MCC is to establish a **topology-agnostic, multi-target firmware platform**. The firmware must run on a standardized hardware controller card (**MDC-100**) without requiring algorithmic rewrites when transitioning between converter topologies (e.g., from a 500 W Synchronous Buck to a 3 kW Phase-Shifted Full-Bridge).

```mermaid
graph TD
    subgraph MCC_Firmware_Architecture ["MCC Layered Firmware Architecture"]
        APP["Application Layer<br/>(CV/CC Mode Manager, MPPT, Battery Charging Profile, SCPI Engine)"]
        CONTROL["Control Core Engine<br/>(State Machine, Soft-Start/Stop, 2P2Z/3P3Z Compensators, Droop Sharing)"]
        SUPERVISOR["Safety Supervisor & Fault Manager<br/>(Trip Zone Handler, Overcurrent/Overvoltage Check, I2t Thermal Model)"]
        HAL["Hardware Abstraction Layer (HAL)<br/>(PWM Driver, ADC Driver, Comparator Driver, Timer Driver, GPIO)"]
        HARDWARE["Physical Hardware Layer<br/>(Target A: STM32G474 / Target B: TMS320F280039C)"]
    end

    APP --> CONTROL
    CONTROL --> HAL
    SUPERVISOR --> HAL
    SUPERVISOR --> CONTROL
    HAL --> HARDWARE
```

---

## 2. Hard Real-Time Timing & Scheduling Requirements

Power electronics digital control requires deterministic, low-latency execution. A missed interrupt or uncontrolled phase jitter in a high-frequency converter causes immediate duty cycle saturation, inductor saturation, and semiconductor destruction.

MPECL firmware establishes three deterministic execution tiers:

```mermaid
timeline
    title Execution Tiers in MCC Firmware
    ISR 0 (Sub-microsecond) : Hardware Trip Zone (Comparator Trip) : Asynchronous / <750 ns
    ISR 1 (High-Priority Real-Time) : ADC Conversion Complete : 100 kHz - 300 kHz (Cycle-by-cycle inner current loop)
    ISR 2 (Medium-Priority Control) : Voltage Loop & State Transition : 10 kHz (Outer voltage loop, CV/CC management)
    Task 3 (Background Non-Realtime) : Safety Supervisor, Telemetry & Fieldbus : 100 Hz - 1 kHz (Modbus, SCPI, HMI refresh)
```

1. **Tier 0: Asynchronous Hardware Trip Zone ($< 750\text{ ns}$):**
   - Implemented via hardware comparator (CMPSS) triggering PWM trip pins directly in silicon.
   - Bypasses software interrupt latency entirely. Shuts down gate drives immediately.
2. **Tier 1: High-Frequency Inner Loop ISR ($100\text{ kHz} - 300\text{ kHz}$):**
   - Triggered by ADC conversion completion (synchronized to PWM carrier midpoint).
   - Worst-case execution budget: **$\le 2.5\,\mu\text{s}$** (utilizing $< 35\%$ CPU capacity at $100\text{ kHz}$).
   - Computes inner inductor current control ($I_L$), cycle-by-cycle peak limiting, and updates PWM compare registers.
3. **Tier 2: Medium-Frequency Outer Loop ISR ($10\text{ kHz}$):**
   - Triggered by a dedicated hardware timer.
   - Worst-case execution budget: **$\le 15\,\mu\text{s}$**.
   - Computes outer voltage regulation ($V_{out}$), Constant Current (CC) / Constant Voltage (CV) smooth clamping, slew rate limiting, and soft-start ramps.
4. **Tier 3: Low-Priority Background Task ($10\text{ Hz} - 1\text{ kHz}$):**
   - Runs in a non-preemptive cooperative round-robin scheduler.
   - Handles isolated Modbus RTU, CAN-FD frame parsing, SCPI commands, OLED display refresh, and non-critical thermal telemetry ($I^2t$ modeling).

---

## 3. Universal State Machine

Every power converter managed by MCC executes an identical top-level deterministic finite state machine (FSM):

```mermaid
stateDiagram-v2
    [*] --> POWER_ON_RESET
    POWER_ON_RESET --> HARDWARE_SELF_TEST: VDD & VAUX stable
    HARDWARE_SELF_TEST --> FAULT: BIST Failure / Trip Asserted
    HARDWARE_SELF_TEST --> STANDBY: BIST Passed

    STANDBY --> PRE_CHARGE: Enable Command Received
    PRE_CHARGE --> SOFT_START: DC Bus Pre-charged > V_min
    PRE_CHARGE --> FAULT: Pre-charge Timeout

    SOFT_START --> NORMAL_RUN: V_out reached target & Loop settled
    SOFT_START --> FAULT: Soft-start Overcurrent / Timeout

    state NORMAL_RUN {
        [*] --> CV_MODE
        CV_MODE --> CC_MODE: Load Current > I_limit
        CC_MODE --> CV_MODE: Load Current < I_limit
    }

    NORMAL_RUN --> SOFT_STOP: Normal Disable Command
    NORMAL_RUN --> FAULT: Trip Event / Sensor Out of Bounds

    SOFT_STOP --> STANDBY: V_out ramped down safely

    FAULT --> FAULT_LATCHED: Hardware Trip Locked
    FAULT_LATCHED --> STANDBY: Manual / Remote Reset (after fault cleared)
```

* **POWER_ON_RESET:** Initializes clocks, sets all PWM pins to high-impedance (tri-state), configures safety trip zones.
* **HARDWARE_SELF_TEST:** Verifies internal references ($V_{ref}$), confirms ADC zero-offset calibration, checks temperature sensors, and verifies that the `/TRIP_ZONE` line is de-asserted.
* **STANDBY:** Awaits physical enable switch, SCPI command, or fieldbus start flag.
* **PRE_CHARGE:** Activates inrush current limiting contactor/resistor; verifies input DC link capacitors charge safely.
* **SOFT_START:** Linearly ramps the reference voltage/current over a programmable duration ($10\text{ ms} - 500\text{ ms}$) to prevent inductor current overshoot.
* **NORMAL_RUN:** Seamless automatic crossover between Constant Voltage (CV) and Constant Current (CC).
* **FAULT_LATCHED:** Latches all PWMs low, records high-resolution fault snapshot in non-volatile memory, and illuminates the red fault indicator.
