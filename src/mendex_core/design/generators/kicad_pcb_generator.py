"""Populated KiCad PCB Generator for Mendex Engineering Studio v2.0.

Compiles Design Intermediate Representation (IR) into a populated KiCad .kicad_pcb
file with board boundaries (Edge.Cuts), component footprints, netlist connectivity,
and design rules conforming to KiCad 7/8/9/10 syntax.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
from uuid import uuid4

from ..ir import DesignIntermediateRepresentation, ComponentType


class KiCadPCBGenerator:
    """Generates populated KiCad 9/10 .kicad_pcb board files from Design IR."""

    @staticmethod
    def generate_pcb_sexpr(
        ir: DesignIntermediateRepresentation,
        board_width_mm: float = 60.0,
        board_height_mm: float = 45.0,
    ) -> str:
        """Generates populated KiCad PCB layout S-expression with valid net connectivity."""
        lines = [
            '(kicad_pcb (version 20240108) (generator "Mendex Studio v2.1") (generator_version "2.1.0")',
            '  (general (thickness 1.6))',
            '  (paper "A4")',
            '  (layers',
            '    (0 "F.Cu" signal)',
            '    (31 "B.Cu" signal)',
            '    (36 "B.SilkS" user "B.Silkscreen")',
            '    (37 "F.SilkS" user "F.Silkscreen")',
            '    (38 "B.Mask" user)',
            '    (39 "F.Mask" user)',
            '    (44 "Edge.Cuts" user)',
            '    (48 "B.Fab" user)',
            '    (49 "F.Fab" user)',
            '  )',
            '  (setup',
            '    (pad_to_mask_clearance 0.05)',
            '    (pcbplotparams (usegerberextensions yes) (usegerberattributes yes) (creategerberjobfile yes))',
            '  )',
        ]

        # Net definitions
        lines.append('  (net 0 "")')
        net_name_to_id: Dict[str, int] = {"": 0}
        for i, net in enumerate(ir.nets):
            net_id = i + 1
            net_name_to_id[net.name] = net_id
            lines.append(f'  (net {net_id} "{net.name}")')

        # Map component pins to (net_id, net_name)
        comp_pin_to_net: Dict[Tuple[str, str], Tuple[int, str]] = {}
        for net_id, net in enumerate(ir.nets, start=1):
            for conn in net.connections:
                comp_pin_to_net[(conn.component_id, str(conn.pin_id))] = (net_id, net.name)

        # Board Boundary Outline on Edge.Cuts
        origin_x = 100.0
        origin_y = 100.0
        x2 = origin_x + board_width_mm
        y2 = origin_y + board_height_mm

        lines.extend([
            f'  (gr_rect (start {origin_x:.2f} {origin_y:.2f}) (end {x2:.2f} {y2:.2f}) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts") (uuid "{uuid4()}"))',
        ])

        # High-voltage isolation barrier milling slot (IEC-61010-1: 5.0 mm clearance)
        has_hv = any(c.type == ComponentType.TRANSFORMER for c in ir.components) or any("VOUT" in n.name for n in ir.nets)
        if has_hv:
            slot_x1 = origin_x + board_width_mm * 0.48
            slot_x2 = slot_x1 + 5.0
            slot_y1 = origin_y + 4.0
            slot_y2 = origin_y + board_height_mm - 4.0
            lines.append(
                f'  (gr_rect (start {slot_x1:.2f} {slot_y1:.2f}) (end {slot_x2:.2f} {slot_y2:.2f}) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts") (uuid "{uuid4()}"))'
            )

        # Place footprints inside the board boundary
        grid_start_x = origin_x + 10.0
        grid_start_y = origin_y + 10.0
        spacing_x = 14.0
        spacing_y = 14.0

        for idx, comp in enumerate(ir.components):
            fp_uuid = str(uuid4())
            fx = grid_start_x + (idx % 4) * spacing_x
            fy = grid_start_y + (idx // 4) * spacing_y

            fp_name = comp.footprint or "Resistor_SMD:R_0805_2012Metric"
            lines.extend([
                f'  (footprint "{fp_name}" (layer "F.Cu") (uuid "{fp_uuid}") (at {fx:.2f} {fy:.2f})',
                f'    (property "Reference" "{comp.designator}" (at 0 -2 0) (layer "F.SilkS") (uuid "{uuid4()}"))',
                f'    (property "Value" "{comp.name}" (at 0 2 0) (layer "F.Fab") (uuid "{uuid4()}"))',
            ])

            # Generate pads with valid (net <id> "<name>") S-expression syntax
            pad_offsets = [(-0.95, 0.0), (0.95, 0.0), (0.0, 1.2), (0.0, -1.2)]
            pins = comp.pins if comp.pins else []
            if not pins:
                # Default 2-pin SMD
                pin_ids = ["1", "2"]
            else:
                pin_ids = [str(p.pin_id) for p in pins]

            for p_idx, pid in enumerate(pin_ids):
                net_info = comp_pin_to_net.get((comp.id, pid), (0, ""))
                net_expr = f'(net {net_info[0]} "{net_info[1]}")' if net_info[0] > 0 else '(net 0 "")'
                ox, oy = pad_offsets[p_idx % len(pad_offsets)]
                lines.append(
                    f'    (pad "{pid}" smd roundrect (at {ox:.2f} {oy:.2f}) (size 1.0 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) {net_expr})'
                )

            lines.append('  )')

        lines.append(")")
        return "\n".join(lines) + "\n"

    @staticmethod
    def export_pcb(
        ir: DesignIntermediateRepresentation,
        output_pcb_path: Path,
        board_width_mm: float = 60.0,
        board_height_mm: float = 45.0,
    ) -> Path:
        """Writes populated .kicad_pcb file to disk."""
        output_pcb_path.parent.mkdir(parents=True, exist_ok=True)
        content = KiCadPCBGenerator.generate_pcb_sexpr(
            ir, board_width_mm=board_width_mm, board_height_mm=board_height_mm
        )
        output_pcb_path.write_text(content, encoding="utf-8")
        return output_pcb_path
