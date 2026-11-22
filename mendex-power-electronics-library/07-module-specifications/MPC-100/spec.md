# Module Specification: MPC-100 Parallel Control & Current Sharing Module

**Document ID:** MPECL-MOD-MPC-100-001  
**Revision:** v1.0-DRAFT  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  
**Hardware Lead:** System Parallelization & Control Lead  

---

## 1. Purpose and Intended Applications
The **MPC-100 Parallel Control and Current Sharing Module** provides active analog and digital current sharing, phase synchronization, and master-slave supervisory coordination across multiple parallel-connected power converter modules, enabling modular scaling up to **$15\text{ kW}$** with $N+1$ fault redundancy.

**Intended Applications:**
- Paralleling $3\text{ kW}$ isolated converter bricks (MPS-300) to form $6\text{ kW}, 9\text{ kW}, 12\text{ kW}$, and $15\text{ kW}$ programmable power supplies.
- Redundant $N+1$ industrial DC power plants where any single module failure must not interrupt critical load power.

---

## 2. Functional Requirements
1. **Active Current Sharing Accuracy:** Maintain current sharing balance between all parallel modules within **$\le \pm 2.5\%$** of rated module current from $20\%$ to $100\%$ load.
2. **Dual Sharing Topologies:**
   - **Mode 1: Analog Dedicated Share Bus:** Single-wire analog share bus ($0 - 3.0\text{ V}$ representing $0 - 100\%$ load) with democratic autonomous master selection (highest current unit automatically commands the share bus).
   - **Mode 2: Digital CAN-FD High-Speed Share:** Digital packet broadcast at $100\text{ Hz}$ with active droop adjustment.
3. **Interleaved Clock Synchronization:** Distribute a master clock pulse ($f_{sync}$) with programmable phase offsets ($0^\circ, 90^\circ, 120^\circ, 180^\circ$) to interleave parallel power stages, reducing input and output RMS ripple current by up to $70\%$.
4. **Hot-Swap & Module Extraction:** Support live insertion and removal of power modules without interrupting DC bus voltage or creating voltage transient spikes ($< \pm 2\%$).

---

## 3. Non-Functional Requirements
1. **Dynamic Sharing Latency:** Current imbalance resolved within $\le 50\text{ ms}$ following a sudden $50\%$ load step.
2. **Failure Isolation:** Short-circuit or controller failure on one module must decouple from the share bus within $\le 100\,\mu\text{s}$, preventing bus corruption.
3. **Operating Temperature:** $-40^\circ\text{C}$ to $+85^\circ\text{C}$.

---

## 4. Proposed Architecture
MPC-100 features a dedicated analog current-share amplifier network (compatible with TI UCC29002 / UCC39002 architecture or discrete op-amp democratic share circuits) paired with an isolated CAN-FD transceiver for digital supervisory control and sync clock distribution via LVDS buffers.

---

## 5. Functional Block Diagram

```mermaid
graph TD
    subgraph Module_N ["Power Module N (DUT)"]
        LOCAL_I["Local Current Sense (MSM-100)"]
        SHARE_AMP["Current Share Controller / Amp<br/>(Democratic Master/Slave)"]
        LOCAL_LOOP["Local Voltage Compensator (MDC-100)"]
        SYNC_RCV["Phase Sync Receiver / PLL"]
    end

    subgraph Inter_Module_Bus ["Shared Backplane Bus"]
        ANALOG_SHARE["Analog Single-Wire Share Bus (0 - 3.0V)"]
        SYNC_LINE["Master Interleaving Clock Bus (f_sync)"]
        CAN_BUS["High-Speed Digital CAN-FD Bus"]
    end

    LOCAL_I --> SHARE_AMP
    SHARE_AMP <--> ANALOG_SHARE
    SHARE_AMP -->|Voltage Trim Adjust (+/- 2%)| LOCAL_LOOP
    SYNC_LINE --> SYNC_RCV
    SYNC_RCV --> LOCAL_LOOP
    CAN_BUS <--> LOCAL_LOOP
```

---

## 6. Electrical Interface Requirements
- Analog Share Bus: $0.0\text{ V}$ to $3.0\text{ V}$ high-impedance single-ended line.
- Clock Sync: 3.3V LVDS or open-drain high-speed line with $100\,\Omega$ termination.
- Module Trim Injection: Output of share amp injects a small bias current into the local MDC-100 voltage divider feedback node, adjusting local $V_{out}$ by $\pm 2.0\%$ to enforce equal load sharing.

---

## 7. Mechanical Interface Considerations
- Physical Format: **Daughtercard or Backplane Subcircuit** with dedicated backplane edge connector.
- Pinout standardized to prevent damage during angled hot-swap insertion (staggered pin lengths: Ground makes first / breaks last).

---

## 8. Hardware Component Options
- **Share Controller IC:** Texas Instruments UCC29002D / UCC39002 (Advanced load share controller) or Microchip MCP6002 discrete precision op-amp network.
- **Clock Buffers:** Texas Instruments DS90LV011A / DS90LV012A (High-speed LVDS line driver/receiver).
- **Isolation:** Silicon Labs Si8621 digital isolators for sync lines.

---

## 9. Firmware Dependencies
- MCC includes an active droop compensation algorithm and CAN-FD peer-to-peer load balancing routine.

---

## 10. Communication Interfaces
- Analog share line: `I_SHARE_BUS`.
- Digital: `CLOCK_SYNC_IN/OUT`, CAN-FD bus.

---

## 11. Safety Requirements
- **Share Bus Clamp:** High-speed clamping diodes ensure the analog share line cannot exceed $+3.3\text{ V}$ or drop below $0\text{ V}$, even if a module power supply fails.
- **Anti-Contention:** Internal diode OR-ing prevents a defective module from dragging down the common share bus.

---

## 12. Supported Power and Voltage Classes
- Scalable across modular racks from $1\text{ kW}$ up to $15\text{ kW}$ (up to 8 parallel modules).

---

## 13. Design Limitations
- Analog share bus sensitive to ground potential offsets between chassis racks; requires star-connected chassis ground return or isolated digital CAN-FD sharing for distributed racks.

---

## 14. Reusability Assessment
- **Reuse Rating:** **100% DIRECTLY REUSABLE** for all multi-module and parallel-redundant products.

---

## 15. Simulation Approach
- Multi-converter parallel transient response and load distribution error modeled in LTspice with mismatched wire impedances.

---

## 16. Verification and Acceptance Criteria
1. Current sharing verified within $\pm 2.0\%$ balance across 4 parallel $3\text{ kW}$ modules operating into a common $12\text{ kW}$ load bank.
2. Hot-plugging a 5th module results in output bus voltage transient $< \pm 1.5\%$ with zero false overcurrent trips.
3. Phase interleaving confirmed on 4-channel oscilloscope showing $90^\circ \pm 5^\circ$ clock displacement.

---

## 17. Estimated Development Complexity
- **Complexity:** Medium-High.
- **Key Challenge:** Preventing control loop interaction (hunting / oscillations) between parallel local voltage loops.

---

## 18. Preliminary BOM Considerations
- Estimated BOM cost: **~\$2.40 - \$3.80 USD** per module.

---

## 19. Risks and Dependencies
- **Risk:** High-frequency noise pickup on long analog share bus cables between distant racks.  
  *Mitigation:* Shielded twisted-pair cabling and low-pass filtering at each module input ($f_c = 1\text{ kHz}$).

---

## 20. Future Scalability
- Future roadmap (MPC-200) targets fully wireless or optical fiber ring communication for multi-rack megawatt utility energy storage installations.
