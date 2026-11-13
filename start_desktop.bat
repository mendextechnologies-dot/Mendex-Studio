@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Mendex Engineering Studio v3.1 - Command Center
echo ========================================================
echo.

set "TAURI_EXE=%~dp0desktop\src-tauri\target\release\mendex-studio.exe"

if exist "%TAURI_EXE%" (
    echo Launching Native Tauri 2 Desktop Application...
    start "" "%TAURI_EXE%"
    exit /b 0
)

echo Starting High-Speed Vite Command Center on http://localhost:5173 ...
echo Bridged to authoritative Python Desktop Service stdio RPC.
echo.
cd /d "%~dp0desktop"
start "" http://localhost:5173
npm run dev
