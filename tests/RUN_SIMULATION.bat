@echo off
setlocal
cd /d "%~dp0.."
if exist "%~dp0..\.venv\Scripts\python.exe" goto run_sim
echo [ASG] Virtualenv not found. Setting up...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\testing\setup.ps1"
if errorlevel 1 goto error

:run_sim
echo [ASG] Starting simulation...
"%~dp0..\.venv\Scripts\python.exe" tests\virtual_agent_simulation.py
if errorlevel 1 goto error
echo.
echo [ASG] Simulation finished.
goto end

:error
echo.
echo [ASG] Error occurred. (ErrorLevel: %errorlevel%)

:end
pause
exit /b %errorlevel%
