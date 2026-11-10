# Manual source/wheel packaging only. No native tools, CI or deployment.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $dirtyFiles = git status --porcelain --untracked-files=no
    if ($dirtyFiles) { throw 'Commit all tracked changes before packaging so the wheel and source archive match.' }
    & '.venv/Scripts/python.exe' -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; packaging stopped.' }
    $version = & '.venv/Scripts/python.exe' -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
    $distributionRoot = Join-Path $projectRoot 'dist'
    New-Item -ItemType Directory -Path $distributionRoot -Force | Out-Null
    & '.venv/Scripts/python.exe' -m pip wheel . --no-deps --wheel-dir $distributionRoot
    if ($LASTEXITCODE -ne 0) { throw 'Wheel build failed.' }
    $archivePath = Join-Path $distributionRoot "mendex-studio-$version-source.zip"
    git archive --format=zip --output=$archivePath HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
    $checksumPath = Join-Path $distributionRoot "mendex-studio-$version-SHA256SUMS.txt"
    Get-ChildItem -LiteralPath $distributionRoot -File | Where-Object { $_.Name -like "*$version*" -and $_.Extension -in '.whl','.zip' } | ForEach-Object {
        $fileHash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
        "$($fileHash.Hash.ToLower())  $($_.Name)"
    } | Set-Content -LiteralPath $checksumPath -Encoding ascii
    Write-Output "Manual packages and checksums created in $distributionRoot"
} finally { Pop-Location }
