@echo off
echo Stopping Diary applications...
echo.

REM Find and kill diary_app.exe processes
tasklist | findstr /I "diary_app.exe" >nul
if %ERRORLEVEL% == 0 (
    echo Stopping diary_app.exe processes...
    taskkill /F /IM diary_app.exe
    timeout /t 2 >nul
)

echo.
echo Starting Diary in Development Mode (Python script)...
echo This will use the updated templates with the Maintenance tab!
echo.

call start_diary_dev.bat

