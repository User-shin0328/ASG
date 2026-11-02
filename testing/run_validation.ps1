param([switch]$TestOnly)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run testing/setup.ps1 first.' }
Push-Location $ProjectRoot
try {
    $CheckArgs = @('-m','testing.postgresql_checks','--keep-db')
    if (Test-Path -LiteralPath 'testing/.runtime/postgresql-validation/session.json') { $CheckArgs += '--reuse' }
    & $Python @CheckArgs
    if ($LASTEXITCODE -ne 0) { throw 'Validation failed. See testing/results/postgresql-validation/REPORT.md.' }
    if (-not $TestOnly) { & $Python -m testing.validation_dashboard }
} finally { Pop-Location }
