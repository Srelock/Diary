@echo off
REM ========================================
REM Build Standalone Executable for Diary App
REM ========================================
REM This script builds a standalone .exe using PyInstaller

setlocal

echo.
echo ========================================
echo Building Diary App Standalone Executable
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo [1/5] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
) else (
    echo PyInstaller is already installed
)

echo.
echo [2/5] Cleaning previous builds...
if exist "build" (
    rmdir /s /q "build"
    echo Removed build directory
)
if exist "dist" (
    rmdir /s /q "dist"
    echo Removed dist directory
)

echo.
echo [3/5] Installing/checking dependencies...
pip install -r docs\requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo Continuing anyway...
)

echo.
echo [4/5] Building executable with PyInstaller...
echo This may take several minutes...
pyinstaller diary_app.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Check the output above for errors
    pause
    exit /b 1
)

echo.
echo [5/5] Verifying build...
if exist "dist\diary_app.exe" (
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Executable location: dist\diary_app.exe
    echo Size: 
    dir "dist\diary_app.exe" | findstr "diary_app.exe"
    echo.
    echo Next steps:
    echo 1. Test the executable: dist\diary_app.exe
    echo 2. Build installer using Inno Setup with installer.iss
    echo.
) else (
    echo.
    echo ERROR: Build completed but executable not found!
    echo Expected location: dist\diary_app.exe
    pause
    exit /b 1
)

endlocal
pause

