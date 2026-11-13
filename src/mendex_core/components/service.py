"""Component and Material Library Service for Mendex Studio."""
from __future__ import annotations

from typing import Dict, List, Optional
from .models import ComponentRecord, MaterialRecord, MagneticCoreRecord


class ComponentLibraryService:
    """Provides shared, read-only component references; qualification is separate."""

    def __init__(self):
        self._components: Dict[str, ComponentRecord] = {}
        self._materials: Dict[str, MaterialRecord] = {}
        self._cores: Dict[str, MagneticCoreRecord] = {}
        self._seed_default_library()

    def _seed_default_library(self) -> None:
        """Load packaged, sourced references without writing project data."""
        import json
        from importlib.resources import files
        from uuid import uuid5, NAMESPACE_URL

        catalog = json.loads(files("mendex_core.config").joinpath("component_library.json").read_text(encoding="utf-8"))
        self.categories = catalog["categories"]
        for field, model, target, key in (
            ("components", ComponentRecord, self._components, "mpn"),
            ("materials", MaterialRecord, self._materials, "name"),
            ("cores", MagneticCoreRecord, self._cores, "name"),
        ):
            for entry in catalog[field]:
                identity = f"mendex:library:{field}:{entry.get('manufacturer', '')}:{entry[key]}"
                record = model(id=str(uuid5(NAMESPACE_URL, identity)), **entry)
                if entry[key] in target:
                    raise ValueError(f"Duplicate library reference: {entry[key]}")
                target[entry[key]] = record

    def list_components(self, category: Optional[str] = None) -> List[ComponentRecord]:
        if category:
            return [c for c in self._components.values() if c.category.lower() == category.lower()]
        return list(self._components.values())

    def get_component(self, mpn: str) -> Optional[ComponentRecord]:
        return self._components.get(mpn)

    def list_materials(self) -> List[MaterialRecord]:
        return list(self._materials.values())

    def get_material(self, name: str) -> Optional[MaterialRecord]:
        return self._materials.get(name)

    def list_cores(self) -> List[MagneticCoreRecord]:
        return list(self._cores.values())

    def get_core(self, name: str) -> Optional[MagneticCoreRecord]:
        return self._cores.get(name)
