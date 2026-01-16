# Building Standalone Executable and Installer

This guide explains how to build a standalone executable and professional installer for the Building Management Diary application.

## Prerequisites

### Required Software

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - Ensure Python is added to PATH during installation

2. **Inno Setup 6.x**
   - Download from: https://jrsoftware.org/isdl.php
   - Install with default options
   - Note the installation path (typically `C:\Program Files (x86)\Inno Setup 6`)

3. **All Python Dependencies**
   - Will be installed automatically by build script
   - See `docs/requirements.txt` for full list

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Disk Space**: ~500 MB free space for build process
- **RAM**: 4 GB minimum
- **Administrator Rights**: Required for Task Scheduler configuration

## Build Process

### Step 1: Prepare the Project

1. Ensure all code changes are committed to git
2. Update version number in `installer.iss` if needed:
   ```
   #define MyAppVersion "1.0.0"
   ```

### Step 2: Build the Executables

**Option A: Build All (Recommended)**

1. Open Command Prompt or PowerShell
2. Navigate to project directory:
   ```cmd
   cd C:\Users\YourName\Desktop\project\Diary
   ```

3. Run the master build script:
   ```cmd
   build_all.bat
   ```
   This builds both the main app and editor (takes 10-15 minutes)

**Option B: Build Individually**

Build main app only:
```cmd
build_exe.bat
```

Build editor only:
```cmd
cd DiaryEditor
build_editor_exe.bat
cd ..
```

**Expected Output**:
```
Built executables:
1. Main App:  dist\diary_app.exe (~100-150 MB)
2. Editor:    DiaryEditor\dist\diary_editor.exe (~80-120 MB)
```

### Step 3: Test the Executable (Optional but Recommended)

1. Run the executable directly:
   ```cmd
   dist\diary_app.exe
   ```
   - Browser should open automatically
   - App should be accessible at http://localhost:5050
   - Press Ctrl+C to stop

2. Test service mode (no browser):
   ```cmd
   dist\diary_app.exe --no-browser
   ```
   - No browser should open
   - App still accessible at http://localhost:5050

### Step 4: Build the Installer

1. Open Inno Setup Compiler
   - Start Menu → Inno Setup → Inno Setup Compiler

2. Open the installer script:
   - File → Open → Select `installer.iss`

3. Compile the installer:
   - Build → Compile (or press Ctrl+F9)

4. Wait for compilation to complete (1-2 minutes)

5. **Output Location**:
   ```
   installer_output\DiaryApp_Setup.exe
   ```

### Step 5: Test the Installer (Recommended)

1. **Important**: Test on a clean system or VM if possible

2. Run the installer:
   ```cmd
   installer_output\DiaryApp_Setup.exe
   ```

3. Follow installation wizard:
   - Accept default installation path or choose custom
   - Select if you want desktop icon
   - Complete installation

4. **Verify Installation**:
   - App should start automatically after installation
   - Check Task Scheduler has two tasks created:
     - `DiaryApp_Startup`
     - `DiaryApp_DailyRestart`

5. **Test Scheduled Tasks**:
   - Restart computer to test startup task
   - Or manually run: `schtasks /Run /TN "DiaryApp_Startup"`

## Files Created

### Build Files
- `dist\diary_app.exe` - Standalone executable (~100-150 MB)
- `build\` - Temporary build files (can be deleted)

### Installer Files
- `installer_output\DiaryApp_Setup.exe` - Professional installer (~100-150 MB)

### Support Files (Bundled in Installer)
- `install_tasks.bat` - Creates scheduled tasks
- `uninstall_tasks.bat` - Removes scheduled tasks
- `restart_service.bat` - Daily restart script
- `config.example.py` - Example configuration

## Installation Details

### Default Installation Path
```
C:\Program Files\DiaryApp\
```

### Directory Structure After Installation
```
C:\Program Files\DiaryApp\
├── diary_app.exe          # Main executable
├── config.py              # User configuration (created from example)
├── config.example.py      # Example configuration
├── install_tasks.bat      # Task setup script
├── uninstall_tasks.bat    # Task cleanup script
├── restart_service.bat    # Daily restart script
├── DiaryEditor\           # Database editor tool
│   ├── editor_app.py     # Editor application
│   ├── start_editor.bat  # Editor launcher
│   ├── README.md         # Editor documentation
│   └── templates\        # Editor HTML templates
│       └── editor.html
├── instance\              # Database directory
│   └── diary.db          # SQLite database (created on first run)
├── logs\                  # Log files
│   ├── restart_log.txt   # Restart history
│   └── settings_access.log
└── reports\               # Generated reports
    ├── PDF\              # PDF reports
    └── CSV\              # CSV reports
```

### Scheduled Tasks Created

1. **DiaryApp_Startup**
   - **Trigger**: System startup
   - **Action**: Start `diary_app.exe --no-browser`
   - **Privileges**: Highest (Administrator)
   - **Purpose**: Auto-start on Windows boot

2. **DiaryApp_DailyRestart**
   - **Trigger**: Daily at 01:00 AM
   - **Action**: Run `restart_service.bat`
   - **Privileges**: Highest (Administrator)
   - **Purpose**: Daily restart for optimal performance

## Configuration

### Email Settings

After installation, configure email settings:

1. **Option 1: Using Web Interface** (Recommended)
   - Open app: http://localhost:5050
   - Navigate to Settings tab
   - Configure email credentials and recipients

2. **Option 2: Edit Config File**
   - Edit: `C:\Program Files\DiaryApp\config.py`
   - Update email credentials
   - Restart app for changes to take effect

### Modifying Restart Time

To change daily restart time from 01:00 AM:

1. Open Task Scheduler
2. Find task: `DiaryApp_DailyRestart`
3. Right-click → Properties
4. Triggers tab → Edit
5. Change start time
6. Click OK

### Using the Database Editor

The DiaryEditor tool allows you to edit past diary occurrences:

1. **Launch the Editor**
   - Start Menu → Building Management Diary → Database Editor
   - Or run: `C:\Program Files\DiaryApp\DiaryEditor\start_editor.bat`

2. **What You Can Do**
   - View occurrences from any past date
   - Edit existing occurrence details
   - Add missed occurrences to past dates
   - Delete incorrect occurrences

3. **Important Notes**
   - Runs on port 5001 (http://127.0.0.1:5001)
   - Can run simultaneously with main app
   - No authentication required (for authorized staff only)
   - Changes are permanent - no undo function
   - See `DiaryEditor\README.md` for full documentation

## Troubleshooting

### Build Issues

**Problem**: PyInstaller fails with "Module not found"
- **Solution**: Ensure all dependencies installed: `pip install -r docs\requirements.txt`

**Problem**: Build successful but exe doesn't run
- **Solution**: Check for antivirus blocking the executable

**Problem**: Exe size is very large (>200 MB)
- **Solution**: Normal for standalone exe with all dependencies

### Installation Issues

**Problem**: "User Account Control" blocks installation
- **Solution**: Right-click installer → Run as Administrator

**Problem**: Scheduled tasks not created
- **Solution**: 
  - Check Task Scheduler: `taskschd.msc`
  - Manually run: `C:\Program Files\DiaryApp\install_tasks.bat`

**Problem**: App doesn't start on boot
- **Solution**:
  - Check task exists: `schtasks /Query /TN "DiaryApp_Startup"`
  - Verify task is enabled in Task Scheduler

### Runtime Issues

**Problem**: App won't start
- **Solution**: Check logs in `C:\Program Files\DiaryApp\logs\`

**Problem**: Database errors
- **Solution**: Check `C:\Program Files\DiaryApp\instance\diary.db` has write permissions

**Problem**: Port 5050 already in use
- **Solution**: Stop other applications using port 5050

## Uninstallation

### Using Control Panel
1. Settings → Apps → Apps & features
2. Find "Building Management Diary"
3. Click Uninstall
4. Follow wizard

### Manual Cleanup (if needed)
```cmd
REM Stop application
taskkill /IM diary_app.exe /F

REM Remove scheduled tasks
schtasks /Delete /TN "DiaryApp_Startup" /F
schtasks /Delete /TN "DiaryApp_DailyRestart" /F

REM Delete installation directory
rmdir /s /q "C:\Program Files\DiaryApp"
```

## Distribution

### Distributing the Installer

The installer `DiaryApp_Setup.exe` is completely standalone:
- No Python installation required on target system
- All dependencies included
- Can be distributed via:
  - USB drive
  - Network share
  - Download link
  - Email (if size permits)

### System Requirements for End Users

- Windows 10/11 (64-bit)
- 200 MB disk space
- Administrator rights (for installation only)
- Internet connection (for email features)

## Updates and Maintenance

### Creating an Update

1. Make code changes in `app.py`
2. Increment version in `installer.iss`
3. Rebuild exe: `build_exe.bat`
4. Rebuild installer with Inno Setup
5. Distribute new installer

### Updating Existing Installation

Users can:
1. Run new installer over existing installation
2. Choose "Yes" to upgrade
3. Database and config preserved automatically

## Support and Logs

### Log Files

Check these logs for troubleshooting:
- `C:\Program Files\DiaryApp\logs\restart_log.txt` - Restart history
- `C:\Program Files\DiaryApp\logs\settings_access.log` - Settings changes
- `C:\Program Files\DiaryApp\logs\shutdown_log.txt` - Shutdown events

### Viewing Task Scheduler Logs

1. Open Task Scheduler: `taskschd.msc`
2. Find task → Properties → History tab
3. Review execution history

## Additional Notes

### Security Considerations

- App runs with highest privileges (required for Task Scheduler)
- Database stored in Program Files (requires admin for direct access)
- Logs directory has full user permissions for troubleshooting

### Performance

- Exe size: ~100-150 MB (includes Python runtime and all libraries)
- First startup: ~5-10 seconds
- Subsequent startups: ~3-5 seconds
- Memory usage: ~100-150 MB

### Customization

To add custom icon:
1. Create/obtain `.ico` file
2. Update `installer.iss`: `SetupIconFile=path\to\icon.ico`
3. Update `diary_app.spec`: `icon='path\to\icon.ico'`
4. Rebuild

## Quick Reference Commands

```cmd
REM Build executable
build_exe.bat

REM Test executable
dist\diary_app.exe

REM Test service mode
dist\diary_app.exe --no-browser

REM View scheduled tasks
schtasks /Query /TN "DiaryApp_Startup"
schtasks /Query /TN "DiaryApp_DailyRestart"

REM Run task manually
schtasks /Run /TN "DiaryApp_Startup"

REM Stop application
taskkill /IM diary_app.exe /F
```

## Contact and Support

For issues or questions:
- GitHub: https://github.com/Srelock/Diary
- Check logs in `C:\Program Files\DiaryApp\logs\`

