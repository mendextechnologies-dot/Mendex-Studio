import sys
from pathlib import Path

# Add root and src to path
sys.path.insert(0, str(Path(".").resolve()))
sys.path.insert(0, str(Path("src").resolve()))

from mendex_core.design.generators.kicad_generator import (
    KiCadSchematicGenerator,
    mendex_ir_to_copper_ops,
)
from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
from tests.core.test_sv1000_p0_schematic import build_complete_sv1000_ir

sv1000_pcb_dir = Path("products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb")
sch_file = sv1000_pcb_dir / "sv1000.kicad_sch"
pcb_file = sv1000_pcb_dir / "sv1000.kicad_pcb"
pro_file = sv1000_pcb_dir / "sv1000.kicad_pro"

print("Target schematic:", sch_file)

# 1. Reset schematic to empty template so Copper can place all 28 parts with clean atomic batch
blank_sch = """(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "347babe6-ba36-4c63-8ad6-bbc5b9273490")
\t(paper "A4")
\t(title_block
\t\t(title "SpectraVolt SV-1000 Precision High-Voltage Converter")
\t\t(comment 1 "Topology: Quasi-Resonant Flyback")
\t\t(comment 2 "Generated from Mendex Design Intermediate Representation")
\t)
\t(lib_symbols)
)
"""
sch_file.write_text(blank_sch, encoding="utf-8")

# 2. Build complete IR
ir = build_complete_sv1000_ir()
ops = mendex_ir_to_copper_ops(ir)
print(f"Generated {len(ops)} declarative Copper operations")

# 3. Apply to sv1000.kicad_sch via CopperKiCadAdapter
adapter = CopperKiCadAdapter()
apply_res = adapter.apply_schematic(sch_file, ops, verify=True)
print("Apply result success:", apply_res.get("success"))
print("Apply result ops_applied:", apply_res.get("ops_applied"))

# 4. Verify ERC
erc = adapter.run_erc(sch_file)
print("ERC result:", erc.get("erc"))

# 5. Inspect schematic content
sch_text = sch_file.read_text(encoding="utf-8")
import re
wires = len(re.findall(r'\(wire\s+', sch_text))
labels = re.findall(r'\(label\s+"([^"]+)"', sch_text)
symbols = re.findall(r'\(property "Reference" "([^"]+)"', sch_text)
print(f"Schematic now contains: {len(symbols)} symbols, {wires} wires, {len(labels)} net labels")
print(f"Symbols ({len(symbols)}): {symbols}")
print(f"Labels ({len(labels)}): {labels[:10]}...")
