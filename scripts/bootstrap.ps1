$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    python -c "import sys; assert sys.version_info[:2] == (3,13), 'Mendex requires Python 3.13'"
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.13 and retry.' }
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    & '.venv/Scripts/python.exe' -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & '.venv/Scripts/python.exe' -m pip install -e . --no-deps
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
    & '.venv/Scripts/python.exe' -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Local tests failed.' }
    & '.venv/Scripts/python.exe' -m mendex_core.doctor
    if ($LASTEXITCODE -ne 0) { throw 'Core diagnostics are blocked. Review doctor output.' }
    Write-Output 'Setup complete. Native tools remain separately installed and unqualified until benchmark checks are implemented.'
} finally { Pop-Location }
