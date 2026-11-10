# Agent 2 handoff and integration review prerequisites

Codex branch: codex/v1.5-integration. Stable contract freeze: **12b56c3**. Canonical imports: `mendex_core.integration_contracts`. Generic executor registration hook: `StudioService(root).integrations.register_reviewed_adapter(adapter)`. This is an explicit reviewed-code hook, not an automatic plugin importer. The application does not load another worktree's source or trust an unreviewed READY assertion.

Run contract tests first, followed by the regression/integration suite. Use a separate worktree/branch and do not modify Codex UI, persistence, schemas or dependency manifests. Propose any boundary/dependency change separately before affected implementation work. No cross-boundary changes are self-merged.

At read-only inspection, Agent 2 was working on antigravity/v1.5-integrations at 7ed71de with additional uncommitted files, including src/integrations/v15_connector.py and docs/ADAPTER_TEST_EVIDENCE.md. Those uncommitted sources are not imported or merged. The following are review observations, not edits or a final judgment on a future PR:

1. The observed connector reports a hard-coded LTspice tested version and returns READY when a path exists. Before acceptance, read the actual configured executable's version and tie verification to reproducible smoke evidence for that exact path/version/operation.
2. Verification accepts configuration.executable_path, while observed execute() uses the constructor's configured path. Bind the executed binary to the verified configuration; configuration changes must invalidate readiness. Declare immutable configuration/thread-safety behavior against the frozen interface.
3. Codex stages inputs at their declared relative paths, often inputs/<file>. Outputs must be collected relative to the actual input location, not assumed at the workdir root. Missing expected solver outputs must not become a successful result merely because the process exited zero.
4. Preserve fractional timeouts and map runner cancellation/timeout states into the frozen terminal statuses. Agent 2 owns process-tree termination and must supply tests demonstrating it. The Codex fixture proves cooperative application behavior only.
5. Supply raw reproducible logs, actual input/model hashes, installed versions and environment metadata. The observed evidence note's OS/Git values differ from the initial repository audit; reconcile them using the actual smoke environment. Documentation assertions alone are not smoke evidence or owner approval.
6. Resource parsers must retain upstream/version/license provenance and avoid treating an arbitrary CSV/JSON shape as validation of a real MagNet/SwitchLossDB release. The Codex metadata UI explicitly leaves interpretation and review pending.

Once a committed PR and evidence are available, Codex can review it in the integration branch, run the frozen contract tests, perform approved synthetic/native smoke checks where installed, and then run the full UI/DB/regression suite. Until then all native operations in this branch remain unverified and no full-v1.5 release is declared.
