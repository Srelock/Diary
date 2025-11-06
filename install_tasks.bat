@echo off
REM ========================================
REM Install Windows Task Scheduler Tasks
REM For Diary App Auto-Start and Daily Restart
REM ========================================
REM This script creates two scheduled tasks:
REM 1. Start app on system boot
REM 2. Restart app daily at 01:00 AM

setlocal

echo Installing Windows Task Scheduler tasks...

REM Get installation directory (passed as parameter or use default)
if "%~1"=="" (
    set "INSTALL_DIR=C:\Program Files\DiaryApp"
) else (
    set "INSTALL_DIR=%~1"
)

set "EXE_PATH=%INSTALL_DIR%\diary_app.exe"
set "RESTART_SCRIPT=%INSTALL_DIR%\restart_service.bat"

echo Installation directory: %INSTALL_DIR%
echo Executable path: %EXE_PATH%

REM Verify executable exists
if not exist "%EXE_PATH%" (
    echo ERROR: Executable not found at %EXE_PATH%
    exit /b 1
)

REM Remove existing tasks if they exist (ignore errors)
echo Removing existing tasks if present...
schtasks /Delete /TN "DiaryApp_Startup" /F >nul 2>&1
schtasks /Delete /TN "DiaryApp_DailyRestart" /F >nul 2>&1

echo.
echo Creating Task 1: Startup task...
REM Create startup task - runs on system boot
schtasks /Create /TN "DiaryApp_Startup" /TR "\"%EXE_PATH%\" --no-browser" /SC ONSTART /RL HIGHEST /F
if errorlevel 1 (
    echo ERROR: Failed to create startup task
    exit /b 1
)
echo Startup task created successfully

echo.
echo Creating Task 2: Daily restart task at 01:00 AM...
REM Create daily restart task - runs at 01:00 AM using restart script
schtasks /Create /TN "DiaryApp_DailyRestart" /TR "\"%RESTART_SCRIPT%\"" /SC DAILY /ST 01:00 /RL HIGHEST /F
if errorlevel 1 (
    echo ERROR: Failed to create daily restart task
    exit /b 1
)
echo Daily restart task created successfully

echo.
echo ========================================
echo Task installation completed!
echo ========================================
echo.
echo Created tasks:
echo 1. DiaryApp_Startup - Runs on system boot
echo 2. DiaryApp_DailyRestart - Runs daily at 01:00 AM
echo.
echo You can view tasks in Task Scheduler or run:
echo   schtasks /Query /TN "DiaryApp_Startup"
echo   schtasks /Query /TN "DiaryApp_DailyRestart"
echo.

endlocal
exit /b 0

