# ASG (AI Agent Secure Gateway) - 로컬 테스트베드 PowerShell 실행 스크립트
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "ASG (AI Agent Secure Gateway) Testbed"

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "  🛡️ [ASG] AI Agent Secure Gateway 통합 테스트베드 및 SOC 대시보드" -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""

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

Write-Host "[*] Python 엔진을 사용합니다: $PyExe" -ForegroundColor Green
Write-Host "[*] ASG 테스트베드 및 관제 대시보드를 기동합니다..." -ForegroundColor Yellow
Write-Host ""

$ScriptPath = Join-Path $PSScriptRoot "scripts\testbed_launcher.py"
& $PyExe $ScriptPath
