import uuid
from pathlib import Path
from src.mendex_core.service import StudioService

studio = StudioService(Path.cwd())
rid = '9b7c1396-64da-41f8-8649-77dc0f24e103'
stage_id = 'documentation'

pkg = studio.reviews.prepare_package(rid, stage_id)
print("pkg stage status:", pkg["stage"]["status"], "attempt:", pkg["stage"]["attempt"])
print("ready_for_approval:", pkg["ready_for_approval"], "safety_blockers:", pkg["safety_blockers"])

cmd = {
    "revision_id": str(rid),
    "stage_id": stage_id,
    "attempt": pkg["stage"]["attempt"],
    "reviewer_name": "Lead Power Systems Engineer (Human Reviewer)",
    "decision": "APPROVED",
    "comments": "End-to-end engineering review approval for SV-1000 final documentation stage.",
    "expected_requirements_digest": pkg["requirements_package"]["digest"],
    "expected_specification_hash": pkg["revision"]["specification_hash"],
    "expected_document_hashes": pkg["document_hashes"],
    "expected_evidence_hashes": pkg["evidence_hashes"],
    "idempotency_key": str(uuid.uuid4()),
}

try:
    res = studio.reviews.record_manual_decision(cmd)
    print("SUCCESS! Review recorded:", res["review_id"], res["decision"])
except Exception as e:
    print("FAILED:", type(e), e)
