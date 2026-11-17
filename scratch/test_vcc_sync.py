import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
import tempfile, shutil
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService

src_dir = Path('products/8f697275-3a8d-456c-ae20-138a7698df61/revisions/9b7c1396-64da-41f8-8649-77dc0f24e103/pcb')
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    for f in src_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, tmp / f.name)
    pcb_f = tmp / 'sv1000.kicad_pcb'
    pcb_txt = pcb_f.read_text(encoding='utf-8')
    pcb_txt = pcb_txt.replace('"VCC"', '"/VCC"')
    pcb_f.write_text(pcb_txt, encoding='utf-8')
    
    ks = KiCadLifecycleService()
    res_eco = ks.forward_annotate_pcb(tmp / 'sv1000.kicad_pcb', tmp / 'sv1000.kicad_sch')
    print('res_eco success:', res_eco.get('success'))
    print('tracks preserved:', res_eco.get('tracks_preserved'))
    print('tracks before:', res_eco.get('tracks_before'), 'after:', res_eco.get('tracks_after'))
    print('drc errors:', res_eco.get('drc', {}).get('drc', {}).get('errors'))
    print('unconnected:', res_eco.get('drc', {}).get('drc', {}).get('unconnected'))
