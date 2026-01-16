# Windows Task Scheduler - App Restart Scripts

This folder contains scripts to restart the Building Management Diary application using Windows Task Scheduler.

## Files

- **restart_app.bat** - Batch script for restarting the app (basic)
- **restart_app.ps1** - PowerShell script for restarting the app (recommended)
- **restart_log.txt** - Log file created automatically (contains restart history)

## Setup Instructions for Windows Task Scheduler

### Method 1: Using PowerShell Script (Recommended)

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, and press Enter
   - Or search for "Task Scheduler" in Windows Start menu

2. **Create Basic Task**
   - Click "Create Basic Task..." in the right panel
   - Name: `Restart Building Management Diary`
   - Description: `Automatically restart the diary application`

3. **Set Trigger**
   - Choose when you want the restart to occur:
     - **Daily** - Recommended for daily restarts (e.g., at 2 AM)
     - **Weekly** - For weekly maintenance
     - **On a schedule** - Custom schedule

4. **Set Action**
   - Action: `Start a program`
   - Program/script: `powershell.exe`
   - Add arguments: `-ExecutionPolicy Bypass -File "C:\Users\kelem\Desktop\Project\Diary\scheduler\restart_app.ps1"`
   - **IMPORTANT:** Update the path to match your actual project location!

5. **Additional Settings**
   - Open the Properties dialog (right-click task → Properties)
   - **General Tab:**
     - Check "Run whether user is logged on or not"
     - Check "Run with highest privileges"
   - **Conditions Tab:**
     - Uncheck "Start the task only if the computer is on AC power" (if applicable)
   - **Settings Tab:**
     - Check "Allow task to be run on demand"
     - Check "Run task as soon as possible after a scheduled start is missed"
     - If task fails, restart every: `5 minutes` (up to 3 times)

6. **Save**
   - Enter your Windows password when prompted
   - Click OK

### Method 2: Using Batch Script

Follow the same steps as Method 1, but for the action:
- Program/script: `C:\Users\kelem\Desktop\Project\Diary\scheduler\restart_app.bat`
- **IMPORTANT:** Update the path to match your actual project location!

**Note:** You may need to run Task Scheduler as Administrator for batch scripts to work properly.

## Testing

### Test the Script Manually

1. **Test PowerShell script:**
   ```
   cd C:\Users\kelem\Desktop\Project\Diary\scheduler
   powershell.exe -ExecutionPolicy Bypass -File restart_app.ps1
   ```

2. **Test Batch script:**
   ```
   cd C:\Users\kelem\Desktop\Project\Diary\scheduler
   restart_app.bat
   ```

3. **Test Task Scheduler:**
   - In Task Scheduler, find your task
   - Right-click → "Run"
   - Check the "Last Run Result" should show `0x0` (success)
   - Check `restart_log.txt` for details

### Verify App is Running

After restart, verify the app is accessible at: `http://localhost:5050`

## Logging

All restart attempts are logged to `restart_log.txt` in this folder with timestamps:
```
[2025-11-02 09:00:00] === Restart script executed ===
[2025-11-02 09:00:01] Stopping process PID: 12345
[2025-11-02 09:00:04] Starting new app instance...
[2025-11-02 09:00:07] App restart completed successfully (PID: 67890)
```

## Common Issues

### Issue: "Execution Policy" Error (PowerShell)
**Solution:** The script uses `-ExecutionPolicy Bypass` flag. If this doesn't work, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Task Doesn't Run
**Solutions:**
1. Check Task Scheduler history (right-click task → History)
2. Ensure the paths in Task Scheduler are correct (use full absolute paths)
3. Check that the user account has permissions to run the task
4. Verify Python is in the system PATH

### Issue: App Doesn't Start
**Solutions:**
1. Check `restart_log.txt` for error messages
2. Verify Python is installed and accessible
3. Test manually: `python app.py` from the project directory
4. Check if port 5050 is already in use

### Issue: Multiple Instances Running
**Solution:** The script should stop existing instances first. If issues persist:
1. Manually stop all Python processes: `taskkill /F /IM python.exe`
2. Then run the restart script

## Schedule Recommendations

- **Daily at 2 AM** - Recommended for regular maintenance (before backup at 2 AM)
- **Every 6 hours** - For critical applications requiring frequent restarts
- **Weekly on Sunday at 3 AM** - For less frequent maintenance
- **On system startup** - To ensure app starts automatically

## Updating the Scripts

If you move the project to a different location:
1. Update the paths in Task Scheduler action
2. The scripts automatically detect the project directory (relative to script location)

## Notes

- The PowerShell script is more robust and handles edge cases better
- Both scripts minimize the app window when starting
- The app will be accessible at `http://localhost:5050` after restart
- The scripts preserve the existing functionality of `start_diary.bat`

