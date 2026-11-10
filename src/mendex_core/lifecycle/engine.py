"""Product Engineering Lifecycle Engine and Verification Framework."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from mendex_core.evidence import digest, specification_hash
from mendex_core.models import Category
from .kicad_service import KiCadLifecycleService
from .models import (
    ArtifactType,
    LifecycleStage,
    ProductLifecycleAssessment,
    ReadinessGate,
    StageEvaluation,
    StageStatus,
    UnifiedEvidenceRecord,
    now,
)


def compute_file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


class ProductLifecycleEngine:
    """Core evaluation engine assessing product engineering maturity across 12 lifecycle stages."""

    STAGE_METADATA = [
        (LifecycleStage.REQUIREMENTS, 1, "Requirements & Specifications", True, "Reviewed SI requirements specification, standards profile, and isolation requirements", "Specification panel"),
        (LifecycleStage.ELECTRICAL_ARCHITECTURE, 2, "Electrical Architecture & Sizing", True, "Analytical sizing calculations for resonant tank, transformer turns ratio, and semiconductor losses", "DC-DC & Transformer Workspaces"),
        (LifecycleStage.CIRCUIT_DESIGN, 3, "Circuit Design & Netlists", True, "Verified schematic netlist, component selections, and operating topology definition", "Circuit Workspace"),
        (LifecycleStage.ELECTRICAL_SIMULATION, 4, "Electrical Simulation & Waveforms", True, "Batch simulation runs with parsed output waveforms showing ripple and switching transients", "Simulation Lab & Waveforms"),
        (LifecycleStage.MAGNETIC_ANALYSIS, 5, "Magnetic Analysis & FEA", False, "2D/3D magnetic FEA simulation solve verifying flux density and leakage inductance", "Transformer Workspace / FEMM"),
        (LifecycleStage.SCHEMATIC_VERIFICATION, 6, "Schematic Capture & ERC", True, "KiCad schematic file (.kicad_sch) with 0 electrical rule check violations", "KiCad Schematic / ERC"),
        (LifecycleStage.PCB_LAYOUT, 7, "PCB Layout & Stackup", True, "KiCad PCB layout (.kicad_pcb) with defined isolation air slots and creepage distances", "KiCad PCB Layout"),
        (LifecycleStage.PCB_DRC, 8, "PCB Design-Rule Check (DRC)", True, "KiCad DRC report with 0 clearance and net violations", "KiCad PCB / DRC"),
        (LifecycleStage.THERMAL_MECHANICAL, 9, "Thermal & Mechanical Evaluation", False, "3D solid model export (STEP) and thermal dissipation loss budget", "FreeCAD 3D Bobbin"),
        (LifecycleStage.BOM_REVIEW, 10, "BOM & Component Review", True, "Structured Bill of Materials (BOM) with manufacturer part numbers and dielectric ratings", "BOM Review"),
        (LifecycleStage.ENGINEERING_VALIDATION, 11, "Engineering Validation & Verification", True, "Append-only validation records with numerical thresholds and evidence SHA-256 hashes", "Validation Panel"),
        (LifecycleStage.PROTOTYPE_READINESS, 12, "Prototype Readiness Review", True, "All mandatory engineering gates PASSED and formal engineering sign-off recorded", "Prototype Gate Review"),
    ]

    def __init__(self, service: Any):
        self.service = service
        self.kicad = KiCadLifecycleService()
        self._init_tables()

    def _init_tables(self):
        try:
            with self.service.connection() as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS lifecycle_approvals (
                        id TEXT PRIMARY KEY,
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        stage_id TEXT NOT NULL,
                        reviewer TEXT NOT NULL,
                        passed INTEGER NOT NULL,
                        notes TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
        except Exception:
            pass

    def record_stage_approval(
        self,
        revision_id: UUID,
        stage_id: LifecycleStage,
        reviewer: str,
        passed: bool,
        notes: str = "",
    ) -> None:
        """Records an explicit, persistent engineering reviewer sign-off for a lifecycle stage."""
        with self.service.connection() as db:
            db.execute(
                """
                INSERT INTO lifecycle_approvals (id, revision_id, stage_id, reviewer, passed, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), str(revision_id), stage_id.value, reviewer, 1 if passed else 0, notes, now().isoformat()),
            )

    def get_stage_approvals(self, revision_id: UUID) -> Dict[str, Dict[str, Any]]:
        """Retrieves latest reviewer approval for each stage."""
        approvals = {}
        try:
            with self.service.connection() as db:
                rows = db.execute(
                    """
                    SELECT stage_id, reviewer, passed, notes, created_at
                    FROM lifecycle_approvals
                    WHERE revision_id = ?
                    ORDER BY created_at ASC
                    """,
                    (str(revision_id),),
                ).fetchall()
                for stage_id, reviewer, passed, notes, created_at in rows:
                    approvals[stage_id] = {
                        "reviewer": reviewer,
                        "passed": bool(passed),
                        "notes": notes,
                        "created_at": datetime.fromisoformat(created_at),
                    }
        except Exception:
            pass
        return approvals

    def get_evidence_register(
        self, product_id: UUID, revision_id: Optional[UUID] = None
    ) -> List[UnifiedEvidenceRecord]:
        """Gathers all traceable engineering evidence records for a product revision."""
        assessment = self.assess(product_id, revision_id)
        records = []
        for stage in assessment.stages.values():
            records.extend(stage.evidence_records)
        return records

    def assess(
        self, product_id: UUID, revision_id: Optional[UUID] = None
    ) -> ProductLifecycleAssessment:
        """Evaluates the 12 engineering lifecycle stages against actual files, jobs, and evidence."""
        product = self.service.get_product(product_id)
        rev_id = revision_id or product.active_revision_id
        revision = self.service.get_revision(rev_id)
        ws_path = self.service.workspace_path(revision)

        approvals = self.get_stage_approvals(rev_id)
        stages: Dict[str, StageEvaluation] = {}
        readiness_gates: List[ReadinessGate] = []
        critical_blockers: List[str] = []
        total_evidence_count = 0

        # Scan workspace files
        ws_files = list(ws_path.glob("**/*")) if ws_path.exists() else []
        file_map = {f.relative_to(ws_path).as_posix(): f for f in ws_files if f.is_file()}

        # Scan database records
        validations = self.service.list_validation(rev_id)
        reports = self.service.list_reports(rev_id)
        simulation_requests = self.service.list_runs(rev_id)

        # Query integration jobs associated with this product/revision
        jobs: List[Dict[str, Any]] = []
        try:
            with self.service.connection() as db:
                rows = db.execute("SELECT id, workspace_id, status, payload FROM integration_jobs").fetchall()
                for jid, wid, st, payload in rows:
                    pdata = json.loads(payload)
                    # Check if associated with this product revision or workspace
                    j_pid = pdata.get("request", {}).get("parameters", {}).get("product_id")
                    if j_pid == str(product_id) or wid == str(rev_id) or wid == "default_workspace":
                        jobs.append(pdata)
        except Exception:
            pass

        # Evaluate Stage 1: REQUIREMENTS
        s1_ev: List[UnifiedEvidenceRecord] = []
        s1_blockers: List[str] = []
        req_files = [f for rel, f in file_map.items() if rel.startswith("requirements/")]
        for rf in req_files:
            s1_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.REQUIREMENTS,
                    artifact_type=ArtifactType.REQUIREMENTS_SPEC,
                    source_tool="manual_specification",
                    source_file=rf.name,
                    sha256=compute_file_sha256(rf),
                    file_size_bytes=rf.stat().st_size,
                    validation_result="PASSED" if revision.specification.source else "NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                    notes="Engineering specification document",
                )
            )
        spec = revision.specification
        has_spec = spec.vin_nom_v is not None and spec.vout_v is not None
        s1_approval = approvals.get(LifecycleStage.REQUIREMENTS.value)
        if s1_approval and s1_approval["passed"]:
            s1_status = StageStatus.PASSED
        elif has_spec and req_files:
            s1_status = StageStatus.PENDING_VERIFICATION
            s1_blockers.append("Formal engineering requirements review sign-off pending")
        elif has_spec:
            s1_status = StageStatus.IN_PROGRESS
            s1_blockers.append("Requirements specification document missing from requirements/ directory")
        else:
            s1_status = StageStatus.NOT_STARTED
            s1_blockers.append("Product specification parameters have not been defined")

        stages[LifecycleStage.REQUIREMENTS.value] = StageEvaluation(
            stage_id=LifecycleStage.REQUIREMENTS,
            title="Requirements & Specifications",
            category_number=1,
            status=s1_status,
            mandatory=True,
            required_evidence_desc="Reviewed SI requirements specification, standards profile, and isolation requirements",
            actual_evidence_desc=f"{len(s1_ev)} requirements artifacts identified; specification hash: {specification_hash(spec)[:12]}",
            evidence_records=s1_ev,
            blockers=s1_blockers,
            reviewer=s1_approval["reviewer"] if s1_approval else None,
            nav_target="Products / Specification",
        )

        # Evaluate Stage 2: ELECTRICAL_ARCHITECTURE
        s2_ev: List[UnifiedEvidenceRecord] = []
        s2_blockers: List[str] = []
        calc_files = [f for rel, f in file_map.items() if "calc" in rel or "sizing" in rel or "loss" in rel]
        for cf in calc_files:
            s2_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.ELECTRICAL_ARCHITECTURE,
                    artifact_type=ArtifactType.CALCULATION_RECORD,
                    source_tool="calculation_engine",
                    source_file=cf.name,
                    sha256=compute_file_sha256(cf),
                    file_size_bytes=cf.stat().st_size,
                    validation_result="PASSED",
                    engineering_revision=revision.revision_label,
                    notes="Analytical electrical sizing calculations",
                )
            )
        s2_approval = approvals.get(LifecycleStage.ELECTRICAL_ARCHITECTURE.value)
        if s2_approval and s2_approval["passed"]:
            s2_status = StageStatus.PASSED
        elif calc_files:
            s2_status = StageStatus.PENDING_VERIFICATION
            s2_blockers.append("Analytical calculations require formal reviewer verification")
        else:
            s2_status = StageStatus.NOT_STARTED
            s2_blockers.append("No analytical sizing calculations stored in workspace")

        stages[LifecycleStage.ELECTRICAL_ARCHITECTURE.value] = StageEvaluation(
            stage_id=LifecycleStage.ELECTRICAL_ARCHITECTURE,
            title="Electrical Architecture & Sizing",
            category_number=2,
            status=s2_status,
            mandatory=True,
            required_evidence_desc="Analytical sizing calculations for resonant tank, transformer turns ratio, and semiconductor losses",
            actual_evidence_desc=f"{len(s2_ev)} calculation records present",
            evidence_records=s2_ev,
            blockers=s2_blockers,
            reviewer=s2_approval["reviewer"] if s2_approval else None,
            nav_target="DC-DC & Transformer Workspaces",
        )

        # Evaluate Stage 3: CIRCUIT_DESIGN
        s3_ev: List[UnifiedEvidenceRecord] = []
        s3_blockers: List[str] = []
        circuit_files = [f for rel, f in file_map.items() if rel.startswith("circuit/")]
        for cfile in circuit_files:
            atype = ArtifactType.MODELICA_SCRIPT if cfile.suffix == ".mos" else ArtifactType.SPICE_NETLIST
            s3_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.CIRCUIT_DESIGN,
                    artifact_type=atype,
                    source_tool="circuit_workspace",
                    source_file=cfile.name,
                    sha256=compute_file_sha256(cfile),
                    file_size_bytes=cfile.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                    notes=f"Circuit design model / netlist: {cfile.name}",
                )
            )
        s3_approval = approvals.get(LifecycleStage.CIRCUIT_DESIGN.value)
        if s3_approval and s3_approval["passed"]:
            s3_status = StageStatus.PASSED
        elif circuit_files:
            s3_status = StageStatus.IN_PROGRESS
            s3_blockers.append("Circuit netlist/model exists but electrical simulation has not verified operating points")
        else:
            s3_status = StageStatus.NOT_STARTED
            s3_blockers.append("No circuit design netlist or Modelica model found in circuit/ directory")

        stages[LifecycleStage.CIRCUIT_DESIGN.value] = StageEvaluation(
            stage_id=LifecycleStage.CIRCUIT_DESIGN,
            title="Circuit Design & Netlists",
            category_number=3,
            status=s3_status,
            mandatory=True,
            required_evidence_desc="Verified schematic netlist, component selections, and operating topology definition",
            actual_evidence_desc=f"{len(s3_ev)} circuit files present in circuit/",
            evidence_records=s3_ev,
            blockers=s3_blockers,
            reviewer=s3_approval["reviewer"] if s3_approval else None,
            nav_target="Circuit Workspace",
        )

        # Evaluate Stage 4: ELECTRICAL_SIMULATION
        s4_ev: List[UnifiedEvidenceRecord] = []
        s4_blockers: List[str] = []
        sim_files = [f for rel, f in file_map.items() if rel.startswith("simulations/") or f.suffix in (".raw", ".log")]
        for sf in sim_files:
            atype = ArtifactType.WAVEFORM_RAW if sf.suffix == ".raw" else ArtifactType.SIMULATION_OUTPUT
            s4_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.ELECTRICAL_SIMULATION,
                    artifact_type=atype,
                    source_tool="ltspice",
                    source_file=sf.name,
                    sha256=compute_file_sha256(sf),
                    file_size_bytes=sf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s4_approval = approvals.get(LifecycleStage.ELECTRICAL_SIMULATION.value)
        if s4_approval and s4_approval["passed"]:
            s4_status = StageStatus.PASSED
        elif len(jobs) > 0:
            # Check if solver jobs succeeded
            succeeded_jobs = [j for j in jobs if j.get("status") == "SUCCEEDED"]
            if succeeded_jobs:
                s4_status = StageStatus.PENDING_VERIFICATION
                s4_blockers.append("Simulation solver run succeeded (Exit 0), but output waveforms have not passed engineering validation criteria")
            else:
                s4_status = StageStatus.FAILED
                s4_blockers.append("Simulation solver jobs failed or timed out")
        elif sim_files:
            s4_status = StageStatus.PENDING_VERIFICATION
            s4_blockers.append("Simulation output artifacts present but unverified against numerical ripple thresholds")
        else:
            s4_status = StageStatus.NOT_STARTED
            s4_blockers.append("No electrical simulation has been executed in Studio")

        stages[LifecycleStage.ELECTRICAL_SIMULATION.value] = StageEvaluation(
            stage_id=LifecycleStage.ELECTRICAL_SIMULATION,
            title="Electrical Simulation & Waveforms",
            category_number=4,
            status=s4_status,
            mandatory=True,
            required_evidence_desc="Batch simulation runs with parsed output waveforms showing ripple and switching transients",
            actual_evidence_desc=f"{len(jobs)} simulation jobs executed; {len(s4_ev)} simulation output files present",
            evidence_records=s4_ev,
            blockers=s4_blockers,
            reviewer=s4_approval["reviewer"] if s4_approval else None,
            nav_target="Simulation Lab & Waveforms",
        )

        # Evaluate Stage 5: MAGNETIC_ANALYSIS
        s5_ev: List[UnifiedEvidenceRecord] = []
        s5_blockers: List[str] = []
        is_magnetic_applicable = product.category in (Category.TRANSFORMER, Category.DC_DC)
        mag_files = [f for rel, f in file_map.items() if rel.startswith("magnetics/")]
        for mf in mag_files:
            s5_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.MAGNETIC_ANALYSIS,
                    artifact_type=ArtifactType.MAGNETIC_MODEL,
                    source_tool="femm",
                    source_file=mf.name,
                    sha256=compute_file_sha256(mf),
                    file_size_bytes=mf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s5_approval = approvals.get(LifecycleStage.MAGNETIC_ANALYSIS.value)
        if not is_magnetic_applicable:
            s5_status = StageStatus.NOT_APPLICABLE
        elif s5_approval and s5_approval["passed"]:
            s5_status = StageStatus.PASSED
        elif mag_files:
            s5_status = StageStatus.IN_PROGRESS
            s5_blockers.append("Magnetic model script present in magnetics/, but FEMM 4.2 FEA solve has not been executed")
        else:
            s5_status = StageStatus.NOT_STARTED
            s5_blockers.append("No magnetic FEA model or FEMM script found in magnetics/ directory")

        stages[LifecycleStage.MAGNETIC_ANALYSIS.value] = StageEvaluation(
            stage_id=LifecycleStage.MAGNETIC_ANALYSIS,
            title="Magnetic Analysis & FEA",
            category_number=5,
            status=s5_status,
            mandatory=is_magnetic_applicable,
            required_evidence_desc="2D/3D magnetic FEA simulation solve verifying flux density and leakage inductance",
            actual_evidence_desc=f"{len(s5_ev)} magnetic model artifacts present",
            evidence_records=s5_ev,
            blockers=s5_blockers,
            reviewer=s5_approval["reviewer"] if s5_approval else None,
            nav_target="Transformer Workspace / FEMM",
        )

        # Evaluate Stage 6: SCHEMATIC_VERIFICATION
        s6_ev: List[UnifiedEvidenceRecord] = []
        s6_blockers: List[str] = []
        sch_files = [f for rel, f in file_map.items() if f.suffix == ".kicad_sch"]
        erc_reports = [f for rel, f in file_map.items() if "erc" in f.name.lower() and f.suffix in (".json", ".txt")]
        for sf in sch_files:
            s6_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.SCHEMATIC_VERIFICATION,
                    artifact_type=ArtifactType.SCHEMATIC_KICAD,
                    source_tool="kicad",
                    source_file=sf.name,
                    sha256=compute_file_sha256(sf),
                    file_size_bytes=sf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        for ef in erc_reports:
            s6_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.SCHEMATIC_VERIFICATION,
                    artifact_type=ArtifactType.ERC_REPORT,
                    source_tool="kicad-cli",
                    source_file=ef.name,
                    sha256=compute_file_sha256(ef),
                    file_size_bytes=ef.stat().st_size,
                    validation_result="PASSED" if "clean" in ef.name else "NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s6_approval = approvals.get(LifecycleStage.SCHEMATIC_VERIFICATION.value)
        if s6_approval and s6_approval["passed"]:
            s6_status = StageStatus.PASSED
        elif sch_files and erc_reports:
            # Check parsed ERC results
            s6_status = StageStatus.PENDING_VERIFICATION
            s6_blockers.append("ERC report generated; review required for final sign-off")
        elif sch_files:
            s6_status = StageStatus.IN_PROGRESS
            s6_blockers.append("KiCad schematic file present but ERC has not been executed")
        else:
            s6_status = StageStatus.NOT_STARTED
            s6_blockers.append("No KiCad schematic (.kicad_sch) file found in workspace")

        stages[LifecycleStage.SCHEMATIC_VERIFICATION.value] = StageEvaluation(
            stage_id=LifecycleStage.SCHEMATIC_VERIFICATION,
            title="Schematic Capture & ERC",
            category_number=6,
            status=s6_status,
            mandatory=True,
            required_evidence_desc="KiCad schematic file (.kicad_sch) with 0 electrical rule check violations",
            actual_evidence_desc=f"{len(sch_files)} schematics and {len(erc_reports)} ERC reports found",
            evidence_records=s6_ev,
            blockers=s6_blockers,
            reviewer=s6_approval["reviewer"] if s6_approval else None,
            nav_target="KiCad Schematic / ERC",
        )

        # Evaluate Stage 7: PCB_LAYOUT
        s7_ev: List[UnifiedEvidenceRecord] = []
        s7_blockers: List[str] = []
        pcb_files = [f for rel, f in file_map.items() if f.suffix == ".kicad_pcb"]
        for pf in pcb_files:
            s7_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.PCB_LAYOUT,
                    artifact_type=ArtifactType.PCB_KICAD,
                    source_tool="kicad",
                    source_file=pf.name,
                    sha256=compute_file_sha256(pf),
                    file_size_bytes=pf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s7_approval = approvals.get(LifecycleStage.PCB_LAYOUT.value)
        if s7_approval and s7_approval["passed"]:
            s7_status = StageStatus.PASSED
        elif pcb_files:
            s7_status = StageStatus.IN_PROGRESS
            s7_blockers.append("PCB layout file present; stackup and isolation routing unreviewed")
        else:
            s7_status = StageStatus.NOT_STARTED
            s7_blockers.append("No KiCad PCB layout (.kicad_pcb) file found in workspace")

        stages[LifecycleStage.PCB_LAYOUT.value] = StageEvaluation(
            stage_id=LifecycleStage.PCB_LAYOUT,
            title="PCB Layout & Stackup",
            category_number=7,
            status=s7_status,
            mandatory=True,
            required_evidence_desc="KiCad PCB layout (.kicad_pcb) with defined isolation air slots and creepage distances",
            actual_evidence_desc=f"{len(pcb_files)} PCB board layouts found in workspace",
            evidence_records=s7_ev,
            blockers=s7_blockers,
            reviewer=s7_approval["reviewer"] if s7_approval else None,
            nav_target="KiCad PCB Layout",
        )

        # Evaluate Stage 8: PCB_DRC
        s8_ev: List[UnifiedEvidenceRecord] = []
        s8_blockers: List[str] = []
        drc_reports = [f for rel, f in file_map.items() if "drc" in f.name.lower() and f.suffix in (".json", ".txt")]
        for df in drc_reports:
            s8_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.PCB_DRC,
                    artifact_type=ArtifactType.DRC_REPORT,
                    source_tool="kicad-cli",
                    source_file=df.name,
                    sha256=compute_file_sha256(df),
                    file_size_bytes=df.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s8_approval = approvals.get(LifecycleStage.PCB_DRC.value)
        if s8_approval and s8_approval["passed"]:
            s8_status = StageStatus.PASSED
        elif drc_reports:
            s8_status = StageStatus.PENDING_VERIFICATION
            s8_blockers.append("DRC report generated; formal clearance review required")
        elif pcb_files:
            s8_status = StageStatus.IN_PROGRESS
            s8_blockers.append("PCB layout exists but DRC has not been executed")
        else:
            s8_status = StageStatus.NOT_STARTED
            s8_blockers.append("No PCB design rule check (DRC) report available")

        stages[LifecycleStage.PCB_DRC.value] = StageEvaluation(
            stage_id=LifecycleStage.PCB_DRC,
            title="PCB Design-Rule Check (DRC)",
            category_number=8,
            status=s8_status,
            mandatory=True,
            required_evidence_desc="KiCad DRC report with 0 clearance and net violations",
            actual_evidence_desc=f"{len(drc_reports)} DRC reports found in workspace",
            evidence_records=s8_ev,
            blockers=s8_blockers,
            reviewer=s8_approval["reviewer"] if s8_approval else None,
            nav_target="KiCad PCB / DRC",
        )

        # Evaluate Stage 9: THERMAL_MECHANICAL
        s9_ev: List[UnifiedEvidenceRecord] = []
        s9_blockers: List[str] = []
        cad_files = [f for rel, f in file_map.items() if rel.startswith("mechanical/") or f.suffix in (".step", ".stp", ".py")]
        for cdf in cad_files:
            s9_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.THERMAL_MECHANICAL,
                    artifact_type=ArtifactType.BOBBIN_CAD,
                    source_tool="freecad",
                    source_file=cdf.name,
                    sha256=compute_file_sha256(cdf),
                    file_size_bytes=cdf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s9_approval = approvals.get(LifecycleStage.THERMAL_MECHANICAL.value)
        if s9_approval and s9_approval["passed"]:
            s9_status = StageStatus.PASSED
        elif cad_files:
            s9_status = StageStatus.IN_PROGRESS
            s9_blockers.append("Mechanical script present, but 3D STEP solid model export has not been generated")
        else:
            s9_status = StageStatus.NOT_STARTED
            s9_blockers.append("No mechanical CAD script or 3D STEP model found in mechanical/ directory")

        stages[LifecycleStage.THERMAL_MECHANICAL.value] = StageEvaluation(
            stage_id=LifecycleStage.THERMAL_MECHANICAL,
            title="Thermal & Mechanical Evaluation",
            category_number=9,
            status=s9_status,
            mandatory=False,
            required_evidence_desc="3D solid model export (STEP) and thermal dissipation loss budget",
            actual_evidence_desc=f"{len(s9_ev)} mechanical/thermal files present",
            evidence_records=s9_ev,
            blockers=s9_blockers,
            reviewer=s9_approval["reviewer"] if s9_approval else None,
            nav_target="FreeCAD 3D Bobbin",
        )

        # Evaluate Stage 10: BOM_REVIEW
        s10_ev: List[UnifiedEvidenceRecord] = []
        s10_blockers: List[str] = []
        bom_files = [f for rel, f in file_map.items() if "bom" in f.name.lower() and f.suffix in (".csv", ".json", ".xlsx")]
        for bf in bom_files:
            s10_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.BOM_REVIEW,
                    artifact_type=ArtifactType.BOM_FILE,
                    source_tool="bom_service",
                    source_file=bf.name,
                    sha256=compute_file_sha256(bf),
                    file_size_bytes=bf.stat().st_size,
                    validation_result="NOT_EVALUATED",
                    engineering_revision=revision.revision_label,
                )
            )
        s10_approval = approvals.get(LifecycleStage.BOM_REVIEW.value)
        if s10_approval and s10_approval["passed"]:
            s10_status = StageStatus.PASSED
        elif bom_files:
            s10_status = StageStatus.PENDING_VERIFICATION
            s10_blockers.append("Structured BOM CSV present; component voltage/thermal rating verification pending")
        else:
            s10_status = StageStatus.NOT_STARTED
            s10_blockers.append("No structured Bill of Materials (.csv/.json) file found in workspace")

        stages[LifecycleStage.BOM_REVIEW.value] = StageEvaluation(
            stage_id=LifecycleStage.BOM_REVIEW,
            title="BOM & Component Review",
            category_number=10,
            status=s10_status,
            mandatory=True,
            required_evidence_desc="Structured Bill of Materials (BOM) with manufacturer part numbers and dielectric ratings",
            actual_evidence_desc=f"{len(s10_ev)} structured BOM files present in workspace",
            evidence_records=s10_ev,
            blockers=s10_blockers,
            reviewer=s10_approval["reviewer"] if s10_approval else None,
            nav_target="BOM Review",
        )

        # Evaluate Stage 11: ENGINEERING_VALIDATION
        s11_ev: List[UnifiedEvidenceRecord] = []
        s11_blockers: List[str] = []
        for val in validations:
            s11_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.ENGINEERING_VALIDATION,
                    artifact_type=ArtifactType.VALIDATION_CHECK,
                    source_tool="validation_service",
                    source_file=val.check.check_id,
                    sha256=val.evidence_sha256 or "",
                    validation_result=val.check.status.value,
                    engineering_revision=revision.revision_label,
                    reviewer_approval=val.check.reviewer,
                    notes=val.check.notes,
                )
            )
        for rep in reports:
            s11_ev.append(
                UnifiedEvidenceRecord(
                    product_id=product_id,
                    revision_id=rev_id,
                    stage_id=LifecycleStage.ENGINEERING_VALIDATION,
                    artifact_type=ArtifactType.ENGINEERING_REPORT,
                    source_tool="report_generator",
                    source_file=Path(rep.report_path).name,
                    sha256=rep.input_hash,
                    validation_result="NOT_EVALUATED" if rep.warnings else "PASSED",
                    engineering_revision=revision.revision_label,
                    notes=f"Draft dossier with {len(rep.warnings)} warnings",
                )
            )
        s11_approval = approvals.get(LifecycleStage.ENGINEERING_VALIDATION.value)
        if s11_approval and s11_approval["passed"]:
            s11_status = StageStatus.PASSED
        elif len(validations) > 0:
            failed_checks = [v for v in validations if v.check.status.value == "fail"]
            if failed_checks:
                s11_status = StageStatus.FAILED
                s11_blockers.append(f"{len(failed_checks)} engineering validation checks failed criteria")
            else:
                s11_status = StageStatus.PENDING_VERIFICATION
                s11_blockers.append("Validation checks recorded; final engineering dossier sign-off pending")
        else:
            s11_status = StageStatus.NOT_STARTED
            s11_blockers.append("Zero validation records logged in Studio for this revision")

        stages[LifecycleStage.ENGINEERING_VALIDATION.value] = StageEvaluation(
            stage_id=LifecycleStage.ENGINEERING_VALIDATION,
            title="Engineering Validation & Verification",
            category_number=11,
            status=s11_status,
            mandatory=True,
            required_evidence_desc="Append-only validation records with numerical thresholds and evidence SHA-256 hashes",
            actual_evidence_desc=f"{len(validations)} validation checks and {len(reports)} engineering reports",
            evidence_records=s11_ev,
            blockers=s11_blockers,
            reviewer=s11_approval["reviewer"] if s11_approval else None,
            nav_target="Validation Panel",
        )

        # Collect total evidence count
        for stg in stages.values():
            total_evidence_count += len(stg.evidence_records)
            if stg.mandatory and stg.status != StageStatus.PASSED and stg.status != StageStatus.NOT_APPLICABLE:
                for b in stg.blockers:
                    critical_blockers.append(f"[{stg.title}] {b}")

        # Evaluate Stage 12: PROTOTYPE_READINESS
        s12_blockers: List[str] = []
        mandatory_unpassed = [
            stg for stg in stages.values()
            if stg.mandatory and stg.status != StageStatus.PASSED and stg.status != StageStatus.NOT_APPLICABLE
        ]
        s12_approval = approvals.get(LifecycleStage.PROTOTYPE_READINESS.value)
        if len(mandatory_unpassed) > 0:
            s12_status = StageStatus.BLOCKED
            s12_blockers.append(f"Prototype blocked: {len(mandatory_unpassed)} mandatory engineering stages remain unpassed")
            prototype_ready = False
        elif not s12_approval or not s12_approval["passed"]:
            s12_status = StageStatus.BLOCKED
            s12_blockers.append("All technical stages completed, but formal Prototype Sign-off Review has not been granted")
            prototype_ready = False
        else:
            s12_status = StageStatus.PASSED
            prototype_ready = True

        stages[LifecycleStage.PROTOTYPE_READINESS.value] = StageEvaluation(
            stage_id=LifecycleStage.PROTOTYPE_READINESS,
            title="Prototype Readiness Review",
            category_number=12,
            status=s12_status,
            mandatory=True,
            required_evidence_desc="All mandatory engineering gates PASSED and formal engineering sign-off recorded",
            actual_evidence_desc="Prototype Authorization Gate: " + ("AUTHORIZED" if prototype_ready else "BLOCKED"),
            evidence_records=[],
            blockers=s12_blockers,
            reviewer=s12_approval["reviewer"] if s12_approval else None,
            nav_target="Prototype Gate Review",
        )

        # Build Readiness Gates
        for stage_key, num, title, mandatory, req_desc, _ in self.STAGE_METADATA:
            stg = stages.get(stage_key.value)
            st_val = stg.status if stg else StageStatus.NOT_STARTED
            is_passed = st_val == StageStatus.PASSED or st_val == StageStatus.NOT_APPLICABLE
            readiness_gates.append(
                ReadinessGate(
                    gate_id=f"gate_{stage_key.value}",
                    title=f"Gate {num}: {title}",
                    stage_id=stage_key,
                    mandatory=mandatory,
                    passed=is_passed,
                    status=st_val.value,
                    reason=stg.blockers[0] if (stg and stg.blockers) else ("Passed" if is_passed else "Pending"),
                )
            )

        # Overall Status
        if prototype_ready:
            overall_status = StageStatus.PASSED
        elif any(stg.status == StageStatus.FAILED for stg in stages.values()):
            overall_status = StageStatus.FAILED
        elif any(stg.status in (StageStatus.IN_PROGRESS, StageStatus.PENDING_VERIFICATION) for stg in stages.values()):
            overall_status = StageStatus.IN_PROGRESS
        else:
            overall_status = StageStatus.NOT_STARTED

        return ProductLifecycleAssessment(
            product_id=product_id,
            product_code=product.code,
            revision_id=rev_id,
            revision_label=revision.revision_label,
            overall_status=overall_status,
            prototype_ready=prototype_ready,
            stages=stages,
            readiness_gates=readiness_gates,
            critical_blockers=critical_blockers,
            total_evidence_count=total_evidence_count,
            last_assessed_at=now(),
        )
