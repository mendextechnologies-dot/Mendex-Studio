# Known limitations

- Integrated foundation: discovery, manual validation, draft HTML/JSON reports, VS Code/native-file handoff and doctor/diagnostic export are implemented. Interactive handoff on a second machine remains unqualified.
- Module workspaces are explicitly NOT IMPLEMENTED; no numeric engineering outputs exist.
- Specification and manual-check editing use typed JSON; category-specific guided forms are future enhancements.
- No approvals, manufacturing release, users/permissions or cloud sharing.
- Previous revisions freeze specification metadata only; native CAD versioning remains pending. Validation evidence is copied and hashed, with original filename preserved.
- Product metadata remains editable; deletion is intentionally unavailable to preserve revision history.
- Local desktop smoke tests cannot replace second-engineer clean-machine qualification.
- Tool discovery searches PATH and known Windows locations, with explicit executable-path configuration. A missing result can mean installation elsewhere. Versions remain unknown in application discovery; compatibility, licenses and benchmarks are not qualified. No native installers or solver processes run.
- Validation values, acceptance criteria, evidence classification and reviewer identity are manually declared. They are not authenticated or independently verified. Historical PASS records do not approve products or establish safety.
- HTML/JSON reports are drafts. PDF/Word generation, embedded plots and report signing are not implemented.
- Append-only storage is enforced through the service and SQLite validation triggers; a user with direct filesystem/database access can alter local data. Evidence changes are detected on recheck. Signed/tamper-proof storage is unavailable.
- Plugin registration supports reviewed in-process Python adapters. Automatic loading of untrusted packages is unavailable. Simulation runs are contract-only with execution disabled.
- Automated editor/native launch tests use mocks; an actual editor/CAD window is not launched during those tests. A returned process ID means launch requested, not application readiness or engineering execution.
- Bootstrap and an independent wheel installation are tested on this workstation. Second-engineer/clean-machine qualification, signed installer and final v0.1.0 tag remain pending.
