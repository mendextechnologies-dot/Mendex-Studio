import pytest
from integrations.calculations.winding_losses import (
    calculate_skin_depth,
    calculate_dowell_ac_resistance,
)
from integrations.calculations.transformer_design import (
    calculate_flyback_transformer_parameters,
)


def test_skin_depth_calculation():
    # At 100 kHz in copper at 100 deg C:
    # rho ~= 2.2e-8 Ohm*m
    # delta ~= sqrt(2.2e-8 / (pi * 4pi*1e-7 * 1e5)) ~= 0.236 mm
    res_100k = calculate_skin_depth(100000.0, temperature_c=100.0)
    assert 0.20 <= res_100k.skin_depth_mm <= 0.26
    assert res_100k.frequency_hz == 100000.0

    # At 1 MHz, skin depth must be smaller (~0.075 mm)
    res_1m = calculate_skin_depth(1000000.0, temperature_c=100.0)
    assert res_1m.skin_depth_mm < res_100k.skin_depth_mm


def test_dowell_ac_resistance_factor():
    # Single layer (m=1), thin wire (0.2 mm) at 100 kHz: F_R should be close to 1.0
    res_single = calculate_dowell_ac_resistance(
        frequency_hz=100000.0,
        conductor_diameter_mm=0.2,
        layers_count=1,
        r_dc_ohm=0.1,
    )
    assert 1.0 <= res_single.f_r <= 1.2
    assert res_single.r_ac_ohm >= res_single.r_dc_ohm

    # 4 layers (m=4), thicker wire (0.8 mm) at 100 kHz: F_R must be significantly higher due to proximity effect
    res_multi = calculate_dowell_ac_resistance(
        frequency_hz=100000.0,
        conductor_diameter_mm=0.8,
        layers_count=4,
        r_dc_ohm=0.1,
    )
    assert res_multi.f_r > res_single.f_r
    assert res_multi.f_r > 2.0


def test_flyback_transformer_sizing():
    # Pilot MX-HVDC-001 illustrative target:
    # 24V nominal (20V min), 1000V @ 50mA = 50W output, 100kHz, 45% duty cycle, EF25 core (Ae = 52.5 mm^2)
    design = calculate_flyback_transformer_parameters(
        vin_min_v=20.0,
        vin_nom_v=24.0,
        vout_v=1000.0,
        iout_a=0.05,
        frequency_hz=100000.0,
        d_max=0.45,
        efficiency=0.88,
        b_max_t=0.22,
        core_ae_mm2=52.5,
    )

    assert design.power_output_w == 50.0
    assert design.primary_turns >= 5
    assert design.secondary_turns > design.primary_turns  # Step-up transformer
    assert design.primary_inductance_uh > 0.0
    assert design.air_gap_mm > 0.0
    assert design.air_gap_mm < 5.0  # Realistic physical gap for EF25/ETD core


def test_invalid_parameters_rejected():
    with pytest.raises(ValueError, match="Frequency must be greater than zero"):
        calculate_skin_depth(-100.0)

    with pytest.raises(ValueError, match="Layers count"):
        calculate_dowell_ac_resistance(100e3, 0.5, 0)

    with pytest.raises(ValueError, match="Maximum duty cycle"):
        calculate_flyback_transformer_parameters(20.0, 24.0, 1000.0, 0.05, d_max=0.95)
