"""Core/support assembly workflow. File-backed draft design, append-only records."""
import json
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from .models import Model, Specification
from .engineering_records.models import StageWrite
from .engineering_lifecycle.models import LifecycleDefinition
from .evidence import digest, specification_hash
from .service import StudioError


def lifecycle_definition():
    stages = [
        ("project_initialization", "Project setup", "Establish the assembly project and revision identity."),
        ("requirements", "Assembly requirements", "Define scope, quantities, dimensions, sources and customer acceptance requirements."),
        ("materials", "Materials and supplier documentation", "Review ferrite identity, material certificates, PTFE and fastener grades."),
        ("mechanical_design", "Mechanical design and STEP parts", "Review native part geometry, controlled drawings, interfaces and assembly arrangement."),
        ("fit_review", "Fit and tolerance review", "Resolve radial clearance, axial tolerance stack and retention construction."),
        ("inspection_plan", "Dimensional inspection planning", "Define supplied criteria, methods, traceability and required physical inspection evidence."),
        ("document_review", "Assembly document review", "Review the controlled drawing set, supply BOM and outstanding decisions. This does not authorize manufacturing.")]
    return LifecycleDefinition(id="core_assembly",version="1.0.0",name="Transformer core and support assembly",
        stages=[dict(id=identifier,name=name,purpose=purpose,dependencies=[stages[i-1][0]] if i else [],
            review_required=bool(i),criteria=[dict(id="review" if i else "identity",description="Recorded human engineering review required" if i else "Project identity exists",
                kind="human_review" if i else "project_context")]) for i,(identifier,name,purpose) in enumerate(stages)])


class AssemblyDimension(Model):
    name: str = Field(min_length=1,max_length=100)
    nominal_m: float = Field(gt=0)
    minimum_m: float | None = Field(default=None,ge=0)
    maximum_m: float | None = Field(default=None,gt=0)
    source: str = Field(min_length=1,max_length=4000)

    @model_validator(mode="after")
    def ordered(self):
        if self.minimum_m is not None and self.minimum_m>self.nominal_m:
            raise ValueError("Minimum dimension exceeds nominal")
        if self.maximum_m is not None and self.maximum_m<self.nominal_m:
            raise ValueError("Maximum dimension is below nominal")
        return self


class AssemblyPart(Model):
    reference: str = Field(min_length=1,max_length=80)
    description: str = Field(min_length=1,max_length=1000)
    quantity: int = Field(gt=0,strict=True)
    material_requirement: str = Field(default="",max_length=1000)
    source: str = Field(min_length=1,max_length=4000)
    cad_relative_path: str | None = None
    notes: str = Field(default="",max_length=4000)
    dimensions: list[AssemblyDimension] = Field(default_factory=list,max_length=100)


class AssemblyIssue(Model):
    id: str = Field(min_length=1,max_length=80)
    title: str = Field(min_length=1,max_length=500)
    description: str = Field(min_length=1,max_length=4000)
    source: str = Field(min_length=1,max_length=4000)
    # A disposition documents a supplied decision; it is not a passed engineering check.
    disposition: str = Field(default="",max_length=4000)
    owner: str = Field(default="",max_length=200)


class AssemblyDesign(Model):
    schema_version: str = Field(default="1.0",pattern=r"^1\.0$")
    scope: str = Field(min_length=1,max_length=4000)
    parts: list[AssemblyPart] = Field(default_factory=list,max_length=2000)
    issues: list[AssemblyIssue] = Field(default_factory=list,max_length=200)
    notes: str = Field(default="",max_length=12000)

    @model_validator(mode="after")
    def unique(self):
        if len({p.reference for p in self.parts})!=len(self.parts) or len({i.id for i in self.issues})!=len(self.issues):
            raise ValueError("Part references and issue identifiers must be unique")
        return self


class AssemblyWrite(StageWrite):
    expected_design_sha256: str | None = Field(default=None,pattern=r"^[a-f0-9]{64}$")
    design: AssemblyDesign


class AssemblyRevision(Model):
    revision_id: UUID
    revision_label: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    expected_input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class AssemblyMesh(Model):
    positions_m: list[tuple[float,float,float]] = Field(min_length=3,max_length=50000)
    triangles: list[tuple[int,int,int]] = Field(min_length=1,max_length=100000)

    @model_validator(mode="after")
    def valid_indices(self):
        if any(i<0 or i>=len(self.positions_m) for triangle in self.triangles for i in triangle):
            raise ValueError("Mesh triangle references an unavailable vertex")
        return self


class CoreAssemblyService:
    def __init__(self,studio):
        self.studio=studio

    def _revision(self,revision_id):
        revision=self.studio.get_revision(revision_id)
        if revision.specification.workflow_profile!="core_assembly":
            raise StudioError("INVALID_INPUT","Select the core and support assembly workflow for this revision")
        lifecycle=self.studio.engineering_lifecycle.get(revision.revision_id)
        if (lifecycle["definition_id"],lifecycle["definition_version"])!=("core_assembly","1.0.0"):
            raise StudioError("CONFLICT","Assembly profile and lifecycle do not match; create an assembly workflow revision")
        return revision

    def create_revision(self,request):
        request=AssemblyRevision.model_validate(request)
        previous=self.studio.get_revision(request.revision_id)
        product=self.studio.get_product(previous.product_id)
        if product.active_revision_id!=previous.revision_id or previous.lifecycle_status!="draft":
            raise StudioError("CONFLICT","Workflow selection requires the current draft revision")
        if specification_hash(previous.specification)!=request.expected_input_hash:
            raise StudioError("CONFLICT","Specification changed; refresh before selecting the workflow")
        # The assigned definition is immutable. Preserve it by creating a new revision.
        definition=lifecycle_definition()
        self.studio.engineering_lifecycle.register_definition(definition,"Packaged core/support assembly workflow")
        old_requirements=self.studio.engineering_records.list_records("requirements",{"revision_id":str(previous.revision_id)})["records"]
        previous_design=self.overview(previous.revision_id)["design"] if previous.specification.workflow_profile=="core_assembly" else None
        spec=previous.specification.model_copy(deep=True)
        spec.workflow_profile="core_assembly"
        revision=self.studio.create_revision(product.product_id,request.revision_label,specification=spec,copy_workspace=True,expected_input_hash=request.expected_input_hash)
        ctx=dict(revision_id=str(revision.revision_id),source="Core/support workflow selection",reason="User-selected assembly workflow; previous revision and evidence retained")
        self.studio.engineering_lifecycle.enroll(dict(**ctx,definition_id=definition.id,version=definition.version,idempotency_key="core-enroll"))
        for action in ("start","complete"):
            self.studio.engineering_lifecycle.apply(dict(**ctx,stage_id="project_initialization",action=action,idempotency_key="core-init-"+action))
        self.studio.engineering_lifecycle.apply(dict(**ctx,stage_id="requirements",action="start",idempotency_key="core-req-start"))
        if old_requirements:
            requirements=[{**r,"verification_status":"NOT_EVALUATED","verification_artifact":None} for r in old_requirements[-1]["requirements"]]
            self.studio.engineering_records.save_requirements(dict(**ctx,stage_id="requirements",expected_input_hash=specification_hash(spec),
                idempotency_key="core-requirements-copy",requirements=requirements))
        if previous_design is not None:
            self.save_design(dict(**ctx,stage_id="requirements",expected_input_hash=specification_hash(spec),
                idempotency_key="core-design-copy",design=previous_design))
        return {"revision":revision.model_dump(mode="json"),"previous_revision_id":str(previous.revision_id),"engineering_status":"NOT_EVALUATED"}

    def overview(self,revision_id):
        revision=self._revision(revision_id)
        records=[]
        after=0
        while True:
            page=self.studio.engineering_records.list_records("artifact",{"revision_id":str(revision.revision_id),"limit":500,"after_sequence":after})
            records.extend(page["records"])
            if len(page["records"])<500:
                break
            after=page["next_after_sequence"]
        designs=[r for r in records if r["relative_path"].startswith("mechanical/core-assembly/design-")]
        latest=designs[-1] if designs else None
        design=None
        if latest and latest.get("snapshot_integrity") and latest.get("original_integrity") and not latest["stale"]:
            path=self.studio.root/latest["snapshot_path"]
            design=AssemblyDesign.model_validate_json(path.read_text(encoding="utf-8")).model_dump(mode="json")
        cad_integrity=design is not None
        folder=self.studio.workspace_path(revision)
        if design is not None:
            expected=latest.get("linked_cad_hashes",{})
            for part in design["parts"]:
                relative=part["cad_relative_path"]
                if relative:
                    try:
                        path=self.studio.engineering_records._confined(folder,relative)
                        cad_integrity=cad_integrity and path.is_file() and expected.get(relative)==digest(path.read_bytes())
                    except (OSError,ValueError,StudioError):
                        cad_integrity=False
        part_images={}
        img_dir=folder/"reports/part-specifications"
        if img_dir.is_dir():
            import base64
            for f in img_dir.glob("*.png"):
                try:
                    data=base64.b64encode(f.read_bytes()).decode("ascii")
                    part_images[f.stem]=f"data:image/png;base64,{data}"
                except Exception:
                    pass
        return {"design":design,"design_sha256":latest["sha256"] if latest else None,"record_id":latest["record_id"] if latest else None,
            "design_integrity":bool(design is not None and cad_integrity),"cad_integrity":cad_integrity,"engineering_status":"NOT_EVALUATED",
            "part_images":part_images,
            "workflow_profile":"core_assembly","lifecycle_definition":lifecycle_definition().model_dump(mode="json")}

    def save_design(self,request):
        request=AssemblyWrite.model_validate(request)
        revision=self._revision(request.revision_id)
        # Serialize current-version check and artifact registration under the same record transaction.
        # _write owns the atomic SQLite transaction and append-only receipt.
        filename="mechanical/core-assembly/design-"+uuid4().hex+".json"
        def perform(db,cleanup,rev,lifecycle,stage):
            current=self.overview(request.revision_id)
            if current["design_sha256"]!=request.expected_design_sha256:
                raise StudioError("CONFLICT","Assembly design changed; reload before saving")
            folder=self.studio.workspace_path(rev)
            cad_hashes={}
            for part in request.design.parts:
                if part.cad_relative_path:
                    path=self.studio.engineering_records._confined(folder,part.cad_relative_path)
                    if not path.is_file() or path.suffix.lower() not in (".step",".stp",".fcstd"):
                        raise StudioError("INVALID_INPUT","Choose an existing STEP or FreeCAD part in this revision")
                    cad_hashes[part.cad_relative_path]=digest(self.studio.engineering_records._bytes(path))
            data=request.design.model_dump_json(indent=2).encode()
            path=folder/filename
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("xb") as f:f.write(data)
            # Unique per-save directory for immutable artifact snapshot; no prior source overwritten.
            snapshot_dir=self.studio.root/".mendex/engineering-records/artifacts"/uuid4().hex
            snapshot_dir.mkdir(parents=True)
            cleanup.append(snapshot_dir)
            target=snapshot_dir/"artifact.json"
            target.write_bytes(data)
            return self.studio.engineering_records._entry(db,request,rev,lifecycle,stage,"artifact",dict(
                relative_path=filename,snapshot_path=target.relative_to(self.studio.root).as_posix(),sha256=digest(data),
                size_bytes=len(data),classification="documentation",review_status="NOT_REVIEWED",design_id=None,design_revision_id=None,
                linked_cad_hashes=cad_hashes))
        try:
            return self.studio.engineering_records._write(request,"save_core_assembly_design",perform)
        except Exception:
            # This request owns this unique unpublished file, never an older artifact.
            path=self.studio.workspace_path(revision)/filename
            if path.is_file() and path.resolve().is_relative_to(self.studio.workspace_path(revision)):
                path.unlink()
            raise

    def assembly_preview(self,revision_id):
        revision=self._revision(revision_id)
        unavailable=lambda reason:{"available":False,"reason":reason,"engineering_status":"NOT_EVALUATED"}
        records=[]
        after=0
        while True:
            page=self.studio.engineering_records.list_records("artifact",{"revision_id":str(revision.revision_id),"limit":500,"after_sequence":after})
            records.extend(page["records"])
            if len(page["records"])<500:break
            after=page["next_after_sequence"]
        candidates=[r for r in records if r["relative_path"].startswith("mechanical/core-assembly/") and r["relative_path"].endswith("/assembly-preview.json")]
        if not candidates:return unavailable("An assembly reconstruction has not been recorded for this revision.")
        record=candidates[-1]
        if record['stale'] or not record.get('original_integrity') or not record.get('snapshot_integrity'):
            return unavailable("The assembly preview record is stale, missing or changed.")
        current=self.overview(revision_id)
        if not current['design_integrity']:return unavailable("The design or linked part CAD failed its integrity check.")
        folder=self.studio.workspace_path(revision)
        try:
            raw=self.studio.engineering_records._bytes(self.studio.root/record['snapshot_path'])
            if len(raw)>4*1024*1024:return unavailable("Assembly preview exceeds the display size limit.")
            data=json.loads(raw)
            if data['design_sha256']!=current['design_sha256']:
                # Clarifications/owners can change without changing the part geometry.
                built=next((r for r in records if r['sha256']==data['design_sha256'] and r['relative_path'].startswith('mechanical/core-assembly/design-') and r.get('snapshot_integrity')),None)
                built_design=AssemblyDesign.model_validate_json(self.studio.engineering_records._bytes(self.studio.root/built['snapshot_path'])) if built else None
                def geometry(parts):
                    return [{key:p[key] for key in ('reference','quantity','cad_relative_path','dimensions')} for p in parts]
                if built_design is None or geometry(built_design.model_dump(mode='json')['parts'])!=geometry(current['design']['parts']):
                    return unavailable("The assembly was built for an earlier design snapshot with different parts or dimensions; rebuild it before treating it as current.")
            if data['units']!='m' or not isinstance(data['instances'],list) or not 1<=len(data['instances'])<=2000:
                return unavailable("Assembly geometry has invalid units or instance data.")
            if not isinstance(data['prototypes'],dict) or not 1<=len(data['prototypes'])<=30:
                return unavailable("Assembly geometry has invalid part prototypes.")
            for value in data['prototypes'].values():AssemblyMesh.model_validate(value)
            for instance in data['instances']:
                if instance['prototype'] not in data['prototypes']:raise ValueError('Unknown prototype')
                # Validate finite, bounded shape without trusting arbitrary JSON for rendering.
                import math
                transform=instance['transform']
                if len(transform)!=4 or any(len(row)!=4 for row in transform) or any(not isinstance(v,(float,int)) or not math.isfinite(v) for row in transform for v in row):
                    raise ValueError('Invalid instance transform')
            bounds=data['bounds_m']
            if len(bounds)!=2 or any(len(row)!=3 for row in bounds) or any(not isinstance(v,(int,float)) or not math.isfinite(v) for row in bounds for v in row):
                raise ValueError('Invalid assembly bounds')
            if any(bounds[0][i]>bounds[1][i] for i in range(3)) or bounds[0]==bounds[1]:raise ValueError('Empty or reversed bounds')
            counts={}
            for instance in data['instances']:counts[instance['prototype']]=counts.get(instance['prototype'],0)+1
            if data['part_counts']!=counts:raise ValueError('Instance counts differ from manifest')
            if not data.get('source_hashes') or not data.get('native_hashes'):raise ValueError('Missing source/native hashes')
            if not all(isinstance(data['native_files'].get(key),str) for key in ('step','freecad')):raise ValueError('Missing assembled native output')
            for relative,expected in {**data['source_hashes'],**data['native_hashes']}.items():
                path=self.studio.engineering_records._confined(folder,relative)
                if not path.is_file() or digest(self.studio.engineering_records._bytes(path))!=expected:
                    return unavailable("An assembly source or native output is missing or changed: "+relative)
            if any(relative not in data['native_hashes'] for relative in data['native_files'].values()):
                raise ValueError('Native file is not hash covered')
        except (OSError,ValueError,KeyError,TypeError,StudioError) as exc:
            return unavailable("Assembly evidence could not be read or validated: "+str(exc))
        img_p = folder / record['relative_path'].replace('assembly-preview.json', 'assembly-preview.png')
        preview_img = None
        if img_p.is_file():
            import base64
            preview_img = f"data:image/png;base64,{base64.b64encode(img_p.read_bytes()).decode('ascii')}"
        exp_step_p = folder / record['relative_path'].replace('assembly-preview.json', 'HFT-000-exploded-assembly.step')
        exploded_step = None
        if exp_step_p.is_file():
            exploded_step = str(exp_step_p.relative_to(folder)).replace('\\', '/')
        exp_fcstd_p = folder / record['relative_path'].replace('assembly-preview.json', 'HFT-000-exploded-assembly.FCStd')
        exploded_freecad = None
        if exp_fcstd_p.is_file():
            exploded_freecad = str(exp_fcstd_p.relative_to(folder)).replace('\\', '/')
        return {
            **data,
            "preview_image_base64": preview_img,
            "exploded_step": exploded_step,
            "exploded_freecad": exploded_freecad,
            "available": True,
            "source_integrity": True,
            "engineering_status": "NOT_EVALUATED"
        }
