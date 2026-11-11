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
        """Generates editable LTspice graphical schematic (.asc) representation."""
        lines = [
            "Version 4",
            "SHEET 1 1200 800",
        ]

        # Place components visually
        base_x = 100
        base_y = 100
        step_x = 160

        for i, comp in enumerate(ir.components):
            x = base_x + (i % 5) * step_x
            y = base_y + (i // 5) * 160
            sym_name = "res"
            if comp.type == ComponentType.CAPACITOR:
                sym_name = "cap"
            elif comp.type == ComponentType.INDUCTOR:
                sym_name = "ind"
            elif comp.type == ComponentType.VOLTAGE_SOURCE:
                sym_name = "voltage"
            elif comp.type == ComponentType.DIODE:
                sym_name = "diode"
            elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN):
                sym_name = "nmos"

            lines.extend([
                f"SYMBOL {sym_name} {x} {y} R0",
                f"SYMATTR InstName {comp.designator}",
                f"SYMATTR Value {comp.value:.6g}",
            ])

        # Add ground flags and simulation command
        lines.extend([
            "FLAG 100 350 0",
            f"TEXT 100 450 Left 2 !.tran {sim_time_s:.6g}",
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
                p = pin_map.get("p", "VIN")
                n = pin_map.get("n", "0")
                lines.append(f"{des} {p} {n} {comp.value:.6g}")

            elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC):
                d = pin_map.get("d", "SW")
                g = pin_map.get("g", "GATE")
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
        d_val = d_nom.value if d_nom else min(max(vout_val / max(vin_val, 1.0), 0.05), 0.95)
        ton = d_val * period

        has_switches = any(c.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC) for c in ir.components)
        if has_switches:
            lines.extend([
                "",
                "* Gate Drive Pulse Sources & Commutation",
                f"V_G1 GATE_HI SW PULSE(0 10 0 10n 10n {ton:.6e} {period:.6e})",
                f"V_G2 GATE_LO 0 PULSE(0 10 {ton + 50e-9:.6e} 10n 10n {max(period - ton - 100e-9, 1e-7):.6e} {period:.6e})",
                "D_FW 0 SW D_IDEAL",
            ])

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
