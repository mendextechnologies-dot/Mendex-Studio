# 16. Windows Packaging Audit

**Target:** Desktop Installer & Executable Packaging  
**Status:** **PARTIAL**

---

## 1. Current State

- **PyInstaller Packaging**: `packaging/` contains PyInstaller specification files for creating standalone Windows binaries of the Python backend.
- **Tauri Packaging**: Because the Tauri desktop shell has not been implemented, no MSI or NSIS Tauri Windows installer exists.
- **Current Distribution**: Source wheel / virtual environment execution via `.venv\Scripts\python.exe -m mendex_ui`.
