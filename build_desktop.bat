@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Mendex Engineering Studio v3.1 - Tauri Desktop Build
echo ========================================================
echo.

:: Add Cargo bin to PATH if present in USERPROFILE
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

where cargo.exe >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Rust toolchain (cargo, rustc) not found in PATH or %USERPROFILE%\.cargo\bin.
    echo.
    echo To build native Tauri 2 binaries on Windows:
    echo   1. Install Rust: winget install Rustlang.Rustup
    echo   2. Install C++ Build Tools: winget install Microsoft.VisualStudio.2022.BuildTools
    echo.
    echo Vite Command Center remains fully operational without compilation via:
    echo   start_desktop.bat (Launches in under 300 ms)
    echo.
    pause
    exit /b 1
)

echo [INFO] Found Cargo:
cargo --version
rustc --version
echo.

cd /d "%~dp0desktop"

echo [1/2] Building React frontend distribution (dist/)...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Compiling Tauri 2 native executable...
call npm run tauri build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Tauri native compilation failed. Ensure MSVC C++ Build Tools and Windows SDK are installed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo   Tauri Desktop Build Complete!
echo   Binary generated at: desktop\src-tauri\target\release\
echo ========================================================
pause
