"""Real LTspice Simulation Runner and Result Parser for Mendex Engineering Studio v2.0.

Executes LTspice in batch mode, ingests actual .raw and .log outputs, extracts
waveforms, calculates physical metrics (Vout, ripple, peak current), and evaluates
engineering requirements.
"""
from __future__ import annotations

import math
import subprocess
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
    convergence_status: str = "CONVERGED"
    requirements_evaluated: Dict[str, str] = Field(default_factory=dict)
    summary_verdict: str = "PENDING"
    error_message: Optional[str] = None


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

    def run_simulation(
        self,
        netlist_path: Path,
        requirements: Optional[List[Requirement]] = None,
        timeout_s: float = 60.0,
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

        work_dir = net_file.parent
        cmd = [str(self.exe_path), "-b", "-ascii", str(net_file)]

        try:
            proc = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return LTspiceSimulationResult(
                success=False,
                exit_code=-1,
                convergence_status="TIMED_OUT",
                summary_verdict="FAILED",
                error_message=f"Simulation timed out after {timeout_s} seconds.",
            )
        except Exception as e:
            return LTspiceSimulationResult(
                success=False,
                exit_code=-1,
                convergence_status="EXECUTION_ERROR",
                summary_verdict="FAILED",
                error_message=str(e),
            )

        log_file = net_file.with_suffix(".log")
        raw_file = net_file.with_suffix(".raw")

        log_path_str = str(log_file) if log_file.exists() else None
        raw_path_str = str(raw_file) if raw_file.exists() else None

        if proc.returncode != 0 or not raw_file.exists():
            return LTspiceSimulationResult(
                success=False,
                exit_code=proc.returncode,
                log_file_path=log_path_str,
                raw_file_path=raw_path_str,
                convergence_status="SOLVER_FAILED",
                summary_verdict="FAILED",
                error_message=f"Solver exited with code {proc.returncode}. Output raw missing.",
            )

        # Parse ASCII raw file
        time_vals, vout_vals, iin_vals = self._parse_ascii_raw(raw_file)

        if not time_vals or not vout_vals:
            # Fallback if raw parse failed
            return LTspiceSimulationResult(
                success=True,
                exit_code=0,
                log_file_path=log_path_str,
                raw_file_path=raw_path_str,
                convergence_status="RAW_EMPTY",
                summary_verdict="FAILED",
            )

        # Analyze steady-state metrics (use last 30% of simulation for steady state)
        n_pts = len(vout_vals)
        start_idx = int(n_pts * 0.70)
        ss_vout = vout_vals[start_idx:] if start_idx < n_pts else vout_vals

        v_mean = sum(ss_vout) / len(ss_vout) if ss_vout else 0.0
        v_min = min(ss_vout) if ss_vout else 0.0
        v_max = max(ss_vout) if ss_vout else 0.0
        v_ripple = v_max - v_min
        i_pk = max(iin_vals) if iin_vals else 0.0

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

        overall_verdict = "PASSED" if all_passed else "FAILED"

        return LTspiceSimulationResult(
            success=True,
            exit_code=0,
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
            convergence_status="CONVERGED",
            requirements_evaluated=verdicts,
            summary_verdict=overall_verdict,
        )

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
                    var_indices[var_name] = idx

        if not in_values:
            return [], [], []

        # Find which indices correspond to V(out), V(in), Time
        t_idx = 0
        v_out_idx = next((idx for name, idx in var_indices.items() if "OUT" in name or "VOUT" in name), 1)
        v_in_idx = next((idx for name, idx in var_indices.items() if "IN" in name or "VIN" in name), 2)
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

                    if v_in_idx - 1 < len(point_vars):
                        iin_vals.append(point_vars[v_in_idx - 1])
                    else:
                        iin_vals.append(0.0)
                except Exception:
                    pass
            i += 1

        return time_vals, vout_vals, iin_vals
