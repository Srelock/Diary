@echo off
REM ========================================
REM Diary Application - Automated Setup
REM For New Machine Deployment
REM ========================================

echo.
echo ========================================
echo  DIARY APPLICATION SETUP
echo ========================================
echo.
echo This script will:
echo  1. Check Python installation
echo  2. Install required packages
echo  3. Verify database setup
echo  4. Test application startup
echo.
echo Please wait...
echo.

REM Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python first:
    echo  1. Download: https://www.python.org/downloads/
    echo  2. Run installer and CHECK "Add Python to PATH"
    echo  3. Restart this script
    echo.
    pause
    exit /b 1
)

python --version
echo Python found!
echo.

REM Check if pip is installed
echo [2/5] Checking pip installation...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: pip is not installed
    echo Installing pip...
    python -m ensurepip --default-pip
    echo.
)

python -m pip --version
echo pip found!
echo.

REM Upgrade pip to latest version
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo pip upgraded!
echo.

REM Install required packages
echo [4/5] Installing required packages...
echo This may take 3-5 minutes on slower machines...
echo.

REM For weak machines, install with no cache to save memory
python -m pip install --no-cache-dir -r requirements.txt

if errorlevel 1 (
    echo.
    echo WARNING: Some packages failed to install
    echo Trying alternative installation method...
    echo.
    
    REM Try installing packages one by one
    python -m pip install Flask==2.3.3
    python -m pip install Werkzeug==2.3.7
    python -m pip install Flask-SQLAlchemy==3.0.5
    python -m pip install SQLAlchemy>=2.0.21
    python -m pip install APScheduler==3.10.4
    python -m pip install reportlab==4.0.4
    python -m pip install email-validator==2.0.0
    python -m pip install python-dateutil==2.8.2
    python -m pip install pywin32>=306
    
    if errorlevel 1 (
        echo.
        echo ERROR: Installation failed
        echo Please check your internet connection and try again
        echo Or install packages manually (see README_SETUP.md)
        echo.
        pause
        exit /b 1
    )
)

echo.
echo All packages installed successfully!
echo.

REM Create necessary directories if they don't exist
echo [5/5] Setting up directories...
if not exist "instance" mkdir instance
if not exist "logs" mkdir logs
if not exist "reports" mkdir reports
if not exist "reports\PDF" mkdir reports\PDF
if not exist "reports\CSV" mkdir reports\CSV
echo Directories created!
echo.

REM Verify installation
echo ========================================
echo  INSTALLATION COMPLETE
echo ========================================
echo.
echo Installed packages:
python -m pip list | findstr "Flask SQLAlchemy APScheduler reportlab email-validator python-dateutil pywin32"
echo.

echo ========================================
echo  SETUP SUCCESSFUL
echo ========================================
echo.
echo You can now start the application by:
echo  1. Double-clicking "START_DIARY.bat"
echo  2. Or running: python app.py
echo.
echo The application will be available at:
echo  http://localhost:5000
echo.
echo For more information, see README_SETUP.md
echo.

pause

