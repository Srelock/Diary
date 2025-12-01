@echo off
title Building Management Diary (Developer Test Mode)
color 0B

echo ========================================
echo   BUILDING MANAGEMENT DIARY
echo   (Developer Test Mode - Port 5001)
echo ========================================
echo.
echo Starting application server on port 5001...
echo.
echo Once started, the application will open in your browser:
echo http://127.0.0.1:5001
echo.
echo Press Ctrl+C to stop the application
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Set development port to 5001
set PORT=5001

REM Run Python script directly (uses updated templates)
python app.py

pause

