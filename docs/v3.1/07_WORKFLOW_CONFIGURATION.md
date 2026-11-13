# Lifecycle configuration contract

The first milestone uses JSON, Pydantic validation and the existing packaged config
directory. No YAML dependency, code loader, eval, SQL, subprocess or visual workflow
framework was added. Canonical schemas are under `contracts/v3.1/` and generated from
`engineering_lifecycle/models.py`; old/frozen schemas were not regenerated.

Each `LifecycleDefinition` has `schema_version: 3.1.0`, an identifier, semantic version,
name and one to one hundred stages. Stages describe purpose, inputs, expected outputs,
dependencies, optional/review flags and one to one hundred criteria. Unknown fields,
duplicate stage/criterion/dependency IDs, missing dependency references and dependency
cycles are rejected. Iteration is a new recorded attempt, not a dependency cycle.

Supported criterion types:

| Kind | Parameters | Meaning |
|---|---|---|
| project_context | No extra criterion parameters | Existing project metadata and revision identity; process context only |
| specification_fields | Unique nonempty list of existing Specification field names | Fields supplied, including rejection of empty/UNASSIGNED values; not completeness or compliance |
| validation_record | check_id and one evidence_kind | Attached existing numerical validation with current intact evidence and effective PASS |

No arbitrary expressions, callback/module names or file-existence completion rules
are accepted. Numerical bounds/units/values come from the existing explicit validation
contract; the lifecycle does not fabricate acceptance thresholds.

Definition `(id, version)` is immutable. Registering identical content returns the
same digest; changed content requires a new version. The packaged default identifier/
version cannot be replaced. Each revision has one immutable definition assignment;
new policy versions apply to a newly enrolled revision, not historical evidence.

Example registration file, for a software process-context fixture only:

```json
{
  "schema_version": "3.1.0",
  "source": "Engineer-supplied software fixture policy",
  "definition": {
    "schema_version": "3.1.0",
    "id": "software_fixture",
    "version": "1.0.0",
    "name": "Software context fixture; not engineering approval",
    "stages": [{
      "id": "context",
      "name": "Recorded context",
      "purpose": "Confirm the existing project identity",
      "review_required": false,
      "criteria": [{
        "id": "identity",
        "description": "Existing project and revision metadata",
        "kind": "project_context"
      }]
    }]
  }
}
```

Custom configuration is policy input from the caller, not a trusted authorization
mechanism. Setting review_required=false does not grant product, safety or manufacturing
approval; the service always reports overall engineering evaluation NOT_EVALUATED.
