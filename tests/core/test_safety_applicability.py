import pytest
from mendex_core.intelligence.calculations import DeterministicCalculationService


@pytest.mark.parametrize('degree', [1, 2, 3, 4])
@pytest.mark.parametrize('group', ['I', 'II', 'IIIa', 'IIIb'])
def test_no_context_combination_can_use_unqualified_rule_tables(degree, group):
    result = DeterministicCalculationService().calculate_iec_creepage_clearance(
        1000, 1500, degree, group, 'reinforced', 500,
        altitude_m=0, rated_impulse_voltage_v=4000, working_frequency_hz=100000,
        standard_edition='Software test context, not a qualified standard')
    assert result.evaluation_status == 'NOT_EVALUATED'
    assert result.verified is False
    assert result.outputs == {}
    assert result.context['pollution_degree'] == degree
    assert 'qualified_ruleset' in result.missing_inputs
    assert 'required_clearance_mm' not in result.outputs
    assert 'compliant' not in result.outputs


def test_missing_inputs_are_explicit_without_assumed_environment_or_geometry():
    result = DeterministicCalculationService().calculate_iec_creepage_clearance()
    assert result.inputs == {}
    assert all(result.context[key] is None for key in ('working_voltage_rms', 'pollution_degree', 'material_group', 'slot_width_mm'))
    assert {'altitude_m', 'rated_impulse_voltage_v', 'working_frequency_hz', 'standard_edition'} <= set(result.missing_inputs)


@pytest.mark.parametrize('kwargs', [
    {'pollution_degree': True}, {'pollution_degree': 2.0}, {'pollution_degree': 5},
    {'material_group': 'unknown'}, {'insulation_type': 'unknown'},
    {'working_voltage_rms': float('nan')}, {'peak_voltage_v': float('inf')},
    {'slot_width_mm': -1}, {'altitude_m': -1}, {'standard_edition': ' '},
])
def test_invalid_safety_context_rejected(kwargs):
    with pytest.raises(ValueError):
        DeterministicCalculationService().calculate_iec_creepage_clearance(**kwargs)


def test_derating_has_no_implicit_standard_limit_or_qualification():
    service = DeterministicCalculationService()
    result = service.calculate_component_derating('mosfet', 600, 1200)
    assert result.outputs['stress_ratio'] == .5
    assert 'max_allowed_ratio' not in result.outputs
    assert 'compliant' not in result.outputs
    assert result.comparison_status == 'NOT_EVALUATED' and not result.verified
    for operating, comparison in [(6, 'WITHIN_SUPPLIED_LIMIT'), (8, 'EXCEEDS_SUPPLIED_LIMIT')]:
        result = service.calculate_component_derating('resistor', operating, 10,
                   max_allowed_ratio=.6, limit_source='Fixture arithmetic criterion')
        assert result.comparison_status == comparison
        assert result.evaluation_status == 'NOT_EVALUATED' and not result.verified
    assert service.calculate_component_derating('resistor', 5, 10, max_allowed_ratio=.6).comparison_status == 'NOT_EVALUATED'


@pytest.mark.parametrize('operating,rated', [(float('nan'), 10), (1, 0), (-1, 10), (True, 2), (1e308, 1e-308)])
def test_invalid_stress_arithmetic_rejected(operating, rated):
    with pytest.raises(ValueError):
        DeterministicCalculationService().calculate_component_derating('part', operating, rated)
