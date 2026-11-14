import pytest
from pathlib import Path
from mendex_core.design.ir import (
    DesignIntermediateRepresentation,
    IRComponent,
    IRPin,
    ComponentType,
    IRParameter,
    IRMagneticGeometry,
)
from mendex_core.design.generators.kicad_generator import (
    KiCadSchematicGenerator,
    mendex_ir_to_copper_ops,
    resolve_symbol_lib_id,
    resolve_footprint,
)
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter


def build_complete_sv1000_ir() -> DesignIntermediateRepresentation:
    """Builds a complete, electrically fully wired DesignIntermediateRepresentation
    for the SpectraVolt SV-1000 Isolated Flyback Converter with:
    - Input power terminal J1
    - Input decoupling C_IN
    - Primary RCD snubber (D_SNUB, C_SNUB, R_SNUB)
    - Flyback Transformer T1 with Aux winding N_aux
    - Primary SiC MOSFET Q1
    - Current sense resistor R_SENSE
    - Gate drive network (R_GATE, D_GATE, R_GS)
    - Aux bias supply (D_AUX, C_AUX, R_START)
    - Primary Current-Mode PWM Controller U2 (UC3843)
    - Oscillator timing (R_T, C_T)
    - Isolated feedback optocoupler U1 (PC817) and primary pull-up R_OPTO_PULL
    - Secondary rectifier D1 and high-voltage filter C_OUT
    - Secondary high-voltage divider chain (R_FB1, R_FB2, R_FB3, R_FB4, R_DIV_LO)
    - Secondary optocoupler bias R_OPTO_BIAS
    - High-voltage output terminal J2
    """
    ir = DesignIntermediateRepresentation(
        title="SpectraVolt SV-1000 Precision High-Voltage Converter",
        topology="Quasi-Resonant Flyback",
        category="isolated_dcdc",
        parameters={
            "Vin": IRParameter(name="Vin", value=24.0, unit="V"),
            "Vout": IRParameter(name="Vout", value=1000.0, unit="V"),
            "Iout": IRParameter(name="Iout", value=0.001, unit="A"),
            "Fsw": IRParameter(name="Fsw", value=100000.0, unit="Hz"),
            "Lp": IRParameter(name="Lp", value=474.42e-6, unit="H"),
        },
        magnetic_geometry=IRMagneticGeometry(
            core_type="ETD34",
            core_material="N87",
            primary_turns=4,
            secondary_turns=233,
            air_gap_mm=0.10,
        ),
    )

    # 1. Terminations
    j1 = IRComponent(
        designator="J1",
        name="Input DC Terminal",
        type=ComponentType.CONNECTOR,
        pins=[IRPin(pin_id="1", name="VIN+"), IRPin(pin_id="2", name="VIN-")],
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )
    j2 = IRComponent(
        designator="J2",
        name="HV Output Terminal",
        type=ComponentType.CONNECTOR,
        pins=[IRPin(pin_id="1", name="HV+"), IRPin(pin_id="2", name="HV-")],
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )

    # 2. Input decoupling
    c_in = IRComponent(
        designator="C_IN",
        name="Input Filter Capacitor",
        type=ComponentType.CAPACITOR,
        value=22e-6,
        unit="F",
        pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
        footprint="Capacitor_SMD:C_1210_3225Metric",
    )

    # 3. Transformer with Auxiliary winding
    t1 = IRComponent(
        designator="T1",
        name="ETD34 Flyback Transformer with Aux",
        type=ComponentType.TRANSFORMER,
        value=474.42e-6,
        unit="H",
        pins=[
            IRPin(pin_id="1", name="PRI_DOT"),
            IRPin(pin_id="2", name="PRI_UNDOT"),
            IRPin(pin_id="3", name="SEC_UNDOT"),
            IRPin(pin_id="4", name="SEC_DOT"),
            IRPin(pin_id="5", name="AUX_DOT"),
            IRPin(pin_id="6", name="AUX_UNDOT"),
        ],
        footprint="Transformer_THT:Transformer_EPCOS_B66359J1014T_Vertical",
        parameters={"kicad_symbol": "Device:Transformer_1P_2S"},
    )

    # 4. Primary Switch & Current Sense
    q1 = IRComponent(
        designator="Q1",
        name="SiC Power MOSFET 1200V",
        type=ComponentType.SWITCH_SIC,
        pins=[IRPin(pin_id="1", name="G"), IRPin(pin_id="2", name="D"), IRPin(pin_id="3", name="S")],
        footprint="Package_TO_SOT_SMD:TO-252-2",
        parameters={"kicad_symbol": "Transistor_FET:Q_NMOS_GDS"},
    )
    r_sense = IRComponent(
        designator="R_SENSE",
        name="Current Sense Resistor 0.22R",
        type=ComponentType.RESISTOR,
        value=0.22,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )

    # 5. Gate Drive Network
    r_gate = IRComponent(
        designator="R_GATE",
        name="Gate Damping Resistor 10R",
        type=ComponentType.RESISTOR,
        value=10.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )
    d_gate = IRComponent(
        designator="D_GATE",
        name="Gate Fast Turn-off Diode",
        type=ComponentType.DIODE,
        pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
        footprint="Diode_SMD:D_SOD-123",
    )
    r_gs = IRComponent(
        designator="R_GS",
        name="Gate Pull-down Resistor 10k",
        type=ComponentType.RESISTOR,
        value=10000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )

    # 6. RCD Primary Snubber
    d_snub = IRComponent(
        designator="D_SNUB",
        name="Snubber Fast Recovery Diode 600V",
        type=ComponentType.DIODE,
        pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
        footprint="Diode_SMD:D_SMA",
    )
    c_snub = IRComponent(
        designator="C_SNUB",
        name="Snubber Ceramic Capacitor 4.7nF 100V",
        type=ComponentType.CAPACITOR,
        value=4.7e-9,
        unit="F",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Capacitor_SMD:C_0805_2012Metric",
    )
    r_snub = IRComponent(
        designator="R_SNUB",
        name="Snubber Bleed Resistor 47k 2W",
        type=ComponentType.RESISTOR,
        value=47000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )

    # 7. Auxiliary Bias Supply
    d_aux = IRComponent(
        designator="D_AUX",
        name="Auxiliary Rectifier Diode",
        type=ComponentType.DIODE,
        pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
        footprint="Diode_SMD:D_SOD-123",
    )
    c_aux = IRComponent(
        designator="C_AUX",
        name="VCC Bypass Capacitor 10uF 25V",
        type=ComponentType.CAPACITOR,
        value=10e-6,
        unit="F",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Capacitor_SMD:C_0805_2012Metric",
    )
    r_start = IRComponent(
        designator="R_START",
        name="Startup Trickle Resistor 220k",
        type=ComponentType.RESISTOR,
        value=220000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )

    # 8. Primary PWM Controller (UC3843)
    u2 = IRComponent(
        designator="U2",
        name="Current-Mode PWM Controller UC3843",
        type=ComponentType.IC_CONTROLLER,
        pins=[
            IRPin(pin_id="1", name="COMP"),
            IRPin(pin_id="2", name="VFB"),
            IRPin(pin_id="3", name="ISENSE"),
            IRPin(pin_id="4", name="RT_CT"),
            IRPin(pin_id="5", name="GND"),
            IRPin(pin_id="6", name="OUT"),
            IRPin(pin_id="7", name="VCC"),
            IRPin(pin_id="8", name="VREF"),
        ],
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        parameters={"kicad_symbol": "Regulator_Controller:UC3843_SOIC8"},
    )
    r_t = IRComponent(
        designator="R_T",
        name="Oscillator Timing Resistor 10k",
        type=ComponentType.RESISTOR,
        value=10000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )
    c_t = IRComponent(
        designator="C_T",
        name="Oscillator Timing Capacitor 1nF",
        type=ComponentType.CAPACITOR,
        value=1e-9,
        unit="F",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Capacitor_SMD:C_0805_2012Metric",
    )

    # 9. Isolated Feedback Optocoupler (PC817)
    u1 = IRComponent(
        designator="U1",
        name="Optocoupler PC817",
        type=ComponentType.OPTOCOUPLER,
        pins=[
            IRPin(pin_id="1", name="A"),
            IRPin(pin_id="2", name="K"),
            IRPin(pin_id="3", name="E"),
            IRPin(pin_id="4", name="C"),
        ],
        footprint="Package_DIP:DIP-4_W7.62mm",
        parameters={"kicad_symbol": "Isolator:PC817"},
    )
    r_opto_pull = IRComponent(
        designator="R_OPTO_PULL",
        name="Opto Pull-Up Resistor 4.7k",
        type=ComponentType.RESISTOR,
        value=4700.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )

    # 10. Secondary High-Voltage Rectifier & Output Filter
    d1 = IRComponent(
        designator="D1",
        name="HV SiC Schottky Rectifier 3300V",
        type=ComponentType.DIODE,
        pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
        footprint="Diode_THT:D_DO-201AE_P15.24mm_Horizontal",
    )
    c_out = IRComponent(
        designator="C_OUT",
        name="High-Voltage DC Output Capacitor 100nF 1500V",
        type=ComponentType.CAPACITOR,
        value=100e-9,
        unit="F",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Capacitor_THT:C_Rect_L18.0mm_W5.0mm_P15.00mm_FKS3_FKP3",
    )

    # 11. Secondary High-Voltage Divider Series Chain (4x 2.5M)
    r_fb1 = IRComponent(
        designator="R_FB1",
        name="HV Resistor 2.5M",
        type=ComponentType.RESISTOR,
        value=2.5e6,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )
    r_fb2 = IRComponent(
        designator="R_FB2",
        name="HV Resistor 2.5M",
        type=ComponentType.RESISTOR,
        value=2.5e6,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )
    r_fb3 = IRComponent(
        designator="R_FB3",
        name="HV Resistor 2.5M",
        type=ComponentType.RESISTOR,
        value=2.5e6,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )
    r_fb4 = IRComponent(
        designator="R_FB4",
        name="HV Resistor 2.5M",
        type=ComponentType.RESISTOR,
        value=2.5e6,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_1206_3216Metric",
    )
    r_div_lo = IRComponent(
        designator="R_DIV_LO",
        name="Lower Divider Resistor 25k",
        type=ComponentType.RESISTOR,
        value=25000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )
    r_opto_bias = IRComponent(
        designator="R_OPTO_BIAS",
        name="Opto Bias Resistor 1k",
        type=ComponentType.RESISTOR,
        value=1000.0,
        unit="Ohm",
        pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        footprint="Resistor_SMD:R_0805_2012Metric",
    )

    # 12. Mechanical Mounting Holes (M3)
    h1 = IRComponent(
        designator="H1",
        name="M3 Mounting Hole",
        type=ComponentType.CONNECTOR,
        pins=[],
        footprint="MountingHole:MountingHole_3.2mm_M3",
        parameters={"kicad_symbol": "Mechanical:MountingHole"},
    )
    h2 = IRComponent(
        designator="H2",
        name="M3 Mounting Hole",
        type=ComponentType.CONNECTOR,
        pins=[],
        footprint="MountingHole:MountingHole_3.2mm_M3",
        parameters={"kicad_symbol": "Mechanical:MountingHole"},
    )
    h3 = IRComponent(
        designator="H3",
        name="M3 Mounting Hole",
        type=ComponentType.CONNECTOR,
        pins=[],
        footprint="MountingHole:MountingHole_3.2mm_M3",
        parameters={"kicad_symbol": "Mechanical:MountingHole"},
    )
    h4 = IRComponent(
        designator="H4",
        name="M3 Mounting Hole",
        type=ComponentType.CONNECTOR,
        pins=[],
        footprint="MountingHole:MountingHole_3.2mm_M3",
        parameters={"kicad_symbol": "Mechanical:MountingHole"},
    )

    ir.components.extend([
        j1, j2, c_in, t1, q1, r_sense,
        r_gate, d_gate, r_gs,
        d_snub, c_snub, r_snub,
        d_aux, c_aux, r_start,
        u2, r_t, c_t,
        u1, r_opto_pull,
        d1, c_out,
        r_fb1, r_fb2, r_fb3, r_fb4, r_div_lo, r_opto_bias,
        h1, h2, h3, h4,
    ])

    # ---------------------------------------------------------
    # NET CONNECTIONS
    # ---------------------------------------------------------
    # Net: VIN (Power In)
    ir.add_net_connection("VIN", j1.id, "1")
    ir.add_net_connection("VIN", c_in.id, "1")
    ir.add_net_connection("VIN", t1.id, "1")
    ir.add_net_connection("VIN", c_snub.id, "1")
    ir.add_net_connection("VIN", r_snub.id, "1")
    ir.add_net_connection("VIN", r_start.id, "1")

    # Net: PRI_GND (Primary Ground)
    ir.add_net_connection("PRI_GND", j1.id, "2")
    ir.add_net_connection("PRI_GND", c_in.id, "2")
    ir.add_net_connection("PRI_GND", r_sense.id, "2")
    ir.add_net_connection("PRI_GND", r_gs.id, "2")
    ir.add_net_connection("PRI_GND", t1.id, "5")
    ir.add_net_connection("PRI_GND", c_aux.id, "2")
    ir.add_net_connection("PRI_GND", u2.id, "5")
    ir.add_net_connection("PRI_GND", u2.id, "2")
    ir.add_net_connection("PRI_GND", c_t.id, "2")
    ir.add_net_connection("PRI_GND", u1.id, "3")

    # Net: PRI_DRAIN (MOSFET Drain node)
    ir.add_net_connection("PRI_DRAIN", t1.id, "2")
    ir.add_net_connection("PRI_DRAIN", q1.id, "2")
    ir.add_net_connection("PRI_DRAIN", d_snub.id, "a")

    # Net: SNUB_NODE (RCD snubber node)
    ir.add_net_connection("SNUB_NODE", d_snub.id, "k")
    ir.add_net_connection("SNUB_NODE", c_snub.id, "2")
    ir.add_net_connection("SNUB_NODE", r_snub.id, "2")

    # Net: ISENSE (Current sense node)
    ir.add_net_connection("ISENSE", q1.id, "3")
    ir.add_net_connection("ISENSE", r_sense.id, "1")
    ir.add_net_connection("ISENSE", u2.id, "3")

    # Net: GATE_DRV (PWM controller output)
    ir.add_net_connection("GATE_DRV", u2.id, "6")
    ir.add_net_connection("GATE_DRV", r_gate.id, "1")
    ir.add_net_connection("GATE_DRV", d_gate.id, "k")

    # Net: GATE (MOSFET Gate pin)
    ir.add_net_connection("GATE", r_gate.id, "2")
    ir.add_net_connection("GATE", d_gate.id, "a")
    ir.add_net_connection("GATE", r_gs.id, "1")
    ir.add_net_connection("GATE", q1.id, "1")

    # Net: AUX_AC (Auxiliary winding node)
    ir.add_net_connection("AUX_AC", t1.id, "6")
    ir.add_net_connection("AUX_AC", d_aux.id, "a")

    # Net: VCC (PWM Controller positive supply)
    ir.add_net_connection("VCC", d_aux.id, "k")
    ir.add_net_connection("VCC", c_aux.id, "1")
    ir.add_net_connection("VCC", r_start.id, "2")
    ir.add_net_connection("VCC", u2.id, "7")

    # Net: VREF (5V Reference output)
    ir.add_net_connection("VREF", u2.id, "8")
    ir.add_net_connection("VREF", r_t.id, "1")
    ir.add_net_connection("VREF", r_opto_pull.id, "1")

    # Net: RT_CT (Oscillator timing node)
    ir.add_net_connection("RT_CT", u2.id, "4")
    ir.add_net_connection("RT_CT", r_t.id, "2")
    ir.add_net_connection("RT_CT", c_t.id, "1")

    # Net: COMP (PWM Feedback input)
    ir.add_net_connection("COMP", u2.id, "1")
    ir.add_net_connection("COMP", r_opto_pull.id, "2")
    ir.add_net_connection("COMP", u1.id, "4")

    # ---------------------------------------------------------
    # SECONDARY SIDE NETS (GALVANICALLY ISOLATED)
    # ---------------------------------------------------------
    # Net: SEC_ANODE (Secondary winding cathode return / AC anode)
    ir.add_net_connection("SEC_ANODE", t1.id, "4")
    ir.add_net_connection("SEC_ANODE", d1.id, "a")

    # Net: SEC_GND (Secondary High-Voltage Ground Return)
    ir.add_net_connection("SEC_GND", t1.id, "3")
    ir.add_net_connection("SEC_GND", c_out.id, "2")
    ir.add_net_connection("SEC_GND", r_div_lo.id, "2")
    ir.add_net_connection("SEC_GND", u1.id, "2")
    ir.add_net_connection("SEC_GND", j2.id, "2")

    # Net: HV_OUT (1000V DC Output)
    ir.add_net_connection("HV_OUT", d1.id, "k")
    ir.add_net_connection("HV_OUT", c_out.id, "1")
    ir.add_net_connection("HV_OUT", r_fb1.id, "1")
    ir.add_net_connection("HV_OUT", j2.id, "1")

    # High-Voltage Resistor Chain Taps
    ir.add_net_connection("FB_TAP1", r_fb1.id, "2")
    ir.add_net_connection("FB_TAP1", r_fb2.id, "1")

    ir.add_net_connection("FB_TAP2", r_fb2.id, "2")
    ir.add_net_connection("FB_TAP2", r_fb3.id, "1")

    ir.add_net_connection("FB_TAP3", r_fb3.id, "2")
    ir.add_net_connection("FB_TAP3", r_fb4.id, "1")

    # Net: FB_DIV (Divided feedback voltage node ~2.5V)
    ir.add_net_connection("FB_DIV", r_fb4.id, "2")
    ir.add_net_connection("FB_DIV", r_div_lo.id, "1")
    ir.add_net_connection("FB_DIV", r_opto_bias.id, "1")

    # Net: OPTO_A (Optocoupler LED Anode)
    ir.add_net_connection("OPTO_A", r_opto_bias.id, "2")
    ir.add_net_connection("OPTO_A", u1.id, "1")

    return ir


def test_build_complete_sv1000_ir_structure():
    ir = build_complete_sv1000_ir()
    assert len(ir.components) == 32
    assert len(ir.nets) == 20

    # Verify all components have non-empty pins (except pure mechanical mounting holes)
    for comp in ir.components:
        if comp.designator.startswith("H"):
            continue
        assert len(comp.pins) >= 2

    # Verify power rails and ground nets
    net_names = {n.name for n in ir.nets}
    assert "VIN" in net_names
    assert "PRI_GND" in net_names
    assert "HV_OUT" in net_names
    assert "SEC_GND" in net_names
    assert "VCC" in net_names
    assert "GATE_DRV" in net_names
    assert "GATE" in net_names

    ops = mendex_ir_to_copper_ops(ir)
    assert len(ops) >= 50

    # Verify place ops for critical components
    place_ops = {op["ref"]: op for op in ops if op.get("op") == "place"}
    assert "Q1" in place_ops
    assert place_ops["Q1"]["lib_id"] == "Transistor_FET:Q_NMOS_GDS"

    assert "U1" in place_ops
    assert place_ops["U1"]["lib_id"] == "Isolator:PC817"

    assert "U2" in place_ops
    assert place_ops["U2"]["lib_id"] == "Regulator_Controller:UC3843_SOIC8"

    assert "T1" in place_ops
    assert place_ops["T1"]["lib_id"] == "Device:Transformer_1P_2S"


def test_export_complete_sv1000_to_kicad(tmp_path: Path):
    """Verifies that the complete SV-1000 IR exports to native KiCad 10 with 0 ERC errors."""
    out_dir = tmp_path / "sv1000_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    ir = build_complete_sv1000_ir()
    res = KiCadSchematicGenerator.export_copper_project(
        ir,
        out_dir,
        board_size=(100.0, 75.0),
        auto_place=True,
        route=False,
    )

    assert res["ops_applied"] >= 50
    assert res["sync"] is True

    # Run native KiCad 10 ERC
    adapter = CopperKiCadAdapter()
    erc = adapter.run_erc(Path(res["schematic"]))
    assert erc.get("error_count", 0) == 0, f"ERC had errors: {erc.get('sheets')}"
