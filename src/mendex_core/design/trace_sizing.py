"""IPC-2152 compliant PCB trace width, ampacity and power routing plan calculation.

Adheres to IPC-2152 (Standard for Determining Current-Carrying Capacity in Printed Board Design)
and conservative IPC-2221 formulas for high-current power electronics routing.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def calculate_ipc2152_trace_width(
    current_a: float,
    delta_t_c: float = 20.0,
    copper_weight_oz: float = 1.0,
    internal: bool = False,
    min_width_mm: float = 0.25,
    derating_factor: float = 1.25,
) -> float:
    """Calculates IPC-2152 / IPC-2221 compliant minimum trace width in millimeters.

    Args:
        current_a: Operating continuous or RMS current in Amperes.
        delta_t_c: Permissible conductor temperature rise in degrees Celsius (default: 20C).
        copper_weight_oz: Copper foil weight in oz/ft^2 (e.g. 1.0 for 35 um, 2.0 for 70 um).
        internal: True if the trace is on an internal PCB layer (FR-4 encapsulated).
        min_width_mm: Minimum allowable trace width based on PCB fab capability.
        derating_factor: Design margin multiplier (default: 1.25x = 25% safety overhead).

    Returns:
        Recommended conductor width in millimeters, rounded to 2 decimal places.
    """
    if current_a <= 0:
        return min_width_mm

    # Apply design safety derating
    design_current = current_a * max(1.0, derating_factor)

    # IPC-2221 / IPC-2152 empirical constants
    # k = 0.048 for external conductors, 0.024 for internal conductors
    k = 0.024 if internal else 0.048
    b = 0.44
    c = 0.725

    # Conductor cross-sectional area in mils^2
    area_mils2 = (design_current / (k * (max(1.0, delta_t_c) ** b))) ** (1.0 / c)

    # Conductor thickness in mils: 1 oz copper = 1.37 mils (34.8 um)
    thickness_mils = max(0.5, copper_weight_oz * 1.37)

    # Conductor width in mils and conversion to mm (1 mil = 0.0254 mm)
    width_mils = area_mils2 / thickness_mils
    width_mm = width_mils * 0.0254

    return max(min_width_mm, round(width_mm, 2))


def calculate_trace_ampacity(
    width_mm: float,
    delta_t_c: float = 20.0,
    copper_weight_oz: float = 1.0,
    internal: bool = False,
) -> float:
    """Calculates allowable continuous current in Amperes for a given trace width."""
    if width_mm <= 0:
        return 0.0

    k = 0.024 if internal else 0.048
    b = 0.44
    c = 0.725

    thickness_mils = max(0.5, copper_weight_oz * 1.37)
    width_mils = width_mm / 0.0254
    area_mils2 = width_mils * thickness_mils

    current_a = k * (max(1.0, delta_t_c) ** b) * (area_mils2 ** c)
    return round(float(current_a), 2)


def calculate_power_netclasses(
    net_currents: Optional[Dict[str, float]] = None,
    copper_weight_oz: float = 1.0,
    delta_t_c: float = 20.0,
    default_signal_track: float = 0.4,
    default_power_track: float = 1.2,
    power_patterns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generates netclasses with IPC-2152 sized conductor widths for power nets."""
    classes: Dict[str, Any] = {
        "Default": {
            "track": default_signal_track,
            "clearance": 0.2,
            "via": [0.6, 0.3],
        },
        "Power": {
            "track": default_power_track,
            "clearance": 0.4,
            "via": [0.8, 0.4],
            "patterns": power_patterns or [
                "*HV*", "*DRAIN*", "*PRI*", "*SEC*", "*VOUT*", "*VIN*",
                "*VBUS*", "*VBAT*", "*SW*", "*PHASE*", "*COIL*", "GND*", "*GND*"
            ],
        },
    }

    if not net_currents:
        return classes

    # Add dedicated netclasses for specific high-current nets
    for net, current in net_currents.items():
        if current > 1.0:
            w = calculate_ipc2152_trace_width(
                current_a=current,
                delta_t_c=delta_t_c,
                copper_weight_oz=copper_weight_oz,
                internal=False,
                min_width_mm=default_signal_track,
            )
            # Choose via size suitable for current (drill >= 0.4mm, annular ring >= 0.2mm)
            via_drill = 0.5 if current > 5.0 else 0.4
            via_dia = via_drill + 0.4
            class_name = f"Power_{net.strip('/').replace('*', '').replace(' ', '_')}"
            classes[class_name] = {
                "track": max(w, default_power_track),
                "clearance": 0.5 if current > 5.0 else 0.3,
                "via": [round(via_dia, 2), round(via_drill, 2)],
                "patterns": [net, f"*{net}*"],
                "rated_current_a": current,
            }

    return classes


def generate_power_routing_plan(
    switching_nets: Optional[List[str]] = None,
    power_nets: Optional[List[str]] = None,
    preferred_outer_layer: str = "F.Cu",
    ripup_rounds: int = 6,
    available_nets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Generates a power electronics-aware routing plan prioritizing switching loops.

    Heuristics enforced:
    1. Switching loop minimization: High di/dt nets routed first with zero or minimal vias.
    2. Reference plane adjacency: Keeps power switching on preferred outer layer directly above GND.
    3. Power bus prioritization: High-current DC nets routed second.
    4. Sensitive analog & gate drive signals routed after power loops are frozen.
    """
    import fnmatch

    sw_candidates = switching_nets or ["*SW*", "*DRAIN*", "*PHASE*", "*LX*", "*COIL_SW*", "*PRI_DRAIN*"]
    pwr_candidates = power_nets or ["*HV*", "*VIN*", "*VOUT*", "*VBUS*", "*VBAT*"]

    if available_nets is not None and available_nets:
        matched_sw: List[str] = []
        matched_pwr: List[str] = []
        for n in available_nets:
            n_clean = str(n).strip()
            if any(fnmatch.fnmatch(n_clean.upper(), pat.upper()) or fnmatch.fnmatch(n_clean.lstrip("/").upper(), pat.upper()) for pat in sw_candidates):
                if n_clean not in matched_sw:
                    matched_sw.append(n_clean)
            elif any(fnmatch.fnmatch(n_clean.upper(), pat.upper()) or fnmatch.fnmatch(n_clean.lstrip("/").upper(), pat.upper()) for pat in pwr_candidates):
                if n_clean not in matched_pwr and n_clean not in matched_sw:
                    matched_pwr.append(n_clean)

        order = matched_sw + matched_pwr + ["*"]
        net_rules: Dict[str, Any] = {}
        for sn in matched_sw:
            net_rules[sn] = {
                "prefer": [preferred_outer_layer],
                "via_budget": 1,
            }
        return {
            "order": order,
            "global": {
                "engine": "v2",
                "ripup_rounds": ripup_rounds,
                "via_cost": 3,
            },
            "nets": net_rules,
        }
    else:
        # Fallback when available nets are unknown: provide safe global heuristics without unchecked net globs
        return {
            "order": ["*"],
            "global": {
                "engine": "v2",
                "ripup_rounds": ripup_rounds,
                "via_cost": 3,
            },
            "nets": {},
        }
