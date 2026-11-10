# Mendex Engineering Studio v2.0 - Standalone Windows Installer Builder
$ErrorActionPreference = 'Stop'

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " MENDEX ENGINEERING STUDIO v2.0 - WINDOWS INSTALLER BUILDER   " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# 1. Verify Clean Git Status
$dirty = git status --porcelain
if ($dirty) {
    Write-Warning "Working tree has uncommitted changes. Please commit before building release installer."
}

# 2. Run Test Suite
Write-Host "[1/4] Running automated acceptance and regression suite..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe
if ($LASTEXITCODE -ne 0) {
    throw "Test suite failed! Cannot build installer with failing tests."
}
Write-Host "All tests passed cleanly." -ForegroundColor Green

# 3. Build Wheel and Source Archive
Write-Host "[2/4] Building wheel and source distribution packages..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File scripts\package.ps1

# 4. Generate Windows Standalone Installer Script
Write-Host "[3/4] Generating standalone Windows desktop installer bundle..." -ForegroundColor Yellow
$installerScript = @"
@echo off
setlocal EnableDelayedExpansion
title Mendex Engineering Studio v2.0 - Desktop Setup

echo ==============================================================
echo  MENDEX ENGINEERING STUDIO v2.0 - ENTERPRISE SETUP WIZARD
echo ==============================================================
echo.

set "TARGET_DIR=%LOCALAPPDATA%\Programs\MendexStudio"
echo Installing Mendex Engineering Studio v2.0 to:
echo   !TARGET_DIR!
echo.

if not exist "!TARGET_DIR!" mkdir "!TARGET_DIR!"

echo Copying core binaries and application package...
xcopy /E /I /Y "%~dp0..\src" "!TARGET_DIR!\src" >nul
xcopy /E /I /Y "%~dp0..\dist" "!TARGET_DIR!\dist" >nul
xcopy /E /I /Y "%~dp0..\resources" "!TARGET_DIR!\resources" >nul

echo Setting up desktop shortcut...
powershell -Command "`$ws = New-Object -ComObject WScript.Shell; `$s = `$ws.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'Mendex Engineering Studio v2.0.lnk')); `$s.TargetPath = 'powershell.exe'; `$s.Arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -Command cd \"\"\"!TARGET_DIR!\"\"\"; `$env:PYTHONPATH=\"\"\"src\"\"\"; pythonw -m mendex_ui'; `$s.IconLocation = '!TARGET_DIR!\resources\brand\shield-64.ico'; `$s.Save()"

echo.
echo ==============================================================
echo  INSTALLATION COMPLETED SUCCESSFULLY!
echo  Desktop shortcut created: 'Mendex Engineering Studio v2.0'
echo ==============================================================
pause
"@

$distDir = "dist"
if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir | Out-Null }
$installerBat = Join-Path $distDir "MendexStudio-v2.0-Setup.bat"
[System.IO.File]::WriteAllText($installerBat, $installerScript, [System.Text.Encoding]::ASCII)

# 5. Compute Installer SHA-256 Checksum
Write-Host "[4/4] Computing SHA-256 checksums..." -ForegroundColor Yellow
$hash = (Get-FileHash $installerBat -Algorithm SHA256).Hash
$manifestPath = Join-Path $distDir "INSTALLER_SHA256_MANIFEST.txt"
"MendexStudio-v2.0-Setup.bat: $hash" | Out-File -FilePath $manifestPath -Encoding utf8

Write-Host "==============================================================" -ForegroundColor Green
Write-Host " MENDEX STUDIO v2.0 INSTALLER READY: $installerBat" -ForegroundColor Green
Write-Host " SHA-256: $hash" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
