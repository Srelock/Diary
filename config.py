# Email Configuration
# IMPORTANT: These settings are used by app.py for sending emails
# Update these with your Gmail credentials

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Gmail SMTP server (do not change)
    'smtp_port': 587,                  # Gmail SMTP port (do not change)
    'email': 'diaryparkwest@gmail.com',        # Your Gmail address
    'password': 'izcl aluk xxri mxit',          # Your Gmail App Password (16 chars)
    'recipient': 'portersparkwest@gmail.com'   # Default recipient (can be changed in Settings tab)
}

# Schedule Configuration
# NOTE: Email time and recipients are controlled via the Settings tab in the web interface
# This DAILY_REPORT_TIME value is NOT used by the app (kept for reference only)
DAILY_REPORT_TIME = "18:00"

# Database Configuration
# NOTE: This is NOT currently used by the app (kept for reference only)
DATABASE_URL = 'sqlite:///diary.db'
