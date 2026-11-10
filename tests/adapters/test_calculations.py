import pytest
from integrations.calculations.power_losses import (
    calculate_semiconductor_losses,
    calculate_core_loss_steinmetz,
)


def test_semiconductor_loss_calculation():
    # Example: C3M0065090D (SiC MOSFET), 65 mOhm, 10A RMS, 45% duty cycle, Eon=85uJ, Eoff=22uJ, 100kHz
    res = calculate_semiconductor_losses(
        part_number="C3M0065090D",
        r_ds_on_ohm=0.065,
        i_rms_a=10.0,
        duty_cycle=0.45,
        e_on_j=85e-6,
        e_off_j=22e-6,
        frequency_hz=100000.0,
    )
    # P_cond = (10^2) * 0.065 * 0.45 = 2.925 W
    assert abs(res.p_conduction_w - 2.925) < 1e-3
    # P_sw = (85u + 22u) * 100k = 107u * 100k = 10.7 W
    assert abs(res.p_switching_w - 10.7) < 1e-3
    # P_total = 2.925 + 10.7 = 13.625 W
    assert abs(res.p_total_w - 13.625) < 1e-3


def test_core_loss_steinmetz_calculation():
    # Example: N87 ferrite core at 100kHz, 0.1T, volume = 15 cm^3 = 15e-6 m^3
    # k=7.13, alpha=1.42, beta=2.65
    res = calculate_core_loss_steinmetz(
        material="N87",
        k=7.13,
        alpha=1.42,
        beta=2.65,
        frequency_hz=100000.0,
        b_peak_t=0.1,
        core_volume_m3=15e-6,
    )
    assert res.volumetric_loss_w_m3 > 0.0
    assert res.total_core_loss_w > 0.0
    assert res.material == "N87"


def test_invalid_parameters_raise_value_error():
    with pytest.raises(ValueError, match="Duty cycle"):
        calculate_semiconductor_losses("TEST", 0.1, 5.0, 1.5, 10e-6, 10e-6, 100e3)

    with pytest.raises(ValueError, match="Frequency"):
        calculate_semiconductor_losses("TEST", 0.1, 5.0, 0.5, 10e-6, 10e-6, -100.0)

    with pytest.raises(ValueError, match="strictly positive"):
        calculate_core_loss_steinmetz("N87", 7.13, 1.42, 2.65, -1000.0, 0.1, 1e-5)
