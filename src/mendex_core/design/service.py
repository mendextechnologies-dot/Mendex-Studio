"""Engineering Design Service coordinating IR, synthesis, artifacts, and revisions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .ir import DesignIntermediateRepresentation
from .models import (
    EngineeringDesign,
    DesignRevision,
    DesignCandidate,
    DesignArtifact,
    ArtifactKind,
    DesignStatus,
    Requirement,
)
from .synthesis import CandidateSynthesisEngine
from .parametric import ParametricDesignEngine, ParametricChangeImpact
from .sync import CrossToolSyncService
from .generators import (
    LTspiceNetlistGenerator,
    KiCadSchematicGenerator,
    FEMMMagneticGenerator,
)


class EngineeringDesignService:
    """Core domain service for Specification-to-Design creation and management."""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.designs_dir = self.data_root / "engineering_designs"
        self.designs_dir.mkdir(parents=True, exist_ok=True)
        self._designs_cache: Dict[str, EngineeringDesign] = {}
        self._load_all()

    def _get_design_file(self, design_id: str) -> Path:
        return self.designs_dir / f"{design_id}.json"

    def _load_all(self) -> None:
        for f in self.designs_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                d = EngineeringDesign.model_validate(data)
                self._designs_cache[d.id] = d
            except Exception:
                pass

    def _persist(self, design: EngineeringDesign) -> None:
        self._designs_cache[design.id] = design
        path = self._get_design_file(design.id)
        path.write_text(design.model_dump_json(indent=2), encoding="utf-8")

    def create_design_from_requirements(
        self,
        workspace_id: str,
        title: str,
        category: str,
        requirements: List[Requirement],
        product_id: Optional[Any] = None,
    ) -> EngineeringDesign:
        """Synthesizes candidate topologies from requirements and initializes a new design."""
        candidates = CandidateSynthesisEngine.synthesize_candidates(requirements)
        clean_prod_id = str(product_id) if product_id is not None else None

        design = EngineeringDesign(
            workspace_id=str(workspace_id),
            title=title,
            category=category,
            product_id=clean_prod_id,
            requirements=requirements,
            candidates=candidates,
        )

        # If candidates synthesized, select top candidate to create initial Revision 1
        if candidates and candidates[0].ir_snapshot:
            selected_cand = candidates[0]
            ir = selected_cand.ir_snapshot.model_copy(deep=True)
            ir.title = title

            rev = DesignRevision(
                design_id=design.id,
                revision_index=1,
                label="Rev 1",
                ir=ir,
                summary=f"Synthesized from {selected_cand.name} topology",
            )
            design.revisions.append(rev)
            design.active_revision_id = rev.id
            design.status = DesignStatus.SYNTHESIZED

        self._persist(design)
        return design

    def get_design(self, design_id: str) -> Optional[EngineeringDesign]:
        return self._designs_cache.get(design_id)

    def list_designs(self, workspace_id: Optional[str] = None) -> List[EngineeringDesign]:
        if workspace_id:
            return [d for d in self._designs_cache.values() if d.workspace_id == workspace_id]
        return list(self._designs_cache.values())

    def generate_native_artifacts(self, design_id: str, workspace_dir: Path) -> List[DesignArtifact]:
        """Generates editable native artifacts (LTspice netlist, KiCad schematic, FEMM Lua) from active IR."""
        design = self.get_design(design_id)
        if not design:
            raise KeyError(f"Design '{design_id}' not found.")

        active_rev = design.get_active_revision()
        if not active_rev:
            raise ValueError("No active design revision available to generate artifacts.")

        ir = active_rev.ir
        artifacts_dir = workspace_dir / "generated_artifacts" / f"rev_{active_rev.revision_index}"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        new_artifacts: List[DesignArtifact] = []

        # 1. LTspice Netlist (.net)
        netlist_content = LTspiceNetlistGenerator.generate_netlist(ir)
        net_path = artifacts_dir / f"{ir.topology.lower()}_circuit.net"
        net_path.write_text(netlist_content, encoding="utf-8")
        net_hash = CrossToolSyncService.compute_sha256(net_path)

        art_net = DesignArtifact(
            design_id=design.id,
            revision_id=active_rev.id,
            kind=ArtifactKind.NETLIST,
            name="LTspice Circuit Netlist",
            path=str(net_path.relative_to(self.data_root)) if net_path.is_relative_to(self.data_root) else str(net_path),
            format="SPICE Netlist (.net)",
            sha256=net_hash,
            source_service="LTspiceNetlistGenerator",
        )
        new_artifacts.append(art_net)

        # 2. KiCad 9 Schematic (.kicad_sch)
        kicad_files = KiCadSchematicGenerator.export_project(ir, artifacts_dir / "kicad")
        sch_path = kicad_files["schematic"]
        sch_hash = CrossToolSyncService.compute_sha256(sch_path)

        art_sch = DesignArtifact(
            design_id=design.id,
            revision_id=active_rev.id,
            kind=ArtifactKind.KICAD_SCH,
            name="KiCad 9 Schematic",
            path=str(sch_path.relative_to(self.data_root)) if sch_path.is_relative_to(self.data_root) else str(sch_path),
            format="KiCad S-Expression (.kicad_sch)",
            sha256=sch_hash,
            source_service="KiCadSchematicGenerator",
        )
        new_artifacts.append(art_sch)

        # 3. FEMM Magnetic Model (.lua) if magnetic geometry exists
        if ir.magnetic_geometry:
            femm_content = FEMMMagneticGenerator.generate_lua_script(ir.magnetic_geometry)
            femm_path = artifacts_dir / "magnetic_simulation.lua"
            femm_path.write_text(femm_content, encoding="utf-8")
            femm_hash = CrossToolSyncService.compute_sha256(femm_path)

            art_femm = DesignArtifact(
                design_id=design.id,
                revision_id=active_rev.id,
                kind=ArtifactKind.FEMM_MODEL,
                name="FEMM Magnetic Lua Model",
                path=str(femm_path.relative_to(self.data_root)) if femm_path.is_relative_to(self.data_root) else str(femm_path),
                format="FEMM Lua Script (.lua)",
                sha256=femm_hash,
                source_service="FEMMMagneticGenerator",
            )
            new_artifacts.append(art_femm)

        active_rev.artifacts = new_artifacts
        self._persist(design)
        return new_artifacts

    def recalculate_parameters(self, design_id: str) -> Dict[str, float]:
        """Recalculates parametric relationships in the active IR."""
        design = self.get_design(design_id)
        if not design or not design.get_active_revision():
            raise KeyError("Design or active revision not found.")

        engine = ParametricDesignEngine(design.get_active_revision().ir)
        results = engine.evaluate_all()
        self._persist(design)
        return results

    def analyze_parameter_impact(self, design_id: str, param_name: str, new_value: float) -> ParametricChangeImpact:
        """Determines downstream impact before applying a parameter change."""
        design = self.get_design(design_id)
        if not design or not design.get_active_revision():
            raise KeyError("Design or active revision not found.")

        engine = ParametricDesignEngine(design.get_active_revision().ir)
        return engine.analyze_impact(param_name, new_value)
