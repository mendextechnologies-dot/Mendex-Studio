# Test results — first lifecycle implementation milestone

Phase 2 verification (12 November 2026): the focused engineering-record/interface/
existing job/recovery run passed 44 tests in 16.39 seconds. The initial full run
recorded 318 passed, 1 skipped in 84.74 seconds (`phase2-test-results.xml`, zero
failures/errors), but its process returned exit 1 after the summary. A separate full
confirmation run completed with **318 passed, 1 skipped in 83.45 seconds**, explicitly
printed `PYTEST_RETURN_CODE=0`, and exited 0. Its separate evidence is
`phase2-confirmation-test-results.xml`. The initial nonzero exit was not reproduced;
its XML is retained rather than overwritten. The skipped excited-FEMM reference case
remains NOT_EVALUATED, as in Phase 1.

After a final cleanup guard to refuse redirected symlink/junction rollback targets,
the 26 new record/interface tests passed again in 9.07 seconds; evidence:
`phase2-final-record-test-results.xml`. Twenty record/calculator schemas and all nine
Phase 1 schemas match their canonical models. Changed-file whitespace and Python
compile checks passed. No live engineering database was enrolled/migrated for these tests.
Phase 1 evidence below is unchanged.

Executed 12 November 2026 against the current working tree. This is backend lifecycle
and existing-application regression evidence, not final v3.1 desktop acceptance.

## Full local regression

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/v3.1/phase1-test-results.xml
```

Result: **292 passed, 1 skipped in 194.44 seconds**. Machine-readable evidence:
`phase1-test-results.xml`. The full run includes the new lifecycle tests plus existing
core, contracts, calculations, adapters, CLI, MCP, integration and Qt tests.

The skipped case was
`tests/integration/test_v20_acceptance.py::test_scenario_c_femm_magnetic_simulation`:
NOT_EVALUATED because no excited reference model with winding current and boundary
conditions exists for that scenario. It remains unavailable, not PASS. A different
existing unexcited-core test is not a replacement for that acceptance case.

## New lifecycle verification

New tests in `tests/core/test_engineering_lifecycle.py` and
`tests/integration/test_engineering_lifecycle_interfaces.py`: **25 passed** in the
focused run and included in the full regression.

Coverage includes:

- Packaged nine-stage configuration; no startup enrollment/component DDL on reads.
- Rejection of executable/unknown config, duplicate/cyclic/missing dependencies.
- Online backup digest, actual restore into an isolated database, original revision
  payload preservation, injected DDL rollback and backup failure without data changes.
- Append-only table triggers, immutable definition versions, future-component rejection.
- Explicit stage completion, blocked-stage restart, new attempts and history pagination.
- Missing/stale/damaged/wrong-kind/wrong-revision evidence and a newer attached FAIL.
- Re-evaluation of completed stages and dependencies without rewriting history.
- Optional/mandatory/review-required exemptions and review requests without approval.
- Concurrent identical retries producing one event, sequence conflicts, revision isolation.
- Separate CLI/MCP clients sharing one assignment and immediately reading each other's
  persisted changes; strict malformed-input errors and definition registration parity.

Test evidence files are explicitly synthetic software fixtures in temporary roots.
No physical measurements or engineering acceptance were manufactured. The new service
did not enroll or migrate the live engineering database during these tests.

## Additional verification and limits

`python scripts/export_lifecycle_contracts.py --check` verified nine generated schemas
against canonical Pydantic models. Python compileall and changed-file whitespace/JSON/
Markdown checks passed.

This milestone does not establish automatic UI synchronization, a complete agent-led
engineering lifecycle, authorized human approval, React/Tauri visual/desktop behavior,
large-waveform performance, frozen sidecar or clean-machine Windows/offline packaging.
Those remain pending/NOT_EVALUATED. No v3.1 production readiness claim is made.
