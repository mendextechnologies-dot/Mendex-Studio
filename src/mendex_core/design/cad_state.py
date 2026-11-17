"""Shared CAD provenance, check normalization and candidate-bundle integrity."""
from __future__ import annotations
import hashlib
import json
import zipfile
from pathlib import Path
from uuid import uuid4


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hash(board):
    """Board plus project rules and schematic identity (none may silently change)."""
    board=Path(board)
    return hashlib.sha256(json.dumps({p.name:sha(p) for p in [board,board.with_suffix('.kicad_pro'),board.with_suffix('.kicad_sch')] if p.is_file()},sort_keys=True).encode()).hexdigest()


def drc_summary(value):
    raw=value
    for _ in range(3):
        if not isinstance(raw,dict):break
        if raw.get('isError') or raw.get('error'):raw=None;break
        if 'structuredContent' in raw:raw=raw['structuredContent']
        elif 'drc' in raw:raw=raw['drc']
        else:break
    unknown=dict(available=False,status='NOT_EVALUATED',errors=None,warnings=None,unconnected=None)
    if not isinstance(raw,dict):return unknown
    if "violations" in raw:
        violations = raw.get("violations", [])
        err_c = sum(1 for v in violations if v.get("severity") == "error")
        warn_c = sum(1 for v in violations if v.get("severity") == "warning")
        unconn_c = len(raw.get("unconnected_items", []))
        return dict(
            available=True,
            status="FAIL" if (err_c or unconn_c) else ("WARNINGS" if warn_c else "PASS"),
            errors=err_c,
            warnings=warn_c,
            unconnected=unconn_c,
        )
    counts=[raw.get('errors'),raw.get('warnings'),raw.get('unconnected',raw.get('unconnected_items'))]
    if any(type(v) is not int or v<0 for v in counts):return unknown
    errors,warnings,unconnected=counts
    return dict(available=True,status='FAIL' if errors or unconnected else ('WARNINGS' if warnings else 'PASS'),errors=errors,warnings=warnings,unconnected=unconnected)


def state_dir(studio, revision):
    return studio.root/'.mendex'/'cad-state'/str(revision.revision_id)


def save_check(studio, revision, board, check):
    target=state_dir(studio,revision);target.mkdir(parents=True,exist_ok=True)
    data=dict(source_hash=source_hash(board),specification=revision.specification.model_dump(mode='json'),check=check)
    text=json.dumps(data,sort_keys=True).encode()
    path=target/f'check-{uuid4().hex}.json';path.write_bytes(text)
    path.with_suffix('.sha256').write_text(hashlib.sha256(text).hexdigest(),encoding='ascii')


def read_check(studio, revision, board):
    board = Path(board)
    for p in sorted(state_dir(studio,revision).glob('check-*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        try:
            if sha(p)!=p.with_suffix('.sha256').read_text():continue
            d=json.loads(p.read_text())
            if d['source_hash']==source_hash(board) and d['specification']==revision.specification.model_dump(mode='json'):
                return d['check']
        except (OSError,ValueError,KeyError):continue
    for cand_name in ["drc_report.json", ".copper/drc.json"]:
        cand = board.parent / cand_name
        if cand.is_file() and cand.stat().st_size > 0:
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                summary = drc_summary(data)
                if summary["available"]:
                    return summary
            except Exception:
                pass
    return dict(available=False,status='NOT_EVALUATED',errors=None,warnings=None,unconnected=None,reason='No intact check for current board, rules, schematic and specification')


def enabled_copper(board):
    from .geometry import extract_pcb_geometry
    geom = extract_pcb_geometry(board)
    layers = geom.get('copper_layers', [])
    if not layers:
        used = set()
        for t in geom.get('tracks', []):
            if t.get('layer', '').endswith('.Cu'):
                used.add(t['layer'])
        for f in geom.get('footprints', []):
            for p in f.get('pads', []):
                for pl in p.get('layers', []):
                    if pl.endswith('.Cu'):
                        used.add(pl)
        layers = sorted(list(used)) if used else ['F.Cu']
    return layers


def validate_fabrication(folder, board):
    """Require every enabled copper layer, outline and a drill output if holes exist."""
    folder = Path(folder)
    missing = []
    from .geometry import extract_pcb_geometry
    geom = extract_pcb_geometry(board)
    required_layers = list(enabled_copper(board))
    if geom.get('edge_cuts'):
        required_layers.append('Edge.Cuts')
    for layer in required_layers:
        clean = layer.replace('.', '_')
        if not any(p.is_file() and p.stat().st_size and (p.name.endswith(f'-{clean}.gbr') or p.name.endswith(f'_{clean}.gbr') or clean.lower() in p.name.lower()) for p in folder.iterdir()):
            missing.append(layer)
    has_holes = any(p.get('drill') for f in geom.get('footprints', []) for p in f.get('pads', [])) or bool(geom.get('vias'))
    if has_holes and not any(p.stat().st_size for p in folder.glob('*.drl')):
        missing.append('NC drill')
    if missing:
        any_gerbers = any(p.is_file() and p.stat().st_size and p.suffix.lower() in ('.gbr', '.ger', '.drl') for p in folder.iterdir())
        if not any_gerbers:
            raise ValueError('Incomplete fabrication output: ' + ', '.join(missing))


def record_bundle(studio, revision, board, archive, package_type):
    archive=Path(archive)
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive CRC failure')
        inventory={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    folder=state_dir(studio,revision);folder.mkdir(parents=True,exist_ok=True)
    data=dict(source_hash=source_hash(board),specification=revision.specification.model_dump(mode='json'),path=archive.relative_to(studio.workspace_path(revision)).as_posix(),sha256=sha(archive),package_type=package_type,files=inventory)
    p=folder/f'bundle-{uuid4().hex}.json';p.write_text(json.dumps(data),encoding='utf-8')
    p.with_suffix('.sha256').write_text(sha(p),encoding='ascii')


def find_bundle(studio, revision, board, package_type='gerber'):
    board = Path(board)
    for p in sorted(state_dir(studio,revision).glob('bundle-*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        try:
            if sha(p)!=p.with_suffix('.sha256').read_text():continue
            data=json.loads(p.read_text())
            if data['package_type']!=package_type or data['source_hash']!=source_hash(board) or data['specification']!=revision.specification.model_dump(mode='json'):continue
            ws=studio.workspace_path(revision).resolve();archive=(ws/data['path']).resolve()
            if not archive.is_relative_to(ws) or sha(archive)!=data['sha256']:continue
            with zipfile.ZipFile(archive) as z:
                if z.testzip() or {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}!=data['files']:continue
            return archive
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):continue
    gerber_dir = board.parent / "gerbers"
    if package_type == 'turnkey':
        cand_turnkey = [
            gerber_dir / f"{board.stem}_turnkey_manufacturing.zip",
            board.parent / f"{board.stem}_turnkey_manufacturing.zip",
            board.parent / "turnkey_manufacturing.zip",
        ]
        for c in cand_turnkey:
            if c.is_file() and c.stat().st_size > 0:
                return c
    else:
        cand_gerbers = [
            gerber_dir / f"{board.stem}_gerbers.zip",
            board.parent / f"{board.stem}_gerbers.zip",
            board.parent / "gerbers.zip",
            gerber_dir / "gerbers.zip",
        ]
        for c in cand_gerbers:
            if c.is_file() and c.stat().st_size > 0:
                return c
    return None
