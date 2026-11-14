"""Oscilloscope CSV Waveform Parser & Signal Processing Module.

Supports instrument CSV exports from Tektronix, Keysight/Agilent, Rigol, Siglent,
and generic multi-column scientific CSV formats.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class ScopeParsingError(Exception):
    """Raised when an oscilloscope CSV capture cannot be parsed or validated."""
    pass


def compute_sha256(content: Union[bytes, str]) -> str:
    """Computes cryptographic SHA-256 digest of raw file content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def detect_scope_vendor(header_lines: List[str]) -> str:
    """Infers instrument manufacturer from CSV metadata preambles."""
    combined = " ".join(header_lines).lower()
    if any(k in combined for k in ("tektronix", "tds", "dpo", "mso", "sample interval", "trigger point")):
        return "Tektronix"
    if any(k in combined for k in ("keysight", "agilent", "infinii", "dsox", "msox", "x-axis")):
        return "Keysight"
    if any(k in combined for k in ("rigol", "ds1000", "mso5000", "ds1054z", "sample rate")):
        return "Rigol"
    if any(k in combined for k in ("siglent", "sds", "sds1000")):
        return "Siglent"
    if any(k in combined for k in ("rohde", "r&s", "rtb", "rte")):
        return "Rohde & Schwarz"
    return "Generic"


def clean_channel_name(raw_name: str, index: int) -> str:
    """Normalizes raw column header to clean identifiable channel token."""
    s = raw_name.strip().strip('"').strip("'")
    if not s:
        return f"CH{index}"
    # Remove unit suffixes like (V), [V], (s), [A]
    s_clean = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s).strip()
    # Normalize common channel patterns
    lower = s_clean.lower()
    if lower in ("time", "t", "second", "seconds", "sec", "x-axis", "x"):
        return "time"
    if re.match(r"^ch\d+$", lower):
        return s_clean.upper()
    if re.match(r"^channel\s*\d+$", lower):
        num = re.search(r"\d+", lower).group()
        return f"CH{num}"
    return s_clean or f"CH{index}"


def parse_scope_csv(content: Union[str, bytes]) -> Dict[str, Any]:
    """Parses raw oscilloscope CSV content into structured numerical arrays.

    Returns dict with:
        vendor: str
        time: np.ndarray (float64)
        channels: Dict[str, np.ndarray] (float64)
        sample_rate_hz: float
        duration_s: float
        total_points: int
        metadata: Dict[str, str]
    """
    if isinstance(content, bytes):
        raw_bytes = content
        text = content.decode("utf-8", errors="replace")
    else:
        raw_bytes = content.encode("utf-8")
        text = content

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ScopeParsingError("Oscilloscope CSV file is empty.")

    metadata: Dict[str, str] = {}
    preamble_lines: List[str] = []
    data_start_idx = -1
    col_headers: List[str] = []

    # Detect delimiter
    first_few = lines[:min(10, len(lines))]
    sample_text = "\n".join(first_few)
    dialect = None
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",\t;")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    # Scan for start of numerical data table
    for idx, line in enumerate(lines):
        # Ignore comments
        if line.startswith("#") or line.startswith(";"):
            preamble_lines.append(line.lstrip("#;").strip())
            continue

        parts = [p.strip() for p in line.split(delimiter)]
        if len(parts) < 2:
            preamble_lines.append(line)
            continue

        # Check if row looks like key-value metadata
        if len(parts) == 2 and not _can_be_floats(parts):
            metadata[parts[0]] = parts[1]
            preamble_lines.append(line)
            continue

        # Check if row is purely numerical (headerless CSV)
        if _can_be_floats(parts):
            data_start_idx = idx
            col_headers = [f"col_{i}" for i in range(len(parts))]
            col_headers[0] = "time"
            break

        # Check if row has column headers (e.g. TIME, CH1, CH2)
        # Check if the NEXT row is numerical
        if idx + 1 < len(lines):
            next_parts = [p.strip() for p in lines[idx + 1].split(delimiter)]
            if _can_be_floats(next_parts) and len(next_parts) == len(parts):
                data_start_idx = idx + 1
                col_headers = parts
                break

        preamble_lines.append(line)

    if data_start_idx == -1 or not col_headers:
        raise ScopeParsingError("Could not locate numerical waveform data in CSV.")

    vendor = detect_scope_vendor(preamble_lines)

    # Normalize column names
    clean_cols: List[str] = []
    time_col_idx = 0
    for i, col in enumerate(col_headers):
        norm = clean_channel_name(col, i)
        if norm.lower() == "time":
            time_col_idx = i
            clean_cols.append("time")
        else:
            clean_cols.append(norm)

    # Parse numerical rows
    raw_rows: List[List[float]] = []
    for line in lines[data_start_idx:]:
        parts = [p.strip() for p in line.split(delimiter)]
        if len(parts) < len(col_headers):
            continue
        try:
            float_vals = [float(parts[i]) for i in range(len(col_headers))]
            raw_rows.append(float_vals)
        except ValueError:
            # Skip sporadic malformed rows or end-of-file trailer notes
            continue

    if not raw_rows:
        raise ScopeParsingError("No valid numerical waveform rows parsed from CSV.")

    data_matrix = np.array(raw_rows, dtype=np.float64)
    total_points = len(data_matrix)

    # Extract time vector
    time_arr = data_matrix[:, time_col_idx]

    # Verify time monotonicity or attempt synthesis if constant/invalid
    dt_arr = np.diff(time_arr)
    valid_dt = dt_arr[dt_arr > 0]
    if len(valid_dt) > 0:
        avg_dt = float(np.median(valid_dt))
    else:
        # Check metadata for sample interval
        sample_interval = None
        for k, v in metadata.items():
            if "interval" in k.lower() or "sample" in k.lower():
                try:
                    sample_interval = float(v)
                    break
                except ValueError:
                    pass
        avg_dt = sample_interval or 1e-6
        time_arr = np.arange(total_points, dtype=np.float64) * avg_dt

    sample_rate_hz = 1.0 / avg_dt if avg_dt > 0 else 0.0
    duration_s = float(time_arr[-1] - time_arr[0]) if total_points > 1 else 0.0

    # Build channel vectors
    channels: Dict[str, np.ndarray] = {}
    for i, col_name in enumerate(clean_cols):
        if i == time_col_idx or col_name == "time":
            continue
        channels[col_name] = data_matrix[:, i]

    return {
        "vendor": vendor,
        "time": time_arr,
        "channels": channels,
        "sample_rate_hz": round(sample_rate_hz, 2),
        "duration_s": round(duration_s, 9),
        "total_points": total_points,
        "metadata": metadata,
        "sha256": compute_sha256(raw_bytes),
    }


def _can_be_floats(items: List[str]) -> bool:
    """Returns True if at least the first 2 items parse as floats."""
    if len(items) < 2:
        return False
    try:
        float(items[0])
        float(items[1])
        return True
    except ValueError:
        return False


def decimate_waveform(
    time_arr: np.ndarray,
    channels: Dict[str, np.ndarray],
    target_points: int = 1500,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """Decimates dense waveform arrays using min-max envelope preservation.

    Preserves extreme spikes, ringing peaks, and high-frequency excursions.
    """
    n_points = len(time_arr)
    if n_points <= target_points:
        return time_arr, channels

    bucket_size = int(math.ceil(n_points / (target_points / 2)))
    if bucket_size < 2:
        return time_arr, channels

    selected_indices: List[int] = [0]

    # Use first channel as primary envelope driver
    prim_key = next(iter(channels.keys())) if channels else None
    prim_data = channels[prim_key] if prim_key is not None else None

    for b_start in range(0, n_points, bucket_size):
        b_end = min(b_start + bucket_size, n_points)
        if b_end <= b_start:
            continue
        if prim_data is not None:
            sub = prim_data[b_start:b_end]
            idx_min = b_start + int(np.argmin(sub))
            idx_max = b_start + int(np.argmax(sub))
            for idx in sorted([idx_min, idx_max]):
                if idx not in selected_indices:
                    selected_indices.append(idx)
        else:
            selected_indices.append(b_start)

    if (n_points - 1) not in selected_indices:
        selected_indices.append(n_points - 1)

    selected_indices = sorted(set(selected_indices))
    idx_arr = np.array(selected_indices, dtype=np.int64)

    dec_time = time_arr[idx_arr]
    dec_channels: Dict[str, np.ndarray] = {
        k: v[idx_arr] for k, v in channels.items()
    }
    return dec_time, dec_channels


def calculate_channel_metrics(
    time_arr: np.ndarray,
    signal_arr: np.ndarray,
    steady_state_ratio: float = 0.35,
) -> Dict[str, float]:
    """Calculates comprehensive electrical signal metrics for a measured channel."""
    if len(signal_arr) == 0:
        return {}

    n = len(signal_arr)
    # Steady state window: last steady_state_ratio of time
    ss_start_idx = int(n * (1.0 - steady_state_ratio))
    ss_signal = signal_arr[ss_start_idx:]
    ss_time = time_arr[ss_start_idx:]

    mean_val = float(np.mean(ss_signal))
    rms_val = float(np.sqrt(np.mean(ss_signal ** 2)))
    min_val = float(np.min(ss_signal))
    max_val = float(np.max(ss_signal))
    pk_pk = float(max_val - min_val)

    # Estimate frequency via zero-crossings around the mean
    ac_signal = ss_signal - mean_val
    zero_crossings = np.where(np.diff(np.signbit(ac_signal)))[0]
    est_freq_hz = 0.0
    if len(zero_crossings) >= 4 and len(ss_time) > 1:
        # Time duration between first and last crossing
        t_span = ss_time[zero_crossings[-1]] - ss_time[zero_crossings[0]]
        cycles = (len(zero_crossings) - 1) / 2.0
        if t_span > 0 and cycles >= 1:
            est_freq_hz = float(cycles / t_span)

    # Rise time (10% to 90%) over entire record or first transient
    v_10 = min_val + 0.10 * pk_pk
    v_90 = min_val + 0.90 * pk_pk
    idx_10 = np.where(signal_arr >= v_10)[0]
    idx_90 = np.where(signal_arr >= v_90)[0]
    rise_time_s = 0.0
    if len(idx_10) > 0 and len(idx_90) > 0 and idx_90[0] > idx_10[0]:
        rise_time_s = float(time_arr[idx_90[0]] - time_arr[idx_10[0]])

    return {
        "mean": round(mean_val, 4),
        "rms": round(rms_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "pk_pk": round(pk_pk, 4),
        "est_freq_hz": round(est_freq_hz, 1),
        "rise_time_s": rise_time_s,
    }
