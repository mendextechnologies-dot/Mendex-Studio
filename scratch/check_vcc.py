import re
from pathlib import Path

pcb = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_pcb').read_text(encoding='utf-8')
matches = re.findall(r'\(net\s+\d*\s*"([^"]*VCC[^"]*)"\)', pcb)
print('matches in pcb:', set(matches))
