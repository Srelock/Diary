@echo off
echo Stopping Diary applications...
echo.

REM Find and kill diary_app.exe
tasklist | findstr /I "diary_app.exe" >nul
if %ERRORLEVEL% == 0 (
    echo Found diary_app.exe, stopping...
    taskkill /F /IM diary_app.exe
    echo Stopped diary_app.exe
) else (
    echo diary_app.exe not running
)

REM Find and kill Python processes that might be running the apps
echo.
echo Checking for Python processes on ports 5000 and 5001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000"') do (
    echo Stopping process %%a on port 5000...
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001"') do (
    echo Stopping process %%a on port 5001...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Done!
timeout /t 2 >nul

