import re
from pathlib import Path

sch = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_sch').read_text(encoding='utf-8')
pcb = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_pcb').read_text(encoding='utf-8')

sch_syms = re.findall(r'\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Footprint"\s+"([^"]+)"', sch, re.DOTALL)
sch_fps = {ref: fp for ref, fp in sch_syms if not ref.startswith('#')}

pcb_fps_raw = re.findall(r'\(footprint\s+"([^"]+)".*?\(property\s+"Reference"\s+"([^"]+)"', pcb, re.DOTALL)
pcb_fps = {ref: fp for fp, ref in pcb_fps_raw}

mismatches = []
for ref, sch_fp in sorted(sch_fps.items()):
    pcb_fp = pcb_fps.get(ref, 'MISSING')
    if sch_fp != pcb_fp:
        mismatches.append((ref, sch_fp, pcb_fp))

print(f"Total components checked: {len(sch_fps)}")
print(f"Footprint mismatches: {len(mismatches)}")
for ref, sch_fp, pcb_fp in mismatches:
    print(f"{ref:10} | SCH: {sch_fp:40} | PCB: {pcb_fp}")
