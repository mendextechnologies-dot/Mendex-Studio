"""Validated operation registry shared by CLI, MCP and future presentation clients."""
from ..engineering_lifecycle.models import VersionedRequest
from . import models

OPERATIONS = {
    "get_project_metadata": (models.ProjectQuery, "Read project metadata including the optimistic-concurrency updated_at token."),
    "update_project_metadata": (models.ProjectUpdate, "Update project metadata using the existing service with idempotency and concurrency guards."),
    "record_requirements": (models.RequirementsWrite, "Append structured sourced requirements for an active lifecycle attempt; does not approve requirements."),
    "list_requirements": (models.RecordList, "Read revision-associated requirements history."),
    "get_requirement_coverage": (models.RevisionQuery, "Find missing declared inputs/criteria; no standards or engineering approval inferred."),
    "list_supported_calculations": (VersionedRequest, "Discover existing deterministic calculators, required inputs/units and implementation caveats."),
    "record_calculation_run": (models.CalculationWrite, "Run an existing calculator and persist exact inputs/results/assumptions/source digest without duplicating formulas."),
    "list_calculation_runs": (models.RecordList, "Read persisted calculation history, including warnings and specification staleness."),
    "get_engineering_record": (models.RecordQuery, "Read a hash-checked engineering record and current effective integrity/staleness."),
    "register_engineering_artifact": (models.ArtifactWrite, "Register a confined revision file, preserving a unique immutable copy and original hash."),
    "list_registered_artifacts": (models.RecordList, "Read registered artifacts with missing/changed original and snapshot checks."),
    "record_validation_evidence": (models.ValidationWrite, "Delegate explicit numerical evidence recording to the existing validation service. Reviewer identity remains unverified."),
    "get_validation_results": (models.RevisionQuery, "Read effective validation status from shared core integrity checks."),
    "get_simulation_status": (models.JobQuery, "Read persisted execution state and this session's actual cancellation capability."),
    "get_simulation_logs": (models.JobQuery, "Read available bounded persisted job logs; absence is not success."),
    "get_simulation_results": (models.JobQuery, "Read persisted job results and evidence integrity, separately from engineering validation."),
    "get_simulation_artifact": (models.JobArtifact, "Preview manifest-checked available text output; no hidden waveform transformation."),
    "cancel_simulation_job": (models.JobCancel, "Request cooperative cancellation only for jobs owned by this session; foreign jobs are not relabelled cancelled."),
    "generate_revision_report": (models.ReportGenerate, "Use the existing report generator with stage attribution, file hashes and idempotency."),
    "get_report_metadata": (models.ReportQuery, "Read report availability/staleness and known integrity; legacy authenticity may be unverified."),
    "list_revision_reports": (models.RevisionQuery, "List existing report metadata for a revision."),
    "export_report_package": (models.ReportExport, "Export a unique local ZIP of the existing report and frozen snapshot, retaining integrity/provenance caveats."),
}


def tool_schemas():
    return [{"name": name, "description": description, "inputSchema": model.model_json_schema()}
            for name, (model, description) in OPERATIONS.items()]


def dispatch(studio, name, arguments):
    model, _ = OPERATIONS[name]
    request = model.model_validate(arguments)
    service = studio.engineering_records
    actions = {
        "update_project_metadata": service.update_project, "record_requirements": service.save_requirements,
        "record_calculation_run": service.run_calculation, "register_engineering_artifact": service.register_artifact,
        "record_validation_evidence": service.record_validation, "cancel_simulation_job": service.cancel_job,
        "generate_revision_report": service.generate_report, "export_report_package": service.export_report,
    }
    if name in actions:
        return actions[name](request)
    if name == "get_project_metadata":
        return studio.get_product(request.project_id).model_dump(mode="json")
    if name == "list_supported_calculations":
        return service.calculation_capabilities()
    lists = {"list_requirements": "requirements", "list_calculation_runs": "calculation", "list_registered_artifacts": "artifact"}
    if name in lists:
        return service.list_records(lists[name], request)
    if name == "get_engineering_record":
        return service.get_record(request.record_id)
    if name == "get_requirement_coverage":
        return service.missing_requirements(request.revision_id)
    if name == "get_validation_results":
        return service.validation_results(request.revision_id)
    if name == "list_revision_reports":
        return service.list_reports(request.revision_id)
    if name == "get_report_metadata":
        return service.report_metadata(request.report_id)
    if name == "get_simulation_artifact":
        return service.job_artifact(request.job_id, request.relative_path)
    return {"get_simulation_status": service.job_detail, "get_simulation_logs": service.job_logs,
            "get_simulation_results": service.job_results}[name](request.job_id)
