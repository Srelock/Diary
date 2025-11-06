@echo off
REM ========================================
REM Restart Diary App Service
REM ========================================
REM This script is called by Windows Task Scheduler
REM to restart the application daily at 01:00 AM

setlocal

REM Determine installation directory
set "INSTALL_DIR=%~dp0"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

set "EXE_PATH=%INSTALL_DIR%\diary_app.exe"
set "LOG_FILE=%INSTALL_DIR%\logs\restart_log.txt"

REM Create logs directory if it doesn't exist
if not exist "%INSTALL_DIR%\logs" mkdir "%INSTALL_DIR%\logs"

REM Log restart attempt
echo [%date% %time%] Restart script executed >> "%LOG_FILE%"

REM Stop all running instances
echo [%date% %time%] Stopping existing instances... >> "%LOG_FILE%"
taskkill /IM diary_app.exe /F >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] No running instances found >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Stopped running instances >> "%LOG_FILE%"
)

REM Wait for processes to fully terminate
timeout /t 3 /nobreak >nul

REM Start the application in service mode (no browser)
echo [%date% %time%] Starting application... >> "%LOG_FILE%"
start "Diary App Service" /MIN "%EXE_PATH%" --no-browser

REM Wait a moment to verify startup
timeout /t 5 /nobreak >nul

REM Check if app is running
tasklist /FI "IMAGENAME eq diary_app.exe" | findstr /C:"diary_app.exe" >nul
if errorlevel 1 (
    echo [%date% %time%] ERROR: Application failed to start >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Application restarted successfully >> "%LOG_FILE%"
)

endlocal
exit /b 0

