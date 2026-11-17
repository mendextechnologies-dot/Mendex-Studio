"""One-time scoped edit script, retained to document the control repair."""
from pathlib import Path
p=Path('src/mendex_core/desktop/service.py');s=p.read_text(encoding='utf-8')
start=s.index('        elif kind == "pcb":',s.index('    def cad_preview'))
end=s.index('        else:\n            sch_files',start)
s=s[:start]+'''        elif kind == "pcb":
            pcb_files = list(pcb_dir.glob("*.kicad_pcb")) if pcb_dir.exists() else []
            pcb_files = pcb_files or list(ws_dir.glob("*.kicad_pcb"))
            if not pcb_files:
                return {"kind":"pcb","available":False,"error":"No PCB in this revision"}
            if len(pcb_files)!=1:
                raise StudioError("CONFLICT", "Choose one active PCB; multiple boards are ambiguous")
            pcb_path=pcb_files[0]
            from ..design.geometry import extract_pcb_geometry
            from ..design.cad_state import read_check, find_bundle, source_hash
            geom=extract_pcb_geometry(pcb_path)
            check=read_check(self.studio,revision,pcb_path)
            archive=find_bundle(self.studio,revision,pcb_path)
            return {**geom,"kind":"pcb","available":geom['is_valid'],"filename":pcb_path.name,
                "source_hash":source_hash(pcb_path),"drc_summary":check,
                "connectivity_status":("CONNECTED" if check['available'] and check['unconnected']==0 else "NOT_EVALUATED"),
                "unconnected_count":check['unconnected'],"is_4layer":geom['layer_count']==4,
                "has_gerbers":archive is not None,"gerber_zip_path":archive.relative_to(ws_dir).as_posix() if archive else None,
                "gerber_filename":archive.name if archive else None,"gerber_sha256":_file_sha256(archive) if archive else None,
                "gerber_bytes":archive.stat().st_size if archive else 0,
                **_inspect_pcb_mechanical_and_3d(pcb_path,revision.specification)}

'''+s[end:]
# Reads use only current hash/view-specific renders; no generic-angle fallback.
start=s.index('        if kind == "3d":',s.index('    def cad_preview'))
end=s.index('        elif kind == "pcb":',start)
s=s[:start]+'''        if kind == "3d":
            view=(getattr(request,'view','iso') or 'iso').lower()
            boards=list(pcb_dir.glob('*.kicad_pcb')) or list(ws_dir.glob('*.kicad_pcb'))
            if len(boards)!=1:
                return dict(kind='3d',available=False,error='Exactly one active PCB is required')
            from ..design.cad_state import source_hash, sha
            fingerprint=source_hash(boards[0])
            cache=self.studio.root/'.mendex'/'previews'/str(revision.revision_id)/fingerprint
            for metadata in sorted(cache.glob(f'{view}-*.json'), key=lambda p:p.stat().st_mtime_ns,reverse=True):
                try:
                    data=json.loads(metadata.read_text());image=cache/data.pop('image_file')
                    if data['view']==view and sha(image)==data['sha256']:
                        import base64
                        return {**data,'render_image':'data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode('ascii')}
                except (OSError,ValueError,KeyError):pass
            return self.render_3d_pcb(models.Render3DQuery(revision_id=request.revision_id,view=view))

'''+s[end:]
# Route success must require actual native DRC and all requested operations.
s=s.replace('        drc_clean = result.get("drc_errors", 0) == 0\n        success = routing_completed and drc_clean', '''        from ..design.cad_state import drc_summary, save_check, source_hash
        check=drc_summary(result.get('drc',{}))
        save_check(self.studio,revision,pcb_path,check)
        success = bool(result.get('success') and routing_completed and check['available'] and check['errors']==0 and check['unconnected']==0 and (not request.pour_ground or result.get('pour_completed')))
'''.rstrip())
s=s.replace('            "routing_completed": routing_completed,\n            "filename": pcb_path.name,','            "routing_completed": routing_completed,\n            "source_hash": source_hash(pcb_path),\n            "drc": check,\n            "drc_available": check["available"],\n            "filename": pcb_path.name,')
# Plane/slot normalized result is snapshotted separately from old reports.
for method,following in [('mill_isolation_slot','setup_4layer_planes'),('setup_4layer_planes','export_cad_step')]:
 a=s.index('    def '+method);b=s.index('    def '+following,a);chunk=s[a:b]
 where=chunk.index('        return self._record_receipt(')
 chunk=chunk[:where]+'''        from ..design.cad_state import drc_summary, save_check, source_hash
        res['drc']=drc_summary(res.get('drc',{}))
        res['source_hash']=source_hash(pcb_path)
        save_check(self.studio,revision,pcb_path,res['drc'])
'''+chunk[where:]
 s=s[:a]+chunk+s[b:]
# Rendering always writes unique derived evidence outside the revision baseline.
a=s.index('    def render_3d_pcb');chunk=s[a:]
old='''        render_filename = "board_3d_render.png" if view_angle == "iso" else f"board_3d_{view_angle}.png"
        render_png = pcb_path.parent / render_filename'''
new='''        from ..design.cad_state import source_hash
        if view_angle not in {'iso','top','bottom','iso_bottom'}:
            raise StudioError('INVALID_INPUT','Unknown 3D view')
        fingerprint=source_hash(pcb_path)
        cache=self.studio.root/'.mendex'/'previews'/str(revision.revision_id)/fingerprint
        cache.mkdir(parents=True,exist_ok=True)
        render_png=cache/f'{view_angle}-{uuid4().hex}.png' '''
assert old in chunk;chunk=chunk.replace(old,new,1)
needle='        return self._record_receipt(scope, getattr(request, "idempotency_key", None), "render_3d_pcb", request.model_dump(mode="json"), res, revision.revision_id)'
assert needle in chunk
chunk=chunk.replace(needle,'''        res['source_hash']=fingerprint
        metadata={k:v for k,v in res.items() if k!='render_image'}
        metadata['image_file']=rendered_path.name
        rendered_path.with_suffix('.json').write_text(json.dumps(metadata),encoding='utf-8')
'''+needle,1);s=s[:a]+chunk
# Export to a unique candidate folder, preserve every existing output.
a=s.index('    def export_gerbers');b=s.index('    def download_gerbers',a);chunk=s[a:b]
chunk=chunk.replace('            out_dir = kicad_service.export_gerbers(','            target_dir=pcb_path.parent/"gerbers"/uuid4().hex\n            out_dir = kicad_service.export_gerbers(',1)
chunk=chunk.replace('                pcb_path,\n                auto_route=', '                pcb_path,\n                output_dir=target_dir,\n                auto_route=',1)
where=chunk.index('            # Copy Procurement BOM')
chunk=chunk[:where]+'''            if export_errors:
                raise StudioError('INVALID_INPUT','; '.join(export_errors))
            from ..design.cad_state import validate_fabrication, record_bundle, source_hash
            validate_fabrication(out_dir,pcb_path)
'''+chunk[where:]
chunk=chunk.replace('            from ..design.models import ArtifactKind','''            record_bundle(self.studio,revision,pcb_path,zip_path,'gerber')
            bom_included=any(out_dir.glob('*_bom.csv'))
            if bom_included:
                record_bundle(self.studio,revision,pcb_path,turnkey_zip_path,'turnkey')
            from ..design.models import ArtifactKind''',1)
chunk=chunk.replace('str(zip_path.relative_to(self.studio.root).as_posix()) if zip_path.is_relative_to(self.studio.root) else str(zip_path)','zip_path.relative_to(ws_dir).as_posix()')
chunk=chunk.replace('                "success": True,\n                "output_dir":', '                "success": True,\n                "source_hash": source_hash(pcb_path),\n                "engineering_status": "NOT_EVALUATED",\n                "assembly_complete": False,\n                "bom_included": bom_included,\n                "output_dir":')
s=s[:a]+chunk+s[b:]
# Existing unidentified/stale ZIPs are not silently served or exported on reads.
a=s.index('        gerber_out_dir =',s.index('    def download_gerbers'));b=s.index('        import base64',a)
s=s[:a]+'''        from ..design.cad_state import find_bundle
        pkg_type=getattr(request,'package_type','gerber')
        if pkg_type not in {'gerber','turnkey'}:raise StudioError('INVALID_INPUT','Unknown package type')
        zip_path=find_bundle(self.studio,revision,pcb_path,pkg_type)
        if zip_path is None:
            return dict(success=False,error='No intact current package. Re-export Gerbers; assembly package also requires a supplied BOM.',status='NOT_EVALUATED')
'''+s[b:]
# Inspector is a read-only native PCB layer view plus validated export inventory.
a=s.index('        gerber_out_dir =',s.index('    def inspect_gerber_layers'));b=s.index('        # Scan Gerber & Drill',a)
s=s[:a]+'''        from ..design.geometry import extract_pcb_geometry
        from ..design.cad_state import find_bundle, source_hash
        geom=extract_pcb_geometry(pcb_path)
        zip_path=find_bundle(self.studio,revision,pcb_path)
        gerber_out_dir=zip_path.parent if zip_path else pcb_path.parent/'gerbers'/'unavailable'
        has_gerbers=zip_path is not None
        gerber_sha256=_file_sha256(zip_path) if zip_path else None
        gerber_bytes=zip_path.stat().st_size if zip_path else 0
        gerber_rel_path=zip_path.relative_to(ws_dir).as_posix() if zip_path else None
        tracks=geom['tracks'];footprints=geom['footprints'];edge_cuts=geom['edge_cuts'];zones=geom['zones']
        layer_count=geom['layer_count'];is_4layer=layer_count==4
        min_x,min_y,max_x,max_y=[geom['bbox'][key] for key in ('min_x','min_y','max_x','max_y')]
        board_drill_hits=[dict(x=p['x'],y=p['y'],diameter=p['drill'],plated=p['type']=='thru_hole',pad_number=p['number'],ref=f['ref'],type='pad') for f in footprints for p in f['pads'] if p['drill']]
        board_drill_hits += [dict(x=v['x'],y=v['y'],diameter=v['diameter'],plated=True,pad_number='VIA',ref='VIA',type='via') for v in geom['vias']]

'''+s[b:]
# Do not mark a legacy or missing BOM archive as an assembly package.
a=s.index('        turnkey_cand_zips =',s.index('    def inspect_gerber_layers'));b=s.index('        has_turnkey =',a)
s=s[:a]+"        turnkey_zip=find_bundle(self.studio,revision,pcb_path,'turnkey')\n\n"+s[b:]
a=s.index('    def inspect_gerber_layers');b=s.index('    def apply_schematic',a);chunk=s[a:b]
chunk=chunk.replace('            "board_name": pcb_path.stem,','            **geom,\n            "source_hash":source_hash(pcb_path),\n            "geometry_source":"NATIVE_PCB_NOT_CAM",\n            "board_name": pcb_path.stem,',1)
s=s[:a]+chunk+s[b:]
p.write_text(s,encoding='utf-8')
