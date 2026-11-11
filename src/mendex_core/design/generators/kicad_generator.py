"""KiCad 9 schematic and project generator from Design Intermediate Representation (IR).

Translates Design IR into valid, editable KiCad .kicad_sch and .kicad_pro files
ready for inspection in Eeschema and verification via kicad-cli sch erc.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from ..ir import DesignIntermediateRepresentation, ComponentType


class KiCadSchematicGenerator:
    """Generates editable KiCad 9 schematic and project files from Design IR."""

    @staticmethod
    def generate_schematic_sexpr(ir: DesignIntermediateRepresentation) -> str:
        """Generates valid KiCad 9 S-expression schematic string."""
        sch_uuid = str(uuid4())
        lines = [
            f'(kicad_sch (version 20231120) (generator "Mendex Studio v1.9") (generator_version "1.9.0") (uuid "{sch_uuid}")',
            '  (paper "A4")',
            '  (title_block',
            f'    (title "{ir.title}")',
            f'    (comment 1 "Topology: {ir.topology}")',
            '    (comment 2 "Generated from Mendex Design Intermediate Representation")',
            '  )',
        ]

        # Coordinates layout grid (X, Y)
        curr_x = 50.8
        curr_y = 50.8
        step_x = 35.0

        # Symbols representation
        for i, comp in enumerate(ir.components):
            sym_uuid = str(uuid4())
            x = curr_x + (i % 4) * step_x
            y = curr_y + (i // 4) * 35.0
            
            lib_id = "Device:R"
            if comp.type == ComponentType.CAPACITOR:
                lib_id = "Device:C"
            elif comp.type == ComponentType.INDUCTOR:
                lib_id = "Device:L"
            elif comp.type == ComponentType.DIODE:
                lib_id = "Device:D"
            elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN):
                lib_id = "Device:Q_NMOS_DGS"
            elif comp.type == ComponentType.TRANSFORMER:
                lib_id = "Device:Transformer_1P_1S"
            elif comp.type == ComponentType.VOLTAGE_SOURCE:
                lib_id = "Simulation_SPICE:VDC"

            footprint_val = comp.footprint or ""
            lines.extend([
                f'  (symbol (lib_id "{lib_id}") (at {x:.2f} {y:.2f} 0) (unit 1)',
                f'    (in_bom yes) (on_board yes) (uuid "{sym_uuid}")',
                f'    (property "Reference" "{comp.designator}" (at {x:.2f} {y - 5.0:.2f} 0))',
                f'    (property "Value" "{comp.name}" (at {x:.2f} {y + 5.0:.2f} 0))',
                f'    (property "Footprint" "{footprint_val}" (at {x:.2f} {y:.2f} 0) (effects (hide yes)))',
                '  )',
            ])

        # Net labels
        for i, port in enumerate(ir.ports):
            port_uuid = str(uuid4())
            px = 30.0
            py = 40.0 + i * 15.0
            lines.append(f'  (hierarchical_label "{port.name}" (shape input) (at {px:.2f} {py:.2f} 180) (uuid "{port_uuid}"))')

        lines.append(")")
        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_project_json(title: str) -> str:
        """Generates standard KiCad 9 .kicad_pro file JSON."""
        pro_dict = {
            "board": {
                "design_settings": {
                    "defaults": {
                        "track_width": 0.25,
                        "clearance": 0.2,
                    }
                }
            },
            "meta": {
                "filename": f"{title}.kicad_pro",
                "version": 1
            },
            "schematic": {
                "annotate_start_num": 1,
                "drawing": {
                    "dashed_lines_dash_length_ratio": 12.0,
                    "dashed_lines_gap_length_ratio": 3.0
                }
            }
        }
        return json.dumps(pro_dict, indent=2)

    @staticmethod
    def export_project(ir: DesignIntermediateRepresentation, target_dir: Path) -> Dict[str, Path]:
        """Exports complete KiCad project files into destination directory."""
        target_dir.mkdir(parents=True, exist_ok=True)
        base_name = ir.title.lower().replace(" ", "_").replace("-", "_")

        sch_path = target_dir / f"{base_name}.kicad_sch"
        pro_path = target_dir / f"{base_name}.kicad_pro"

        sch_path.write_text(KiCadSchematicGenerator.generate_schematic_sexpr(ir), encoding="utf-8")
        pro_path.write_text(KiCadSchematicGenerator.generate_project_json(ir.title), encoding="utf-8")

        return {
            "schematic": sch_path,
            "project": pro_path,
        }
