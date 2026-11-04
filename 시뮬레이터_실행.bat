@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" goto run_sim
echo [ASG] 가상 환경을 찾을 수 없습니다. 설정을 진행합니다...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0testing\setup.ps1"
if errorlevel 1 goto error

:run_sim
echo [ASG] 가상 에이전트 시뮬레이터를 실행합니다...
"%~dp0.venv\Scripts\python.exe" "%~dp0tests\virtual_agent_simulation.py" --persist-data
if errorlevel 1 goto error
goto end

:error
echo.
echo [ASG] 시뮬레이터 실행 중 오류가 발생했습니다. (에러 코드: %errorlevel%)

:end
pause
exit /b %errorlevel%
