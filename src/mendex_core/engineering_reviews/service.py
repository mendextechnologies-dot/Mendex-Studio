"""Authoritative human engineering-review workflow and reviewer authorization service."""
import hashlib
import hmac
import json
from pathlib import Path
from uuid import UUID, uuid4

from ..engineering_lifecycle.service import canonical, fingerprint
from ..engineering_lifecycle.storage import file_hash
from ..evidence import digest, specification_hash
from ..models import now
from ..service import StudioError
from . import models, storage

MAX_FILE = 50 * 1024 * 1024


class EngineeringReviewService:
    def __init__(self, studio):
        self.studio = studio

    def _reviewers(self, db):
        rows = db.execute("SELECT id, name, email, roles, status, created_at FROM engineering_reviewers ORDER BY created_at").fetchall()
        return [
            models.ReviewerProfile(
                id=r[0],
                name=r[1],
                email=r[2],
                roles=json.loads(r[3]),
                status=models.ReviewerStatus(r[4]),
                created_at=r[5],
            )
            for r in rows if "manual_attribution" not in json.loads(r[3])
        ]

    def list_reviewers(self):
        storage.initialize(self.studio)
        with self.studio.connection() as db:
            return [r.model_dump(mode="json") for r in self._reviewers(db)]

    def register_reviewer(self, request):
        request = models.ReviewerRegistration.model_validate(request)
        # Prevent automated agents or scripts from creating unverified reviewer profiles
        if any(prefix in request.id.lower() for prefix in ("agent", "mcp", "bot", "auto", "claude", "codex")):
            raise StudioError("INVALID_INPUT", "Automated agent IDs cannot be registered as authorized human reviewers")
        storage.initialize(self.studio)
        now_iso = now().isoformat()
        secret_hash, salt = storage.hash_secret(request.secret)
        with self.studio.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT id FROM engineering_reviewers WHERE id=?", (request.id,)).fetchone()
            if existing:
                raise StudioError("CONFLICT", "Reviewer ID is already registered")
            db.execute(
                "INSERT INTO engineering_reviewers VALUES(?,?,?,?,?,?,?,?)",
                (request.id, request.name, request.email, json.dumps(request.roles), secret_hash, salt, "ACTIVE", now_iso),
            )
            return {
                "schema_version": "3.1.0",
                "reviewer": {
                    "id": request.id,
                    "name": request.name,
                    "email": request.email,
                    "roles": request.roles,
                    "status": "ACTIVE",
                    "created_at": now_iso,
                },
            }

    def prepare_package(self, revision_id, stage_id="requirements"):
        revision = self.studio.get_revision(revision_id)
        product = self.studio.get_product(revision.product_id)
        current_spec_hash = specification_hash(revision.specification)
        
        # 1. Lifecycle context & attempt
        lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
        stage = next((s for s in lifecycle["stages"] if s["definition"]["id"] == stage_id), None)
        if stage is None:
            raise StudioError("NOT_FOUND", f"Stage '{stage_id}' is not part of this lifecycle")

        # 2. Requirements snapshot
        req_records = self.studio.engineering_records.list_records("requirements", {"revision_id": str(revision.revision_id)})["records"]
        active_req_record = req_records[-1] if req_records else None
        req_digest = fingerprint(active_req_record["requirements"]) if active_req_record else "0" * 64
        requirements_list = active_req_record["requirements"] if active_req_record else []

        # 3. Missing requirements analysis
        missing_info = self.studio.engineering_records.missing_requirements(revision.revision_id)

        # 4. Workspace document hashes
        ws_path = self.studio.workspace_path(revision)
        doc_hashes = {}
        if ws_path.exists():
            for f in sorted(ws_path.glob("**/*")):
                if f.is_file() and f.stat().st_size <= MAX_FILE:
                    rel = f.relative_to(ws_path).as_posix()
                    doc_hashes[rel] = file_hash(f)

        # 5. Evidence hashes attached to current attempt
        evidence_hashes = {}
        for rec_id in stage.get("evidence_record_ids", []):
            try:
                entry = next((e for e in self.studio.validation_summary(revision.revision_id) if str(e["record"].record_id) == str(rec_id)), None)
                if entry and entry["record"].evidence_sha256:
                    evidence_hashes[str(rec_id)] = entry["record"].evidence_sha256
            except Exception:
                pass

        # 6. Conflicts analysis & safety checks
        conflicts = []
        safety_blockers = []

        # Check specification completeness for high-voltage DC-DC safety
        spec = revision.specification
        if spec.vin_nom_v is None or spec.vout_v is None:
            safety_blockers.append("Mandatory voltage specification missing (vin_nom_v or vout_v is undefined)")
        if not spec.isolation_requirement:
            safety_blockers.append("High-voltage isolation requirement must be explicitly specified")

        # Check each requirement for acceptance criteria & safety
        for req in requirements_list:
            req_id = req["id"]
            if not req.get("acceptance_criterion"):
                conflicts.append({
                    "requirement_id": req_id,
                    "conflict_type": "MISSING_ACCEPTANCE_CRITERIA",
                    "description": f"Requirement {req_id} has no defined acceptance criterion",
                    "severity": "CRITICAL" if req.get("discipline") == "safety" or req.get("mandatory") else "MAJOR",
                    "disposition": "UNRESOLVED",
                })
                if req.get("discipline") == "safety" or req.get("mandatory"):
                    safety_blockers.append(f"Safety-critical requirement {req_id} lacks acceptance criteria")

            # Numerical target vs specification check
            field = req.get("specification_field")
            if field and req.get("target_value") is not None:
                spec_val = getattr(spec, field, None)
                if spec_val is not None and abs(spec_val - req["target_value"]) > 1e-6:
                    conflicts.append({
                        "requirement_id": req_id,
                        "conflict_type": "TARGET_SPECIFICATION_MISMATCH",
                        "description": f"Target value {req['target_value']} does not match specification {spec_val} for {field}",
                        "severity": "CRITICAL",
                        "disposition": "UNRESOLVED",
                    })
                    safety_blockers.append(f"Target mismatch between requirement {req_id} and specification {field}")

        # Submitter detection from stage attempt or requirements author
        submitter = stage.get("reason", "")
        if active_req_record and active_req_record.get("source"):
            submitter = active_req_record["source"]
        elif stage.get("last_activity"):
            submitter = product.owner or "Engineer"
        if not submitter:
            submitter = "Author / Submitter"

        # Previous reviews for this stage/attempt
        history = self.list_reviews(revision.revision_id, stage_id)

        return {
            "schema_version": "3.1.0",
            "project": {
                "project_id": str(product.product_id),
                "code": product.code,
                "name": product.name,
                "category": product.category,
                "owner": product.owner,
            },
            "revision": {
                "revision_id": str(revision.revision_id),
                "revision_label": revision.revision_label,
                "lifecycle_status": revision.lifecycle_status,
                "specification": spec.model_dump(mode="json"),
                "specification_hash": current_spec_hash,
            },
            "stage": {
                "id": stage["definition"]["id"],
                "name": stage["definition"]["name"],
                "purpose": stage["definition"]["purpose"],
                "attempt": stage["attempt"],
                "status": stage["status"],
                "review_status": stage["review_status"],
            },
            "requirements_package": {
                "record_id": active_req_record["record_id"] if active_req_record else None,
                "digest": req_digest,
                "count": len(requirements_list),
                "requirements": requirements_list,
            },
            "missing_information": missing_info.get("missing", []),
            "document_hashes": doc_hashes,
            "evidence_hashes": evidence_hashes,
            "conflicts": conflicts,
            "safety_blockers": safety_blockers,
            "safety_items": [{"id": "safety_" + hashlib.sha256(b.encode()).hexdigest()[:24], "description": b}
                             for b in safety_blockers],
            "submitter": submitter,
            "review_history": history,
            "ready_for_approval": len(requirements_list) > 0 and len(safety_blockers) == 0,
        }

    def request_review(self, request):
        request = models.ReviewRequestCommand.model_validate(request)
        revision = self.studio.get_revision(request.revision_id)
        if revision.lifecycle_status != "draft":
            raise StudioError("IMMUTABLE", "Review request requires a draft revision")
        
        # Update stage attempt to AWAITING_REVIEW
        stage_cmd = {
            "schema_version": "3.1.0",
            "revision_id": str(request.revision_id),
            "stage_id": request.stage_id,
            "action": "request_review",
            "source": request.submitter,
            "reason": request.reason,
            "idempotency_key": request.idempotency_key,
        }
        event = self.studio.engineering_lifecycle.apply(stage_cmd)
        return {
            "schema_version": "3.1.0",
            "revision_id": str(request.revision_id),
            "stage_id": request.stage_id,
            "review_status": "REQUESTED",
            "submitter": request.submitter,
            "event": event,
        }

    def record_decision(self, command):
        command = models.ReviewDecisionCommand.model_validate(command)
        return self._record_decision(command)

    def record_manual_decision(self, request):
        """Desktop-local declared review; no identity authentication is claimed.

        Not exposed as a decision tool through MCP/CLI. This is a local workflow
        convention, not a security boundary against software running as this user.
        """
        request = models.ManualReviewDecisionCommand.model_validate(request)
        reviewer_id = "manual_" + hashlib.sha256(request.reviewer_name.casefold().encode()).hexdigest()[:32]
        command = models.ReviewDecisionCommand.model_validate({
            **request.model_dump(exclude={"reviewer_name", "expected_document_hashes", "expected_evidence_hashes"}),
            "reviewer_id": reviewer_id, "reviewer_secret": "manual-attribution-only"})
        return self._record_decision(command, manual_name=request.reviewer_name,
            expected_documents=request.expected_document_hashes, expected_evidence=request.expected_evidence_hashes)

    def _record_decision(self, command, manual_name=None, expected_documents=None, expected_evidence=None):
        storage.initialize(self.studio)
        scope = f"review:{command.revision_id}:{command.stage_id}:{command.attempt}"
        request_digest = (fingerprint(command) if manual_name is None else fingerprint({
            **command.model_dump(mode="json"), "manual_name": manual_name,
            "expected_documents": expected_documents, "expected_evidence": expected_evidence}))

        # 1. Idempotency replay check
        with self.studio.connection() as db:
            row = db.execute("SELECT operation, request_digest, response FROM engineering_review_receipts WHERE scope=? AND request_key=?",
                             (scope, command.idempotency_key)).fetchone()
            if row:
                if row[:2] != ("record_decision", request_digest):
                    raise StudioError("CONFLICT", "Idempotency key reused with different inputs or operation")
                return json.loads(row[2])

        revision = self.studio.get_revision(command.revision_id)
        if revision.lifecycle_status != "draft":
            raise StudioError("IMMUTABLE", "Review recording requires a draft revision")

        # 2. Verify current specification and requirements digests
        current_spec_hash = specification_hash(revision.specification)
        if current_spec_hash != command.expected_specification_hash:
            raise StudioError("CONFLICT", "Specification hash changed; retrieve current review package before deciding")

        package = self.prepare_package(command.revision_id, command.stage_id)
        if manual_name is not None and (package["document_hashes"] != expected_documents or package["evidence_hashes"] != expected_evidence):
            raise StudioError("CONFLICT", "Reviewed documents or evidence changed; reopen the review package")
        if command.attempt != package["stage"]["attempt"] or package["stage"]["status"] not in ("IN_PROGRESS", "AWAITING_REVIEW", "BLOCKED"):
            raise StudioError("CONFLICT", "Review the current active stage attempt before deciding")
        if package["requirements_package"]["digest"] != command.expected_requirements_digest:
            raise StudioError("CONFLICT", "Requirements snapshot changed; review the latest package")

        if len(package["requirements_package"]["requirements"]) == 0:
            raise StudioError("INVALID_INPUT", "Cannot record review on an empty requirements package")

        # 3. Automated Agent Prevention
        if any(prefix in command.reviewer_id.lower() for prefix in ("agent", "mcp", "bot", "auto", "claude", "codex")):
            raise StudioError("FORBIDDEN", "Automated agents cannot approve human engineering reviews")

        # 4. Authenticate Reviewer Credentials
        if manual_name is not None:
            r_name, r_salt, r_roles_json = manual_name, None, "[]"
        else:
            with self.studio.connection() as db:
                rev_row = db.execute("SELECT id, name, email, roles, secret_hash, salt, status FROM engineering_reviewers WHERE id=?", (command.reviewer_id,)).fetchone()
                if not rev_row:
                    raise StudioError("UNAUTHORIZED", f"Unknown reviewer ID '{command.reviewer_id}'")
                r_id, r_name, r_email, r_roles_json, r_hash, r_salt, r_status = rev_row
                if r_status != "ACTIVE":
                    raise StudioError("FORBIDDEN", "Reviewer credential has been revoked")
                if not storage.verify_secret(command.reviewer_secret, r_salt, r_hash):
                    raise StudioError("UNAUTHORIZED", "Reviewer authorization failed: invalid passphrase or secret key")

        # 5. Anti-Self-Approval & Role Authorization
        reviewer_roles = json.loads(r_roles_json)
        if manual_name is None and "requirements_reviewer" not in reviewer_roles and "lead_engineer" not in reviewer_roles:
            raise StudioError("FORBIDDEN", "Reviewer lacks 'requirements_reviewer' or 'lead_engineer' authorization")

        submitter_id = package["submitter"].lower()
        if command.reviewer_id.lower() == submitter_id or r_name.lower() in submitter_id:
            raise StudioError("FORBIDDEN", "Self-approval is strictly forbidden: the author/submitter cannot approve their own submission")

        # 5. Mandatory Safety-Critical Blockers & Deferral Verification (for APPROVED decision)
        if command.decision == models.ReviewDecision.APPROVED:
            safety_blockers = package["safety_blockers"]
            deferred_req_ids = {d.requirement_id for d in command.deferrals}

            unresolved_blockers = []
            for blocker in safety_blockers:
                # Check if any deferred requirement explicitly covers this blocker
                blocker_id = "safety_" + hashlib.sha256(blocker.encode()).hexdigest()[:24]
                is_deferred = (blocker_id in deferred_req_ids if manual_name is not None
                               else any(req_id in blocker for req_id in deferred_req_ids))
                if not is_deferred:
                    unresolved_blockers.append(blocker)

            if unresolved_blockers:
                raise StudioError("INVALID_INPUT", "Approval blocked by unresolved mandatory safety items: " + "; ".join(unresolved_blockers))
            if any(c.severity == "CRITICAL" and c.disposition == "UNRESOLVED" for c in command.conflicts):
                raise StudioError("INVALID_INPUT", "Approval blocked by unresolved critical requirement conflicts")

            # Validate each deferral structure
            for deferral in command.deferrals:
                if not deferral.rationale or not deferral.owner or not deferral.scope or not deferral.downstream_gate:
                    raise StudioError("INVALID_INPUT", f"Deferral for {deferral.requirement_id} must specify rationale, owner, scope and downstream gate")

        # 6. Compute Cryptographic Signature
        now_iso = now().isoformat()
        review_id = str(uuid4())
        sig_payload = f"{package['project']['project_id']}:{revision.revision_id}:{command.stage_id}:{command.attempt}:{command.expected_requirements_digest}:{command.expected_specification_hash}:{command.decision.value}:{command.reviewer_id}:{now_iso}"
        signature = (hashlib.sha256(sig_payload.encode("utf-8")).hexdigest() if manual_name is not None
                     else hmac.new(r_salt.encode("utf-8"), sig_payload.encode("utf-8"), hashlib.sha256).hexdigest())

        # 7. Atomically insert Review Record into SQLite
        record_data = {
            "schema_version": "3.1.0",
            "review_id": review_id,
            "project_id": package["project"]["project_id"],
            "revision_id": str(revision.revision_id),
            "stage_id": command.stage_id,
            "attempt": command.attempt,
            "requirements_record_id": package["requirements_package"]["record_id"],
            "requirements_digest": command.expected_requirements_digest,
            "specification_hash": command.expected_specification_hash,
            "document_hashes": package["document_hashes"],
            "evidence_hashes": package["evidence_hashes"],
            "conflicts": [c.model_dump(mode="json") for c in command.conflicts],
            "deferrals": [d.model_dump(mode="json") for d in command.deferrals],
            "submitter": package["submitter"],
            "reviewer_id": command.reviewer_id,
            "reviewer_name": r_name,
            "review_mode": "MANUALLY_DECLARED" if manual_name is not None else "CREDENTIAL_CHECKED",
            "identity_authenticated": False,
            "signature_kind": "CONTENT_DIGEST_NOT_IDENTITY_PROOF" if manual_name is not None else "LEGACY_HMAC",
            "decision": command.decision.value,
            "comments": command.comments,
            "signature": signature,
            "timestamp": now_iso,
            "stale": False,
            "unresolved_safety_blockers": [] if command.decision == models.ReviewDecision.APPROVED else package["safety_blockers"],
            "effective_status": "APPROVED" if command.decision == models.ReviewDecision.APPROVED else command.decision.value,
        }

        with self.studio.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            # Serialize decisions with other core writers; an earlier package
            # read is not a concurrency guarantee.
            receipt = db.execute("SELECT operation, request_digest, response FROM engineering_review_receipts WHERE scope=? AND request_key=?",
                                 (scope, command.idempotency_key)).fetchone()
            if receipt:
                if receipt[:2] != ("record_decision", request_digest):
                    raise StudioError("CONFLICT", "Idempotency key reused with different inputs or operation")
                return json.loads(receipt[2])
            fresh = self.prepare_package(command.revision_id, command.stage_id)
            if (fresh["revision"]["specification_hash"] != command.expected_specification_hash
                    or fresh["requirements_package"]["digest"] != command.expected_requirements_digest
                    or fresh["stage"]["attempt"] != command.attempt
                    or fresh["stage"]["status"] != package["stage"]["status"]
                    or fresh["document_hashes"] != package["document_hashes"]
                    or fresh["evidence_hashes"] != package["evidence_hashes"]):
                raise StudioError("CONFLICT", "Review package changed while submitting; reopen it")
            if manual_name is not None:
                # Compatibility attribution row for the existing FK. No account,
                # role authorization, password or user-visible profile is created.
                db.execute("INSERT OR IGNORE INTO engineering_reviewers VALUES(?,?,?,?,?,?,?,?)",
                    (command.reviewer_id, manual_name, "", json.dumps(["manual_attribution"]), "", "", "ACTIVE", now_iso))
            cur = db.execute(
                """INSERT INTO engineering_reviews(
                    id, project_id, revision_id, stage_id, attempt, requirements_record_id,
                    requirements_digest, specification_hash, document_hashes, evidence_hashes,
                    conflicts, deferrals, submitter, reviewer_id, decision, comments, signature,
                    idempotency_key, created_at, payload
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    review_id,
                    record_data["project_id"],
                    record_data["revision_id"],
                    command.stage_id,
                    command.attempt,
                    record_data["requirements_record_id"],
                    command.expected_requirements_digest,
                    command.expected_specification_hash,
                    json.dumps(record_data["document_hashes"]),
                    json.dumps(record_data["evidence_hashes"]),
                    json.dumps(record_data["conflicts"]),
                    json.dumps(record_data["deferrals"]),
                    record_data["submitter"],
                    command.reviewer_id,
                    command.decision.value,
                    command.comments,
                    signature,
                    command.idempotency_key,
                    now_iso,
                    canonical(record_data),
                ),
            )
            record_data["sequence"] = cur.lastrowid

            # Update lifecycle event and stage review status
            stage_review_status = "APPROVED" if command.decision == models.ReviewDecision.APPROVED else command.decision.value
            lifecycle_action = "request_review" if command.decision == models.ReviewDecision.APPROVED else ("block" if command.decision == models.ReviewDecision.REJECTED else "reopen")
            
            # Record receipt for idempotency
            db.execute(
                "INSERT INTO engineering_review_receipts VALUES(?,?,?,?,?,?)",
                (scope, command.idempotency_key, "record_decision", request_digest, canonical(record_data), now_iso),
            )

        return record_data

    def effective_review(self, revision_id, stage_id="requirements", attempt=None, db=None):
        if db is None:
            with self.studio.connection() as conn:
                return self._effective_review_db(conn, revision_id, stage_id, attempt)
        return self._effective_review_db(db, revision_id, stage_id, attempt)

    def _effective_review_db(self, db, revision_id, stage_id, attempt):
        if not storage.installed(db):
            return None
        revision = self.studio.get_revision(revision_id)
        current_spec_hash = specification_hash(revision.specification)
        
        if attempt is not None:
            row = db.execute(
                "SELECT sequence, payload FROM engineering_reviews WHERE revision_id=? AND stage_id=? AND attempt=? ORDER BY sequence DESC LIMIT 1",
                (str(revision_id), stage_id, attempt),
            ).fetchone()
        else:
            row = db.execute(
                "SELECT sequence, payload FROM engineering_reviews WHERE revision_id=? AND stage_id=? ORDER BY sequence DESC LIMIT 1",
                (str(revision_id), stage_id),
            ).fetchone()

        if not row:
            return None

        record = json.loads(row[1])
        record["sequence"] = row[0]

        # Check staleness: Specification changed?
        stale = record["specification_hash"] != current_spec_hash

        # Check staleness: Requirements record changed?
        req_records = self.studio.engineering_records.list_records("requirements", {"revision_id": str(revision_id)})["records"]
        current_req_digest = fingerprint(req_records[-1]["requirements"]) if req_records else "0" * 64
        if current_req_digest != record["requirements_digest"]:
            stale = True

        # Check staleness: Document files changed or deleted?
        ws_path = self.studio.workspace_path(revision)
        for rel, expected_hash in record.get("document_hashes", {}).items():
            file_p = ws_path / rel
            if not file_p.is_file() or file_hash(file_p) != expected_hash:
                stale = True
                break

        record["stale"] = stale
        record["effective_status"] = "STALE" if stale else record["decision"]
        return record

    def list_reviews(self, revision_id, stage_id=None):
        with self.studio.connection() as db:
            if not storage.installed(db):
                return []
            if stage_id:
                rows = db.execute(
                    "SELECT sequence, payload FROM engineering_reviews WHERE revision_id=? AND stage_id=? ORDER BY sequence DESC",
                    (str(revision_id), stage_id),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT sequence, payload FROM engineering_reviews WHERE revision_id=? ORDER BY sequence DESC",
                    (str(revision_id),),
                ).fetchall()

        results = []
        for seq, payload in rows:
            rec = json.loads(payload)
            rec["sequence"] = seq
            results.append(rec)
        return results
