from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field


class SemiconductorLossResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    part_number: str
    p_conduction_w: float = Field(ge=0.0)
    p_switching_w: float = Field(ge=0.0)
    p_total_w: float = Field(ge=0.0)
    duty_cycle: float = Field(ge=0.0, le=1.0)
    frequency_hz: float = Field(gt=0.0)
    unit: str = "Watts (W)"


class CoreLossResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    material: str
    volumetric_loss_w_m3: float = Field(ge=0.0)
    total_core_loss_w: float = Field(ge=0.0)
    frequency_hz: float = Field(gt=0.0)
    b_peak_t: float = Field(gt=0.0)
    core_volume_m3: float = Field(gt=0.0)
    method: str = "Steinmetz Equation: Pv = k * f^alpha * B^beta"
    unit: str = "Watts (W)"


def calculate_semiconductor_losses(
    part_number: str,
    r_ds_on_ohm: float,
    i_rms_a: float,
    duty_cycle: float,
    e_on_j: float,
    e_off_j: float,
    frequency_hz: float,
) -> SemiconductorLossResult:
    """Calculates conduction and switching losses for a power semiconductor device

    under continuous/discontinuous operating conditions with explicit SI units.
    """
    if duty_cycle < 0.0 or duty_cycle > 1.0:
        raise ValueError("Duty cycle must be in range [0.0, 1.0]")
    if frequency_hz <= 0.0:
        raise ValueError("Frequency must be greater than zero")

    # Conduction loss: P_cond = I_on_rms^2 * R_ds_on * D
    # where i_rms_a is the conduction-interval RMS current during t_on.
    # (For full-period switch RMS current I_sw_rms = I_on_rms * sqrt(D), set duty_cycle=1.0).
    p_cond = (i_rms_a ** 2) * r_ds_on_ohm * duty_cycle
    p_sw = (e_on_j + e_off_j) * frequency_hz
    p_total = p_cond + p_sw

    return SemiconductorLossResult(
        part_number=part_number,
        p_conduction_w=round(p_cond, 6),
        p_switching_w=round(p_sw, 6),
        p_total_w=round(p_total, 6),
        duty_cycle=duty_cycle,
        frequency_hz=frequency_hz,
    )


def calculate_core_loss_steinmetz(
    material: str,
    k: float,
    alpha: float,
    beta: float,
    frequency_hz: float,
    b_peak_t: float,
    core_volume_m3: float,
) -> CoreLossResult:
    """Calculates volumetric and total magnetic core loss using Steinmetz parameters

    derived from verified MagNet material datasets.
    Pv = k * (f/1e3)^alpha * B^beta (W/m^3 or mW/cm^3 converted to W/m^3)
    """
    if frequency_hz <= 0.0 or b_peak_t <= 0.0 or core_volume_m3 <= 0.0:
        raise ValueError("Frequency, peak flux density, and core volume must be strictly positive")

    # Standard empirical Steinmetz form: Pv [W/m^3] = k * (f_hz / 1e3)^alpha * (B_t)^beta
    pv = k * ((frequency_hz / 1000.0) ** alpha) * (b_peak_t ** beta) * 1000.0
    p_total = pv * core_volume_m3

    return CoreLossResult(
        material=material,
        volumetric_loss_w_m3=round(pv, 2),
        total_core_loss_w=round(p_total, 4),
        frequency_hz=frequency_hz,
        b_peak_t=b_peak_t,
        core_volume_m3=core_volume_m3,
    )
