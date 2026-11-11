# 13 - Security and Reliability (independent)

All findings come from code reading unless marked LIVE. Line numbers marked "(now)" are for untracked files that were being edited concurrently during the audit.

| # | Sev | Finding | Evidence |
|---|---|---|---|
| S1 | P0 (project rule) | `delete_product` permanently deletes validations, runs, reports, approvals, and measurements, then runs `shutil.rmtree` on `products/<id>` (report and evidence files). It has no immutability or archived-baseline check and no confirmation. It is exposed to agents via MCP `delete_product` and CLI `delete-product`. This conflicts with AGENTS.md "Never change frozen baselines or raw evidence" | service.py:242-293; controller.py:926 (now); server.py:167 (now); cli.py:39,358 |
| S2 | P1 | `open_tool_file` accepts any absolute path, and relative `..` paths are not contained. LIVE: `../../../../../Windows/win.ini` resolved to `C:\Users\Sagar\AppData\Windows\win.ini` | controller.py:1017-1023 (now); probe id 22 |
| S3 | P1 | The MCP/CLI default data root is `Path.cwd()`, and `mcp_config.json` uses `--root .`. Agent writes therefore land in the repo. The untracked repo files `engineering_designs/1af250bd...json` and `workspaces/4f7a9de8...` show this already happens (not created by this audit) | cli.py:30; mcp/__main__.py:15; controller.py:38; mcp_config.json |
| S4 | P1 | There is no approval gate and there are no MCP annotations for process-launching tools. `open_native` calls `os.startfile` for .html/.htm/.pdf/.json/.md/.txt/.csv/.log, so a workspace .html file opens in the default browser | launch.py:165-167 |
| S5 | P1 | The API key is stored in plaintext JSON at `<data_root>/.mendex/ai_config.json` and copied into `os.environ`. It is protected only by `.gitignore` (`.mendex/`, line 5). There is no DPAPI/keyring. Parse errors are swallowed (`except Exception: pass`) | ai/config.py:19-21,47-63,66-88 |
| S6 | P2 | `SafeRunner.allowlist_patterns` is stored but never used, so `validate_command` only checks that the executable exists. `MAX_CAPTURE_BYTES` truncates after `communicate()` has already buffered the full output, so it does not bound memory. Positive: timeout plus `taskkill /T /F` tree-kill and a cancel watcher are implemented. No `shell=True` was found in src | safe_runner.py:67-68,70-86,116-150,195-211 |
| S7 | P2 | The design runners bypass SafeRunner. LTspice uses `subprocess.run(timeout)` with no tree-kill. FEMM uses `Popen` plus a polling loop and `terminate()`, with shared `ifile.txt`/`ofile.txt` in the FEMM root dir, so concurrent runs collide. `freecadcmd` runs with timeout 30 and errors swallowed. An untracked `femm_in.tmp` sits in the repo root | ltspice_runner.py:134-141; femm_runner.py:71-72,87,97,188; design/service.py:244-251 |
| S8 | P2 | LIVE: the MCP stdio loop is single-threaded and writes full tracebacks to stderr. With an undrained stderr pipe the server hung more than 120 s; in-process the same call took 0.001 s. Synchronous `run_simulation` blocks all requests | server.py:510,635 (now) |
| S9 | P2 | Input handling is ad hoc. Missing keys surface as KeyError text, and schemas are not enforced. Calculation range checks do exist (LIVE: negative freq and duty 7 rejected) | server.py `_dispatch_tool` |
| S10 | info | Positive: workspace IDs are UUID-validated with resolve + relative_to containment, and artifact paths reject `..` and absolute escapes (LIVE). Subprocess calls use argument lists | controller.py:44-110 (now) |

## Not verified
- Solver timeout/kill behavior in practice (no solvers were run).
- Report immutability on regeneration.
- Log rotation.
- Dependency CVEs (no `pip audit`; installs forbidden).
