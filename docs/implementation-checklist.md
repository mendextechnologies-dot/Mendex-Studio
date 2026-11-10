# Three-day implementation checklist

Scope: final foundation addendum of supplied guide; user owns approval decisions. Start: 10 November 2026, Asia/Calcutta. This is an execution sequence, not a claim that elapsed calendar days have passed.

## Day 1 — foundation

- [x] Read complete source guide, inspect workspace and development runtime.
- [x] Establish package boundaries, service contract and engineering rules.
- [x] Implement typed specifications, SQLite v1 migration, products and revisions.
- [x] Create per-revision local workspaces; freeze previous specifications.
- [x] Build real-service desktop dashboard, product editor and navigation.
- [x] Pass persistence, failure-path and desktop smoke tests (10 passed).
- [x] Record environment and test results; initialize local Git baseline.

## Day 2 — extensibility

- [x] Adapter protocol, discovery capability registry and native executable detection/configuration.
- [x] Simulation-run contracts, no automatic execution claims.
- [x] Append-only manual validation entries with provenance and evidence hashes.
- [x] Basic draft HTML/JSON report service and module-specific workspace views.
- [x] Tool Manager, validation/report views and revisioned knowledge content (0.2).
- [x] Verify missing tools, no-PASS-without-evidence, stale evidence and deliberate failure cases (17 tests).

## Day 3 — integration

- [x] VS Code/project-file launching with path validation (automated launch mocks).
- [x] CLI doctor, diagnostic export and UI/core integration.
- [x] Product → specification → revision → tool check → evidence → draft report automated smoke test, including deliberate FAIL (21 tests).
- [x] Reproduce wheel installation in a fresh local environment; document rollback and remaining issues.
- [x] Capture seven desktop screens and run installed-package desktop smoke test.
- [x] Complete actual primary-workstation VS Code, File Explorer and native-document handoff (matching windows observed).
- [x] Complete backup/restore regression; preserve specification/evidence hashes after restore.
- [x] Add the remaining framework contracts: AI interface, versioned rule registry, data-only plugin loader and persisted simulation availability requests.
- [x] Complete draft/review editing, label changes, atomic product/specification saves, metadata/specification exports and evidence opening.
- [x] Pass 28 tests, Windows-native desktop smoke and independent local wheel-install checks.
- [x] Prepare v0.1.0 foundation tag and manual source/wheel/checksum packaging after the primary-machine release gates pass.

## Separate pilot qualification (not part of a software implementation claim)

- [ ] Independent second-engineer / clean-machine acceptance, following docs/manual-acceptance.md.
- [ ] Native solver benchmarks, actual engineering calculations, KiCad checks, physical/HV testing and product review: post-foundation scope, not claimed by this release.

Source repository: https://github.com/mendextechnologies-dot/Mendex-Studio · branch `main` · foundation software version `0.1.0`. See docs/requirements-matrix.md for the audit. Final-addendum release gate: primary-machine clean installation, repeatable smoke, no fabricated results, tests green and open issues documented. This replaces the earlier overly broad checklist item that conflated the foundation tag with independent pilot qualification. No engineering/manufacturing approval, CI/CD or deployment is implemented.
