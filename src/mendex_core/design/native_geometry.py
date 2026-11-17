"""Read-only structural KiCad geometry; physical bounds exclude viewport padding."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
from copper_kicad.sexpr import loads


def children(node, key):
    return [n for n in node[1:] if isinstance(n, list) and n and n[0] == key]


def field(node, key, default=None):
    found = children(node, key)
    return found[0][1:] if found else default


def first(node, key, default=None):
    values = field(node, key)
    return values[0] if values else default


def points(node):
    pts = children(node, 'pts')
    return [[float(p[1]), float(p[2])] for p in children(pts[0], 'xy')] if pts else []


def arc_points(start, mid, end):
    ax, ay = start; bx, by = mid; cx, cy = end
    det = 2 * (ax * (by-cy) + bx * (cy-ay) + cx * (ay-by))
    if abs(det) < 1e-12: return [start, mid, end]
    aa, bb, cc = ax*ax+ay*ay, bx*bx+by*by, cx*cx+cy*cy
    ox = (aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/det
    oy = (aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/det
    a, b, c = [math.atan2(y-oy, x-ox) for x,y in (start, mid, end)]
    sweep = (c-a) % (2*math.pi)
    if (b-a) % (2*math.pi) > sweep: sweep -= 2*math.pi
    radius = math.hypot(ax-ox,ay-oy)
    count = max(8, min(4096, int(abs(sweep)*radius/0.15)))
    return [[ox+radius*math.cos(a+sweep*i/count),oy+radius*math.sin(a+sweep*i/count)] for i in range(count+1)]


def extract_pcb_geometry(pcb_path: Path | None):
    empty = dict(footprints=[], edge_cuts=[], tracks=[], vias=[], zones=[], graphics=[], copper_layers=[],
                 bbox=dict(min_x=0.,max_x=0.,min_y=0.,max_y=0.,width=0.,height=0.),has_pcb=False,is_valid=False)
    if not pcb_path or not Path(pcb_path).is_file(): return empty
    data = Path(pcb_path).read_bytes()
    try:
        tree = loads(data.decode('utf-8'))
        if not isinstance(tree,list) or tree[0] != 'kicad_pcb': return {**empty,'error':'Not a KiCad PCB'}
        nets = {str(n[1]): str(n[2]) for n in children(tree,'net') if len(n)>2}
        def net(node):
            raw=first(node,'net', first(node,'net_name',''))
            return nets.get(str(raw),str(raw))
        layer_nodes=children(tree,'layers')
        layers=[str(n[1]) for n in layer_nodes[0][1:] if isinstance(n,list) and len(n)>1 and str(n[1]).endswith('.Cu')] if layer_nodes else []
        edges=[];graphics=[];tracks=[];vias=[];zones=[];fps=[]
        for node in tree[1:]:
            if not isinstance(node,list) or not node: continue
            kind=str(node[0]);layer=str(first(node,'layer',''))
            if kind in ('gr_line','gr_rect','gr_arc','gr_poly','gr_circle'):
                shape={'type':kind[3:],'layer':layer}
                if kind in ('gr_line','gr_rect'):
                    a,b=field(node,'start'),field(node,'end')
                    if not a or not b: continue
                    x1,y1,x2,y2=map(float,(*a[:2],*b[:2]))
                    if kind=='gr_rect':x1,x2=sorted((x1,x2));y1,y2=sorted((y1,y2))
                    shape.update(x1=x1,y1=y1,x2=x2,y2=y2)
                elif kind=='gr_arc':
                    shape['points']=arc_points(*[[float(v) for v in field(node,key)[:2]] for key in ('start','mid','end')])
                elif kind=='gr_poly':shape['points']=points(node)
                else:
                    a,b=field(node,'center'),field(node,'end')
                    if not a or not b:continue
                    x,y=float(a[0]),float(a[1]);radius=math.hypot(float(b[0])-x,float(b[1])-y)
                    shape.update(type='poly',points=[[x+radius*math.cos(t*math.pi/32),y+radius*math.sin(t*math.pi/32)] for t in range(65)])
                (edges if layer=='Edge.Cuts' else graphics).append(shape)
            elif kind in ('segment','arc'):
                a,b=field(node,'start'),field(node,'end')
                if not a or not b:continue
                track=dict(x1=float(a[0]),y1=float(a[1]),x2=float(b[0]),y2=float(b[1]),width=float(first(node,'width',.4)),layer=layer,net=net(node),type=kind)
                if kind=='arc':track['points']=arc_points(*[[float(v) for v in field(node,key)[:2]] for key in ('start','mid','end')])
                tracks.append(track)
            elif kind=='via':
                at=field(node,'at',[0,0]);vias.append(dict(x=float(at[0]),y=float(at[1]),size=float(first(node,'size',.6)),diameter=float(first(node,'drill',.3)),layers=[str(v) for v in field(node,'layers',[])],net=net(node)))
            elif kind=='zone':
                zlayers=field(node,'layers',[layer]);filled=[]
                for poly in children(node,'filled_polygon'):
                    filled.append(dict(layer=str(first(poly,'layer',layer)),points=points(poly)))
                zones.append(dict(net=net(node),layer=layer or str(zlayers[0]),layers=[str(v) for v in zlayers],filled_polygons=filled,
                                  outlines=[points(p) for p in children(node,'polygon')]))
            elif kind=='footprint':
                at=field(node,'at',[0,0]);x,y=float(at[0]),float(at[1]);rot=float(at[2]) if len(at)>2 else 0.
                props={str(n[1]):str(n[2]) for n in children(node,'property') if len(n)>2}
                padlist=[];silks=[];angle=-math.radians(rot)
                for pad in children(node,'pad'):
                    pos=field(pad,'at',[0,0]);ox,oy=float(pos[0]),float(pos[1]);size=field(pad,'size',[0,0]);drill=field(pad,'drill',[])
                    numeric=[float(v) for v in drill if not isinstance(v,list) and str(v)!='oval']
                    padlist.append(dict(number=str(pad[1]),type=str(pad[2]),shape=str(pad[3]),ox=ox,oy=oy,
                        x=x+ox*math.cos(angle)-oy*math.sin(angle),y=y+ox*math.sin(angle)+oy*math.cos(angle),
                        rot=rot+(float(pos[2]) if len(pos)>2 else 0),sx=float(size[0]),sy=float(size[1]),
                        drill=numeric[0] if numeric else None,drill_size=numeric,layers=[str(v) for v in field(pad,'layers',[])],net=net(pad)))
                for key in ('fp_line','fp_rect','fp_circle'):
                    for graphic in children(node,key):
                        glayer=str(first(graphic,'layer','F.SilkS'));a,b=field(graphic,'start'),field(graphic,'end')
                        if key in ('fp_line','fp_rect') and a and b:
                            x1,y1,x2,y2=map(float,(*a[:2],*b[:2]))
                            if key=='fp_rect':x1,x2=sorted((x1,x2));y1,y2=sorted((y1,y2))
                            silks.append(dict(type=key[3:],x1=x1,y1=y1,x2=x2,y2=y2,layer=glayer))
                        elif key=='fp_circle':
                            center=field(graphic,'center')
                            if center and b:silks.append(dict(type='circle',cx=float(center[0]),cy=float(center[1]),r=math.hypot(float(b[0])-float(center[0]),float(b[1])-float(center[1])),layer=glayer))
                model=first(node,'model')
                fps.append(dict(name=str(node[1]),ref=props.get('Reference','?'),value=props.get('Value',''),x=x,y=y,rot=rot,
                    layer=layer,pads=padlist,silks=silks,model=model,has_3d_model=model is not None,dnp=bool(children(node,'dnp'))))
        coords=[]
        for edge in edges:coords.extend(edge.get('points',[[edge.get('x1',0),edge.get('y1',0)],[edge.get('x2',0),edge.get('y2',0)]]))
        if not coords:coords=[[f['x'],f['y']] for f in fps]
        bbox=empty['bbox']
        if coords:
            xs,ys=zip(*coords);bbox=dict(min_x=min(xs),max_x=max(xs),min_y=min(ys),max_y=max(ys),width=max(xs)-min(xs),height=max(ys)-min(ys))
        return dict(footprints=fps,edge_cuts=edges,tracks=tracks,vias=vias,zones=zones,graphics=graphics,bbox=bbox,
                    copper_layers=layers,layer_count=len(layers),has_pcb=True,is_valid=bool(fps or edges or tracks or zones),
                    source_sha256=hashlib.sha256(data).hexdigest(),native_track_count=len(tracks),displayed_track_count=len(tracks),
                    connectivity_status='NOT_EVALUATED')
    except (ValueError,IndexError,TypeError,UnicodeError) as exc:
        return {**empty,'has_pcb':True,'error':f'Invalid PCB geometry: {exc}'}
