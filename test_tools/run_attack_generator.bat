@echo off
chcp 65001 > nul
title ASG (AI Agent Secure Gateway) - 공격 & 트래픽 발생기 (Attack Simulator)

echo =======================================================================
echo   [ASG] AI Agent Secure Gateway - 대화형 공격 및 트래픽 발생기
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
echo [*] 공격 시뮬레이터를 시작합니다...
echo.

%PY_EXE% "%~dp0..\scripts\traffic_generator.py" --mode menu

pause
