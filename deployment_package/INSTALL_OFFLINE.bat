@echo off
REM ========================================
REM Install Python Packages from Offline Cache
REM Use this after downloading packages with
REM DOWNLOAD_PACKAGES_FOR_OFFLINE.bat
REM ========================================

echo.
echo ========================================
echo  OFFLINE PACKAGE INSTALLER
echo ========================================
echo.

REM Check if packages folder exists
if not exist "packages" (
    echo ERROR: packages folder not found!
    echo.
    echo Please:
    echo  1. Run DOWNLOAD_PACKAGES_FOR_OFFLINE.bat on a machine with internet
    echo  2. Copy the "packages" folder to this directory
    echo  3. Run this script again
    echo.
    pause
    exit /b 1
)

echo Found packages folder
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    echo Please install Python first (see INSTALLATION_LINKS.txt)
    pause
    exit /b 1
)

echo Python found!
echo.

REM Install packages from local cache
echo Installing packages from offline cache...
echo.

python -m pip install --no-index --find-links=packages -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    echo Trying alternative method...
    echo.
    
    REM Try upgrading pip first
    python -m pip install --no-index --find-links=packages --upgrade pip
    
    REM Try again
    python -m pip install --no-index --find-links=packages -r requirements.txt
)

echo.
echo ========================================
echo  INSTALLATION COMPLETE
echo ========================================
echo.
echo All packages installed successfully!
echo.
echo You can now start the application by:
echo  1. Double-clicking START_DIARY.bat
echo  2. Or running: python app.py
echo.

pause

