@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0..\.venv\Scripts\python.exe" goto run_test
echo [ASG] 가상환경이 없습니다. 환경 설정을 먼저 진행합니다...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto error

:run_test
echo [ASG] 테스트를 실행합니다...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1"
if errorlevel 1 goto error
echo.
echo [ASG] 모든 테스트가 정상 통과했습니다.
goto end

:error
echo.
echo [ASG] 테스트 실패 (에러 코드: %errorlevel%)

:end
pause
exit /b %errorlevel%
