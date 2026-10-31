$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run testing/setup.ps1 first.' }
Push-Location $ProjectRoot
try { & $Python -m testing.console; exit $LASTEXITCODE } finally { Pop-Location }
