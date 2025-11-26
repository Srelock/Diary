@echo off
REM ========================================
REM Build Standalone Executable for Diary Editor
REM ========================================

setlocal

echo.
echo ========================================
echo Building Diary Editor Standalone Executable
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

echo [1/4] Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install --no-warn-script-location pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
) else (
    echo PyInstaller is already installed
)

echo.
echo [2/4] Cleaning previous builds...
if exist "build" (
    rmdir /s /q "build"
    echo Removed build directory
)
if exist "dist" (
    rmdir /s /q "dist"
    echo Removed dist directory
)

echo.
echo [3/4] Installing/checking dependencies...
pip install --no-warn-script-location Flask Flask-SQLAlchemy reportlab Pillow
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo Continuing anyway...
)

echo.
echo [4/5] Generating version information...
cd ..
python generate_version.py
cd DiaryEditor
if errorlevel 1 (
    echo WARNING: Version generation failed, using default version
)

echo.
echo [5/5] Building executable with PyInstaller...
echo This may take several minutes...
python -m PyInstaller editor_app.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Check the output above for errors
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Executable location: dist\diary_editor.exe
echo Size: 
dir "dist\diary_editor.exe" | findstr "diary_editor.exe"
echo.
echo Test the editor:
echo   dist\diary_editor.exe
echo.

endlocal
pause

