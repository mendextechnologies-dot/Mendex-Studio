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


from integrations.calculations.thermal_sizing import (
    calculate_semiconductor_thermal,
    calculate_magnetic_thermal,
    calculate_ipc2152_trace_thermal,
)


def test_semiconductor_thermal_calculation():
    # 2.5W dissipation, 25°C ambient, 150°C Tj_max, 80% derating (120°C limit)
    # Rth_jc=1.5 °C/W, Rth_cs=0.5 °C/W, Rth_sa=10.0 °C/W
    res = calculate_semiconductor_thermal(
        part_number="IPB65R190CFD",
        p_loss_w=2.5,
        t_ambient_c=25.0,
        t_j_max_c=150.0,
        derating_factor=0.80,
        r_th_jc_c_w=1.5,
        r_th_cs_c_w=0.5,
        r_th_sa_c_w=10.0,
    )
    # Rth_total = 1.5 + 0.5 + 10 = 12.0 °C/W
    assert res.r_th_total_c_w == 12.0
    # Tj = 25 + 2.5 * 12 = 55.0 °C
    assert res.t_junction_c == 55.0
    # Tc = 25 + 2.5 * (0.5 + 10) = 51.25 °C
    assert res.t_case_c == 51.25
    # Limit = 150 * 0.8 = 120.0 °C
    assert res.t_j_limit_c == 120.0
    # Margin = 120 - 55 = 65.0 °C
    assert res.thermal_margin_c == 65.0
    assert res.status == "PASS_DERATED"
    assert res.thermal_vias_recommended >= 1


def test_magnetic_thermal_calculation():
    # 0.5W core loss + 0.5W winding loss = 1.0W total on ETD34 (45 cm^2)
    # Ambient = 25°C, Class B limit = 130°C
    res = calculate_magnetic_thermal(
        component_name="T1_ETD34",
        p_core_w=0.5,
        p_winding_w=0.5,
        surface_area_cm2=45.0,
        t_ambient_c=25.0,
        t_class_max_c=130.0,
        insulation_class="Class B (130°C)",
    )
    # Delta_T = 450 * (1.0 / 45)^0.833 = ~18.8 °C
    assert 15.0 < res.delta_t_surface_c < 22.0
    assert res.t_surface_c > 40.0
    assert res.t_hotspot_c > res.t_surface_c
    assert res.thermal_margin_c > 50.0
    assert res.status == "PASS"


def test_ipc2152_trace_thermal_calculation():
    # 5.0A current, 10°C rise, 1oz copper (35 um) on external layer (F.Cu)
    res_ext = calculate_ipc2152_trace_thermal(
        current_a=5.0,
        target_delta_t_c=10.0,
        copper_thickness_oz=1.0,
        is_internal=False,
        layer_name="F.Cu",
    )
    assert res_ext.min_trace_width_mm > 0.5
    assert res_ext.min_trace_width_mm < 5.0
    assert res_ext.cross_sectional_area_mils2 > 0

    # Internal layer (In1.Cu) has poorer cooling -> requires wider trace
    res_int = calculate_ipc2152_trace_thermal(
        current_a=5.0,
        target_delta_t_c=10.0,
        copper_thickness_oz=1.0,
        is_internal=True,
        layer_name="In1.Cu",
    )
    assert res_int.min_trace_width_mm > res_ext.min_trace_width_mm


def test_thermal_invalid_parameters_raise_value_error():
    with pytest.raises(ValueError, match="Power loss must be non-negative"):
        calculate_semiconductor_thermal(p_loss_w=-1.0)
    with pytest.raises(ValueError, match="Max junction temperature"):
        calculate_semiconductor_thermal(t_ambient_c=100.0, t_j_max_c=80.0)
    with pytest.raises(ValueError, match="Surface area must be strictly positive"):
        calculate_magnetic_thermal(surface_area_cm2=-10.0)
    with pytest.raises(ValueError, match="Current must be strictly positive"):
        calculate_ipc2152_trace_thermal(current_a=-2.0)
