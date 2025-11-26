@echo off
title Building Management Diary
color 0B

echo ========================================
echo   BUILDING MANAGEMENT DIARY
echo ========================================
echo.
echo Starting application server on port 5000...
echo.
echo Once started, the application will open in your browser:
echo http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the application
echo ========================================
echo.

REM Check if standalone exe exists (installed version)
if exist "diary_app.exe" (
    echo Running standalone executable...
    diary_app.exe
) else if exist "dist\diary_app.exe" (
    echo Running standalone executable...
    dist\diary_app.exe
) else (
    echo Running Python script...
    REM Activate virtual environment if it exists
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
    )
    python app.py
)

pause

