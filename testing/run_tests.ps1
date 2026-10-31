param([switch]$SkipExe)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run testing/setup.ps1 first.' }
Push-Location $ProjectRoot
try {
    $RunArgs = @('-m', 'testing.run_acceptance')
    if ($SkipExe) { $RunArgs += '--skip-exe' }
    & $Python @RunArgs
    if ($LASTEXITCODE -ne 0) { throw 'Some checks failed. See testing/results/latest/REPORT.md.' }
} finally { Pop-Location }
