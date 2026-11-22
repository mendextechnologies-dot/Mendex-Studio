"""Checks against explicitly drawn, straight-edged KiCad placement geometry.

No electrical clearance, physical body dimensions or safety rules are inferred.
Unsupported geometry is unavailable, never a zero-violation result.
"""
from __future__ import annotations

import math


# Numerical coincidence tolerance only, not a placement/engineering clearance.
EPS_M = 1e-12
MAX_POLYGON_VERTICES = 2000


class UnsupportedGeometry(ValueError):
    pass


def _point(value):
    if len(value) != 2 or not all(math.isfinite(v) for v in value):
        raise UnsupportedGeometry("Missing or non-finite point")
    return tuple(value)


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _cross(a, b, c):
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if not math.isfinite(value):
        raise UnsupportedGeometry("Geometry exceeds numerical range")
    return value


def _on_segment(p, a, b):
    return (abs(_cross(a, b, p)) <= EPS_M * _distance(a, b)
            and min(a[0], b[0]) - EPS_M <= p[0] <= max(a[0], b[0]) + EPS_M
            and min(a[1], b[1]) - EPS_M <= p[1] <= max(a[1], b[1]) + EPS_M)


def _segments_touch(a, b, c, d):
    if any((_on_segment(p, x, y)) for p, x, y in ((a, c, d), (b, c, d), (c, a, b), (d, a, b))):
        return True
    return ((_cross(a, b, c) > 0) != (_cross(a, b, d) > 0)
            and (_cross(c, d, a) > 0) != (_cross(c, d, b) > 0))


def _edges(polygon):
    return zip(polygon, polygon[1:] + polygon[:1])


def _area(polygon):
    # Translate to the first point to avoid cancellation at large board offsets.
    origin = polygon[0]
    area = abs(sum(_cross(origin, a, b) for a, b in _edges(polygon))) / 2
    if not math.isfinite(area):
        raise UnsupportedGeometry("Polygon area exceeds numerical range")
    return area


def _inside(p, polygon):
    """1 strictly inside, 0 on boundary, -1 outside (simple polygon)."""
    inside = False
    for a, b in _edges(polygon):
        if _on_segment(p, a, b):
            return 0
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return 1 if inside else -1


def _boundaries_touch(a, b):
    return any(_segments_touch(x, y, u, v) for x, y in _edges(a) for u, v in _edges(b))


def _overlap(a, b):
    return _boundaries_touch(a, b) or _inside(a[0], b) >= 0 or _inside(b[0], a) >= 0


def _simple(vertices):
    points = [_point(p) for p in vertices]
    if len(points) > 1 and _distance(points[0], points[-1]) <= EPS_M:
        points.pop()
    if not 3 <= len(points) <= MAX_POLYGON_VERTICES:
        raise UnsupportedGeometry("Polygon needs 3–2000 vertices")
    edges = list(_edges(points))
    if any(_distance(a, b) <= EPS_M for a, b in edges) or _area(points) <= EPS_M ** 2:
        raise UnsupportedGeometry("Degenerate polygon")
    for i, (a, b) in enumerate(edges):
        # Consecutive edges may share their endpoint, but must not backtrack.
        c = edges[(i + 1) % len(edges)][1]
        if _on_segment(c, a, b) or _on_segment(a, b, c):
            raise UnsupportedGeometry("Backtracking polygon edges")
        for j in range(i + 1, len(edges)):
            if j == i + 1 or (i == 0 and j == len(edges) - 1):
                continue
            if _segments_touch(a, b, *edges[j]):
                raise UnsupportedGeometry("Self-intersecting polygon")
    return points


def polygons(primitives):
    """Closed rect/poly shapes and unambiguous loops of line segments only."""
    result, segments = [], []
    for primitive in primitives:
        if primitive.get("has_curves"):
            raise UnsupportedGeometry("Curved polygon edges are unsupported")
        kind = primitive["kind"]
        points = primitive["points_m"]
        if kind in {"gr_rect", "fp_rect"}:
            a, b = _point(points.get("start", [])), _point(points.get("end", []))
            result.append(_simple([a, (b[0], a[1]), b, (a[0], b[1])]))
        elif kind in {"gr_poly", "fp_poly", "polygon"}:
            result.append(_simple(points.get("vertices", [])))
        elif kind in {"gr_line", "fp_line"}:
            segments.append((_point(points.get("start", [])), _point(points.get("end", []))))
        else:
            raise UnsupportedGeometry("Unsupported curved or non-polygon primitive: " + kind)
    if len(segments) > MAX_POLYGON_VERTICES:
        raise UnsupportedGeometry("Too many outline segments")
    # Cluster endpoints only within the documented computational tolerance.
    vertices, adjacency = [], {}
    for a, b in segments:
        ids = []
        for p in (a, b):
            found = next((i for i, v in enumerate(vertices) if _distance(p, v) <= EPS_M), None)
            if found is None:
                found = len(vertices)
                vertices.append(p)
            ids.append(found)
        a_id, b_id = ids
        if a_id == b_id or b_id in adjacency.get(a_id, []):
            raise UnsupportedGeometry("Degenerate or duplicate outline segment")
        adjacency.setdefault(a_id, []).append(b_id)
        adjacency.setdefault(b_id, []).append(a_id)
    if any(len(neighbours) != 2 for neighbours in adjacency.values()):
        raise UnsupportedGeometry("Outline is open or branched")
    unused = set(adjacency)
    while unused:
        start = min(unused)
        current, previous, loop = start, None, []
        while True:
            if current not in unused:
                if current == start:
                    break
                raise UnsupportedGeometry("Ambiguous outline loop")
            unused.remove(current)
            loop.append(vertices[current])
            following = next(v for v in adjacency[current] if v != previous)
            previous, current = current, following
        result.append(_simple(loop))
    if not result:
        raise UnsupportedGeometry("No closed polygon geometry supplied")
    return result


def _transform(poly, component):
    angle = -math.radians(component["rotation_deg"])
    co, si = math.cos(angle), math.sin(angle)
    return [(component["x_m"] + x * co - y * si, component["y_m"] + x * si + y * co) for x, y in poly]


def _board_primitive(primitive, components):
    if not primitive.get("reference"):
        return primitive
    component = components[primitive["reference"]]
    if primitive["kind"] in {"gr_rect", "fp_rect"}:
        return {"kind": "gr_poly", "points_m": {"vertices": _transform(polygons([primitive])[0], component)}}
    points = {key: _transform(value, component) if key == "vertices" else _transform([value], component)[0]
              for key, value in primitive["points_m"].items()}
    return {**primitive, "points_m": points}


def _check(issues=None, unavailable=None):
    issues, unavailable = issues or [], unavailable or []
    return {"status": "ISSUES_FOUND" if issues else ("NOT_EVALUATED" if unavailable else "CLEAR"),
            "complete": not unavailable, "issues": issues, "unavailable": unavailable}


def evaluate_placement(analysis, original=None, fixed_references=()):
    components = {c["reference"]: c for c in analysis["components"]}
    coverage = []
    bodies = {}
    for ref, component in components.items():
        try:
            sides = {}
            for layer in ("F.CrtYd", "B.CrtYd"):
                primitives = [p for p in component["courtyards_local"] if p["layer"] == layer]
                if primitives:
                    sides[layer[0]] = [_transform(p, component) for p in polygons(primitives)]
            body_side = str(component["layer"]).split(".")[0]
            if body_side not in {"F", "B"} or body_side not in sides:
                raise UnsupportedGeometry("Missing courtyard on component side")
            bodies[ref] = sides
        except (UnsupportedGeometry, KeyError, TypeError, ValueError) as exc:
            coverage.append({"reference": ref, "reason": str(exc)})
    if not components:
        coverage.append({"reason": "No components to evaluate"})

    board = []
    outline_missing = []
    try:
        board = sorted(polygons([_board_primitive(p, components) for p in analysis["edge_cuts"]]), key=_area, reverse=True)
        for hole in board[1:]:
            if _boundaries_touch(board[0], hole) or _inside(hole[0], board[0]) != 1:
                raise UnsupportedGeometry("Outline must have one outer boundary with internal cutouts")
        for i, hole in enumerate(board[1:]):
            if any(_overlap(hole, other) for other in board[i + 2:]):
                raise UnsupportedGeometry("Nested or intersecting cutouts are unsupported")
    except (UnsupportedGeometry, KeyError, TypeError, ValueError) as exc:
        board = []
        outline_missing.append({"reason": str(exc)})
    containment_issues = []
    if board:
        outer, holes = board[0], board[1:]
        for ref, sides in bodies.items():
            if any(_boundaries_touch(poly, outer) or any(_inside(p, outer) != 1 for p in poly)
                   or any(_overlap(poly, hole) for hole in holes) for ps in sides.values() for poly in ps):
                containment_issues.append({"code": "OUTSIDE_BOARD_OR_TOUCHING_EDGE", "reference": ref})

    overlap_issues = []
    entries = list(bodies.items())
    for i, (ref, sides) in enumerate(entries):
        for other_ref, other_sides in entries[i + 1:]:
            for side in sides.keys() & other_sides.keys():
                if any(_overlap(a, b) for a in sides[side] for b in other_sides[side]):
                    overlap_issues.append({"code": "COURTYARDS_OVERLAP_OR_TOUCH", "references": [ref, other_ref], "side": side})

    keepout_issues, keepout_missing = [], []
    for index, keepout in enumerate(analysis["keepouts"]):
        rule = keepout["rules"].get("footprints")
        if rule == "allowed":
            continue
        if rule != "not_allowed":
            keepout_missing.append({"keepout_index": index, "reason": "Footprint restriction is not explicit"})
            continue
        try:
            shapes = polygons(keepout["polygons"])
            owner = keepout["reference"]
            if owner:
                shapes = [_transform(p, components[owner]) for p in shapes]
            layers = set(keepout["layers"])
            if not layers or not layers <= {"F.Cu", "B.Cu", "*.Cu", "F&B.Cu"}:
                raise UnsupportedGeometry("Keepout layers cannot be mapped completely to board sides")
            sides = {"F", "B"} if layers & {"*.Cu", "F&B.Cu"} else {v[0] for v in layers}
            for ref, body_sides in bodies.items():
                # A footprint's own rule area travels with it and excludes other footprints.
                if ref == owner:
                    continue
                if any(_overlap(a, b) for side in sides & body_sides.keys() for a in shapes for b in body_sides[side]):
                    keepout_issues.append({"code": "FOOTPRINT_KEEPOUT", "reference": ref, "keepout_index": index, "owner": owner})
        except (UnsupportedGeometry, KeyError, TypeError, ValueError) as exc:
            keepout_missing.append({"keepout_index": index, "reason": str(exc)})

    fixed_issues = []
    native_fixed = {ref for ref, c in (original or components).items() if c["locked"] or c.get("outline_anchor")}
    fixed = set(fixed_references) | native_fixed
    for ref in sorted(fixed):
        if ref not in components:
            fixed_issues.append({"code": "UNKNOWN_FIXED_COMPONENT", "reference": ref})
        elif original is not None:
            before, after = original[ref], components[ref]
            if any(before[k] != after[k] for k in ("x_m", "y_m", "rotation_deg", "layer")):
                fixed_issues.append({"code": "FIXED_COMPONENT_MOVED", "reference": ref})

    checks = {
        "board_outline": _check(unavailable=outline_missing),
        "board_containment": _check(containment_issues, coverage + outline_missing),
        "courtyard_overlap": _check(overlap_issues, coverage),
        "footprint_keepouts": _check(keepout_issues, coverage + keepout_missing),
        "fixed_components": _check(fixed_issues),
    }
    status = "ISSUES_FOUND" if any(c["status"] == "ISSUES_FOUND" for c in checks.values()) else (
        "NOT_EVALUATED" if any(c["status"] == "NOT_EVALUATED" for c in checks.values()) else "CLEAR")
    return {"engine": "mendex-placement-geometry/1", "status": status,
            "complete": all(c["complete"] for c in checks.values()), "checks": checks,
            "fixed_references": sorted(fixed), "numerical_tolerance_m": EPS_M,
            "evaluation_status": "NOT_EVALUATED",
            "notice": "Drawn courtyard geometry only; no electrical clearance, 3D collision, DRC or safety qualification."}
