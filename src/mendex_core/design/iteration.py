"""AI-assisted design iteration engine for closed-loop optimization in Mendex Studio v2.0.

Analyzes real simulation results against requirements, performs analytical calculations
to resolve violations (e.g. output ripple, voltage drop), formulates approval proposals
with trade-offs, branches new immutable revisions, and compares before/after results.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .models import EngineeringDesign, DesignRevision, Requirement, DesignStatus
from .ltspice_runner import LTspiceRunner, LTspiceSimulationResult
from .sync import CrossToolSyncService
from .generators import LTspiceNetlistGenerator, KiCadSchematicGenerator


class DesignIterationProposal(BaseModel):
    """Proposal formulated by AI Copilot to fix an unmet requirement."""
    parameter_to_change: str
    current_value: float
    proposed_value: float
    unit: str
    rationale: str
    trade_offs: str
    target_requirement: str
    observed_metric: float
    required_metric: float
    approval_status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED


class DesignIterationEngine:
    """Orchestrates closed-loop iteration with mandatory human-in-the-loop approval."""

    @staticmethod
    def analyze_simulation_and_propose(
        design: EngineeringDesign,
        sim_result: LTspiceSimulationResult,
    ) -> Optional[DesignIterationProposal]:
        """Examines simulation result against requirements and formulates an optimization proposal."""
        active_rev = design.get_active_revision()
        if not active_rev:
            return None

        ir = active_rev.ir

        # Check for ripple failure
        for req in design.requirements:
            p_name = req.parameter.lower()
            if p_name in ("ripple", "vout_ripple", "voltage_ripple"):
                max_ripple = req.max_value or (0.02 * req.target_value if req.target_value else 0.05)
                actual_ripple = sim_result.vout_ripple_pk_pk_v
                if actual_ripple > max_ripple:
                    # Analytical calculation: Delta_V = Delta_IL / (8 * fsw * C)
                    # To reduce ripple by ratio, scale C by (actual / target)
                    ratio = actual_ripple / max(max_ripple, 0.001)
                    curr_c_comp = ir.get_component("C1") or ir.get_component("C")
                    curr_c_val = curr_c_comp.value if curr_c_comp else 100e-6
                    new_c_val = curr_c_val * max(ratio * 1.25, 1.5)  # add 25% margin

                    return DesignIterationProposal(
                        parameter_to_change="C",
                        current_value=curr_c_val,
                        proposed_value=new_c_val,
                        unit="F",
                        target_requirement=f"Output Voltage Ripple <= {max_ripple*1e3:.1f}mV",
                        observed_metric=actual_ripple,
                        required_metric=max_ripple,
                        rationale=(
                            f"Output voltage ripple observed is {actual_ripple*1e3:.1f}mV, exceeding requirement threshold of {max_ripple*1e3:.1f}mV. "
                            f"According to LC filter ripple relation Delta_V = Delta_I_L / (8 * f_sw * C), increasing filter capacitance from "
                            f"{curr_c_val*1e6:.1f}uF to {new_c_val*1e6:.1f}uF will bring steady-state ripple down below limit."
                        ),
                        trade_offs=(
                            "Reduces voltage ripple by ~60-80% and improves load transient response. "
                            "Trade-off: Increases capacitor physical package size and slightly increases inrush charging current at startup."
                        ),
                    )

            elif p_name in ("vout", "target_voltage"):
                target_v = req.target_value
                measured_v = sim_result.vout_mean_v
                tol = (req.tolerance_pct or 5.0) / 100.0
                if abs(measured_v - target_v) / max(target_v, 0.01) > tol:
                    # Sizing proposal: adjust duty cycle or feedback resistor
                    return DesignIterationProposal(
                        parameter_to_change="d_nom",
                        current_value=ir.parameters.get("d_nom", ir.parameters.get("D", None)).value if "d_nom" in ir.parameters else 0.5,
                        proposed_value=target_v / max(ir.parameters.get("Vin", ir.parameters.get("vin", None)).value, 1.0) if "Vin" in ir.parameters else 0.45,
                        unit="ratio",
                        target_requirement=f"Output Voltage {target_v:.2f}V +- {tol*100:.1f}%",
                        observed_metric=measured_v,
                        required_metric=target_v,
                        rationale=f"Output voltage measured {measured_v:.2f}V vs target {target_v:.2f}V. Adjust duty cycle to compensate for diode/switch conduction drops.",
                        trade_offs="Re-centers output voltage within regulation window.",
                    )

        return None

    @staticmethod
    def apply_iteration_proposal(
        design: EngineeringDesign,
        proposal: DesignIterationProposal,
        root_dir: Path,
        runner: LTspiceRunner,
    ) -> Dict[str, Any]:
        """Applies proposal to create new revision, regenerate netlist, and re-run simulation."""
        if proposal.approval_status != "APPROVED":
            raise PermissionError("Iteration proposal cannot be applied without explicit engineer approval.")

        active_rev = design.get_active_revision()
        if not active_rev:
            raise ValueError("Design has no active revision.")

        # 1. Update IR in new revision
        new_ir = active_rev.ir.model_copy(deep=True)
        param_name = proposal.parameter_to_change
        if param_name in new_ir.parameters:
            new_ir.parameters[param_name].value = proposal.proposed_value

        # Also update matching component
        for comp in new_ir.components:
            if comp.designator in (param_name, f"{param_name}1"):
                comp.value = proposal.proposed_value

        # 2. Branch Revision
        new_rev_index = len(design.revisions) + 1
        artifacts_dir = root_dir / "workspaces" / design.workspace_id / "generated_artifacts" / f"rev_{new_rev_index}"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 3. Regenerate native netlist & schematic
        net_content = LTspiceNetlistGenerator.generate_netlist(new_ir)
        net_path = artifacts_dir / f"{new_ir.topology.lower()}_circuit.net"
        net_path.write_text(net_content, encoding="utf-8")

        kicad_files = KiCadSchematicGenerator.export_project(new_ir, artifacts_dir / "kicad")

        new_rev = DesignRevision(
            design_id=design.id,
            revision_index=new_rev_index,
            label=f"Rev {new_rev_index}",
            ir=new_ir,
            summary=f"Optimized {proposal.parameter_to_change} from {proposal.current_value:.6g} to {proposal.proposed_value:.6g} to meet {proposal.target_requirement}",
        )
        design.revisions.append(new_rev)
        design.active_revision_id = new_rev.id
        design.status = DesignStatus.IN_REVIEW

        # 4. Re-run simulation
        new_sim_result = runner.run_simulation(net_path, requirements=design.requirements)

        return {
            "success": new_sim_result.success,
            "new_revision_label": new_rev.label,
            "revision_index": new_rev_index,
            "parameter_changed": proposal.parameter_to_change,
            "old_value": proposal.current_value,
            "new_value": proposal.proposed_value,
            "simulation_result": new_sim_result,
            "ripple_before_v": proposal.observed_metric,
            "ripple_after_v": new_sim_result.vout_ripple_pk_pk_v,
            "mean_vout_after_v": new_sim_result.vout_mean_v,
            "summary_verdict": new_sim_result.summary_verdict,
        }
