# Quick Start - Building the Installer

This is a quick reference guide for building the standalone installer.

## Prerequisites Check

✅ Python 3.8+ installed and in PATH
✅ Administrator rights
✅ ~500 MB free disk space

## Build in 3 Steps

### 1. Build Executable (5-10 minutes)

```cmd
build_exe.bat
```

**Output**: `dist\diary_app.exe`

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

✅ Standalone .exe (no Python needed)
✅ Professional installer/uninstaller
✅ Auto-starts on Windows boot
✅ Daily restart at 01:00 AM
✅ Task Scheduler integration
✅ Desktop & Start Menu shortcuts

## Quick Test

Test the exe before building installer:
```cmd
# Normal mode (opens browser)
dist\diary_app.exe

# Service mode (no browser)
dist\diary_app.exe --no-browser
```

## Files Created

```
build_exe.bat              # Build executable script
diary_app.spec            # PyInstaller configuration
installer.iss             # Inno Setup installer script
install_tasks.bat         # Task Scheduler setup
uninstall_tasks.bat       # Task Scheduler cleanup  
restart_service.bat       # Daily restart script
BUILD_INSTRUCTIONS.md     # Full documentation
```

## Need Help?

See **BUILD_INSTRUCTIONS.md** for detailed guide, troubleshooting, and all options.

