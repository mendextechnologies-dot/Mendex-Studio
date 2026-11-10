# v0.1 foundation requirements audit

Authority: the supplied guide's final Part IV foundation addendum, especially sections 24, 27, 28 and 33. Earlier long-term pilot capabilities are not silently promoted into three-day deliverables.

| Requirement | Implemented behavior / evidence |
|---|---|
| Desktop launch and dashboard/navigation | PySide6 real-service desktop; headless and Windows-native smoke captures |
| Product creation/editing and persisted specs | Typed SI contracts; atomic metadata/spec save; reopen tests |
| Revision creation/editing and lifecycle | Draft-label editing, draft/review locks, new revision archives prior baseline; no approval bypass |
| Workspace folders and revision metadata | UUID-based folders, creation-time revision.json, immutable specification snapshot exports |
| Transformer/converter/device/PCB foundations | Revision-specific workspaces, required inputs and explicit unimplemented engineering execution |
| Tool registry and detection | Packaged JSON definitions, configured/PATH/known locations, available Windows version metadata; never falsely READY |
| Full adapter boundary | probe/validate/prepare/run/parse/self_test contracts, declared capabilities, schemas, timeout/error taxonomy |
| Simulation job framework | Append-only persisted NOT_SUPPORTED availability requests with input snapshots; no invented runs |
| Validation/provenance | Manual values/criteria, actual nonempty evidence for PASS/FAIL, copied SHA-256 artifacts, stale/tamper checks |
| Basic reporting | Draft HTML + frozen JSON with requirements, history, hashes, limitations, tools, requests, rules and plugins |
| VS Code/native-file integration | Shell-free editor handoff; real VS Code, Explorer and document windows observed on primary workstation |
| Engineering guidelines and rule registry | Revisioned guidance, category-specific required inputs and physical-verification rules; no invented thresholds |
| AI service interface | Typed provider-neutral, read-only contract with UNAVAILABLE default and no network calls |
| Plugin loader | JSON manifests extend discovery and rules; IDs/schema/path validation, content hashes, atomic rejection; no executable plugin code |
| CLI and diagnostics | Shared services, JSON errors, workstation/core readiness distinction and local diagnostic exports |
| Tests/install/backup | Automated deliberate failures, migrations, UI, evidence, plugin and backup/restore tests; fresh local wheel installation |
| Manual packaging | Python wheel, committed-source archive and SHA-256 checksums; no bundled third-party tools |
| Repository/documentation | main on user-provided GitHub repository, frozen JSON schemas, examples, setup/rollback, test log and limitations |
| Foundation software release | Tag only after primary installation/smoke/tests/issues gate; no manufacturing approval |

Not claimed by v0.1: automatic FEMM/LTspice correctness, verified transformer design, completed KiCad integration, physical/HV safety, standards compliance, production readiness, advanced AI, automated laboratory controls, enterprise PLM, cloud identity or CI/CD. Independent-engineer pilot qualification remains unperformed and is not represented as a completed software implementation task.
