# v1.5 integration decisions

- 2026-11-10: Final two-agent addendum governs this request. Implement Codex-owned UI/services/DB/contracts; leave native adapters/runners/parsers/dataset integration files to Agent 2. No sub-agent is substituted for the owner's second agent.
- Preserve the released v0.1 app and legacy contracts. New plan version labels are not evidence of a v1.3 application release. New boundary schema is 1.5.0, not an unsupported full-v1.5 release claim.
- Keep the original main worktree clean. Freeze contracts in an isolated `codex/v1.5-integration` worktree and publish that branch for review; do not merge unreviewed cross-boundary changes or tag a full release.
- No new runtime dependencies, commercial software, downloads, global configuration, CI/CD, cloud service, hardware control or product-specific design is required.
- A Codex-owned in-process synthetic adapter proves UI → service → job → evidence → report without claiming native-solver support. Agent 2 must supply the real safe subprocess runner and operation-specific smoke evidence.
- Research entries are resources/datasets/benchmarks, not installable solvers. MagNet overlap and unresolved dataset terms remain visible. License review metadata is not legal approval; no proprietary dataset content is bundled.
- 2026-11-10: Agent 2 subsequently became active in the original checkout on antigravity/v1.5-integrations. Its uncommitted connector/evidence was inspected read-only; no imports, edits, verification claims or merges were made. Review prerequisites are recorded in docs/AGENT2_HANDOFF.md.
- Jobs use the same SQLite database with additive schema v4. Frozen 1.5.0 interface files are unchanged after 12b56c3. Manifest bytes are written deterministically and hashed separately in persistence; staged inputs, output artifacts and logs are verified on read. The synthetic fixture is explicitly distinct from Agent 2's safe subprocess runner.
