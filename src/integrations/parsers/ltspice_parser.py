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
        self.measurements: dict[str, float] = {}
        self._parse()

    def _parse(self):
        for line in self.raw_log.splitlines():
            line_str = line.strip()
            # Capture warnings and errors
            if "warning:" in line_str.lower():
                self.warnings.append(line_str)
                continue
            err_keywords = (
                "error", "fatal", "singular", "can't find", "cannot find",
                "not defined", "unknown subckt", "unknown", "syntax",
                "time step too small", "timestep too small", "convergence failed",
                "is floating"
            )
            if any(k in line_str.lower() for k in err_keywords):
                self.errors.append(line_str)

            # Operating point variable values, e.g. V(n001): 12.0
            op_match = re.match(r"^([a-zA-Z0-9_\(\)]+):\s+([\-\+]?\d+(?:\.\d+)?(?:[eE][\-\+]?\d+)?)\s+voltage$", line_str, re.IGNORECASE)
            if op_match:
                name, val = op_match.groups()
                try:
                    self.operating_points[name] = float(val)
                except ValueError:
                    pass

            # .meas results: e.g. "vout_avg: AVG(v(vout))=11.7102 FROM 0.001 TO 0.002"
            # or "vout_ripple: vout_max-vout_min=0.1141 FROM 0.001 TO 0.002"
            # or "rc_meas: v(vout)=6.3212 at 0.001"
            meas_match = re.match(r"^([a-zA-Z0-9_]+):\s+(?:[^\n=]+=)?([\-\+]?\d+(?:\.\d+)?(?:[eE][\-\+]?\d+)?)(?:\s+from|\s+at|\s*$)", line_str, re.IGNORECASE)
            if meas_match:
                m_name, m_val = meas_match.groups()
                try:
                    f_val = float(m_val)
                    self.measurements[m_name] = f_val
                    self.metrics[m_name] = f_val
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
    """Unified parser for ASCII and Binary LTspice .raw files returning dict of NumPy arrays."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_path}")
    if np is None:
        raise ImportError("NumPy is required for vectorized raw waveform parsing")

    raw_bytes = raw_path.read_bytes()
    if not raw_bytes:
        return {}

    is_utf16 = raw_bytes[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(raw_bytes) > 2 and raw_bytes[1:2] == b"\x00")

    bin_marker = b"B\x00i\x00n\x00a\x00r\x00y\x00:\x00" if is_utf16 else b"Binary:"
    val_marker = b"V\x00a\x00l\x00u\x00e\x00s\x00:\x00" if is_utf16 else b"Values:"

    bin_idx = raw_bytes.find(bin_marker)
    val_idx = raw_bytes.find(val_marker)

    if bin_idx != -1:
        # Binary format
        header_text = raw_bytes[:bin_idx].decode("utf-16" if is_utf16 else "utf-8", errors="replace")
        data_start = bin_idx + len(bin_marker)
        if is_utf16:
            while data_start + 2 <= len(raw_bytes) and raw_bytes[data_start:data_start+2] in (b"\r\x00", b"\n\x00"):
                data_start += 2
        else:
            while data_start < len(raw_bytes) and raw_bytes[data_start:data_start+1] in (b"\r", b"\n"):
                data_start += 1

        var_names: list[str] = []
        num_points = 0
        in_vars = False
        for line in header_text.splitlines():
            line_s = line.strip()
            if line_s.startswith("No. Points:"):
                try:
                    num_points = int(line_s.split(":", 1)[1].strip())
                except ValueError:
                    num_points = 0
            elif line_s.startswith("Variables:"):
                in_vars = True
                continue
            elif in_vars:
                parts = line_s.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    var_names.append(parts[1])

        if not var_names or num_points == 0:
            return {}

        n_vars = len(var_names)
        point_bytes = 8 + (n_vars - 1) * 4
        total_data_bytes = num_points * point_bytes
        if data_start + total_data_bytes > len(raw_bytes):
            available_points = (len(raw_bytes) - data_start) // point_bytes
            num_points = max(0, available_points)

        if num_points == 0:
            return {}

        dt = np.dtype([("time", "<f8")] + [(name, "<f4") for name in var_names[1:]])
        arr = np.frombuffer(raw_bytes[data_start:data_start + num_points * point_bytes], dtype=dt, count=num_points)
        result: dict[str, Any] = {"time": np.array(arr["time"], dtype=np.float64)}
        for name in var_names[1:]:
            result[name] = np.array(arr[name], dtype=np.float64)
        return result

    # Otherwise ASCII format (Values:)
    try:
        text = raw_bytes.decode("utf-16" if is_utf16 else "utf-8", errors="replace")
    except Exception:
        text = raw_bytes.decode("latin-1", errors="replace")

    lines = text.splitlines()
    vars_start = False
    vals_start = False
    var_names = []
    data_lines = []

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
            if len(parts) >= 2 and parts[0].isdigit():
                var_names.append(parts[1])
        elif vals_start:
            if s:
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

    if len(all_floats) % n_vars != 0:
        pts = len(all_floats) // n_vars
        all_floats = all_floats[:pts * n_vars]

    arr = np.array(all_floats, dtype=np.float64).reshape(-1, n_vars)
    return {name: arr[:, i] for i, name in enumerate(var_names)}


parse_raw_waveforms = parse_ascii_raw_waveforms


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
