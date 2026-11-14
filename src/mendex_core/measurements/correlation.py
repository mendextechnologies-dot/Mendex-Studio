"""Real-vs-Simulated Waveform Correlation & Validation Engine.

Correlates physical oscilloscope CSV measurements against LTspice / ngspice
simulation vectors, computing DC error, AC ripple deviation, peak switch stress,
frequency alignment, and statistical Pearson R^2 waveform fidelity.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def correlate_channels(
    sim_time: np.ndarray,
    sim_signal: np.ndarray,
    meas_time: np.ndarray,
    meas_signal: np.ndarray,
    channel_name: str,
    target_tolerance_pct: float = 5.0,
    steady_state_ratio: float = 0.40,
) -> Dict[str, Any]:
    """Correlates a single measured oscilloscope channel against a simulated trace.

    Calculates:
        - DC steady-state mean error and relative percentage
        - Peak-to-peak AC ripple comparison
        - Peak maximum voltage / switch stress comparison
        - Approximate switching frequency correlation
        - Pearson correlation coefficient (r and R^2) over aligned steady-state window
    """
    if len(sim_signal) < 2 or len(meas_signal) < 2:
        return {
            "channel": channel_name,
            "status": "UNAVAILABLE",
            "reason": "Insufficient waveform points for correlation",
        }

    # 1. Steady-state analysis of simulated signal
    n_sim = len(sim_time)
    ss_sim_start = int(n_sim * (1.0 - steady_state_ratio))
    sim_ss_time = sim_time[ss_sim_start:]
    sim_ss_sig = sim_signal[ss_sim_start:]

    sim_dc = float(np.mean(sim_ss_sig))
    sim_pk_pk = float(np.max(sim_ss_sig) - np.min(sim_ss_sig))
    sim_max = float(np.max(sim_ss_sig))
    sim_min = float(np.min(sim_ss_sig))

    # 2. Steady-state analysis of measured signal
    n_meas = len(meas_time)
    ss_meas_start = int(n_meas * (1.0 - steady_state_ratio))
    meas_ss_time = meas_time[ss_meas_start:]
    meas_ss_sig = meas_signal[ss_meas_start:]

    meas_dc = float(np.mean(meas_ss_sig))
    meas_pk_pk = float(np.max(meas_ss_sig) - np.min(meas_ss_sig))
    meas_max = float(np.max(meas_ss_sig))
    meas_min = float(np.min(meas_ss_sig))

    # 3. DC Metrics
    dc_delta_abs = float(abs(meas_dc - sim_dc))
    sim_denom = abs(sim_dc) if abs(sim_dc) > 1e-6 else 1.0
    dc_error_pct = float((dc_delta_abs / sim_denom) * 100.0)

    # 4. Ripple & Peak Metrics
    ripple_delta_abs = float(abs(meas_pk_pk - sim_pk_pk))
    peak_delta_abs = float(abs(meas_max - sim_max))

    # 5. Switching Frequency Estimation
    sim_freq = _estimate_frequency(sim_ss_time, sim_ss_sig, sim_dc)
    meas_freq = _estimate_frequency(meas_ss_time, meas_ss_sig, meas_dc)
    freq_delta_hz = float(abs(meas_freq - sim_freq)) if sim_freq > 0 and meas_freq > 0 else None

    # 6. Pearson R^2 correlation across overlapping normalized time
    # Time-align by shifting measured time to align with simulation steady-state span
    r_squared, pearson_r = _calculate_r_squared(
        sim_ss_time, sim_ss_sig, meas_ss_time, meas_ss_sig
    )

    # 7. Evaluate Pass/Fail/Warning Grade
    if dc_error_pct <= target_tolerance_pct and r_squared >= 0.75:
        grade = "CORRELATED_PASS"
        grade_desc = f"Measured within {target_tolerance_pct:.1f}% tolerance (R² = {r_squared:.3f})"
    elif dc_error_pct <= target_tolerance_pct * 1.5 and r_squared >= 0.60:
        grade = "WARNING_DEVIATION"
        grade_desc = f"Marginal deviation: {dc_error_pct:.2f}% DC error, R² = {r_squared:.3f}"
    else:
        grade = "EXCEEDED_TOLERANCE"
        grade_desc = f"Exceeded allowable tolerance: {dc_error_pct:.2f}% DC error (R² = {r_squared:.3f})"

    return {
        "channel": channel_name,
        "status": grade,
        "status_description": grade_desc,
        "dc_simulated": round(sim_dc, 4),
        "dc_measured": round(meas_dc, 4),
        "dc_delta_abs": round(dc_delta_abs, 4),
        "dc_error_percent": round(dc_error_pct, 2),
        "ripple_simulated_pk_pk": round(sim_pk_pk, 4),
        "ripple_measured_pk_pk": round(meas_pk_pk, 4),
        "ripple_delta_abs": round(ripple_delta_abs, 4),
        "peak_simulated": round(sim_max, 4),
        "peak_measured": round(meas_max, 4),
        "peak_delta_abs": round(peak_delta_abs, 4),
        "frequency_simulated_hz": round(sim_freq, 1) if sim_freq > 0 else None,
        "frequency_measured_hz": round(meas_freq, 1) if meas_freq > 0 else None,
        "frequency_delta_hz": round(freq_delta_hz, 1) if freq_delta_hz is not None else None,
        "pearson_r": round(pearson_r, 4),
        "r_squared": round(r_squared, 4),
    }


def _estimate_frequency(time_arr: np.ndarray, signal_arr: np.ndarray, mean_val: float) -> float:
    """Estimates fundamental switching frequency via zero crossings."""
    if len(time_arr) < 4:
        return 0.0
    ac = signal_arr - mean_val
    crossings = np.where(np.diff(np.signbit(ac)))[0]
    if len(crossings) >= 4:
        t_span = time_arr[crossings[-1]] - time_arr[crossings[0]]
        cycles = (len(crossings) - 1) / 2.0
        if t_span > 0 and cycles >= 1:
            return float(cycles / t_span)
    return 0.0


def _calculate_r_squared(
    sim_t: np.ndarray,
    sim_v: np.ndarray,
    meas_t: np.ndarray,
    meas_v: np.ndarray,
) -> Tuple[float, float]:
    """Calculates Pearson r and R^2 by interpolating measured signal onto normalized simulation grid."""
    try:
        # Normalize time grids to [0, 1]
        sim_t_norm = (sim_t - sim_t[0]) / max(sim_t[-1] - sim_t[0], 1e-12)
        meas_t_norm = (meas_t - meas_t[0]) / max(meas_t[-1] - meas_t[0], 1e-12)

        # Interpolate measured signal onto simulation normalized grid
        meas_interp = np.interp(sim_t_norm, meas_t_norm, meas_v)

        # Compute Pearson correlation
        sim_diff = sim_v - np.mean(sim_v)
        meas_diff = meas_interp - np.mean(meas_interp)

        denom = np.sqrt(np.sum(sim_diff ** 2) * np.sum(meas_diff ** 2))
        if denom < 1e-12:
            # Constant or zero-variance signals: if means match closely, return 1.0, else 0.0
            mean_match = 1.0 - min(abs(np.mean(sim_v) - np.mean(meas_v)) / max(abs(np.mean(sim_v)), 1e-6), 1.0)
            return float(mean_match), float(mean_match)

        r = float(np.sum(sim_diff * meas_diff) / denom)
        r_sq = max(0.0, min(1.0, r ** 2))
        return r_sq, r
    except Exception:
        return 0.0, 0.0


def correlate_scope_with_simulation(
    sim_waveforms: Dict[str, Any],
    meas_data: Dict[str, Any],
    channel_mapping: Dict[str, str],
    target_tolerance_pct: float = 5.0,
) -> Dict[str, Any]:
    """Correlates complete physical scope capture against parsed simulation raw waveforms.

    Args:
        sim_waveforms: dict containing 'time' and trace arrays from ltspice_parser.
        meas_data: dict containing 'time' and 'channels' from scope_parser.
        channel_mapping: dict mapping scope channel -> sim trace, e.g. {"CH1": "V(vout)"}.
        target_tolerance_pct: allowable percentage error threshold.

    Returns:
        Structured correlation scorecard with per-channel metrics and overall grade.
    """
    sim_time = sim_waveforms.get("time") if "time" in sim_waveforms else sim_waveforms.get("Time")
    meas_time = meas_data.get("time")
    meas_channels = meas_data.get("channels", {})

    if sim_time is None or meas_time is None:
        return {
            "status": "UNAVAILABLE",
            "reason": "Missing simulation or measurement time vectors",
            "channels": [],
        }

    results: List[Dict[str, Any]] = []
    has_warning = False
    has_failed = False

    for scope_ch, sim_trace in channel_mapping.items():
        if scope_ch not in meas_channels:
            continue
        if sim_trace not in sim_waveforms:
            continue

        meas_sig = np.asarray(meas_channels[scope_ch], dtype=np.float64)
        sim_sig = np.asarray(sim_waveforms[sim_trace], dtype=np.float64)

        channel_res = correlate_channels(
            sim_time=np.asarray(sim_time, dtype=np.float64),
            sim_signal=sim_sig,
            meas_time=np.asarray(meas_time, dtype=np.float64),
            meas_signal=meas_sig,
            channel_name=f"{scope_ch} -> {sim_trace}",
            target_tolerance_pct=target_tolerance_pct,
        )
        channel_res["scope_channel"] = scope_ch
        channel_res["sim_trace"] = sim_trace
        results.append(channel_res)

        if channel_res["status"] == "EXCEEDED_TOLERANCE":
            has_failed = True
        elif channel_res["status"] == "WARNING_DEVIATION":
            has_warning = True

    overall_status = "CORRELATED_PASS"
    if has_failed:
        overall_status = "EXCEEDED_TOLERANCE"
    elif has_warning:
        overall_status = "WARNING_DEVIATION"
    elif not results:
        overall_status = "NOT_EVALUATED"

    # Compute overall average R^2 and DC error
    avg_r2 = float(np.mean([r["r_squared"] for r in results])) if results else 0.0
    avg_dc_err = float(np.mean([r["dc_error_percent"] for r in results])) if results else 0.0

    return {
        "status": overall_status,
        "channels_evaluated": len(results),
        "average_r_squared": round(avg_r2, 4),
        "average_dc_error_percent": round(avg_dc_err, 2),
        "channel_correlations": results,
        "measurement_sha256": meas_data.get("sha256"),
        "vendor": meas_data.get("vendor", "Generic"),
        "total_measured_points": meas_data.get("total_points", len(meas_time)),
        "sampling_rate_hz": meas_data.get("sample_rate_hz", 0.0),
    }
