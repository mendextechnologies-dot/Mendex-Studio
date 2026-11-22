"""Disposable data + real stdio desktop bridge for React workflow regression."""
import argparse
import json
from pathlib import Path

from mendex_core.desktop.__main__ import serve
from mendex_core.desktop.service import DesktopService
from mendex_core.pcb import file_hash
from mendex_core.service import StudioService
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.root.exists():
        raise ValueError("Fixture root must not exist")
    studio = StudioService(args.root)
    try:
        product = studio.create_product("LAYOUT-UI", "Synthetic placement UI fixture", "pcb", "Software test")
        revision = studio.get_revision(product.active_revision_id)
        path = studio.workspace_path(revision) / "pcb/fixture.kicad_pcb"
        footprints = []
        for ref, x, locked in (("U1", 10, False), ("R1", 30, False), ("J1", 40, True)):
            footprints.append(f'''(footprint "Synthetic:{ref}" {"locked" if locked else ""}
              (layer "F.Cu") (at {x} 20) (property "Reference" "{ref}")
              (fp_rect (start -1 -1) (end 1 1) (layer "F.CrtYd"))
              (pad "1" smd rect (at 0 0) (size 1 1) (layers "F.Cu") (net 1 "SYNTHETIC")))''')
        path.write_text('(kicad_pcb (version 20250114) (net 1 "SYNTHETIC") '
                        '(gr_rect (start 0 0) (end 50 40) (layer "Edge.Cuts")) '
                        + ' '.join(footprints) + ')', encoding="utf-8")
        empty = studio.create_product("LAYOUT-EMPTY", "Empty revision fixture", "pcb", "Software test")
        print(json.dumps({"revision_id": str(revision.revision_id), "empty_revision_id": str(empty.active_revision_id),
                          "board_path": str(path), "source_sha256": file_hash(path)}), flush=True)
        serve(DesktopService(studio), sys.stdin, sys.stdout)
    finally:
        studio.integrations.shutdown()


if __name__ == "__main__":
    main()
