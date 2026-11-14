"""Strict review operation registry with human-only gate."""
from ..models import Model
from . import models
from ..service import StudioError

READ_OPERATIONS = {
    "get_review_package": (models.ReviewPackageQuery, "Inspect requirements package, conflicts, and verification coverage."),
    "request_stage_review": (models.ReviewRequestCommand, "Request formal human engineering review for a stage."),
    "list_authorized_reviewers": (Model, "List qualified human reviewers and authorized roles."),
    "get_stage_review_history": (models.ReviewPackageQuery, "Read append-only review history and signatures for a stage."),
}

HUMAN_ONLY_OPERATIONS = {
    "record_human_review": (models.ReviewDecisionCommand, "Record an authorized human review decision with credential proof."),
    "register_authorized_reviewer": (models.ReviewerRegistration, "Provision a qualified human reviewer with authorization credentials."),
}

OPERATIONS = {**READ_OPERATIONS, **HUMAN_ONLY_OPERATIONS}


def mcp_tool_schemas():
    """Return tool schemas exposed to AI agents and MCP callers (strictly read-only and request review only)."""
    return [
        {"name": name, "description": description, "inputSchema": model.model_json_schema()}
        for name, (model, description) in READ_OPERATIONS.items()
    ]


def tool_schemas():
    """Default schemas exposed for automated discovery; excludes human review decisions."""
    return mcp_tool_schemas()


def dispatch(service, name, arguments, caller_is_mcp=False):
    if name not in OPERATIONS:
        raise NotImplementedError(name)
    if caller_is_mcp and name in HUMAN_ONLY_OPERATIONS:
        raise StudioError(
            "FORBIDDEN",
            f"AI agents and MCP clients cannot execute '{name}'. Reviewer provisioning and sign-off decisions require interactive human authorization."
        )
    model, _ = OPERATIONS[name]
    request = model.model_validate(arguments)
    reviews = service.reviews
    if name == "get_review_package":
        return reviews.prepare_package(request.revision_id, request.stage_id)
    if name == "request_stage_review":
        return reviews.request_review(request)
    if name == "record_human_review":
        return reviews.record_decision(request)
    if name == "list_authorized_reviewers":
        return reviews.list_reviewers()
    if name == "register_authorized_reviewer":
        return reviews.register_reviewer(request)
    if name == "get_stage_review_history":
        return reviews.list_reviews(request.revision_id, request.stage_id)
    raise NotImplementedError(name)
