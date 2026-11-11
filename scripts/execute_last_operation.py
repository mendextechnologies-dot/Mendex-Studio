from pathlib import Path
from mendex_core.service import StudioService

root = Path.cwd()
studio = StudioService(root)
service = studio.design
design_id = "e4b793f0-9f5e-4c9c-8e8d-1ff254ef5f15"
design = service.get_design(design_id)
ws_path = root / "workspaces" / design.workspace_id
ws_path.mkdir(parents=True, exist_ok=True)

print(f"=== DESIGN: {design.title} ===")
print(f"Initial Active Rev: {design.get_active_revision().label}")

# 1. Run Rev 1 simulation
print("Running Rev 1 LTspice simulation...")
sim1 = service.run_ltspice_simulation(design.id, ws_path)
ripple1_mv = sim1.vout_ripple_pk_pk_v * 1000.0
print(f"Rev 1 Result: Success={sim1.success}, Status={sim1.convergence_status}, Vout_mean={sim1.vout_mean_v:.3f}V, Ripple={ripple1_mv:.2f}mV, Verdict={sim1.summary_verdict}")

# 2. AI Closed-Loop Diagnostics
proposal = service.propose_iteration(design.id, sim1)
if proposal:
    print(f"\nProposal Generated: {proposal.rationale}")
    print(f"Action: Adjust {proposal.parameter_to_change} from {proposal.current_value:.3e} -> {proposal.proposed_value:.3e}")
    proposal.approval_status = "APPROVED"

    # 3. Apply Iteration & Branch Rev 2
    res = service.apply_iteration(design.id, proposal)
    print(f"\nIteration Applied: Rev {res.get('revision_index')} created.")

    # 4. Simulate Rev 2
    print("Running Rev 2 LTspice simulation to verify convergence...")
    sim2 = service.run_ltspice_simulation(design.id, ws_path)
    ripple2_mv = sim2.vout_ripple_pk_pk_v * 1000.0
    print(f"Rev 2 Result: Success={sim2.success}, Status={sim2.convergence_status}, Vout_mean={sim2.vout_mean_v:.3f}V, Ripple={ripple2_mv:.2f}mV, Verdict={sim2.summary_verdict}")
    print(f"Ripple Reduction: {ripple1_mv:.2f}mV -> {ripple2_mv:.2f}mV (Delta: -{(ripple1_mv - ripple2_mv):.2f}mV)")
else:
    print("\nRev 1 already satisfies all specifications without violations.")
