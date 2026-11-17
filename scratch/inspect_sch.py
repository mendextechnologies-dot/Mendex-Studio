import re
from pathlib import Path

sch = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_sch').read_text(encoding='utf-8')
symbols = re.findall(r'\(symbol\s+\(lib_id\s+"([^"]+)".*?\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Value"\s+"([^"]+)"', sch, re.DOTALL)
for lib, ref, val in sorted(symbols, key=lambda x: x[1]):
    print(f'{ref:10} | {val:20} | {lib}')
