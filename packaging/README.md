# Manual v0.1 distributions

`scripts/package.ps1` runs local tests, builds a Python wheel and archives committed source, then writes SHA-256 checksums under ignored `dist/`. Source-based setup and the wheel are the supported foundation distributions. Commit the reviewed sources before packaging; `git archive` packages HEAD, never uncommitted edits.

The wheel requires Python 3.13 plus requirements-lock.txt dependencies. Native engineering tools are installed separately. No installers, licenses or EDA binaries are redistributed. An optional signed/bundled desktop executable is a future distribution enhancement; no signing identity is available here.
