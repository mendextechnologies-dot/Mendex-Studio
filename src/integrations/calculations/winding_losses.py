from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field

# Physical Constants
MU_0 = 4.0 * math.pi * 1e-7  # Permeability of free space [H/m]
RHO_CU_20C = 1.68e-8          # Copper resistivity at 20 deg C [Ohm*m]
ALPHA_CU = 0.00393            # Temperature coefficient of copper [/deg C]


class SkinDepthResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frequency_hz: float = Field(gt=0.0)
    temperature_c: float = Field(ge=-40.0, le=250.0)
    resistivity_ohm_m: float = Field(gt=0.0)
    skin_depth_m: float = Field(gt=0.0)
    skin_depth_mm: float = Field(gt=0.0)
    unit: str = "Meters (m)"


class DowellLossFactorResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frequency_hz: float
    layers_count: int = Field(ge=1)
    skin_depth_mm: float = Field(gt=0.0)
    conductor_diameter_mm: float = Field(gt=0.0)
    xi: float = Field(ge=0.0, description="Normalized conductor height to skin depth ratio")
    f_r: float = Field(ge=1.0, description="Dowell AC-to-DC resistance factor (Rac / Rdc)")
    r_dc_ohm: float = Field(ge=0.0)
    r_ac_ohm: float = Field(ge=0.0)
    unit: str = "Dimensionless ratio / Ohms"


def calculate_copper_resistivity(temperature_c: float = 20.0) -> float:
    """Calculates temperature-dependent copper resistivity in Ohm*m."""
    return RHO_CU_20C * (1.0 + ALPHA_CU * (temperature_c - 20.0))


def calculate_skin_depth(frequency_hz: float, temperature_c: float = 100.0) -> SkinDepthResult:
    """Calculates penetration skin depth delta in copper wire:

    delta = sqrt(rho / (pi * mu_0 * f))
    """
    if frequency_hz <= 0.0:
        raise ValueError("Frequency must be greater than zero")

    rho = calculate_copper_resistivity(temperature_c)
    delta_m = math.sqrt(rho / (math.pi * MU_0 * frequency_hz))
    delta_mm = delta_m * 1000.0

    return SkinDepthResult(
        frequency_hz=frequency_hz,
        temperature_c=temperature_c,
        resistivity_ohm_m=round(rho, 11),
        skin_depth_m=round(delta_m, 9),
        skin_depth_mm=round(delta_mm, 6),
    )


def calculate_dowell_ac_resistance(
    frequency_hz: float,
    conductor_diameter_mm: float,
    layers_count: int,
    layer_porosity_factor: float = 0.85,
    r_dc_ohm: float = 0.05,
    temperature_c: float = 100.0,
) -> DowellLossFactorResult:
    """Calculates high-frequency AC winding resistance multiplier (F_R = R_ac / R_dc)

    using Dowell's analytical 1D formulation for multi-layer transformer windings.
    """
    if layers_count < 1:
        raise ValueError("Layers count must be at least 1")
    if conductor_diameter_mm <= 0.0 or layer_porosity_factor <= 0.0:
        raise ValueError("Conductor diameter and porosity must be positive")

    skin = calculate_skin_depth(frequency_hz, temperature_c)
    delta_mm = skin.skin_depth_mm

    # Effective rectangular conductor height with identical copper area
    # h = d * sqrt(pi/4) = 0.8862 * d
    h_eff_mm = conductor_diameter_mm * math.sqrt(math.pi / 4.0)

    # Normalized conductor height xi = (h_eff / delta) * sqrt(eta)
    eta = min(1.0, max(0.1, layer_porosity_factor))
    xi = (h_eff_mm / delta_mm) * math.sqrt(eta)

    # Dowell's equations
    # F_R = xi * [ (sinh(2xi) + sin(2xi)) / (cosh(2xi) - cos(2xi)) +
    #              (2 * (m^2 - 1) / 3) * (sinh(xi) - sin(xi)) / (cosh(xi) + cos(xi)) ]
    m = float(layers_count)

    # Numerator & denominator terms with numerical stability guards
    if xi < 1e-4:
        f_r = 1.0
    else:
        term1_num = math.sinh(2.0 * xi) + math.sin(2.0 * xi)
        term1_den = math.cosh(2.0 * xi) - math.cos(2.0 * xi)
        term1 = term1_num / term1_den if term1_den != 0.0 else 1.0

        term2_num = math.sinh(xi) - math.sin(xi)
        term2_den = math.cosh(xi) + math.cos(xi)
        term2_weight = (2.0 * (m ** 2 - 1.0)) / 3.0
        term2 = term2_weight * (term2_num / term2_den) if term2_den != 0.0 else 0.0

        f_r = xi * (term1 + term2)

    # F_R cannot be less than 1.0
    f_r = max(1.0, f_r)
    r_ac = r_dc_ohm * f_r

    return DowellLossFactorResult(
        frequency_hz=frequency_hz,
        layers_count=layers_count,
        skin_depth_mm=round(delta_mm, 6),
        conductor_diameter_mm=conductor_diameter_mm,
        xi=round(xi, 4),
        f_r=round(f_r, 4),
        r_dc_ohm=round(r_dc_ohm, 6),
        r_ac_ohm=round(r_ac, 6),
    )
