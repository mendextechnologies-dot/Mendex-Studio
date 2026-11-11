# Codex v1.5 integration workflow

Current scope (11 November 2026): PLECS, MATLAB/Simulink, Ansys Maxwell,
Ansys Icepak and SolidWorks integrations have been removed from active catalogs,
connectors and UI. There are 13 retained catalog resources (14 on the dashboard
with ngspice). Historical settings/jobs/evidence are retained; old settings do not
reactivate removed tools. Free/open-source tools and freeware LTspice remain.

This branch adds the Codex-owned application half of the two-agent plan. It preserves the original v0.1 workflows and does not claim all native connectors are implemented.

## Run and demonstrate

Use a virtual environment installed from the existing requirements-lock.txt and editable project setup. The catalog JSON is packaged by the existing package-data rule; no dependency manifest changes are needed.

```powershell
python -m mendex_ui
python -m pytest -q
python scripts/v15_codex_smoke.py
python -m mendex_core.integration_cli catalog
python -m mendex_core.integration_cli new-workspace "Generic software demo"
python -m mendex_core.integration_cli demo --workspace <workspace-uuid>
python -m mendex_core.integration_cli jobs
python -m mendex_core.integration_cli report <job-uuid>
```

The CLI demo is foreground and waits for its synthetic job; it is not a detached native runner. UI jobs run outside the Qt thread. Create a generic workspace in Jobs & Results, optionally attach a harmless input, start the synthetic demo, inspect progress/logs and preview verified artifacts. Cancel/retry preserves history; retries get new IDs. Reports export fresh HTML/JSON under the job directory. No engineering product or model is created.

Tool Center shows all 18 inventory names. Save absolute local paths and non-secret license-review references; detect never upgrades a tool to READY. Native verification remains unavailable without an accepted Agent 2 connector. A synthetic success means software completed only; engineering remains NOT_EVALUATED. Commercial entries do not block startup and never cause purchase, activation or installation.

Dataset Catalog records the source URL, exact release/version, license-review reference and provenance. An optional local file is copied opaquely and hashed (20 MiB limit); no upstream data is downloaded, licensed, parsed or declared valid by the UI. Overlapping MagNet names remain distinct inventory labels. SwitchLossDB canonical upstream/license resolution is pending.

## Persistence and limits

SQLite schema v4 is an additive migration from v3. Back up `.mendex` and products together while Studio is closed before upgrading; older applications cannot open v4 databases. Restore a matching backup for rollback. Generic workspace inputs are under `.mendex/iw`, dedicated job evidence under `.mendex/ij`, and resource copies under `.mendex/datasets`. These files stay excluded from Git.

The Codex queue uses two cooperative worker threads, bounded request/input/artifact/log/preview sizes and controlled workdirs. It never launches a subprocess. Agent 2 must supply the executable allowlist, process isolation, process-tree cancellation and real runner resource bounds. Adapter exceptions, malformed/missing/escaping outputs, deliberate failure, cooperative timeout/cancellation and altered evidence are handled without an engineering PASS. Cross-process job control and automatic crash recovery are not claimed; cancel must be acknowledged by the owning process/runner. Terminal jobs reopen through persisted records.

## Catalog reference audit

Metadata was checked against official/project references on 10 November 2026. These references inform labels and review notes, not machine-specific licenses or executable readiness:

- [IEEE PELS inventory](https://github.com/IEEE-PELS/awesome-PELS-open-source-editors-pick): inventory reference for SwitchLossDB; canonical upstream and release license unresolved.
- [Princeton MagNet](https://github.com/PrincetonUniversity/magnet), [MagNet Challenge](https://github.com/minjiechen/magnetchallenge): related datasets/research/benchmarks; exact release terms must be reviewed separately.
- [KiCad licenses](https://www.kicad.org/about/licenses/), [ADI LTspice](https://www.analog.com/ltspice), [FEMM](https://www.femm.info/), [FreeCAD](https://www.freecad.org/): distribution-specific software/data terms and connector verification remain required.
- [OpenModelica licensing](https://openmodelica.org/useresresources/license/), [Qucs-S](https://ra3xdh.github.io/), [Python license](https://www.python.org/psf/license/), [Jupyter](https://jupyter.org/about), [Git](https://git-scm.com/): exact installed distributions/backends remain Agent 2's audit responsibility.
- PLECS, MATLAB/Simulink, Maxwell/Icepak and SolidWorks are optional commercial inventory entries per the owner-supplied plan; no paid integration is enabled here.

See docs/CONTRACTS.md, docs/OWNERSHIP_V1_5.md and docs/AGENT2_HANDOFF.md before implementing or merging connectors. Owner acceptance and the final combined release remain pending.
