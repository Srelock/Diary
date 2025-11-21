# Quick Start - Building the Installer

This is a quick reference guide for building the standalone installer.

## Prerequisites Check

✅ Python 3.8+ installed and in PATH
✅ Administrator rights
✅ ~500 MB free disk space

## Build in 3 Steps

### 1. Build Executables (10-15 minutes)

```cmd
build_all.bat
```

**Output**: 
- `dist\diary_app.exe` (Main App)
- `DiaryEditor\dist\diary_editor.exe` (Database Editor)

### 2. Install Inno Setup (One-time, 2 minutes)

Download and install from: https://jrsoftware.org/isdl.php

### 3. Build Installer (2 minutes)

1. Open **Inno Setup Compiler**
2. File → Open → `installer.iss`
3. Build → Compile (Ctrl+F9)

**Output**: `installer_output\DiaryApp_Setup.exe`

## Test

Run the installer:
```cmd
installer_output\DiaryApp_Setup.exe
```

## What You Get

✅ Standalone .exe files (no Python needed)
✅ Main App + Database Editor (both standalone)
✅ Professional installer/uninstaller
✅ Auto-starts on Windows boot
✅ Daily restart at 01:00 AM
✅ Task Scheduler integration
✅ Desktop & Start Menu shortcuts

## Quick Test

Test the executables before building installer:
```cmd
# Main App - Normal mode (opens browser)
dist\diary_app.exe

# Main App - Service mode (no browser)
dist\diary_app.exe --no-browser

# Database Editor
DiaryEditor\dist\diary_editor.exe
```

## Files Created

```
build_all.bat                        # Build all executables
build_exe.bat                        # Build main app only
diary_app.spec                       # PyInstaller config (main app)
DiaryEditor/build_editor_exe.bat     # Build editor only
DiaryEditor/editor_app.spec          # PyInstaller config (editor)
installer.iss                        # Inno Setup installer script
install_tasks.bat                    # Task Scheduler setup
uninstall_tasks.bat                  # Task Scheduler cleanup  
restart_service.bat                  # Daily restart script
BUILD_INSTRUCTIONS.md                # Full documentation
```

## Need Help?

See **BUILD_INSTRUCTIONS.md** for detailed guide, troubleshooting, and all options.

