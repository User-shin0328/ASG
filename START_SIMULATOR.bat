@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" goto run_sim
echo [ASG] Virtual environment not found. Running setup...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0testing\setup.ps1"
if errorlevel 1 goto error

:run_sim
echo [ASG] Starting Virtual Agent Simulation...
"%~dp0.venv\Scripts\python.exe" "%~dp0tests\virtual_agent_simulation.py" --persist-data
if errorlevel 1 goto error
goto end

:error
echo.
echo [ASG] Simulation exited with error level %errorlevel%.

:end
pause
exit /b %errorlevel%
