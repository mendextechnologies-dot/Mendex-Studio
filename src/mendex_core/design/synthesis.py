"""Candidate synthesis engine for power electronic topologies.

Interprets requirements, checks feasibility constraints, computes analytical
design metrics, and builds concrete DesignIntermediateRepresentation models.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .ir import (
    DesignIntermediateRepresentation,
    IRComponent,
    IRPin,
    IRNet,
    IRPort,
    IRParameter,
    IRMagneticGeometry,
    ComponentType,
    PortDirection,
)
from .models import Requirement, DesignCandidate, CandidateApprovalStatus


class CandidateSynthesisEngine:
    """Deterministic power electronics topology synthesis and candidate evaluation."""

    @staticmethod
    def synthesize_candidates(requirements: List[Requirement]) -> List[DesignCandidate]:
        """Synthesizes and ranks candidate topologies based on requirements."""
        # Extract key electrical inputs. Critical requirements are never invented.
        by_name = {r.parameter.lower(): r for r in requirements}
        req_map: Dict[str, float] = {name: r.target_value for name, r in by_name.items()}

        def _required(*names: str) -> float:
            for name in names:
                if name in req_map and req_map[name] is not None:
                    return float(req_map[name])
            raise ValueError(f"Missing required design requirement: {names[0]}")

        vin_nom = _required("vin_nom", "vin")
        vout = _required("vout")
        if req_map.get("iout") is None and req_map.get("pout") is not None:
            iout = float(req_map["pout"]) / vout  # derived from explicit output power requirement
        else:
            iout = _required("iout")
        fsw = _required("fsw", "frequency_hz")
        vin_req = by_name.get("vin_nom") or by_name.get("vin")
        vin_min = req_map.get("vin_min", vin_req.min_value if vin_req and vin_req.min_value is not None else vin_nom)
        vin_max = req_map.get("vin_max", vin_req.max_value if vin_req and vin_req.max_value is not None else vin_nom)
        ripple_req = by_name.get("ripple")
        ripple_v = None
        if ripple_req is not None:
            ripple_v = ripple_req.max_value if ripple_req.max_value is not None else ripple_req.target_value

        for label, value in (("vin_nom", vin_nom), ("vin_min", vin_min), ("vin_max", vin_max), ("vout", vout), ("iout", iout), ("fsw", fsw)):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Design requirement '{label}' must be a finite positive value (got {value}).")
        if not (vin_min <= vin_nom <= vin_max):
            raise ValueError(f"Input range invalid: require vin_min <= vin_nom <= vin_max (got {vin_min}, {vin_nom}, {vin_max}).")
        if ripple_v is not None and (not math.isfinite(ripple_v) or ripple_v <= 0):
            raise ValueError(f"Ripple requirement must be a finite positive value (got {ripple_v}).")
        pout = vout * iout
        isolated = bool(
            req_map.get("isolation", 0.0) > 0
            or req_map.get("isolated", 0.0) > 0
            or req_map.get("isolation_v", 0.0) > 0
            or req_map.get("isolation_voltage", 0.0) > 0
        )

        candidates: List[DesignCandidate] = []

        # Candidate 1: Synchronous Buck Converter (Non-isolated step-down)
        if not isolated and vin_min > vout:
            d_nom = vout / vin_nom
            delta_il = 0.3 * iout
            l_val = (vin_nom - vout) * d_nom / (fsw * max(delta_il, 0.01))
            ripple_target = ripple_v if ripple_v is not None else 0.01 * vout  # 1% of Vout only when no requirement given
            c_val = delta_il / (8.0 * fsw * ripple_target)
            v_stress = vin_max * 1.25

            ir_buck = CandidateSynthesisEngine._build_buck_ir(
                vin_nom=vin_nom, vout=vout, iout=iout, fsw=fsw, l_val=l_val, c_val=c_val
            )

            cand_buck = DesignCandidate(
                topology="Synchronous Buck Converter",
                name="Non-Isolated Synchronous Buck",
                description="High efficiency step-down converter with synchronous MOSFET rectification.",
                parameters={"d_nom": d_nom, "l_uh": l_val * 1e6, "c_uf": c_val * 1e6, "fsw_khz": fsw / 1e3},
                calculated_metrics={
                    "estimated_efficiency": 0.94,
                    "switch_voltage_stress_v": v_stress,
                    "peak_inductor_current_a": iout + delta_il / 2.0,
                    "component_count": 8,
                },
                rationale="Ideal for non-isolated point-of-load conversion with minimum passive volume.",
                constraints_satisfied=True,
                feasibility_score=0.95,
                ir_snapshot=ir_buck,
            )
            candidates.append(cand_buck)

        # Candidate 2: Quasi-Resonant / Discontinuous Flyback Converter (Isolated or High Ratio)
        # Always evaluate isolated flyback
        d_max = 0.45
        # Reflected voltage Vor = (Vin_min * Dmax) / (1 - Dmax)
        vor = (vin_min * d_max) / (1.0 - d_max)
        n_ratio = vor / max(vout + 0.7, 0.1)  # Np / Ns
        # Primary magnetizing inductance Lm = (Vin_min * Dmax)^2 / (2 * Pout * fsw / eta)
        eta_est = 0.88
        pin_est = pout / eta_est
        lm_val = (vin_min * d_max) ** 2 / (2.0 * pin_est * fsw)
        v_ds_stress = vin_max + vor + 50.0  # margin for leakage spike

        ir_flyback = CandidateSynthesisEngine._build_flyback_ir(
            vin_nom=vin_nom, vout=vout, iout=iout, fsw=fsw, lm_val=lm_val, n_ratio=n_ratio
        )

        cand_flyback = DesignCandidate(
            topology="Discontinuous Flyback Converter",
            name="Isolated Single-Switch Flyback",
            description="Isolated flyback converter utilizing coupled inductor with energy storage.",
            parameters={"d_nom": d_max, "lm_uh": lm_val * 1e6, "turns_ratio_np_ns": n_ratio, "fsw_khz": fsw / 1e3},
            calculated_metrics={
                "estimated_efficiency": eta_est,
                "switch_voltage_stress_v": v_ds_stress,
                "peak_primary_current_a": (2.0 * pin_est) / (vin_min * d_max),
                "component_count": 10,
            },
            rationale="Provides galvanic isolation and simple single-switch architecture.",
            constraints_satisfied=True,
            feasibility_score=0.90 if isolated else 0.80,
            ir_snapshot=ir_flyback,
        )
        candidates.append(cand_flyback)

        # Candidate 3: Push-Pull / Forward Converter (for medium/high power isolated)
        if isolated or pout > 50.0:
            n_ratio_pp = (vout + 0.7) / (2.0 * vin_min * 0.45)
            cand_pp = DesignCandidate(
                topology="Push-Pull Isolated Converter",
                name="Push-Pull Multi-Output Converter",
                description="Center-tapped primary transformer converter with dual low-side switches.",
                parameters={"d_nom": 0.40, "turns_ratio_np_ns": 1.0 / max(n_ratio_pp, 0.01), "fsw_khz": fsw / 1e3},
                calculated_metrics={
                    "estimated_efficiency": 0.91,
                    "switch_voltage_stress_v": 2.2 * vin_max,
                    "peak_primary_current_a": pin_est / vin_min,
                    "component_count": 14,
                },
                rationale="Lower switch current stress and symmetrical core excitation.",
                constraints_satisfied=True,
                feasibility_score=0.85 if pout > 100.0 else 0.75,
                ir_snapshot=None,
            )
            candidates.append(cand_pp)

        # Sort by feasibility score descending
        candidates.sort(key=lambda c: c.feasibility_score, reverse=True)
        if candidates:
            candidates[0].status = CandidateApprovalStatus.SELECTED

        return candidates

    @staticmethod
    def _build_buck_ir(
        vin_nom: float, vout: float, iout: float, fsw: float, l_val: float, c_val: float
    ) -> DesignIntermediateRepresentation:
        """Constructs concrete DesignIntermediateRepresentation for Buck converter."""
        ir = DesignIntermediateRepresentation(
            title="Synchronous Buck Converter 12V",
            topology="Buck",
            category="dc_dc_converter",
            parameters={
                "Vin": IRParameter(name="Vin", value=vin_nom, unit="V", description="Input Voltage"),
                "Vout": IRParameter(name="Vout", value=vout, unit="V", description="Output Voltage"),
                "Iout": IRParameter(name="Iout", value=iout, unit="A", description="Load Current"),
                "Fsw": IRParameter(name="Fsw", value=fsw, unit="Hz", description="Switching Frequency"),
                "L": IRParameter(name="L", value=l_val, unit="H", description="Output Inductor"),
                "C": IRParameter(name="C", value=c_val, unit="F", description="Output Capacitor"),
            },
        )

        # Components
        v_in_comp = IRComponent(
            designator="V1",
            name="Input DC Supply",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
        )
        q1_comp = IRComponent(
            designator="Q1",
            name="High-Side Switch",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.025, "v_ds_max": 60.0},
            spice_model="BSC026N08NS5",
        )
        q2_comp = IRComponent(
            designator="Q2",
            name="Synchronous Low-Side Switch",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.015, "v_ds_max": 60.0},
            spice_model="BSC026N08NS5",
        )
        l1_comp = IRComponent(
            designator="L1",
            name="Power Inductor",
            type=ComponentType.INDUCTOR,
            value=l_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            parameters={"dcr": 0.012, "isat": iout * 1.5},
        )
        c1_comp = IRComponent(
            designator="C1",
            name="Output Filter Capacitor",
            type=ComponentType.CAPACITOR,
            value=c_val,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
            parameters={"esr": 0.005},
        )
        r_load_comp = IRComponent(
            designator="R_LOAD",
            name="Load Resistor",
            type=ComponentType.RESISTOR,
            value=vout / max(iout, 0.01),
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        ir.components.extend([v_in_comp, q1_comp, q2_comp, l1_comp, c1_comp, r_load_comp])

        # Interconnecting Nets
        # Net VIN: V1(+) -> Q1(D)
        ir.add_net_connection("VIN", v_in_comp.id, "p")
        ir.add_net_connection("VIN", q1_comp.id, "d")

        # Net SW: Q1(S) -> Q2(D) -> L1(1)
        ir.add_net_connection("SW", q1_comp.id, "s")
        ir.add_net_connection("SW", q2_comp.id, "d")
        ir.add_net_connection("SW", l1_comp.id, "1")

        # Net VOUT: L1(2) -> C1(+) -> R_LOAD(1)
        ir.add_net_connection("VOUT", l1_comp.id, "2")
        ir.add_net_connection("VOUT", c1_comp.id, "1")
        ir.add_net_connection("VOUT", r_load_comp.id, "1")

        # Net GND: V1(-) -> Q2(S) -> C1(-) -> R_LOAD(2)
        ir.add_net_connection("GND", v_in_comp.id, "n")
        ir.add_net_connection("GND", q2_comp.id, "s")
        ir.add_net_connection("GND", c1_comp.id, "2")
        ir.add_net_connection("GND", r_load_comp.id, "2")

        # Gate Control Nets
        ir.add_net_connection("GATE_HI", q1_comp.id, "g")
        ir.add_net_connection("GATE_LO", q2_comp.id, "g")

        # Ports
        ir.ports = [
            IRPort(name="VIN_PORT", direction=PortDirection.INPUT, net_name="VIN", nominal_voltage=vin_nom),
            IRPort(name="VOUT_PORT", direction=PortDirection.OUTPUT, net_name="VOUT", nominal_voltage=vout),
            IRPort(name="GND_PORT", direction=PortDirection.GROUND, net_name="GND", nominal_voltage=0.0),
        ]

        return ir

    @staticmethod
    def _build_flyback_ir(
        vin_nom: float, vout: float, iout: float, fsw: float, lm_val: float, n_ratio: float
    ) -> DesignIntermediateRepresentation:
        """Constructs concrete DesignIntermediateRepresentation for Flyback converter."""
        ir = DesignIntermediateRepresentation(
            title="Isolated Flyback Converter",
            topology="Flyback",
            category="isolated_dcdc",
            parameters={
                "Vin": IRParameter(name="Vin", value=vin_nom, unit="V"),
                "Vout": IRParameter(name="Vout", value=vout, unit="V"),
                "Iout": IRParameter(name="Iout", value=iout, unit="A"),
                "Fsw": IRParameter(name="Fsw", value=fsw, unit="Hz"),
                "Lm": IRParameter(name="Lm", value=lm_val, unit="H"),
                "N_ratio": IRParameter(name="N_ratio", value=n_ratio, unit="ratio"),
                # Open-loop CCM duty at nominal input: D = Vor / (Vin + Vor), Vor = Np/Ns * (Vout + Vf)
                "d_nom": IRParameter(
                    name="d_nom",
                    value=(n_ratio * (vout + 0.7)) / (vin_nom + n_ratio * (vout + 0.7)),
                    unit="ratio",
                    description="Open-loop CCM duty cycle at nominal input (diode Vf = 0.7 V assumed)",
                ),
            },
            magnetic_geometry=IRMagneticGeometry(
                core_type="ETD34",
                core_material="N87",
                primary_turns=max(int(12 * n_ratio), 12),
                secondary_turns=12,
                air_gap_mm=0.65,
            ),
        )

        v_in = IRComponent(
            designator="V1",
            name="Input DC Supply",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
        )
        t1 = IRComponent(
            designator="T1",
            name="Coupled Flyback Transformer",
            type=ComponentType.TRANSFORMER,
            value=lm_val,
            unit="H",
            pins=[
                IRPin(pin_id="pri_dot", name="PRI+"),
                IRPin(pin_id="pri_undot", name="PRI-"),
                IRPin(pin_id="sec_dot", name="SEC+"),
                IRPin(pin_id="sec_undot", name="SEC-"),
            ],
            parameters={"primary_inductance": lm_val, "turns_ratio": n_ratio},
        )
        q1 = IRComponent(
            designator="Q1",
            name="Primary Switching MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"v_ds_max": 200.0, "rds_on": 0.055},
        )
        d1 = IRComponent(
            designator="D1",
            name="Secondary Rectifier Diode",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": 100.0},
        )
        c_out = IRComponent(
            designator="C1",
            name="Secondary Output Capacitor",
            type=ComponentType.CAPACITOR,
            value=100e-6,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
        )
        r_load = IRComponent(
            designator="R_LOAD",
            name="Output Load",
            type=ComponentType.RESISTOR,
            value=vout / max(iout, 0.01),
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        ir.components.extend([v_in, t1, q1, d1, c_out, r_load])

        # Primary Loop Nets
        ir.add_net_connection("VIN", v_in.id, "p")
        ir.add_net_connection("VIN", t1.id, "pri_dot")

        ir.add_net_connection("DRAIN", t1.id, "pri_undot")
        ir.add_net_connection("DRAIN", q1.id, "d")

        ir.add_net_connection("PRI_GND", v_in.id, "n")
        ir.add_net_connection("PRI_GND", q1.id, "s")

        # Gate net driven by the open-loop PWM source emitted by the netlist generator
        ir.add_net_connection("GATE", q1.id, "g")

        # Secondary Loop Nets
        ir.add_net_connection("SEC_ANODE", t1.id, "sec_undot")
        ir.add_net_connection("SEC_ANODE", d1.id, "a")

        ir.add_net_connection("VOUT", d1.id, "k")
        ir.add_net_connection("VOUT", c_out.id, "1")
        ir.add_net_connection("VOUT", r_load.id, "1")

        ir.add_net_connection("SEC_GND", t1.id, "sec_dot")
        ir.add_net_connection("SEC_GND", c_out.id, "2")
        ir.add_net_connection("SEC_GND", r_load.id, "2")

        return ir
