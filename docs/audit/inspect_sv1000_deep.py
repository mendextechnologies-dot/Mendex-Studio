from pathlib import Path
import json
import re

ws = Path("products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103")

print("=== 1. SCHEMATIC INSPECTION ===")
sch_file = ws / "pcb/sv1000.kicad_sch"
sch_text = sch_file.read_text(encoding="utf-8")
print(f"Schematic file: {sch_file} ({len(sch_text)} bytes)")
refs = re.findall(r'\(property "Reference" "([^"]+)"', sch_text)
vals = re.findall(r'\(property "Value" "([^"]+)"', sch_text)
fps = re.findall(r'\(property "Footprint" "([^"]+)"', sch_text)
print("Symbols in schematic:")
for r, v, f in zip(refs, vals, fps):
    print(f"  {r}: {v} | Footprint: {f}")

nets = set(re.findall(r'\(net\s+\d+\s+"([^"]+)"\)', sch_text))
print(f"Nets in schematic: {nets}")

# Check wires / connections / pins
wires = len(re.findall(r'\(wire\s+', sch_text))
labels = re.findall(r'\(label\s+"([^"]+)"', sch_text)
hier_labels = re.findall(r'\(hierarchical_label\s+"([^"]+)"', sch_text)
global_labels = re.findall(r'\(global_label\s+"([^"]+)"', sch_text)
print(f"Wires count: {wires}, Labels: {labels}, Global labels: {global_labels}")

print("\n=== 2. PCB LAYOUT INSPECTION ===")
pcb_file = ws / "pcb/sv1000.kicad_pcb"
pcb_text = pcb_file.read_text(encoding="utf-8")
print(f"PCB file: {pcb_file} ({len(pcb_text)} bytes)")

# Layers
layers = re.findall(r'\(\d+\s+"([^"]+)"\s+(?:signal|power|user)\)', pcb_text)
print(f"PCB Layers: {layers}")

# Components on PCB
pcb_fps = re.findall(r'\(footprint\s+"([^"]+)"', pcb_text)
pcb_refs = re.findall(r'\(property "Reference"\s+"([^"]+)"', pcb_text)
print(f"Footprints count: {len(pcb_fps)}, References: {pcb_refs}")

# Tracks and Vias
tracks = len(re.findall(r'\(segment\s+', pcb_text))
vias = len(re.findall(r'\(via\s+', pcb_text))
zones = len(re.findall(r'\(zone\s+', pcb_text))
print(f"PCB Tracks: {tracks}, Vias: {vias}, Zones: {zones}")

# Edge.Cuts / Isolation slot
edge_cuts = re.findall(r'\(gr_\w+\s+.*?\(layer\s+"Edge\.Cuts"\)\)', pcb_text, re.DOTALL)
print(f"Edge.Cuts elements: {len(edge_cuts)}")
for ec in edge_cuts:
    print(f"  {ec[:120]}...")

# 3D models assigned
models = re.findall(r'\(model\s+"([^"]+)"', pcb_text)
print(f"3D models on PCB ({len(models)}): {models}")

print("\n=== 3. BOM INSPECTION ===")
bom_file = ws / "bom/bom.json"
if bom_file.exists():
    bom_data = json.loads(bom_file.read_text(encoding="utf-8"))
    print(f"BOM items count: {len(bom_data)}")
    for item in bom_data:
        print(f"  {item.get('reference')}: {item.get('value')} | MPN: {item.get('mpn')} | Pkg: {item.get('package')} | Footprint: {item.get('footprint')}")

print("\n=== 4. DRC AND ERC REPORTS ===")
drc_file = ws / "pcb/drc_report.json"
if drc_file.exists():
    drc_data = json.loads(drc_file.read_text(encoding="utf-8"))
    print(f"DRC Report: violations={len(drc_data.get('violations', []))}, unconnected={len(drc_data.get('unconnected_items', []))}")
    if drc_data.get('violations'):
        print(f"  DRC violations: {drc_data.get('violations')[:5]}")

erc_file = ws / "pcb/erc_report.json"
if erc_file.exists():
    erc_data = json.loads(erc_file.read_text(encoding="utf-8"))
    print(f"ERC Report: errors={erc_data.get('error_count', 0)}, warnings={erc_data.get('warning_count', 0)}")
    if erc_data.get('sheets'):
        print(f"  ERC violations: {erc_data.get('sheets')[0].get('violations', [])[:5]}")

print("\n=== 5. LTSPICE SIMULATION ===")
net_file = ws / "simulations/flyback_circuit.net"
if net_file.exists():
    print(f"--- Netlist ({net_file}) ---")
    print(net_file.read_text(encoding="utf-8"))

log_file = ws / "simulations/flyback_circuit.log"
if log_file.exists():
    print(f"--- Log ({log_file}) ---")
    print(log_file.read_text(encoding="utf-8"))

print("\n=== 6. FEMM SIMULATION ===")
fem_lua = ws / "simulations/etd34_magnetics.lua"
if fem_lua.exists():
    print(f"--- Lua Script ({fem_lua}) ---")
    print(fem_lua.read_text(encoding="utf-8"))

fem_res = ws / "simulations/femm_results.txt"
if fem_res.exists():
    print(f"--- FEMM Results ({fem_res}) ---")
    print(fem_res.read_text(encoding="utf-8"))

print("\n=== 7. DETAILED SCHEMATIC SYMBOL AUDIT ===")
matches = re.finditer(r'\(symbol\s+\(lib_id "([^"]+)"\).*?\(property "Reference" "([^"]+)".*?\(property "Value" "([^"]+)".*?\(property "Footprint" "([^"]+)"', sch_text, re.DOTALL)
for m in matches:
    lib_id, ref, val, fp = m.groups()
    print(f"Ref: {ref:8s} | LibId: {lib_id:30s} | Footprint: {fp}")

print("\n=== 8. CHECK FOR CONNECTORS, CONTROLLER, GATE DRIVE ===")
# Check if there is an input connector (VIN, GND) or output connector (HV+, HV-)
print("Connectors on schematic:", [r for r in refs if r.startswith("J") or "CONN" in r])
print("Controller / PWM IC on schematic:", [r for r in refs if r.startswith("U")])
print("Gate driver on schematic:", [r for r in refs if "GATE" in r or "DRV" in r])
