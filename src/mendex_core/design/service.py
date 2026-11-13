"""Engineering Design Service coordinating IR, synthesis, artifacts, and revisions."""
from __future__ import annotations

import json
import shutil
import subprocess
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
    KiCadPCBGenerator,
    FEMMMagneticGenerator,
)
from .ltspice_runner import LTspiceRunner, LTspiceSimulationResult
from .femm_runner import FEMMRunner, FEMMSimulationResult
from .iteration import DesignIterationEngine, DesignIterationProposal
from .naming import sanitize_filename, clean_title


class EngineeringDesignService:
    """Core domain service for Specification-to-Design creation and management."""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.designs_dir = self.data_root / "engineering_designs"
        self.designs_dir.mkdir(parents=True, exist_ok=True)
        self._designs_cache: Dict[str, EngineeringDesign] = {}
        self.ltspice_runner = LTspiceRunner()
        self.femm_runner = FEMMRunner()
        self._load_all()

    def _get_design_file(self, design_id: str) -> Path:
        return self.designs_dir / f"{design_id}.json"

    def _load_all(self) -> None:
        fresh = {}
        for f in self.designs_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                d = EngineeringDesign.model_validate(data)
                fresh[d.id] = d
            except Exception:
                pass
        self._designs_cache = fresh

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
        safe_title = clean_title(title, fallback="Untitled Engineering Design")

        design = EngineeringDesign(
            workspace_id=str(workspace_id),
            title=safe_title,
            category=category,
            product_id=clean_prod_id,
            requirements=requirements,
            candidates=candidates,
        )

        # If candidates synthesized, select top candidate to create initial Revision 1
        if candidates and candidates[0].ir_snapshot:
            selected_cand = candidates[0]
            ir = selected_cand.ir_snapshot.model_copy(deep=True)
            ir.title = safe_title

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
        f = self._get_design_file(design_id)
        if not f.exists():
            self._designs_cache.pop(design_id, None)
            return None
        if design_id in self._designs_cache:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                fresh = EngineeringDesign.model_validate(data)
                cached = self._designs_cache[design_id]
                cached.revisions = fresh.revisions
                cached.status = fresh.status
                cached.title = fresh.title
                cached.category = fresh.category
                cached.description = fresh.description
                cached.active_revision_index = fresh.active_revision_index
                return cached
            except Exception:
                return self._designs_cache[design_id]
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            d = EngineeringDesign.model_validate(data)
            self._designs_cache[d.id] = d
            return d
        except Exception:
            return None

    def list_designs(self, workspace_id: Optional[str] = None) -> List[EngineeringDesign]:
        self._load_all()
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
        # Every generation is a new snapshot, including regeneration of the same
        # design revision. Previously registered native bytes must never be replaced.
        artifacts_dir = self.data_root / ".mendex" / "ga" / uuid4().hex
        artifacts_dir.mkdir(parents=True, exist_ok=False)

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

        # 1b. LTspice Graphical Schematic (.asc)
        asc_content = LTspiceNetlistGenerator.generate_asc_schematic(ir)
        asc_path = artifacts_dir / f"{ir.topology.lower()}_schematic.asc"
        asc_path.write_text(asc_content, encoding="utf-8")
        asc_hash = CrossToolSyncService.compute_sha256(asc_path)
        art_asc = DesignArtifact(
            design_id=design.id,
            revision_id=active_rev.id,
            kind=ArtifactKind.NETLIST,
            name="LTspice Graphical Schematic",
            path=str(asc_path.relative_to(self.data_root)) if asc_path.is_relative_to(self.data_root) else str(asc_path),
            format="LTspice Schematic (.asc)",
            sha256=asc_hash,
            source_service="LTspiceNetlistGenerator",
        )
        new_artifacts.append(art_asc)

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

        # 2b. KiCad Populated PCB Layout (.kicad_pcb)
        base_title = sanitize_filename(ir.title or ir.topology, fallback="kicad_pcb")
        pcb_path = artifacts_dir / "kicad" / f"{base_title}.kicad_pcb"
        KiCadPCBGenerator.export_pcb(ir, pcb_path)
        pcb_hash = CrossToolSyncService.compute_sha256(pcb_path)
        art_pcb = DesignArtifact(
            design_id=design.id,
            revision_id=active_rev.id,
            kind=ArtifactKind.KICAD_PCB,
            name="KiCad 9 Populated PCB Layout",
            path=str(pcb_path.relative_to(self.data_root)) if pcb_path.is_relative_to(self.data_root) else str(pcb_path),
            format="KiCad PCB (.kicad_pcb)",
            sha256=pcb_hash,
            source_service="KiCadPCBGenerator",
        )
        new_artifacts.append(art_pcb)

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

            # 4. FreeCAD 3D Bobbin STEP Model
            from integrations.generators.freecad_generator import generate_freecad_bobbin_script
            geom = ir.magnetic_geometry
            step_path = artifacts_dir / "bobbin.step"
            freecad_script_path = artifacts_dir / "generate_bobbin.py"
            fc_script = generate_freecad_bobbin_script(
                flange_od_mm=geom.flange_od_mm,
                core_id_mm=getattr(geom, "core_id_mm", geom.barrel_od_mm - 2.0),
                height_mm=geom.bobbin_height_mm,
                output_step_path=str(step_path),
            )
            freecad_script_path.write_text(fc_script, encoding="utf-8")

            fc_cmd = Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
            if not fc_cmd.exists() and (found_fc := shutil.which("freecadcmd")):
                fc_cmd = Path(found_fc)
            if fc_cmd.exists():
                try:
                    subprocess.run([str(fc_cmd), str(freecad_script_path)], capture_output=True, timeout=30)
                except Exception:
                    pass
            if step_path.exists():
                step_hash = CrossToolSyncService.compute_sha256(step_path)
                art_step = DesignArtifact(
                    design_id=design.id,
                    revision_id=active_rev.id,
                    kind=ArtifactKind.STEP_SOLID,
                    name="FreeCAD 3D Bobbin Model",
                    path=str(step_path.relative_to(self.data_root)) if step_path.is_relative_to(self.data_root) else str(step_path),
                    format="ISO 10303 STEP (.step)",
                    sha256=step_hash,
                    source_service="FreeCADBobbinGenerator",
                )
                new_artifacts.append(art_step)

        active_rev.artifacts.extend(new_artifacts)
        self._persist(design)
        return new_artifacts

    def run_ltspice_simulation(self, design_id: str, workspace_dir: Path) -> LTspiceSimulationResult:
        """Executes real LTspice batch simulation and parses numerical waveforms and metrics."""
        design = self.get_design(design_id)
        if not design or not design.get_active_revision():
            raise KeyError(f"Design '{design_id}' or active revision not found.")

        active_rev = design.get_active_revision()
        netlists = [a for a in active_rev.artifacts if Path(a.path).suffix.lower() == ".net"]
        if not netlists:
            self.generate_native_artifacts(design_id, workspace_dir)
            netlists = [a for a in design.get_active_revision().artifacts if Path(a.path).suffix.lower() == ".net"]
        artifact = netlists[-1]
        original = (self.data_root / artifact.path).resolve()
        if not original.is_relative_to(self.data_root.resolve()) or CrossToolSyncService.compute_sha256(original) != artifact.sha256:
            raise ValueError("Registered netlist is outside the data root or has changed")
        run = self.data_root / ".mendex" / "dr" / uuid4().hex
        run.mkdir(parents=True, exist_ok=False)
        net_path = run / "input.net"
        net_path.write_bytes(original.read_bytes())
        return self.ltspice_runner.run_simulation(net_path, requirements=design.requirements, working_dir=run)

    def run_femm_simulation(self, design_id: str, workspace_dir: Path) -> FEMMSimulationResult:
        """Executes real FEMM 4.2 magnetic FEA and verifies flux density."""
        design = self.get_design(design_id)
        if not design or not design.get_active_revision():
            raise KeyError(f"Design '{design_id}' or active revision not found.")

        active_rev = design.get_active_revision()
        if not active_rev.ir.magnetic_geometry:
            raise ValueError("Design does not have magnetic geometry defined.")

        artifacts_dir = self.data_root / ".mendex" / "dr" / uuid4().hex
        return self.femm_runner.run_magnetic_analysis(active_rev.ir.magnetic_geometry, artifacts_dir)

    def propose_iteration(self, design_id: str, sim_result: LTspiceSimulationResult) -> Optional[DesignIterationProposal]:
        """Formulates an engineering improvement proposal when a requirement fails."""
        design = self.get_design(design_id)
        if not design:
            raise KeyError(f"Design '{design_id}' not found.")
        return DesignIterationEngine.analyze_simulation_and_propose(design, sim_result)

    def apply_iteration(self, design_id: str, proposal: DesignIterationProposal) -> Dict[str, Any]:
        """Applies approved proposal, branches new revision, and re-simulates."""
        design = self.get_design(design_id)
        if not design:
            raise KeyError(f"Design '{design_id}' not found.")
        res = DesignIterationEngine.apply_iteration_proposal(design, proposal, self.data_root, self.ltspice_runner)
        self._persist(design)
        return res

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

    def open_artifact(self, design_id: str, artifact_name: str) -> Dict[str, Any]:
        """Launches the native engineering tool for a specific artifact with verified inputs."""
        from mendex_core.launch import open_native
        design = self.get_design(design_id)
        if not design or not design.get_active_revision():
            raise KeyError("Design or active revision not found.")

        target_art = None
        for art in design.get_active_revision().artifacts:
            if art.name.lower() == artifact_name.lower() or art.kind.value == artifact_name.lower() or Path(art.path).name.lower() == artifact_name.lower():
                target_art = art
                break
        if not target_art:
            raise FileNotFoundError(f"Artifact '{artifact_name}' not found in active revision.")

        art_path = self.data_root / target_art.path if not Path(target_art.path).is_absolute() else Path(target_art.path)
        if not art_path.exists():
            raise FileNotFoundError(f"Artifact file does not exist on disk: {art_path}")

        open_native(art_path)
        return {
            "design_id": design_id,
            "artifact_name": target_art.name,
            "path": str(art_path),
            "status": "opened_in_native_tool",
        }
