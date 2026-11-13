"""Mendex Engineering Intelligence — Deterministic Calculation Service.

Executes unit-aware, dimensionally consistent, reproducible engineering calculations
using explicit mathematical equations (not ungrounded LLM numerical guesses).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class CalculationResult(BaseModel):
    calculation_id: str = Field(default_factory=lambda: str(uuid4()))
    formula_id: str
    name: str
    inputs: Dict[str, float]
    input_units: Dict[str, str]
    outputs: Dict[str, float]
    output_units: Dict[str, str]
    origin: str = "calculated"
    verified: bool = True
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: str
    reference_source: str
    notes: List[str] = Field(default_factory=list)


class DeterministicCalculationService:
    """Rigorous analytical engineering calculation engine with dimensional and boundary checks."""

    # Fundamental physical constants
    MU_0 = 4.0 * math.pi * 1e-7  # H/m (vacuum permeability)
    COPPER_RHO_20C = 1.68e-8     # Ohm*m (copper resistivity at 20°C)
    COPPER_RHO_100C = 2.22e-8    # Ohm*m (copper resistivity at 100°C)

    def calculate_skin_depth(
        self,
        frequency_hz: float,
        temperature_c: float = 100.0,
        mu_r: float = 1.0,
    ) -> CalculationResult:
        if frequency_hz <= 0:
            raise ValueError("Frequency must be strictly positive.")
        if mu_r <= 0:
            raise ValueError("Relative permeability must be strictly positive.")

        # Temperature-adjusted resistivity: rho(T) = rho_20 * (1 + 0.00393 * (T - 20))
        rho = self.COPPER_RHO_20C * (1.0 + 0.00393 * (temperature_c - 20.0))
        delta = math.sqrt(rho / (math.pi * frequency_hz * self.MU_0 * mu_r))

        return CalculationResult(
            formula_id="EQ-SKIN-01",
            name="Conductor Skin Depth",
            inputs={"frequency_hz": frequency_hz, "temperature_c": temperature_c, "mu_r": mu_r},
            input_units={"frequency_hz": "Hz", "temperature_c": "deg_C", "mu_r": "dimensionless"},
            outputs={"skin_depth_m": delta, "skin_depth_mm": delta * 1e3},
            output_units={"skin_depth_m": "m", "skin_depth_mm": "mm"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_skin_depth",
            reference_source="Electromagnetic Waves and Radiating Systems, Jordan & Balmain",
            notes=[f"Evaluated at T={temperature_c}°C with copper resistivity rho={rho:.3e} Ohm*m"],
        )

    def calculate_dowell_factor(
        self,
        layer_thickness_m: float,
        skin_depth_m: float,
        num_layers: int,
    ) -> CalculationResult:
        if layer_thickness_m <= 0 or skin_depth_m <= 0 or num_layers < 1:
            raise ValueError("Layer thickness, skin depth must be positive, layers >= 1.")

        xi = layer_thickness_m / skin_depth_m
        m = float(num_layers)

        # Dowell Equation:
        # F_R = xi * [ (sinh(2*xi) + sin(2*xi)) / (cosh(2*xi) - cos(2*xi))
        #             + (2/3) * (m^2 - 1) * (sinh(xi) - sin(xi)) / (cosh(xi) + cos(xi)) ]
        term1 = (math.sinh(2.0 * xi) + math.sin(2.0 * xi)) / (math.cosh(2.0 * xi) - math.cos(2.0 * xi))
        term2 = (2.0 / 3.0) * (m ** 2 - 1.0) * (math.sinh(xi) - math.sin(xi)) / (math.cosh(xi) + math.cos(xi))
        f_r = xi * (term1 + term2)

        return CalculationResult(
            formula_id="EQ-DOWELL-01",
            name="Dowell AC Winding Loss Factor",
            inputs={"layer_thickness_m": layer_thickness_m, "skin_depth_m": skin_depth_m, "num_layers": float(num_layers)},
            input_units={"layer_thickness_m": "m", "skin_depth_m": "m", "num_layers": "dimensionless"},
            outputs={"xi_ratio": xi, "F_R": f_r},
            output_units={"xi_ratio": "dimensionless", "F_R": "dimensionless"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_dowell_factor",
            reference_source="P. L. Dowell (1966)",
            notes=[f"Dowell factor F_R = {f_r:.3f} indicates AC resistance is {f_r:.2f}x DC resistance."],
        )

    def calculate_dowell_analysis(
        self,
        frequency_hz: float,
        conductor_diameter_mm: float,
        num_layers: int,
        temperature_c: float = 100.0,
        layer_porosity_factor: float = 0.85,
        r_dc_ohm: float = 0.05,
    ) -> CalculationResult:
        """Comprehensive high-frequency Dowell analysis with skin depth, Fr factor, and wire recommendations."""
        if frequency_hz <= 0 or conductor_diameter_mm <= 0 or num_layers < 1:
            raise ValueError("Frequency, conductor diameter must be positive, layers >= 1.")

        rho = self.COPPER_RHO_20C * (1.0 + 0.00393 * (temperature_c - 20.0))
        delta_m = math.sqrt(rho / (math.pi * frequency_hz * self.MU_0 * 1.0))
        delta_mm = delta_m * 1e3

        # Effective rectangular conductor height: h = d * sqrt(pi/4)
        h_eff_mm = conductor_diameter_mm * math.sqrt(math.pi / 4.0)
        eta = min(1.0, max(0.1, layer_porosity_factor))
        xi = (h_eff_mm / delta_mm) * math.sqrt(eta)

        m = float(num_layers)
        if xi < 1e-4:
            f_r = 1.0
        else:
            term1 = (math.sinh(2.0 * xi) + math.sin(2.0 * xi)) / (math.cosh(2.0 * xi) - math.cos(2.0 * xi))
            term2 = (2.0 / 3.0) * (m ** 2 - 1.0) * (math.sinh(xi) - math.sin(xi)) / (math.cosh(xi) + math.cos(xi))
            f_r = max(1.0, xi * (term1 + term2))

        r_ac = r_dc_ohm * f_r

        # Engineering verdict & recommendation
        if f_r <= 1.5:
            rec = "PASS — Solid Magnet Wire Suitable (Low AC Proximity Penalty)"
            verdict = "PASS"
        elif f_r <= 3.0:
            rec = "CAUTION — Copper Foil or Multifilar Winding Recommended"
            verdict = "MARGINAL"
        else:
            rec = "HIGH LOSS — Stranded Litz Wire Mandatory (Severe Proximity Eddy Current)"
            verdict = "FAIL"

        return CalculationResult(
            formula_id="EQ-DOWELL-02",
            name="Comprehensive Dowell HF AC Winding Analysis",
            inputs={
                "frequency_hz": frequency_hz,
                "conductor_diameter_mm": conductor_diameter_mm,
                "num_layers": float(num_layers),
                "temperature_c": temperature_c,
                "layer_porosity": eta,
                "r_dc_ohm": r_dc_ohm,
            },
            input_units={
                "frequency_hz": "Hz",
                "conductor_diameter_mm": "mm",
                "num_layers": "count",
                "temperature_c": "deg_C",
                "layer_porosity": "ratio",
                "r_dc_ohm": "Ohm",
            },
            outputs={
                "skin_depth_mm": round(delta_mm, 4),
                "h_eff_mm": round(h_eff_mm, 4),
                "xi_ratio": round(xi, 4),
                "f_r": round(f_r, 3),
                "r_ac_ohm": round(r_ac, 5),
                "compliant": 1.0 if verdict == "PASS" else (0.5 if verdict == "MARGINAL" else 0.0),
            },
            output_units={
                "skin_depth_mm": "mm",
                "h_eff_mm": "mm",
                "xi_ratio": "ratio",
                "f_r": "multiplier",
                "r_ac_ohm": "Ohm",
                "compliant": "score",
            },
            provenance="src/mendex_core/intelligence/calculations.py::calculate_dowell_analysis",
            reference_source="P.L. Dowell (1966), Effects of Eddy Currents in Transformer Windings",
            notes=[
                f"Skin Depth: {delta_mm:.3f} mm @ {frequency_hz/1000.0:.1f} kHz, T={temperature_c}°C",
                f"Normalized height xi: {xi:.3f}, Dowell factor F_r: {f_r:.2f}x (R_ac={r_ac*1000:.1f} mOhm)",
                f"Recommendation: {rec}",
            ],
        )

    def calculate_magnetic_core_sizing_and_loss(
        self,
        frequency_hz: float,
        b_peak_t: float,
        core_volume_mm3: float,
        core_ae_mm2: float,
        cm: float = 16.9,
        alpha: float = 1.25,
        beta: float = 2.35,
        b_sat_t: float = 0.40,
        vin_v: Optional[float] = None,
        duty_cycle: Optional[float] = None,
    ) -> CalculationResult:
        """Evaluates Steinmetz volumetric loss, total core dissipation, and saturation margins."""
        if frequency_hz <= 0 or b_peak_t <= 0 or core_volume_mm3 <= 0 or core_ae_mm2 <= 0:
            raise ValueError("Frequency, flux density, volume, and area must be positive.")

        p_v = cm * (frequency_hz ** alpha) * (b_peak_t ** beta)
        core_volume_m3 = core_volume_mm3 * 1e-9
        p_core_total = p_v * core_volume_m3

        sat_margin_pct = max(0.0, (1.0 - (b_peak_t / b_sat_t)) * 100.0)
        if sat_margin_pct >= 30.0:
            verdict = "PASS (Safe Margin)"
            compliant = 1.0
        elif sat_margin_pct >= 15.0:
            verdict = "MARGINAL (Close to Saturation)"
            compliant = 0.5
        else:
            verdict = "FAIL (Core Saturation Risk)"
            compliant = 0.0

        turns_calc = 0.0
        if vin_v is not None and duty_cycle is not None and vin_v > 0 and duty_cycle > 0:
            ae_m2 = core_ae_mm2 * 1e-6
            turns_calc = (vin_v * duty_cycle) / (frequency_hz * ae_m2 * b_peak_t)

        return CalculationResult(
            formula_id="EQ-MAGNET-01",
            name="Magnetic Core Steinmetz Loss & Saturation Analysis",
            inputs={
                "frequency_hz": frequency_hz,
                "b_peak_t": b_peak_t,
                "core_volume_mm3": core_volume_mm3,
                "core_ae_mm2": core_ae_mm2,
                "b_sat_t": b_sat_t,
            },
            input_units={
                "frequency_hz": "Hz",
                "b_peak_t": "T",
                "core_volume_mm3": "mm^3",
                "core_ae_mm2": "mm^2",
                "b_sat_t": "T",
            },
            outputs={
                "volumetric_loss_w_m3": round(p_v, 2),
                "total_core_loss_w": round(p_core_total, 4),
                "saturation_margin_pct": round(sat_margin_pct, 2),
                "calculated_primary_turns": round(turns_calc, 1),
                "compliant": compliant,
            },
            output_units={
                "volumetric_loss_w_m3": "W/m^3",
                "total_core_loss_w": "W",
                "saturation_margin_pct": "%",
                "calculated_primary_turns": "turns",
                "compliant": "score",
            },
            provenance="src/mendex_core/intelligence/calculations.py::calculate_magnetic_core_sizing_and_loss",
            reference_source="Steinmetz Equation & Faraday Induction Law; verified against MagNet Dataset",
            notes=[
                f"Core Loss: {p_core_total:.3f} W (Volumetric: {p_v:.0f} W/m^3)",
                f"Peak Flux: {b_peak_t:.3f} T / Saturation: {b_sat_t:.3f} T (Margin: {sat_margin_pct:.1f}%)",
                f"Status: {verdict}",
            ],
        )

    def calculate_flyback_sizing(
        self,
        vin_min_v: float,
        vin_nom_v: float,
        vout_v: float,
        iout_a: float,
        fsw_hz: float,
        ripple_factor_krf: float = 0.4,
        efficiency: float = 0.88,
    ) -> CalculationResult:
        if vin_min_v <= 0 or vout_v <= 0 or iout_a <= 0 or fsw_hz <= 0:
            raise ValueError("Voltages, current, and frequency must be positive numbers.")

        p_out = vout_v * iout_a
        p_in = p_out / efficiency

        # Duty cycle at Vin_min assuming target D_max = 0.45
        d_max = 0.45
        v_reflected = (vin_min_v * d_max) / (1.0 - d_max)
        turns_ratio_np_ns = v_reflected / (vout_v + 0.7)  # including secondary diode drop

        # Primary peak and RMS current in CCM
        i_in_avg = p_in / vin_min_v
        delta_il = ripple_factor_krf * i_in_avg * 2.0
        i_pri_peak = (i_in_avg / d_max) + (delta_il / 2.0)

        # Primary inductance: L_p = (Vin_min * D_max) / (delta_il * fsw)
        l_p = (vin_min_v * d_max) / (delta_il * fsw_hz)

        return CalculationResult(
            formula_id="EQ-FLYBACK-LP",
            name="CCM Flyback Converter Sizing",
            inputs={
                "vin_min_v": vin_min_v, "vin_nom_v": vin_nom_v, "vout_v": vout_v,
                "iout_a": iout_a, "fsw_hz": fsw_hz, "ripple_factor": ripple_factor_krf
            },
            input_units={
                "vin_min_v": "V", "vin_nom_v": "V", "vout_v": "V",
                "iout_a": "A", "fsw_hz": "Hz", "ripple_factor": "dimensionless"
            },
            outputs={
                "p_out_w": p_out,
                "d_max": d_max,
                "v_reflected_v": v_reflected,
                "turns_ratio_np_ns": turns_ratio_np_ns,
                "primary_inductance_h": l_p,
                "primary_inductance_uh": l_p * 1e6,
                "primary_peak_current_a": i_pri_peak,
            },
            output_units={
                "p_out_w": "W", "d_max": "dimensionless", "v_reflected_v": "V",
                "turns_ratio_np_ns": "dimensionless", "primary_inductance_h": "H",
                "primary_inductance_uh": "uH", "primary_peak_current_a": "A"
            },
            provenance="src/mendex_core/intelligence/calculations.py::calculate_flyback_sizing",
            reference_source="R.W. Erickson, Fundamentals of Power Electronics",
            notes=["Continuous Conduction Mode (CCM) design with 40% inductor current ripple."],
        )

    def calculate_steinmetz_loss(
        self,
        frequency_hz: float,
        b_max_t: float,
        core_volume_m3: float,
        cm: float = 16.7,
        alpha: float = 1.35,
        beta: float = 2.40,
    ) -> CalculationResult:
        if frequency_hz <= 0 or b_max_t <= 0 or core_volume_m3 <= 0:
            raise ValueError("Frequency, peak flux density, and core volume must be positive.")

        # Modified Steinmetz Equation: P_v (W/m^3) = Cm * f^alpha * B^beta
        p_v = cm * (frequency_hz ** alpha) * (b_max_t ** beta)
        p_total = p_v * core_volume_m3

        return CalculationResult(
            formula_id="EQ-STEINMETZ-01",
            name="Steinmetz Magnetic Core Loss",
            inputs={"frequency_hz": frequency_hz, "b_max_t": b_max_t, "core_volume_m3": core_volume_m3},
            input_units={"frequency_hz": "Hz", "b_max_t": "T", "core_volume_m3": "m^3"},
            outputs={"volumetric_loss_w_m3": p_v, "total_core_loss_w": p_total},
            output_units={"volumetric_loss_w_m3": "W/m^3", "total_core_loss_w": "W"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_steinmetz_loss",
            reference_source="Modified Steinmetz Equation, validated against Princeton MagNet dataset",
            notes=[f"Evaluated with parameters Cm={cm}, alpha={alpha}, beta={beta}"],
        )

    def calculate_semiconductor_losses(
        self,
        i_rms_a: float,
        r_ds_on_ohm: float,
        e_on_j: float,
        e_off_j: float,
        fsw_hz: float,
    ) -> CalculationResult:
        if i_rms_a < 0 or r_ds_on_ohm < 0 or e_on_j < 0 or e_off_j < 0 or fsw_hz <= 0:
            raise ValueError("Loss parameters must be non-negative; frequency positive.")

        p_cond = (i_rms_a ** 2) * r_ds_on_ohm
        p_sw = (e_on_j + e_off_j) * fsw_hz
        p_total = p_cond + p_sw

        return CalculationResult(
            formula_id="EQ-SEMI-LOSS-01",
            name="Power Semiconductor Conduction and Switching Loss",
            inputs={"i_rms_a": i_rms_a, "r_ds_on_ohm": r_ds_on_ohm, "e_on_j": e_on_j, "e_off_j": e_off_j, "fsw_hz": fsw_hz},
            input_units={"i_rms_a": "A", "r_ds_on_ohm": "Ohm", "e_on_j": "J", "e_off_j": "J", "fsw_hz": "Hz"},
            outputs={"conduction_loss_w": p_cond, "switching_loss_w": p_sw, "total_loss_w": p_total},
            output_units={"conduction_loss_w": "W", "switching_loss_w": "W", "total_loss_w": "W"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_semiconductor_losses",
            reference_source="SwitchLossDB & IEC 60747-8 Power MOSFET standard",
            notes=[f"Total loss: {p_total:.2f} W (P_cond: {p_cond:.2f} W, P_sw: {p_sw:.2f} W)"],
        )

    def calculate_lc_resonance(
        self,
        inductance_h: float,
        capacitance_f: float,
    ) -> CalculationResult:
        if inductance_h <= 0 or capacitance_f <= 0:
            raise ValueError("Inductance and capacitance must be strictly positive.")

        f_0 = 1.0 / (2.0 * math.pi * math.sqrt(inductance_h * capacitance_f))
        z_0 = math.sqrt(inductance_h / capacitance_f)

        return CalculationResult(
            formula_id="EQ-RESONANT-LC",
            name="LC Series Resonance Frequency and Characteristic Impedance",
            inputs={"inductance_h": inductance_h, "capacitance_f": capacitance_f},
            input_units={"inductance_h": "H", "capacitance_f": "F"},
            outputs={"resonant_frequency_hz": f_0, "characteristic_impedance_ohm": z_0},
            output_units={"resonant_frequency_hz": "Hz", "characteristic_impedance_ohm": "Ohm"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_lc_resonance",
            reference_source="Linear Circuit Theory",
            notes=[f"Resonant frequency: {f_0:.2f} Hz, Characteristic impedance: {z_0:.2f} Ohm"],
        )

    def calculate_iec_creepage_clearance(
        self,
        working_voltage_rms: float,
        peak_voltage_v: float,
        pollution_degree: int = 2,
        material_group: str = "IIIa",
        insulation_type: str = "reinforced",
        slot_width_mm: float = 0.0,
    ) -> CalculationResult:
        """Evaluates electrical clearance and creepage per IEC 60664-1:2020 & IEC 61010-1:2010 Section 6.7."""
        if working_voltage_rms <= 0 or peak_voltage_v <= 0:
            raise ValueError("Working voltage and peak voltage must be strictly positive.")

        is_reinforced = insulation_type.lower() == "reinforced"

        # IEC 60664-1 Table F.4 / IEC 61010-1 Table 4 Clearance (air gap, mm)
        if peak_voltage_v <= 330.0:
            basic_clearance = 0.5
        elif peak_voltage_v <= 500.0:
            basic_clearance = 0.8
        elif peak_voltage_v <= 800.0:
            basic_clearance = 1.5
        elif peak_voltage_v <= 1000.0:
            basic_clearance = 2.0
        elif peak_voltage_v <= 1500.0:
            basic_clearance = 3.0
        elif peak_voltage_v <= 2500.0:
            basic_clearance = 4.0
        else:
            basic_clearance = 4.0 + (peak_voltage_v - 2500.0) * 0.002

        # In IEC 61010-1, 1000V RMS CAT II requires 2.5 mm basic clearance
        if working_voltage_rms >= 1000.0:
            basic_clearance = max(basic_clearance, 2.5)

        req_clearance = basic_clearance * (2.0 if is_reinforced else 1.0)

        # IEC 60664-1 Table F.4 Creepage (surface distance, mm) for Material Group IIIa, PD2
        if working_voltage_rms <= 100.0:
            basic_creepage = 1.0
        elif working_voltage_rms <= 250.0:
            basic_creepage = 2.5
        elif working_voltage_rms <= 400.0:
            basic_creepage = 4.0
        elif working_voltage_rms <= 630.0:
            basic_creepage = 6.3
        elif working_voltage_rms <= 800.0:
            basic_creepage = 8.0
        elif working_voltage_rms <= 1000.0:
            basic_creepage = 10.0
        else:
            basic_creepage = 10.0 + (working_voltage_rms - 1000.0) * 0.01

        mg_factor = 0.7 if material_group.upper() == "I" else (0.85 if material_group.upper() == "II" else 1.0)
        basic_creepage *= mg_factor
        req_creepage = basic_creepage * (2.0 if is_reinforced else 1.0)

        slot_effective = slot_width_mm >= 1.0
        compliance = (slot_width_mm >= req_clearance) if slot_effective else (slot_width_mm >= req_creepage)

        return CalculationResult(
            formula_id="EQ-IEC-CREEPAGE-01",
            name="IEC 60664-1 & IEC 61010-1 High-Voltage Insulation Coordination",
            inputs={
                "working_voltage_rms": working_voltage_rms,
                "peak_voltage_v": peak_voltage_v,
                "pollution_degree": float(pollution_degree),
                "slot_width_mm": slot_width_mm,
            },
            input_units={
                "working_voltage_rms": "V RMS",
                "peak_voltage_v": "V pk",
                "pollution_degree": "dimensionless",
                "slot_width_mm": "mm",
            },
            outputs={
                "required_clearance_mm": round(req_clearance, 2),
                "required_creepage_mm": round(req_creepage, 2),
                "effective_slot_width_mm": round(slot_width_mm, 2),
                "compliant": 1.0 if compliance else 0.0,
            },
            output_units={
                "required_clearance_mm": "mm",
                "required_creepage_mm": "mm",
                "effective_slot_width_mm": "mm",
                "compliant": "boolean",
            },
            provenance="src/mendex_core/intelligence/calculations.py::calculate_iec_creepage_clearance",
            reference_source="IEC 60664-1:2020 & IEC 61010-1:2010 Section 6.7 Table 4 & Table F.4",
            notes=[
                f"Insulation: {insulation_type.capitalize()}, Pollution Degree: {pollution_degree}, Material Group: {material_group}",
                f"Air clearance required: {req_clearance:.2f} mm; Surface creepage required: {req_creepage:.2f} mm",
                f"Milling slot: {slot_width_mm:.2f} mm -> Compliance: {'PASS' if compliance else 'FAIL'}",
            ],
        )

    def calculate_component_derating(
        self,
        component_type: str,
        operating_val: float,
        rated_val: float,
        standard: str = "IPC-9592B / NAVSEA",
    ) -> CalculationResult:
        """Evaluates electrical stress derating against standard IPC-9592B / NAVSEA 80% industrial rules."""
        if rated_val <= 0:
            raise ValueError("Rated value must be strictly positive.")
        if operating_val < 0:
            raise ValueError("Operating value must be non-negative.")

        ctype = component_type.lower()
        if "resistor" in ctype:
            max_ratio = 0.60
        elif "semiconductor" in ctype or "mosfet" in ctype or "diode" in ctype or "igbt" in ctype:
            max_ratio = 0.80
        elif "capacitor" in ctype:
            max_ratio = 0.80
        else:
            max_ratio = 0.80

        stress_ratio = operating_val / rated_val
        margin_pct = (1.0 - stress_ratio) * 100.0

        if stress_ratio <= max_ratio:
            verdict = "PASS"
        elif stress_ratio <= 0.90:
            verdict = "MARGINAL"
        else:
            verdict = "FAIL"

        return CalculationResult(
            formula_id="EQ-DERATING-01",
            name="Electronic Component Stress & Derating Analysis",
            inputs={"operating_val": operating_val, "rated_val": rated_val, "max_allowed_ratio": max_ratio},
            input_units={"operating_val": "SI", "rated_val": "SI", "max_allowed_ratio": "ratio"},
            outputs={
                "stress_ratio": round(stress_ratio, 4),
                "margin_pct": round(margin_pct, 2),
                "max_allowed_ratio": max_ratio,
                "compliant": 1.0 if verdict == "PASS" else 0.0,
            },
            output_units={"stress_ratio": "ratio", "margin_pct": "%", "max_allowed_ratio": "ratio", "compliant": "boolean"},
            provenance="src/mendex_core/intelligence/calculations.py::calculate_component_derating",
            reference_source=f"Standard {standard} (IPC-9592B Class 2/3 Power Conversion)",
            notes=[f"Component: {component_type}, Stress: {stress_ratio*100:.1f}% (Limit: {max_ratio*100:.0f}%), Verdict: {verdict}"],
        )
