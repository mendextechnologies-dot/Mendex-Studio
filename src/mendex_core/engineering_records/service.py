"""Persistent agent operations over the existing authoritative engineering services."""
import json
import shutil
import sys
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

from ..engineering_lifecycle.service import canonical, fingerprint
from ..engineering_lifecycle.storage import file_hash
from ..evidence import Report, specification_hash
from ..integration_contracts import TERMINAL, safe_relative
from ..models import now
from ..service import StudioError
from . import calculations, models, storage

MAX_FILE = 50 * 1024 * 1024


class EngineeringRecordService:
    def __init__(self, studio):
        self.studio = studio

    def _context(self, request):
        revision = self.studio.get_revision(request.revision_id)
        if revision.lifecycle_status != "draft":
            raise StudioError("IMMUTABLE", "Engineering writes require a draft revision")
        if specification_hash(revision.specification) != request.expected_input_hash:
            raise StudioError("CONFLICT", "Specification changed; retrieve current input hash")
        lifecycle = self.studio.engineering_lifecycle.get(revision.revision_id)
        stage = next((s for s in lifecycle["stages"] if s["definition"]["id"] == request.stage_id), None)
        if stage is None:
            raise StudioError("NOT_FOUND", "Stage is not part of the revision lifecycle")
        if stage["status"] != "IN_PROGRESS" or stage["stale"]:
            raise StudioError("CONFLICT", "Start/reopen a current stage attempt before recording outputs")
        return revision, lifecycle, stage

    def _mutate(self, request, operation, scope, perform):
        if len(request.model_dump_json()) > 512 * 1024:
            raise StudioError("INVALID_INPUT", "Engineering request exceeds 512 KiB")
        request_digest = fingerprint(request)
        storage.initialize(self.studio)
        cleanup = []
        try:
            with self.studio.atomic() as db:
                row = db.execute("SELECT operation,request_digest,response FROM engineering_records_receipts WHERE scope=? AND request_key=?", (scope, request.idempotency_key)).fetchone()
                if row:
                    if row[:2] != (operation, request_digest):
                        raise StudioError("CONFLICT", "Idempotency key reused with different inputs or operation")
                    return json.loads(row[2])
                result = perform(db, cleanup)
                db.execute("INSERT INTO engineering_records_receipts VALUES(?,?,?,?,?,?,?,?)",
                           (scope, request.idempotency_key, operation, request_digest, canonical(result), request.source, request.reason, now().isoformat()))
                return result
        except Exception:
            # Only unique directories created by this failed operation are candidates.
            for folder in reversed(cleanup):
                if folder.is_symlink() or folder.is_junction():
                    continue
                resolved = folder.resolve()
                if resolved == folder and resolved.is_relative_to(self.studio.root) and resolved != self.studio.root and resolved.is_dir():
                    shutil.rmtree(folder)
            raise

    def _write(self, request, operation, perform):
        return self._mutate(request, operation, "revision:" + str(request.revision_id),
                            lambda db, cleanup: perform(db, cleanup, *self._context(request)))

    @staticmethod
    def _entry(db, request, revision, lifecycle, stage, kind, data):
        record = {"schema_version": "3.1.0", "record_id": str(uuid4()), "kind": kind,
                  "project_id": str(revision.product_id), "revision_id": str(revision.revision_id),
                  "stage_id": request.stage_id, "assignment_id": lifecycle["assignment_id"],
                  "attempt": stage["attempt"], "input_hash": request.expected_input_hash,
                  "specification": revision.specification.model_dump(mode="json"), "source": request.source,
                  "reason": request.reason, "timestamp": now().isoformat(), "engineering_status": "NOT_EVALUATED", **data}
        cursor = db.execute("INSERT INTO engineering_records_entries(id,revision_id,kind,stage_id,payload,digest) VALUES(?,?,?,?,?,?)",
                            (record["record_id"], str(revision.revision_id), kind, request.stage_id, canonical(record), fingerprint(record)))
        return {"sequence": cursor.lastrowid, **record}

    def update_project(self, request):
        request = models.ProjectUpdate.model_validate(request)
        self.studio.get_product(request.project_id)

        def perform(db, cleanup):
            current = self.studio.get_product(request.project_id)
            if current.updated_at != request.expected_updated_at:
                raise StudioError("CONFLICT", "Project metadata changed; retrieve current updated_at")
            product = self.studio.update_product(request.project_id, request.name, request.owner, request.description)
            return {"schema_version": "3.1.0", "product": product.model_dump(mode="json"), "source": request.source,
                    "reason": request.reason, "engineering_status": "NOT_EVALUATED"}

        return self._mutate(request, "update_project", "project:" + str(request.project_id), perform)

    def save_requirements(self, request):
        request = models.RequirementsWrite.model_validate(request)

        def perform(db, cleanup, revision, lifecycle, stage):
            previous = db.execute("SELECT id FROM engineering_records_entries WHERE revision_id=? AND kind='requirements' ORDER BY sequence", (str(revision.revision_id),)).fetchall()
            return self._entry(db, request, revision, lifecycle, stage, "requirements",
                               {"requirements": [r.model_dump(mode="json") for r in request.requirements],
                                "requirements_version": len(previous) + 1, "supersedes_record_id": previous[-1][0] if previous else None})

        return self._write(request, "save_requirements", perform)

    def list_records(self, kind, request):
        request = models.RecordList.model_validate(request)
        self.studio.get_revision(request.revision_id)
        with self.studio.connection() as db:
            if not storage.installed(db):
                return {"schema_version": "3.1.0", "records": [], "next_after_sequence": request.after_sequence}
            rows = db.execute("SELECT sequence,payload,digest FROM engineering_records_entries WHERE revision_id=? AND kind=? AND sequence>? AND (? IS NULL OR stage_id=?) ORDER BY sequence LIMIT ?",
                              (str(request.revision_id), kind, request.after_sequence, request.stage_id, request.stage_id, request.limit)).fetchall()
        records = [self._read_entry(sequence, payload, expected) for sequence, payload, expected in rows]
        return {"schema_version": "3.1.0", "records": records,
                "next_after_sequence": records[-1]["sequence"] if records else request.after_sequence}

    def _read_entry(self, sequence, payload, expected):
        record = json.loads(payload)
        if fingerprint(record) != expected:
            raise StudioError("STORAGE_ERROR", "Engineering record digest mismatch")
        revision = self.studio.get_revision(record["revision_id"])
        record.update(sequence=sequence, stale=record["input_hash"] != specification_hash(revision.specification))
        if record["kind"] == "artifact":
            record.update(self._artifact_integrity(record))
        record["effective_status"] = "NOT_EVALUATED" if record["stale"] or record.get("snapshot_integrity") is False or record.get("original_integrity") is False else "RECORDED"
        return record

    def get_record(self, record_id):
        record_id = str(UUID(str(record_id)))
        with self.studio.connection() as db:
            if not storage.installed(db):
                raise StudioError("NOT_FOUND", "Engineering record not found")
            row = db.execute("SELECT sequence,payload,digest FROM engineering_records_entries WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise StudioError("NOT_FOUND", "Engineering record not found")
        return self._read_entry(*row)

    def missing_requirements(self, revision_id):
        revision = self.studio.get_revision(revision_id)
        with self.studio.connection() as db:
            row = db.execute("SELECT sequence,payload,digest FROM engineering_records_entries WHERE revision_id=? AND kind='requirements' ORDER BY sequence DESC LIMIT 1", (str(revision.revision_id),)).fetchone() if storage.installed(db) else None
        if row is None:
            return {"schema_version": "3.1.0", "evaluation": "NOT_EVALUATED", "missing": ["No structured requirements snapshot recorded"], "record_id": None}
        record = self._read_entry(*row)
        missing = []
        if record["stale"]:
            missing.append("Requirements snapshot belongs to an older specification")
        for requirement in record["requirements"]:
            if not requirement["mandatory"]:
                continue
            field = requirement["specification_field"]
            if not requirement["acceptance_criterion"]:
                missing.append(requirement["id"] + ": acceptance criterion missing")
            if field and getattr(revision.specification, field) in (None, "", "UNASSIGNED", []):
                missing.append(requirement["id"] + ": specification field missing: " + field)
            if field and requirement["target_value"] is not None and getattr(revision.specification, field) != requirement["target_value"]:
                missing.append(requirement["id"] + ": supplied target differs from specification")
            units = {"vin_min_v": "V", "vin_nom_v": "V", "vin_max_v": "V", "vout_v": "V", "iout_a": "A", "switching_frequency_hz": "Hz", "ambient_temperature_k": "K"}
            if field in units and requirement["target_value"] is not None and requirement["unit"] != units[field]:
                missing.append(requirement["id"] + ": target unit must match specification unit " + units[field] + "; no conversion assumed")
        return {"schema_version": "3.1.0", "record_id": record["record_id"], "missing": missing,
                "evaluation": "NOT_EVALUATED", "note": "Missing-input coverage only; criteria and standards have not been verified."}

    def calculation_capabilities(self):
        return calculations.capabilities()

    def run_calculation(self, request):
        request = models.CalculationWrite.model_validate(request)
        item = calculations.catalog()[request.calculation]
        parameters = item["model"].model_validate(request.parameters).model_dump(mode="json")

        def perform(db, cleanup, revision, lifecycle, stage):
            from ..controller import MendexEngineeringController
            result, error = None, None
            try:
                result = MendexEngineeringController(service=self.studio).run_calculation(request.calculation, parameters)
                canonical(result)  # Reject non-finite/non-JSON results before claiming execution success.
            except (ArithmeticError, ValueError) as exc:
                result, error = None, str(exc)
            return self._entry(db, request, revision, lifecycle, stage, "calculation",
                               {"calculation": request.calculation, "parameters": parameters, "result": result,
                                "assumptions": request.assumptions, "warnings": item["warnings"],
                                "formula_reference": item["formula"], "implementation": item["module"].__name__ + "." + item["function"],
                                "implementation_sha256": file_hash(Path(item["module"].__file__)), "python_version": sys.version.split()[0],
                                "status": "FAILED" if error else "SUCCEEDED", "error": error,
                                "unit_conventions": "Input/output suffixes preserve existing core units; no implicit unit conversion."})

        return self._write(request, "run_calculation", perform)

    def _confined(self, base, relative):
        path = (base / safe_relative(relative)).resolve()
        if not path.is_relative_to(base.resolve()) or not path.is_relative_to(self.studio.root):
            raise StudioError("INVALID_INPUT", "File path escapes its engineering context")
        return path

    @staticmethod
    def _bytes(path):
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise StudioError("INVALID_INPUT", "File is missing or exceeds 50 MiB")
        with path.open("rb") as handle:
            content = handle.read(MAX_FILE + 1)
        if len(content) > MAX_FILE:
            raise StudioError("INVALID_INPUT", "File grew beyond 50 MiB")
        return content

    def register_artifact(self, request):
        request = models.ArtifactWrite.model_validate(request)

        def perform(db, cleanup, revision, lifecycle, stage):
            source = self._confined(self.studio.workspace_path(revision), request.relative_path)
            if request.design_id:
                design = self.studio.design.get_design(str(request.design_id))
                if not design or not (design.product_id == str(revision.product_id) or design.workspace_id in (str(revision.product_id), str(revision.revision_id))):
                    raise StudioError("INVALID_INPUT", "Design is not associated with this project/revision")
                if str(request.design_revision_id) not in {r.id for r in design.revisions}:
                    raise StudioError("NOT_FOUND", "Design revision not found")
            data = self._bytes(source)
            from ..evidence import digest
            if digest(data) != request.expected_sha256:
                raise StudioError("CONFLICT", "Artifact content differs from supplied digest")
            folder = self._confined(self.studio.root, ".mendex/engineering-records/artifacts/" + str(uuid4()))
            folder.mkdir(parents=True, exist_ok=False)
            cleanup.append(folder)
            target = folder / ("artifact" + source.suffix[:16])
            with target.open("xb") as handle:
                handle.write(data)
            return self._entry(db, request, revision, lifecycle, stage, "artifact",
                               {"relative_path": request.relative_path, "snapshot_path": target.relative_to(self.studio.root).as_posix(),
                                "sha256": request.expected_sha256, "size_bytes": len(data), "classification": request.classification,
                                "design_id": str(request.design_id) if request.design_id else None,
                                "design_revision_id": str(request.design_revision_id) if request.design_revision_id else None,
                                "review_status": "NOT_REVIEWED"})

        return self._write(request, "register_artifact", perform)

    def _artifact_integrity(self, record):
        revision = self.studio.get_revision(record["revision_id"])
        paths = {"snapshot": (self.studio.root, record["snapshot_path"]),
                 "original": (self.studio.workspace_path(revision), record["relative_path"])}
        result = {}
        for label, (base, relative) in paths.items():
            try:
                path = self._confined(base, relative)
                result[label + "_integrity"] = path.is_file() and path.stat().st_size <= MAX_FILE and file_hash(path) == record["sha256"]
            except (OSError, ValueError, StudioError):
                result[label + "_integrity"] = False
        return result

    def record_validation(self, request):
        request = models.ValidationWrite.model_validate(request)

        def perform(db, cleanup, revision, lifecycle, stage):
            if request.evidence_path:
                path = Path(request.evidence_path)
                if not path.is_absolute():
                    raise StudioError("INVALID_INPUT", "Evidence path must be absolute")
                from ..evidence import digest
                if digest(self._bytes(path)) != request.expected_evidence_sha256:
                    raise StudioError("CONFLICT", "Evidence differs from supplied digest")
            record = self.studio.record_validation(revision.revision_id, request.check, request.evidence_path)
            folder = self.studio.workspace_path(revision) / "validation" / str(record.record_id)
            cleanup.append(folder)
            if request.evidence_path and record.evidence_sha256 != request.expected_evidence_sha256:
                raise StudioError("CONFLICT", "Evidence changed during registration")
            return self._entry(db, request, revision, lifecycle, stage, "validation",
                               {"validation_record": record.model_dump(mode="json"),
                                "note": "Caller-supplied numerical check, evidence and reviewer; not authorization."})

        return self._write(request, "record_validation", perform)

    def validation_results(self, revision_id):
        return {"schema_version": "3.1.0", "engineering_status": "NOT_EVALUATED",
                "results": [{**entry, "record": entry["record"].model_dump(mode="json")}
                            for entry in self.studio.validation_summary(revision_id)]}

    def job_detail(self, job_id):
        record = self.studio.integrations.job(job_id)
        intact = self.studio.integrations.evidence_integrity(job_id)
        return {"schema_version": "3.1.0", "job": record.model_dump(mode="json"),
                "evidence_integrity": intact, "engineering_status": "NOT_EVALUATED",
                "cancellation_supported": self.studio.integrations.cancellation_supported(job_id),
                "results_validated": False, "review_status": "NOT_REVIEWED"}

    def job_logs(self, job_id):
        return {"schema_version": "3.1.0", "job_id": str(job_id), "text": self.studio.integrations.logs(job_id), "limit_bytes": 65536}

    def job_results(self, job_id):
        detail = self.job_detail(job_id)
        return {**detail, "result": detail["job"]["result"],
                "note": "Execution results and evidence availability are separate from engineering validation."}

    def job_artifact(self, job_id, relative_path):
        return {"schema_version": "3.1.0", "job_id": str(job_id), "relative_path": relative_path,
                "text": self.studio.integrations.preview_artifact(job_id, relative_path),
                "note": "Manifest-checked preview; binary waveforms are not transformed or fabricated."}

    def cancel_job(self, request):
        request = models.JobCancel.model_validate(request)
        self.studio.integrations.job(request.job_id)

        def perform(db, cleanup):
            record = self.studio.integrations.cancel_owned(request.job_id)
            return {"schema_version": "3.1.0", "job_id": str(request.job_id), "status": record.status.value,
                    "cancellation_requested": record.status not in TERMINAL or record.status.value == "CANCELLED",
                    "note": "Cooperative request only. Solver termination is not inferred from a request."}

        return self._mutate(request, "cancel_job", "job:" + str(request.job_id), perform)

    def _report_files(self, report):
        html_path = self._confined(self.studio.root, report.report_path)
        snapshot_path = self._confined(html_path.parent, "snapshot.json")
        return {"report.html": self._bytes(html_path), "snapshot.json": self._bytes(snapshot_path)}

    def report_metadata(self, report_id):
        report = self.studio._get("reports", report_id, Report)
        revision = self.studio.get_revision(report.revision_id)
        result = {"schema_version": "3.1.0", "report": report.model_dump(mode="json"),
                  "stale": report.input_hash != specification_hash(revision.specification), "engineering_status": "NOT_EVALUATED"}
        try:
            from ..evidence import digest
            data = self._report_files(report)
            hashes = {name: digest(content) for name, content in data.items()}
            snapshot = json.loads(data["snapshot.json"])
            snapshot_matches = snapshot.get("report") == report.model_dump(mode="json")
            expected = None
            with self.studio.connection() as db:
                if storage.installed(db):
                    for (payload,) in db.execute("SELECT payload FROM engineering_records_entries WHERE revision_id=? AND kind='report'", (str(report.revision_id),)):
                        entry = json.loads(payload)
                        if entry["report"]["report_id"] == str(report.report_id):
                            expected = self.get_record(entry["record_id"])["file_hashes"]
                            break
            integrity = "INTACT" if expected == hashes and snapshot_matches else ("UNVERIFIED_LEGACY" if expected is None and snapshot_matches else "FAILED")
            result.update(available=True, file_hashes=hashes, integrity=integrity)
        except (OSError, ValueError, StudioError):
            result.update(available=False, integrity="FAILED", file_hashes={})
        return result

    def list_reports(self, revision_id):
        return [self.report_metadata(report.report_id) for report in self.studio.list_reports(revision_id)]

    def generate_report(self, request):
        request = models.ReportGenerate.model_validate(request)

        def perform(db, cleanup, revision, lifecycle, stage):
            from ..evidence import digest
            report = self.studio.generate_report(revision.revision_id)
            folder = self._confined(self.studio.root, report.report_path).parent
            cleanup.append(folder)
            hashes = {name: digest(content) for name, content in self._report_files(report).items()}
            return self._entry(db, request, revision, lifecycle, stage, "report",
                               {"report": report.model_dump(mode="json"), "file_hashes": hashes})

        return self._write(request, "generate_report", perform)

    def export_report(self, request):
        request = models.ReportExport.model_validate(request)
        report = self.studio._get("reports", request.report_id, Report)

        def perform(db, cleanup):
            from ..evidence import digest
            metadata = self.report_metadata(request.report_id)
            if not metadata["available"] or metadata["integrity"] == "FAILED":
                raise StudioError("INVALID_INPUT", "Report is missing or modified; cannot export as recorded evidence")
            data = self._report_files(report)
            if {name: digest(content) for name, content in data.items()} != metadata["file_hashes"]:
                raise StudioError("CONFLICT", "Report changed during export")
            folder = self._confined(self.studio.root, ".mendex/engineering-records/exports/" + str(uuid4()))
            folder.mkdir(parents=True, exist_ok=False)
            cleanup.append(folder)
            target = folder / "report-package.zip"
            manifest = {**metadata, "source": request.source, "reason": request.reason,
                        "note": "Report and frozen snapshot only; no raw evidence is altered or approval implied. Legacy files lack original trusted hashes."}
            with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, content in data.items():
                    archive.writestr(name, content)
                archive.writestr("manifest.json", canonical(manifest))
            return {"schema_version": "3.1.0", "report_id": str(request.report_id),
                    "path": target.relative_to(self.studio.root).as_posix(), "sha256": file_hash(target),
                    "integrity": metadata["integrity"], "engineering_status": "NOT_EVALUATED"}

        return self._mutate(request, "export_report", "report:" + str(request.report_id), perform)
