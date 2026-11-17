from pathlib import Path

pcb_path = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb/sv1000.kicad_pcb')
content = pcb_path.read_text(encoding='utf-8')
print('Count of "VCC":', content.count('"VCC"'))
print('Count of "/VCC":', content.count('"/VCC"'))

new_content = content.replace('"VCC"', '"/VCC"')
pcb_path.write_text(new_content, encoding='utf-8')
print('Updated sv1000.kicad_pcb successfully')
