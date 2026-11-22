"""Software-only preview evidence fixtures, never native/physical qualification."""
import json
from uuid import uuid4

import pytest

from mendex_core.evidence import digest,specification_hash
from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService


@pytest.fixture
def context(tmp_path):
    s=StudioService(tmp_path)
    p=s.create_product('PREVIEW-FIXTURE','Software fixture','transformer','Fixture')
    previous=s.get_revision(p.active_revision_id)
    result=s.core_assembly.create_revision(dict(revision_id=str(previous.revision_id),revision_label='CORE001',expected_input_hash=specification_hash(previous.specification)))
    r=s.get_revision(result['revision']['revision_id']);ws=s.workspace_path(r)
    source=ws/'mechanical/source.STEP';source.write_bytes(b'Software geometry fixture,not CAD')
    request=dict(revision_id=str(r.revision_id),stage_id='requirements',expected_input_hash=specification_hash(r.specification),source='Software fixture',reason='Preview integrity test',idempotency_key='fixture-design',
        design=dict(scope='Software-only fixture',parts=[dict(reference='P1',description='Test part',quantity=1,source='Fixture',cad_relative_path='mechanical/source.STEP')]))
    s.core_assembly.save_design(request)
    folder=ws/'mechanical/core-assembly/test';folder.mkdir(parents=True)
    for name in ('assembly.step','assembly.FCStd'):(folder/name).write_bytes(b'Software-only native artifact fixture')
    data=dict(schema_version='1.0',units='m',design_sha256=s.core_assembly.overview(r.revision_id)['design_sha256'],source_hashes={'mechanical/source.STEP':digest(source.read_bytes())},
        native_files={key:(folder/name).relative_to(ws).as_posix() for key,name in [('step','assembly.step'),('freecad','assembly.FCStd')]},
        native_hashes={(folder/name).relative_to(ws).as_posix():digest((folder/name).read_bytes()) for name in ('assembly.step','assembly.FCStd')},
        prototypes={'test':dict(positions_m=[[0,0,0],[.1,0,0],[0,.1,0]],triangles=[[0,1,2]])},
        instances=[dict(name='Software fixture',prototype='test',color='#dddddd',transform=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])],
        bounds_m=[[0,0,0],[.1,.1,.1]],part_counts={'test':1},assumptions=['Software fixture only'],omissions=[])
    return s,r,ws,folder,data,request


def register(context,data=None):
    s,r,ws,folder,original,_=context
    path=folder/'assembly-preview.json'
    path.write_text(json.dumps(data or original))
    return s.engineering_records.register_artifact(dict(revision_id=str(r.revision_id),stage_id='requirements',expected_input_hash=specification_hash(r.specification),source='Software fixture',
        reason='Test read-only preview integrity',idempotency_key=str(uuid4()),relative_path=path.relative_to(ws).as_posix(),expected_sha256=digest(path.read_bytes()),classification='documentation'))


def test_unavailable_preview_never_substitutes_electronics_geometry(context):
    s,r,*_=context
    result=s.core_assembly.assembly_preview(r.revision_id)
    assert result['available'] is False and 'prototypes' not in result
    assert result['engineering_status']=='NOT_EVALUATED'


def test_intact_preview_is_shared_with_desktop_and_not_approval(context):
    s,r,*_=context;register(context)
    result=s.core_assembly.assembly_preview(r.revision_id)
    assert result['available'] and result['source_integrity']
    assert len(result['instances'])==1 and result['engineering_status']=='NOT_EVALUATED'
    assert DesktopService(s).dispatch('core_assembly_preview',{'revision_id':str(r.revision_id)})==result


@pytest.mark.parametrize('relative',['mechanical/source.STEP','mechanical/core-assembly/test/assembly.step','mechanical/core-assembly/test/assembly.FCStd','mechanical/core-assembly/test/assembly-preview.json'])
def test_changed_source_output_or_preview_is_not_displayed_as_current(context,relative):
    s,r,ws,*_=context;register(context)
    (ws/relative).write_bytes(b'Changed fixture')
    result=s.core_assembly.assembly_preview(r.revision_id)
    assert not result['available'] and 'prototypes' not in result


def test_preview_for_older_design_is_unavailable(context):
    s,r,ws,folder,data,request=context;register(context)
    current=s.core_assembly.overview(r.revision_id)
    request.update(idempotency_key='next',expected_design_sha256=current['design_sha256'])
    request['design']['parts'][0]['quantity']=2
    s.core_assembly.save_design(request)
    result=s.core_assembly.assembly_preview(r.revision_id)
    assert not result['available'] and 'earlier design' in result['reason']


def test_document_clarification_does_not_invalidate_unchanged_geometry(context):
    s,r,ws,folder,data,request=context;register(context)
    current=s.core_assembly.overview(r.revision_id)
    request.update(idempotency_key='notes-only',expected_design_sha256=current['design_sha256'])
    request['design']['notes']='A supplied documentation clarification; no geometry change.'
    s.core_assembly.save_design(request)
    assert s.core_assembly.assembly_preview(r.revision_id)['available']


@pytest.mark.parametrize('change',['indices','units','matrix','prototype','path','bounds','counts'])
def test_invalid_mesh_or_unconfined_file_is_unavailable(context,change):
    s,r,ws,folder,data,_=context
    if change=='indices':data['prototypes']['test']['triangles']=[[0,1,999]]
    if change=='units':data['units']='mm'
    if change=='matrix':data['instances'][0]['transform'][0][0]=float('nan')
    if change=='prototype':data['instances'][0]['prototype']='missing'
    if change=='path':data['native_hashes']['../outside.step']='0'*64
    if change=='bounds':data['bounds_m'][0][0]=float('nan')
    if change=='counts':data['part_counts']['test']=99
    register(context,data)
    result=s.core_assembly.assembly_preview(r.revision_id)
    assert not result['available'] and 'prototypes' not in result
