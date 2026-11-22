"""Geometric regression cases: coordinates are synthetic metres, not evidence."""
from copy import deepcopy

import pytest

from mendex_core.pcb_placement import UnsupportedGeometry, evaluate_placement, polygons


def rect(x1, y1, x2, y2, layer="F.CrtYd"):
    return {"kind": "fp_rect", "layer": layer, "points_m": {"start": [x1, y1], "end": [x2, y2]}}


def poly(points, layer="Edge.Cuts"):
    return {"kind": "gr_poly", "layer": layer, "points_m": {"vertices": points}}


def component(ref, x, y, *, rotation=0, side="F", locked=False, half=.001):
    return {"reference": ref, "x_m": x, "y_m": y, "rotation_deg": rotation,
            "layer": side + ".Cu", "locked": locked, "courtyards_local": [rect(-half, -half, half, half, side + ".CrtYd")]}


def board(*components):
    return {"components": list(components), "edge_cuts": [rect(0, 0, .05, .04, "Edge.Cuts")], "keepouts": []}


def keepout(shape, *, layers=("F.Cu",), owner=None, rule="not_allowed"):
    return {"reference": owner, "layers": list(layers), "polygons": [shape], "rules": {"footprints": rule}}


def check(analysis, name):
    return evaluate_placement(analysis)["checks"][name]


def test_complete_geometry_has_only_scoped_clear_results():
    result = evaluate_placement(board(component("A", .01, .01), component("B", .02, .01)))
    assert result["status"] == "CLEAR" and result["complete"]
    assert result["evaluation_status"] == "NOT_EVALUATED"
    assert all(c["status"] == "CLEAR" for c in result["checks"].values())


@pytest.mark.parametrize("x,y", [(.0005, .02), (.001, .02), (.0495, .02), (.02, -.01), (.02, .0395)])
def test_outside_or_touching_board_is_an_issue(x, y):
    result = check(board(component("A", x, y)), "board_containment")
    assert result["status"] == "ISSUES_FOUND" and result["complete"]


def test_concave_outline_catches_edges_crossing_void_with_all_vertices_inside():
    a = board(component("A", .025, .025))
    a["edge_cuts"] = [poly([(0, 0), (.05, 0), (.05, .04), (.03, .04), (.03, .02), (.02, .02), (.02, .04), (0, .04)])]
    a["components"][0]["courtyards_local"] = [rect(-.01, -.001, .01, .001)]
    assert check(a, "board_containment")["status"] == "ISSUES_FOUND"


def test_enclosed_board_cutout_is_detected_without_vertex_crossings():
    a = board(component("A", .02, .02, half=.005))
    a["edge_cuts"].append(rect(.019, .019, .021, .021, "Edge.Cuts"))
    assert check(a, "board_containment")["status"] == "ISSUES_FOUND"


@pytest.mark.parametrize("primitives", [[], [poly([(0, 0), (1, 1), (0, 1), (1, 0)])],
    [{"kind": "gr_arc", "points_m": {}}],
    [{"kind": "gr_line", "points_m": {"start": [0, 0], "end": [1, 0]}}],
    [poly([(0, 0), (float("nan"), 0), (0, 1)])],
    [rect(0, 0, 1, 1), rect(2, 2, 3, 3)]])
def test_unsupported_or_invalid_board_never_clears(primitives):
    a = board(component("A", .01, .01))
    a["edge_cuts"] = primitives
    assert check(a, "board_outline")["status"] == "NOT_EVALUATED"
    assert check(a, "board_containment")["status"] == "NOT_EVALUATED"
    assert evaluate_placement(a)["status"] == "NOT_EVALUATED"


def test_closed_unordered_segments_form_outline_and_duplicate_branch_is_unavailable():
    vertices = [(0, 0), (.05, 0), (.05, .04), (0, .04)]
    segments = [{"kind": "gr_line", "points_m": {"start": vertices[i], "end": vertices[(i+1)%4]}} for i in (2, 0, 3, 1)]
    a = board(component("A", .01, .01))
    a["edge_cuts"] = segments
    assert check(a, "board_outline")["status"] == "CLEAR"
    a["edge_cuts"].append(segments[0])
    assert check(a, "board_outline")["status"] == "NOT_EVALUATED"


def test_rotated_courtyard_is_not_an_unrotated_or_axis_aligned_proxy():
    a = board(component("A", .01, .01, rotation=90), component("B", .01, .014))
    a["components"][0]["courtyards_local"] = [rect(-.005, -.0005, .005, .0005)]
    assert check(a, "courtyard_overlap")["status"] == "ISSUES_FOUND"
    a["components"][0]["rotation_deg"] = 0
    assert check(a, "courtyard_overlap")["status"] == "CLEAR"


@pytest.mark.parametrize("side,expected", [("F", "ISSUES_FOUND"), ("B", "CLEAR")])
def test_overlap_and_touch_are_side_specific(side, expected):
    a = board(component("A", .01, .01), component("B", .012, .01, side=side))
    assert check(a, "courtyard_overlap")["status"] == expected


def test_same_side_one_courtyard_fully_inside_another_is_overlap():
    a = board(component("A", .01, .01, half=.005), component("B", .01, .01))
    assert check(a, "courtyard_overlap")["status"] == "ISSUES_FOUND"


def test_missing_courtyard_does_not_hide_known_overlap_or_clear_unknown_geometry():
    a = board(component("A", .01, .01), component("B", .01, .01), component("C", .02, .02))
    a["components"][2]["courtyards_local"] = []
    result = check(a, "courtyard_overlap")
    assert result["status"] == "ISSUES_FOUND" and not result["complete"]
    a["components"][1]["x_m"] = .03
    assert check(a, "courtyard_overlap")["status"] == "NOT_EVALUATED"


def test_curved_polygon_courtyard_never_silently_becomes_straight_edges():
    a = board(component("A", .01, .01))
    a["components"][0]["courtyards_local"] = [{**poly([(0, 0), (.001, 0), (0, .001)], "F.CrtYd"), "has_curves": True}]
    assert check(a, "courtyard_overlap")["status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("layers,expected", [(("F.Cu",), "ISSUES_FOUND"), (("B.Cu",), "CLEAR"),
    (("*.Cu",), "ISSUES_FOUND"), (("F&B.Cu",), "ISSUES_FOUND"), (("In1.Cu",), "NOT_EVALUATED")])
def test_keepout_rule_layers_and_enclosure(layers, expected):
    a = board(component("A", .01, .01, half=.003))
    a["keepouts"] = [keepout(poly([(.009, .009), (.011, .009), (.011, .011), (.009, .011)]), layers=layers)]
    assert check(a, "footprint_keepouts")["status"] == expected


def test_allowed_footprints_do_not_turn_track_keepouts_into_component_restrictions():
    a = board(component("A", .01, .01))
    a["keepouts"] = [keepout(rect(0, 0, .03, .03), rule="allowed")]
    assert check(a, "footprint_keepouts")["status"] == "CLEAR"
    a["keepouts"][0]["rules"] = {"tracks": "not_allowed"}
    assert check(a, "footprint_keepouts")["status"] == "NOT_EVALUATED"


def test_owned_keepout_rotates_with_owner_and_excludes_other_components():
    a = board(component("J1", .01, .01, rotation=90), component("R1", .01, .005))
    a["keepouts"] = [keepout(rect(.004, -.001, .006, .001), owner="J1")]
    assert check(a, "footprint_keepouts")["issues"][0]["reference"] == "R1"
    a["components"][1]["y_m"] = .02
    assert check(a, "footprint_keepouts")["status"] == "CLEAR"


def test_native_and_explicit_fixed_positions_include_rotation_and_side():
    a = board(component("J1", .01, .01, locked=True), component("R1", .03, .01))
    original = {c["reference"]: deepcopy(c) for c in a["components"]}
    a["components"][0]["x_m"] += .001
    a["components"][1]["rotation_deg"] = 90
    result = evaluate_placement(a, original, ["R1"])
    assert result["fixed_references"] == ["J1", "R1"]
    assert {i["reference"] for i in result["checks"]["fixed_components"]["issues"]} == {"J1", "R1"}
    assert evaluate_placement(a, original, ["UNKNOWN"])["checks"]["fixed_components"]["status"] == "ISSUES_FOUND"


def test_rotated_footprint_local_edge_rectangle_is_transformed_as_polygon():
    a = board(component("A", .02, .02, rotation=45))
    a["edge_cuts"] = [{**rect(-.01, -.005, .01, .005, "Edge.Cuts"), "reference": "A"}]
    assert check(a, "board_containment")["status"] == "CLEAR"


def test_geometry_budget_and_backtracking_polygon_are_unavailable():
    with pytest.raises(UnsupportedGeometry):
        polygons([poly([(0, 0), (2, 0), (1, 0), (1, 1)])])
    with pytest.raises(UnsupportedGeometry):
        polygons([poly([(i, 0) for i in range(2001)])])


def test_finite_points_with_overflowing_area_cannot_clear_geometry():
    a = board(component("A", .01, .01))
    a["edge_cuts"] = [rect(-8e153, -8e153, 8e153, 8e153, "Edge.Cuts")]
    assert check(a, "board_outline")["status"] == "NOT_EVALUATED"
