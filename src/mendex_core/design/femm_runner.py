"""Real FEMM 4.2 Magnetic FEA Runner and Result Extractor for Mendex Studio v2.0.

Dispatches magnetic models to installed FEMM solver, performs finite element meshing,
solves field equations, extracts peak flux density (B_max), and checks core saturation.
"""
from __future__ import annotations

import math
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .ir import IRMagneticGeometry


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
    """Controls real FEMM 4.2 finite element solver via official filelink protocol."""

    DEFAULT_BIN = Path(r"C:\femm42\bin\femm.exe")

    def __init__(self, executable_path: Optional[str] = None):
        self.exe_path = Path(executable_path) if executable_path else self.DEFAULT_BIN
        self.rootdir = self.exe_path.parent if self.exe_path.exists() else None

    @property
    def is_available(self) -> bool:
        return self.exe_path.exists() and self.rootdir is not None

    def run_magnetic_analysis(
        self,
        geometry: IRMagneticGeometry,
        work_dir: Path,
        saturation_limit_t: float = 0.49,
        timeout_s: float = 30.0,
    ) -> FEMMSimulationResult:
        """Runs FEMM 4.2 finite element mesher and solver on magnetic core geometry."""
        if not self.is_available:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_NOT_FOUND",
                summary_verdict="BLOCKED",
                error_message=f"FEMM executable not found at {self.exe_path}",
            )

        work_dir.mkdir(parents=True, exist_ok=True)
        core_fem = work_dir / f"{geometry.core_type.lower()}_core.fem"
        core_fem_str = str(core_fem).replace("\\", "/")

        ifile = self.rootdir / "ifile.txt"
        ofile = self.rootdir / "ofile.txt"

        # Clear any dangling pipe files
        if ifile.exists():
            try:
                ifile.unlink()
            except Exception:
                pass
        if ofile.exists():
            try:
                ofile.unlink()
            except Exception:
                pass

        # Launch FEMM in filelink mode
        proc = subprocess.Popen([str(self.exe_path), "-filelink", "-windowhide"])
        time.sleep(0.4)

        def _call_femm(cmd_str: str) -> str:
            with open(ifile, "w", encoding="latin1") as f:
                f.write(f"flput({cmd_str})")
            
            start_t = time.time()
            while not ofile.exists():
                time.sleep(0.01)
                if time.time() - start_t > timeout_s:
                    raise TimeoutError(f"FEMM filelink timed out waiting for response to: {cmd_str}")

            with open(ofile, "r", encoding="latin1") as f:
                resp = f.read().strip()
            ofile.unlink()
            return resp

        try:
            _call_femm("setcompatibilitymode(0)")
            _call_femm("create(0)")
            _call_femm('mi_probdef(100000, "millimeters", "planar", 1e-8, 20, 30)')

            # Draw core outline
            w = geometry.flange_od_mm / 2.0
            h = geometry.bobbin_height_mm / 2.0
            _call_femm(f"mi_drawrectangle(-{w}, -{h}, {w}, {h})")

            # Materials
            _call_femm('mi_addmaterial("Air", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0)')
            _call_femm(f'mi_addmaterial("{geometry.core_material}", 2200, 2200, 0, 0, 0, 0, 0, 1, 0, 0, 0)')
            _call_femm("mi_addblocklabel(0, 0)")
            _call_femm("mi_selectlabel(0, 0)")
            _call_femm(f'mi_setblockprop("{geometry.core_material}", 1, 0, "<None>", 0, 0, 0)')
            _call_femm("mi_clearselected()")

            # Save and solve
            _call_femm(f'mi_saveas("{core_fem_str}")')
            _call_femm("mi_createmesh()")
            _call_femm("mi_analyze(1)")
            _call_femm("mi_loadsolution()")

            # Point value calculation in core center
            raw_pt = _call_femm("mo_getpointvalues(0, 0)")
            
            # Close documents
            _call_femm("mo_close()")
            _call_femm("mi_close()")
            _call_femm("exit()")

            # Parse flux density magnitude from solver output
            b_measured = None
            if raw_pt and raw_pt.strip():
                try:
                    import json
                    nums = json.loads(raw_pt)
                    if isinstance(nums, list) and len(nums) >= 3:
                        b1 = float(nums[1])
                        b2 = float(nums[2])
                        b_calc = math.sqrt(b1**2 + b2**2)
                        # A zero field means the model carries no excitation; never substitute an estimate.
                        if b_calc > 1e-6:
                            b_measured = b_calc
                    elif isinstance(nums, (int, float)):
                        b_measured = abs(float(nums))
                except Exception:
                    b_measured = None

            if b_measured is None:
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

            is_sat = b_measured >= saturation_limit_t
            return FEMMSimulationResult(
                success=True,
                b_max_tesla=b_measured,
                saturation_threshold_t=saturation_limit_t,
                is_saturated=is_sat,
                core_fem_path=str(core_fem),
                solver_status="SOLVED_CONVERGED",
                summary_verdict="PASSED" if not is_sat else "FAILED (SATURATED)",
            )

        except Exception as e:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_ERROR",
                summary_verdict="FAILED",
                error_message=str(e),
            )
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            if ifile.exists():
                try:
                    ifile.unlink()
                except Exception:
                    pass
            if ofile.exists():
                try:
                    ofile.unlink()
                except Exception:
                    pass

    @classmethod
    def run_script(cls, script_path: Path, working_dir: Optional[Path] = None) -> FEMMSimulationResult:
        """Executes a Lua script headlessly in FEMM."""
        runner = cls()
        script = Path(script_path).resolve()
        if not script.exists():
            return FEMMSimulationResult(
                success=False,
                solver_status="NOT_FOUND",
                summary_verdict="NOT_EVALUATED",
                error_message=f"Script file '{script}' not found.",
            )
        wdir = working_dir or script.parent
        executable = str(runner.exe_path) if runner.exe_path.exists() else "femm.exe"
        cmd = [executable, "-windowhide", f"-lua-script={script}"]
        start = time.perf_counter()
        try:
            res = subprocess.run(cmd, cwd=str(wdir), capture_output=True, text=True, timeout=60)
            elapsed = time.perf_counter() - start
            # Exit code 0 only proves the script ran; no field quantity is extracted here.
            return FEMMSimulationResult(
                success=(res.returncode == 0),
                solver_status="SCRIPT_COMPLETED" if res.returncode == 0 else "SOLVER_ERROR",
                summary_verdict="NOT_EVALUATED" if res.returncode == 0 else "FAILED",
                execution_time_s=elapsed,
                error_message=res.stderr if res.returncode != 0 else None,
            )
        except Exception as exc:
            return FEMMSimulationResult(
                success=False,
                solver_status="SOLVER_ERROR",
                summary_verdict="NOT_EVALUATED",
                error_message=str(exc),
            )
