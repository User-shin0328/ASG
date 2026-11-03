@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0..\.venv\Scripts\python.exe" goto run_test
echo [ASG] Virtual environment not found. Running setup...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto error

:run_test
echo [ASG] Running tests from testing folder...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1"
if errorlevel 1 goto error
echo.
echo [ASG] All tests completed successfully.
goto end

:error
echo.
echo [ASG] Tests failed with error level %errorlevel%.

:end
pause
exit /b %errorlevel%
