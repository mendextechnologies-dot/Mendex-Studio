"""One strict operation registry shared by MCP and CLI; no transport business rules."""
from ..models import Model
from .models import DefinitionQuery, Enrollment, HistoryQuery, LifecycleQuery, RegisterDefinition, StageCommand

OPERATIONS = {
    "list_lifecycle_definitions": (Model, "List packaged and registered lifecycle definitions."),
    "get_lifecycle_definition": (DefinitionQuery, "Retrieve one versioned data-only lifecycle definition."),
    "register_lifecycle_definition": (RegisterDefinition, "Register an immutable validated definition; no executable configuration."),
    "enroll_lifecycle": (Enrollment, "Explicitly enroll a draft revision; no historical PASS states are inherited."),
    "get_project_lifecycle": (LifecycleQuery, "Read lifecycle stages and effective evidence/dependency/review blockers."),
    "get_lifecycle_history": (HistoryQuery, "Read append-only lifecycle history with sequence pagination."),
    "apply_lifecycle_stage": (StageCommand, "Start/reopen/block/fail/request review/attach validation evidence/complete a stage. Completion is guarded; no approval operation."),
}


def tool_schemas():
    return [{"name": name, "description": description, "inputSchema": model.model_json_schema()}
            for name, (model, description) in OPERATIONS.items()]


def dispatch(service, name, arguments):
    model, _ = OPERATIONS[name]
    request = model.model_validate(arguments)
    lifecycle = service.engineering_lifecycle
    if name == "list_lifecycle_definitions":
        return lifecycle.list_definitions()
    if name == "get_lifecycle_definition":
        return lifecycle.definition(request.definition_id, request.version)
    if name == "register_lifecycle_definition":
        return lifecycle.register_definition(request.definition, request.source)
    if name == "enroll_lifecycle":
        return lifecycle.enroll(request)
    if name == "get_project_lifecycle":
        return lifecycle.get(request.revision_id)
    if name == "get_lifecycle_history":
        return lifecycle.history(**request.model_dump(exclude={"schema_version"}))
    return lifecycle.apply(request)
