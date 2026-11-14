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



TOPOLOGY_APPLICABILITY_MATRIX = {
    "buck": {
        "readiness": "QUALIFIED_REFERENCE",
        "description": "Non-isolated synchronous step-down converter with verified SPICE, ERC, DRC, and 4-layer PCB models.",
        "vin_min_v": 4.5,
        "vin_max_v": 60.0,
        "max_power_w": 500.0,
        "isolated": False,
        "qualification_notes": [
            "Verified 12V -> 5V, 1A end-to-end reference with KiCad ERC/DRC, Copper autorouting, and LTspice transient convergence."
        ],
    },
    "boost": {
        "readiness": "EXPERIMENTAL",
        "description": "Non-isolated step-up converter. Sizing and netlist available; physical layout and closed-loop control require application review.",
        "vin_min_v": 3.0,
        "vin_max_v": 48.0,
        "max_power_w": 300.0,
        "isolated": False,
        "qualification_notes": [
            "Preliminary analytical sizing. Physical layout and active closed-loop feedback are NOT_EVALUATED."
        ],
    },
    "flyback": {
        "readiness": "EXPERIMENTAL",
        "description": "Isolated single-switch flyback converter. Analytical transformer sizing available; leakage inductance clamping and magnetic FEA require qualification.",
        "vin_min_v": 10.0,
        "vin_max_v": 400.0,
        "max_power_w": 150.0,
        "isolated": True,
        "qualification_notes": [
            "Analytical sizing model available. Transformer construction and primary snubber require independent engineering review."
        ],
    },
    "push-pull": {
        "readiness": "EXPERIMENTAL",
        "description": "Center-tapped push-pull isolated converter. Sizing equations preliminary; flux-imbalance protection NOT_EVALUATED.",
        "isolated": True,
        "qualification_notes": ["Preliminary sizing model only; flux-imbalance protection NOT_EVALUATED."],
    },
    "llc": {
        "readiness": "EXPERIMENTAL",
        "description": "Resonant half-bridge LLC converter. First-harmonic approximation available; split-frequency gain curve requires independent qualification.",
        "isolated": True,
        "qualification_notes": ["First-harmonic approximation model only; resonant tank physical tolerances NOT_EVALUATED."],
    },
    "psfb": {
        "readiness": "EXPERIMENTAL",
        "description": "Phase-shifted full-bridge converter. Primary ZVS transitions preliminary; secondary snubber and synchronous rectification NOT_EVALUATED.",
        "isolated": True,
        "qualification_notes": ["ZVS transition assumptions preliminary; secondary rectification NOT_EVALUATED."],
    },
}

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

        # Candidate 1B: Asynchronous Boost Converter (Non-isolated step-up)
        if not isolated and vout > vin_nom:
            d_nom = (vout - vin_nom) / max(vout, 0.01)
            i_in_avg = iout / max(1.0 - d_nom, 0.05)
            delta_il = 0.3 * i_in_avg
            l_val = (vin_nom * d_nom) / (fsw * max(delta_il, 0.01))
            ripple_target = ripple_v if ripple_v is not None else 0.01 * vout
            c_val = (iout * d_nom) / (fsw * max(ripple_target, 0.001))
            v_stress = vout * 1.25

            ir_boost = CandidateSynthesisEngine._build_boost_ir(
                vin_nom=vin_nom, vout=vout, iout=iout, fsw=fsw, l_val=l_val, c_val=c_val
            )

            cand_boost = DesignCandidate(
                topology="Asynchronous Boost Converter",
                name="Non-Isolated Step-Up Boost",
                description="High efficiency step-up converter with power MOSFET and ultrafast catch diode.",
                parameters={"d_nom": d_nom, "l_uh": l_val * 1e6, "c_uf": c_val * 1e6, "fsw_khz": fsw / 1e3},
                calculated_metrics={
                    "estimated_efficiency": 0.93,
                    "switch_voltage_stress_v": v_stress,
                    "peak_inductor_current_a": i_in_avg + delta_il / 2.0,
                    "component_count": 6,
                },
                rationale="Standard topology for step-up DC-DC conversion with minimal active component count.",
                constraints_satisfied=True,
                feasibility_score=0.95,
                ir_snapshot=ir_boost,
            )
            candidates.append(cand_boost)

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
                description="Center-tapped secondary transformer converter with dual-rectifier output filter.",
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
                ir_snapshot=CandidateSynthesisEngine._build_pushpull_ir(
                    vin_nom=vin_nom,
                    vout=vout,
                    iout=iout,
                    fsw=fsw,
                    lm_val=lm_val,
                    n_ratio=n_ratio_pp,
                ),
            )
            candidates.append(cand_pp)

        # Candidate 4: LLC Resonant Half-Bridge Converter (High efficiency isolated)
        if isolated or pout >= 60.0:
            n_ratio_llc = vin_nom / max(2.0 * vout, 0.1)
            r_load = vout / max(iout, 0.01)
            r_ac = (8.0 / (math.pi ** 2)) * (n_ratio_llc ** 2) * r_load
            q_factor = 0.45
            w_r = 2.0 * math.pi * fsw
            lr_val = (q_factor * r_ac) / w_r
            cr_val = 1.0 / (w_r ** 2 * lr_val)
            lm_val_llc = 5.0 * lr_val

            cand_llc = DesignCandidate(
                topology="LLC Resonant Half-Bridge Converter",
                name="Isolated LLC Resonant Half-Bridge",
                description="High-frequency zero-voltage switching (ZVS) resonant converter with integrated leakage inductance.",
                parameters={
                    "turns_ratio_np_ns": n_ratio_llc,
                    "lr_uh": lr_val * 1e6,
                    "cr_nf": cr_val * 1e9,
                    "lm_uh": lm_val_llc * 1e6,
                    "fr_khz": fsw / 1e3,
                },
                calculated_metrics={
                    "estimated_efficiency": 0.96,
                    "switch_voltage_stress_v": vin_max,
                    "peak_primary_current_a": (math.pi / 2.0) * (pin_est / (vin_min / 2.0)),
                    "component_count": 12,
                },
                rationale="Zero-voltage switching (ZVS) across wide load range with minimum electromagnetic emissions.",
                constraints_satisfied=True,
                feasibility_score=0.92 if pout >= 100.0 else 0.82,
                ir_snapshot=CandidateSynthesisEngine._build_llc_ir(
                    vin_nom=vin_nom,
                    vout=vout,
                    iout=iout,
                    fsw=fsw,
                    lr_val=lr_val,
                    cr_val=cr_val,
                    lm_val=lm_val_llc,
                    n_ratio=n_ratio_llc,
                ),
            )
            candidates.append(cand_llc)

        # Candidate 5: Phase-Shifted Full-Bridge (PSFB) Converter (High power isolated, ZVS)
        if isolated or pout >= 100.0:
            d_max_psfb = 0.45
            d_eff = 0.70
            n_ratio_psfb = (vin_min * d_max_psfb) / max(vout + 0.6, 0.1)
            l_shim_val = 15.0e-6
            v_sec = vin_nom / max(n_ratio_psfb, 0.01)
            delta_i_lout = 0.20 * iout
            l_out_val = ((v_sec - vout) * d_eff) / (2.0 * fsw * max(delta_i_lout, 0.01))
            c_out_val = max(delta_i_lout / (8.0 * (2.0 * fsw) * max(0.01 * vout, 0.005)), 100e-6)

            cand_psfb = DesignCandidate(
                topology="Phase-Shifted Full-Bridge Converter",
                name="Isolated Phase-Shifted Full-Bridge",
                description="High-power isolated converter with 4-switch bridge, zero-voltage switching (ZVS), and full-wave rectification.",
                parameters={
                    "turns_ratio_np_ns": n_ratio_psfb,
                    "d_eff": d_eff,
                    "l_shim_uh": l_shim_val * 1e6,
                    "l_out_uh": l_out_val * 1e6,
                    "c_out_uf": c_out_val * 1e6,
                    "fsw_khz": fsw / 1e3,
                },
                calculated_metrics={
                    "estimated_efficiency": 0.95,
                    "switch_voltage_stress_v": vin_max,
                    "peak_primary_current_a": pin_est / (vin_min * d_eff),
                    "component_count": 14,
                },
                rationale="Ideal for high-power applications (kW range) requiring galvanic isolation and high efficiency via soft switching.",
                constraints_satisfied=True,
                feasibility_score=0.94 if pout >= 200.0 else 0.86,
                ir_snapshot=CandidateSynthesisEngine._build_psfb_ir(
                    vin_nom=vin_nom,
                    vout=vout,
                    iout=iout,
                    fsw=fsw,
                    l_shim_val=l_shim_val,
                    l_out_val=l_out_val,
                    c_out_val=c_out_val,
                    n_ratio=n_ratio_psfb,
                ),
            )
            candidates.append(cand_psfb)

        # Stamp readiness status and applicability metadata per G13
        for cand in candidates:
            top_key = cand.topology.lower()
            matched_key = None
            for k in TOPOLOGY_APPLICABILITY_MATRIX:
                if k in top_key:
                    matched_key = k
                    break
            app = TOPOLOGY_APPLICABILITY_MATRIX.get(matched_key, {})
            cand.readiness_status = app.get("readiness", "EXPERIMENTAL")
            cand.qualification_notes = list(app.get("qualification_notes", ["Unqualified experimental topology."]))

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

        # Components (Sourced, exact MPNs and reviewed pin/footprint maps per G05)
        v_in_comp = IRComponent(
            designator="V1",
            name="Input DC Supply Terminal",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            mpn="61300211121",
            manufacturer="Wurth Elektronik",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
            parameters={"voltage_rating_v": 250.0, "current_rating_a": 3.0, "package": "PinHeader_1x02", "pin_map": {"p": "1", "n": "2"}},
        )
        q1_comp = IRComponent(
            designator="Q1",
            name="High-Side Power MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            mpn="IPD036N04L G",
            manufacturer="Infineon Technologies",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.0036, "v_ds_max": 40.0, "i_d_max": 90.0, "package": "TO-252-2", "pin_map": {"g": "1", "d": "2", "s": "3"}},
            spice_model="BSC026N08NS5",
        )
        q2_comp = IRComponent(
            designator="Q2",
            name="Synchronous Low-Side Power MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            mpn="IPD036N04L G",
            manufacturer="Infineon Technologies",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.0036, "v_ds_max": 40.0, "i_d_max": 90.0, "package": "TO-252-2", "pin_map": {"g": "1", "d": "2", "s": "3"}},
            spice_model="BSC026N08NS5",
        )
        l1_comp = IRComponent(
            designator="L1",
            name="Molded Power Inductor",
            type=ComponentType.INDUCTOR,
            value=l_val,
            unit="H",
            mpn="SRP1265A-220M",
            manufacturer="Bourns",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            parameters={"dcr": 0.012, "isat": 10.0, "current_rating_a": 5.5, "package": "1210", "pin_map": {"1": "1", "2": "2"}},
        )
        c1_comp = IRComponent(
            designator="C1",
            name="Multi-Layer Ceramic Capacitor (MLCC)",
            type=ComponentType.CAPACITOR,
            value=c_val,
            unit="F",
            mpn="C1210C106K5RACTU",
            manufacturer="KEMET",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
            parameters={"voltage_rating_v": 50.0, "esr": 0.005, "capacitance_uf": 10.0, "package": "1210", "pin_map": {"1": "1", "2": "2"}},
        )
        r_load_comp = IRComponent(
            designator="R_LOAD",
            name="Thick Film Chip Resistor",
            type=ComponentType.RESISTOR,
            value=vout / max(iout, 0.01),
            unit="Ohm",
            mpn="RC1206FR-075RL",
            manufacturer="YAGEO",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            parameters={"power_rating_w": 0.25, "tolerance_pct": 1.0, "package": "1206", "pin_map": {"1": "1", "2": "2"}},
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

        # Gate Drive Pulse Sources (open-loop PWM drives for Q1 and Q2)
        period = 1.0 / max(fsw, 1000.0)
        d_val = min(max(vout / max(vin_nom, 1.0), 0.05), 0.95)
        ton = d_val * period
        v_g1_pulse = f"PULSE(0 10 0 10n 10n {ton:.6e} {period:.6e})"
        v_g2_pulse = f"PULSE(0 10 {ton + 50e-9:.6e} 10n 10n {max(period - ton - 100e-9, 1e-7):.6e} {period:.6e})"

        v_g1_comp = IRComponent(
            designator="V_G1",
            name="High-Side Gate Drive PWM Source",
            type=ComponentType.VOLTAGE_SOURCE,
            value=10.0,
            unit="V",
            mpn="61300211121",
            manufacturer="Wurth Elektronik",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
            parameters={"pulse": v_g1_pulse, "voltage_rating_v": 250.0, "current_rating_a": 3.0, "package": "PinHeader_1x02", "pin_map": {"p": "1", "n": "2"}},
            footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        )
        v_g2_comp = IRComponent(
            designator="V_G2",
            name="Low-Side Gate Drive PWM Source",
            type=ComponentType.VOLTAGE_SOURCE,
            value=10.0,
            unit="V",
            mpn="61300211121",
            manufacturer="Wurth Elektronik",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
            parameters={"pulse": v_g2_pulse, "voltage_rating_v": 250.0, "current_rating_a": 3.0, "package": "PinHeader_1x02", "pin_map": {"p": "1", "n": "2"}},
            footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        )

        # Set official footprints on power stage components
        v_in_comp.footprint = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
        q1_comp.footprint = "Package_TO_SOT_SMD:TO-252-2"
        q2_comp.footprint = "Package_TO_SOT_SMD:TO-252-2"
        l1_comp.footprint = "Inductor_SMD:L_1210_3225Metric"
        c1_comp.footprint = "Capacitor_SMD:C_1210_3225Metric"
        r_load_comp.footprint = "Resistor_SMD:R_1206_3216Metric"

        ir.components.extend([v_g1_comp, v_g2_comp])

        # Gate Control Nets
        ir.add_net_connection("GATE_HI", q1_comp.id, "g")
        ir.add_net_connection("GATE_HI", v_g1_comp.id, "p")
        ir.add_net_connection("SW", v_g1_comp.id, "n")

        ir.add_net_connection("GATE_LO", q2_comp.id, "g")
        ir.add_net_connection("GATE_LO", v_g2_comp.id, "p")
        ir.add_net_connection("GND", v_g2_comp.id, "n")

        # Explicit non-isolated metadata (G14: prevents isolation barrier slot)
        ir.metadata["isolated"] = False

        # Ports
        ir.ports = [
            IRPort(name="VIN_PORT", direction=PortDirection.INPUT, net_name="VIN", nominal_voltage=vin_nom),
            IRPort(name="VOUT_PORT", direction=PortDirection.OUTPUT, net_name="VOUT", nominal_voltage=vout),
            IRPort(name="GND_PORT", direction=PortDirection.GROUND, net_name="GND", nominal_voltage=0.0),
        ]

        return ir

    @staticmethod
    def _build_boost_ir(
        vin_nom: float, vout: float, iout: float, fsw: float, l_val: float, c_val: float
    ) -> DesignIntermediateRepresentation:
        """Constructs concrete DesignIntermediateRepresentation for Boost converter."""
        d_nom = (vout - vin_nom) / max(vout, 0.01)
        r_load_val = vout / max(iout, 0.01)
        ir = DesignIntermediateRepresentation(
            title=f"Boost Converter {vin_nom:g}V to {vout:g}V",
            topology="Boost",
            category="dc_dc_converter",
            parameters={
                "Vin": IRParameter(name="Vin", value=vin_nom, unit="V", description="Input Voltage"),
                "Vout": IRParameter(name="Vout", value=vout, unit="V", description="Output Voltage"),
                "Iout": IRParameter(name="Iout", value=iout, unit="A", description="Load Current"),
                "Fsw": IRParameter(name="Fsw", value=fsw, unit="Hz", description="Switching Frequency"),
                "L": IRParameter(name="L", value=l_val, unit="H", description="Boost Inductor"),
                "C": IRParameter(name="C", value=c_val, unit="F", description="Output Filter Capacitor"),
                "D_nom": IRParameter(name="D_nom", value=d_nom, unit="ratio", description="Nominal Duty Cycle"),
            },
        )

        v_in_comp = IRComponent(
            designator="V1",
            name="Input DC Supply",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
        )
        l1_comp = IRComponent(
            designator="L1",
            name="Boost Inductor",
            type=ComponentType.INDUCTOR,
            value=l_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            parameters={"dcr": 0.015, "isat": (iout / max(1.0 - d_nom, 0.05)) * 1.5},
        )
        q1_comp = IRComponent(
            designator="Q1",
            name="Low-Side Switching MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.020, "v_ds_max": vout * 1.5},
            spice_model="BSC026N08NS5",
        )
        d1_comp = IRComponent(
            designator="D1",
            name="Catch Diode",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": vout * 1.5},
        )
        c1_comp = IRComponent(
            designator="C1",
            name="Output Filter Capacitor",
            type=ComponentType.CAPACITOR,
            value=c_val,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
            parameters={"esr": 0.008},
        )
        r_load_comp = IRComponent(
            designator="R_LOAD",
            name="Load Resistor",
            type=ComponentType.RESISTOR,
            value=r_load_val,
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )
        j_gate_comp = IRComponent(
            designator="J_GATE",
            name="Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="GND")],
        )

        ir.components.extend([v_in_comp, l1_comp, q1_comp, d1_comp, c1_comp, r_load_comp, j_gate_comp])

        # Interconnecting Nets
        # VIN: V1(+) -> L1(1)
        ir.add_net_connection("VIN", v_in_comp.id, "p")
        ir.add_net_connection("VIN", l1_comp.id, "1")

        # SW: L1(2) -> Q1(d) -> D1(a)
        ir.add_net_connection("SW", l1_comp.id, "2")
        ir.add_net_connection("SW", q1_comp.id, "d")
        ir.add_net_connection("SW", d1_comp.id, "a")

        # VOUT: D1(k) -> C1(1) -> R_LOAD(1)
        ir.add_net_connection("VOUT", d1_comp.id, "k")
        ir.add_net_connection("VOUT", c1_comp.id, "1")
        ir.add_net_connection("VOUT", r_load_comp.id, "1")

        # GND: V1(-) -> Q1(s) -> C1(2) -> R_LOAD(2)
        ir.add_net_connection("GND", v_in_comp.id, "n")
        ir.add_net_connection("GND", q1_comp.id, "s")
        ir.add_net_connection("GND", c1_comp.id, "2")
        ir.add_net_connection("GND", r_load_comp.id, "2")

        # Gate Control Net
        ir.add_net_connection("GATE", j_gate_comp.id, "1")
        ir.add_net_connection("GATE", q1_comp.id, "g")
        ir.add_net_connection("GND", j_gate_comp.id, "2")

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

    @staticmethod
    def _build_pushpull_ir(
        vin_nom: float, vout: float, iout: float, fsw: float, lm_val: float, n_ratio: float
    ) -> DesignIntermediateRepresentation:
        """Constructs concrete DesignIntermediateRepresentation for Push-Pull / Forward multi-winding converter."""
        d_nom = 0.40
        l_out_val = max((vout * (1.0 - d_nom)) / (fsw * max(iout * 0.3, 0.1)), 10e-6)
        r_load_val = vout / max(iout, 0.01)

        ir = DesignIntermediateRepresentation(
            title="Push-Pull Dual-Secondary Converter",
            topology="Push-Pull",
            category="isolated_dcdc",
            parameters={
                "Vin": IRParameter(name="Vin", value=vin_nom, unit="V", description="Input Voltage"),
                "Vout": IRParameter(name="Vout", value=vout, unit="V", description="Output Voltage"),
                "Iout": IRParameter(name="Iout", value=iout, unit="A", description="Load Current"),
                "Fsw": IRParameter(name="Fsw", value=fsw, unit="Hz", description="Switching Frequency"),
                "Lm": IRParameter(name="Lm", value=lm_val, unit="H", description="Primary Magnetizing Inductance"),
                "Lout": IRParameter(name="Lout", value=l_out_val, unit="H", description="Secondary Output Inductor"),
                "N_ratio": IRParameter(name="N_ratio", value=n_ratio, unit="ratio", description="Turns Ratio Ns/Np"),
                "d_nom": IRParameter(name="d_nom", value=d_nom, unit="ratio", description="Nominal Duty Cycle"),
            },
            magnetic_geometry=IRMagneticGeometry(
                core_type="ETD39",
                core_material="N87",
                primary_turns=max(int(10 * n_ratio), 10),
                secondary_turns=10,
                air_gap_mm=0.0,
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
            name="Push-Pull Dual-Secondary Transformer",
            type=ComponentType.TRANSFORMER,
            value=lm_val,
            unit="H",
            pins=[
                IRPin(pin_id="pri_dot", name="AA"),
                IRPin(pin_id="pri_undot", name="AB"),
                IRPin(pin_id="sec1_dot", name="SA"),
                IRPin(pin_id="sec1_undot", name="SB"),
                IRPin(pin_id="sec2_dot", name="SC"),
                IRPin(pin_id="sec2_undot", name="SD"),
            ],
            parameters={"primary_inductance": lm_val, "turns_ratio": n_ratio},
        )
        q1 = IRComponent(
            designator="Q1",
            name="Primary Switching MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"v_ds_max": 200.0, "rds_on": 0.040},
        )
        j_gate = IRComponent(
            designator="J_GATE",
            name="Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="GND")],
        )
        d1 = IRComponent(
            designator="D1",
            name="Secondary Rectifier Diode 1",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": 100.0},
        )
        d2 = IRComponent(
            designator="D2",
            name="Secondary Rectifier Diode 2",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": 100.0},
        )
        l1 = IRComponent(
            designator="L1",
            name="Secondary Output Filter Inductor",
            type=ComponentType.INDUCTOR,
            value=l_out_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
            parameters={"dcr": 0.012},
        )
        c_out = IRComponent(
            designator="C1",
            name="Secondary Output Filter Capacitor",
            type=ComponentType.CAPACITOR,
            value=100e-6,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
        )
        r_load = IRComponent(
            designator="R_LOAD",
            name="Output Load Resistor",
            type=ComponentType.RESISTOR,
            value=r_load_val,
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        ir.components.extend([v_in, t1, q1, j_gate, d1, d2, l1, c_out, r_load])

        # Primary Loop Nets
        ir.add_net_connection("VIN", v_in.id, "p")
        ir.add_net_connection("VIN", t1.id, "pri_dot")

        ir.add_net_connection("DRAIN", t1.id, "pri_undot")
        ir.add_net_connection("DRAIN", q1.id, "d")

        ir.add_net_connection("PRI_GND", v_in.id, "n")
        ir.add_net_connection("PRI_GND", q1.id, "s")
        ir.add_net_connection("PRI_GND", j_gate.id, "2")

        ir.add_net_connection("GATE", q1.id, "g")
        ir.add_net_connection("GATE", j_gate.id, "1")

        # Secondary Loop Nets (Full-wave center-tapped secondary)
        ir.add_net_connection("SEC_RECT1", t1.id, "sec1_dot")
        ir.add_net_connection("SEC_RECT1", d1.id, "a")

        ir.add_net_connection("SEC_RECT2", t1.id, "sec2_undot")
        ir.add_net_connection("SEC_RECT2", d2.id, "a")

        ir.add_net_connection("SW_SEC", d1.id, "k")
        ir.add_net_connection("SW_SEC", d2.id, "k")
        ir.add_net_connection("SW_SEC", l1.id, "1")

        ir.add_net_connection("VOUT", l1.id, "2")
        ir.add_net_connection("VOUT", c_out.id, "1")
        ir.add_net_connection("VOUT", r_load.id, "1")

        # Center-tap connected to SEC_GND
        ir.add_net_connection("SEC_GND", t1.id, "sec1_undot")
        ir.add_net_connection("SEC_GND", t1.id, "sec2_dot")
        ir.add_net_connection("SEC_GND", c_out.id, "2")
        ir.add_net_connection("SEC_GND", r_load.id, "2")

        # Ports
        ir.ports = [
            IRPort(name="VIN_PORT", direction=PortDirection.INPUT, net_name="VIN", nominal_voltage=vin_nom),
            IRPort(name="VOUT_PORT", direction=PortDirection.OUTPUT, net_name="VOUT", nominal_voltage=vout),
            IRPort(name="PRI_GND_PORT", direction=PortDirection.GROUND, net_name="PRI_GND", nominal_voltage=0.0),
            IRPort(name="SEC_GND_PORT", direction=PortDirection.GROUND, net_name="SEC_GND", nominal_voltage=0.0),
        ]

        return ir


    @staticmethod
    def _build_llc_ir(
        vin_nom: float,
        vout: float,
        iout: float,
        fsw: float,
        lr_val: float,
        cr_val: float,
        lm_val: float,
        n_ratio: float,
    ) -> DesignIntermediateRepresentation:
        """Constructs concrete DesignIntermediateRepresentation for LLC Resonant Half-Bridge Converter."""
        ir = DesignIntermediateRepresentation(
            title="LLC Resonant Half-Bridge DC-DC Converter",
            description=f"Isolated LLC resonant converter (Vin={vin_nom}V, Vout={vout}V, Iout={iout}A, Fsw={fsw/1e3:.1f}kHz)",
            topology="LLC Resonant Half-Bridge",
        )

        r_load_val = vout / max(iout, 0.01)

        v_in = IRComponent(
            designator="V1",
            name="Input DC Power Source",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
        )

        q1 = IRComponent(
            designator="Q1",
            name="High-Side Half-Bridge MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"v_ds_max": vin_nom * 1.5, "r_ds_on": 0.045},
        )

        q2 = IRComponent(
            designator="Q2",
            name="Low-Side Half-Bridge MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"v_ds_max": vin_nom * 1.5, "r_ds_on": 0.045},
        )

        j_gate_hi = IRComponent(
            designator="J_GATE_HI",
            name="High-Side Gate Drive Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )

        j_gate_lo = IRComponent(
            designator="J_GATE_LO",
            name="Low-Side Gate Drive Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )

        cr = IRComponent(
            designator="CR1",
            name="Resonant Tank Capacitor",
            type=ComponentType.CAPACITOR,
            value=cr_val,
            unit="F",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        lr = IRComponent(
            designator="LR1",
            name="Resonant Tank Inductor",
            type=ComponentType.INDUCTOR,
            value=lr_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        t1 = IRComponent(
            designator="T1",
            name="LLC Resonant Isolation Transformer",
            type=ComponentType.TRANSFORMER,
            pins=[
                IRPin(pin_id="pri_dot", name="PRI_DOT"),
                IRPin(pin_id="pri_undot", name="PRI_UNDOT"),
                IRPin(pin_id="sec1_dot", name="SEC1_DOT"),
                IRPin(pin_id="sec1_undot", name="SEC1_UNDOT"),
                IRPin(pin_id="sec2_dot", name="SEC2_DOT"),
                IRPin(pin_id="sec2_undot", name="SEC2_UNDOT"),
            ],
            parameters={"turns_ratio": n_ratio, "lm_h": lm_val},
        )

        d1 = IRComponent(
            designator="D1",
            name="Secondary Rectifier Diode 1",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": 2.5 * vout},
        )

        d2 = IRComponent(
            designator="D2",
            name="Secondary Rectifier Diode 2",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.45, "vr_max": 2.5 * vout},
        )

        c_out = IRComponent(
            designator="C1",
            name="Secondary Output Filter Capacitor",
            type=ComponentType.CAPACITOR,
            value=220e-6,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
        )

        r_load = IRComponent(
            designator="R_LOAD",
            name="Output Load Resistor",
            type=ComponentType.RESISTOR,
            value=r_load_val,
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        ir.components.extend([v_in, q1, q2, j_gate_hi, j_gate_lo, cr, lr, t1, d1, d2, c_out, r_load])

        # Primary Loop Nets
        ir.add_net_connection("VIN", v_in.id, "p")
        ir.add_net_connection("VIN", q1.id, "d")

        ir.add_net_connection("HB_MID", q1.id, "s")
        ir.add_net_connection("HB_MID", q2.id, "d")
        ir.add_net_connection("HB_MID", j_gate_hi.id, "2")
        ir.add_net_connection("HB_MID", cr.id, "1")

        ir.add_net_connection("PRI_GND", v_in.id, "n")
        ir.add_net_connection("PRI_GND", q2.id, "s")
        ir.add_net_connection("PRI_GND", j_gate_lo.id, "2")
        ir.add_net_connection("PRI_GND", t1.id, "pri_undot")

        ir.add_net_connection("GATE_HI", q1.id, "g")
        ir.add_net_connection("GATE_HI", j_gate_hi.id, "1")

        ir.add_net_connection("GATE_LO", q2.id, "g")
        ir.add_net_connection("GATE_LO", j_gate_lo.id, "1")

        ir.add_net_connection("RES_NODE", cr.id, "2")
        ir.add_net_connection("RES_NODE", lr.id, "1")

        ir.add_net_connection("TX_PRI", lr.id, "2")
        ir.add_net_connection("TX_PRI", t1.id, "pri_dot")

        # Secondary Loop Nets (Center-Tapped Full-Wave Rectification)
        ir.add_net_connection("SEC_RECT1", t1.id, "sec1_dot")
        ir.add_net_connection("SEC_RECT1", d1.id, "a")

        ir.add_net_connection("SEC_RECT2", t1.id, "sec2_undot")
        ir.add_net_connection("SEC_RECT2", d2.id, "a")

        ir.add_net_connection("VOUT", d1.id, "k")
        ir.add_net_connection("VOUT", d2.id, "k")
        ir.add_net_connection("VOUT", c_out.id, "1")
        ir.add_net_connection("VOUT", r_load.id, "1")

        ir.add_net_connection("SEC_GND", t1.id, "sec1_undot")
        ir.add_net_connection("SEC_GND", t1.id, "sec2_dot")
        ir.add_net_connection("SEC_GND", c_out.id, "2")
        ir.add_net_connection("SEC_GND", r_load.id, "2")

        # Ports
        ir.ports = [
            IRPort(name="VIN_PORT", direction=PortDirection.INPUT, net_name="VIN", nominal_voltage=vin_nom),
            IRPort(name="VOUT_PORT", direction=PortDirection.OUTPUT, net_name="VOUT", nominal_voltage=vout),
            IRPort(name="PRI_GND_PORT", direction=PortDirection.GROUND, net_name="PRI_GND", nominal_voltage=0.0),
            IRPort(name="SEC_GND_PORT", direction=PortDirection.GROUND, net_name="SEC_GND", nominal_voltage=0.0),
        ]

        return ir

    @staticmethod
    def _build_psfb_ir(
        vin_nom: float,
        vout: float,
        iout: float,
        fsw: float,
        l_shim_val: float,
        l_out_val: float,
        c_out_val: float,
        n_ratio: float,
    ) -> DesignIntermediateRepresentation:
        """Constructs IR for an Isolated Phase-Shifted Full-Bridge (PSFB) Converter."""
        ir = DesignIntermediateRepresentation(
            title="Phase-Shifted Full-Bridge Converter",
            description=f"Isolated PSFB: {vin_nom}V -> {vout}V @ {iout}A, {fsw/1e3:.0f}kHz",
        )

        r_load_val = vout / max(iout, 0.01)

        v_in = IRComponent(
            designator="V1",
            name="DC Input Source",
            type=ComponentType.VOLTAGE_SOURCE,
            value=vin_nom,
            unit="V",
            pins=[IRPin(pin_id="p", name="+"), IRPin(pin_id="n", name="-")],
        )

        # Leading Leg A switches
        q1 = IRComponent(
            designator="Q1",
            name="Leg A High-Side MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            value=vin_nom * 1.5,
            unit="V",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.040, "v_ds_max": vin_nom * 1.5},
        )
        q2 = IRComponent(
            designator="Q2",
            name="Leg A Low-Side MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            value=vin_nom * 1.5,
            unit="V",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.040, "v_ds_max": vin_nom * 1.5},
        )
        j_gate_a_hi = IRComponent(
            designator="J_GATE_A_HI",
            name="Leg A High Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )
        j_gate_a_lo = IRComponent(
            designator="J_GATE_A_LO",
            name="Leg A Low Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )

        # Lagging Leg B switches
        q3 = IRComponent(
            designator="Q3",
            name="Leg B High-Side MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            value=vin_nom * 1.5,
            unit="V",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.040, "v_ds_max": vin_nom * 1.5},
        )
        q4 = IRComponent(
            designator="Q4",
            name="Leg B Low-Side MOSFET",
            type=ComponentType.SWITCH_MOSFET,
            value=vin_nom * 1.5,
            unit="V",
            pins=[IRPin(pin_id="d", name="D"), IRPin(pin_id="g", name="G"), IRPin(pin_id="s", name="S")],
            parameters={"rds_on": 0.040, "v_ds_max": vin_nom * 1.5},
        )
        j_gate_b_hi = IRComponent(
            designator="J_GATE_B_HI",
            name="Leg B High Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )
        j_gate_b_lo = IRComponent(
            designator="J_GATE_B_LO",
            name="Leg B Low Gate Control Header",
            type=ComponentType.CONNECTOR,
            pins=[IRPin(pin_id="1", name="GATE"), IRPin(pin_id="2", name="SOURCE")],
        )

        # Resonant Shim Inductor
        l_shim = IRComponent(
            designator="L_SHIM",
            name="Primary ZVS Shim Inductor",
            type=ComponentType.INDUCTOR,
            value=l_shim_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        # Isolation Transformer
        t1 = IRComponent(
            designator="T1",
            name="PSFB Isolation Transformer",
            type=ComponentType.TRANSFORMER,
            pins=[
                IRPin(pin_id="pri_dot", name="PRI_DOT"),
                IRPin(pin_id="pri_undot", name="PRI_UNDOT"),
                IRPin(pin_id="sec1_dot", name="SEC1_DOT"),
                IRPin(pin_id="sec1_undot", name="SEC1_UNDOT"),
                IRPin(pin_id="sec2_dot", name="SEC2_DOT"),
                IRPin(pin_id="sec2_undot", name="SEC2_UNDOT"),
            ],
            parameters={"turns_ratio": n_ratio},
        )

        # Secondary Full-Wave Rectifiers
        d1 = IRComponent(
            designator="D1",
            name="Secondary Rectifier Diode 1",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.50, "vr_max": 2.5 * vout},
        )
        d2 = IRComponent(
            designator="D2",
            name="Secondary Rectifier Diode 2",
            type=ComponentType.DIODE,
            pins=[IRPin(pin_id="a", name="A"), IRPin(pin_id="k", name="K")],
            parameters={"vf": 0.50, "vr_max": 2.5 * vout},
        )

        # Secondary Output Filter
        l_out = IRComponent(
            designator="L_OUT",
            name="Secondary Output Filter Inductor",
            type=ComponentType.INDUCTOR,
            value=l_out_val,
            unit="H",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )
        c_out = IRComponent(
            designator="C_OUT",
            name="Secondary Output Filter Capacitor",
            type=ComponentType.CAPACITOR,
            value=c_out_val,
            unit="F",
            pins=[IRPin(pin_id="1", name="+"), IRPin(pin_id="2", name="-")],
        )
        r_load = IRComponent(
            designator="R_LOAD",
            name="Output Load Resistor",
            type=ComponentType.RESISTOR,
            value=r_load_val,
            unit="Ohm",
            pins=[IRPin(pin_id="1", name="1"), IRPin(pin_id="2", name="2")],
        )

        ir.components.extend([
            v_in, q1, q2, j_gate_a_hi, j_gate_a_lo,
            q3, q4, j_gate_b_hi, j_gate_b_lo,
            l_shim, t1, d1, d2, l_out, c_out, r_load
        ])

        # Primary Loop Nets
        ir.add_net_connection("VIN", v_in.id, "p")
        ir.add_net_connection("VIN", q1.id, "d")
        ir.add_net_connection("VIN", q3.id, "d")

        ir.add_net_connection("PRI_GND", v_in.id, "n")
        ir.add_net_connection("PRI_GND", q2.id, "s")
        ir.add_net_connection("PRI_GND", q4.id, "s")
        ir.add_net_connection("PRI_GND", j_gate_a_lo.id, "2")
        ir.add_net_connection("PRI_GND", j_gate_b_lo.id, "2")

        ir.add_net_connection("HB_LEG_A", q1.id, "s")
        ir.add_net_connection("HB_LEG_A", q2.id, "d")
        ir.add_net_connection("HB_LEG_A", j_gate_a_hi.id, "2")
        ir.add_net_connection("HB_LEG_A", l_shim.id, "1")

        ir.add_net_connection("GATE_A_HI", q1.id, "g")
        ir.add_net_connection("GATE_A_HI", j_gate_a_hi.id, "1")

        ir.add_net_connection("GATE_A_LO", q2.id, "g")
        ir.add_net_connection("GATE_A_LO", j_gate_a_lo.id, "1")

        ir.add_net_connection("HB_LEG_B", q3.id, "s")
        ir.add_net_connection("HB_LEG_B", q4.id, "d")
        ir.add_net_connection("HB_LEG_B", j_gate_b_hi.id, "2")
        ir.add_net_connection("HB_LEG_B", t1.id, "pri_undot")

        ir.add_net_connection("GATE_B_HI", q3.id, "g")
        ir.add_net_connection("GATE_B_HI", j_gate_b_hi.id, "1")

        ir.add_net_connection("GATE_B_LO", q4.id, "g")
        ir.add_net_connection("GATE_B_LO", j_gate_b_lo.id, "1")

        ir.add_net_connection("TX_PRI_DOT", l_shim.id, "2")
        ir.add_net_connection("TX_PRI_DOT", t1.id, "pri_dot")

        # Secondary Loop Nets (Center-Tapped Rectification with LC Output Filter)
        ir.add_net_connection("SEC_RECT1", t1.id, "sec1_dot")
        ir.add_net_connection("SEC_RECT1", d1.id, "a")

        ir.add_net_connection("SEC_RECT2", t1.id, "sec2_undot")
        ir.add_net_connection("SEC_RECT2", d2.id, "a")

        ir.add_net_connection("SEC_SW", d1.id, "k")
        ir.add_net_connection("SEC_SW", d2.id, "k")
        ir.add_net_connection("SEC_SW", l_out.id, "1")

        ir.add_net_connection("VOUT", l_out.id, "2")
        ir.add_net_connection("VOUT", c_out.id, "1")
        ir.add_net_connection("VOUT", r_load.id, "1")

        ir.add_net_connection("SEC_GND", t1.id, "sec1_undot")
        ir.add_net_connection("SEC_GND", t1.id, "sec2_dot")
        ir.add_net_connection("SEC_GND", c_out.id, "2")
        ir.add_net_connection("SEC_GND", r_load.id, "2")

        # Ports
        ir.ports = [
            IRPort(name="VIN_PORT", direction=PortDirection.INPUT, net_name="VIN", nominal_voltage=vin_nom),
            IRPort(name="VOUT_PORT", direction=PortDirection.OUTPUT, net_name="VOUT", nominal_voltage=vout),
            IRPort(name="PRI_GND_PORT", direction=PortDirection.GROUND, net_name="PRI_GND", nominal_voltage=0.0),
            IRPort(name="SEC_GND_PORT", direction=PortDirection.GROUND, net_name="SEC_GND", nominal_voltage=0.0),
        ]

        return ir
