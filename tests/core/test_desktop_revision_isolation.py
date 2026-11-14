from uuid import uuid4

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.models import EngineeringDesign
from mendex_core.desktop.models import ProjectQuery
from mendex_core.desktop.service import DesktopService
from mendex_core.evidence import specification_hash
from mendex_core.integration_contracts import JobRecord, JobRequest


def test_project_jobs_cannot_leak_across_projects_or_revisions(tmp_path, monkeypatch):
    controller = MendexEngineeringController(tmp_path)
    a = controller.create_project('Fixture A', code='A', auto_enroll=True)
    b = controller.create_project('Fixture B', code='B', auto_enroll=True)
    studio = controller.service
    pa, pb = studio.get_product(a['project_id']), studio.get_product(b['project_id'])
    old_a = studio.get_revision(pa.active_revision_id)
    new_a = studio.create_revision(pa.product_id, 'R002')

    def job(project=None, revision=None, workspace=None):
        parameters = {} if project is None else {
            'project_id': str(project), 'revision_id': str(revision),
            'input_hash': specification_hash(studio.get_revision(revision).specification),
        }
        return JobRecord(request=JobRequest(
            workspace_id=workspace or project or uuid4(), tool_id='fixture', operation='inspect',
            parameters=parameters, provenance='Software fixture; no solver executed'))

    current = job(pa.product_id, old_a.revision_id)
    wrong_project = job(pb.product_id, pb.active_revision_id)
    wrong_revision = job(pa.product_id, new_a.revision_id)
    contradictory = job(pa.product_id, old_a.revision_id, workspace=pb.product_id)
    legacy = job()
    jobs = [current, wrong_project, wrong_revision, contradictory, legacy]
    monkeypatch.setattr(studio.integrations, 'list_jobs', lambda: jobs)
    desktop = DesktopService(studio)
    view = desktop.project(ProjectQuery(project_id=pa.product_id, revision_id=old_a.revision_id))
    assert [j['job_id'] for j in view['simulations']] == [str(current.request.job_id)]
    assert view['simulations'][0]['stale'] is False
    assert view['simulations'][0]['evidence_available'] is False
    assert view['unattributed_simulation_count'] == 2
    global_jobs = desktop.simulations()
    assert len(global_jobs) == 5
    assert global_jobs[-1]['revision_id'] is None
    assert global_jobs[-2]['project_id'] is None
    assert all(j['engineering_status'] == 'NOT_EVALUATED' for j in global_jobs)
    assert all(j['tool_id'] == j['request']['tool_id'] for j in global_jobs)
    # A dashboard with real queued jobs must consume the same normalized contract.
    assert desktop.overview()['metrics']['completed_simulations'] == 0


def test_desktop_designs_require_explicit_project_and_revision_link(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    a = controller.create_project('Fixture A', code='A', auto_enroll=True)
    b = controller.create_project('Fixture B', code='B', auto_enroll=True)
    studio = controller.service
    pa, pb = studio.get_product(a['project_id']), studio.get_product(b['project_id'])
    def design(product, revision, title):
        d = EngineeringDesign(workspace_id=str(product), title=title, category='pcb', product_id=str(product))
        d.core_revision_id = str(revision) if revision else None
        studio.design._persist(d)
        return d
    linked = design(pa.product_id, pa.active_revision_id, 'Linked design')
    design(pa.product_id, None, 'Legacy unassigned design')
    design(pb.product_id, pb.active_revision_id, 'Other project design')
    view = DesktopService(studio).project(ProjectQuery(project_id=pa.product_id))
    assert [d['id'] for d in view['designs']] == [linked.id]
