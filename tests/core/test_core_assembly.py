"""Disposable core-only project fixtures; no engineering qualification implied."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mendex_core.core_assembly import AssemblyDesign, lifecycle_definition
from mendex_core.desktop.service import DesktopService
from mendex_core.evidence import specification_hash
from mendex_core.models import Specification
from mendex_core.service import StudioError, StudioService


@pytest.fixture
def setup(tmp_path):
    s=StudioService(tmp_path)
    p=s.create_product('CORE-FIXTURE','Software fixture','transformer','Fixture engineer')
    old=s.get_revision(p.active_revision_id)
    source=s.workspace_path(old)/'mechanical/source.STEP'
    source.write_bytes(b'Software fixture only; not CAD evidence')
    return s,p,old


def convert(setup):
    s,p,old=setup
    request=dict(revision_id=str(old.revision_id),revision_label='CORE001',expected_input_hash=specification_hash(old.specification))
    result=s.core_assembly.create_revision(request)
    return s,s.get_revision(result['revision']['revision_id'])


def write_request(s,r,**changes):
    return dict(revision_id=str(r.revision_id),stage_id='requirements',expected_input_hash=specification_hash(r.specification),
        source='Software fixture',reason='Test append-only sourced design',idempotency_key=str(uuid4()),
        design=dict(scope='Core and support fixture',parts=[dict(reference='P1',description='Fixture part',quantity=3,
            source='Test source',cad_relative_path='mechanical/source.STEP')],
            issues=[dict(id='FIT1',title='Unresolved fit',description='Test decision',source='Test source')]),**changes)


def test_default_hash_is_compatible_and_core_profile_changes_context():
    spec=Specification(source='Historical fixture')
    old_payload=spec.model_dump(mode='json',exclude={'workflow_profile'})
    old_hash=hashlib.sha256(json.dumps(old_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert specification_hash(spec)==old_hash
    spec.workflow_profile='core_assembly'
    assert specification_hash(spec)!=old_hash


def test_profile_revision_preserves_previous_files_and_lifecycle(setup):
    s,p,old=setup
    s.engineering_lifecycle.enroll(dict(revision_id=str(old.revision_id),source='Fixture',reason='Original enrollment',idempotency_key='old-enroll'))
    old_lifecycle=s.engineering_lifecycle.get(old.revision_id)
    content=(s.workspace_path(old)/'mechanical/source.STEP').read_bytes()
    s,r=convert(setup)
    assert s.get_revision(old.revision_id).lifecycle_status=='archived'
    assert s.get_revision(old.revision_id).specification.workflow_profile=='electronics'
    assert s.get_product(p.product_id).active_revision_id==r.revision_id
    assert (s.workspace_path(old)/'mechanical/source.STEP').read_bytes()==content
    assert (s.workspace_path(r)/'mechanical/source.STEP').read_bytes()==content
    previous=s.engineering_lifecycle.get(old.revision_id)
    assert previous['assignment_id']==old_lifecycle['assignment_id']
    assert previous['definition_id']=='engineering'
    current=s.engineering_lifecycle.get(r.revision_id)
    assert current['definition_id']=='core_assembly'
    assert len(current['stages'])==7
    assert current['stages'][1]['status']=='IN_PROGRESS'
    assert current['engineering_status']=='NOT_EVALUATED'
    assert all('pcb' not in x.id for x in lifecycle_definition().stages)
    assert s.core_assembly.overview(r.revision_id)['design'] is None


def test_copy_failure_rolls_back_revision_and_keeps_original_draft(setup,monkeypatch):
    s,p,old=setup
    import mendex_core.service as service
    def fail(*args,**kwargs):raise OSError('fixture copy failure')
    monkeypatch.setattr(service.shutil,'copy2',fail)
    with pytest.raises(OSError,match='copy failure'):convert(setup)
    assert s.get_product(p.product_id).active_revision_id==old.revision_id
    assert s.get_revision(old.revision_id).lifecycle_status=='draft'
    assert len(s.list_revisions(p.product_id))==1


def test_stale_workflow_request_is_rejected(setup):
    s,p,old=setup
    request=dict(revision_id=str(old.revision_id),revision_label='CORE001',expected_input_hash=specification_hash(old.specification))
    s.update_specification(old.revision_id,Specification(source='Changed'))
    with pytest.raises(StudioError,match='Specification changed'):s.core_assembly.create_revision(request)
    assert len(s.list_revisions(p.product_id))==1


def test_design_is_append_only_with_retries_and_concurrency_guard(setup):
    s,r=convert(setup)
    req=write_request(s,r)
    first=s.core_assembly.save_design(req)
    assert s.core_assembly.save_design(req)==first
    old_file=(s.workspace_path(r)/first['relative_path']).read_bytes()
    current=s.core_assembly.overview(r.revision_id)
    assert current['design_integrity'] and current['design']['parts'][0]['quantity']==3
    changed=write_request(s,r,expected_design_sha256=current['design_sha256'])
    changed['design']['issues'][0]['disposition']='Supplied fixture clarification, not physical proof'
    second=s.core_assembly.save_design(changed)
    assert second['relative_path']!=first['relative_path']
    assert (s.workspace_path(r)/first['relative_path']).read_bytes()==old_file
    assert (s.root/first['snapshot_path']).read_bytes()==old_file
    with pytest.raises(StudioError,match='design changed'):s.core_assembly.save_design(write_request(s,r))
    assert s.core_assembly.overview(r.revision_id)['engineering_status']=='NOT_EVALUATED'


def test_parallel_design_writes_cannot_overwrite_each_other(setup):
    s,r=convert(setup)
    def save(_):
        try:return s.core_assembly.save_design(write_request(s,r))
        except StudioError as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,range(2)))
    assert sum(isinstance(x,dict) for x in results)==1
    assert 'CONFLICT' in results


@pytest.mark.parametrize('path',['../escape.STEP','mechanical/missing.STEP','requirements/requirements.json'])
def test_design_rejects_missing_or_escaping_cad_paths(setup,path):
    s,r=convert(setup)
    req=write_request(s,r)
    req['design']['parts'][0]['cad_relative_path']=path
    with pytest.raises((StudioError,ValueError)):s.core_assembly.save_design(req)
    assert s.core_assembly.overview(r.revision_id)['design'] is None


def test_modified_design_does_not_remain_current_intact_evidence(setup):
    s,r=convert(setup)
    record=s.core_assembly.save_design(write_request(s,r))
    (s.workspace_path(r)/record['relative_path']).write_text('{}')
    result=s.core_assembly.overview(r.revision_id)
    assert result['design'] is None and not result['design_integrity']
    assert result['engineering_status']=='NOT_EVALUATED'


def test_linked_cad_change_invalidates_design_integrity(setup):
    s,r=convert(setup)
    s.core_assembly.save_design(write_request(s,r))
    (s.workspace_path(r)/'mechanical/source.STEP').write_bytes(b'Changed software fixture')
    result=s.core_assembly.overview(r.revision_id)
    assert not result['cad_integrity'] and not result['design_integrity']
    assert result['engineering_status']=='NOT_EVALUATED'


def test_dimension_limits_are_sourced_finite_and_ordered():
    from mendex_core.core_assembly import AssemblyDimension
    dimension=AssemblyDimension(name='Outside diameter',nominal_m=.064,minimum_m=.0639,maximum_m=.064,source='Fixture drawing')
    assert dimension.nominal_m==.064
    with pytest.raises(ValidationError):AssemblyDimension(name='Invalid',nominal_m=.064,minimum_m=.065,source='Fixture')
    with pytest.raises(ValidationError):AssemblyDimension(name='Invalid',nominal_m=float('nan'),source='Fixture')


def test_next_core_revision_carries_design_but_not_review_acceptance(setup):
    s,r=convert(setup)
    s.core_assembly.save_design(write_request(s,r))
    result=s.core_assembly.create_revision(dict(revision_id=str(r.revision_id),revision_label='CORE002',expected_input_hash=specification_hash(r.specification)))
    current=s.core_assembly.overview(result['revision']['revision_id'])
    assert current['design_integrity'] and len(current['design']['parts'])==1
    assert current['engineering_status']=='NOT_EVALUATED'
    stages=s.engineering_lifecycle.get(result['revision']['revision_id'])['stages']
    assert stages[1]['status']=='IN_PROGRESS' and stages[2]['status']=='NOT_STARTED'


def test_core_review_omits_electronics_requirements_and_keeps_fit_blockers(setup):
    s,r=convert(setup)
    s.core_assembly.save_design(write_request(s,r))
    package=s.reviews.prepare_package(r.revision_id,'requirements')
    assert not any('voltage' in x.lower() or 'isolation' in x.lower() for x in package['safety_blockers'])
    package=s.reviews.prepare_package(r.revision_id,'fit_review')
    assert any('FIT1' in x for x in package['safety_blockers'])
    lifecycle=s.engineering_lifecycle.get(r.revision_id)
    assert lifecycle['stages'][1]['blockers']  # No review or automatic PASS supplied.


def test_electronics_and_archived_revisions_cannot_write_core_designs(setup):
    s,p,old=setup
    with pytest.raises(StudioError):s.core_assembly.overview(old.revision_id)
    s,r=convert(setup)
    s.create_revision(p.product_id,'NEXT')
    with pytest.raises(StudioError,match='draft'):s.core_assembly.save_design(write_request(s,r))


def test_desktop_and_cli_use_same_core_operations(setup,tmp_path,capsys):
    s,p,old=setup
    d=DesktopService(s)
    result=d.dispatch('create_core_assembly_revision',dict(revision_id=str(old.revision_id),revision_label='CORE001',expected_input_hash=specification_hash(old.specification)))
    r=s.get_revision(result['revision']['revision_id'])
    d.dispatch('save_core_assembly',write_request(s,r))
    desktop=d.dispatch('core_assembly',{'revision_id':str(r.revision_id)})
    from mendex_core.cli import main
    request=tmp_path/'request.json'
    request.write_text(json.dumps({'revision_id':str(r.revision_id)}))
    assert main(['--root',str(s.root),'core-assembly','show',str(request)])==0
    cli=json.loads(capsys.readouterr().out)
    assert cli==desktop


def test_strict_design_rejects_fabricated_qualification_and_duplicate_parts():
    with pytest.raises(ValidationError):AssemblyDesign(scope='Fixture',qualification='PASS')
    part=dict(reference='P1',description='Fixture',quantity=1,source='Fixture')
    with pytest.raises(ValidationError):AssemblyDesign(scope='Fixture',parts=[part,part])
