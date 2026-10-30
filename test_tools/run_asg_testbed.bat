@echo off
chcp 65001 > nul
title ASG (AI Agent Secure Gateway) - 로컬 테스트베드 런처

echo =======================================================================
echo   [ASG] AI Agent Secure Gateway 통합 테스트베드 및 SOC 대시보드
echo =======================================================================
echo.

set PY_EXE=

if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    set PY_EXE="%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    goto :FOUND
)

python -c "import sys" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PY_EXE=python
    goto :FOUND
)

py -c "import sys" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PY_EXE=py
    goto :FOUND
)

echo [오류] 시스템에서 정상적으로 실행 가능한 Python 환경을 찾을 수 없습니다.
echo Python 3.10 이상을 설치하거나 환경 변수 PATH를 확인해 주세요.
pause
exit /b 1

:FOUND
echo [*] Python 엔진 감지: %PY_EXE%
echo [*] ASG 테스트베드 및 관제 대시보드를 기동합니다...
echo.

%PY_EXE% "%~dp0..\scripts\testbed_launcher.py"

pause
