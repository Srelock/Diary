@echo off
REM ========================================
REM Interactive Setup Wizard
REM Guides you through the entire installation
REM ========================================

:menu
cls
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║           DIARY APPLICATION - SETUP WIZARD                     ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Please select an option:
echo.
echo  1. Check if Python is installed
echo  2. Install application (automatic)
echo  3. Install application (minimal - for weak machines)
echo  4. Install from offline packages
echo  5. Download packages for offline installation
echo  6. Start application (normal mode)
echo  7. Start application (safe mode - for weak machines)
echo  8. View installation guides
echo  9. Exit
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto check_python
if "%choice%"=="2" goto install_auto
if "%choice%"=="3" goto install_minimal
if "%choice%"=="4" goto install_offline
if "%choice%"=="5" goto download_packages
if "%choice%"=="6" goto start_normal
if "%choice%"=="7" goto start_safe
if "%choice%"=="8" goto view_guides
if "%choice%"=="9" goto exit

echo.
echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

REM ========================================
:check_python
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  CHECKING PYTHON INSTALLATION
echo ═══════════════════════════════════════════════════════════════
echo.
call CHECK_PYTHON.bat
echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:install_auto
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  AUTOMATIC INSTALLATION (FULL)
echo ═══════════════════════════════════════════════════════════════
echo.
echo This will install all required packages.
echo Internet connection required.
echo Estimated time: 3-5 minutes
echo.
set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" goto menu

call SETUP_APPLICATION.bat
echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:install_minimal
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  MINIMAL INSTALLATION (FOR WEAK MACHINES)
echo ═══════════════════════════════════════════════════════════════
echo.
echo This will install only essential packages.
echo Internet connection required.
echo Estimated time: 2-3 minutes
echo.
set /p confirm="Continue? (Y/N): "
if /i not "%confirm%"=="Y" goto menu

echo.
echo Installing minimal packages...
python -m pip install --no-cache-dir -r requirements_minimal.txt

if errorlevel 1 (
    echo.
    echo Installation failed. Please check errors above.
) else (
    echo.
    echo Minimal installation complete!
    echo.
    echo Note: Some features may be limited:
    echo  - Auto-scheduled reports disabled
    echo  - PDF printing may not work
    echo.
    echo You can install additional packages later if needed.
)

echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:install_offline
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  OFFLINE INSTALLATION
echo ═══════════════════════════════════════════════════════════════
echo.
call INSTALL_OFFLINE.bat
echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:download_packages
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  DOWNLOAD PACKAGES FOR OFFLINE INSTALLATION
echo ═══════════════════════════════════════════════════════════════
echo.
call DOWNLOAD_PACKAGES_FOR_OFFLINE.bat
echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:start_normal
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  STARTING APPLICATION (NORMAL MODE)
echo ═══════════════════════════════════════════════════════════════
echo.
echo Checking if application files exist...

if not exist "app.py" (
    echo.
    echo ERROR: app.py not found!
    echo.
    echo This wizard must be run from the Diary application folder.
    echo Please copy all application files to this directory.
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto menu
)

echo Application files found!
echo.
echo Starting application...
echo.
call START_DIARY.bat
goto menu

REM ========================================
:start_safe
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  STARTING APPLICATION (SAFE MODE)
echo ═══════════════════════════════════════════════════════════════
echo.
echo Checking if application files exist...

if not exist "app.py" (
    echo.
    echo ERROR: app.py not found!
    echo.
    echo This wizard must be run from the Diary application folder.
    echo Please copy all application files to this directory.
    echo.
    echo Press any key to return to menu...
    pause >nul
    goto menu
)

echo Application files found!
echo.
echo Starting application in Safe Mode...
echo.
call START_DIARY_SAFE_MODE.bat
goto menu

REM ========================================
:view_guides
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  INSTALLATION GUIDES
echo ═══════════════════════════════════════════════════════════════
echo.
echo Available documentation:
echo.
echo  1. START_HERE.txt - Overview and quick start
echo  2. QUICK_START_GUIDE.txt - 3-step quick installation
echo  3. README_SETUP.md - Complete detailed guide
echo  4. DEPLOYMENT_CHECKLIST.txt - Step-by-step checklist
echo  5. INSTALLATION_LINKS.txt - Python download links
echo  6. Return to main menu
echo.

set /p guide="Which guide would you like to open? (1-6): "

if "%guide%"=="1" start notepad START_HERE.txt
if "%guide%"=="2" start notepad QUICK_START_GUIDE.txt
if "%guide%"=="3" start notepad README_SETUP.md
if "%guide%"=="4" start notepad DEPLOYMENT_CHECKLIST.txt
if "%guide%"=="5" start notepad INSTALLATION_LINKS.txt
if "%guide%"=="6" goto menu

echo.
echo Press any key to return to menu...
pause >nul
goto menu

REM ========================================
:exit
cls
echo.
echo ═══════════════════════════════════════════════════════════════
echo  Thank you for using the Diary Application Setup Wizard!
echo ═══════════════════════════════════════════════════════════════
echo.
echo For help and documentation:
echo  - READ: START_HERE.txt
echo  - READ: README_SETUP.md
echo.
echo To start the application:
echo  - RUN: START_DIARY.bat
echo.
echo Good luck! 
echo.

timeout /t 3 >nul
exit /b 0

