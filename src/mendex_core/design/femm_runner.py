"""Real FEMM 4.2 Magnetic FEA Runner and Result Extractor for Mendex Studio v2.0.

Dispatches magnetic models to installed FEMM solver, performs finite element meshing,
solves field equations, extracts peak flux density (B_max), and checks core saturation.
"""
from __future__ import annotations

import math
import os
import re
import time
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .ir import IRMagneticGeometry
from .generators.femm_generator import FEMMMagneticGenerator
from integrations.runners.safe_runner import SafeRunner

_FEMM_PROCESS_LOCK = threading.Lock()


class FEMMSimulationResult(BaseModel):
    success: bool
    b_max_tesla: float = 0.0
    saturation_threshold_t: float = 0.49
    is_saturated: bool = False
    core_fem_path: Optional[str] = None
    solver_status: str = "NOT_EVALUATED"
    summary_verdict: str = "NOT_EVALUATED"
    error_message: Optional[str] = None
    execution_time_s: float = 0.0

    @property
    def b_max_t(self) -> float:
        return self.b_max_tesla

    @property
    def core_saturated(self) -> bool:
        return self.is_saturated


class FEMMRunner:
    @staticmethod
    def compare_analytical_vs_fea(
        turns: int,
        current_a: float,
        air_gap_mm: float,
        core_le_mm: float = 50.0,
        mu_r: float = 2200.0,
        fea_b_max: float = 0.0,
    ) -> Dict[str, Any]:
        """Compares FEA peak flux density against 1D magnetic reluctance calculation.

        B_analytical = (mu_0 * N * I) / (l_gap + l_e / mu_r)
        """
        import math
        mu_0 = 4.0 * math.pi * 1e-7
        if turns <= 0 or current_a <= 0:
            return {
                "analytical_b_t": 0.0,
                "fea_b_max_t": fea_b_max,
                "ratio": 0.0,
                "status": "NOT_EVALUATED (Zero Excitation)",
            }
        lg_m = max(1e-6, air_gap_mm * 1e-3)
        le_m = max(1e-3, core_le_mm * 1e-3)
        b_analytical = (mu_0 * float(turns) * float(current_a)) / (lg_m + (le_m / max(1.0, mu_r)))
        ratio = (fea_b_max / b_analytical) if b_analytical > 0 else 0.0
        agreement = "CONVERGED_ORDER_OF_MAGNITUDE" if 0.25 <= ratio <= 4.0 else "DIVERGENT"
        return {
            "analytical_b_t": round(b_analytical, 5),
            "fea_b_max_t": round(fea_b_max, 5),
            "ratio": round(ratio, 3),
            "status": agreement,
        }

    """Controls real FEMM 4.2 finite element solver via headless script execution."""

    DEFAULT_BIN = Path(r"C:\femm42\bin\femm.exe")

    def __init__(self, executable_path: Optional[str] = None):
        self.exe_path = Path(executable_path) if executable_path else self.DEFAULT_BIN
        self.rootdir = self.exe_path.parent if self.exe_path.exists() else None

    @property
    def is_available(self) -> bool:
        return self.exe_path.exists() and self.exe_path.is_file()

    def run_magnetic_analysis(
        self,
        geometry: IRMagneticGeometry,
        work_dir: Path,
        saturation_limit_t: float = 0.49,
        timeout_s: float = 30.0,
        peak_current_a: Optional[float] = None,
    ) -> FEMMSimulationResult:
        """Runs FEMM 4.2 finite element mesher and solver on magnetic core geometry."""
        with _FEMM_PROCESS_LOCK:
            return self._run_magnetic_analysis_locked(
                geometry=geometry,
                work_dir=work_dir,
                saturation_limit_t=saturation_limit_t,
                timeout_s=timeout_s,
                peak_current_a=peak_current_a,
            )

    def _run_magnetic_analysis_locked(
        self,
        geometry: IRMagneticGeometry,
        work_dir: Path,
        saturation_limit_t: float = 0.49,
        timeout_s: float = 30.0,
        peak_current_a: Optional[float] = None,
    ) -> FEMMSimulationResult:
        if not self.is_available:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_NOT_FOUND",
                summary_verdict="BLOCKED",
                error_message=f"FEMM executable not found at {self.exe_path}",
            )

        work_dir = Path(work_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
        core_fem = work_dir / f"{geometry.core_type.lower()}_core.fem"

        eff_current = peak_current_a if peak_current_a is not None else getattr(geometry, "peak_current_a", 0.0) or 0.0

        # When there is no excitation current, solver field is physically zero.
        # AGENTS.md rule: Unavailable checks remain NOT_EVALUATED. Never fabricate calculations.
        if eff_current <= 0:
            return FEMMSimulationResult(
                success=False,
                b_max_tesla=0.0,
                saturation_threshold_t=saturation_limit_t,
                is_saturated=False,
                core_fem_path=str(core_fem),
                solver_status="NOT_EVALUATED",
                summary_verdict="NOT_EVALUATED",
                error_message=(
                    "No verified flux density: solver returned no or zero field. The generated model has no "
                    "winding excitation or boundary conditions, so saturation was not evaluated."
                ),
            )

        # Excited model path: generate complete FEA model with winding excitation and A=0 Dirichlet boundary
        geom_copy = geometry.model_copy(update={"peak_current_a": eff_current})
        lua_script = FEMMMagneticGenerator.generate_lua_script(geom_copy, output_ans_path=str(work_dir / "femm_sim.ans"))
        lua_file = work_dir / "femm_sim.lua"
        lua_file.write_text(lua_script, encoding="utf-8")

        runner = SafeRunner()
        cmd = [str(self.exe_path), "-windowhide", f"-lua-script={lua_file.resolve()}"]
        start_t = time.perf_counter()
        exec_out = runner.run(cmd, cwd=work_dir, timeout_s=int(timeout_s))
        elapsed = time.perf_counter() - start_t

        if exec_out.exit_code != 0:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_ERROR",
                summary_verdict="FAILED",
                execution_time_s=elapsed,
                error_message=f"FEMM solver exited with code {exec_out.exit_code}: {exec_out.stderr}",
            )

        results_txt = work_dir / "results.txt"
        b_max = None
        if results_txt.exists():
            for line in results_txt.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if k.strip().lower() in ("peak_b_pk_tesla", "b_max", "b_max_t", "b_max_tesla"):
                        try:
                            b_max = float(v.strip())
                        except ValueError:
                            pass

        if b_max is None or b_max <= 1e-6:
            return FEMMSimulationResult(
                success=False,
                b_max_tesla=0.0,
                saturation_threshold_t=saturation_limit_t,
                is_saturated=False,
                core_fem_path=str(work_dir / "temp_mag.fem"),
                solver_status="NOT_EVALUATED",
                summary_verdict="NOT_EVALUATED",
                execution_time_s=elapsed,
                error_message="No verified flux density extracted from solver results.",
            )

        is_sat = b_max >= saturation_limit_t
        return FEMMSimulationResult(
            success=True,
            b_max_tesla=b_max,
            saturation_threshold_t=saturation_limit_t,
            is_saturated=is_sat,
            core_fem_path=str(work_dir / "temp_mag.fem"),
            solver_status="SOLVED_CONVERGED",
            summary_verdict="PASSED" if not is_sat else "FAILED (SATURATED)",
            execution_time_s=elapsed,
        )

    @classmethod
    def run_script(cls, script_path: Path, working_dir: Optional[Path] = None) -> FEMMSimulationResult:
        """Executes a Lua script headlessly in FEMM and extracts metrics from results."""
        runner = cls()
        script = Path(script_path).resolve()
        if not script.exists():
            return FEMMSimulationResult(
                success=False,
                solver_status="NOT_FOUND",
                summary_verdict="NOT_EVALUATED",
                error_message=f"Script file '{script}' not found.",
            )
        wdir = (working_dir or script.parent).resolve()
        executable = str(runner.exe_path) if runner.exe_path.exists() else "femm.exe"
        cmd = [executable, "-windowhide", f"-lua-script={script}"]
        
        safe_runner = SafeRunner()
        start = time.perf_counter()
        exec_out = safe_runner.run(cmd, cwd=wdir, timeout_s=60)
        elapsed = time.perf_counter() - start

        if exec_out.exit_code != 0:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_ERROR",
                summary_verdict="FAILED",
                execution_time_s=elapsed,
                error_message=exec_out.stderr or f"Exit code {exec_out.exit_code}",
            )

        # Check if results.txt or femm_results.txt was created
        b_max = None
        for r_name in ("results.txt", "femm_results.txt"):
            rf = wdir / r_name
            if rf.exists():
                for line in rf.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k.strip().lower() in ("peak_b_pk_tesla", "b_max", "b_max_t", "b_max_tesla"):
                            try:
                                b_max = float(v.strip())
                            except ValueError:
                                pass
                if b_max is not None:
                    break

        if b_max is not None and b_max > 1e-6:
            is_sat = b_max >= 0.49
            return FEMMSimulationResult(
                success=True,
                b_max_tesla=b_max,
                is_saturated=is_sat,
                solver_status="SOLVED_CONVERGED",
                summary_verdict="PASSED" if not is_sat else "FAILED (SATURATED)",
                execution_time_s=elapsed,
            )

        # Script completed cleanly but no field output recorded
        return FEMMSimulationResult(
            success=True,
            solver_status="SCRIPT_COMPLETED",
            summary_verdict="NOT_EVALUATED",
            execution_time_s=elapsed,
        )
