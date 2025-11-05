@echo off
REM ========================================
REM Restart Building Management Diary App
REM ========================================
REM This script stops any running instance and starts a new one
REM Designed for use with Windows Task Scheduler

setlocal

REM Get the parent directory (project root)
set "PROJECT_DIR=%~dp0.."
set "APP_PATH=%PROJECT_DIR%\app.py"
set "LOG_FILE=%PROJECT_DIR%\scheduler\restart_log.txt"

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Log restart attempt
echo [%date% %time%] Restart script executed >> "%LOG_FILE%"

REM Find and stop any running Python processes for app.py
echo Stopping existing app instances...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /C:"PID:"') do (
    set PID=%%a
    for /f "usebackq tokens=*" %%b in (`wmic process where "ProcessId=%%a" get CommandLine /value ^| findstr /C:"app.py"`) do (
        echo Stopping process PID: %%a
        taskkill /PID %%a /F >nul 2>&1
        echo [%date% %time%] Stopped process PID: %%a >> "%LOG_FILE%"
    )
)

REM Wait a moment for processes to fully terminate
timeout /t 2 /nobreak >nul

REM Start the app
echo Starting application...
echo [%date% %time%] Starting new app instance >> "%LOG_FILE%"
start "Building Management Diary" /MIN python "%APP_PATH%"

REM Wait a moment to verify startup
timeout /t 3 /nobreak >nul

REM Check if app is running
tasklist /FI "IMAGENAME eq python.exe" | findstr /C:"python.exe" >nul
if %errorlevel% equ 0 (
    echo [%date% %time%] App restart completed successfully >> "%LOG_FILE%"
    echo Restart completed successfully!
) else (
    echo [%date% %time%] ERROR: App may not have started correctly >> "%LOG_FILE%"
    echo WARNING: App may not have started correctly
)

endlocal

