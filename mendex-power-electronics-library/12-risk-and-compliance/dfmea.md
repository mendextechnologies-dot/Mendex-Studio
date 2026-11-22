# MPECL Design Failure Mode & Effects Analysis (DFMEA)

**Document ID:** MPECL-DOC-RSK-001  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  
**Methodology:** AIAG & VDA Failure Mode and Effects Analysis Standard  

---

## 1. DFMEA Scoring System & Thresholds

Severity ($S$), Occurrence ($O$), and Detection ($D$) are evaluated on a standard 1 to 10 scale:
* **Risk Priority Number (RPN):** $RPN = S \times O \times D$ (Range: $1\text{ to }1000$).
* **Action Priority Threshold:** Any item with **$S \ge 8$** (Safety / Fire Hazard / Lethal Voltage) or **$RPN \ge 120$** mandates immediate engineering prevention controls prior to design freeze.

---

## 2. Core System DFMEA Matrix

| Item / Module | Potential Failure Mode | Potential Effect of Failure | $S$ | Potential Causes | Current Prevention Controls | $O$ | Current Detection Controls | $D$ | $RPN$ | Recommended Engineering Action |
|---|---|---|---|---|---|---|---|---|---|---|
| **MDC-100** (Digital Controller) | Firmware task loop hangs during full-power operation | PWM duty cycle freezes at maximum; inductor saturates; destructive shoot-through | **9** | Unhandled pointer exception, stack overflow, or ESD clock glitch | Dedicated hardware watchdog timer resets MCU within $200\text{ ms}$; failsafe pull-downs on PWM pins | 3 | Hardware watchdog reset test; static code analysis (MISRA-C) | 3 | **81** | Hardware trip line (MSP-100) operates autonomously of MCU clock. |
| **MGD-100** (Gate Driver) | Cross-conduction shoot-through across half-bridge switches | Direct dead short across DC bus; catastrophic explosion of both power MOSFETs | **9** | Insufficient dead-time; parasitic $C_{gd} \cdot \frac{dv}{dt}$ induced gate turn-on | Hardware interlock logic prevents simultaneous high/low drive; Active Miller Clamp sinks gate current | 3 | Pre-power gate timing verification on 1 GHz scope; optical isolation | 2 | **54** | Enforce negative gate bias ($-4\text{ V}$) for all high-voltage SiC switches. |
| **MSM-100** (Sensing IP) | Current shunt solder joint fractures due to thermal cycling | Current feedback drops to zero; controller commands maximum duty cycle; overcurrent runaway | **9** | Solder joint fatigue from high thermal expansion mismatch in high-current shunts | Symmetrical PCB thermal copper balancing; large SMD pads | 2 | Redundant software overvoltage check; independent secondary primary CT sensor | 3 | **54** | Use dedicated 4-terminal metal-strip shunts with flexible gull-wing leads. |
| **MSP-100** (Protection IP) | Hardware trip comparator fails to trip during dead short | Sustained output short circuit; trace burnout, fire hazard | **10** | High-frequency ground bounce offsets comparator reference voltage | Local star-grounding to clean AGND; high-frequency decoupling capacitor at comparator pins | 2 | Pre-shipment automated short-circuit qualification test | 2 | **40** | Back up fast comparator with secondary slow-blow ceramic HBC fuse. |
| **MAP-100** (Aux Power) | Sustained Indian grid 440 VAC neutral-float overvoltage | Auxiliary flyback switcher explodes; complete loss of control power and cooling fans | **8** | Broken neutral in 3-phase industrial facility; 230V rail rises to 440V | 550V high-energy MOV surge clamp; 500V rated bulk electrolytic capacitors | 4 | Continuous bench 440 VAC soak test for 24 hours | 2 | **64** | Add auto-disconnect series depletion FET or voltage-dependent relay disconnect. |
| **MPS-100** (Buck Power) | High-side MOSFET fails short-circuit (drain-to-source) | Full unregulated input voltage ($48\text{ V}$) dumped directly onto $12\text{ V}$ load equipment | **8** | Over-voltage avalanche breakdown or thermal overheating | $25\%$ voltage derating margin ($100\text{ V}$ FET on $48\text{ V}$ bus); low thermal resistance heatsink | 3 | Fast output overvoltage comparator activates crowbar thyristor to blow fuse | 2 | **48** | Crowbar thyristor clamps output to ground in $< 2\,\mu\text{s}$, blowing input fuse safely. |
| **MPS-300** (Isolated LLC) | Loss of Zero-Voltage Switching (ZVS) at light load | Excessive turn-on capacitive switching losses; primary SiC switches overheat and fail | **7** | Insufficient resonant inductor energy to discharge switch $C_{oss}$ during dead-time | Adaptive dead-time lookup table in firmware; burst-mode operation at light load | 4 | Real-time heatsink temperature monitoring (MTM-100) triggers derating | 2 | **56** | Firmware transitions automatically to burst mode when load current $< 15\%$. |
| **MEM-100** (EMI Filter) | Common-mode choke core saturates under high pulse current | Attenuation drops by $> 30\text{ dB}$; severe conducted noise pollutes grid; fails EMC | **6** | Magnetic flux saturation in high-permeability ferrite under transient current | Select high-saturation flux density nanocrystalline cores ($B_{sat} \approx 1.2\text{ T}$) | 3 | Laboratory conducted emissions scan with CISPR 16 LISN | 2 | **36** | Nanocrystalline material provides $3\times$ higher saturation flux than standard ferrite. |
