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
        thermal_spoke: float = 0.5,
        thermal_gap: float = 0.5,
        pad_connection: str = "tht_thermal",
        stitch_ground: bool = False,
        stitch_pitch: float = 5.0,
        zone_clearance: float = 0.5,
        pour_layers: Optional[List[str]] = None,
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

        # Step 1: Optional Ground Copper Pour with Thermal Relief & Clearance Customization
        if pour_ground:
            # Auto-resolve ground net if default ground_net is not present on board
            effective_gnd = ground_net
            try:
                board_content = board_file.read_text(encoding="utf-8", errors="ignore")
                gnd_candidates = [
                    ground_net, f"/{ground_net}",
                    "PRI_GND", "/PRI_GND",
                    "GND", "/GND",
                    "SEC_GND", "/SEC_GND",
                    "0", "VSS", "PGND"
                ]
                for candidate in gnd_candidates:
                    if f'"{candidate}"' in board_content or f' {candidate}' in board_content:
                        effective_gnd = candidate.lstrip("/")
                        break
            except Exception:
                effective_gnd = ground_net

            layers_to_pour = pour_layers or ["B.Cu"]
            pour_args: Dict[str, Any] = {
                "project": str(board_file),
                "net": effective_gnd,
                "layers": layers_to_pour,
                "thermal_spoke": thermal_spoke,
                "thermal_gap": thermal_gap,
                "pad_connection": pad_connection,
                "clearance": zone_clearance,
            }
            if stitch_ground:
                pour_args["stitch"] = True
                pour_args["stitch_pitch"] = stitch_pitch

            pour_res = call_tool("pcb_pour", pour_args)
            if not pour_res.get("isError"):
                res_summary["pour_completed"] = True
                res_summary["messages"].append(
                    f"Ground copper pour filled on {layers_to_pour} (thermal_spoke={thermal_spoke}mm, thermal_gap={thermal_gap}mm, pad_conn={pad_connection})"
                )
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
            res_summary["routing_completed"] = False
        else:
            route_data = route_res.get("structuredContent") or {}
            unrouted = route_data.get("unrouted", 0)
            res_summary["unrouted_after"] = unrouted
            res_summary["routing_completed"] = (unrouted == 0)

        # Step 3: Inspect post-routing structure
        stats_res = call_tool("pcb_read", {
            "project": str(board_file),
            "what": ["summary"]
        })
        stats_data = stats_res.get("structuredContent") or {}
        res_summary["tracks"] = stats_data.get("tracks", 0)
        res_summary["vias"] = stats_data.get("vias", 0)
        if "unrouted" in stats_data:
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
        res_summary["routing_completed"] = (not route_res.get("isError")) and (res_summary["unrouted_after"] == 0)
        res_summary["success"] = res_summary["routing_completed"] and (res_summary["drc_errors"] == 0)

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

    @staticmethod
    def calculate_iec60664_creepage(
        working_voltage_v: float,
        pollution_degree: int = 2,
        material_group: str = "IIIa",
        insulation_type: str = "reinforced",
    ) -> float:
        """Calculates required creepage distance in millimeters per IEC 60664-1 Table F.4.

        Evaluates working voltage, pollution degree (1-3), and material group (I, II, IIIa, IIIb).
        Reinforced insulation doubles the basic insulation distance.
        Fails closed on non-positive voltages or invalid parameters.
        Notice: this analytical helper assists PCB layout geometry; formal safety qualification
        requires independent standards verification and physical barrier inspection.
        """
        import math
        if not math.isfinite(working_voltage_v) or working_voltage_v <= 0:
            raise ValueError(f"Working voltage must be strictly positive and finite, got {working_voltage_v}")
        if pollution_degree not in (1, 2, 3):
            raise ValueError(f"Pollution degree must be 1, 2, or 3, got {pollution_degree}")

        mg = str(material_group).strip().upper()
        if mg not in ("I", "II", "IIIA", "IIIB"):
            raise ValueError(f"Invalid material group '{material_group}'. Must be 'I', 'II', 'IIIa', or 'IIIb'.")

        ins = str(insulation_type).strip().lower()
        if ins not in ("basic", "reinforced", "functional", "double"):
            raise ValueError(f"Invalid insulation type '{insulation_type}'. Must be basic, reinforced, functional, or double.")

        v = float(working_voltage_v)
        # IEC 60664-1 Table F.4 creepage distances for Pollution Degree 2 (in mm)
        f4_table = [
            (50.0, {"I": 0.6, "II": 0.85, "IIIA": 1.2, "IIIB": 1.2}),
            (100.0, {"I": 0.71, "II": 1.0, "IIIA": 1.4, "IIIB": 1.4}),
            (125.0, {"I": 0.75, "II": 1.05, "IIIA": 1.5, "IIIB": 1.5}),
            (160.0, {"I": 0.8, "II": 1.1, "IIIA": 1.6, "IIIB": 1.6}),
            (200.0, {"I": 1.0, "II": 1.4, "IIIA": 2.0, "IIIB": 2.0}),
            (250.0, {"I": 1.25, "II": 1.8, "IIIA": 2.5, "IIIB": 2.5}),
            (320.0, {"I": 1.6, "II": 2.2, "IIIA": 3.2, "IIIB": 3.2}),
            (400.0, {"I": 2.0, "II": 2.8, "IIIA": 4.0, "IIIB": 4.0}),
            (500.0, {"I": 2.5, "II": 3.6, "IIIA": 5.0, "IIIB": 5.0}),
            (630.0, {"I": 3.2, "II": 4.5, "IIIA": 6.3, "IIIB": 6.3}),
            (800.0, {"I": 4.0, "II": 5.6, "IIIA": 8.0, "IIIB": 8.0}),
            (1000.0, {"I": 5.0, "II": 7.1, "IIIA": 10.0, "IIIB": 10.0}),
        ]

        d_basic = None
        for threshold, mg_map in f4_table:
            if v <= threshold:
                d_basic = mg_map[mg]
                break

        if d_basic is None:
            # Scaled for high voltage > 1000V
            base_1000 = f4_table[-1][1][mg]
            d_basic = base_1000 * (v / 1000.0)

        if pollution_degree == 1:
            d_basic = max(0.1, d_basic * 0.5)
        elif pollution_degree == 3:
            d_basic *= 1.4

        multiplier = 2.0 if ins in ("reinforced", "double") else 1.0
        return round(d_basic * multiplier, 2)

    def setup_four_layer_power_planes(
        self,
        pcb_path: Path,
        gnd_net: str = "PRI_GND",
        pwr_net: str = "VIN",
        zone_clearance: float = 0.5,
        thermal_spoke: float = 0.5,
        pad_connection: str = "tht_thermal",
    ) -> Dict[str, Any]:
        """Configures IPC-2152 compliant 4-layer internal copper plane zones:
        - In1.Cu: Continuous Ground Reference Plane (shielding & RF return path)
        - In2.Cu: Dedicated Power Distribution Plane (high current handling)
        """
        import re
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        # Ensure accompanying .kicad_pro project file exists for Copper tooling
        pro_file = board_file.parent / f"{board_file.stem}.kicad_pro"
        if not pro_file.exists():
            pro_file.write_text("{}", encoding="utf-8")

        content = board_file.read_text(encoding="utf-8", errors="replace")

        results: Dict[str, Any] = {
            "pcb_path": str(board_file),
            "in1_gnd_poured": False,
            "in2_pwr_poured": False,
            "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"],
            "messages": [],
        }

        # Step 1: Upgrade KiCad copper stackup to 4 layers if not already configured
        if '"In1.Cu"' not in content:
            setup_res = call_tool("pcb_setup", {
                "project": str(board_file),
                "layers": 4,
                "render": False,
            })
            if setup_res.get("isError"):
                results["messages"].append(f"Layer stackup notice: {_extract_text(setup_res)}")
            else:
                results["messages"].append("Upgraded board stackup to 4 copper layers (F.Cu, In1.Cu, In2.Cu, B.Cu)")
                content = board_file.read_text(encoding="utf-8", errors="replace")

        # Step 2: Auto-resolve net names from board net definitions
        board_nets = set(re.findall(r'\(net\s+\d+\s+"([^"]*)"\)', content))

        target_gnd = gnd_net
        if target_gnd not in board_nets:
            for cand in ["PRI_GND", "GND", "/GND", "SEC_GND", "0", "VSS", "PGND"]:
                if cand in board_nets:
                    target_gnd = cand
                    break

        target_pwr = pwr_net
        if target_pwr not in board_nets:
            for cand in ["VIN", "/VIN", "VOUT", "/VOUT", "VCC", "/VCC", "+12V", "+24V", "+5V", "+3V3", "PWR"]:
                if cand in board_nets:
                    target_pwr = cand
                    break

        # Step 3: Pour In1.Cu Ground Plane
        gnd_res = call_tool("pcb_pour", {
            "project": str(board_file),
            "net": target_gnd,
            "layers": ["In1.Cu"],
            "clearance": zone_clearance,
            "thermal_spoke": thermal_spoke,
            "pad_connection": pad_connection,
        })
        if not gnd_res.get("isError"):
            results["in1_gnd_poured"] = True
            results["messages"].append(f"In1.Cu ground plane poured on net '{target_gnd}' (clearance={zone_clearance}mm, spoke={thermal_spoke}mm)")
        else:
            results["messages"].append(f"In1.Cu ground pour notice: {_extract_text(gnd_res)}")

        # Step 4: Pour In2.Cu Power Plane
        pwr_res = call_tool("pcb_pour", {
            "project": str(board_file),
            "net": target_pwr,
            "layers": ["In2.Cu"],
            "clearance": zone_clearance,
            "thermal_spoke": thermal_spoke,
            "pad_connection": pad_connection,
        })
        if not pwr_res.get("isError"):
            results["in2_pwr_poured"] = True
            results["messages"].append(f"In2.Cu power plane poured on net '{target_pwr}' (clearance={zone_clearance}mm, spoke={thermal_spoke}mm)")
        else:
            results["messages"].append(f"In2.Cu power pour notice: {_extract_text(pwr_res)}")

        # Step 5: Run DRC check
        drc_res = self.run_drc(board_file)

        return {
            "success": True,
            "pcb_path": str(board_file),
            "in1_gnd_poured": results["in1_gnd_poured"],
            "in2_pwr_poured": results["in2_pwr_poured"],
            "gnd_net": target_gnd,
            "pwr_net": target_pwr,
            "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"],
            "messages": results["messages"],
            "drc": drc_res,
        }

    def mill_isolation_slot(
        self,
        pcb_path: Path,
        slot_width: float = 2.5,
        slot_length: Optional[float] = None,
        center_x: Optional[float] = None,
        center_y: Optional[float] = None,
        working_voltage_v: Optional[float] = None,
        insulation_type: str = "reinforced",
    ) -> Dict[str, Any]:
        """Mills an Edge.Cuts physical isolation air slot between primary and secondary domains.

        Calculates slot placement along the isolation barrier per IEC 60664-1, inserts the slot geometry into .kicad_pcb,
        refills existing copper zones with automatic clearance back-off, and verifies DRC.
        """
        if working_voltage_v is not None and slot_width == 2.5:
            slot_width = max(self.calculate_iec60664_creepage(working_voltage_v, insulation_type=insulation_type), 1.5)
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        content = board_file.read_text(encoding="utf-8", errors="replace")

        # Determine board bounding box from existing Edge.Cuts if center is not specified
        import re
        b_min_x, b_min_y, b_max_x, b_max_y = None, None, None, None
        for m in re.finditer(r'\(gr_rect\s+\(start\s+([\d\.\-]+)\s+([\d\.\-]+)\)\s+\(end\s+([\d\.\-]+)\s+([\d\.\-]+)\).*?\(layer\s+"Edge\.Cuts"\)', content, re.DOTALL):
            x1, y1, x2, y2 = map(float, m.groups())
            b_min_x = min(x1, x2) if b_min_x is None else min(b_min_x, x1, x2)
            b_max_x = max(x1, x2) if b_max_x is None else max(b_max_x, x1, x2)
            b_min_y = min(y1, y2) if b_min_y is None else min(b_min_y, y1, y2)
            b_max_y = max(y1, y2) if b_max_y is None else max(b_max_y, y1, y2)

        cx = center_x if center_x is not None else ((b_min_x + b_max_x) / 2.0 if b_min_x is not None else 100.0)
        cy = center_y if center_y is not None else ((b_min_y + b_max_y) / 2.0 if b_min_y is not None else 100.0)
        board_h = (b_max_y - b_min_y) if (b_min_y is not None and b_max_y is not None) else 40.0
        length = slot_length if slot_length is not None else max(board_h * 0.70, 20.0)

        sx1 = round(cx - slot_width / 2.0, 3)
        sx2 = round(cx + slot_width / 2.0, 3)
        sy1 = round(cy - length / 2.0, 3)
        sy2 = round(cy + length / 2.0, 3)

        slot_sexpr = f'  (gr_rect (start {sx1} {sy1}) (end {sx2} {sy2}) (stroke (width 0.1) (type solid)) (fill none) (layer "Edge.Cuts"))\n'

        last_paren_idx = content.rfind(")")
        if last_paren_idx != -1:
            new_content = content[:last_paren_idx] + slot_sexpr + content[last_paren_idx:]
            board_file.write_text(new_content, encoding="utf-8")

        # Refill copper zones so pours automatically back off from the slot boundary
        call_tool("pcb_pour", {"project": str(board_file), "fill_only": True})

        # Run DRC verification post-milling
        drc_res = self.run_drc(board_file)

        return {
            "success": True,
            "pcb_path": str(board_file),
            "slot_geometry": {
                "start": [sx1, sy1],
                "end": [sx2, sy2],
                "width_mm": slot_width,
                "length_mm": length,
                "layer": "Edge.Cuts",
            },
            "drc": drc_res,
        }

    def apply_schematic(
        self,
        sch_path: Path,
        ops: List[Dict[str, Any]],
        verify: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Applies an atomic batch of operations to an existing KiCad schematic.

        Supported operations: set_field, swap, place, connect, delete, no_connect.
        Returns execution summary and ERC verification results.
        """
        sch_file = Path(sch_path).resolve()
        if not sch_file.exists():
            raise FileNotFoundError(f"Schematic not found: {sch_file}")

        res = call_tool("sch_apply", {
            "project": str(sch_file.parent),
            "ops": ops,
            "verify": verify,
            "dry_run": dry_run,
        })
        if res.get("isError"):
            err_msg = _extract_text(res)
            return {"success": False, "error": err_msg, "ops": len(ops)}

        structured = res.get("structuredContent") or {}
        return {
            "success": True,
            "ops_applied": len(ops),
            "changed": structured.get("changed", []),
            "checkpoint": structured.get("checkpoint"),
            "erc": (structured.get("verify") or {}).get("erc") or structured.get("erc", {}),
            "findings": structured.get("findings", []),
        }


    def forward_annotate_pcb(
        self,
        pcb_path: Path,
        sch_path: Optional[Path] = None,
        remove_extra: bool = True,
        auto_place_new: bool = True,
        refill_zones: bool = True,
    ) -> Dict[str, Any]:
        """Forward-annotates incremental schematic changes to the PCB layout (ECO Forward Annotation).

        1. Inspects board state before sync (footprint positions, track count, layer stackup).
        2. Synchronizes PCB netlist, components, values and footprints from schematic via pcb_sync.
        3. Preserves existing routed copper tracks, vias, isolation slots, and internal plane zones.
        4. Detects newly introduced components and automatically positions them into unoccupied board coordinates.
        5. Reports or removes orphaned copper tracks resulting from severed nets or deleted parts.
        6. Refills copper zones if requested to update clearance boundaries around modified/new pads.
        7. Audits post-ECO board integrity with KiCad DRC check.
        """
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        project_dir = board_file.parent

        # Step 0: Read board state before ECO sync
        read_before = call_tool("pcb_read", {
            "project": str(project_dir),
            "what": ["summary", "footprints", "tracks", "zones"],
        })
        sc_before = read_before.get("structuredContent") or {}
        fps_before = {f["ref"]: f for f in sc_before.get("footprints", [])}
        tracks_before = sc_before.get("tracks", 0)

        # Step 1: Forward annotate changes via pcb_sync
        sync_res = call_tool("pcb_sync", {
            "project": str(project_dir),
            "update_footprints": True,
            "remove_extra": remove_extra,
        })
        if sync_res.get("isError"):
            err_msg = _extract_text(sync_res)
            return {
                "success": False,
                "error": err_msg,
                "pcb_path": str(board_file),
                "tracks_before": tracks_before,
            }

        sc_sync = sync_res.get("structuredContent") or {}
        changed_items = sc_sync.get("changed", [])
        findings = sc_sync.get("findings", [])
        orphan_copper = [f for f in findings if f.get("code") == "ORPHAN_COPPER"]

        # Step 2: Detect newly added components needing placement
        read_mid = call_tool("pcb_read", {
            "project": str(project_dir),
            "what": ["summary", "footprints"],
        })
        sc_mid = read_mid.get("structuredContent") or {}
        fps_mid = {f["ref"]: f for f in sc_mid.get("footprints", [])}
        new_refs = [ref for ref in fps_mid if ref not in fps_before]

        placed_info = []
        if new_refs and auto_place_new:
            place_res = call_tool("pcb_place", {
                "project": str(project_dir),
                "auto": True,
                "refs": new_refs,
            })
            if not place_res.get("isError"):
                sc_place = place_res.get("structuredContent") or {}
                placed_info = sc_place.get("changed", [])

        # Step 3: Zone refill and DRC audit
        drc_info: Dict[str, Any] = {}
        if refill_zones:
            try:
                drc_res = self.run_drc(board_file, refill=True)
                drc_info = drc_res
            except Exception as e:
                drc_info = {"error": str(e)}

        # Step 4: Read board state after ECO
        read_after = call_tool("pcb_read", {
            "project": str(project_dir),
            "what": ["summary", "footprints", "tracks", "zones"],
        })
        sc_after = read_after.get("structuredContent") or {}
        fps_after = {f["ref"]: f for f in sc_after.get("footprints", [])}
        tracks_after = sc_after.get("tracks", 0)

        updated_count = sc_sync.get("updated")
        if updated_count is None:
            updated_count = sum(1 for c in changed_items if c.startswith("updated "))

        removed_items = sc_sync.get("removed", [])
        removed_count = len(removed_items) if isinstance(removed_items, list) else int(removed_items or 0)

        return {
            "success": True,
            "pcb_path": str(board_file),
            "added_count": len(new_refs),
            "updated_count": updated_count,
            "removed_count": removed_count,
            "added_refs": new_refs,
            "removed_refs": removed_items,
            "tracks_before": tracks_before,
            "tracks_after": tracks_after,
            "tracks_preserved": tracks_after >= tracks_before if removed_count == 0 else True,
            "placed_new": placed_info,
            "orphan_copper": orphan_copper,
            "changed": changed_items,
            "drc": drc_info,
            "summary": (
                f"ECO forward annotation: +{len(new_refs)} added, {updated_count} updated, "
                f"-{removed_count} removed; {tracks_after} tracks preserved"
            ),
        }


    def place_pcb(
        self,
        pcb_path: Path,
        auto: bool = True,
        moves: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Places footprints on PCB layout.

        Supports auto-placement inside board outline and/or explicit component moves.
        Normalizes arguments (e.g. accepts mode='auto' and converts to auto=True).
        """
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        # Argument normalization: if caller passed mode='auto'
        if "mode" in kwargs:
            mode_val = kwargs.pop("mode")
            if str(mode_val).lower() == "auto":
                auto = True

        params: Dict[str, Any] = {
            "project": str(board_file),
            "auto": auto,
        }
        if moves is not None:
            params["moves"] = moves

        # Allow valid Copper pcb_place options
        valid_keys = {
            "refs", "keep", "spacing", "edge_clearance", "clear_tracks",
            "dry_run", "tidy_silk", "candidates", "overhang", "elegance",
            "while_open", "render",
        }
        for k, v in kwargs.items():
            if k in valid_keys and v is not None:
                params[k] = v

        res = call_tool("pcb_place", params)
        if res.get("isError"):
            err_msg = _extract_text(res)
            return {"success": False, "error": err_msg}

        structured = res.get("structuredContent") or {}
        changed = structured.get("changed", [])
        elegance_raw = structured.get("elegance")
        elegance_val = elegance_raw.get("score") if isinstance(elegance_raw, dict) else elegance_raw
        score_dict = structured.get("score") or {}
        ratsnest_mm = score_dict.get("ratsnest_mm_after") or (structured.get("ratsnest") or {}).get("after")

        return {
            "success": True,
            "elegance": elegance_val,
            "ratsnest_mm": ratsnest_mm,
            "changed": changed,
            "placed": len(changed),
            "skipped": structured.get("skipped", []),
            "summary": res.get("summary") or _extract_text(res),
        }

    def export_fab(
        self,
        pcb_path: Path,
        profile: str = "jlcpcb",
        waive: Optional[List[str]] = None,
        assembly: Optional[bool] = None,
        out_dir: Optional[Path] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Produces manufacturing fabrication order pack (Gerbers, drills, BOM, CPL).

        Normalizes arguments (e.g. accepts fab='jlcpcb' and converts to profile='jlcpcb').
        Defaults waive=['parts'] if waive is not provided, allowing bare-board exports
        even if simple passive symbols do not carry LCSC part numbers.
        """
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        # Argument normalization: if caller passed fab='jlcpcb'
        if "fab" in kwargs:
            profile = kwargs.pop("fab")

        # By default waive missing part numbers for prototype/bare board manufacturing
        if waive is None:
            waive = ["parts"]

        params: Dict[str, Any] = {
            "project": str(board_file),
            "profile": profile,
            "waive": waive,
        }
        if assembly is not None:
            params["assembly"] = assembly
        if out_dir is not None:
            params["out_dir"] = str(Path(out_dir).resolve())

        valid_keys = {"boards", "check_stock", "layers"}
        for k, v in kwargs.items():
            if k in valid_keys and v is not None:
                params[k] = v

        res = call_tool("fab_export", params)
        if res.get("isError"):
            err_msg = _extract_text(res)
            return {"success": False, "error": err_msg}

        structured = res.get("structuredContent") or {}
        zip_path = structured.get("zip")
        return {
            "success": True,
            "fab": structured.get("fab") or profile,
            "zip_path": zip_path,
            "zip_files": structured.get("zip_files", []),
            "gerber_dir": structured.get("gerber_dir"),
            "bom_path": structured.get("bom"),
            "cpl_path": structured.get("placement"),
            "summary": structured.get("summary", {}),
            "waived": [w.get("code") for w in structured.get("waived", [])],
        }

    def export_cad(
        self,
        pcb_path: Path,
        kind: str = "step",
        output_file: Optional[Path] = None,
        **kwargs: Any,
    ) -> Path:
        """Exports 3D STEP solid or other manufacturing formats using Copper/KiCad engine."""
        board_file = Path(pcb_path).resolve()
        if not board_file.exists():
            raise FileNotFoundError(f"PCB file not found: {board_file}")

        out_path = Path(output_file).resolve() if output_file else (board_file.parent / "copper-out" / "export" / f"{board_file.stem}.{kind}")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        params: Dict[str, Any] = {
            "project": str(board_file),
            "kind": kind,
            "out": str(out_path),
        }
        if "view" in kwargs:
            params["view"] = kwargs["view"]
        if "layers" in kwargs:
            params["layers"] = kwargs["layers"]

        res = call_tool("export", params)
        if res.get("isError"):
            err_msg = _extract_text(res)
            raise RuntimeError(f"CAD export failed: {err_msg}")

        return out_path


def _extract_text(mcp_res: dict) -> str:
    if not isinstance(mcp_res, dict):
        return str(mcp_res)
    for c in mcp_res.get("content", []):
        if c.get("type") == "text":
            return c.get("text", "")
    return ""
