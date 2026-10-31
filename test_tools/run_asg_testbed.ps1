$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Exe = Join-Path $ProjectRoot 'ASG.exe'
if (Test-Path -LiteralPath $Exe) { & $Exe; exit $LASTEXITCODE }
$Python = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run testing/setup.ps1 or build ASG.exe first.' }
Push-Location $ProjectRoot
try { & $Python -m scripts.testbed_launcher; exit $LASTEXITCODE } finally { Pop-Location }
