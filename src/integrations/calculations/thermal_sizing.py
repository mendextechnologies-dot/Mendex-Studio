"""Closed-form electro-thermal calculations per IPC-2152, IPC-9592B, and JEDEC standards."""
from __future__ import annotations

import math
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SemiconductorThermalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    part_number: str
    p_loss_w: float = Field(ge=0.0)
    t_ambient_c: float
    t_j_max_c: float = Field(gt=0.0)
    derating_factor: float = Field(gt=0.0, le=1.0)
    t_j_limit_c: float = Field(gt=0.0)  # derated limit: derating_factor * t_j_max_c
    r_th_jc_c_w: float = Field(ge=0.0)
    r_th_cs_c_w: float = Field(ge=0.0)
    r_th_sa_c_w: float = Field(ge=0.0)  # heatsink to ambient
    r_th_total_c_w: float = Field(ge=0.0)
    t_junction_c: float
    t_case_c: float
    thermal_margin_c: float  # t_j_limit_c - t_junction_c
    thermal_margin_pct: float  # (thermal_margin_c / delta_t_allowable) * 100
    heatsink_required_c_w: float = Field(ge=0.0)  # max allowable heatsink Rth to satisfy derated Tj
    pcb_copper_area_req_cm2: float = Field(ge=0.0)  # required 2oz copper area if PCB surface-cooled
    thermal_vias_recommended: int = Field(ge=1)
    status: str  # "PASS_DERATED", "PASS_ABSOLUTE_ONLY", "OVER_TEMPERATURE"
    unit: str = "Degrees Celsius (°C) and °C/W"


class MagneticThermalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component_name: str
    p_core_w: float = Field(ge=0.0)
    p_winding_w: float = Field(ge=0.0)
    p_total_w: float = Field(ge=0.0)
    surface_area_cm2: float = Field(gt=0.0)
    t_ambient_c: float
    t_class_max_c: float = Field(gt=0.0)  # e.g. 130.0 for Class B, 155.0 for Class F
    insulation_class: str
    delta_t_surface_c: float = Field(ge=0.0)
    t_surface_c: float
    t_hotspot_c: float
    thermal_margin_c: float
    r_th_mag_c_w: float = Field(ge=0.0)
    status: str
    unit: str = "Degrees Celsius (°C) and Watts (W)"


class IPC2152ThermalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    current_a: float = Field(gt=0.0)
    copper_thickness_oz: float = Field(gt=0.0)
    is_internal: bool
    layer_name: str
    target_delta_t_c: float = Field(gt=0.0)
    min_trace_width_mm: float = Field(gt=0.0)
    cross_sectional_area_mils2: float = Field(gt=0.0)
    trace_resistance_m_ohm_per_meter: float = Field(gt=0.0)
    conduction_loss_w_per_meter: float = Field(gt=0.0)
    formula: str = "IPC-2221 / IPC-2152 Conservative Derivation: I = k * Delta_T^0.44 * A^0.725"
    unit: str = "Millimeters (mm), Amperes (A), and Watts/meter"


def calculate_semiconductor_thermal(
    part_number: str = "UNSPECIFIED",
    p_loss_w: float = 1.0,
    t_ambient_c: float = 25.0,
    t_j_max_c: float = 150.0,
    derating_factor: float = 0.80,
    r_th_jc_c_w: float = 1.5,
    r_th_cs_c_w: float = 0.5,
    r_th_sa_c_w: float = 0.0,
) -> SemiconductorThermalResult:
    """Calculates junction temperature, required heatsink thermal resistance,

    and PCB copper cooling area under IPC-9592B / JEDEC standards.
    """
    if p_loss_w < 0.0:
        raise ValueError("Power loss must be non-negative")
    if t_j_max_c <= t_ambient_c:
        raise ValueError(f"Max junction temperature ({t_j_max_c}°C) must exceed ambient ({t_ambient_c}°C)")
    if derating_factor <= 0.0 or derating_factor > 1.0:
        raise ValueError("Derating factor must be in range (0.0, 1.0]")
    if r_th_jc_c_w < 0.0 or r_th_cs_c_w < 0.0 or r_th_sa_c_w < 0.0:
        raise ValueError("Thermal resistances must be non-negative")

    t_j_limit = t_j_max_c * derating_factor
    delta_t_allowable = max(0.01, t_j_limit - t_ambient_c)

    # Allowable total thermal resistance to meet derated junction limit
    if p_loss_w > 0:
        r_th_ja_derated = delta_t_allowable / p_loss_w
        r_th_sa_req = max(0.0, r_th_ja_derated - r_th_jc_c_w - r_th_cs_c_w)
    else:
        r_th_sa_req = 999.0

    # If heatsink Rth_sa is not provided (0.0), size heatsink with 20% safety margin per IPC-9592B
    if r_th_sa_c_w > 0:
        effective_r_sa = r_th_sa_c_w
    else:
        effective_r_sa = max(0.5, round(r_th_sa_req * 0.80, 2))
    r_th_total = r_th_jc_c_w + r_th_cs_c_w + effective_r_sa

    t_junction = t_ambient_c + p_loss_w * r_th_total
    t_case = t_ambient_c + p_loss_w * (r_th_cs_c_w + effective_r_sa)

    thermal_margin_c = t_j_limit - t_junction
    thermal_margin_pct = (thermal_margin_c / delta_t_allowable) * 100.0 if delta_t_allowable > 0 else 0.0

    # PCB copper area sizing for surface mount packages (IPC-2152 empirical formula for 2oz Cu):
    # Rth_cu_pcb = 50 / (A_cm2 ^ 0.70) => A_cm2 = (50 / Rth_sa_req) ^ (1 / 0.70)
    if r_th_sa_req > 0:
        pcb_area_cm2 = (50.0 / min(r_th_sa_req, 100.0)) ** (1.0 / 0.70)
    else:
        pcb_area_cm2 = 0.0

    # Thermal vias: each 0.3mm solder-filled via carries ~0.35W with low delta T
    vias_count = max(1, math.ceil(p_loss_w / 0.35)) if p_loss_w > 0 else 1

    if r_th_sa_c_w > 0:
        if t_junction <= t_j_limit:
            status = "PASS_DERATED"
        elif t_junction <= t_j_max_c:
            status = "PASS_ABSOLUTE_ONLY"
        else:
            status = "OVER_TEMPERATURE"
    else:
        # Heatsink was not explicitly specified by user; report sized heatsink requirement
        if r_th_sa_req <= 0:
            status = "OVER_TEMPERATURE"
        elif t_junction <= t_j_limit:
            status = "HEATSINK_SIZED"
        else:
            status = "OVER_TEMPERATURE"

    return SemiconductorThermalResult(
        part_number=part_number,
        p_loss_w=round(p_loss_w, 4),
        t_ambient_c=round(t_ambient_c, 2),
        t_j_max_c=round(t_j_max_c, 2),
        derating_factor=round(derating_factor, 3),
        t_j_limit_c=round(t_j_limit, 2),
        r_th_jc_c_w=round(r_th_jc_c_w, 3),
        r_th_cs_c_w=round(r_th_cs_c_w, 3),
        r_th_sa_c_w=round(effective_r_sa, 3),
        r_th_total_c_w=round(r_th_total, 3),
        t_junction_c=round(t_junction, 2),
        t_case_c=round(t_case, 2),
        thermal_margin_c=round(thermal_margin_c, 2),
        thermal_margin_pct=round(thermal_margin_pct, 1),
        heatsink_required_c_w=round(r_th_sa_req, 3),
        pcb_copper_area_req_cm2=round(pcb_area_cm2, 2),
        thermal_vias_recommended=vias_count,
        status=status,
    )


def calculate_magnetic_thermal(
    component_name: str = "T1",
    p_core_w: float = 0.5,
    p_winding_w: float = 0.5,
    surface_area_cm2: float = 45.0,  # e.g. ETD34
    t_ambient_c: float = 25.0,
    t_class_max_c: float = 130.0,  # Class B standard
    insulation_class: str = "Class B (130°C)",
) -> MagneticThermalResult:
    """Calculates magnetic component surface temperature rise, internal hotspot,

    and insulation safety margins using McLyman empirical free-air convection formulas.
    Delta_T = 450 * (P_total / A_t [cm^2]) ^ 0.833
    """
    if p_core_w < 0.0 or p_winding_w < 0.0:
        raise ValueError("Core and winding losses must be non-negative")
    if surface_area_cm2 <= 0.0:
        raise ValueError("Surface area must be strictly positive")
    if t_class_max_c <= t_ambient_c:
        raise ValueError(f"Class max temperature ({t_class_max_c}°C) must exceed ambient ({t_ambient_c}°C)")

    p_total = p_core_w + p_winding_w
    if p_total > 0:
        psi = p_total / surface_area_cm2
        delta_t_surface = 450.0 * (psi ** 0.833)
        r_th_mag = delta_t_surface / p_total
    else:
        delta_t_surface = 0.0
        r_th_mag = 0.0

    t_surface = t_ambient_c + delta_t_surface
    # Internal hotspot temperature: core center / primary winding carries 15% gradient
    t_hotspot = t_ambient_c + delta_t_surface * 1.15

    thermal_margin = t_class_max_c - t_hotspot
    status = "PASS" if thermal_margin >= 0 else "OVER_TEMPERATURE"

    return MagneticThermalResult(
        component_name=component_name,
        p_core_w=round(p_core_w, 4),
        p_winding_w=round(p_winding_w, 4),
        p_total_w=round(p_total, 4),
        surface_area_cm2=round(surface_area_cm2, 2),
        t_ambient_c=round(t_ambient_c, 2),
        t_class_max_c=round(t_class_max_c, 2),
        insulation_class=insulation_class,
        delta_t_surface_c=round(delta_t_surface, 2),
        t_surface_c=round(t_surface, 2),
        t_hotspot_c=round(t_hotspot, 2),
        thermal_margin_c=round(thermal_margin, 2),
        r_th_mag_c_w=round(r_th_mag, 3),
        status=status,
    )


def calculate_ipc2152_trace_thermal(
    current_a: float,
    target_delta_t_c: float = 10.0,
    copper_thickness_oz: float = 1.0,
    is_internal: bool = False,
    layer_name: str = "F.Cu",
) -> IPC2152ThermalResult:
    """Calculates minimum trace width, cross-sectional area, and linear loss
    using the IPC-2221 empirical power-law approximation for conservative trace sizing.
    Notice: Normative IPC-2152 qualification requires complete board stackup, plane coupling,
    and environmental factors; single-trace power laws provide analytical design baselines only.
    """
    if current_a <= 0.0:
        raise ValueError("Current must be strictly positive")
    if target_delta_t_c <= 0.0:
        raise ValueError("Target delta T must be strictly positive")
    if copper_thickness_oz <= 0.0:
        raise ValueError("Copper thickness must be strictly positive")

    k = 0.024 if is_internal else 0.048
    # Area [mils^2] = ( I / (k * Delta_T^0.44) ) ^ (1 / 0.725)
    area_mils2 = (current_a / (k * (target_delta_t_c ** 0.44))) ** (1.0 / 0.725)

    # Thickness in mils (1 oz Cu = 1.378 mils = 35 um)
    thickness_mils = copper_thickness_oz * 1.378
    width_mils = area_mils2 / thickness_mils
    width_mm = width_mils * 0.0254

    # Copper resistivity at 20°C: rho = 1.72e-8 Ohm*m. At 50°C: ~1.92e-8 Ohm*m
    area_m2 = area_mils2 * ((2.54e-5) ** 2)
    r_per_meter = (1.92e-8) / area_m2
    loss_per_meter = (current_a ** 2) * r_per_meter

    return IPC2152ThermalResult(
        current_a=round(current_a, 3),
        copper_thickness_oz=round(copper_thickness_oz, 2),
        is_internal=is_internal,
        layer_name=layer_name,
        target_delta_t_c=round(target_delta_t_c, 2),
        min_trace_width_mm=round(width_mm, 3),
        cross_sectional_area_mils2=round(area_mils2, 2),
        trace_resistance_m_ohm_per_meter=round(r_per_meter * 1000.0, 3),
        conduction_loss_w_per_meter=round(loss_per_meter, 3),
    )
