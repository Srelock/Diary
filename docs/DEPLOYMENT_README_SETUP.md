# Diary Application - Deployment Package for New Machine

## System Requirements (Optimized for Weak Machines)

### Minimum Requirements:
- **OS**: Windows 7 or later (32-bit or 64-bit)
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 500MB free space
- **Processor**: Any dual-core processor
- **Internet**: Required for initial setup only

---

## Quick Setup Guide (3 Steps)

### Step 1: Install Python

1. Download Python 3.8 or later (recommended: Python 3.8.10 for weak machines)
   - **Direct Download Link**: https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe
   - For 32-bit systems: https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe

2. Run the installer:
   - ✅ **IMPORTANT**: Check "Add Python to PATH"
   - ✅ Check "Install pip"
   - Click "Install Now"

3. Verify installation:
   - Open Command Prompt
   - Type: `python --version`
   - Should show: Python 3.8.x

### Step 2: Run Automated Setup

1. Double-click `SETUP_APPLICATION.bat`
2. Wait for all dependencies to install (2-5 minutes)
3. The script will verify everything is working

### Step 3: Start the Application

1. Double-click `START_DIARY.bat`
2. Browser will open automatically at http://localhost:5000
3. The application is now running!

---

## Manual Setup (If Automated Setup Fails)

### Install Dependencies Manually:

```bash
# Open Command Prompt in the application folder
cd C:\path\to\Diary

# Install all required packages
pip install -r requirements.txt

# If you get errors on weak machines, try:
pip install --no-cache-dir -r requirements.txt

# Or install one by one:
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==3.0.5
pip install APScheduler==3.10.4
pip install reportlab==4.0.4
pip install email-validator==2.0.0
pip install python-dateutil==2.8.2
pip install pywin32>=306
```

---

## What Gets Installed

### Python Packages (Total ~50MB):
1. **Flask** (2.3.3) - Web application framework
2. **Flask-SQLAlchemy** (3.0.5) - Database management
3. **APScheduler** (3.10.4) - Scheduled report generation
4. **ReportLab** (4.0.4) - PDF creation
5. **email-validator** (2.0.0) - Email validation
6. **python-dateutil** (2.8.2) - Date utilities
7. **pywin32** (306+) - Windows integration

---

## Performance Tips for Weak Machines

### Optimize Performance:

1. **Close Other Applications**: Free up RAM before starting
2. **Use Lightweight Browser**: Microsoft Edge or Chrome (1-2 tabs only)
3. **Disable Auto-Reports**: In Settings tab, disable scheduled reports if not needed
4. **Clear Old Reports**: Delete old PDF/CSV files from `reports/` folder
5. **Reduce Database Size**: Delete old diary entries periodically

### If Application is Slow:

1. Open `config.py` and verify email settings
2. Disable email notifications if not needed
3. Use CSV exports instead of PDF (faster)
4. Limit report date ranges to 1-2 weeks maximum

---

## Troubleshooting

### Python Not Found
- Error: `'python' is not recognized`
- Solution: Reinstall Python and check "Add to PATH"

### Pip Install Fails
- Error: `pip install` errors
- Solution: Try `python -m pip install --upgrade pip`
- Then: `python -m pip install -r requirements.txt`

### Port Already in Use
- Error: `Address already in use`
- Solution: Change port in `app.py` (line ~900): `app.run(port=5001)`

### Out of Memory
- Error: Application crashes
- Solution: 
  - Close other programs
  - Restart computer
  - Try `python app.py --host=127.0.0.1 --port=5000`

### PyWin32 Installation Issues
- Error: `DLL load failed`
- Solution: Run as Administrator: `python Scripts/pywin32_postinstall.py -install`

---

## File Structure After Setup

```
Diary/
├── app.py                      # Main application
├── config.py                   # Email & settings
├── requirements.txt            # Dependencies
├── start_diary.bat            # Quick start script
├── instance/
│   └── diary.db               # Database (auto-created)
├── templates/
│   └── index.html             # Web interface
├── reports/                   # Generated reports
│   ├── PDF/
│   └── CSV/
└── logs/                      # Application logs
```

---

## Configuration

### Email Setup (Optional):

1. Edit `config.py`
2. Update email credentials:
   ```python
   EMAIL_CONFIG = {
       'email': 'your-email@gmail.com',
       'password': 'your-app-password',
       'recipient': 'recipient@email.com'
   }
   ```

3. For Gmail App Password:
   - Enable 2FA on Gmail
   - Generate App Password: https://myaccount.google.com/apppasswords

---

## Daily Use

### Starting the Application:
- Double-click `START_DIARY.bat`
- Or run: `python app.py`

### Stopping the Application:
- Close the Command Prompt window
- Or press `Ctrl+C` in terminal

### Accessing the Application:
- Local: http://localhost:5000
- Network: http://YOUR-IP:5000

---

## Support & Additional Help

### Default Login (if PIN system enabled):
- Check `PIN_SYSTEM_GUIDE.md` for PIN setup

### Documentation:
- `EDITOR_GUIDE.md` - Rich text editor features
- `STAFF_MANAGEMENT_GUIDE.md` - Staff management
- `PIN_SYSTEM_GUIDE.md` - Security setup

### Getting Help:
- Check logs in `logs/` folder
- Review error messages in Command Prompt
- Ensure all dependencies are installed correctly

---

## Uninstallation

To remove the application:

1. Delete the entire `Diary` folder
2. (Optional) Uninstall Python packages:
   ```bash
   pip uninstall Flask Flask-SQLAlchemy APScheduler reportlab email-validator python-dateutil pywin32
   ```
3. (Optional) Uninstall Python from Windows Settings

---

## License & Credits

This is a building management diary application designed for daily operations logging and report generation.

**Version**: 1.0
**Last Updated**: October 2025

