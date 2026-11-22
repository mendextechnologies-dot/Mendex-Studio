# MPECL Human Machine Interface (HMI) Specification

**Document ID:** MPECL-DOC-MCN-003  
**Revision:** v1.0  
**Status:** APPROVED FOR DESIGN  
**Target Organization:** Mendex Electronics LLP  

---

## 1. Overview & Mechanical Enclosure Decoupling

The **MHM-100 Human Machine Interface** module provides direct local operator control and visual status monitoring for benchtop, rackmount, and industrial cabinet installations.

To ensure that front-panel industrial design variations do not require redesigning the internal power motherboard, MHM-100 is engineered as an independent front-panel daughter assembly communicating over an isolated $4\text{-wire}$ or $10\text{-pin}$ ribbon cable.

```mermaid
graph LR
    subgraph Front_Panel_Assembly ["MHM-100 Front Panel Assembly"]
        DISP["Graphical Display<br/>(128x64 Monochrome OLED / 3.5-inch Color TFT)"]
        ENCODER["Optical / Mechanical Rotary Encoder<br/>(Fine & Coarse Parameter Adjustment)"]
        BUTTONS["Illuminated Tactile Pushbuttons<br/>(Output ON/OFF, Menu, Esc, Voltage/Current Select)"]
        LEDS["Discrete High-Visibility Status LEDs<br/>(Green: CV Mode, Orange: CC Mode, Red: Fault)"]
    end

    subgraph Internal_Controller ["MDC-100 Universal Controller"]
        MCU_I2C["Dedicated I2C / SPI Bus + 3x Interrupt Lines"]
    end

    DISP <-->|I2C / SPI| MCU_I2C
    ENCODER -->|Quadrature A/B + Push Switch| MCU_I2C
    BUTTONS -->|Debounced GPIO| MCU_I2C
    LEDS <--|Direct Drive / I2C Expander| MCU_I2C
```

---

## 2. Display Technologies & Driver Options

MHM-100 specifies two standardized display variants:

| Variant | Display Technology | Resolution / Size | Controller IC | Interface | Target Applications |
|---|---|---|---|---|---|
| **MHM-100-A** | High-Contrast White OLED | $128 \times 64$ pixels ($0.96"$ or $1.3"$) | SSD1306 / SH1106 | I2C ($400\text{ kHz}$) or 4-wire SPI | Low-cost industrial DIN-rail power supplies, compact chargers |
| **MHM-100-B** | Full-Color Sunlight Readable TFT | $320 \times 480$ pixels ($3.5"$) | ILI9488 / ST7796 | High-speed SPI ($30\text{ MHz}$) | High-end laboratory power supplies, dual-output programmable supplies |

---

## 3. Operator Interface Ergonomics & Parameter Adjustment

1. **Dual-Rate Rotary Knob Algorithm:**
   - Turning the encoder slowly increments/decrements setpoints by the finest resolution ($10\text{ mV}$ or $10\text{ mA}$).
   - Turning the encoder quickly (acceleration detection in firmware) multiplies the step size by $\times 10$ or $\times 100$ ($1.0\text{ V}$ or $1.0\text{ A}$ steps), enabling rapid navigation across wide output ranges.
2. **Dedicated Physical "Output Enable" Button:**
   - Independent physical latching/tactile push button with ring LED illumination.
   - Red backlight indicates Output OFF (Safe Standby). Green backlight indicates Output Active (Energized).
3. **Immediate Mode Annunciation:**
   - Green LED: Constant Voltage (CV) Active.
   - Amber / Yellow LED: Constant Current (CC) Clamped.
   - Flashing Red LED: Trip Zone Active (Fault Latch).
