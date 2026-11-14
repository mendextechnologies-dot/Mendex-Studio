from pathlib import Path
from copper_kicad.sch.model import Schematic
from copper_kicad.kicad.libs import read_symbol

def build_sv1000_authentic_sch():
    sch = Schematic.new("sv1000", paper="A3", title="SpectraVolt SV-1000 Precision High-Voltage Converter")
    
    # 1. Embed all required symbols from standard libraries
    libs_to_embed = [
        "Connector:Conn_01x02_Pin",
        "Device:C",
        "Device:D",
        "Device:R",
        "Device:Transformer_1P_2S",
        "Isolator:PC817",
        "Mechanical:MountingHole",
        "Regulator_Controller:UC3843_SOIC8",
        "Transistor_FET:Q_NMOS_GDS",
        "power:PWR_FLAG",
    ]
    keys = {}
    for lib_id in libs_to_embed:
        sym = read_symbol(lib_id)
        keys[lib_id] = sch.embed(sym)

    # 2. Place all symbols
    insts = {}
    def place(ref, lib_id, pos, rot=0, val=None, fp=""):
        inst = sch.add_symbol(
            keys[lib_id],
            lib_id,
            ref,
            pos,
            rot=rot,
            value=val or ref,
            fields={"Footprint": fp},
        )
        insts[ref] = inst
        return inst

    # --- PRIMARY POWER STAGE (Top-Left to Top-Middle) ---
    place("J1", "Connector:Conn_01x02_Pin", (40.64, 60.96), rot=0, val="Input DC 24V", fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")
    place("CIN", "Device:C", (68.58, 60.96), rot=0, val="22uF 50V Ceramic", fp="Capacitor_SMD:C_1210_3225Metric")
    place("RSTART", "Device:R", (93.98, 73.66), rot=0, val="220k 0.5W", fp="Resistor_SMD:R_1206_3216Metric")
    
    # Primary RCD Snubber
    place("RSNUB", "Device:R", (121.92, 38.10), rot=90, val="47k 2W", fp="Resistor_SMD:R_2512_6332Metric")
    place("CSNUB", "Device:C", (121.92, 48.26), rot=90, val="4.7nF 630V", fp="Capacitor_SMD:C_1206_3216Metric")
    place("DSNUB", "Device:D", (137.16, 43.18), rot=0, val="ES1J 600V", fp="Diode_SMD:D_SMA")

    # Flyback Transformer T1
    place("T1", "Device:Transformer_1P_2S", (165.10, 60.96), rot=0, val="Flyback Transformer Lp=474uH", fp="Transformer_THT:Transformer_Breve_TEZ-22x24")

    # Primary MOSFET & Current Sense
    place("Q1", "Transistor_FET:Q_NMOS_GDS", (142.24, 101.60), rot=0, val="C3M0065090J 900V SiC", fp="Package_TO_SOT_SMD:TO-252-2")
    place("RSENSE", "Device:R", (144.78, 127.00), rot=0, val="0.22R 2W", fp="Resistor_SMD:R_1206_3216Metric")
    place("RGS", "Device:R", (132.08, 114.30), rot=0, val="10k", fp="Resistor_SMD:R_0805_2012Metric")

    # --- SECONDARY HIGH-VOLTAGE OUTPUT STAGE (Top-Right) ---
    place("D1", "Device:D", (203.20, 50.80), rot=270, val="C3D02060A 3300V SiC", fp="Diode_THT:D_DO-201AE_P15.24mm_Horizontal")
    place("COUT", "Device:C", (241.30, 60.96), rot=0, val="100nF 1500V Foil", fp="Capacitor_THT:C_Rect_L18.0mm_W5.0mm_P15.00mm_FKS3_FKP3")
    place("J2", "Connector:Conn_01x02_Pin", (279.40, 60.96), rot=0, val="HV Output 1000V", fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical")

    # --- SECONDARY HV FEEDBACK DIVIDER CHAIN ---
    place("RFB1", "Device:R", (254.00, 93.98), rot=0, val="2.5M 1600V", fp="Resistor_SMD:R_1206_3216Metric")
    place("RFB2", "Device:R", (254.00, 114.30), rot=0, val="2.5M 1600V", fp="Resistor_SMD:R_1206_3216Metric")
    place("RFB3", "Device:R", (254.00, 134.62), rot=0, val="2.5M 1600V", fp="Resistor_SMD:R_1206_3216Metric")
    place("RFB4", "Device:R", (254.00, 154.94), rot=0, val="2.5M 1600V", fp="Resistor_SMD:R_1206_3216Metric")
    place("RDIVLO", "Device:R", (254.00, 175.26), rot=0, val="25k 0.1%", fp="Resistor_SMD:R_0805_2012Metric")
    place("ROPTOBIAS", "Device:R", (233.68, 165.10), rot=90, val="1k", fp="Resistor_SMD:R_0805_2012Metric")

    # --- GALVANIC ISOLATION OPTOCOUPLER ---
    place("U1", "Isolator:PC817", (203.20, 165.10), rot=0, val="PC817 Optocoupler", fp="Package_DIP:DIP-4_W7.62mm")

    # --- PWM CONTROLLER & GATE DRIVE ---
    place("U2", "Regulator_Controller:UC3843_SOIC8", (88.90, 165.10), rot=0, val="UC3843 Current Mode PWM", fp="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    place("RT", "Device:R", (55.88, 160.02), rot=0, val="10k", fp="Resistor_SMD:R_0805_2012Metric")
    place("CT", "Device:C", (55.88, 177.80), rot=0, val="1nF", fp="Capacitor_SMD:C_0805_2012Metric")
    place("ROPTOPULL", "Device:R", (71.12, 149.86), rot=0, val="4.7k", fp="Resistor_SMD:R_0805_2012Metric")
    
    # Gate Drive Network
    place("RGATE", "Device:R", (116.84, 165.10), rot=90, val="10R", fp="Resistor_SMD:R_0805_2012Metric")
    place("DGATE", "Device:D", (116.84, 175.26), rot=180, val="1N4148", fp="Diode_SMD:D_SOD-123")

    # Aux Bias Supply
    place("DAUX", "Device:D", (190.50, 83.82), rot=270, val="1N4937", fp="Diode_SMD:D_SMA")
    place("CAUX", "Device:C", (208.28, 93.98), rot=0, val="10uF 50V", fp="Capacitor_SMD:C_0805_2012Metric")

    # Mechanical Mounting Holes (Dedicated Mounting Box at bottom right)
    place("H1", "Mechanical:MountingHole", (330.20, 220.00), rot=0, val="M3 Mounting Hole", fp="MountingHole:MountingHole_3.2mm_M3")
    place("H2", "Mechanical:MountingHole", (355.60, 220.00), rot=0, val="M3 Mounting Hole", fp="MountingHole:MountingHole_3.2mm_M3")
    place("H3", "Mechanical:MountingHole", (330.20, 245.00), rot=0, val="M3 Mounting Hole", fp="MountingHole:MountingHole_3.2mm_M3")
    place("H4", "Mechanical:MountingHole", (355.60, 245.00), rot=0, val="M3 Mounting Hole", fp="MountingHole:MountingHole_3.2mm_M3")

    # Common Ground Buses Coordinates
    PRI_GND_Y = 195.58
    SEC_GND_Y = 195.58

    # Power Flags
    place("#FLG01", "power:PWR_FLAG", (45.72, 53.34), rot=0, val="PWR_FLAG") # VIN
    place("#FLG02", "power:PWR_FLAG", (45.72, 203.20), rot=180, val="PWR_FLAG") # PRI_GND
    place("#FLG03", "power:PWR_FLAG", (207.01, 45.72), rot=0, val="PWR_FLAG") # HV_OUT
    place("#FLG04", "power:PWR_FLAG", (279.40, SEC_GND_Y), rot=0, val="PWR_FLAG") # SEC_GND
    place("#FLG05", "power:PWR_FLAG", (88.90, 144.78), rot=0, val="PWR_FLAG") # VCC

    # Helper coordinate getters
    def pin_pos(ref, pin_num):
        inst = insts[ref]
        for p in inst.pins_world():
            if str(p["number"]) == str(pin_num):
                return tuple(p["xy"])
        raise ValueError(f"Pin {pin_num} not found on {ref}")

    def wire(p1, p2):
        sch.add_wire(p1, p2)

    def junction(pt):
        sch.add_junction(pt)

    # --- COMMON GROUND BUSES ---
    wire((45.72, PRI_GND_Y), (215.00, PRI_GND_Y))
    wire((45.72, PRI_GND_Y), pin_pos("#FLG02", 1))
    sch.add_label("PRI_GND", (100.00, PRI_GND_Y), angle=0)

    wire((215.90, SEC_GND_Y), (284.48, SEC_GND_Y))
    junction(pin_pos("#FLG04", 1))
    sch.add_label("SEC_GND", (260.00, SEC_GND_Y), angle=0)

    # --- PRIMARY INPUT WIRES ---
    j1_p1 = pin_pos("J1", 1)
    cin_p1 = pin_pos("CIN", 1)
    wire(j1_p1, (45.72, 57.15))
    wire((45.72, 57.15), cin_p1)
    junction((45.72, 57.15))
    wire((45.72, 57.15), pin_pos("#FLG01", 1))
    sch.add_label("VIN", (55.00, 57.15), angle=0)

    # J1 Pin 2 down to PRI_GND Bus
    j1_p2 = pin_pos("J1", 2)
    wire(j1_p2, (45.72, PRI_GND_Y))
    junction((45.72, PRI_GND_Y))

    # CIN Pin 2 down to PRI_GND Bus
    cin_p2 = pin_pos("CIN", 2)
    wire(cin_p2, (68.58, PRI_GND_Y))
    junction((68.58, PRI_GND_Y))

    # VIN rail extension to RSTART and T1 Pin 1
    rstart_p1 = pin_pos("RSTART", 1)
    t1_p1 = pin_pos("T1", 1)
    wire(cin_p1, (93.98, 57.15))
    junction(cin_p1)
    wire((93.98, 57.15), rstart_p1)
    junction((93.98, 57.15))
    wire((93.98, 57.15), (150.00, 57.15))
    wire((150.00, 57.15), (150.00, 66.04))
    wire((150.00, 66.04), t1_p1)

    # RSTART Pin 2 to VCC bus
    rstart_p2 = pin_pos("RSTART", 2)
    u2_vcc = pin_pos("U2", 7)
    wire(rstart_p2, (93.98, 149.86))
    wire((93.98, 149.86), (88.90, 149.86))
    wire((88.90, 149.86), u2_vcc)
    junction((88.90, 149.86))
    wire((88.90, 149.86), pin_pos("#FLG05", 1))
    sch.add_label("VCC", (98.00, 149.86), angle=0)

    # Snubber across Primary Winding (T1 Pin 1 to RSNUB/CSNUB, T1 Pin 2 to DSNUB)
    rsnub_p1 = pin_pos("RSNUB", 1)
    csnub_p1 = pin_pos("CSNUB", 1)
    wire((114.30, 57.15), (114.30, rsnub_p1[1]))
    junction((114.30, 57.15))
    wire((114.30, rsnub_p1[1]), rsnub_p1)
    wire((114.30, csnub_p1[1]), csnub_p1)
    junction((114.30, csnub_p1[1]))
    
    rsnub_p2 = pin_pos("RSNUB", 2)
    csnub_p2 = pin_pos("CSNUB", 2)
    dsnub_p2 = pin_pos("DSNUB", 2) # Cathode
    wire(rsnub_p2, (129.54, rsnub_p2[1]))
    wire(csnub_p2, (129.54, csnub_p2[1]))
    wire((129.54, rsnub_p2[1]), (129.54, csnub_p2[1]))
    wire((129.54, csnub_p2[1]), dsnub_p2)
    junction((129.54, csnub_p2[1]))
    sch.add_label("SNUB_NODE", (129.54, 35.00), angle=90)
    wire((129.54, rsnub_p2[1]), (129.54, 35.00))

    # T1 Pin 2 to Q1 Drain and DSNUB Anode
    t1_p2 = pin_pos("T1", 2)
    dsnub_p1 = pin_pos("DSNUB", 1) # Anode
    q1_d = pin_pos("Q1", 2)
    wire(dsnub_p1, (144.78, dsnub_p1[1]))
    wire((144.78, dsnub_p1[1]), (144.78, 55.88))
    wire((144.78, 55.88), t1_p2)
    wire((144.78, 55.88), q1_d)
    junction((144.78, 55.88))
    sch.add_label("PRI_DRAIN", (148.00, 75.00), angle=0)
    wire((144.78, 75.00), (148.00, 75.00))
    junction((144.78, 75.00))

    # Q1 Source to RSENSE Pin 1 and U2 ISENSE Pin 3
    q1_s = pin_pos("Q1", 3)
    rsense_p1 = pin_pos("RSENSE", 1)
    u2_isense = pin_pos("U2", 3)
    wire(q1_s, rsense_p1)
    junction(q1_s)
    wire(q1_s, (148.00, q1_s[1]))
    wire((148.00, q1_s[1]), (148.00, 170.18))
    wire((148.00, 170.18), (101.60, 170.18))
    wire((101.60, 170.18), u2_isense)
    sch.add_label("ISENSE", (148.00, 145.00), angle=0)

    # RSENSE Pin 2 to PRI_GND Bus
    rsense_p2 = pin_pos("RSENSE", 2)
    wire(rsense_p2, (144.78, PRI_GND_Y))
    junction((144.78, PRI_GND_Y))

    # Q1 Gate from Gate Network and RGS
    q1_g = pin_pos("Q1", 1)
    rgs_p1 = pin_pos("RGS", 1)
    rgs_p2 = pin_pos("RGS", 2)
    wire(q1_g, (132.08, q1_g[1]))
    wire((132.08, q1_g[1]), rgs_p1)
    junction((132.08, q1_g[1]))
    wire(rgs_p2, (132.08, PRI_GND_Y))
    junction((132.08, PRI_GND_Y))
    sch.add_label("GATE", (135.00, q1_g[1]), angle=0)

    # Gate Drive RGATE & DGATE from U2 OUT Pin 6
    u2_out = pin_pos("U2", 6)
    rgate_p1 = pin_pos("RGATE", 1)
    rgate_p2 = pin_pos("RGATE", 2)
    dgate_p1 = pin_pos("DGATE", 1)
    dgate_p2 = pin_pos("DGATE", 2)
    wire(u2_out, (109.22, u2_out[1]))
    wire((109.22, u2_out[1]), (109.22, rgate_p1[1]))
    wire((109.22, rgate_p1[1]), rgate_p1)
    junction((109.22, rgate_p1[1]))
    wire((109.22, rgate_p1[1]), (109.22, dgate_p1[1]))
    wire((109.22, dgate_p1[1]), dgate_p1)
    sch.add_label("GATE_DRV", (109.22, 160.00), angle=90)
    wire((109.22, u2_out[1]), (109.22, 160.00))
    
    wire(rgate_p2, (127.00, rgate_p2[1]))
    wire(dgate_p2, (127.00, dgate_p2[1]))
    wire((127.00, rgate_p2[1]), (127.00, dgate_p2[1]))
    wire((127.00, rgate_p2[1]), (127.00, 101.60))
    wire((127.00, 101.60), (132.08, 101.60))
    junction((127.00, rgate_p2[1]))

    # --- SECONDARY HIGH VOLTAGE OUTPUT WIRES ---
    t1_p3 = pin_pos("T1", 3)
    d1_p1 = pin_pos("D1", 1)
    d1_p2 = pin_pos("D1", 2)
    wire(t1_p3, d1_p1)

    cout_p1 = pin_pos("COUT", 1)
    j2_p1 = pin_pos("J2", 1)
    wire(d1_p2, (207.01, 53.34))
    wire((207.01, 53.34), (241.30, 53.34))
    wire((241.30, 53.34), cout_p1)
    junction((241.30, 53.34))
    wire((241.30, 53.34), (284.48, 53.34))
    wire((284.48, 53.34), j2_p1)
    junction((284.48, 53.34))
    wire((207.01, 53.34), pin_pos("#FLG03", 1))
    junction((207.01, 53.34))
    sch.add_label("HV_OUT", (260.00, 53.34), angle=0)

    # Secondary Ground Bus connections
    t1_p4 = pin_pos("T1", 4)
    cout_p2 = pin_pos("COUT", 2)
    j2_p2 = pin_pos("J2", 2)
    
    wire(t1_p4, (215.90, 58.42))
    wire((215.90, 58.42), (215.90, SEC_GND_Y))
    junction((215.90, SEC_GND_Y))

    wire(cout_p2, (241.30, SEC_GND_Y))
    junction((241.30, SEC_GND_Y))

    wire(j2_p2, (284.48, j2_p2[1]))
    wire((284.48, j2_p2[1]), (284.48, SEC_GND_Y))
    junction((284.48, SEC_GND_Y))

    # --- SECONDARY FEEDBACK DIVIDER CHAIN WIRES ---
    rfb1_p1 = pin_pos("RFB1", 1)
    rfb1_p2 = pin_pos("RFB1", 2)
    rfb2_p1 = pin_pos("RFB2", 1)
    rfb2_p2 = pin_pos("RFB2", 2)
    rfb3_p1 = pin_pos("RFB3", 1)
    rfb3_p2 = pin_pos("RFB3", 2)
    rfb4_p1 = pin_pos("RFB4", 1)
    rfb4_p2 = pin_pos("RFB4", 2)
    rdivlo_p1 = pin_pos("RDIVLO", 1)
    rdivlo_p2 = pin_pos("RDIVLO", 2)
    roptobias_p1 = pin_pos("ROPTOBIAS", 1)
    roptobias_p2 = pin_pos("ROPTOBIAS", 2)
    u1_p1 = pin_pos("U1", 1) # Anode
    u1_p2 = pin_pos("U1", 2) # Cathode
    u1_p3 = pin_pos("U1", 3) # Emitter
    u1_p4 = pin_pos("U1", 4) # Collector

    # Tap HV_OUT to RFB1 Pin 1
    wire((254.00, 53.34), rfb1_p1)
    junction((254.00, 53.34))
    
    # Series cascade
    wire(rfb1_p2, rfb2_p1)
    wire(rfb2_p2, rfb3_p1)
    wire(rfb3_p2, rfb4_p1)
    
    # RFB4 Pin 2 to RDIVLO Pin 1 and ROPTOBIAS Pin 1
    wire(rfb4_p2, (254.00, 165.10))
    wire((254.00, 165.10), rdivlo_p1)
    junction((254.00, 165.10))
    wire((254.00, 165.10), roptobias_p1)
    sch.add_label("FB_DIV", (257.00, 165.10), angle=0)
    
    # RDIVLO Pin 2 down to SEC_GND Bus
    wire(rdivlo_p2, (254.00, SEC_GND_Y))
    junction((254.00, SEC_GND_Y))

    # ROPTOBIAS Pin 2 to U1 Pin 1 Anode
    wire(roptobias_p2, u1_p1)
    sch.add_label("OPTO_A", (u1_p1[0], 160.00), angle=90)
    wire(u1_p1, (u1_p1[0], 160.00))

    # U1 Pin 2 Cathode down to SEC_GND Bus
    wire(u1_p2, (u1_p2[0], SEC_GND_Y))
    junction((u1_p2[0], SEC_GND_Y))

    # U1 Pin 3 Emitter down to PRI_GND Bus
    wire(u1_p3, (u1_p3[0], PRI_GND_Y))
    junction((u1_p3[0], PRI_GND_Y))

    # U1 Pin 4 Collector to COMP (U2 Pin 1) and ROPTOPULL
    u2_comp = pin_pos("U2", 1)
    roptopull_p1 = pin_pos("ROPTOPULL", 1)
    roptopull_p2 = pin_pos("ROPTOPULL", 2)
    wire(u1_p4, (210.82, u1_p4[1]))
    wire((210.82, u1_p4[1]), (210.82, 139.70))
    wire((210.82, 139.70), (71.12, 139.70))
    wire((71.12, 139.70), roptopull_p2)
    wire((71.12, 139.70), (71.12, u2_comp[1]))
    wire((71.12, u2_comp[1]), u2_comp)
    junction((71.12, 139.70))
    sch.add_label("COMP", (150.00, 139.70), angle=0)

    # ROPTOPULL Pin 1 to VREF (U2 Pin 8)
    u2_vref = pin_pos("U2", 8)
    wire(roptopull_p1, (71.12, 144.78))
    wire((71.12, 144.78), (63.50, 144.78))
    wire((63.50, 144.78), (63.50, u2_vref[1]))
    wire((63.50, u2_vref[1]), u2_vref)
    junction((63.50, u2_vref[1]))
    sch.add_label("VREF", (63.50, 140.00), angle=90)
    wire((63.50, 144.78), (63.50, 140.00))

    # RT to VREF and CT to PRI_GND
    rt_p1 = pin_pos("RT", 1)
    rt_p2 = pin_pos("RT", 2)
    ct_p1 = pin_pos("CT", 1)
    ct_p2 = pin_pos("CT", 2)
    u2_rtct = pin_pos("U2", 4)
    wire(rt_p1, (55.88, u2_vref[1]))
    wire((55.88, u2_vref[1]), (63.50, u2_vref[1]))
    junction((55.88, u2_vref[1]))
    
    wire(rt_p2, ct_p1)
    junction(rt_p2)
    wire(rt_p2, (55.88, u2_rtct[1]))
    wire((55.88, u2_rtct[1]), u2_rtct)
    sch.add_label("RT_CT", (50.00, u2_rtct[1]), angle=180)
    wire((55.88, u2_rtct[1]), (50.00, u2_rtct[1]))

    # CT Pin 2 down to PRI_GND Bus
    wire(ct_p2, (55.88, PRI_GND_Y))
    junction((55.88, PRI_GND_Y))

    # U2 Pin 2 (VFB) down to PRI_GND Bus
    u2_vfb = pin_pos("U2", 2)
    wire(u2_vfb, (68.58, u2_vfb[1]))
    wire((68.58, u2_vfb[1]), (68.58, PRI_GND_Y))
    junction((68.58, PRI_GND_Y))

    # U2 Pin 5 (GND) down to PRI_GND Bus
    u2_gnd = pin_pos("U2", 5)
    wire(u2_gnd, (u2_gnd[0], PRI_GND_Y))
    junction((u2_gnd[0], PRI_GND_Y))

    # Aux winding T1 Pin 5 to DAUX Anode, Pin 6 to PRI_GND Bus
    t1_p5 = pin_pos("T1", 5)
    t1_p6 = pin_pos("T1", 6)
    daux_p1 = pin_pos("DAUX", 1)
    daux_p2 = pin_pos("DAUX", 2)
    caux_p1 = pin_pos("CAUX", 1)
    caux_p2 = pin_pos("CAUX", 2)
    
    wire(t1_p5, (180.00, 63.50))
    wire((180.00, 63.50), (180.00, 83.82))
    wire((180.00, 83.82), daux_p1)
    sch.add_label("AUX_AC", (180.00, 75.00), angle=0)
    
    wire(daux_p2, (198.12, daux_p2[1]))
    wire((198.12, daux_p2[1]), (208.28, daux_p2[1]))
    wire((208.28, daux_p2[1]), caux_p1)
    junction((208.28, daux_p2[1]))
    wire((208.28, daux_p2[1]), (208.28, 149.86))
    wire((208.28, 149.86), (93.98, 149.86))
    junction((93.98, 149.86))

    # Aux Bottom Pin 6 down to PRI_GND Bus
    wire(t1_p6, (170.00, 71.12))
    wire((170.00, 71.12), (170.00, PRI_GND_Y))
    junction((170.00, PRI_GND_Y))
    
    # CAUX Pin 2 down to PRI_GND Bus
    wire(caux_p2, (208.28, PRI_GND_Y))
    junction((208.28, PRI_GND_Y))

    return sch.text()

out_sch = build_sv1000_authentic_sch()
Path("scratch/sv1000_clean_test.kicad_sch").write_text(out_sch, encoding="utf-8")
print("Regenerated with net labels!")
