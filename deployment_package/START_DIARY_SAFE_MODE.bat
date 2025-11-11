@echo off
REM ========================================
REM Diary Application - Safe Mode Startup
REM For weak machines with limited resources
REM ========================================

echo.
echo ========================================
echo  DIARY APPLICATION - SAFE MODE
echo ========================================
echo.
echo Safe Mode optimizations:
echo  - Reduced memory usage
echo  - Disabled auto-browser open
echo  - Single-threaded mode
echo  - Debug mode OFF
echo.
echo Starting application...
echo.
echo The application will be available at:
echo  http://localhost:5000
echo.
echo Press Ctrl+C to stop the application
echo.

REM Set environment variables for low-resource mode
set FLASK_ENV=production
set PYTHONOPTIMIZE=1

REM Start with minimal settings
python app.py --host=127.0.0.1 --port=5000

pause

