# Email Configuration
# IMPORTANT: These settings are used by app.py for sending emails
# 
# SETUP INSTRUCTIONS:
# 1. Copy this file to config.py
# 2. Update the values below with your actual credentials
# 3. NEVER commit config.py to git (it's in .gitignore)

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Gmail SMTP server (do not change)
    'smtp_port': 587,                  # Gmail SMTP port (do not change)
    'email': 'your-email@gmail.com',        # Your Gmail address
    'password': 'your-app-password-here',    # Your Gmail App Password (16 chars)
    'recipient': 'recipient@gmail.com'       # Default recipient (can be changed in Settings tab)
}

# Schedule Configuration
# NOTE: Email time and recipients are controlled via the Settings tab in the web interface
# This DAILY_REPORT_TIME value is NOT used by the app (kept for reference only)
DAILY_REPORT_TIME = "23:59"

# Database Configuration
# NOTE: This is NOT currently used by the app (kept for reference only)
DATABASE_URL = 'sqlite:///diary.db'
