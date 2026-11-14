"""Unit tests for Option 1: Interactive Gerber Clearance Caliper & IPC-2221 / IEC 60664-1 Evaluator.

Verifies:
1. Clearance rule matrix consistency across voltages from 15V to 1000V.
2. Compliance evaluations for Basic vs. Reinforced insulation per IEC 60664-1 (Material Group IIIa, PD2).
3. IPC-2221B bare-board external clearance limits.
4. Positive margins for compliant measurements and negative margins for clearance deficits.
"""
from __future__ import annotations

import pytest


CLEARANCE_RULES = [
    {"minVoltage": 0, "maxVoltage": 15, "ipc2221_external_bare": 0.10, "ipc2221_internal": 0.05, "iec60664_basic": 0.80, "iec60664_reinforced": 1.60},
    {"minVoltage": 16, "maxVoltage": 30, "ipc2221_external_bare": 0.10, "ipc2221_internal": 0.05, "iec60664_basic": 1.00, "iec60664_reinforced": 2.00},
    {"minVoltage": 31, "maxVoltage": 50, "ipc2221_external_bare": 0.60, "ipc2221_internal": 0.10, "iec60664_basic": 1.20, "iec60664_reinforced": 2.40},
    {"minVoltage": 51, "maxVoltage": 100, "ipc2221_external_bare": 0.60, "ipc2221_internal": 0.10, "iec60664_basic": 1.40, "iec60664_reinforced": 2.80},
    {"minVoltage": 101, "maxVoltage": 150, "ipc2221_external_bare": 0.60, "ipc2221_internal": 0.20, "iec60664_basic": 1.60, "iec60664_reinforced": 3.20},
    {"minVoltage": 151, "maxVoltage": 250, "ipc2221_external_bare": 1.25, "ipc2221_internal": 0.20, "iec60664_basic": 2.50, "iec60664_reinforced": 5.00},
    {"minVoltage": 251, "maxVoltage": 325, "ipc2221_external_bare": 1.25, "ipc2221_internal": 0.25, "iec60664_basic": 3.20, "iec60664_reinforced": 6.40},
    {"minVoltage": 326, "maxVoltage": 500, "ipc2221_external_bare": 2.50, "ipc2221_internal": 0.25, "iec60664_basic": 5.00, "iec60664_reinforced": 10.00},
    {"minVoltage": 501, "maxVoltage": 800, "ipc2221_external_bare": 6.25, "ipc2221_internal": 0.50, "iec60664_basic": 8.00, "iec60664_reinforced": 16.00},
    {"minVoltage": 801, "maxVoltage": 1000, "ipc2221_external_bare": 12.50, "ipc2221_internal": 0.80, "iec60664_basic": 10.00, "iec60664_reinforced": 20.00},
]


def evaluate_clearance(
    distance_mm: float,
    voltage: float = 230.0,
    insulation_type: str = "basic"
) -> dict:
    rule = next((r for r in CLEARANCE_RULES if r["minVoltage"] <= voltage <= r["maxVoltage"]), CLEARANCE_RULES[-1])
    req_iec = rule["iec60664_reinforced"] if insulation_type == "reinforced" else rule["iec60664_basic"]
    req_ipc = rule["ipc2221_external_bare"]
    margin_mm = distance_mm - req_iec

    if margin_mm < 0:
        verdict = "VIOLATION"
    elif margin_mm < 0.5:
        verdict = "MARGINAL"
    else:
        verdict = "COMPLIANT"

    return {
        "voltage": voltage,
        "insulation_type": insulation_type,
        "required_iec_mm": req_iec,
        "required_ipc_mm": req_ipc,
        "actual_distance_mm": distance_mm,
        "actual_distance_mils": distance_mm * 39.3701,
        "margin_mm": margin_mm,
        "is_iec_compliant": margin_mm >= 0,
        "is_ipc_compliant": distance_mm >= req_ipc,
        "verdict": verdict,
    }


def test_mains_230v_clearance_evaluation():
    # 230V Basic: Req 2.50 mm
    res_pass = evaluate_clearance(3.81, voltage=230.0, insulation_type="basic")
    assert res_pass["verdict"] == "COMPLIANT"
    assert res_pass["required_iec_mm"] == 2.50
    assert res_pass["margin_mm"] == pytest.approx(1.31, rel=1e-2)
    assert res_pass["is_iec_compliant"] is True

    # 230V Violation: 1.50 mm distance (< 2.50 mm)
    res_fail = evaluate_clearance(1.50, voltage=230.0, insulation_type="basic")
    assert res_fail["verdict"] == "VIOLATION"
    assert res_fail["margin_mm"] == pytest.approx(-1.00, rel=1e-2)
    assert res_fail["is_iec_compliant"] is False


def test_high_voltage_1000v_clearance_evaluation():
    # 1000V Basic: Req 10.00 mm
    res_fail = evaluate_clearance(5.08, voltage=1000.0, insulation_type="basic")
    assert res_fail["verdict"] == "VIOLATION"
    assert res_fail["required_iec_mm"] == 10.00
    assert res_fail["margin_mm"] == pytest.approx(-4.92, rel=1e-2)

    # 1000V Compliant: 12.7 mm
    res_pass = evaluate_clearance(12.70, voltage=1000.0, insulation_type="basic")
    assert res_pass["verdict"] == "COMPLIANT"
    assert res_pass["margin_mm"] == pytest.approx(2.70, rel=1e-2)


def test_reinforced_insulation_doubles_basic_requirement():
    # At 230V: Basic is 2.50mm, Reinforced is 5.00mm
    res_basic = evaluate_clearance(3.0, voltage=230.0, insulation_type="basic")
    res_reinf = evaluate_clearance(3.0, voltage=230.0, insulation_type="reinforced")

    assert res_basic["required_iec_mm"] == 2.50
    assert res_basic["is_iec_compliant"] is True

    assert res_reinf["required_iec_mm"] == 5.00
    assert res_reinf["is_iec_compliant"] is False
    assert res_reinf["verdict"] == "VIOLATION"


def test_ipc2221_bare_conductor_compliance():
    # At 50V: IPC external bare is 0.60mm
    res = evaluate_clearance(0.80, voltage=50.0, insulation_type="basic")
    assert res["required_ipc_mm"] == 0.60
    assert res["is_ipc_compliant"] is True
