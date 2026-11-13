"""Reference integrity and the actual desktop wire format; no live project data."""
import pytest
from pydantic import ValidationError

from mendex_core.components.models import ComponentRecord, MaterialRecord, MagneticCoreRecord
from mendex_core.components.service import ComponentLibraryService
from mendex_core.desktop.service import DesktopService
from mendex_core.service import StudioService


def test_desktop_catalog_uses_canonical_fields_and_distinct_material_properties(tmp_path):
    payload = DesktopService(StudioService(tmp_path)).components()
    materials = {row['name']: row for row in payload['materials']}
    assert materials['N87']['initial_permeability_ui'] == 2200
    assert materials['N97']['initial_permeability_ui'] == 2300
    assert materials['N87']['saturation_flux_t'] == 0.49
    assert '25 degrees C' in materials['N87']['conditions']
    assert materials['N87']['curie_temp_qualifier'] == '>'
    assert materials['KoolMu']['initial_permeability_ui'] is None
    assert all(row['ae_mm2'] is None for row in payload['cores'])
    assert all(row['verification_status'] == 'NOT_EVALUATED'
               for group in ('components', 'materials', 'cores') for row in payload[group])


def test_catalog_expansion_sources_and_stable_identity():
    first, second = ComponentLibraryService(), ComponentLibraryService()
    assert len(first.list_components()) == 20
    assert [p.id for p in first.list_components()] == [p.id for p in second.list_components()]
    assert len({p.id for p in first.list_components()}) == len(first.list_components())
    categories = {c['id'] for c in first.categories}
    assert len(categories) == 30
    assert all(p.category in categories and p.datasheet_url.startswith('https://')
               for p in first.list_components())
    assert first.get_component('UCC21520').record_kind == 'FAMILY'
    assert first.get_component('C3M0065090D').lifecycle_status == 'NRND'
    diode = first.get_component('MBR20100CT')
    assert diode.current_rating_a == 10
    assert 'PER LEG' in diode.conditions
    assert first.list_components('MOSFET') == first.list_components('mosfet')


def test_unknown_ratings_models_and_loss_fits_are_not_invented():
    part = ComponentRecord(mpn='uncharacterized', manufacturer='unknown', category='capacitor')
    assert part.voltage_rating_v is None and part.package is None
    assert part.kicad_footprint is None and part.spice_model_name is None
    assert not MaterialRecord(name='unknown').loss_model_ready
    assert not MagneticCoreRecord(name='unknown').geometry_ready
    library = ComponentLibraryService()
    assert all(not m.loss_model_ready for m in library.list_materials())
    assert all(not c.geometry_ready for c in library.list_cores())


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 0])
def test_bad_physical_rating_rejected(value):
    with pytest.raises(ValidationError):
        ComponentRecord(mpn='bad', manufacturer='unknown', category='mosfet', voltage_rating_v=value)
