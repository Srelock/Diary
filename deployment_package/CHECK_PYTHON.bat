@echo off
REM ========================================
REM Python Installation Checker
REM Quick diagnostic tool
REM ========================================

echo.
echo ========================================
echo  PYTHON INSTALLATION CHECKER
echo ========================================
echo.

REM Check Python
echo Checking Python installation...
python --version 2>nul
if errorlevel 1 (
    echo [FAIL] Python is NOT installed or not in PATH
    echo.
    echo SOLUTION:
    echo 1. Download Python from: https://www.python.org/downloads/
    echo 2. During installation, CHECK "Add Python to PATH"
    echo 3. Restart computer after installation
    echo 4. Run this script again
    echo.
    goto :end
) else (
    echo [OK] Python is installed
)

echo.

REM Check pip
echo Checking pip installation...
python -m pip --version 2>nul
if errorlevel 1 (
    echo [FAIL] pip is NOT installed
    echo.
    echo SOLUTION:
    echo Run: python -m ensurepip --default-pip
    echo.
    goto :end
) else (
    echo [OK] pip is installed
)

echo.

REM Check installed packages
echo Checking required packages...
echo.

python -c "import flask" 2>nul
if errorlevel 1 (
    echo [MISSING] Flask
) else (
    echo [OK] Flask
)

python -c "import flask_sqlalchemy" 2>nul
if errorlevel 1 (
    echo [MISSING] Flask-SQLAlchemy
) else (
    echo [OK] Flask-SQLAlchemy
)

python -c "import apscheduler" 2>nul
if errorlevel 1 (
    echo [MISSING] APScheduler
) else (
    echo [OK] APScheduler
)

python -c "import reportlab" 2>nul
if errorlevel 1 (
    echo [MISSING] ReportLab
) else (
    echo [OK] ReportLab
)

python -c "import win32api" 2>nul
if errorlevel 1 (
    echo [MISSING] pywin32
) else (
    echo [OK] pywin32
)

echo.
echo ========================================
echo  SYSTEM INFORMATION
echo ========================================
echo.
echo Python version:
python --version

echo.
echo Pip version:
python -m pip --version

echo.
echo Python location:
where python

echo.
echo ========================================
echo.
echo If packages are missing, run SETUP_APPLICATION.bat
echo.

:end
pause

