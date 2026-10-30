@echo off
chcp 65001 > nul
title ASG (AI Agent Secure Gateway) - 로컬 테스트베드 런처

echo =======================================================================
echo   [ASG] AI Agent Secure Gateway 통합 테스트베드 및 SOC 대시보드
echo =======================================================================
echo.

set PY_EXE=python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set PY_EXE=py
    where py >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
            set PY_EXE="%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        ) else (
            echo [오류] 시스템에서 Python 실행 파일을 찾을 수 없습니다.
            pause
            exit /b 1
        )
    )
)

echo [*] Python 엔진을 감지했습니다: %PY_EXE%
echo [*] ASG 테스트베드 및 관제 대시보드를 기동합니다...
echo.

%PY_EXE% "%~dp0scripts\testbed_launcher.py"

pause
