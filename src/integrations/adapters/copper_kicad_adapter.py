"""Copper KiCad Integration Adapter for Mendex Engineering Studio.

Provides native KiCad 10 automated topological routing, copper zone pouring,
raytraced 3D board rendering, and ERC/DRC verification by internally leveraging
the embedded copper_kicad engine.

Mendex Core remains the exclusive authority for:
  - Engineering specifications and calculations
  - High-voltage clearance/creepage rules (IEC 60664-1 / IEC 61010-1)
  - 9-stage engineering lifecycle and immutable audit logs
  - Human reviewer sign-offs and reporting
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# Import internal copper_kicad engine modules
import copper_kicad.tools
from copper_kicad.mcp.registry import call_tool, TOOLS
from copper_kicad import project as P
from copper_kicad.kicad import env
from copper_kicad.pcb import rules
from copper_kicad.render import pcb_3d


class CopperKiCadAdapter:
    """Internal adapter connecting Mendex Engineering Core to copper_kicad."""

    def __init__(self, kicad_cli_path: Optional[str] = None):
        if kicad_cli_path:
            os.environ["COPPER_KICAD_CLI"] = str(Path(kicad_cli_path).resolve())
        # Disable remote update pinging per Mendex engineering rules
        os.environ["COPPER_NO_UPDATE_CHECK"] = "1"
        self._inst = None

    @property
    def install(self):
        if self._inst is None:
            self._inst = env.kicad()
        return self._inst

    def is_available(self) -> bool:
        """Returns True if KiCad 10 CLI and pcbnew Python interpreter are operational."""
        try:
            inst = self.install
            return bool(inst and inst.cli and inst.cli.exists())
        except Exception:
            return False

    def doctor_status(self) -> Dict[str, Any]:
        """Returns structured diagnostic status of KiCad and Copper engine."""
        try:
            from copper_kicad.review import project_info as I
            return I.status()
        except Exception as exc:
            return {"available": False, "error": str(exc)}

    def route_pcb(
        self,
        pcb_path: Path,
        pour_ground: bool = True,
        ground_net: str = "GND",
        ripup: str = "all",
        default_track: float = 0.4,
        power_track: float = 1.2,
        power_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Routes all unrouted nets on a KiCad PCB layout using the internal guided router.

        Applies power electronics net-class widths (e.g. 1.2 mm - 2.5 mm for power nets,
        0.4 mm for signals), and optionally pours a solid ground return copper zone on B.Cu.
        Returns a dictionary with routing metrics (tracks, vias, unrouted count, DRC errors).
        """
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        project_dir = board_file.parent
        res_summary = {
            "pcb_path": str(board_file),
            "pour_completed": False,
            "routing_completed": False,
            "unrouted_before": -1,
            "unrouted_after": -1,
            "tracks": 0,
            "vias": 0,
            "drc_errors": 0,
            "netclasses": {},
            "messages": [],
        }

        # Step 0: Power Electronics Net-Class Injection
        try:
            pr = P.resolve(board_file)
            p_pats = power_patterns or ["*HV*", "*DRAIN*", "*PRI*", "*SEC*", "*VOUT*", "*VIN*"]
            nc_info = rules.set_netclasses(
                pr,
                default_track=default_track,
                power_track=power_track,
                extra_power=p_pats,
                write=True,
            )
            res_summary["netclasses"] = nc_info
            res_summary["messages"].append(f"Netclasses configured: Default={default_track}mm, Power={power_track}mm")
        except Exception as e:
            res_summary["messages"].append(f"Netclass setup notice: {e}")

        # Step 1: Optional Ground Copper Pour
        if pour_ground:
            pour_res = call_tool("pcb_pour", {
                "project": str(board_file),
                "net": ground_net,
                "layers": ["B.Cu"]
            })
            if not pour_res.get("isError"):
                res_summary["pour_completed"] = True
                res_summary["messages"].append("Ground copper pour filled on B.Cu")
            else:
                text_err = _extract_text(pour_res)
                res_summary["messages"].append(f"Pour notice: {text_err}")

        # Step 2: Deterministic Guided Routing
        route_res = call_tool("pcb_route_guided", {
            "project": str(board_file),
            "ripup": ripup
        })

        if route_res.get("isError"):
            err_msg = _extract_text(route_res)
            res_summary["messages"].append(f"Guided routing error: {err_msg}")
        else:
            res_summary["routing_completed"] = True
            route_data = route_res.get("structuredContent") or {}
            res_summary["unrouted_after"] = route_data.get("unrouted", 0)

        # Step 3: Inspect post-routing structure
        stats_res = call_tool("pcb_read", {
            "project": str(board_file),
            "what": ["summary"]
        })
        stats_data = stats_res.get("structuredContent") or {}
        res_summary["tracks"] = stats_data.get("tracks", 0)
        res_summary["vias"] = stats_data.get("vias", 0)
        res_summary["unrouted_after"] = stats_data.get("unrouted", 0)

        # Step 4: Verify DRC
        drc_res = call_tool("verify", {
            "project": str(board_file),
            "what": ["drc"],
            "refill": True
        })
        drc_data = (drc_res.get("structuredContent") or {}).get("drc") or {}
        res_summary["drc_errors"] = drc_data.get("errors", 0)
        res_summary["drc_warnings"] = drc_data.get("warnings", 0)

        return res_summary

    def render_3d(
        self,
        pcb_path: Path,
        output_png: Optional[Path] = None,
        view: str = "iso",
        width: int = 1200,
        height: int = 900,
        quality: str = "basic"
    ) -> Path:
        """Renders a raytraced 3D image of the PCB using KiCad's native CLI renderer.

        Saves to output_png or board directory / copper-out / render / pcb-3d-<view>.png.
        """
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        out_dir = output_png.parent if output_png else (board_file.parent / "copper-out" / "render")
        out_dir.mkdir(parents=True, exist_ok=True)

        img = pcb_3d(board_file, out_dir=out_dir, view=view, width=width, height=height, quality=quality)
        src_path = Path(img.path)

        if output_png:
            target = Path(output_png).resolve()
            if src_path != target:
                shutil.copy2(src_path, target)
                return target

        return src_path

    def run_erc(self, sch_path: Path) -> Dict[str, Any]:
        """Runs KiCad ERC on schematic using Copper verify engine."""
        sch_file = Path(sch_path).resolve()
        if not sch_file.exists():
            raise FileNotFoundError(f"Schematic not found: {sch_file}")

        res = call_tool("verify", {
            "project": str(sch_file.parent),
            "what": ["erc"]
        })
        return res.get("structuredContent") or {}

    def run_drc(self, pcb_path: Path, refill: bool = True) -> Dict[str, Any]:
        """Runs KiCad DRC on PCB layout using Copper verify engine."""
        pcb_file = Path(pcb_path).resolve()
        if not pcb_file.exists():
            raise FileNotFoundError(f"PCB file not found: {pcb_file}")

        res = call_tool("verify", {
            "project": str(pcb_file.parent),
            "what": ["drc"],
            "refill": refill
        })
        return res.get("structuredContent") or {}


def _extract_text(mcp_res: dict) -> str:
    if not isinstance(mcp_res, dict):
        return str(mcp_res)
    for c in mcp_res.get("content", []):
        if c.get("type") == "text":
            return c.get("text", "")
    return ""
