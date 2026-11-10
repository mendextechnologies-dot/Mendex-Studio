from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field

MU_0 = 4.0 * math.pi * 1e-7  # H/m


class FlybackTransformerDesign(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    power_output_w: float = Field(gt=0.0)
    power_input_w: float = Field(gt=0.0)
    turns_ratio_np_over_ns: float = Field(gt=0.0)
    primary_inductance_h: float = Field(gt=0.0)
    primary_inductance_uh: float = Field(gt=0.0)
    primary_peak_current_a: float = Field(gt=0.0)
    primary_rms_current_a: float = Field(gt=0.0)
    secondary_peak_current_a: float = Field(gt=0.0)
    secondary_rms_current_a: float = Field(gt=0.0)
    primary_turns: int = Field(ge=1)
    secondary_turns: int = Field(ge=1)
    air_gap_m: float = Field(gt=0.0)
    air_gap_mm: float = Field(gt=0.0)
    core_ae_m2: float = Field(gt=0.0)
    b_max_t: float = Field(gt=0.0)
    frequency_hz: float = Field(gt=0.0)


def calculate_flyback_transformer_parameters(
    vin_min_v: float,
    vin_nom_v: float,
    vout_v: float,
    iout_a: float,
    frequency_hz: float = 100000.0,
    d_max: float = 0.45,
    efficiency: float = 0.88,
    b_max_t: float = 0.25,
    core_ae_mm2: float = 125.0,  # e.g., EF25 or ETD29 core
    v_diode_drop_v: float = 1.0,
) -> FlybackTransformerDesign:
    """Calculates first-principles analytical parameters for an isolated Flyback power transformer

    operating in continuous / boundary conduction mode.
    """
    if vin_min_v <= 0.0 or vout_v <= 0.0 or iout_a <= 0.0 or frequency_hz <= 0.0:
        raise ValueError("Voltages, currents, and frequency must be positive non-zero quantities")
    if d_max <= 0.0 or d_max >= 0.8:
        raise ValueError("Maximum duty cycle must be in range (0.0, 0.8)")
    if efficiency <= 0.0 or efficiency > 1.0:
        raise ValueError("Efficiency must be in range (0.0, 1.0]")

    p_out = vout_v * iout_a
    p_in = p_out / efficiency

    # Turns ratio n = Np / Ns
    n = (vin_min_v / (vout_v + v_diode_drop_v)) * (d_max / (1.0 - d_max))

    # Core cross section in m^2
    ae_m2 = core_ae_mm2 * 1e-6

    # Minimum primary turns to avoid core saturation:
    # Np = (Vin_min * D_max) / (B_max * Ae * f_sw)
    np_raw = (vin_min_v * d_max) / (b_max_t * ae_m2 * frequency_hz)
    primary_turns = max(1, math.ceil(np_raw))

    # Secondary turns
    secondary_turns = max(1, round(primary_turns / n))

    # Actual turns ratio
    actual_n = primary_turns / secondary_turns

    # Primary magnetizing inductance Lm for target duty cycle:
    # Lm = (Vin_min * D_max)^2 / (2 * Pin * f_sw * K_rf)
    # where K_rf is ripple factor (assume 0.8 for continuous/borderline mode)
    l_m = ((vin_min_v * d_max) ** 2) / (2.0 * p_in * frequency_hz * 0.8)

    # Primary currents
    i_in_avg = p_in / vin_min_v
    delta_i = (vin_min_v * d_max) / (l_m * frequency_hz)
    i_pk_pri = (i_in_avg / d_max) + (delta_i / 2.0)
    i_rms_pri = math.sqrt(d_max * ((i_in_avg / d_max) ** 2 + (delta_i ** 2) / 12.0))

    # Secondary currents
    i_pk_sec = i_pk_pri * actual_n
    d_sec = 1.0 - d_max
    i_rms_sec = math.sqrt(d_sec * ((iout_a / d_sec) ** 2 + ((delta_i * actual_n) ** 2) / 12.0))

    # Physical air gap length:
    # lg = (mu_0 * Np^2 * Ae) / Lm
    air_gap_m = (MU_0 * (primary_turns ** 2) * ae_m2) / l_m
    air_gap_mm = air_gap_m * 1000.0

    return FlybackTransformerDesign(
        power_output_w=round(p_out, 3),
        power_input_w=round(p_in, 3),
        turns_ratio_np_over_ns=round(actual_n, 4),
        primary_inductance_h=round(l_m, 7),
        primary_inductance_uh=round(l_m * 1e6, 2),
        primary_peak_current_a=round(i_pk_pri, 3),
        primary_rms_current_a=round(i_rms_pri, 3),
        secondary_peak_current_a=round(i_pk_sec, 3),
        secondary_rms_current_a=round(i_rms_sec, 3),
        primary_turns=primary_turns,
        secondary_turns=secondary_turns,
        air_gap_m=round(air_gap_m, 7),
        air_gap_mm=round(air_gap_mm, 4),
        core_ae_m2=round(ae_m2, 8),
        b_max_t=b_max_t,
        frequency_hz=frequency_hz,
    )
