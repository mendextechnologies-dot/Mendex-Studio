# 11 Data Integrity and Revisions (independent)

Method: scripts integ.py and conc.py in %TEMP%\mendex-audit\scripts, data root %TEMP%\mendex-audit\core.

## IDs and timestamps
- Product, revision, workspace and report IDs are UUID4 (live output).
- Revision labels look like R001.
- Timestamps are ISO UTC (for example created_at ...+00:00).

## Hashes
- Reports: input_hash plus a sha256 of the report file (controller.py:798).
- Artifacts: sha256 computed only when listed (controller.py:644).
- PCB: manifest.sha256 (pcb.py:248).
- Design artifacts: sha256 (design/service.py:147,165).

## Tamper test (P1)
- I appended bytes to a generated report.html. get_validation_summary did not change.
- StudioService has no verify or integrity method (searching dir() for 'verif' returned []).
- **Changes made outside the app are not detected.** Hashes are recorded when files are created but never checked again.

## Overwrite and atomicity
- A second generate_report created a new report_id. The first report was not overwritten.
- Writes are plain write_text (service.py:153, 567-568). There is no temp-file plus os.replace pattern anywhere in src (grep), so writes are not atomic.

## Deletion (P0)
- delete_product (service.py:242-293) hard-deletes validation, report, run, approval, measurement and ECR rows and the evidence folders. It does not check frozen state.
- It is exposed through MCP (mcp/server.py:98,489) and the CLI (cli.py:359).

## Concurrency
- Two processes each ran 15 create_product calls on the same root: 30/30 succeeded with 0 errors. SQLite uses timeout=10 (service.py:103), and delete uses BEGIN IMMEDIATE.
- No WAL mode was found. JSON and artifact files (for example engineering_designs/*.json) have no file locking. Concurrent writes to those files: NOT VERIFIED.

## Offline operation
- intelligence/models.py:243 imports requests (AI provider path).
- No httpx, supabase or urllib imports were found in mendex_core (grep).
- The core engineering paths I probed ran offline.

## Not verified
- Solver config capture and simulation run IDs: NOT VERIFIED (solvers not run).
