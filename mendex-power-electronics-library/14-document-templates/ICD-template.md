# Interface Control Document (ICD) Template

**Document ID:** MPECL-ICD-XXX-001  
**Revision:** vX.X  
**Status:** DRAFT | UNDER REVIEW | APPROVED FOR DESIGN | RELEASED  
**Target Organization:** Mendex Electronics LLP  
**Systems Integration Lead:** `[Name / Title]`  

---

## 1. Interface Scope & Mechanical Mating
* Physical connectors (Type, manufacturer part number, pitch, pin count).
* Mating orientation, polarizing keys, and mechanical retention hardware.

---

## 2. Pinout Definition Table
| Pin # | Signal Name | Electrical Class | Direction (In/Out/Bidir) | Voltage Levels | Impedance / Load | Description |
|---|---|---|---|---|---|---|
| 1 | `+5V_AUX` | Class E | Power In | $+5.0\text{ V} \pm 5\%$ | $\ge 2.0\text{ A}$ | Auxiliary power input |
| 2 | `DGND` | Return | Return | $0\text{ V}$ Ref | Low-impedance | Digital logic return |
| 3 | `PWM1_H` | Class A | Output | $3.3\text{ V}$ LVCMOS | $Z_0 = 50\,\Omega$ | High-side gate command |
| 4 | `PWM1_L` | Class A | Output | $3.3\text{ V}$ LVCMOS | $Z_0 = 50\,\Omega$ | Low-side gate command |
| 5 | `/TRIP_ZONE` | Class C | Input | $0 - 3.3\text{ V}$ Open-Drain | $2.2\text{ k}\Omega$ pull-up | Active-low trip line |
| 6 | `V_SENSE_P` | Class B | Input | $0 - 3.0\text{ V}$ Diff | $\ge 100\text{ k}\Omega$ | Voltage feedback positive |
| 7 | `V_SENSE_N` | Class B | Input | $0 - 3.0\text{ V}$ Diff | $\ge 100\text{ k}\Omega$ | Voltage feedback negative |

---

## 3. Grounding & Isolation Boundaries
* Isolation barrier diagram delineating SELV, Primary, Secondary, and Chassis grounds.
* Dielectric test voltage requirements ($V_{test}$ in $V_{RMS}$).

---

## 4. Signal Timing Diagrams
* Setup and hold times for SPI/I2C communication.
* Minimum dead-time margin between complementary PWM outputs.
