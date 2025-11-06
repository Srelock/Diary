@echo off
REM ========================================
REM Uninstall Windows Task Scheduler Tasks
REM For Diary App
REM ========================================
REM This script removes scheduled tasks and stops the application

setlocal

echo Uninstalling Diary App scheduled tasks...

REM Stop all running instances of diary_app.exe
echo.
echo Stopping all running instances...
taskkill /IM diary_app.exe /F >nul 2>&1
if errorlevel 1 (
    echo No running instances found
) else (
    echo Application stopped
    timeout /t 2 /nobreak >nul
)

REM Delete scheduled tasks
echo.
echo Removing scheduled tasks...

schtasks /Delete /TN "DiaryApp_Startup" /F >nul 2>&1
if errorlevel 1 (
    echo Task "DiaryApp_Startup" not found or already removed
) else (
    echo Removed task: DiaryApp_Startup
)

schtasks /Delete /TN "DiaryApp_DailyRestart" /F >nul 2>&1
if errorlevel 1 (
    echo Task "DiaryApp_DailyRestart" not found or already removed
) else (
    echo Removed task: DiaryApp_DailyRestart
)

echo.
echo ========================================
echo Task uninstallation completed!
echo ========================================

endlocal
exit /b 0

