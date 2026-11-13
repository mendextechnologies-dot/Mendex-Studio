"""One strict review operation registry shared by MCP and CLI."""
from ..models import Model
from . import models

OPERATIONS = {
    "get_review_package": (models.ReviewPackageQuery, "Inspect requirements package, conflicts, and verification coverage."),
    "request_stage_review": (models.ReviewRequestCommand, "Request formal human engineering review for a stage."),
    "record_human_review": (models.ReviewDecisionCommand, "Record an authorized human review decision with credential proof."),
    "list_authorized_reviewers": (Model, "List qualified human reviewers and authorized roles."),
    "register_authorized_reviewer": (models.ReviewerRegistration, "Provision a qualified human reviewer with authorization credentials."),
    "get_stage_review_history": (models.ReviewPackageQuery, "Read append-only review history and signatures for a stage."),
}


def tool_schemas():
    return [
        {"name": name, "description": description, "inputSchema": model.model_json_schema()}
        for name, (model, description) in OPERATIONS.items()
    ]


def dispatch(service, name, arguments):
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
