#!/usr/bin/env python3
"""
Setup script for Building Management Diary Application
Run this script to install dependencies and configure the application
"""

import subprocess
import sys
import os
import sqlite3
from pathlib import Path

def install_requirements():
    """Install required Python packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing packages: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    directories = [
        'reports',
        'reports/PDF',
        'reports/CSV',
        'templates',
        'static'
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_config_file():
    """Create configuration file with email settings"""
    config_content = '''# Email Configuration
# Update these settings with your email provider details

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Change to your email provider
    'smtp_port': 587,
    'email': 'your-email@gmail.com',  # Change to your email
    'password': 'your-app-password',  # Change to your app password
    'recipient': 'recipient@example.com'  # Change to recipient email
}

# Schedule Configuration
# Daily report will be sent at 11:59 PM
DAILY_REPORT_TIME = "23:59"

# Database Configuration
DATABASE_URL = 'sqlite:///diary.db'
'''
    
    with open('config.py', 'w') as f:
        f.write(config_content)
    print("✓ Configuration file created: config.py")
    print("⚠️  Please update config.py with your email settings!")

def create_startup_script():
    """Create startup script for easy launching"""
    startup_content = '''@echo off
echo Starting Building Management Diary...
echo.
echo The application will be available at: http://localhost:5050
echo Press Ctrl+C to stop the application
echo.
python app.py
pause
'''
    
    with open('start_diary.bat', 'w') as f:
        f.write(startup_content)
    print("✓ Startup script created: start_diary.bat")

def create_readme():
    """Create README file with instructions"""
    readme_content = '''# Building Management Diary

A comprehensive diary application for building management with the following features:

## Features

### 1. Daily Occurrences
- Record daily events with time, flat number, and description
- Automatic PDF generation and email sending
- Data clearing after email is sent

### 2. Staff Rota
- Manage staff schedules and shifts
- Track holidays and time-off
- Calendar view of staff availability

### 3. CCTV & Intercom Faults
- Log faults with location and description
- Track fault status (open, in progress, closed)
- Timestamp and resolution tracking

### 4. Water Temperature Monitoring
- Record hourly temperature readings
- Temperature history tracking
- Real-time temperature display

## Installation

1. Run the setup script:
   ```
   python setup.py
   ```

2. Update email configuration in `config.py`

3. Start the application:
   ```
   python app.py
   ```
   Or double-click `start_diary.bat`

## Usage

1. Open your web browser and go to: http://localhost:5050
2. Use the navigation tabs to access different features
3. The application will automatically send daily reports at 6:00 PM
4. All data is stored locally in SQLite database

## Email Configuration

Update the following in `config.py`:
- SMTP server settings
- Your email address and password
- Recipient email address

## System Requirements

- Windows 10/11
- Python 3.8 or higher
- Internet connection for email functionality
- 4GB RAM minimum (recommended 8GB)

## Troubleshooting

- If email doesn't work, check your email provider's SMTP settings
- For Gmail, use App Passwords instead of your regular password
- Make sure Windows Firewall allows Python to access the network
- Check that all required packages are installed: `pip install -r requirements.txt`

## Support

For technical support or feature requests, contact your system administrator.
'''
    
    with open('README.md', 'w') as f:
        f.write(readme_content)
    print("✓ README file created: README.md")

def main():
    """Main setup function"""
    print("=" * 60)
    print("Building Management Diary - Setup")
    print("=" * 60)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✓ Python version: {sys.version}")
    print()
    
    # Install requirements
    if not install_requirements():
        return False
    
    print()
    
    # Create directories
    create_directories()
    print()
    
    # Create configuration file
    create_config_file()
    print()
    
    # Create startup script
    create_startup_script()
    print()
    
    # Create README
    create_readme()
    print()
    
    print("=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update email settings in config.py")
    print("2. Run: python app.py")
    print("3. Open browser to: http://localhost:5050")
    print()
    print("Or simply double-click 'start_diary.bat' to start!")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
