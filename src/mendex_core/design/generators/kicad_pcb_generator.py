"""Populated KiCad PCB Generator for Mendex Engineering Studio v2.0.

Compiles Design Intermediate Representation (IR) into a populated KiCad .kicad_pcb
file with board boundaries (Edge.Cuts), component footprints, netlist connectivity,
silkscreen fabrication graphics, 3D model links, and design rules conforming to KiCad 7/8/9/10 syntax.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from ..ir import DesignIntermediateRepresentation, ComponentType, IRComponent


FOOTPRINT_3D_MODEL_MAP: Dict[str, str] = {
    # TO/SOT Packages
    "Package_TO_SOT_SMD:TO-252-2": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/TO-252-2.step",
    "Package_TO_SOT_SMD:TO-263-2": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/TO-263-2.step",
    "Package_TO_SOT_SMD:SOT-223-3_TabPin2": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/SOT-223-3_TabPin2.step",
    "Package_TO_SOT_SMD:SOT-23": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/SOT-23.step",
    "Package_TO_SOT_THT:TO-220-3_Vertical": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-3_Vertical.step",
    "Package_TO_SOT_THT:TO-220-2_Vertical": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-2_Vertical.step",
    "Package_TO_SOT_THT:TO-247-3_Vertical": "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-247-3_Vertical.step",

    # SOIC / SO / DIP Packages
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm": "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step",
    "Package_SO:SO-8_3.9x4.9mm_P1.27mm": "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step",
    "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm": "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-16_3.9x9.9mm_P1.27mm.step",
    "Package_DIP:DIP-8_W7.62mm": "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm.step",
    "Package_DIP:DIP-14_W7.62mm": "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-14_W7.62mm.step",
    "Package_DIP:DIP-16_W7.62mm": "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-16_W7.62mm.step",

    # SMD Capacitors
    "Capacitor_SMD:C_0402_1005Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0402_1005Metric.step",
    "Capacitor_SMD:C_0603_1608Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0603_1608Metric.step",
    "Capacitor_SMD:C_0805_2012Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0805_2012Metric.step",
    "Capacitor_SMD:C_1206_3216Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1206_3216Metric.step",
    "Capacitor_SMD:C_1210_3225Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1210_3225Metric.step",
    "Capacitor_SMD:C_1812_4532Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1812_4532Metric.step",
    "Capacitor_SMD:C_2220_5650Metric": "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_2220_5650Metric.step",

    # THT Radial Polarized Capacitors
    "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D5.0mm_P2.50mm.step",
    "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D8.0mm_P3.50mm.step",
    "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D10.0mm_P5.00mm.step",
    "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D12.5mm_P5.00mm.step",
    "Capacitor_THT:CP_Radial_D16.0mm_P7.50mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D16.0mm_P7.50mm.step",
    "Capacitor_THT:CP_Radial_D18.0mm_P7.50mm": "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D18.0mm_P7.50mm.step",

    # SMD Resistors
    "Resistor_SMD:R_0402_1005Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0402_1005Metric.step",
    "Resistor_SMD:R_0603_1608Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0603_1608Metric.step",
    "Resistor_SMD:R_0805_2012Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805_2012Metric.step",
    "Resistor_SMD:R_1206_3216Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_1206_3216Metric.step",
    "Resistor_SMD:R_1210_3225Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_1210_3225Metric.step",
    "Resistor_SMD:R_2010_5025Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_2010_5025Metric.step",
    "Resistor_SMD:R_2512_6332Metric": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_2512_6332Metric.step",

    # THT Resistors
    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal": "${KICAD10_3DMODEL_DIR}/Resistor_THT.3dshapes/R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal.step",

    # Diodes
    "Diode_SMD:D_SMA": "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMA.step",
    "Diode_SMD:D_SMB": "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMB.step",
    "Diode_SMD:D_SMC": "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMC.step",
    "Diode_SMD:D_SOD-123": "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SOD-123.step",
    "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal": "${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/D_DO-41_SOD81_P10.16mm_Horizontal.step",
    "Diode_THT:D_DO-15_P10.16mm_Horizontal": "${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/D_DO-15_P10.16mm_Horizontal.step",
    "Diode_THT:Diode_Bridge_19.0x3.5mm_P5.1mm": "${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/Diode_Bridge_19.0x3.5mm_P5.1mm.step",

    # Terminal Blocks & Connectors
    "TerminalBlock:TerminalBlock_bornier-2_P5.08mm": "${KICAD10_3DMODEL_DIR}/TerminalBlock_Phoenix.3dshapes/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step",
    "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal": "${KICAD10_3DMODEL_DIR}/TerminalBlock_Phoenix.3dshapes/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step",
    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical": "${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step",
    "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical": "${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x03_P2.54mm_Vertical.step",

    # Switches & Buttons
    "Button_Switch_THT:SW_PUSH_6mm": "${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/SW_PUSH_6mm.step",
    "Button_Switch_SMD:SW_SPST_PTS645": "${KICAD10_3DMODEL_DIR}/Button_Switch_SMD.3dshapes/SW_SPST_PTS645.step",

    # Magnetics / Transformers / Inductors
    "Transformer_THT:Transformer_ETD34_Vertical": "${KICAD10_3DMODEL_DIR}/Transformer_THT.3dshapes/Transformer_37x44.step",
    "Inductor_SMD:L_12x12mm_H8mm": "${KICAD10_3DMODEL_DIR}/Inductor_SMD.3dshapes/L_12x12mm_H8mm.step",
}


def resolve_3d_model(fp_name: str, comp_type: ComponentType, comp_name: str = "") -> Optional[str]:
    """Resolves the installed KiCad 3D model STEP path for a footprint."""
    if fp_name in FOOTPRINT_3D_MODEL_MAP:
        return FOOTPRINT_3D_MODEL_MAP[fp_name]

    low_fp = fp_name.lower()
    low_name = comp_name.lower()

    if "to-252" in low_fp or "dpack" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/TO-252-2.step"
    if "to-220" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-3_Vertical.step"
    if "to-247" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-247-3_Vertical.step"
    if "soic-8" in low_fp or "so-8" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step"
    if "dip-8" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm.step"
    if "dip-14" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-14_W7.62mm.step"
    if "dip-16" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-16_W7.62mm.step"
    if "cp_radial" in low_fp or "radial" in low_fp:
        if "d18" in low_fp:
            return "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D18.0mm_P7.50mm.step"
        return "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D10.0mm_P5.00mm.step"
    if "bornier" in low_fp or "terminalblock" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/TerminalBlock_Phoenix.3dshapes/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step"
    if "bridge" in low_fp or "bridge" in low_name:
        return "${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/Diode_Bridge_19.0x3.5mm_P5.1mm.step"
    if "sw_push" in low_fp or "button" in low_name:
        return "${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/SW_PUSH_6mm.step"
    if "etd34" in low_fp or "etd" in low_name or "transformer" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Transformer_THT.3dshapes/Transformer_37x44.step"
    if "sma" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMA.step"
    if "smb" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMB.step"
    if "2512" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_2512_6332Metric.step"
    if "1812" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1812_4532Metric.step"
    if "1210" in low_fp:
        return "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1210_3225Metric.step"
    if "1206" in low_fp:
        if comp_type in (ComponentType.CAPACITOR, ComponentType.CAPACITOR_POLARIZED):
            return "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_1206_3216Metric.step"
        return "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_1206_3216Metric.step"
    if "0805" in low_fp:
        if comp_type in (ComponentType.CAPACITOR, ComponentType.CAPACITOR_POLARIZED):
            return "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0805_2012Metric.step"
        return "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805_2012Metric.step"

    # ComponentType fallback
    if comp_type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_SIC, ComponentType.SWITCH_GAN):
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/TO-252-2.step"
    if comp_type == ComponentType.SWITCH_IGBT:
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-3_Vertical.step"
    if comp_type == ComponentType.REGULATOR_LINEAR:
        return "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_THT.3dshapes/TO-220-3_Vertical.step"
    if comp_type in (ComponentType.GATE_DRIVER, ComponentType.OPTOCOUPLER, ComponentType.IC_CONTROLLER, ComponentType.IC_LOGIC):
        return "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-8_W7.62mm.step"
    if comp_type == ComponentType.CAPACITOR_POLARIZED:
        return "${KICAD10_3DMODEL_DIR}/Capacitor_THT.3dshapes/CP_Radial_D10.0mm_P5.00mm.step"
    if comp_type == ComponentType.CAPACITOR:
        return "${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0805_2012Metric.step"
    if comp_type == ComponentType.DIODE:
        return "${KICAD10_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMA.step"
    if comp_type == ComponentType.BRIDGE_RECTIFIER:
        return "${KICAD10_3DMODEL_DIR}/Diode_THT.3dshapes/Diode_Bridge_19.0x3.5mm_P5.1mm.step"
    if comp_type == ComponentType.CONNECTOR:
        return "${KICAD10_3DMODEL_DIR}/TerminalBlock_Phoenix.3dshapes/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step"
    if comp_type == ComponentType.SWITCH_PUSH:
        return "${KICAD10_3DMODEL_DIR}/Button_Switch_THT.3dshapes/SW_PUSH_6mm.step"
    if comp_type == ComponentType.TRANSFORMER:
        return "${KICAD10_3DMODEL_DIR}/Transformer_THT.3dshapes/Transformer_37x44.step"
    if comp_type == ComponentType.RESISTOR:
        return "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805_2012Metric.step"

    return "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805_2012Metric.step"


def _generate_footprint_pads(
    fp_name: str,
    comp: IRComponent,
    comp_pin_to_net: Dict[Tuple[str, str], Tuple[int, str]],
) -> List[str]:
    """Generates realistic pad geometry conforming to KiCad IPC standards."""
    pad_lines: List[str] = []
    low_fp = fp_name.lower()
    pins = [str(p.pin_id) for p in comp.pins] if comp.pins else []

    def get_net_expr(pid: str) -> str:
        net_info = comp_pin_to_net.get((comp.id, pid), (0, ""))
        return f'(net {net_info[0]} "{net_info[1]}")' if net_info[0] > 0 else '(net 0 "")'

    # 1. TO-252-2 (D-PAK)
    if "to-252" in low_fp or "dpack" in low_fp:
        # Gate (pin 1), Tab/Drain (pin 2), Source (pin 3)
        pad_lines.append(f'    (pad "1" smd roundrect (at -2.28 -2.5) (size 1.14 2.0) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" smd roundrect (at 0.0 2.2) (size 6.0 5.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr("2")})')
        pad_lines.append(f'    (pad "3" smd roundrect (at 2.28 -2.5) (size 1.14 2.0) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr("3")})')
        return pad_lines

    # 2. TO-220-3 Vertical (THT Linear Regulators, Transistors)
    if "to-220" in low_fp:
        pad_lines.append(f'    (pad "1" thru_hole rect (at -2.54 0.0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" thru_hole circle (at 0.0 0.0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("2")})')
        pad_lines.append(f'    (pad "3" thru_hole circle (at 2.54 0.0) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("3")})')
        return pad_lines

    # 3. DIP-8 / SOIC-8 (Dual In-Line / SOIC 8-pin)
    if "dip-8" in low_fp or "soic-8" in low_fp or "so-8" in low_fp or comp.type in (ComponentType.GATE_DRIVER, ComponentType.OPTOCOUPLER):
        is_tht = "dip" in low_fp
        for i in range(4):
            pid = str(i + 1)
            y = -1.905 + i * 1.27 if not is_tht else -3.81 + i * 2.54
            x = -2.47 if not is_tht else -3.81
            if is_tht:
                shape = "rect" if i == 0 else "circle"
                pad_lines.append(f'    (pad "{pid}" thru_hole {shape} (at {x:.2f} {y:.2f}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask") {get_net_expr(pid)})')
            else:
                pad_lines.append(f'    (pad "{pid}" smd roundrect (at {x:.2f} {y:.2f}) (size 1.55 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr(pid)})')
        for i in range(4):
            pid = str(8 - i)
            y = -1.905 + i * 1.27 if not is_tht else -3.81 + i * 2.54
            x = 2.47 if not is_tht else 3.81
            if is_tht:
                pad_lines.append(f'    (pad "{pid}" thru_hole circle (at {x:.2f} {y:.2f}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask") {get_net_expr(pid)})')
            else:
                pad_lines.append(f'    (pad "{pid}" smd roundrect (at {x:.2f} {y:.2f}) (size 1.55 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr(pid)})')
        return pad_lines

    # 4. DIP-16 (Logic ICs, e.g. 74HC123)
    if "dip-16" in low_fp or comp.type == ComponentType.IC_LOGIC:
        for i in range(8):
            pid = str(i + 1)
            y = -8.89 + i * 2.54
            shape = "rect" if i == 0 else "circle"
            pad_lines.append(f'    (pad "{pid}" thru_hole {shape} (at -3.81 {y:.2f}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask") {get_net_expr(pid)})')
        for i in range(8):
            pid = str(16 - i)
            y = -8.89 + i * 2.54
            pad_lines.append(f'    (pad "{pid}" thru_hole circle (at 3.81 {y:.2f}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask") {get_net_expr(pid)})')
        return pad_lines

    # 5. Radial Polarized Capacitor (THT)
    if "cp_radial" in low_fp or comp.type == ComponentType.CAPACITOR_POLARIZED:
        pitch = 7.5 if "d18" in low_fp else 5.0
        hp = pitch / 2.0
        pad_lines.append(f'    (pad "1" thru_hole rect (at {-hp:.2f} 0.0) (size 2.0 2.0) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" thru_hole circle (at {hp:.2f} 0.0) (size 2.0 2.0) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("2")})')
        return pad_lines

    # 6. Terminal Block (2-pin, 5.08mm pitch)
    if "bornier" in low_fp or "terminalblock" in low_fp or comp.type == ComponentType.CONNECTOR:
        pad_lines.append(f'    (pad "1" thru_hole rect (at -2.54 0.0) (size 2.5 2.5) (drill 1.3) (layers "*.Cu" "*.Mask") {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" thru_hole circle (at 2.54 0.0) (size 2.5 2.5) (drill 1.3) (layers "*.Cu" "*.Mask") {get_net_expr("2")})')
        return pad_lines

    # 7. Bridge Rectifier (4-pin THT)
    if "bridge" in low_fp or comp.type == ComponentType.BRIDGE_RECTIFIER:
        pad_lines.append(f'    (pad "1" thru_hole rect (at -7.65 0.0) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask") {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" thru_hole circle (at -2.55 0.0) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask") {get_net_expr("2")})')
        pad_lines.append(f'    (pad "3" thru_hole circle (at 2.55 0.0) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask") {get_net_expr("3")})')
        pad_lines.append(f'    (pad "4" thru_hole circle (at 7.65 0.0) (size 2.2 2.2) (drill 1.2) (layers "*.Cu" "*.Mask") {get_net_expr("4")})')
        return pad_lines

    # 8. Push Button (2-pin / 4-pin THT)
    if "sw_push" in low_fp or comp.type == ComponentType.SWITCH_PUSH:
        pad_lines.append(f'    (pad "1" thru_hole rect (at -3.25 -2.25) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("1")})')
        pad_lines.append(f'    (pad "2" thru_hole circle (at 3.25 -2.25) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("2")})')
        pad_lines.append(f'    (pad "3" thru_hole circle (at -3.25 2.25) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("3")})')
        pad_lines.append(f'    (pad "4" thru_hole circle (at 3.25 2.25) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask") {get_net_expr("4")})')
        return pad_lines

    # 9. Standard 2-pin SMD Components (0805, 1206, 1210, 1812, 2512, SMA, SMB, SMC)
    pin_ids = pins if pins else ["1", "2"]
    if "2512" in low_fp:
        offset_x, sz_x, sz_y = 2.8, 1.15, 3.2
    elif "1812" in low_fp:
        offset_x, sz_x, sz_y = 2.0, 1.0, 3.2
    elif "1210" in low_fp:
        offset_x, sz_x, sz_y = 1.45, 1.0, 2.5
    elif "1206" in low_fp:
        offset_x, sz_x, sz_y = 1.45, 1.0, 1.6
    elif "sma" in low_fp:
        offset_x, sz_x, sz_y = 2.15, 1.5, 1.8
    else:  # 0805 default
        offset_x, sz_x, sz_y = 0.95, 1.0, 1.3

    for p_idx, pid in enumerate(pin_ids[:2]):
        ox = -offset_x if p_idx == 0 else offset_x
        pad_lines.append(
            f'    (pad "{pid}" smd roundrect (at {ox:.2f} 0.0) (size {sz_x:.2f} {sz_y:.2f}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr(pid)})'
        )

    # If component has extra pins beyond 2, generate additional standard pads
    for p_idx, pid in enumerate(pin_ids[2:], start=2):
        oy = 1.2 if p_idx % 2 == 0 else -1.2
        pad_lines.append(
            f'    (pad "{pid}" smd roundrect (at 0.0 {oy:.2f}) (size 1.0 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {get_net_expr(pid)})'
        )

    return pad_lines


def _generate_silkscreen_graphics(fp_name: str, comp: IRComponent) -> List[str]:
    """Generates silkscreen outlines and polarity markers for KiCad 3D/2D views."""
    lines: List[str] = []
    low_fp = fp_name.lower()

    if "cp_radial" in low_fp or comp.type == ComponentType.CAPACITOR_POLARIZED:
        radius = 9.0 if "d18" in low_fp else 5.0
        lines.append(f'    (fp_circle (center 0 0) (end {radius:.2f} 0) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
        # Polarity plus sign
        lines.append(f'    (fp_line (start -3.5 1.5) (end -1.5 1.5) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
        lines.append(f'    (fp_line (start -2.5 0.5) (end -2.5 2.5) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
    elif "to-220" in low_fp:
        # Heatsink tab and body outline
        lines.append(f'    (fp_rect (start -5.2 -2.8) (end 5.2 2.2) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
        lines.append(f'    (fp_line (start -5.2 -1.8) (end 5.2 -1.8) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
    elif "to-252" in low_fp or "dpack" in low_fp:
        lines.append(f'    (fp_rect (start -3.3 -3.5) (end 3.3 4.5) (stroke (width 0.12) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
    elif "bornier" in low_fp or "terminalblock" in low_fp or comp.type == ComponentType.CONNECTOR:
        lines.append(f'    (fp_rect (start -5.2 -4.0) (end 5.2 4.0) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
    elif "dip" in low_fp or "soic" in low_fp or "so-8" in low_fp:
        h = 10.0 if "16" in low_fp else 5.0
        lines.append(f'    (fp_rect (start -3.0 {-h:.2f}) (end 3.0 {h:.2f}) (stroke (width 0.12) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
        lines.append(f'    (fp_circle (center -2.0 {-h + 1.0:.2f}) (end -1.7 {-h + 1.0:.2f}) (stroke (width 0.15) (type solid)) (layer "F.SilkS") (uuid "{uuid4()}"))')
    return lines



def _get_pad_offsets(fp_name: str) -> Dict[str, Tuple[float, float]]:
    """Calculates physical pad relative offsets for routing trace endpoints."""
    low = fp_name.lower()
    if "to-252" in low or "dpack" in low:
        return {"1": (-2.28, -2.5), "2": (0.0, 2.2), "3": (2.28, -2.5)}
    if "to-220" in low:
        return {"1": (-2.54, 0.0), "2": (0.0, 0.0), "3": (2.54, 0.0)}
    if "to-247" in low:
        return {"1": (-5.45, 0.0), "2": (0.0, 0.0), "3": (5.45, 0.0)}
    if "cp_radial" in low:
        return {"1": (-2.5, 0.0), "2": (2.5, 0.0)}
    if "terminalblock" in low or "bornier" in low:
        return {"1": (-2.54, 0.0), "2": (2.54, 0.0)}
    if "pinheader_1x02" in low:
        return {"1": (0.0, -1.27), "2": (0.0, 1.27)}
    if "pinheader_1x03" in low:
        return {"1": (0.0, -2.54), "2": (0.0, 0.0), "3": (0.0, 2.54)}
    if "dip-8" in low:
        return {
            "1": (-3.81, -3.81), "2": (-3.81, -1.27), "3": (-3.81, 1.27), "4": (-3.81, 3.81),
            "5": (3.81, 3.81), "6": (3.81, 1.27), "7": (3.81, -1.27), "8": (3.81, -3.81)
        }
    if "dip-16" in low or "soic-16" in low:
        res = {}
        for p in range(1, 9):
            res[str(p)] = (-3.81, -8.89 + (p - 1) * 2.54)
        for p in range(9, 17):
            res[str(p)] = (3.81, 8.89 - (p - 9) * 2.54)
        return res
    if "soic-8" in low or "so-8" in low:
        return {
            "1": (-2.6, -1.905), "2": (-2.6, -0.635), "3": (-2.6, 0.635), "4": (-2.6, 1.905),
            "5": (2.6, 1.905), "6": (2.6, 0.635), "7": (2.6, -0.635), "8": (2.6, -1.905)
        }
    if "sw_push" in low:
        return {"1": (-3.25, -2.25), "2": (3.25, -2.25), "3": (-3.25, 2.25), "4": (3.25, 2.25)}
    if "transformer" in low:
        return {"1": (-10.0, -10.0), "2": (-10.0, 10.0), "3": (10.0, -10.0), "4": (10.0, 10.0)}
    if "diode_bridge" in low:
        return {"1": (-5.0, 0.0), "2": (0.0, 0.0), "3": (5.0, 0.0), "4": (10.0, 0.0)}
    # Default 2-pad SMDs (passives, diodes)
    return {"1": (-1.0, 0.0), "2": (1.0, 0.0)}


def _generate_copper_tracks(
    ir: DesignIntermediateRepresentation,
    comp_positions: Dict[str, Tuple[float, float, str]],
) -> List[str]:
    """Generates 45-degree chamfered copper tracks connecting pads of common nets."""
    track_lines: List[str] = []
    for net_id, net in enumerate(ir.nets, start=1):
        if len(net.connections) < 2:
            continue
        low_name = net.name.lower()
        is_power = net.is_power or any(k in low_name for k in ("vin", "vout", "vbus", "gnd", "pwr", "rail", "1200v", "1000v", "hv"))
        track_width = 1.0 if is_power else 0.4
        layer = "B.Cu" if net.is_ground or "gnd" in low_name else "F.Cu"

        pads = []
        for conn in net.connections:
            if conn.component_id in comp_positions:
                fx, fy, fp_name = comp_positions[conn.component_id]
                offsets = _get_pad_offsets(fp_name)
                ox, oy = offsets.get(str(conn.pin_id), (0.0, 0.0))
                pads.append((fx + ox, fy + oy))

        for i in range(len(pads) - 1):
            x1, y1 = pads[i]
            x2, y2 = pads[i + 1]
            dx = x2 - x1
            dy = y2 - y1

            if abs(dx) < 0.01 and abs(dy) < 0.01:
                continue

            if abs(dx) < 0.01 or abs(dy) < 0.01:
                track_lines.append(
                    f'  (segment (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) (width {track_width:.2f}) (layer "{layer}") (net {net_id}) (uuid "{uuid4()}"))'
                )
            else:
                sign_x = 1.0 if dx > 0 else -1.0
                sign_y = 1.0 if dy > 0 else -1.0
                if abs(dx) >= abs(dy):
                    mid_x = x2 - sign_x * abs(dy)
                    track_lines.append(
                        f'  (segment (start {x1:.2f} {y1:.2f}) (end {mid_x:.2f} {y1:.2f}) (width {track_width:.2f}) (layer "{layer}") (net {net_id}) (uuid "{uuid4()}"))'
                    )
                    track_lines.append(
                        f'  (segment (start {mid_x:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) (width {track_width:.2f}) (layer "{layer}") (net {net_id}) (uuid "{uuid4()}"))'
                    )
                else:
                    mid_y = y2 - sign_y * abs(dx)
                    track_lines.append(
                        f'  (segment (start {x1:.2f} {y1:.2f}) (end {x1:.2f} {mid_y:.2f}) (width {track_width:.2f}) (layer "{layer}") (net {net_id}) (uuid "{uuid4()}"))'
                    )
                    track_lines.append(
                        f'  (segment (start {x1:.2f} {mid_y:.2f}) (end {x2:.2f} {y2:.2f}) (width {track_width:.2f}) (layer "{layer}") (net {net_id}) (uuid "{uuid4()}"))'
                    )

    return track_lines


class KiCadPCBGenerator:
    """Generates populated KiCad 9/10 .kicad_pcb board files from Design IR."""

    @staticmethod
    def generate_pcb_sexpr(
        ir: DesignIntermediateRepresentation,
        board_width_mm: float = 85.0,
        board_height_mm: float = 65.0,
        route_tracks: bool = False,
    ) -> str:
        """Generates populated KiCad PCB layout S-expression with valid net connectivity and 3D models."""
        lines = [
            '(kicad_pcb (version 20240108) (generator "Mendex Studio v2.1 (Placement Only - Unrouted)") (generator_version "2.1.0")',
            '  (general (thickness 1.6))',
            '  (paper "A4")',
            '  (layers',
            '    (0 "F.Cu" signal)',
            '    (31 "B.Cu" signal)',
            '    (36 "B.SilkS" user "B.Silkscreen")',
            '    (37 "F.SilkS" user "F.Silkscreen")',
            '    (38 "B.Mask" user)',
            '    (39 "F.Mask" user)',
            '    (44 "Edge.Cuts" user)',
            '    (48 "B.Fab" user)',
            '    (49 "F.Fab" user)',
            '  )',
            '  (setup',
            '    (pad_to_mask_clearance 0.05)',
            '    (pcbplotparams (usegerberextensions yes) (usegerberattributes yes) (creategerberjobfile yes))',
            '  )',
        ]

        # Net definitions
        lines.append('  (net 0 "")')
        net_name_to_id: Dict[str, int] = {"": 0}
        for i, net in enumerate(ir.nets):
            net_id = i + 1
            net_name_to_id[net.name] = net_id
            lines.append(f'  (net {net_id} "{net.name}")')

        # Map component pins to (net_id, net_name)
        comp_pin_to_net: Dict[Tuple[str, str], Tuple[int, str]] = {}
        for net_id, net in enumerate(ir.nets, start=1):
            for conn in net.connections:
                comp_pin_to_net[(conn.component_id, str(conn.pin_id))] = (net_id, net.name)

        # Board Boundary Outline on Edge.Cuts
        origin_x = 100.0
        origin_y = 100.0
        x2 = origin_x + board_width_mm
        y2 = origin_y + board_height_mm

        lines.extend([
            f'  (gr_rect (start {origin_x:.2f} {origin_y:.2f}) (end {x2:.2f} {y2:.2f}) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts") (uuid "{uuid4()}"))',
            f'  (gr_text "Mendex Studio: ' + ("Routed Hardware Design (Native Copper Tracks & 3D Model Bindings)" if route_tracks else "Placement Only (Unrouted - Routing & DRC Required Before Fabrication)") + f'" (at {origin_x + 5.0:.2f} {origin_y - 3.0:.2f}) (layer "F.SilkS") (effects (font (size 1.0 1.0) (thickness 0.15))) (uuid "{uuid4()}"))',
        ])

        # High-voltage isolation barrier milling slot (IEC-61010-1: 5.0 mm clearance)
        has_hv = any(c.type == ComponentType.TRANSFORMER for c in ir.components) or any("VOUT" in n.name for n in ir.nets)
        if has_hv:
            slot_x1 = origin_x + board_width_mm * 0.48
            slot_x2 = slot_x1 + 5.0
            slot_y1 = origin_y + 4.0
            slot_y2 = origin_y + board_height_mm - 4.0
            lines.append(
                f'  (gr_rect (start {slot_x1:.2f} {slot_y1:.2f}) (end {slot_x2:.2f} {slot_y2:.2f}) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts") (uuid "{uuid4()}"))'
            )

        # Place footprints inside the board boundary
        grid_start_x = origin_x + 12.0
        grid_start_y = origin_y + 12.0
        spacing_x = 18.0
        spacing_y = 18.0
        comp_positions: Dict[str, Tuple[float, float, str]] = {}

        for idx, comp in enumerate(ir.components):
            fp_uuid = str(uuid4())
            fx = grid_start_x + (idx % 4) * spacing_x
            fy = grid_start_y + (idx // 4) * spacing_y

            # Resolve footprint identifier
            fp_name = comp.footprint
            if not fp_name:
                if comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_SIC, ComponentType.SWITCH_GAN):
                    fp_name = "Package_TO_SOT_SMD:TO-252-2"
                elif comp.type == ComponentType.SWITCH_IGBT:
                    fp_name = "Package_TO_SOT_THT:TO-220-3_Vertical"
                elif comp.type == ComponentType.REGULATOR_LINEAR:
                    fp_name = "Package_TO_SOT_THT:TO-220-3_Vertical"
                elif comp.type == ComponentType.CAPACITOR_POLARIZED:
                    fp_name = "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm"
                elif comp.type == ComponentType.CONNECTOR:
                    fp_name = "TerminalBlock:TerminalBlock_bornier-2_P5.08mm"
                elif comp.type in (ComponentType.GATE_DRIVER, ComponentType.OPTOCOUPLER, ComponentType.IC_CONTROLLER):
                    fp_name = "Package_DIP:DIP-8_W7.62mm"
                elif comp.type == ComponentType.IC_LOGIC:
                    fp_name = "Package_DIP:DIP-16_W7.62mm"
                elif comp.type == ComponentType.SWITCH_PUSH:
                    fp_name = "Button_Switch_THT:SW_PUSH_6mm"
                elif comp.type == ComponentType.TRANSFORMER:
                    fp_name = "Transformer_THT:Transformer_ETD34_Vertical"
                elif comp.type == ComponentType.DIODE:
                    fp_name = "Diode_SMD:D_SMA"
                else:
                    fp_name = "Resistor_SMD:R_0805_2012Metric"

            lines.extend([
                f'  (footprint "{fp_name}" (layer "F.Cu") (uuid "{fp_uuid}") (at {fx:.2f} {fy:.2f})',
                f'    (property "Reference" "{comp.designator}" (at 0 -3.5 0) (layer "F.SilkS") (uuid "{uuid4()}"))',
                f'    (property "Value" "{comp.name}" (at 0 3.5 0) (layer "F.Fab") (uuid "{uuid4()}"))',
            ])

            # Silkscreen graphics
            lines.extend(_generate_silkscreen_graphics(fp_name, comp))

            # Footprint pads
            lines.extend(_generate_footprint_pads(fp_name, comp, comp_pin_to_net))

            # 3D Model S-Expression
            model_path = resolve_3d_model(fp_name, comp.type, comp.name)
            if model_path:
                lines.extend([
                    f'    (model "{model_path}"',
                    '      (offset (xyz 0 0 0))',
                    '      (scale (xyz 1 1 1))',
                    '      (rotate (xyz 0 0 0))',
                    '    )',
                ])

            comp_positions[comp.id] = (fx, fy, fp_name)
            lines.append('  )')

        # Routed Copper Tracks with 45-degree chamfers (when routing requested)
        if route_tracks:
            lines.extend(_generate_copper_tracks(ir, comp_positions))

        lines.append(")")
        return "\n".join(lines) + "\n"

    @staticmethod
    def export_pcb(
        ir: DesignIntermediateRepresentation,
        output_pcb_path: Path,
        board_width_mm: float = 85.0,
        board_height_mm: float = 65.0,
        route_tracks: bool = False,
    ) -> Path:
        """Writes populated .kicad_pcb file to disk."""
        output_pcb_path.parent.mkdir(parents=True, exist_ok=True)
        content = KiCadPCBGenerator.generate_pcb_sexpr(
            ir, board_width_mm=board_width_mm, board_height_mm=board_height_mm, route_tracks=route_tracks
        )
        output_pcb_path.write_text(content, encoding="utf-8")
        return output_pcb_path
