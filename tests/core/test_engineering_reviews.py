"""Comprehensive unit and integration test suite for human engineering reviews in Mendex Core.

All tests use disposable tmp_path fixtures and never mutate or touch the live database.
"""
import json
import sqlite3
from uuid import uuid4
import pytest
from pydantic import ValidationError

from mendex_core.service import StudioError, StudioService
from mendex_core.engineering_reviews.models import ReviewDecision, ReviewerRegistration, AuthorizedDeferral
from mendex_core.evidence import specification_hash
from mendex_core.models import Specification


def manual_package(service, rid, name="Independent local reviewer"):
    pkg = service.reviews.prepare_package(rid)
    return {"revision_id": str(rid), "stage_id": "requirements", "attempt": pkg["stage"]["attempt"],
            "reviewer_name": name, "decision": "APPROVED", "comments": "Reviewed this exact disposable requirements snapshot.",
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "expected_document_hashes": pkg["document_hashes"], "expected_evidence_hashes": pkg["evidence_hashes"],
            "idempotency_key": str(uuid4())}


def simple_requirements(service, rid):
    return add_requirements(service, rid, [{"id": "req_local", "discipline": "electrical", "description": "Disposable requirement",
         "source": "Synthetic software fixture only", "acceptance_criterion": "Explicit disposable software criterion; no hardware evidence"}])


def test_no_production_profiles_seeded(tmp_path):
    service = StudioService(tmp_path)
    assert service.reviews.list_reviewers() == []


def test_manual_review_desktop_without_profile_and_explicit_attribution(review_context):
    from mendex_core.desktop.service import DesktopService
    service, rid, _ = review_context
    assert service.reviews.list_reviewers() == []
    simple_requirements(service, rid)
    request = manual_package(service, rid)
    result = DesktopService(service).dispatch("submit_review", request)
    assert result["reviewer_name"] == request["reviewer_name"]
    assert result["review_mode"] == "MANUALLY_DECLARED"
    assert result["identity_authenticated"] is False
    assert result["signature_kind"] == "CONTENT_DIGEST_NOT_IDENTITY_PROOF"
    assert service.reviews.record_manual_decision(request) == result
    assert all(r["id"] != result["reviewer_id"] for r in service.reviews.list_reviewers())
    # The review does not complete a stage or authorize hardware by itself.
    view = service.engineering_lifecycle.get(rid)
    assert view["stages"][1]["status"] == "IN_PROGRESS"
    assert view["engineering_status"] == "NOT_EVALUATED"
    service.engineering_lifecycle.apply({"revision_id": str(rid), "stage_id": "requirements", "action": "complete",
        "source": "Test operator", "reason": "Complete the software process criterion only", "idempotency_key": "manual-complete"})
    assert service.engineering_lifecycle.get(rid)["stages"][1]["effective_status"] == "COMPLETED"


@pytest.mark.parametrize("decision", ["REJECTED", "CHANGES_REQUESTED"])
def test_manual_negative_decisions_preserve_history(review_context, decision):
    service, rid, _ = review_context
    simple_requirements(service, rid)
    request = {**manual_package(service, rid), "decision": decision}
    recorded = service.reviews.record_manual_decision(request)
    assert service.reviews.effective_review(rid)["effective_status"] == decision
    assert service.reviews.list_reviews(rid)[0]["review_id"] == recorded["review_id"]


def test_manual_safety_blocker_not_removed_by_no_password(review_context):
    service, rid, _ = review_context
    simple_requirements(service, rid)
    revision = service.get_revision(rid)
    spec = revision.specification.model_dump()
    spec["isolation_requirement"] = ""
    service.update_specification(rid, Specification.model_validate(spec))
    with pytest.raises(StudioError, match="safety"):
        service.reviews.record_manual_decision(manual_package(service, rid))
    assert service.reviews.list_reviews(rid) == []


def test_manual_deferral_requires_exact_safety_item_and_explicit_fields(review_context):
    service, rid, _ = review_context
    simple_requirements(service, rid)
    spec = service.get_revision(rid).specification.model_dump()
    spec["isolation_requirement"] = ""
    service.update_specification(rid, Specification.model_validate(spec))
    request = manual_package(service, rid)
    item = service.reviews.prepare_package(rid)["safety_items"][0]
    deferral = {"requirement_id": "High-voltage", "rationale": "Defer final selection to feasibility review only",
                "owner": "Named fixture HV engineer", "scope": "Preliminary analysis only, no physical work",
                "downstream_gate": "Before completing Stage 3; before detailed design"}
    with pytest.raises(StudioError, match="safety"):
        service.reviews.record_manual_decision({**request, "deferrals": [deferral]})
    result = service.reviews.record_manual_decision({**request, "deferrals": [{**deferral, "requirement_id": item["id"]}]})
    assert result["deferrals"][0]["downstream_gate"] == deferral["downstream_gate"]
    assert result["identity_authenticated"] is False


def test_manual_review_rejects_changed_documents_and_stale_attempt(review_context):
    service, rid, _ = review_context
    simple_requirements(service, rid)
    document = service.workspace_path(service.get_revision(rid)) / "requirements" / "review.txt"
    document.write_text("First draft")
    request = manual_package(service, rid)
    document.write_text("Changed after package opened")
    with pytest.raises(StudioError, match="documents or evidence changed"):
        service.reviews.record_manual_decision(request)
    request = manual_package(service, rid)
    request["attempt"] += 1
    with pytest.raises(StudioError, match="current active stage attempt"):
        service.reviews.record_manual_decision(request)


def test_manual_review_requires_name_comments_and_cannot_use_mcp(review_context):
    from mendex_core.engineering_reviews.api import dispatch
    service, rid, _ = review_context
    simple_requirements(service, rid)
    request = manual_package(service, rid)
    with pytest.raises(ValidationError):
        service.reviews.record_manual_decision({**request, "reviewer_name": "   "})
    with pytest.raises(ValidationError):
        service.reviews.record_manual_decision({**request, "comments": "   "})
    with pytest.raises(ValidationError):
        dispatch(service, "record_human_review", request)
    assert service.reviews.list_reviews(rid) == []


def test_manual_review_detects_later_tamper_and_refuses_self_review(review_context):
    service, rid, _ = review_context
    simple_requirements(service, rid)
    with pytest.raises(StudioError, match="Self-approval"):
        service.reviews.record_manual_decision(manual_package(service, rid, "Junior Design Engineer"))
    document = service.workspace_path(service.get_revision(rid)) / "requirements" / "review.txt"
    document.write_text("Reviewed bytes")
    result = service.reviews.record_manual_decision(manual_package(service, rid))
    document.write_text("Later edit")
    assert service.reviews.effective_review(rid)["effective_status"] == "STALE"
    assert service.reviews.list_reviews(rid)[0]["signature"] == result["signature"]


@pytest.fixture
def review_context(tmp_path, request):
    service = StudioService(tmp_path)
    # Legacy credential tests explicitly provision disposable test identities.
    # Production initialization no longer seeds profiles or passwords.
    legacy_reviewers = (
        ("reviewer_lead_human", "Lead Power Systems Engineer", "test-review-passphrase-1"),
        ("reviewer_safety_lead", "Safety Reviewer", "test-review-passphrase-2"),
    ) if not request.node.name.startswith("test_manual") else ()
    for reviewer_id, name, secret in legacy_reviewers:
        service.reviews.register_reviewer({"id": reviewer_id, "name": name,
            "email": reviewer_id + "@example.test", "roles": ["requirements_reviewer", "lead_engineer"], "secret": secret})
    product = service.create_product("TEST-CONV", "High-Voltage Test Converter", "dc_dc_converter", "Junior Design Engineer")
    rev = service.get_revision(product.active_revision_id)
    service.update_specification(
        rev.revision_id,
        Specification(vin_nom_v=24.0, vout_v=1000.0, iout_a=0.1, isolation_requirement="3kV galvanic isolation"),
    )
    # Enroll in default standard 9-stage lifecycle
    service.engineering_lifecycle.enroll({
        "revision_id": str(rev.revision_id),
        "source": "test-harness",
        "reason": "Test enrollment",
        "idempotency_key": "enroll-test",
    })
    # Start and complete Stage 1
    service.engineering_lifecycle.apply({
        "schema_version": "3.1.0",
        "revision_id": str(rev.revision_id),
        "stage_id": "project_initialization",
        "action": "start",
        "source": "engineer",
        "reason": "Starting project initialization",
        "idempotency_key": "s1-start",
    })
    service.engineering_lifecycle.apply({
        "schema_version": "3.1.0",
        "revision_id": str(rev.revision_id),
        "stage_id": "project_initialization",
        "action": "complete",
        "source": "engineer",
        "reason": "Completing project initialization",
        "idempotency_key": "s1-complete",
    })
    # Start Stage 2
    service.engineering_lifecycle.apply({
        "schema_version": "3.1.0",
        "revision_id": str(rev.revision_id),
        "stage_id": "requirements",
        "action": "start",
        "source": "engineer",
        "reason": "Starting requirements stage",
        "idempotency_key": "s2-start",
    })
    return service, rev.revision_id, tmp_path


def add_requirements(service, rev_id, req_list, source="Junior Design Engineer"):
    rev = service.get_revision(rev_id)
    spec_hash = specification_hash(rev.specification)
    return service.engineering_records.save_requirements({
        "schema_version": "3.1.0",
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "expected_input_hash": spec_hash,
        "source": source,
        "reason": "Authoritative requirements baseline",
        "idempotency_key": str(uuid4()),
        "requirements": req_list,
    })


def test_list_and_register_reviewers(review_context):
    service, rev_id, _ = review_context
    reviewers = service.reviews.list_reviewers()
    assert len(reviewers) >= 2
    # Verify passwords/salts are not exposed
    for r in reviewers:
        assert "secret_hash" not in r
        assert "salt" not in r
        assert r["status"] == "ACTIVE"

    # Register new qualified reviewer
    new_rev = service.reviews.register_reviewer(
        ReviewerRegistration(
            id="rev_external_expert",
            name="External PE Consultant",
            email="pe@consulting.example",
            roles=["requirements_reviewer", "lead_engineer"],
            secret="CorrectHorseBatteryStaple!99",
        )
    )
    assert new_rev["reviewer"]["id"] == "rev_external_expert"

    # Registering duplicate ID must fail
    with pytest.raises(StudioError) as exc:
        service.reviews.register_reviewer(
            ReviewerRegistration(
                id="rev_external_expert",
                name="Duplicate Reviewer",
                email="dup@example.com",
                roles=["lead_engineer"],
                secret="Pass1234!",
            )
        )
    assert exc.value.code == "CONFLICT"

    # Registering automated agent ID must be rejected
    with pytest.raises(StudioError) as exc:
        service.reviews.register_reviewer(
            ReviewerRegistration(
                id="agent_codex_bot",
                name="Codex Autonomous Agent",
                email="agent@bot.example",
                roles=["lead_engineer"],
                secret="AgentPass123!",
            )
        )
    assert exc.value.code == "INVALID_INPUT"
    assert "Automated agent IDs cannot be registered" in str(exc.value)


def test_self_approval_rejected(review_context):
    service, rev_id, _ = review_context

    # Register reviewer with same name as product owner / submitter
    service.reviews.register_reviewer(
        ReviewerRegistration(
            id="rev_junior_eng",
            name="Junior Design Engineer",
            email="junior@company.example",
            roles=["requirements_reviewer"],
            secret="ValidPassphrase123!",
        )
    )

    # Add requirements authored by Junior Design Engineer
    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Input Voltage Range",
                "source": "Handbook Section 2.1",
                "specification_field": "vin_nom_v",
                "target_value": 24.0,
                "unit": "V",
                "acceptance_criterion": "Measured input within 20-30V range",
                "mandatory": True,
            }
        ],
        source="Junior Design Engineer",
    )

    pkg = service.reviews.prepare_package(rev_id, "requirements")

    # Author/submitter tries to approve
    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision({
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "attempt": 1,
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "reviewer_id": "rev_junior_eng",
            "reviewer_secret": "ValidPassphrase123!",
            "decision": "APPROVED",
            "comments": "Self approving my own package",
            "idempotency_key": "self-approve-attempt",
        })
    assert exc.value.code == "FORBIDDEN"
    assert "Self-approval is strictly forbidden" in str(exc.value)


def test_automated_agent_approval_blocked(review_context):
    service, rev_id, _ = review_context

    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Input Voltage Range",
                "source": "Handbook Section 2.1",
                "specification_field": "vin_nom_v",
                "target_value": 24.0,
                "unit": "V",
                "acceptance_criterion": "Acceptance criteria present",
                "mandatory": True,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")

    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision({
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "attempt": 1,
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "reviewer_id": "agent_codex",
            "reviewer_secret": "secret",
            "decision": "APPROVED",
            "comments": "Agent auto approval",
            "idempotency_key": "agent-approve-attempt",
        })
    assert exc.value.code == "FORBIDDEN"
    assert "Automated agents cannot approve" in str(exc.value)


def test_unauthorized_credentials_and_unknown_reviewer(review_context):
    service, rev_id, _ = review_context

    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Input Voltage Range",
                "source": "Handbook Section 2.1",
                "specification_field": "vin_nom_v",
                "target_value": 24.0,
                "unit": "V",
                "acceptance_criterion": "Acceptance criteria present",
                "mandatory": True,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")

    # Nonexistent reviewer
    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision({
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "attempt": 1,
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "reviewer_id": "unknown_ghost_reviewer",
            "reviewer_secret": "any",
            "decision": "APPROVED",
            "comments": "Fake approval",
            "idempotency_key": "ghost-attempt",
        })
    assert exc.value.code == "UNAUTHORIZED"

    # Known reviewer with incorrect passphrase
    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision({
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "attempt": 1,
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "reviewer_id": "reviewer_lead_human",
            "reviewer_secret": "WrongPassword123!",
            "decision": "APPROVED",
            "comments": "Wrong password attempt",
            "idempotency_key": "wrong-pw-attempt",
        })
    assert exc.value.code == "UNAUTHORIZED"


def test_safety_blocker_requires_authorized_deferral(review_context):
    service, rev_id, _ = review_context

    # Register requirement missing acceptance criteria (mandatory safety)
    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_safe_01",
                "discipline": "safety",
                "description": "Dielectric Withstand Hipot",
                "source": "Safety standard IEC 62368-1",
                "target_value": 3000.0,
                "unit": "V",
                "acceptance_criterion": "",  # Missing criteria triggers conflict/blocker
                "mandatory": True,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")
    assert len(pkg["safety_blockers"]) > 0

    # Attempt approval without deferral -> must fail
    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision({
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "attempt": 1,
            "expected_requirements_digest": pkg["requirements_package"]["digest"],
            "expected_specification_hash": pkg["revision"]["specification_hash"],
            "reviewer_id": "reviewer_lead_human",
            "reviewer_secret": "test-review-passphrase-1",
            "decision": "APPROVED",
            "comments": "Approved without safety deferral",
            "idempotency_key": "no-deferral-approve",
        })
    assert exc.value.code == "INVALID_INPUT"
    assert "Approval blocked by unresolved mandatory safety items" in str(exc.value)

    # Approve with valid authorized deferral
    res = service.reviews.record_decision({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_lead_human",
        "reviewer_secret": "test-review-passphrase-1",
        "decision": "APPROVED",
        "comments": "Approved with authorized deferral for hipot dielectric criterion",
        "deferrals": [
            {
                "requirement_id": "req_safe_01",
                "rationale": "Detailed hipot dielectric breakdown threshold will be calibrated after core bobbin potting vendor sample is received.",
                "owner": "Chief High-Voltage Safety Officer",
                "scope": "Hipot threshold specification only; galvanic isolation distance remains mandatory.",
                "downstream_gate": "Stage 6: Hardware Testing",
            }
        ],
        "idempotency_key": "deferral-approve-success",
    })
    assert res["decision"] == "APPROVED"
    assert len(res["deferrals"]) == 1
    assert res["signature"] is not None


def test_rejection_and_changes_requested_flow(review_context):
    service, rev_id, _ = review_context

    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_002",
                "discipline": "electrical",
                "description": "Efficiency Target",
                "source": "Handbook Section 3.2",
                "target_value": 0.95,
                "unit": "ratio",
                "acceptance_criterion": "Efficiency > 92% at full load",
                "mandatory": False,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")

    # Return for changes
    res_changes = service.reviews.record_decision({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_lead_human",
        "reviewer_secret": "test-review-passphrase-1",
        "decision": "CHANGES_REQUESTED",
        "comments": "Please refine the thermal dissipation budget for efficiency at 50C ambient.",
        "idempotency_key": "req-changes-key",
    })
    assert res_changes["decision"] == "CHANGES_REQUESTED"

    # Reject
    res_reject = service.reviews.record_decision({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_safety_lead",
        "reviewer_secret": "test-review-passphrase-2",
        "decision": "REJECTED",
        "comments": "Fundamental isolation discrepancy in topology definition.",
        "idempotency_key": "reject-key",
    })
    assert res_reject["decision"] == "REJECTED"


def test_stale_detection_on_spec_or_file_change(review_context):
    service, rev_id, tmp_path = review_context

    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Nominal Output",
                "source": "Handbook Section 2.1",
                "specification_field": "vout_v",
                "target_value": 1000.0,
                "unit": "V",
                "acceptance_criterion": "Measured output within 1% at 100W",
                "mandatory": True,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")

    # Approve
    service.reviews.record_decision({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_lead_human",
        "reviewer_secret": "test-review-passphrase-1",
        "decision": "APPROVED",
        "comments": "Approved requirements package",
        "idempotency_key": "approve-for-staleness-test",
    })

    # Effective review is initially not stale
    eff = service.reviews.effective_review(rev_id, "requirements")
    assert eff is not None
    assert eff["stale"] is False
    assert eff["effective_status"] == "APPROVED"

    # Now change the specification -> effective review must become STALE
    service.update_specification(
        rev_id,
        Specification(vin_nom_v=24.0, vout_v=1200.0, iout_a=0.12, isolation_requirement="3kV"),
    )
    eff_stale = service.reviews.effective_review(rev_id, "requirements")
    assert eff_stale["stale"] is True
    assert eff_stale["effective_status"] == "STALE"


def test_idempotency_and_concurrency(review_context):
    service, rev_id, _ = review_context

    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Nominal Output",
                "source": "Handbook Section 2.1",
                "specification_field": "vout_v",
                "target_value": 1000.0,
                "unit": "V",
                "acceptance_criterion": "Acceptance criteria present",
                "mandatory": True,
            }
        ],
    )
    pkg = service.reviews.prepare_package(rev_id, "requirements")

    cmd = {
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_lead_human",
        "reviewer_secret": "test-review-passphrase-1",
        "decision": "APPROVED",
        "comments": "Approved requirements package",
        "idempotency_key": "replay-idempotency-key",
    }

    # First call
    res1 = service.reviews.record_decision(cmd)
    # Replay call with exact same idempotency key
    res2 = service.reviews.record_decision(cmd)

    assert res1["review_id"] == res2["review_id"]
    assert res1["signature"] == res2["signature"]

    # Replay with same key but different decision must fail
    cmd_conflict = dict(cmd)
    cmd_conflict["decision"] = "REJECTED"
    with pytest.raises(StudioError) as exc:
        service.reviews.record_decision(cmd_conflict)
    assert exc.value.code == "CONFLICT"


def test_stage2_completion_end_to_end(review_context):
    service, rev_id, _ = review_context

    # Attempting to complete Stage 2 without human review must fail
    with pytest.raises(StudioError) as exc:
        service.engineering_lifecycle.apply({
            "schema_version": "3.1.0",
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "action": "complete",
            "source": "engineer",
            "reason": "Attempting early completion",
            "idempotency_key": "s2-early-complete",
        })
    assert exc.value.code == "INVALID_INPUT"
    assert "Authorized human review is required" in str(exc.value)

    # 2. Add complete requirements package
    add_requirements(
        service,
        rev_id,
        [
            {
                "id": "req_001",
                "discipline": "electrical",
                "description": "Nominal Output",
                "source": "Handbook Section 2.1",
                "specification_field": "vout_v",
                "target_value": 1000.0,
                "unit": "V",
                "acceptance_criterion": "Output reaches 1000V within 10ms",
                "mandatory": True,
            }
        ],
    )

    # 3. Request review
    service.reviews.request_review({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "submitter": "Junior Design Engineer",
        "reason": "Requirements baseline ready for formal review",
        "idempotency_key": "req-review-request",
    })

    # Attempting complete when review is merely requested must still fail!
    with pytest.raises(StudioError) as exc:
        service.engineering_lifecycle.apply({
            "schema_version": "3.1.0",
            "revision_id": str(rev_id),
            "stage_id": "requirements",
            "action": "complete",
            "source": "engineer",
            "reason": "Attempting completion on review requested",
            "idempotency_key": "s2-on-requested-complete",
        })
    assert exc.value.code == "INVALID_INPUT"
    assert "review requests are not approvals" in str(exc.value)

    # 4. Authorized human reviewer approves the package
    pkg = service.reviews.prepare_package(rev_id, "requirements")
    service.reviews.record_decision({
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "attempt": 1,
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "reviewer_id": "reviewer_lead_human",
        "reviewer_secret": "test-review-passphrase-1",
        "decision": "APPROVED",
        "comments": "Approved requirements package for Stage 2",
        "idempotency_key": "formal-human-approval",
    })

    # 5. Now completing Stage 2 must succeed!
    service.engineering_lifecycle.apply({
        "schema_version": "3.1.0",
        "revision_id": str(rev_id),
        "stage_id": "requirements",
        "action": "complete",
        "source": "Lead Engineer",
        "reason": "Stage 2 review approved and all criteria satisfied",
        "idempotency_key": "s2-complete-success",
    })

    lifecycle_after = service.engineering_lifecycle.get(rev_id)
    s2_after = next(s for s in lifecycle_after["stages"] if s["definition"]["id"] == "requirements")
    assert s2_after["status"] == "COMPLETED"
    s3_after = next(s for s in lifecycle_after["stages"] if s["definition"]["id"] == "feasibility")
    assert s3_after["status"] == "NOT_STARTED"
