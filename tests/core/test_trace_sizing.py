import pytest
from mendex_core.design.trace_sizing import (
    calculate_ipc2152_trace_width,
    calculate_trace_ampacity,
    calculate_power_netclasses,
    generate_power_routing_plan,
)


def test_ipc2152_trace_width_derivation():
    """Verifies that IPC-2152 trace sizing increases monotonically with current and respects copper weight."""
    w_1a = calculate_ipc2152_trace_width(current_a=1.0, delta_t_c=20.0, copper_weight_oz=1.0)
    w_5a = calculate_ipc2152_trace_width(current_a=5.0, delta_t_c=20.0, copper_weight_oz=1.0)
    w_10a = calculate_ipc2152_trace_width(current_a=10.0, delta_t_c=20.0, copper_weight_oz=1.0)

    assert w_1a > 0.2
    assert w_5a > w_1a
    assert w_10a > w_5a

    # 2 oz copper requires less width for same current than 1 oz copper
    w_5a_2oz = calculate_ipc2152_trace_width(current_a=5.0, delta_t_c=20.0, copper_weight_oz=2.0)
    assert w_5a_2oz < w_5a


def test_trace_ampacity_calculation():
    """Verifies reciprocal ampacity calculation."""
    amp_1mm = calculate_trace_ampacity(width_mm=1.0, delta_t_c=20.0, copper_weight_oz=1.0)
    amp_2mm = calculate_trace_ampacity(width_mm=2.0, delta_t_c=20.0, copper_weight_oz=1.0)

    assert amp_1mm > 0.5
    assert amp_2mm > amp_1mm


def test_power_netclasses_generation():
    """Verifies generation of netclasses with dynamic high-current net definitions."""
    net_currents = {"/Vin": 8.0, "/Vdiv": 0.5}
    nc = calculate_power_netclasses(
        net_currents=net_currents,
        copper_weight_oz=1.0,
        delta_t_c=20.0,
        default_signal_track=0.35,
        default_power_track=1.2,
    )

    assert "Default" in nc
    assert nc["Default"]["track"] == 0.35
    assert "Power" in nc
    assert nc["Power"]["track"] == 1.2
    # Specific netclass created for high-current net > 1.0A
    assert "Power_Vin" in nc
    assert nc["Power_Vin"]["track"] > 1.2
    assert nc["Power_Vin"]["rated_current_a"] == 8.0


def test_power_routing_plan_with_available_nets():
    """Verifies that power routing plan filters strictly to routable nets on the board."""
    available = ["/Vin", "/Vdiv", "GND"]
    plan = generate_power_routing_plan(
        switching_nets=["*SW*"],
        power_nets=["*Vin*"],
        available_nets=available,
    )

    assert plan is not None
    assert "/Vin" in plan["order"]
    # *SW* matched no net, so it must not be in order or nets
    assert "*SW*" not in plan["order"]
    assert "*SW*" not in plan["nets"]
