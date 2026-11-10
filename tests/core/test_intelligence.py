"""Tests for Mendex Engineering Intelligence Foundation."""
import pytest
from mendex_core.intelligence import (
    EngineeringKnowledgeService,
    DeterministicCalculationService,
    ModelRegistry,
    LocalRuleEngineBackend,
    EngineeringReasoningOrchestrator,
    EngineeringBenchmarkRegistry,
)
from mendex_core.service import StudioService


def test_knowledge_service_formulas_and_materials():
    knowledge = EngineeringKnowledgeService()
    
    # 1. Formulas
    formulas = knowledge.list_formulas()
    assert len(formulas) >= 5
    dowell = knowledge.get_formula("EQ-DOWELL-01")
    assert dowell is not None
    assert "F_R" in dowell.output
    assert "sinh" in dowell.latex

    # 2. Materials
    materials = knowledge.list_materials()
    assert len(materials) >= 2
    ferrite = knowledge.get_material("MAT-FERRITE-N87")
    assert ferrite is not None
    assert ferrite.properties["saturation_flux_density_25C"] == 0.49

    # 3. Standards
    standards = knowledge.list_standards()
    assert len(standards) >= 2
    iec = knowledge.get_standard("STD-IEC-62368-1")
    assert iec is not None
    assert "clearance" in iec.rules["reinforced_insulation_230V_pollution_2"].lower()


def test_deterministic_calculation_service():
    calc = DeterministicCalculationService()

    # 1. Skin depth: f=100kHz in Copper at 100°C -> delta ~ 0.237 mm
    res_skin = calc.calculate_skin_depth(100e3, temperature_c=100.0)
    assert res_skin.verified
    assert res_skin.origin == "calculated"
    assert 0.20 < res_skin.outputs["skin_depth_mm"] < 0.26

    # 2. Dowell Factor: h=0.237mm, delta=0.237mm (xi=1.0), m=2 layers -> F_R ~ 1.41
    res_dowell = calc.calculate_dowell_factor(0.237e-3, 0.237e-3, num_layers=2)
    assert res_dowell.verified
    assert 1.35 < res_dowell.outputs["F_R"] < 1.45

    # 3. Flyback Sizing: 24V -> 1000V, 100mA, 100kHz
    res_fly = calc.calculate_flyback_sizing(vin_min_v=18.0, vin_nom_v=24.0, vout_v=1000.0, iout_a=0.1, fsw_hz=100e3)
    assert res_fly.outputs["p_out_w"] == 100.0
    assert res_fly.outputs["primary_inductance_uh"] > 0
    assert res_fly.outputs["turns_ratio_np_ns"] > 0

    # 4. Steinmetz Core Loss: 100kHz, 0.1T, volume = 1e-5 m^3
    res_core = calc.calculate_steinmetz_loss(100e3, 0.1, core_volume_m3=1e-5)
    assert res_core.outputs["total_core_loss_w"] > 0

    # 5. Semiconductor Losses: 5A, 65mOhm, Eon=142uJ, Eoff=68uJ, 100kHz
    res_semi = calc.calculate_semiconductor_losses(i_rms_a=5.0, r_ds_on_ohm=0.065, e_on_j=142e-6, e_off_j=68e-6, fsw_hz=100e3)
    assert res_semi.outputs["conduction_loss_w"] > 0
    assert res_semi.outputs["switching_loss_w"] > 0
    assert res_semi.outputs["total_loss_w"] == res_semi.outputs["conduction_loss_w"] + res_semi.outputs["switching_loss_w"]

    # 6. LC Resonance: 10uH, 100nF -> ~159.155 kHz
    res_lc = calc.calculate_lc_resonance(inductance_h=10e-6, capacitance_f=100e-9)
    assert 158e3 < res_lc.outputs["resonant_frequency_hz"] < 161e3

    # Boundary and error validation
    with pytest.raises(ValueError):
        calc.calculate_skin_depth(-10)
    with pytest.raises(ValueError):
        calc.calculate_lc_resonance(0, 10)


def test_reasoning_orchestrator_and_studio_service(tmp_path):
    svc = StudioService(tmp_path)
    assert hasattr(svc, "intelligence")

    # Ask Dowell question
    resp_dowell = svc.advise_engineering("How does Dowell calculate AC winding loss?")
    assert resp_dowell["provider"] == "local_engineering_rules"
    assert "F_R" in resp_dowell["reply"]
    assert len(resp_dowell["suggested_actions"]) > 0

    # Ask SPICE circuit question
    resp_spice = svc.advise_engineering("I want to simulate transient ripple for my DC-DC converter")
    assert any(r["target_tool_or_module"] == "ltspice" for r in resp_spice["recommendations"])

    # Ask PCB safety question
    resp_pcb = svc.advise_engineering("What is the clearance requirement for 400V high voltage PCB?")
    assert any(r["target_tool_or_module"] == "kicad" for r in resp_pcb["recommendations"])


def test_engineering_benchmark_evaluation():
    benchmarks = EngineeringBenchmarkRegistry()
    cases = benchmarks.list_cases()
    assert len(cases) >= 3

    # Perfect prediction test
    predictions = {
        "BM-SKIN-100KHZ": {"skin_depth_mm": 0.237},
        "BM-DOWELL-2LAYER": {"F_R": 1.406},
        "BM-LC-RESONANCE": {"resonant_frequency_hz": 159155.0},
    }
    metrics = benchmarks.evaluate_predictions(predictions)
    assert metrics.all_within_tolerance
    assert metrics.accuracy_percentage == 100.0
    assert metrics.passed_cases == 3
