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

        # Models & directives
        lines.extend([
            "",
            "* Models & Controls",
            ".model D_IDEAL D(Ron=0.01 Roff=1Meg Vfwd=0.45)",
            ".model BSC026N08NS5 VDMOS(Rg=1.0 Vto=3.0 Rd=0.015)",
            ".model NMOS_DEFAULT_Q1 VDMOS(Rg=1.0 Vto=3.0 Rd=0.025)",
            ".model NMOS_DEFAULT_Q2 VDMOS(Rg=1.0 Vto=3.0 Rd=0.015)",
            "",
            f".tran 0 {sim_time_s:.6g} 0 10u",
            ".backanno",
            ".end",
        ])

        return "\n".join(lines) + "\n"
