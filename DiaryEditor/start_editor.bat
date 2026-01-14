@echo off
title Diary Report Editor
color 0B

echo ========================================
echo   DIARY REPORT EDITOR
echo ========================================
echo.
echo Starting editor server on port 5001...
echo.
echo Once started, editor will open in your browser:
echo Local access:   http://127.0.0.1:5001
echo.
echo Other PCs on the network can connect using:
echo Network access: http://%COMPUTERNAME%:5001
echo.
echo Press Ctrl+C to stop the editor
echo ========================================
echo.

REM Check if standalone exe exists (installed version)
if exist "diary_editor.exe" (
    echo Running standalone executable...
    diary_editor.exe
) else if exist "dist\diary_editor.exe" (
    echo Running standalone executable...
    dist\diary_editor.exe
) else (
    echo Running Python script...
    REM Activate virtual environment if it exists in parent Diary folder
    if exist "..\Diary\venv\Scripts\activate.bat" (
        call ..\Diary\venv\Scripts\activate.bat
    )
    python editor_app.py
)

pause

