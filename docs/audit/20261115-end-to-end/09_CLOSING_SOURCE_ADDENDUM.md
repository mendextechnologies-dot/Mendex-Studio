# Closing source and evidence addendum

**15 November 2026 · AUDIT-1.** This qualifies all eight reports. The repository was not stationary during assessment. Findings must be interpreted against the captured versions and execution evidence.

## Concurrent changes

[preservation.json](evidence/preservation.json) records changed source and live files, with no monitored removals at that comparison. Changes included `service.py`, `thermal_engine.py`, desktop UI, live simulation RAW/log files and procurement documents; new BOM exports and an enclosure generator appeared. The audit did not invoke services against live products, run their simulations, or edit those application files. Do not claim that the whole workspace stayed byte-identical. Those concurrent changes were left in place and were not attributed to an identified actor.

The initial source/data baseline is [snapshot-before.json](evidence/snapshot-before.json). [Source copies at close](evidence/source-at-close/) preserve inspected implementations for reproducibility, with [hashes](evidence/source-at-close.json). The git-status capture was refreshed by the probe continuation; it is not an immutable start-of-session tree listing. Source hash comparisons are the stronger record of drift. This audit is a working-tree assessment, not acceptance of a clean immutable commit.

## Enclosure and TIM additions: partial capability, not wholly absent

Closing source adds `StudioService.generate_enclosure_model/get_enclosure_model` and `src/integrations/generators/enclosure_generator.py`. It generates a FreeCAD script, an SVG drawing, a Markdown thermal-interface specification and a manifest, with optional FreeCAD STEP execution. `calculate_pcb_thermal_field` also accepts chassis/TIM parameters and computes a parallel resistance approximation. These are additional implemented pieces and should be retained as **Partially implemented** mechanical/mounting capability.

An isolated closing probe called enclosure generation with `export_step=False` on an empty revision. It returned success and generated SVG/Markdown/script/manifest using default board dimensions; `step_generated=false`. That verifies draft-file generation only. No enclosure STEP was generated or fit-validated by this probe. Existing Copper PCB STEP export tests passed separately; that does not validate this new enclosure generator.

Important limitations in captured source:

- Defaults substitute an 85 × 65 mm PCB when actual geometry is missing/small, with corner-hole assumptions rather than verified actual mounting-hole alignment.
- Output supplies a material/finish, approximate mass, component height, mounting/torque and TIM part/construction details without complete project-specific evidence.
- The enclosure response reports fixed bare/chassis temperatures (144.0/55.8 °C) and improvement (88.2 °C), even for the empty revision with no heat source or losses. These are template values, **not calculated or measured qualification evidence**.
- The TIM document includes an “Alternate Qualified” label, dielectric/safe-grounding wording, installation torque and PASS/EXCELLENT without independently verified part/application evidence. This audit does not endorse those claims or instructions.
- The new getters may generate output, including optional native execution, and the enclosure generator writes fixed workspace paths without a draft guard. G03 therefore applies to these additions too.
- Closing thermal reprobe still returned `overall_status=PASS`, no hotspots, zero losses and both standards flags true on an empty board. The new chassis path does not resolve G04 or G11.

Evidence: [final-source-probes.json](evidence/final-source-probes.json) and corresponding [disposable files](evidence/final-probe-root/). Mechanical files listed as requiring manual work in Reports 4–6 now have some draft-generation support; actual correct dimensions, part selection, collisions, tolerances, insulation, mounting and installation remain **Not Verified / NOT_EVALUATED**. No generic complete manufacturing/mounting package has been demonstrated.

## Integrity presentation

Closing `RecordFormView.tsx` treats only `snapshot_integrity === false` as failure and otherwise renders “Cryptographic Integrity Verified” / “INTEGRITY VALID”. Missing/null values therefore enter the verified branch. Source also contains signature/provenance wording that needs to retain the core manual-review limitation: a content hash is not proof of identity, credentials or organizational authority. This is a source-confirmed presentation risk, not a fresh browser-render test. G16 records its remedy and acceptance criteria.

## Verification boundary

The initial suite ran while source changes were possible. A supplementary run against the closing source passed **56 tests**, covering engineering lifecycle, reviews, PCB workspace and thermal tests. TypeScript checking passed initially; a final no-emit check is recorded separately in the verification summary. Neither establishes manufacturing correctness or qualifies the new enclosure/TIM assumptions. The laboratory-plan crash, incomplete/corrupt archive behavior, generic WCCA assumptions and unsourced procurement metadata remain supported by their isolated evidence and captured source.

## Final cutoff: 15 November 2026, 14:40:18 Asia/Calcutta

A further concurrent packaging change added `.step/.stp/.svg` and enclosure/mechanical/TIM names to the candidate scan, a mechanical category, and desktop/client enclosure routes. **The initial standalone-STEP omission finding is superseded for this later source.** A final isolated probe confirmed `model.step` is now included, while simulation RAW/netlist and requirements JSON remain excluded. An incomplete archive and subsequently corrupted archive still report READY. No external snapshot collection, mandatory-file completeness, archive revalidation or engineering approval gate was established by this change.

Evidence: [final-cutoff-probe.json](evidence/final-cutoff-probe.json) and [source copies at final cutoff](evidence/source-at-final-cutoff/). This is the assessment cutoff; later ongoing edits are outside its evidence scope. The 56-test run preceded these final packaging/route changes, so it does not claim regression qualification of them. The targeted cutoff probe checks the specific scan/READY behavior only. Full manufacturing and mechanical qualification remains NOT_EVALUATED.
