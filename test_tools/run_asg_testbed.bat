@echo off
if exist "%~dp0..\ASG.exe" (
  "%~dp0..\ASG.exe"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_asg_testbed.ps1"
)
if errorlevel 1 pause
