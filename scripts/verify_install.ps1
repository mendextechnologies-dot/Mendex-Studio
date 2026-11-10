# Independent wheel installation in a new environment on the SAME workstation.
# This is not second-machine qualification. Nothing is deleted or overwritten.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$verificationRoot = Join-Path $projectRoot ('.mendex/qa/install-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $verificationRoot -Force | Out-Null
$pythonPath = Join-Path $verificationRoot 'venv/Scripts/python.exe'
Push-Location $projectRoot
try {
    python -m venv (Join-Path $verificationRoot 'venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create independent virtual environment.' }
    & $pythonPath -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency install failed.' }
    & $pythonPath -m pip install . --no-deps
    if ($LASTEXITCODE -ne 0) { throw 'Wheel installation failed.' }
    & $pythonPath -m pytest -q tests
    if ($LASTEXITCODE -ne 0) { throw 'Independent-environment tests failed.' }
    Push-Location $verificationRoot
    try {
        & $pythonPath -m mendex_core.doctor --root (Join-Path $verificationRoot 'data') --export
        if ($LASTEXITCODE -ne 0) { throw 'Installed doctor failed.' }
        $priorQtPlatform = $env:QT_QPA_PLATFORM
        try {
            $env:QT_QPA_PLATFORM = 'offscreen'
            & $pythonPath -m mendex_ui --root (Join-Path $verificationRoot 'data') --smoke-test
            if ($LASTEXITCODE -ne 0) { throw 'Installed desktop launch failed.' }
        } finally { $env:QT_QPA_PLATFORM = $priorQtPlatform }
    } finally { Pop-Location }
    Write-Output "Independent install passed. Verification files retained at: $verificationRoot"
} finally { Pop-Location }
