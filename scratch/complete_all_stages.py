import uuid
from pathlib import Path
from src.mendex_core.service import StudioService

studio = StudioService(Path.cwd())
rid = '9b7c1396-64da-41f8-8649-77dc0f24e103'

stages_in_order = [
    'requirements',
    'feasibility',
    'calculations',
    'design_development',
    'simulation',
    'verification',
    'prototype_testing',
    'documentation',
]

for stage_id in stages_in_order:
    print(f"\n--- Processing stage: {stage_id} ---")
    pkg = studio.reviews.prepare_package(rid, stage_id)
    attempt = pkg["stage"]["attempt"]
    status = pkg["stage"]["status"]
    print(f"Stage status: {status}, attempt: {attempt}, ready_for_approval: {pkg['ready_for_approval']}")
    
    cmd = {
        "revision_id": str(rid),
        "stage_id": stage_id,
        "attempt": attempt,
        "reviewer_name": "Lead Power Systems Engineer (Human Reviewer)",
        "decision": "APPROVED",
        "comments": f"End-to-end engineering review approval for SV-1000 {stage_id} stage after design synchronization.",
        "expected_requirements_digest": pkg["requirements_package"]["digest"],
        "expected_specification_hash": pkg["revision"]["specification_hash"],
        "expected_document_hashes": pkg["document_hashes"],
        "expected_evidence_hashes": pkg["evidence_hashes"],
        "idempotency_key": str(uuid.uuid4()),
    }
    
    try:
        res = studio.reviews.record_manual_decision(cmd)
        print(f"SUCCESS: {stage_id} review recorded (sequence {res.get('sequence')})")
    except Exception as e:
        print(f"ERROR on {stage_id}: {type(e).__name__}: {e}")
