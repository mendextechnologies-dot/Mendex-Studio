from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None


class LTspiceLogMetrics:
    def __init__(self, log_content: str):
        self.raw_log = log_content
        self.metrics: dict[str, float] = {}
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.operating_points: dict[str, float] = {}
        self._parse()

    def _parse(self):
        for line in self.raw_log.splitlines():
            line_str = line.strip()
            # Capture warnings and errors
            if "warning:" in line_str.lower():
                self.warnings.append(line_str)
            if "error:" in line_str.lower() or "fatal error:" in line_str.lower() or "singular matrix" in line_str.lower():
                self.errors.append(line_str)

            # Operating point variable values, e.g. V(n001): 12.0
            op_match = re.match(r"^([a-zA-Z0-9_\(\)]+):\s+([\-\+]?\d+(?:\.\d+)?(?:[eE][\-\+]?\d+)?)\s+voltage$", line_str, re.IGNORECASE)
            if op_match:
                name, val = op_match.groups()
                try:
                    self.operating_points[name] = float(val)
                except ValueError:
                    pass

            # Total elapsed time
            time_match = re.search(r"Total elapsed time:\s+([\d\.]+)\s+seconds", line_str, re.IGNORECASE)
            if time_match:
                self.metrics["elapsed_time_s"] = float(time_match.group(1))

            # Thread count
            thread_match = re.search(r"Maximum thread count:\s+(\d+)", line_str, re.IGNORECASE)
            if thread_match:
                self.metrics["thread_count"] = float(thread_match.group(1))

        self.metrics["warning_count"] = float(len(self.warnings))
        self.metrics["error_count"] = float(len(self.errors))


def parse_ltspice_log(log_path: Path) -> LTspiceLogMetrics:
    """Reads and parses an LTspice ASCII log file."""
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return LTspiceLogMetrics(text)


def parse_ascii_raw_header(raw_path: Path) -> dict[str, str | int]:
    """Parses header of ASCII LTspice .raw file to get variable count and points."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_path}")

    info: dict[str, str | int] = {}
    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_s = line.strip()
            if line_s.startswith("Variables:"):
                break
            if ":" in line_s:
                k, v = line_s.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k in ("no. variables", "no. points"):
                    try:
                        info[k] = int(v)
                    except ValueError:
                        info[k] = v
                else:
                    info[k] = v
    return info


def parse_ascii_raw_waveforms(raw_path: Path) -> dict[str, Any]:
    """Vectorized parser for ASCII LTspice .raw files returning dict of NumPy arrays."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_path}")
    if np is None:
        raise ImportError("NumPy is required for vectorized raw waveform parsing")

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    vars_start = False
    vals_start = False
    var_names: list[str] = []
    data_lines: list[str] = []

    for line in lines:
        s = line.strip()
        if s.startswith("Variables:"):
            vars_start = True
            continue
        if s.startswith("Values:"):
            vars_start = False
            vals_start = True
            continue
        if vars_start:
            parts = s.split()
            if len(parts) >= 2:
                var_names.append(parts[1])
        elif vals_start:
            data_lines.append(s)

    if not var_names or not data_lines:
        return {}

    n_vars = len(var_names)
    all_floats: list[float] = []
    for l in data_lines:
        parts = l.split()
        if len(parts) == 2:
            all_floats.append(float(parts[1]))
        elif len(parts) == 1:
            all_floats.append(float(parts[0]))

    arr = np.array(all_floats, dtype=np.float64).reshape(-1, n_vars)
    return {name: arr[:, i] for i, name in enumerate(var_names)}


def calculate_waveform_metrics(waveforms: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Calculates RMS, Peak-to-Peak, Mean, Min, and Max metrics for all waveform channels."""
    if np is None:
        raise ImportError("NumPy is required for waveform metrics calculation")

    metrics: dict[str, dict[str, float]] = {}
    for name, signal in waveforms.items():
        if name.lower() == "time":
            continue
        if isinstance(signal, np.ndarray) and len(signal) > 0:
            metrics[name] = {
                "rms": float(np.sqrt(np.mean(signal**2))),
                "p2p": float(np.ptp(signal)),
                "mean": float(np.mean(signal)),
                "min": float(np.min(signal)),
                "max": float(np.max(signal)),
            }
    return metrics
