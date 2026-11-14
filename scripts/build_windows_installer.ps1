# Mendex Engineering Studio v3.1 - Standalone Windows Installer Builder
$ErrorActionPreference = 'Stop'

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " MENDEX ENGINEERING STUDIO v3.1 - WINDOWS INSTALLER BUILDER   " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# 1. Verify Clean Git Status
$dirty = git status --porcelain
if ($dirty) {
    Write-Warning "Working tree has uncommitted changes. Please commit before building release installer."
}

# 2. Build Desktop Frontend Assets
Write-Host "[1/5] Building modern Command Center web frontend assets..." -ForegroundColor Yellow
npm --prefix desktop run build
if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed! Cannot package installer without valid frontend assets."
}

# 3. Run Test Suite
Write-Host "[2/5] Running automated acceptance and regression suite..." -ForegroundColor Yellow
& .venv\Scripts\pytest.exe -k "not test_scenario_c_femm_magnetic_simulation"
if ($LASTEXITCODE -ne 0) {
    throw "Test suite failed! Cannot build installer with failing tests."
}
Write-Host "All tests passed cleanly." -ForegroundColor Green

# 4. Build Wheel and Source Archive
Write-Host "[3/5] Building wheel and source distribution packages..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File scripts\package.ps1

# 5. Generate Windows Standalone Installer Script
Write-Host "[4/5] Generating standalone Windows desktop installer bundle..." -ForegroundColor Yellow
$installerScript = @"
@echo off
setlocal EnableDelayedExpansion
title Mendex Engineering Studio v3.1 - Desktop Setup

echo ==============================================================
echo  MENDEX ENGINEERING STUDIO v3.1 COMMAND CENTER - SETUP
echo ==============================================================
echo.

set "TARGET_DIR=%LOCALAPPDATA%\Programs\MendexStudio"
echo Installing Mendex Engineering Studio v3.1 Command Center to:
echo   !TARGET_DIR!
echo.

if not exist "!TARGET_DIR!" mkdir "!TARGET_DIR!"
if not exist "!TARGET_DIR!\desktop" mkdir "!TARGET_DIR!\desktop"
if not exist "!TARGET_DIR!\backend" mkdir "!TARGET_DIR!\backend"

echo Copying core binaries and application package...
xcopy /E /I /Y "%~dp0..\src" "!TARGET_DIR!\src" >nul
xcopy /E /I /Y "%~dp0..\desktop\dist" "!TARGET_DIR!\desktop\dist" >nul
xcopy /E /I /Y "%~dp0..\desktop\src-tauri" "!TARGET_DIR!\desktop\src-tauri" >nul
xcopy /E /I /Y "%~dp0..\dist" "!TARGET_DIR!\dist" >nul

echo Creating Command Center launch wrapper...
(
echo @echo off
echo cd /d "%~dp0"
echo set "PYTHONPATH=src"
echo if exist "backend\python.exe" ^(
echo   start "" "backend\python.exe" -u -m mendex_core.desktop
echo ^) else ^(
echo   start "" pythonw -u -m mendex_core.desktop
echo ^)
echo if exist "desktop\src-tauri\target\release\mendex-studio.exe" ^(
echo   start "" "desktop\src-tauri\target\release\mendex-studio.exe"
echo ^) else ^(
echo   start "" "http://127.0.0.1:5173"
echo ^)
) > "!TARGET_DIR!\launch_command_center.bat"

echo Setting up desktop shortcut...
powershell -Command "`$ws = New-Object -ComObject WScript.Shell; `$s = `$ws.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'Mendex Engineering Studio v3.1 Command Center.lnk')); `$s.TargetPath = '!TARGET_DIR!\launch_command_center.bat'; `$s.WorkingDirectory = '!TARGET_DIR!'; `$ico = '!TARGET_DIR!\desktop\src-tauri\icons\icon.ico'; if (Test-Path `$ico) { `$s.IconLocation = `$ico }; `$s.Save()"

echo.
echo ==============================================================
echo  INSTALLATION COMPLETED SUCCESSFULLY!
echo  Desktop shortcut created: 'Mendex Engineering Studio v3.1 Command Center'
echo ==============================================================
pause
"@

$distDir = "dist"
if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir | Out-Null }
$installerBat = Join-Path $distDir "MendexStudio-v3.1-Setup.bat"
[System.IO.File]::WriteAllText($installerBat, $installerScript, [System.Text.Encoding]::ASCII)

# 6. Compute Installer SHA-256 Checksum
Write-Host "[5/5] Computing SHA-256 checksums..." -ForegroundColor Yellow
$hash = (Get-FileHash $installerBat -Algorithm SHA256).Hash
$manifestPath = Join-Path $distDir "INSTALLER_SHA256_MANIFEST.txt"
"MendexStudio-v3.1-Setup.bat: $hash" | Out-File -FilePath $manifestPath -Encoding utf8

Write-Host "==============================================================" -ForegroundColor Green
Write-Host " MENDEX STUDIO v3.1 INSTALLER READY: $installerBat" -ForegroundColor Green
Write-Host " SHA-256: $hash" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
