@echo off
REM ========================================
REM Download Python Packages for Offline Installation
REM Run this on a machine WITH internet to prepare
REM packages for offline installation on new machine
REM ========================================

echo.
echo ========================================
echo  OFFLINE PACKAGE DOWNLOADER
echo ========================================
echo.
echo This script will download all required Python
echo packages so you can install them on a machine
echo without internet connection.
echo.
echo The packages will be saved to: packages\
echo Total download size: ~50-70 MB
echo.

REM Check if Python and pip are available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    echo Please install Python first
    pause
    exit /b 1
)

echo Python found!
echo.

REM Create packages directory
if not exist "packages" mkdir packages
echo Created packages directory
echo.

REM Download all packages
echo Downloading packages...
echo This may take 2-5 minutes depending on your internet speed...
echo.

python -m pip download -r requirements.txt -d packages

if errorlevel 1 (
    echo.
    echo ERROR: Download failed
    echo Please check your internet connection
    pause
    exit /b 1
)

echo.
echo ========================================
echo  DOWNLOAD COMPLETE
echo ========================================
echo.
echo All packages have been downloaded to: packages\
echo.
echo To install on offline machine:
echo  1. Copy the entire "packages" folder to the new machine
echo  2. Copy requirements.txt to the new machine
echo  3. Run: pip install --no-index --find-links=packages -r requirements.txt
echo.
echo Or use the INSTALL_OFFLINE.bat script
echo.

pause

