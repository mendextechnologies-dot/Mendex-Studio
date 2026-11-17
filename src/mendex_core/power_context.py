"""Read-only, revision-scoped component bindings for power calculations."""
import hashlib
import json
import re
from pathlib import Path

from .evidence import specification_hash
from .power_analysis import AnalysisRequest, DeviceModel
from .service import StudioError


def component_context(studio, revision_id):
    revision = studio.get_revision(revision_id)
    workspace = studio.workspace_path(revision).resolve()
    sources, rows, problems, library = [], [], [], []
    bom = workspace / "bom" / "bom.json"
    if bom.exists():
        if not bom.resolve().is_relative_to(workspace) or bom.stat().st_size > 2_000_000:
            problems.append("BOM is outside the revision or exceeds the 2 MB read limit")
        else:
            raw = bom.read_bytes()
            sources.append({"source": "bom/bom.json", "sha256": hashlib.sha256(raw).hexdigest()})
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    data = data.get("items")
                if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
                    raise ValueError("Expected a BOM row list or an object with items")
                for row in data:
                    references = str(row.get("designator") or "").strip()
                    for ref in filter(None, re.split(r"[,;\s]+", references)):
                        rows.append({"reference": ref, "mpn": str(row.get("mpn") or "").strip(),
                                     "manufacturer": str(row.get("manufacturer") or "").strip(), "source": "bom/bom.json"})
                    if row.get("power_thermal_model"):
                        library.append(DeviceModel.model_validate(row["power_thermal_model"]))
            except (ValueError, TypeError) as exc:
                problems.append(f"BOM/model data cannot be read: {exc}")
    for design in studio.design.list_designs():
        if design.core_revision_id != str(revision.revision_id) or design.product_id != str(revision.product_id):
            continue
        active = design.get_active_revision()
        if active is None:
            continue
        source = f"design:{design.id}:{active.id}"
        sources.append({"source": source, "sha256": hashlib.sha256(active.ir.model_dump_json().encode()).hexdigest()})
        for c in active.ir.components:
            rows.append({"reference": c.designator, "mpn": c.mpn or "", "manufacturer": c.manufacturer or "", "source": source})
            if c.parameters.get("power_thermal_model"):
                try:
                    library.append(DeviceModel.model_validate(c.parameters["power_thermal_model"]))
                except ValueError as exc:
                    problems.append(f"{c.designator}: supplied power model is invalid: {exc}")
    grouped = {}
    for row in rows:
        grouped.setdefault(row["reference"], []).append(row)
    components = []
    for ref, entries in sorted(grouped.items()):
        identities = {(r["mpn"].casefold(), r["manufacturer"].casefold()) for r in entries}
        complete = all(r["mpn"] for r in entries)
        components.append({"reference": ref, "mpn": entries[0]["mpn"], "manufacturer": entries[0]["manufacturer"],
                           "status": "AVAILABLE" if complete and len(identities) == 1 else "NOT_EVALUATED",
                           "reason": "" if complete and len(identities) == 1 else "Part identity missing or inconsistent between BOM/design sources",
                           "sources": entries})
    snapshot = {"specification_sha256": specification_hash(revision.specification),
                "binding_implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "sources": sorted(sources, key=lambda s: s["source"]),
                "components": components, "problems": problems}
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"revision_id": str(revision.revision_id), "component_hash": digest, **snapshot,
            "model_library": [m.model_dump(mode="json") for m in library],
            "note": "Current saved core IR/BOM only. Unsaved native schematic edits must first be imported/forward annotated."}


def resolve_bound_models(request: AnalysisRequest, context):
    if request.expected_component_hash and request.expected_component_hash != context["component_hash"]:
        raise StudioError("CONFLICT", "Components changed; refresh component context before recalculating or recording")
    available = {c["reference"]: c for c in context["components"]}
    canonical_models = [DeviceModel.model_validate(m) for m in context["model_library"]]
    bank = request.model_library
    devices, errors = [], {}
    for index, device in enumerate(request.devices):
        resolved = device
        ref = device.component_reference
        if ref:
            component = available.get(ref)
            if context["problems"]:
                errors[index] = "; ".join(context["problems"])
            elif component is None:
                errors[index] = f"{ref}: component removed or not present in this revision"
            elif component["status"] != "AVAILABLE":
                errors[index] = f"{ref}: {component['reason']}"
            else:
                def matches(m):
                    return (m.mpn or "").casefold() == component["mpn"].casefold() and (m.manufacturer or "").casefold() == component["manufacturer"].casefold()
                # Explicit models embedded in the current BOM/IR take precedence;
                # otherwise keep the selected exact model or find its replacement.
                embedded = [m for m in canonical_models if matches(m)]
                candidates = embedded or ([device] if matches(device) else [m for m in bank if matches(m)])
                unique = {}
                for candidate in candidates:
                    item = candidate.model_dump(mode="json")
                    item["component_reference"] = ref
                    unique[json.dumps(item, sort_keys=True)] = item
                if len(unique) != 1:
                    errors[index] = f"{ref}: {'no' if not unique else 'ambiguous'} sourced model for {component['manufacturer']} {component['mpn']}; old model is not reused"
                else:
                    resolved = DeviceModel.model_validate(next(iter(unique.values())))
                    resolved = resolved.model_copy(update={"name": f"{ref}: {component['mpn']}"})
        devices.append(resolved.model_dump(mode="json"))
    effective = request.model_dump(mode="json")
    effective.update(devices=devices, expected_component_hash=context["component_hash"])
    return effective, errors
