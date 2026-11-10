# Dependency Requests from Agent 2 (Antigravity) • v1.5

**Date:** 10 November 2026  
**Requester:** Agent 2 (Engineering Integration Lead)  
**Approver / Owner:** Agent 1 (Codex / Integration Lead)

---

## 1. Current Dependency Status

For the implementation of **v1.5 Foundation and Core Adapters**:
- Standard library Python 3.13 (`subprocess`, `hashlib`, `shutil`, `json`, `dataclasses`, `pathlib`, `typing`) plus existing project dependencies (`pydantic>=2.12,<3`) are **100% sufficient**.
- No external packages are currently required to run the safe runner, tool detection, LTspice batch execution, dataset validation, and adapter test suites.
- Therefore, **ZERO immediate modifications to `pyproject.toml` or `requirements-lock.txt` are requested at this time.**

---

## 2. Future Optional Dependency Proposals (For Joint Review in Later Sprints)

When external tools are installed and specialized capabilities are enabled on developer workstations, Codex may consider adding the following optional dependencies under `[project.optional-dependencies]`:

| Proposed Package | Target Integration | Purpose | Priority |
|---|---|---|---|
| `pyfemm` | FEMM 2.0 | Python wrapper for FEMM ActiveX/Lua automation | Low (gated on FEMM installation) |
| `scipy` / `numpy` | Analytical Math / LTspice raw parsing | Vectorized waveform processing and FFT analysis | Medium (deferred until advanced waveform UI) |
| `h5py` | MagNet Research Dataset | Reading dense HDF5 waveform files from Princeton MagNet repository | Medium (CSV/JSON supported natively) |

*Agent 2 will not edit `pyproject.toml` or install unapproved packages.*
