param([string]$Python)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Python) {
    $BundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $BundledPython) { $Python = $BundledPython }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if ($LASTEXITCODE -ne 0) { throw 'A working Python 3.10+ is required. Use -Python with its full path.' }
$EnvPython = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $EnvPython)) {
    & $Python -m venv (Join-Path $ProjectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create test environment.' }
}
& $EnvPython -m pip install -r (Join-Path $PSScriptRoot 'build-requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
Write-Host 'Ready. Run .\testing\run_tests.ps1 or .\scripts\build_exe.ps1'
