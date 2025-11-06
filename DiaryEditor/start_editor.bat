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
echo http://127.0.0.1:5001
echo.
echo Press Ctrl+C to stop the editor
echo ========================================
echo.

REM Activate virtual environment if it exists in parent Diary folder
if exist "..\Diary\venv\Scripts\activate.bat" (
    call ..\Diary\venv\Scripts\activate.bat
)

REM Start the editor app
python editor_app.py

pause

