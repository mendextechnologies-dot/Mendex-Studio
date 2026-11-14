# 12 — Performance & Reliability (measured)

Audit date: 2026-11-14. Host: Windows 11, Python 3.13.7 (`.venv`).

The desktop backend (`python -m mendex_core.desktop --root <temp>`) was driven over its **stdio JSON-lines protocol** by `bridge.py.txt` and `perf.py.txt`. There is no HTTP server. Roots were seeded in-process with N projects, each lifecycle-enrolled. Raw output is in `docs/audit/evidence/ui_perf_e2e/perf.log` and `perf200_quiet.log`.

Single run per configuration, on a developer laptop with other apps running (a user LTspice GUI and two pre-existing desktop backends). Treat these as indicative, not benchmark-grade.

## Startup and memory

| N projects | spawn → handshake reply | RSS (launcher + interpreter) idle | RSS after load |
|---|---|---|---|
| 1 | 0.707 s | 60.6 MB | 62.3 MB |
| 50 | 0.731 s | 59.9 MB | 63.7 MB → 74.0 MB after the large-artifact tests |
| 200 | 1.084 s (1.287 s quiet re-run) | 60.7 MB | 63.5 MB |

## Endpoint latency (stdio round trip, median / max of 10–15 sequential calls)

| Method | N=1 | N=50 | N=200 (first run*) | N=200 quiet re-run |
|---|---|---|---|---|
| overview | 27 / 30 ms | 74 / 80 ms | 1544 / 4346 ms | 470 / 1764 ms |
| projects | 1.5 / 1.8 ms | 48 / 62 ms | 1769 / 3327 ms | 1265 / 1582 ms |
| reports | 2.4 / 3.0 ms | 256 / 329 ms | 3432 / 6699 ms | 2088 / 2164 ms |
| tools (live probes) | 147 / 160 ms | 247 / 323 ms | 907 / 2851 ms | 534 / 599 ms |
| settings | 51 / 154 ms | 150 / 197 ms | 132 / 165 ms | — |
| simulations (0 jobs) | 0.5 ms | 0.6 ms | 3.5 ms | — |
| components | 0.4 ms | 0.9 ms | 1.8 ms | — |
| project (one) | 39 / 54 ms | 43 / 93 ms | 23 / 37 ms | — |

\*The first N=200 run overlapped with a headless-Chrome screenshot session against another temp root, so it is inflated. The quiet re-run is the better figure.

**Scaling defect (HIGH for the multi-project use case):** `projects`, `overview` and `reports` are O(N) with per-project queries that each open a fresh SQLite connection. A cProfile of `DesktopService.projects()` in-process at N=200 measured 0.256 s: 401 `sqlite3.connect` calls and 802 `execute` calls (`service.py:75-95` → `StudioService.list_revisions` / `get_product`). `reports` walks every product and revision.

The round trip over the bridge (1.2–2.1 s) is several times slower than the in-process time. The cause was not isolated: thread-pool contention and GIL are suspected but not verified.

The raw database is not the bottleneck. `count(*)` over all 22 tables took 2.4 ms (N=1) and 11.5 ms (N=200); the DB file was 0.73 MB.

## Polling load (what the open UI costs)

The App poll cycle (overview, projects and simulations concurrently, every 4 s, `App.tsx:64`), with backend CPU measured across 10 cycles:

| N | wall time per cycle | backend CPU per cycle | approx. share of one core at 4 s |
|---|---|---|---|
| 1 | 85 ms | 86 ms | 2.2 % |
| 50 | 245 ms | 366 ms | 9.1 % |
| 200 | 647 ms | 2,736 ms | **68 %** (first, contended run) |

The page-level poll comes on top of this: the Tools page adds 0.5–0.9 s of live tool probing every 4 s, and the Reports page adds about 2 s at N=200. Polling continues with no visibility pause or backoff.

## Large artifacts

* A revision with a 50 MiB random `.raw`, an 11.6 MB ASCII `.raw` and 1,200 small files:
  * `project` median 207 ms; payload 169 kB (file list capped at 1000 entries by `limits.files`).
  * `waveform` on the 50 MiB binary: 15 ms → `UNSUPPORTED` (binary is refused; the size cap is 50 MiB).
  * `waveform` on the ASCII file: 15 ms → `{"samples": [], "traces": []}`. Nothing is parsed, so the endpoint is a stub (see doc 09).
* RSS grew from 63.7 to 74.0 MB.

## Concurrency and long-running jobs

* 20 concurrent `project` requests: 0 errors (the pending cap of 16 was not hit, because requests drain quickly).
* A `projects` call issued while a `waveform` call was in flight completed normally. The read pool has 4 workers.
* **Simulations do not run in the desktop backend at all.** The UI has no run method, so a simulation cannot block the desktop bridge. A real LTspice run through the CLI (`simulation run`, E2E step 8) took 1.2 s wall time in a separate process, and the backend reflected the new job on its next `simulations` call.
* Defect: the job record reports `execution_time_s: 0.0` for that run (see doc 14).
* LTspice's own 60 s timeout is in `design/ltspice_runner.py:113`. A long-running or hung solver was not tested.

## Shutdown, orphans, error recovery

| Test | Result |
|---|---|
| `shutdown` RPC | process exit rc 0 (all runs) |
| stdin EOF (simulates Tauri or Vite closing the pipe) | exit in 0.07 s, rc 0, no surviving child |
| kill backend (launcher and interpreter) mid-`project` request | no response, as expected; no surviving children |
| restart after kill | handshake in 1.457 s; 50/50 projects intact |
| restart after clean shutdown (E2E) | handshake in 0.865 s; project payload byte-identical apart from `timestamp` |
| LTspice orphans after the E2E simulation | none observed. The only LTspice.exe was the user's pre-existing GUI (PID 14896). |

Client-side recovery comes from code only and was not exercised in Tauri:
* The Vite plugin answers pending requests with 503 `BRIDGE_RESTARTING` on exit and respawns on the next request. Its 30 s timeout returns 504.
* Tauri `main.rs:27-31` restarts the child if `try_wait` reports it exited.
* The UI keeps the last data and shows `syncError` or "Displayed records may be stale".

Observation: two `mendex_core.desktop` processes **without `--root`** (PIDs 18964 and 19836) were already running on the machine during the audit. They were started outside this audit and are presumably a dev/Tauri session using the default (repo) root. They were left untouched.

## Severity summary

1. HIGH: Desktop list endpoints scale badly: about 1.3–2.1 s per call at 200 projects, with N+1 SQLite connections. Combined with 4 s polling, the open UI costs a large share of a core (68 % measured at N=200 under contention).
2. MEDIUM: `tools` live-probes executables on every 4 s poll (0.15–0.9 s each).
3. MEDIUM: No polling backoff or visibility pause.
4. LOW: `execution_time_s` is recorded as 0.0 for a real run; the waveform stub means large-result handling is untested beyond refusal paths.
5. OK: startup under 1.3 s, RSS about 60–75 MB, clean shutdown, no orphans, data intact after kill and restart.
