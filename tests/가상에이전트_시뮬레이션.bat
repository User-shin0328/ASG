@echo off
setlocal
cd /d "%~dp0.."
if exist "%~dp0..\.venv\Scripts\python.exe" goto run_sim
echo [ASG] 가상 환경을 찾을 수 없습니다. 설정을 진행합니다...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\testing\setup.ps1"
if errorlevel 1 goto error

:run_sim
echo [ASG] 가상 에이전트 및 사내 DB 대시보드 시뮬레이션을 시작합니다...
"%~dp0..\.venv\Scripts\python.exe" tests\virtual_agent_simulation.py
if errorlevel 1 goto error
echo.
echo [ASG] 시뮬레이션이 정상 종료되었습니다.
goto end

:error
echo.
echo [ASG] 실행 중 오류가 발생했습니다. (ErrorLevel: %errorlevel%)

:end
pause
exit /b %errorlevel%
