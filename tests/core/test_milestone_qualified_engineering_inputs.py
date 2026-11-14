"""Verification tests for Milestone: Qualified Engineering Inputs (G05, G06, G08, G09, G10).

Covers:
- G10: IEC 60664-1 Table F.4 material group differentiation, negative/zero voltage rejection, fail-closed behavior.
- G08: Steinmetz loss coefficient conventions (empirical kHz vs SI Hz) parity across calculators and domain validation.
- G09: Truthful thermal qualification, removal of fabricated heatsink passes, and IPC-2221 trace formula labeling.
- G05: Sourced, exact MPNs, manufacturers, ratings, and pin maps on the coherent buck reference.
- G06: First-class Specification schema extension and Requirement verification links.
"""
from __future__ import annotations

import math
import pytest

from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
from integrations.calculations.power_losses import calculate_core_loss_steinmetz
from integrations.calculations.thermal_sizing import (
    calculate_semiconductor_thermal,
    calculate_magnetic_thermal,
    calculate_ipc2152_trace_thermal,
)
from mendex_core.intelligence.calculations import DeterministicCalculationService
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.models import Specification
from mendex_core.engineering_records.models import Requirement


# ==============================================================================
# G10: Insulation Coordination and Fail-Closed Creepage Verification
# ==============================================================================

def test_g10_creepage_material_groups_yield_distinct_iec60664_distances():
    """Verify that IEC 60664-1 Table F.4 resolves different creepage distances

    for Material Groups I, II, IIIa, IIIb at 230V working voltage,
    resolving the duplicate 5.0mm probe counterexample in boundary-results.json.
    """
    # 230V basic insulation per Table F.4
    d_basic_i = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="I", insulation_type="basic")
    d_basic_ii = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="II", insulation_type="basic")
    d_basic_iiia = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="IIIa", insulation_type="basic")
    d_basic_iiib = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="IIIb", insulation_type="basic")

    assert d_basic_i == 1.25, f"Material Group I should be 1.25mm, got {d_basic_i}"
    assert d_basic_ii == 1.80, f"Material Group II should be 1.80mm, got {d_basic_ii}"
    assert d_basic_iiia == 2.50, f"Material Group IIIa should be 2.50mm, got {d_basic_iiia}"
    assert d_basic_iiib == 2.50, f"Material Group IIIb should be 2.50mm, got {d_basic_iiib}"

    # 230V reinforced insulation (doubled)
    d_reinf_i = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="I", insulation_type="reinforced")
    d_reinf_ii = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="II", insulation_type="reinforced")
    d_reinf_iiia = CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="IIIa", insulation_type="reinforced")

    assert d_reinf_i == 2.50, f"Material Group I reinforced should be 2.50mm, got {d_reinf_i}"
    assert d_reinf_ii == 3.60, f"Material Group II reinforced should be 3.60mm, got {d_reinf_ii}"
    assert d_reinf_iiia == 5.00, f"Material Group IIIa reinforced should be 5.00mm, got {d_reinf_iiia}"

    # Verify that Material Group I, II, and IIIa are NOT identical
    assert len({d_basic_i, d_basic_ii, d_basic_iiia}) == 3


def test_g10_creepage_rejects_negative_or_zero_voltage():
    """Verify that calculate_iec60664_creepage fails closed on non-positive voltages

    instead of blindly calling abs() and returning 5.0mm.
    """
    with pytest.raises(ValueError, match="strictly positive"):
        CopperKiCadAdapter.calculate_iec60664_creepage(-230.0)

    with pytest.raises(ValueError, match="strictly positive"):
        CopperKiCadAdapter.calculate_iec60664_creepage(0.0)


def test_g10_creepage_rejects_invalid_material_group_and_pollution_degree():
    """Verify strict validation of material groups and pollution degrees."""
    with pytest.raises(ValueError, match="Invalid material group"):
        CopperKiCadAdapter.calculate_iec60664_creepage(230.0, material_group="IV")

    with pytest.raises(ValueError, match="Pollution degree"):
        CopperKiCadAdapter.calculate_iec60664_creepage(230.0, pollution_degree=4)


# ==============================================================================
# G08: Magnetic Loss Coefficient Conventions Parity Verification
# ==============================================================================

def test_g08_steinmetz_loss_paths_concur_under_declared_conventions():
    """Verify that calculate_core_loss_steinmetz and calculate_steinmetz_loss

    yield identical numerical results under both empirical kHz and SI Hz conventions,
    resolving the 1000x discrepancy counterexample in engineering-counterexamples.json.
    """
    service = DeterministicCalculationService()

    # Case 1: Datasheet empirical kHz convention (TDK N87 benchmark)
    # f = 100 kHz (100,000 Hz), B = 0.1 T, V = 15 cm^3 (15e-6 m^3), k = 7.13, alpha = 1.42, beta = 2.65
    res1 = calculate_core_loss_steinmetz(
        material="N87",
        k=7.13,
        alpha=1.42,
        beta=2.65,
        frequency_hz=100000.0,
        b_peak_t=0.1,
        core_volume_m3=15e-6,
        convention="empirical_khz",
    )
    res2 = service.calculate_steinmetz_loss(
        frequency_hz=100000.0,
        b_max_t=0.1,
        core_volume_m3=15e-6,
        cm=7.13,
        alpha=1.42,
        beta=2.65,
        convention="empirical_khz",
    )

    assert abs(res1.volumetric_loss_w_m3 - res2.outputs["volumetric_loss_w_m3"]) < 0.05
    assert abs(res1.total_core_loss_w - res2.outputs["total_core_loss_w"]) < 1e-4

    # Case 2: SI Hz convention benchmark
    # f = 1000 Hz, B = 0.1 T, V = 1e-6 m^3, Cm = 1.0, alpha = 2.0, beta = 2.0
    # Expected Pv = 1.0 * (1000^2) * (0.1^2) = 1e6 * 0.01 = 10,000 W/m^3
    # Total loss = 10000 * 1e-6 = 0.01 W
    res1_si = calculate_core_loss_steinmetz(
        material="Fixture",
        k=1.0,
        alpha=2.0,
        beta=2.0,
        frequency_hz=1000.0,
        b_peak_t=0.1,
        core_volume_m3=1e-6,
        convention="si_hz",
    )
    res2_si = service.calculate_steinmetz_loss(
        frequency_hz=1000.0,
        b_max_t=0.1,
        core_volume_m3=1e-6,
        cm=1.0,
        alpha=2.0,
        beta=2.0,
        convention="si_hz",
    )

    assert abs(res1_si.volumetric_loss_w_m3 - 10000.0) < 1e-3
    assert abs(res2_si.outputs["volumetric_loss_w_m3"] - 10000.0) < 1e-3
    assert abs(res1_si.total_core_loss_w - 0.01) < 1e-5
    assert abs(res2_si.outputs["total_core_loss_w"] - 0.01) < 1e-5


def test_g08_steinmetz_rejects_non_positive_coefficients_or_invalid_conventions():
    """Verify fail-closed rejection of unphysical coefficients."""
    service = DeterministicCalculationService()
    with pytest.raises(ValueError, match="strictly positive"):
        calculate_core_loss_steinmetz("N87", k=-5.0, alpha=1.42, beta=2.65, frequency_hz=100e3, b_peak_t=0.1, core_volume_m3=1e-5)

    with pytest.raises(ValueError, match="Unknown Steinmetz convention"):
        calculate_core_loss_steinmetz("N87", k=7.13, alpha=1.42, beta=2.65, frequency_hz=100e3, b_peak_t=0.1, core_volume_m3=1e-5, convention="invalid_unit")

    with pytest.raises(ValueError, match="Unknown Steinmetz convention"):
        service.calculate_steinmetz_loss(frequency_hz=100e3, b_max_t=0.1, core_volume_m3=1e-5, convention="bogus")


# ==============================================================================
# G09: Thermal Sizing Qualification & Attribution Verification
# ==============================================================================

def test_g09_trace_width_formula_label_attributes_ipc2221_empirical_derivation():
    """Verify that calculate_ipc2152_trace_thermal attributes the power-law equation

    truthfully to IPC-2221 / IPC-2152 conservative derivation.
    """
    res = calculate_ipc2152_trace_thermal(current_a=5.0, target_delta_t_c=10.0, copper_thickness_oz=1.0)
    assert "IPC-2221 / IPC-2152 Conservative Derivation" in res.formula
    assert res.min_trace_width_mm > 0.0


def test_g09_semiconductor_thermal_requires_heatsink_specification_to_claim_pass():
    """Verify that when no heatsink is specified (r_th_sa_c_w == 0), the calculator

    reports HEATSINK_SIZED with the required heatsink rating, and only grants
    PASS_DERATED when an explicit heatsink satisfying the limit is supplied.
    """
    # 1. Unspecified heatsink (r_th_sa_c_w == 0.0)
    res_unsized = calculate_semiconductor_thermal(
        part_number="IPB65R190CFD",
        p_loss_w=5.0,
        t_ambient_c=25.0,
        t_j_max_c=150.0,
        derating_factor=0.80,
        r_th_jc_c_w=1.5,
        r_th_cs_c_w=0.5,
        r_th_sa_c_w=0.0,
    )
    assert res_unsized.status == "HEATSINK_SIZED"
    assert res_unsized.heatsink_required_c_w > 0.0

    # 2. Supplied heatsink satisfying the requirement
    res_sized = calculate_semiconductor_thermal(
        part_number="IPB65R190CFD",
        p_loss_w=5.0,
        t_ambient_c=25.0,
        t_j_max_c=150.0,
        derating_factor=0.80,
        r_th_jc_c_w=1.5,
        r_th_cs_c_w=0.5,
        r_th_sa_c_w=res_unsized.heatsink_required_c_w * 0.9,
    )
    assert res_sized.status == "PASS_DERATED"

    # 3. Inadequate heatsink causes over-temperature
    res_hot = calculate_semiconductor_thermal(
        part_number="IPB65R190CFD",
        p_loss_w=5.0,
        t_ambient_c=25.0,
        t_j_max_c=150.0,
        derating_factor=0.80,
        r_th_jc_c_w=1.5,
        r_th_cs_c_w=0.5,
        r_th_sa_c_w=50.0,  # Far too high
    )
    assert res_hot.status == "OVER_TEMPERATURE"


# ==============================================================================
# G05: BOM Parts & Sourced Model Qualification Verification
# ==============================================================================

def test_g05_buck_synthesis_components_resolve_exact_mpns_ratings_and_footprints():
    """Verify that all components synthesized for the coherent buck reference

    have exact manufacturer part numbers, manufacturers, official footprints,
    and reviewed pin maps.
    """
    ir = CandidateSynthesisEngine._build_buck_ir(
        vin_nom=12.0,
        vout=5.0,
        iout=1.0,
        fsw=100000.0,
        l_val=47e-6,
        c_val=47e-6,
    )

    assert len(ir.components) >= 6
    for comp in ir.components:
        assert comp.mpn, f"Component {comp.designator} must have an exact MPN"
        assert comp.manufacturer, f"Component {comp.designator} must have a manufacturer"
        assert comp.footprint, f"Component {comp.designator} must have an official footprint"
        assert ":" in comp.footprint, f"Footprint {comp.footprint} must be fully library-qualified"

    # Inspect power stage components specifically
    q1 = next(c for c in ir.components if c.designator == "Q1")
    assert q1.mpn == "IPD036N04L G"
    assert q1.manufacturer == "Infineon Technologies"
    assert q1.footprint == "Package_TO_SOT_SMD:TO-252-2"
    assert q1.parameters.get("pin_map") == {"g": "1", "d": "2", "s": "3"}

    l1 = next(c for c in ir.components if c.designator == "L1")
    assert l1.mpn == "SRP1265A-220M"
    assert l1.footprint == "Inductor_SMD:L_1210_3225Metric"

    c1 = next(c for c in ir.components if c.designator == "C1")
    assert c1.mpn == "C1210C106K5RACTU"
    assert c1.footprint == "Capacitor_SMD:C_1210_3225Metric"


# ==============================================================================
# G06: Typed Specification & Requirement Verification Links
# ==============================================================================

def test_g06_specification_and_requirements_link_verification_methods():
    """Verify that Specification supports complete power converter engineering fields

    and Requirement supports explicit verification methods and status links.
    """
    spec = Specification(
        vin_min_v=10.0,
        vin_nom_v=12.0,
        vin_max_v=14.0,
        vout_v=5.0,
        iout_a=1.0,
        switching_frequency_hz=200000.0,
        target_efficiency_pct=92.0,
        vout_ripple_max_mv=50.0,
        ambient_temperature_c=25.0,
        ambient_temperature_k=298.15,
        max_pcb_width_mm=50.0,
        max_pcb_height_mm=35.0,
    )

    assert spec.target_efficiency_pct == 92.0
    assert spec.vout_ripple_max_mv == 50.0
    assert spec.ambient_temperature_c == 25.0

    # Test thermodynamic consistency validator
    with pytest.raises(ValueError, match="thermodynamically consistent"):
        Specification(
            vin_nom_v=12.0,
            ambient_temperature_c=25.0,
            ambient_temperature_k=350.0,  # Inconsistent
        )

    # Test ripple vs nominal voltage validator
    with pytest.raises(ValueError, match="strictly less than nominal output voltage"):
        Specification(
            vout_v=5.0,
            vout_ripple_max_mv=6000.0,  # 6V ripple on 5V output
        )

    # Create Requirement linked to Specification field
    req = Requirement(
        id="req_elec_eff_01",
        discipline="electrical",
        description="Full-load power conversion efficiency >= 92%",
        source="Customer brief Section 3.2",
        acceptance_criterion="Measured or simulated efficiency at Vin=12V, Iout=1A must be >= 92.0%",
        specification_field="target_efficiency_pct",
        target_value=92.0,
        unit="%",
        verification_method="simulation",
        verification_status="NOT_EVALUATED",
    )
    assert req.verification_method == "simulation"
    assert req.verification_status == "NOT_EVALUATED"

    # Test min_value / max_value range validation
    with pytest.raises(ValueError, match="min_value cannot exceed max_value"):
        Requirement(
            id="req_range_err",
            discipline="performance",
            description="Invalid range requirement",
            source="Test",
            min_value=10.0,
            max_value=5.0,
            unit="V",
        )
