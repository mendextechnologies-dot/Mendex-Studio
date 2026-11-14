"""Real LTspice Simulation Runner and Result Parser for Mendex Engineering Studio v2.0.

Executes LTspice in batch mode, ingests actual .raw and .log outputs, extracts
waveforms, calculates physical metrics (Vout, ripple, peak current), and evaluates
engineering requirements.
"""
from __future__ import annotations

import math
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from .models import Requirement


class WaveformTrace(BaseModel):
    name: str
    unit: str
    points: List[float] = Field(default_factory=list)


class LTspiceSimulationResult(BaseModel):
    success: bool
    exit_code: int
    raw_file_path: Optional[str] = None
    log_file_path: Optional[str] = None
    elapsed_time_s: float = 0.0
    time_trace: List[float] = Field(default_factory=list)
    vout_trace: List[float] = Field(default_factory=list)
    iin_trace: List[float] = Field(default_factory=list)
    vout_mean_v: float = 0.0
    vout_ripple_pk_pk_v: float = 0.0
    vout_min_v: float = 0.0
    vout_max_v: float = 0.0
    i_peak_a: float = 0.0
    convergence_status: str = "NOT_EVALUATED"
    log_errors: List[str] = Field(default_factory=list)
    log_warnings: List[str] = Field(default_factory=list)
    requirements_evaluated: Dict[str, str] = Field(default_factory=dict)
    measurements: Dict[str, float] = Field(default_factory=dict)
    summary_verdict: str = "PENDING"
    error_message: Optional[str] = None

    @property
    def raw_file(self) -> Optional[Path]:
        return Path(self.raw_file_path) if self.raw_file_path else None

    @property
    def log_file(self) -> Optional[Path]:
        return Path(self.log_file_path) if self.log_file_path else None

    @property
    def execution_time_s(self) -> float:
        return self.elapsed_time_s

    @property
    def steady_state_metrics(self) -> Dict[str, float]:
        return {
            "vout_mean_v": self.vout_mean_v,
            "vout_ripple_pk_pk_v": self.vout_ripple_pk_pk_v,
            "vout_min_v": self.vout_min_v,
            "vout_max_v": self.vout_max_v,
            "i_peak_a": self.i_peak_a,
        }


class LTspiceRunner:
    """Discovers and executes real LTspice solver, parsing true numerical outputs."""

    DEFAULT_PATHS = [
        r"C:\Program Files\ADI\LTspice\LTspice.exe",
        r"C:\Users\Sagar\AppData\Local\Programs\ADI\LTspice\LTspice.exe",
        r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
    ]

    def __init__(self, executable_path: Optional[str] = None):
        self.exe_path = None
        if executable_path and Path(executable_path).exists():
            self.exe_path = Path(executable_path)
        else:
            for p in self.DEFAULT_PATHS:
                if Path(p).exists():
                    self.exe_path = Path(p)
                    break

    @property
    def is_available(self) -> bool:
        return self.exe_path is not None and self.exe_path.exists()

    @classmethod
    def run_transient(
        cls,
        netlist_path: Path,
        sim_time_s: float = 0.002,
        time_step_s: Optional[float] = None,
        working_dir: Optional[Path] = None,
    ) -> LTspiceSimulationResult:
        """Convenience classmethod reconciling public simulation runner interface."""
        runner = cls()
        return runner.run_simulation(
            netlist_path=netlist_path,
            stop_time_s=sim_time_s,
            time_step_s=time_step_s,
            working_dir=working_dir,
        )

    def run_simulation(
        self,
        netlist_path: Path,
        requirements: Optional[List[Requirement]] = None,
        timeout_s: float = 60.0,
        stop_time_s: Optional[float] = None,
        time_step_s: Optional[float] = None,
        working_dir: Optional[Path] = None,
    ) -> LTspiceSimulationResult:
        """Executes LTspice on netlist file and parses real simulation metrics."""
        if not self.is_available:
            return LTspiceSimulationResult(
                success=False,
                exit_code=-1,
                convergence_status="SOLVER_NOT_FOUND",
                summary_verdict="BLOCKED",
                error_message="LTspice executable not found on workstation.",
            )

        net_file = netlist_path.resolve()
        if not net_file.exists():
            raise FileNotFoundError(f"Netlist file not found: {net_file}")

        work_dir = Path(working_dir).resolve() if working_dir else net_file.parent
        cmd = [str(self.exe_path), "-b", "-ascii", str(net_file)]
        start_clock = time.perf_counter()

        try:
            proc = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True, timeout=timeout_s)
            elapsed_s = max(0.001, time.perf_counter() - start_clock)
        except subprocess.TimeoutExpired:
            elapsed_s = time.perf_counter() - start_clock
            return LTspiceSimulationResult(
                success=False,
                exit_code=-1,
                elapsed_time_s=round(elapsed_s, 4),
                convergence_status="TIMED_OUT",
                summary_verdict="FAILED",
                error_message=f"Simulation timed out after {timeout_s} seconds.",
            )
        except Exception as e:
            elapsed_s = time.perf_counter() - start_clock
            return LTspiceSimulationResult(
                success=False,
                exit_code=-1,
                elapsed_time_s=round(elapsed_s, 4),
                convergence_status="EXECUTION_ERROR",
                summary_verdict="FAILED",
                error_message=str(e),
            )

        log_file = net_file.with_suffix(".log")
        raw_file = net_file.with_suffix(".raw")

        log_path_str = str(log_file) if log_file.exists() else None
        raw_path_str = str(raw_file) if raw_file.exists() else None

        log_errors, log_warnings = self._parse_log(log_file)

        if proc.returncode != 0 or not raw_file.exists():
            detail = "; ".join(log_errors) if log_errors else "Output raw missing."
            return LTspiceSimulationResult(
                success=False,
                exit_code=proc.returncode,
                elapsed_time_s=round(elapsed_s, 4),
                log_file_path=log_path_str,
                raw_file_path=raw_path_str,
                convergence_status="SOLVER_FAILED",
                log_errors=log_errors,
                log_warnings=log_warnings,
                summary_verdict="FAILED",
                error_message=f"Solver exited with code {proc.returncode}. {detail}",
            )

        # Parse ASCII raw file
        time_vals, vout_vals, iin_vals = self._parse_ascii_raw(raw_file)

        if not time_vals or not vout_vals:
            # Fallback if raw parse failed
            return LTspiceSimulationResult(
                success=False,
                exit_code=0,
                log_file_path=log_path_str,
                raw_file_path=raw_path_str,
                convergence_status="RAW_EMPTY",
                log_errors=log_errors,
                log_warnings=log_warnings,
                summary_verdict="FAILED",
                error_message="Solver produced no parseable output waveform.",
            )

        # Parse .meas statements from log if present
        meas_map: Dict[str, float] = {}
        if log_file.exists():
            import re
            log_txt = log_file.read_text(encoding="utf-8", errors="ignore")
            for line_item in log_txt.splitlines():
                m_match = re.match(r"^([a-zA-Z0-9_]+):\s+(?:[^=]+=)?([\-\+]?\d+(?:\.\d+)?(?:[eE][\-\+]?\d+)?)(?:\s+from|\s+at|\s*$)", line_item.strip(), re.IGNORECASE)
                if m_match:
                    k_name, k_val = m_match.groups()
                    try:
                        meas_map[k_name.lower()] = float(k_val)
                    except ValueError:
                        pass

        # Analyze steady-state metrics (use last 30% of simulation for steady state)
        n_pts = len(vout_vals)
        start_idx = int(n_pts * 0.70)
        ss_vout = vout_vals[start_idx:] if start_idx < n_pts else vout_vals

        v_mean = sum(ss_vout) / len(ss_vout) if ss_vout else 0.0
        v_min = min(ss_vout) if ss_vout else 0.0
        v_max = max(ss_vout) if ss_vout else 0.0
        v_ripple = v_max - v_min
        # Use .meas if present
        if "vout_avg" in meas_map:
            v_mean = meas_map["vout_avg"]
        if "vout_ripple" in meas_map:
            v_ripple = meas_map["vout_ripple"]
        if "vout_min" in meas_map:
            v_min = meas_map["vout_min"]
        if "vout_max" in meas_map:
            v_max = meas_map["vout_max"]
        # Peak current over the same steady-state window (excludes start-up inrush).
        ss_iin = iin_vals[int(len(iin_vals) * 0.70):] if iin_vals else []
        i_pk = max((abs(v) for v in ss_iin), default=0.0)

        # Evaluate requirements
        verdicts: Dict[str, str] = {}
        all_passed = True

        if requirements:
            for req in requirements:
                p_name = req.parameter.lower()
                if p_name in ("vout", "v_out", "target_voltage"):
                    tol = (req.tolerance_pct or 5.0) / 100.0
                    target = req.target_value
                    diff = abs(v_mean - target) / max(target, 0.01)
                    passed = diff <= tol
                    verdicts[req.parameter] = f"{'PASSED' if passed else 'FAILED'} (Measured {v_mean:.2f}V vs Target {target:.2f}V, diff {diff*100:.1f}%)"
                    if not passed:
                        all_passed = False

                elif p_name in ("ripple", "vout_ripple", "voltage_ripple"):
                    max_rip = req.max_value or (0.02 * req.target_value if req.target_value else 0.1)
                    passed = v_ripple <= max_rip
                    verdicts[req.parameter] = f"{'PASSED' if passed else 'FAILED'} (Ripple {v_ripple*1e3:.1f}mV vs Max {max_rip*1e3:.1f}mV)"
                    if not passed:
                        all_passed = False

        if log_errors:
            convergence = "SOLVER_ERRORS"
            overall_verdict = "FAILED"
        elif not verdicts:
            # A run with no evaluated requirement proves nothing about the design.
            convergence = "COMPLETED_WITH_WARNINGS" if log_warnings else "COMPLETED"
            overall_verdict = "NOT_EVALUATED"
        else:
            convergence = "COMPLETED_WITH_WARNINGS" if log_warnings else "COMPLETED"
            overall_verdict = "PASSED" if all_passed else "FAILED"

        return LTspiceSimulationResult(
            success=True,
            exit_code=0,
            elapsed_time_s=round(elapsed_s, 4),
            raw_file_path=raw_path_str,
            log_file_path=log_path_str,
            time_trace=time_vals[:200],  # sample points for preview
            vout_trace=vout_vals[:200],
            iin_trace=iin_vals[:200],
            vout_mean_v=round(v_mean, 4),
            vout_ripple_pk_pk_v=round(v_ripple, 4),
            vout_min_v=round(v_min, 4),
            vout_max_v=round(v_max, 4),
            i_peak_a=round(i_pk, 4),
            convergence_status=convergence,
            log_errors=log_errors,
            log_warnings=log_warnings,
            requirements_evaluated=verdicts,
            measurements=meas_map,
            summary_verdict=overall_verdict,
        )

    ERROR_MARKERS = ("error", "singular matrix", "time step too small", "timestep too small", "convergence failed", "unknown", "can't find")
    WARNING_MARKERS = ("warning", "floating", "questionable use")

    @classmethod
    def _parse_log(cls, log_path: Path) -> tuple[List[str], List[str]]:
        """Extracts solver errors and warnings from the LTspice .log (UTF-16 or 8-bit)."""
        if not log_path.exists():
            return [], ["Solver log file missing."]
        data = log_path.read_bytes()
        text = None
        if data[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(data) > 1 and data[1:2] == b"\x00"):
            try:
                text = data.decode("utf-16")
            except UnicodeDecodeError:
                text = None
        if text is None:
            text = data.decode("latin-1")
        errors: List[str] = []
        warnings: List[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            low = line.lower()
            if not line:
                continue
            if "is floating" in low:
                errors.append(line)  # a floating node (e.g. undriven gate) invalidates the circuit
            elif any(m in low for m in cls.WARNING_MARKERS):
                warnings.append(line)
            elif any(m in low for m in cls.ERROR_MARKERS):
                errors.append(line)
        return errors, warnings

    def _parse_ascii_raw(self, raw_path: Path) -> tuple[List[float], List[float], List[float]]:
        """Parses ASCII .raw file generated with -ascii flag."""
        time_vals: List[float] = []
        vout_vals: List[float] = []
        iin_vals: List[float] = []

        try:
            with open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return [], [], []

        # Find Variables and Values section
        var_indices: Dict[str, int] = {}
        var_types: Dict[int, str] = {}
        in_vars = False
        in_values = False

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("Variables:"):
                in_vars = True
                continue
            elif line_str.startswith("Values:"):
                in_vars = False
                in_values = True
                continue

            if in_vars:
                parts = line_str.split()
                if len(parts) >= 3 and parts[0].isdigit():
                    idx = int(parts[0])
                    var_name = parts[1].upper()
                    var_type = parts[2].lower() if len(parts) >= 3 else ""
                    var_indices[var_name] = idx
                    var_types[idx] = var_type

        if not in_values:
            return [], [], []

        # Find indices: V(out) must be a voltage signal, I(in) must be an actual current signal!
        t_idx = 0
        v_out_idx = None
        for name, idx in var_indices.items():
            is_volt = var_types.get(idx) == "voltage" or name.startswith("V(")
            if is_volt and any(k in name for k in ("OUT", "VOUT")):
                v_out_idx = idx
                break
        if v_out_idx is None:
            for name, idx in var_indices.items():
                is_volt = var_types.get(idx) == "voltage" or name.startswith("V(")
                if is_volt and not any(k in name for k in ("VIN", "V(IN)")):
                    v_out_idx = idx
                    break

        # Current extraction: NEVER select V(vin) as input current! Only true current signals.
        i_in_idx = None
        for name, idx in var_indices.items():
            is_curr = var_types.get(idx) == "current" or name.startswith("I(")
            if is_curr and any(k in name for k in ("IN", "VIN", "V1", "L1", "PRI")):
                i_in_idx = idx
                break
        if i_in_idx is None:
            for name, idx in var_indices.items():
                if var_types.get(idx) == "current" or name.startswith("I("):
                    i_in_idx = idx
                    break
        n_vars = len(var_indices)

        # Parse data points
        # In LTspice ASCII raw transient, each timestep starts with:
        # <point_num> <time_val>
        # followed by remaining variables on subsequent lines or same line
        curr_vals = []
        val_lines = [l.strip() for l in lines[lines.index("Values:\n")+1:] if l.strip()]

        i = 0
        while i < len(val_lines):
            parts = val_lines[i].split()
            if len(parts) >= 2 and parts[0].isdigit():
                # Start of timestep
                try:
                    t_val = float(parts[1])
                    time_vals.append(t_val)
                    # Next lines are variables
                    point_vars = []
                    i += 1
                    while i < len(val_lines) and not (val_lines[i].split() and val_lines[i].split()[0].isdigit() and len(val_lines[i].split()) >= 2 and "." not in val_lines[i].split()[0]):
                        point_vars.extend([float(v) for v in val_lines[i].split() if v])
                        if len(point_vars) >= n_vars - 1:
                            break
                        i += 1

                    if v_out_idx - 1 < len(point_vars):
                        vout_vals.append(point_vars[v_out_idx - 1])
                    else:
                        vout_vals.append(0.0)

                    if i_in_idx is not None and (i_in_idx - 1) < len(point_vars):
                        iin_vals.append(point_vars[i_in_idx - 1])
                except Exception:
                    pass
            i += 1

        return time_vals, vout_vals, iin_vals
