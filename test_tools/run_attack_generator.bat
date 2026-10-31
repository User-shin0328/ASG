@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_attack_generator.ps1"
if errorlevel 1 pause
