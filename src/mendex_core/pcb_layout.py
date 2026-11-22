"""First-party, structural PCB analysis and isolated placement candidates.

No model inference, routing, rule clearance or engineering qualification is implied.
Native inputs are read only; all coordinates in the public contract use SI units.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from typing import Annotated
from pydantic import Field, model_validator
from copper_kicad import sexpr

from .evidence import digest, specification_hash
from .models import Lifecycle, Model, now
from .pcb import file_hash, native_structure
from .service import StudioError
from .pcb_placement import evaluate_placement


class PlacementMove(Model):
    reference: str = Field(min_length=1, max_length=100)
    x_m: float = Field(ge=-10, le=10, strict=True)
    y_m: float = Field(ge=-10, le=10, strict=True)


class LayoutPlan(Model):
    relative_path: str = Field(min_length=1, max_length=1000)
    expected_context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    moves: list[PlacementMove] = Field(default_factory=list, max_length=10000)
    rationale: str = Field(min_length=1, max_length=4000)
    fixed_references: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def unique_moves(self):
        from .integration_contracts import safe_relative
        safe_relative(self.relative_path)
        if len({m.reference for m in self.moves}) != len(self.moves):
            raise ValueError("A component may appear only once in a placement plan")
        if len(set(self.fixed_references)) != len(self.fixed_references):
            raise ValueError("Fixed component references must be unique")
        return self


def _children(node, name):
    return sexpr.find_all(node, name)


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite native geometry")
    return number


def _position(node):
    at = sexpr.find(node, "at")
    if at is None or len(at) < 3:
        raise ValueError("Footprints and pads require explicit positions")
    return _number(at[1]) / 1000, _number(at[2]) / 1000, _number(at[3]) if len(at) > 3 else 0.0


def _locked(node):
    return sexpr.Sym("locked") in [v for v in node[1:] if not isinstance(v, list)] or (
        sexpr.find(node, "locked") is not None and str(sexpr.value(node, "locked", "yes")) != "no")


def _read_tree(path):
    native_structure(path)  # size, single-root and balanced-document validation
    try:
        tree = sexpr.loads(path.read_text(encoding="utf-8-sig"))
    except (IndexError, RecursionError) as exc:
        raise ValueError("Invalid native board structure") from exc
    if sexpr.head(tree) != "kicad_pcb":
        raise ValueError("Select a KiCad PCB board")
    return tree


def _geometry(node):
    """Preserve explicit primitive points; do not infer a closed board envelope."""
    points = {}
    for key in ("start", "mid", "end", "center"):
        entry = sexpr.find(node, key)
        if entry is not None:
            points[key] = [_number(v) / 1000 for v in entry[1:3]]
    pts = sexpr.find(node, "pts")
    if pts:
        points["vertices"] = [[_number(v) / 1000 for v in p[1:3]] for p in _children(pts, "xy")]
    return {"kind": str(node[0]), "layer": str(sexpr.value(node, "layer", "")), "points_m": points,
            "has_curves": bool(pts and any(isinstance(p, list) and p and p[0] != "xy" for p in pts[1:]))}


def _keepout(zone, reference):
    rules = sexpr.find(zone, "keepout")
    layers = sexpr.find(zone, "layers")
    return {"reference": reference, "coordinate_frame": "footprint_local" if reference else "board",
            "layers": [str(v) for v in layers[1:]] if layers else [str(sexpr.value(zone, "layer", ""))],
            "rules": {str(r[0]): str(r[1]) for r in rules[1:] if isinstance(r, list) and len(r) == 2},
            "polygons": [_geometry(p) for p in _children(zone, "polygon")]}


def analyze_tree(tree):
    nets = {}
    for n in _children(tree, "net"):
        if len(n) != 3 or str(n[1]) in nets:
            raise ValueError("Malformed or duplicate net definition")
        nets[str(n[1])] = str(n[2])
    components, references, connectivity = [], set(), {}
    keepouts = []
    for fp in _children(tree, "footprint"):
        props = {str(p[1]): str(p[2]) for p in _children(fp, "property") if len(p) >= 3}
        for p in _children(fp, "fp_text"):
            if len(p) >= 3:
                props.setdefault(str(p[1]).capitalize(), str(p[2]))
        ref = props.get("Reference", "")
        if not ref or ref in references:
            raise ValueError("Every footprint needs a unique reference")
        references.add(ref)
        x, y, rotation = _position(fp)
        angle = -math.radians(rotation)
        pads = []
        for pad in _children(fp, "pad"):
            if len(pad) < 4:
                raise ValueError("Malformed native pad")
            px, py, _ = _position(pad)
            size = sexpr.find(pad, "size")
            if size is None or len(size) < 3:
                raise ValueError("Pad size is missing")
            dimensions = [_number(v) / 1000 for v in size[1:3]]
            if min(dimensions) <= 0:
                raise ValueError("Pad sizes must be positive")
            net = sexpr.find(pad, "net")
            name = ""
            if net is not None:
                if len(net) < 2:
                    raise ValueError("Malformed pad net")
                net_id = str(net[1])
                name = str(net[2]) if len(net) > 2 else (
                    str(net[1]) if not isinstance(net[1], sexpr.Sym) else nets.get(net_id, ""))
                if net_id in nets and name != nets[net_id]:
                    raise ValueError("Pad net disagrees with board net definition")
                if net_id != "0" and not name:
                    raise ValueError("Unresolved pad net")
                if name:
                    connectivity.setdefault(name, []).append({"reference": ref, "pad": str(pad[1])})
            pads.append({"number": str(pad[1]), "net": name, "size_m": dimensions,
                         "x_m": x + px * math.cos(angle) - py * math.sin(angle),
                         "y_m": y + px * math.sin(angle) + py * math.cos(angle)})
        courtyards = [_geometry(g) for g in fp[1:] if isinstance(g, list) and g
                      and str(sexpr.value(g, "layer", "")).endswith(".CrtYd")]
        components.append({"reference": ref, "value": props.get("Value", ""),
                           "footprint": str(fp[1]), "x_m": x, "y_m": y,
                           "rotation_deg": rotation, "layer": str(sexpr.value(fp, "layer", "")),
                           "locked": _locked(fp), "pads": pads, "courtyards_local": courtyards})
        components[-1]["outline_anchor"] = any(isinstance(g, list) and g and sexpr.value(g, "layer") == "Edge.Cuts" for g in fp[1:])
        for zone in _children(fp, "zone"):
            if sexpr.find(zone, "keepout") is not None:
                keepouts.append(_keepout(zone, ref))
    for zone in _children(tree, "zone"):
        if sexpr.find(zone, "keepout") is not None:
            keepouts.append(_keepout(zone, None))
    copper = {k: len(_children(tree, k)) for k in ("segment", "arc", "via")}
    copper["zone"] = sum(sexpr.find(z, "keepout") is None for z in _children(tree, "zone"))
    edges = [_geometry(g) for g in tree[1:] if isinstance(g, list) and g and sexpr.value(g, "layer") == "Edge.Cuts"]
    for fp, component in zip(_children(tree, "footprint"), components, strict=True):
        edges.extend({**_geometry(g), "reference": component["reference"]} for g in fp[1:]
                     if isinstance(g, list) and g and sexpr.value(g, "layer") == "Edge.Cuts")
    result = {"engine": "mendex-pcb-layout/2", "native_format_version": str(sexpr.value(tree, "version", "unknown")),
            "components": components,
            "nets": [{"name": name, "pads": pads} for name, pads in sorted(connectivity.items())],
            "edge_cuts": edges,
            "keepouts": keepouts, "copper_counts": copper,
            "populated": bool(components) and any(c["pads"] for c in components),
            "evaluation_status": "NOT_EVALUATED",
            "warnings": ["Structural extraction only; connectivity is not a routed-connectivity check.",
                         "Placement checks use drawn straight-edged courtyards and outlines; electrical clearance, DRC, isolation and thermal checks are unavailable.",
                         "External library dependencies are not embedded or qualified."]}
    result["placement_constraints"] = evaluate_placement(result)
    return result


class PCBLayoutService:
    def __init__(self, studio):
        self.studio = studio

    def analyze(self, revision_id, relative_path):
        from .integration_contracts import safe_relative
        try:
            safe_relative(relative_path)
        except ValueError as exc:
            raise StudioError("INVALID_INPUT", str(exc)) from exc
        revision, workspace, source = self.studio.pcb._design(revision_id, relative_path)
        relative_path = source.relative_to(workspace).as_posix()
        if source.suffix != ".kicad_pcb":
            raise StudioError("INVALID_INPUT", "Layout analysis requires a KiCad PCB")
        _, _, pcb = self.studio.pcb._revision(revision_id)
        context = self.studio.pcb._context(pcb)
        try:
            analysis = analyze_tree(_read_tree(source))
        except (ValueError, IndexError, TypeError, RecursionError) as exc:
            raise StudioError("INVALID_INPUT", str(exc)) from exc
        spec_hash = specification_hash(revision.specification)
        if (context != self.studio.pcb._context(pcb) or
                specification_hash(self.studio.get_revision(revision_id).specification) != spec_hash):
            raise StudioError("CONFLICT", "PCB inputs changed during analysis")
        return {"schema_version": 1, "revision_id": str(revision.revision_id),
                "source": relative_path, "source_sha256": context[source.relative_to(pcb).as_posix()],
                "specification_sha256": spec_hash, "context": context,
                "context_sha256": digest(json.dumps({"source": relative_path, "context": context,
                                                     "specification": spec_hash}, sort_keys=True).encode()),
                **analysis}

    def _storage(self, revision_id):
        path = self.studio.root / ".mendex" / "pcb-layout" / str(UUID(str(revision_id)))
        if any(p.is_symlink() or p.is_junction() for p in (path, path.parent, path.parent.parent)):
            raise StudioError("INVALID_INPUT", "Layout storage must not use links or junctions")
        path = path.resolve()
        if not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "Layout storage escapes data root")
        return path

    def _prepare_plan(self, revision_id, request):
        plan = LayoutPlan.model_validate(request)
        analysis = self.analyze(revision_id, plan.relative_path)
        if plan.expected_context_sha256 != analysis["context_sha256"]:
            raise StudioError("CONFLICT", "Board context changed; analyze again before creating a candidate")
        if not analysis["populated"]:
            raise StudioError("INVALID_INPUT", "Layout candidates require populated footprints and pads")
        original = {c["reference"]: c for c in analysis["components"]}
        if any(ref not in original for ref in plan.fixed_references):
            raise StudioError("INVALID_INPUT", "Unknown fixed component reference")
        for move in plan.moves:
            if move.reference not in original or original[move.reference]["locked"]:
                raise StudioError("INVALID_INPUT", "Unknown or locked component: " + move.reference)
            if original[move.reference]["outline_anchor"]:
                raise StudioError("INVALID_INPUT", "Board-outline component cannot move: " + move.reference)
            if move.reference in plan.fixed_references:
                raise StudioError("INVALID_INPUT", "Explicitly fixed component cannot move: " + move.reference)
        if plan.moves and any(analysis["copper_counts"].values()):
            raise StudioError("INVALID_INPUT", "Component moves require an unrouted board without copper zones; existing copper cannot follow moves")
        proposed = deepcopy(analysis)
        moved = {m.reference: m for m in plan.moves}
        for c in proposed["components"]:
            if c["reference"] in moved:
                move = moved[c["reference"]]
                # Match the native writer's 6 decimal millimetre precision.
                x, y = round(move.x_m * 1000, 6) / 1000, round(move.y_m * 1000, 6) / 1000
                dx, dy = x - c["x_m"], y - c["y_m"]
                c["x_m"], c["y_m"] = x, y
                for pad in c["pads"]:
                    pad["x_m"] += dx
                    pad["y_m"] += dy
        report = evaluate_placement(proposed, original, plan.fixed_references)
        proposed["placement_constraints"] = report
        return plan, analysis, proposed, report

    def preview_plan(self, revision_id, request):
        plan, analysis, proposed, report = self._prepare_plan(revision_id, request)
        revision = self.studio.get_revision(revision_id)
        if self.analyze(revision_id, plan.relative_path)["context_sha256"] != analysis["context_sha256"]:
            raise StudioError("CONFLICT", "Board context changed during preview")
        return {"revision_id": str(revision_id), "context_sha256": analysis["context_sha256"],
                "analysis": proposed, "placement_constraints": report,
                "can_create": revision.lifecycle_status == Lifecycle.DRAFT and (not plan.moves or report["status"] == "CLEAR"),
                "evaluation_status": "NOT_EVALUATED", "position_resolution_m": 1e-9}

    def create_candidate(self, revision_id, request):
        with self.studio.atomic():
            revision = self.studio.get_revision(revision_id)
            if revision.lifecycle_status != Lifecycle.DRAFT:
                raise StudioError("IMMUTABLE", "Layout candidates require a draft revision")
            plan, analysis, _, report = self._prepare_plan(revision_id, request)
            if plan.moves and report["status"] != "CLEAR":
                raise StudioError("INVALID_INPUT", "Placement constraints are " + report["status"] + "; preview the plan for violations or unavailable geometry")
            _, _, pcb = self.studio.pcb._revision(revision_id)
            candidate_id = str(uuid4())
            folder = self._storage(revision_id) / candidate_id
            inputs = folder / "inputs"
            inputs.mkdir(parents=True, exist_ok=False)
            for name, sha in analysis["context"].items():
                dest = inputs / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pcb / name, dest)
                if file_hash(dest) != sha:
                    raise StudioError("CONFLICT", "PCB inputs changed during snapshot")
            source_relative = Path(analysis["source"]).relative_to("pcb")
            tree = _read_tree(inputs / source_relative)
            moves = {m.reference: m for m in plan.moves}
            for fp, component in zip(_children(tree, "footprint"), analysis["components"], strict=True):
                ref = component["reference"]
                if ref in moves:
                    at = sexpr.find(fp, "at")
                    at[1:3] = [moves[ref].x_m * 1000, moves[ref].y_m * 1000]
            output = folder / "output"
            shutil.copytree(inputs, output)
            board = output / source_relative
            if moves:
                board.write_text(sexpr.dumps(tree) + "\n", encoding="utf-8")
            result_analysis = analyze_tree(_read_tree(board))
            result_report = evaluate_placement(result_analysis, {c["reference"]: c for c in analysis["components"]}, plan.fixed_references)
            result_analysis["placement_constraints"] = result_report
            if plan.moves and result_report["status"] != "CLEAR":
                raise StudioError("CONFLICT", "Serialized candidate did not retain clear placement constraints")
            current = self.analyze(revision_id, plan.relative_path)
            if current["context_sha256"] != analysis["context_sha256"]:
                raise StudioError("CONFLICT", "PCB context changed while creating candidate")
            result = {"candidate_id": candidate_id, "revision_id": str(revision_id),
                      "created_at": now().isoformat(), "status": "DRAFT_CANDIDATE",
                      "evaluation_status": "NOT_EVALUATED", "plan": plan.model_dump(mode="json"),
                      "checks": {name: "NOT_EVALUATED" for name in ("drc", "placement_clearance", "routing")},
                      "placement_constraints": result_report,
                      "context_sha256": analysis["context_sha256"], "source_sha256": analysis["source_sha256"],
                      "context": analysis["context"], "specification_sha256": analysis["specification_sha256"],
                      "specification_snapshot": revision.specification.model_dump(mode="json"),
                      "board_relative_path": (Path("output") / source_relative).as_posix(),
                      "analysis": result_analysis}
            (folder / "candidate.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
            artifacts = {p.relative_to(folder).as_posix(): file_hash(p) for p in folder.rglob("*") if p.is_file()}
            (folder / "manifest.json").write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
            (folder / "manifest.sha256").write_text(file_hash(folder / "manifest.json"), encoding="ascii")
        return self.read_candidate(revision_id, candidate_id)

    def read_candidate(self, revision_id, candidate_id):
        self.studio.get_revision(revision_id)
        try:
            candidate_id = str(UUID(str(candidate_id)))
        except ValueError as exc:
            raise StudioError("INVALID_INPUT", "Invalid candidate identifier") from exc
        folder = self._storage(revision_id) / candidate_id
        if not folder.is_dir() or folder.is_symlink() or folder.is_junction():
            raise StudioError("NOT_FOUND", "Layout candidate not found")
        invalid = {"candidate_id": candidate_id, "integrity": False, "stale": True,
                   "effective_constraint_status": "NOT_EVALUATED",
                   "evaluation_status": "NOT_EVALUATED", "status": "NOT_EVALUATED",
                   "diagnostic": "Candidate evidence is incomplete, missing or modified"}
        try:
            manifest = folder / "manifest.json"
            if file_hash(manifest) != (folder / "manifest.sha256").read_text().strip():
                return invalid
            artifacts = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(artifacts, dict) or "candidate.json" not in artifacts:
                return invalid
            paths = list(folder.rglob("*"))
            if any(p.is_symlink() or p.is_junction() for p in paths):
                return invalid
            actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
            if actual != set(artifacts) | {"manifest.json", "manifest.sha256"}:
                return invalid
            for name, sha in artifacts.items():
                path = (folder / name).resolve()
                if not path.is_relative_to(folder) or not path.is_file() or file_hash(path) != sha:
                    return invalid
            result = json.loads((folder / "candidate.json").read_text(encoding="utf-8"))
            try:
                current = self.analyze(revision_id, result["plan"]["relative_path"])
                stale = current["context_sha256"] != result["context_sha256"]
            except (StudioError, OSError, ValueError):
                stale = True
            return {**result, "integrity": True, "stale": stale,
                    "effective_constraint_status": "NOT_EVALUATED" if stale else result.get("placement_constraints", {}).get("status", "NOT_EVALUATED"),
                    "status": "NOT_EVALUATED" if stale else result["status"],
                    "folder": str(folder), "board_path": str(folder / result["board_relative_path"])}
        except (OSError, ValueError, KeyError, TypeError):
            return invalid

    def list_candidates(self, revision_id):
        self.studio.get_revision(revision_id)
        folder = self._storage(revision_id)
        results = []
        for p in sorted(folder.iterdir()) if folder.is_dir() else []:
            try:
                UUID(p.name)
            except ValueError:
                continue
            if p.is_dir() and not p.is_symlink() and not p.is_junction():
                results.append(self.read_candidate(revision_id, p.name))
        return results
