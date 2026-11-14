"""Golden regression test for P0-5: Verifying mathematical sizing of Flyback converter and transformer."""
import pytest
from mendex_core.intelligence.calculations import DeterministicCalculationService
from integrations.calculations.transformer_design import calculate_flyback_transformer_parameters


def test_flyback_sizing_matches_hand_calculation():
    calc = DeterministicCalculationService()
    # Benchmark case from audit report 04:
    # 85V -> 12V @ 2A, 100kHz, K_RF=0.4, efficiency=0.88, D_max=0.45
    result = calc.calculate_flyback_sizing(
        vin_min_v=85.0,
        vin_nom_v=110.0,
        vout_v=12.0,
        iout_a=2.0,
        fsw_hz=100e3,
        ripple_factor_krf=0.4,
        efficiency=0.88,
    )
    outputs = result.outputs

    # P_out = 24W, P_in = 27.2727W
    assert abs(outputs["p_out_w"] - 24.0) < 0.01

    # Hand calculation: L_p = 670.6 uH (previous buggy code produced 1490.2 uH)
    assert 669.0 < outputs["primary_inductance_uh"] < 672.0, f"Expected ~670.6 uH, got {outputs['primary_inductance_uh']}"

    # Hand calculation: I_pri_peak = 0.998 A (previous buggy code produced 0.841 A)
    assert 0.990 < outputs["primary_peak_current_a"] < 1.005, f"Expected ~0.998 A, got {outputs['primary_peak_current_a']}"


def test_transformer_design_never_exceeds_flux_limit():
    # Sizing ETD34 transformer with Ae = 52 mm2, B_max = 0.25 T
    design = calculate_flyback_transformer_parameters(
        vin_min_v=85.0,
        vin_nom_v=110.0,
        vout_v=12.0,
        iout_a=2.0,
        frequency_hz=100e3,
        d_max=0.45,
        b_max_t=0.25,
        core_ae_mm2=52.0,
        v_diode_drop_v=0.7,
        efficiency=0.88,
    )

    ae_m2 = 52.0 * 1e-6
    # Calculate actual peak flux density: B_pk = (Lm * I_pk) / (Np * Ae)
    b_pk_actual = (design.primary_inductance_h * design.primary_peak_current_a) / (design.primary_turns * ae_m2)

    # Must be strictly <= B_max (previous code reached 0.276 T > 0.25 T)
    assert b_pk_actual <= 0.250 + 1e-6, f"Peak flux {b_pk_actual} exceeds B_max limit of 0.25 T"
