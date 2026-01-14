@echo off
title Building Management Diary (Development Mode)
color 0B

echo ========================================
echo   BUILDING MANAGEMENT DIARY
echo   (Development Mode - Python Script)
echo ========================================
echo.
echo Starting application server on port 5000...
echo.
echo Once started, the application will open in your browser:
echo Local access:   http://127.0.0.1:5000
echo.
echo Other PCs on the network can connect using:
echo Network access: http://%COMPUTERNAME%:5000
echo.
echo Press Ctrl+C to stop the application
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run Python script directly (uses updated templates)
python app.py

pause

