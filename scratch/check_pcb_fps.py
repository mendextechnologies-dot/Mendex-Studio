import re
from pathlib import Path

pcb = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_pcb').read_text(encoding='utf-8')
fps = re.findall(r'\(footprint\s+"([^"]+)".*?\(property\s+"Reference"\s+"([^"]+)"', pcb, re.DOTALL)
for fp, ref in sorted(fps, key=lambda x: x[1]):
    if ref in ['CSNUB', 'DAUX', 'RSNUB', 'RGATE', 'T1', 'CIN', 'COUT', 'U1', 'U2', 'Q1']:
        print(f'{ref:10} | PCB: {fp}')
