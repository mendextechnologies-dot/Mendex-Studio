# 15. Security & Reliability Audit

**Target:** Stdio Transport, Process Isolation, Memory & File Boundaries  
**Status:** **PASS**

---

## 1. Security Architecture

1. **No Network Listeners**: Mendex Studio opens 0 public listening sockets. Communication occurs entirely over local stdio or in-process Python calls.
2. **Frame Bounding**: `src/mendex_core/desktop/__main__.py` enforces a strict request maximum of 256 KiB and response maximum of 8 MiB.
3. **Execution Timeouts**: External solver subprocesses (LTspice, FEMM, KiCad) enforce hard execution timeouts (30 to 120s) preventing hung zombie processes.
4. **Filesystem Confinement**: Path traversal outside the configured data root is rejected.
