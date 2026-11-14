"""LTspice netlist generator from Design Intermediate Representation (IR).

Translates abstract components and nets into valid, executable SPICE syntax (.net / .cir)
with transient simulation directives and deterministic component values.
"""
from __future__ import annotations

from typing import Dict, List
from ..ir import DesignIntermediateRepresentation, ComponentType


class LTspiceNetlistGenerator:
    """Generates executable SPICE netlists from DesignIntermediateRepresentation."""

    @staticmethod
    def generate_asc_schematic(ir: DesignIntermediateRepresentation, sim_time_s: float = 0.005) -> str:
        """Generates editable LTspice graphical schematic (.asc) representation with qualified nets."""
        lines = [
            "Version 4",
            "SHEET 1 1400 900",
        ]

        # Map component pins to net names
        comp_pin_to_net: Dict[str, Dict[str, str]] = {}
        for net in ir.nets:
            net_name = "0" if net.name.upper() in ("GND", "0", "PRI_GND", "SEC_GND") else net.name
            for conn in net.connections:
                if conn.component_id not in comp_pin_to_net:
                    comp_pin_to_net[conn.component_id] = {}
                comp_pin_to_net[conn.component_id][str(conn.pin_id)] = net_name

        # Place components visually
        base_x = 100
        base_y = 100
        step_x = 220
        step_y = 180

        for i, comp in enumerate(ir.components):
            x = base_x + (i % 4) * step_x
            y = base_y + (i // 4) * step_y
            pin_map = comp_pin_to_net.get(comp.id, {})

            sym_name = "res"
            val_str = f"{comp.value:.6g}" if comp.value is not None else "1k"
            if comp.type == ComponentType.CAPACITOR:
                sym_name = "cap"
            elif comp.type == ComponentType.INDUCTOR:
                sym_name = "ind"
            elif comp.type == ComponentType.VOLTAGE_SOURCE:
                sym_name = "voltage"
                if comp.parameters.get("pulse"):
                    val_str = comp.parameters["pulse"]
                elif comp.designator.startswith("V_G"):
                    # Calculate pulse for gate source
                    fsw_p = ir.parameters.get("Fsw", ir.parameters.get("fsw", None))
                    fsw_v = fsw_p.value if fsw_p else 100000.0
                    period_v = 1.0 / max(fsw_v, 1000.0)
                    vin_p = ir.parameters.get("Vin", ir.parameters.get("vin", None))
                    vout_p = ir.parameters.get("Vout", ir.parameters.get("vout", None))
                    vin_v = vin_p.value if vin_p else 12.0
                    vout_v = vout_p.value if vout_p else 5.0
                    d_v = min(max(vout_v / max(vin_v, 1.0), 0.05), 0.95)
                    ton_v = d_v * period_v
                    if "1" in comp.designator or "HI" in comp.name.upper():
                        val_str = f"PULSE(0 10 0 10n 10n {ton_v:.6e} {period_v:.6e})"
                    else:
                        val_str = f"PULSE(0 10 {ton_v + 50e-9:.6e} 10n 10n {max(period_v - ton_v - 100e-9, 1e-7):.6e} {period_v:.6e})"
            elif comp.type == ComponentType.DIODE:
                sym_name = "diode"
                val_str = "D_IDEAL"
            elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC):
                sym_name = "nmos"
                val_str = comp.spice_model or f"NMOS_DEFAULT_{comp.designator}"

            lines.extend([
                f"SYMBOL {sym_name} {x} {y} R0",
                f"SYMATTR InstName {comp.designator}",
                f"SYMATTR Value {val_str}",
            ])

            # Attach net flags to exact symbol pin coordinates to prevent NC_* floating nodes
            if sym_name == "res":
                p1_net = pin_map.get("1", "0")
                p2_net = pin_map.get("2", "0")
                lines.append(f"FLAG {x + 16} {y + 16} {p1_net}")
                lines.append(f"FLAG {x + 16} {y + 96} {p2_net}")
            elif sym_name == "ind":
                p1_net = pin_map.get("1", "0")
                p2_net = pin_map.get("2", "0")
                lines.append(f"FLAG {x + 16} {y + 16} {p1_net}")
                lines.append(f"FLAG {x + 16} {y + 96} {p2_net}")
            elif sym_name == "cap":
                p1_net = pin_map.get("1", "0")
                p2_net = pin_map.get("2", "0")
                lines.append(f"FLAG {x + 16} {y} {p1_net}")
                lines.append(f"FLAG {x + 16} {y + 64} {p2_net}")
            elif sym_name == "diode":
                p1_net = pin_map.get("a", pin_map.get("1", "0"))
                p2_net = pin_map.get("k", pin_map.get("2", "0"))
                lines.append(f"FLAG {x + 16} {y} {p1_net}")
                lines.append(f"FLAG {x + 16} {y + 64} {p2_net}")
            elif sym_name == "voltage":
                p_net = pin_map.get("p", pin_map.get("1", "VIN"))
                n_net = pin_map.get("n", pin_map.get("2", "0"))
                lines.append(f"FLAG {x} {y + 16} {p_net}")
                lines.append(f"FLAG {x} {y + 96} {n_net}")
            elif sym_name == "nmos":
                d_net = pin_map.get("d", pin_map.get("2", "SW"))
                g_net = pin_map.get("g", pin_map.get("1", "GATE"))
                s_net = pin_map.get("s", pin_map.get("3", "0"))
                lines.append(f"FLAG {x + 48} {y} {d_net}")
                lines.append(f"FLAG {x} {y + 80} {g_net}")
                lines.append(f"FLAG {x + 48} {y + 96} {s_net}")

        # Add ground flags, simulation command and device models
        lines.extend([
            "FLAG 100 450 0",
            f"TEXT 100 500 Left 2 !.tran 0 {sim_time_s:.6g} 0 10u",
            "TEXT 100 550 Left 2 !.model BSC026N08NS5 VDMOS(Rg=1.0 Vto=3.0 Rd=0.015)",
            "TEXT 100 600 Left 2 !.model D_IDEAL D(Ron=0.005 Roff=1Meg Vfwd=0.35)",
            "TEXT 100 650 Left 2 !.model NMOS_DEFAULT VDMOS(Rg=1.0 Vto=3.0 Rd=0.025)",
        ])

        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_netlist(ir: DesignIntermediateRepresentation, sim_time_s: float = 0.005) -> str:
        """Converts IR components and connectivity into SPICE netlist text."""
        lines: List[str] = [
            f"* MENDEX ENGINEERING STUDIO v1.9 — SPICE NETLIST",
            f"* Title: {ir.title}",
            f"* Topology: {ir.topology}",
            f"* Generated from Canonical Design IR",
            "",
        ]

        # Map component pins to net names
        comp_pin_to_net: Dict[str, Dict[str, str]] = {}
        for net in ir.nets:
            net_name = "0" if net.name.upper() in ("GND", "0", "PRI_GND", "SEC_GND") else net.name
            for conn in net.connections:
                if conn.component_id not in comp_pin_to_net:
                    comp_pin_to_net[conn.component_id] = {}
                comp_pin_to_net[conn.component_id][conn.pin_id] = net_name

        # Emit components
        for comp in ir.components:
            pin_map = comp_pin_to_net.get(comp.id, {})
            des = comp.designator

            if comp.type == ComponentType.RESISTOR:
                p1 = pin_map.get("1", "0")
                p2 = pin_map.get("2", "0")
                lines.append(f"{des} {p1} {p2} {comp.value:.6g}")

            elif comp.type == ComponentType.CAPACITOR:
                p1 = pin_map.get("1", "0")
                p2 = pin_map.get("2", "0")
                lines.append(f"{des} {p1} {p2} {comp.value:.6g}")

            elif comp.type == ComponentType.INDUCTOR:
                p1 = pin_map.get("1", "0")
                p2 = pin_map.get("2", "0")
                lines.append(f"{des} {p1} {p2} {comp.value:.6g}")

            elif comp.type == ComponentType.VOLTAGE_SOURCE:
                p = pin_map.get("p", pin_map.get("1", "VIN"))
                n = pin_map.get("n", pin_map.get("2", "0"))
                if comp.parameters.get("pulse"):
                    lines.append(f"{des} {p} {n} {comp.parameters['pulse']}")
                else:
                    lines.append(f"{des} {p} {n} {comp.value:.6g}")

            elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC):
                d = pin_map.get("d", "SW")
                g = pin_map.get("g", f"GATE_{des}")
                s = pin_map.get("s", "0")
                model_name = comp.spice_model or f"NMOS_DEFAULT_{des}"
                lines.append(f"M_{des} {d} {g} {s} {s} {model_name}")

            elif comp.type == ComponentType.DIODE:
                a = pin_map.get("a", "ANODE")
                k = pin_map.get("k", "CATHODE")
                lines.append(f"{des} {a} {k} D_IDEAL")

            elif comp.type == ComponentType.TRANSFORMER:
                pri_p = pin_map.get("pri_dot", "VIN")
                pri_n = pin_map.get("pri_undot", "DRAIN")
                sec_p = pin_map.get("sec_dot", "0")
                sec_n = pin_map.get("sec_undot", "SEC_ANODE")
                lp = comp.parameters.get("primary_inductance", comp.value or 100e-6)
                n = comp.parameters.get("turns_ratio", 2.0)
                ls = lp / (n ** 2) if n > 0 else lp
                lines.append(f"L_pri_{des} {pri_p} {pri_n} {lp:.6g}")
                lines.append(f"L_sec_{des} {sec_p} {sec_n} {ls:.6g}")
                lines.append(f"K_{des} L_pri_{des} L_sec_{des} 0.998")

        # Gate Drive Pulse Controls
        fsw = ir.parameters.get("Fsw", ir.parameters.get("fsw", None))
        fsw_val = fsw.value if fsw else 100000.0
        period = 1.0 / max(fsw_val, 1000.0)

        vin_p = ir.parameters.get("Vin", ir.parameters.get("vin", None))
        vout_p = ir.parameters.get("Vout", ir.parameters.get("vout", None))
        vin_val = vin_p.value if vin_p else 24.0
        vout_val = vout_p.value if vout_p else 5.0

        d_nom = ir.parameters.get("d_nom", ir.parameters.get("D", None))
        if d_nom:
            d_val = d_nom.value
        elif any(c.type == ComponentType.TRANSFORMER for c in ir.components):
            d_val = 0.45
        else:
            d_val = min(max(vout_val / max(vin_val, 1.0), 0.05), 0.95)
        ton = d_val * period

        # Drive every switch gate relative to its own source node: first switch is the main switch,
        # a second switch (synchronous rectifier) receives the complementary pulse with dead time.
        switches = [c for c in ir.components if c.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC)]
        has_explicit_gate_sources = any(c.designator.startswith("V_G") for c in ir.components)
        if switches and not has_explicit_gate_sources:
            lines.extend(["", "* Gate Drive Pulse Sources (open-loop PWM)"])
            for index, sw in enumerate(switches[:2]):
                pins = comp_pin_to_net.get(sw.id, {})
                gate = pins.get("g", f"GATE_{sw.designator}")
                source = pins.get("s", "0")
                if index == 0:
                    lines.append(f"V_G{index + 1} {gate} {source} PULSE(0 10 0 10n 10n {ton:.6e} {period:.6e})")
                else:
                    lines.append(f"V_G{index + 1} {gate} {source} PULSE(0 10 {ton + 50e-9:.6e} 10n 10n {max(period - ton - 100e-9, 1e-7):.6e} {period:.6e})")
        if any("SW" in pins.values() for pins in comp_pin_to_net.values()):
            lines.append("D_FW 0 SW D_IDEAL")

        # Models & directives
        lines.extend([
            "",
            "* Models & Controls",
            ".model D_IDEAL D(Ron=0.005 Roff=1Meg Vfwd=0.35)",
            ".model BSC026N08NS5 VDMOS(Rg=1.0 Vto=3.0 Rd=0.015)",
            ".model NMOS_DEFAULT_Q1 VDMOS(Rg=1.0 Vto=3.0 Rd=0.025)",
            ".model NMOS_DEFAULT_Q2 VDMOS(Rg=1.0 Vto=3.0 Rd=0.015)",
            "",
            f".tran 0 {sim_time_s:.6g} 0 10u",
            ".backanno",
            ".end",
        ])

        return "\n".join(lines) + "\n"
