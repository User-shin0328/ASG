# ASG (AI Agent Secure Gateway) - 통합 로컬 테스트베드 PowerShell 실행 스크립트
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "ASG Local Testbed & SOC Dashboard"

$PyExe = "python"
$HasPython = Get-Command python -ErrorAction SilentlyContinue

if (-not $HasPython -or $HasPython.Version -eq "0.0.0.0") {
    $CodexPy = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $CodexPy) {
        $PyExe = $CodexPy
    } else {
        $PyCandidate = Get-Command py -ErrorAction SilentlyContinue
        if ($PyCandidate) {
            $PyExe = "py"
        } else {
            Write-Host "[오류] 시스템에서 유효한 Python 3.10+ 버전을 찾을 수 없습니다." -ForegroundColor Red
            Exit 1
        }
    }
}

$ScriptPath = Join-Path $PSScriptRoot "..\scripts\testbed_launcher.py"
& $PyExe $ScriptPath
