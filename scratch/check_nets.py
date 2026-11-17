import re
from pathlib import Path

pcb = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_pcb').read_text(encoding='utf-8')
pcb_nets = set(re.findall(r'\(net\s+\d+\s+"([^"]+)"', pcb))
print('pcb nets:', sorted(pcb_nets))

sch = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_sch').read_text(encoding='utf-8')
sch_labels = set(re.findall(r'\(label\s+"([^"]+)"', sch))
sch_glabels = set(re.findall(r'\(global_label\s+"([^"]+)"', sch))
sch_hlabels = set(re.findall(r'\(hierarchical_label\s+"([^"]+)"', sch))
print('sch labels:', sorted(sch_labels | sch_glabels | sch_hlabels))
