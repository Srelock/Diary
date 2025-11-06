@echo off
REM ========================================
REM Build All Standalone Executables
REM Main App + DiaryEditor
REM ========================================

setlocal

echo.
echo ========================================
echo Building All Diary App Executables
echo ========================================
echo.

REM Build main diary app
echo [STEP 1/2] Building Main Diary App...
echo ========================================
call build_exe.bat
if errorlevel 1 (
    echo.
    echo ERROR: Main app build failed!
    pause
    exit /b 1
)

echo.
echo.
echo [STEP 2/2] Building Diary Editor...
echo ========================================
cd DiaryEditor
call build_editor_exe.bat
if errorlevel 1 (
    echo.
    echo ERROR: Editor build failed!
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo.
echo ========================================
echo ALL BUILDS SUCCESSFUL!
echo ========================================
echo.
echo Built executables:
echo 1. Main App:  dist\diary_app.exe
echo 2. Editor:    DiaryEditor\dist\diary_editor.exe
echo.
echo Next step:
echo - Compile installer.iss with Inno Setup to create installer
echo.

endlocal
pause

