from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import csv
import smtplib
import socket
import traceback
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import hashlib
import hmac
import webbrowser
import threading
import signal
import sys
import time
from functools import wraps
from collections import defaultdict
from colorama import init, Fore, Style

# Try to import bcrypt for secure PIN hashing, fallback to hashlib if not available
try:
    import bcrypt
    BCrypt_AVAILABLE = True
except ImportError:
    BCrypt_AVAILABLE = False
    print(Fore.YELLOW + "⚠️ Warning: bcrypt not available. Install with: pip install bcrypt")
    print(Fore.YELLOW + "⚠️ Using SHA-256 (less secure). Consider upgrading.")

# Initialize colorama for Windows console colors
init(autoreset=True)

# ===== PIN HASHING AND VERIFICATION =====

def hash_pin(pin):
    """Hash a PIN using bcrypt (if available) or SHA-256 as fallback"""
    if BCrypt_AVAILABLE:
        # bcrypt requires bytes
        return bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Fallback to SHA-256 (less secure but compatible)
        return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin_hash(pin, hashed):
    """Verify a PIN against its hash using secure comparison"""
    if not hashed:
        return False
    
    if BCrypt_AVAILABLE and (hashed.startswith('$2a$') or hashed.startswith('$2b$') or hashed.startswith('$2y$')):
        # bcrypt hash (starts with $2a$, $2b$, or $2y$)
        try:
            return bcrypt.checkpw(pin.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            print(Fore.RED + f"Error verifying bcrypt PIN: {e}")
            return False
    else:
        # SHA-256 hash - use constant-time comparison
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        return hmac.compare_digest(pin_hash, hashed)

# ===== RATE LIMITING =====

# Rate limiting storage (in-memory, resets on restart)
rate_limit_storage = defaultdict(list)

def rate_limit(max_attempts=5, window=300):
    """
    Rate limiting decorator to prevent brute force attacks
    max_attempts: Maximum number of attempts allowed
    window: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP address)
            client_id = request.remote_addr
            current_time = time.time()
            
            # Clean up old attempts outside the time window
            rate_limit_storage[client_id] = [
                attempt_time for attempt_time in rate_limit_storage[client_id]
                if current_time - attempt_time < window
            ]
            
            # Check if rate limit exceeded
            if len(rate_limit_storage[client_id]) >= max_attempts:
                return jsonify({
                    'success': False,
                    'error': f'Too many attempts. Please try again in {window // 60} minutes.'
                }), 429  # HTTP 429 Too Many Requests
            
            # Record this attempt
            rate_limit_storage[client_id].append(current_time)
            
            # Call the original function
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_base_path():
    """Get the base path for the application - works for both script and compiled .exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Get base path for application (must be defined before loading config)
BASE_PATH = get_base_path()

# Import configuration from config.py
def load_email_config():
    """Load email configuration from config.py, handling both script and .exe modes"""
    config_path = os.path.join(BASE_PATH, 'config.py')
    
    # If config.py doesn't exist, try to create it from config.example.py
    if not os.path.exists(config_path):
        example_config_path = None
        
        # Try to find config.example.py
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe - check bundled location first
            try:
                example_config_path = get_resource_path('config.example.py')
                if not os.path.exists(example_config_path):
                    # Fallback to same directory as .exe
                    example_config_path = os.path.join(BASE_PATH, 'config.example.py')
            except:
                example_config_path = os.path.join(BASE_PATH, 'config.example.py')
        else:
            # Running as script - check same directory
            example_config_path = os.path.join(BASE_PATH, 'config.example.py')
        
        # If config.example.py exists, copy it to config.py
        if example_config_path and os.path.exists(example_config_path):
            try:
                import shutil
                shutil.copy2(example_config_path, config_path)
                print(Fore.GREEN + f"✓ Created config.py from config.example.py")
                print(Fore.YELLOW + "⚠️ Please update config.py with your email credentials!")
            except Exception as e:
                print(Fore.YELLOW + f"⚠️ Could not create config.py from example: {e}")
                print(Fore.YELLOW + "⚠️ Using default email configuration")
                return {
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'email': 'your-email@gmail.com',
                    'password': 'your-app-password',
                    'recipient': 'recipient@example.com'
                }
        else:
            print(Fore.YELLOW + f"⚠️ config.py not found at {config_path}")
            print(Fore.YELLOW + "⚠️ config.example.py also not found")
            print(Fore.YELLOW + "⚠️ Using default email configuration")
            return {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email': 'your-email@gmail.com',
                'password': 'your-app-password',
                'recipient': 'recipient@example.com'
            }
    
    # Add base path to sys.path if not already there (for .exe mode)
    if BASE_PATH not in sys.path:
        sys.path.insert(0, BASE_PATH)
    
    # Try importing config first
    try:
        from config import EMAIL_CONFIG
        print(Fore.GREEN + "✓ Email configuration loaded from config.py")
        return EMAIL_CONFIG
    except ImportError as import_err:
        # If import fails, try loading the file directly
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            print(Fore.GREEN + "✓ Email configuration loaded from config.py")
            return config_module.EMAIL_CONFIG
        except Exception as load_err:
            print(Fore.YELLOW + f"⚠️ Error loading config.py: {load_err}")
            print(Fore.YELLOW + "⚠️ Using default email configuration")
            return {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email': 'your-email@gmail.com',
                'password': 'your-app-password',
                'recipient': 'recipient@example.com'
            }
    except Exception as e:
        # Other unexpected errors
        print(Fore.YELLOW + f"⚠️ Unexpected error loading config: {e}")
        print(Fore.YELLOW + "⚠️ Using default email configuration")
        return {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'email': 'your-email@gmail.com',
            'password': 'your-app-password',
            'recipient': 'recipient@example.com'
        }

# Load email configuration
EMAIL_CONFIG = load_email_config()

# Ensure required directories exist
instance_dir = os.path.join(BASE_PATH, 'instance')
os.makedirs(instance_dir, exist_ok=True)

# Templates directory - use get_resource_path for PyInstaller compatibility
# When running as .exe, templates are in _MEIPASS temp folder
# When running as script, templates are in project directory
templates_dir = get_resource_path('templates')

# Initialize Flask app
app = Flask(__name__, template_folder=templates_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "diary.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class DailyOccurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    time = db.Column(db.String(10), nullable=False)
    flat_number = db.Column(db.String(20), nullable=False)
    reported_by = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sent = db.Column(db.Boolean, default=False)

class StaffRota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    staff_name = db.Column(db.String(100), nullable=False)
    shift_start = db.Column(db.String(10))
    shift_end = db.Column(db.String(10))
    status = db.Column(db.String(20), default='working')  # working, off, holiday
    notes = db.Column(db.Text)

class CCTVFault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    fault_type = db.Column(db.String(50), nullable=False)  # CCTV or Intercom
    flat_number = db.Column(db.String(20), nullable=False)
    block_number = db.Column(db.String(20))
    floor_number = db.Column(db.String(20))
    location = db.Column(db.String(100))  # Keep for backwards compatibility
    description = db.Column(db.Text, nullable=False)
    contact_details = db.Column(db.String(200))
    additional_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed
    resolved_date = db.Column(db.DateTime)

class WaterTemperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    temperature = db.Column(db.Float, nullable=False)
    time_recorded = db.Column(db.String(5), nullable=False)  # Format: HH:MM

class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sent_date = db.Column(db.DateTime, default=datetime.now)
    recipient = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    pdf_path = db.Column(db.String(500), nullable=False)

class ScheduleSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_time = db.Column(db.String(5), default='18:00')  # Format: HH:MM
    email_enabled = db.Column(db.Boolean, default=True)
    recipient_email = db.Column(db.String(500), default='recipient@example.com')  # Support multiple emails
    # Sender email settings (configurable in Settings tab)
    sender_email = db.Column(db.String(200), default='')
    sender_password = db.Column(db.String(200), default='')
    smtp_server = db.Column(db.String(200), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=587)
    last_updated = db.Column(db.DateTime, default=datetime.now)

class StaffMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)  # Shift 1&2: red, yellow, green, blue | Night Shift: purple, darkred, darkgreen, brownishyellow
    shift = db.Column(db.Integer, nullable=False)  # 1, 2, or 3 (Night Shift)
    active = db.Column(db.Boolean, default=True)

class ShiftLeader(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    pin = db.Column(db.String(100), nullable=False)  # Store hashed PIN
    active = db.Column(db.Boolean, default=True)
    is_super_user = db.Column(db.Boolean, default=False)  # Super user has special privileges
    created_date = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user_name = db.Column(db.String(100), nullable=False)  # Shift leader name
    action_type = db.Column(db.String(50), nullable=False)  # e.g., 'delete', 'modify', 'add'
    entity_type = db.Column(db.String(50), nullable=False)  # e.g., 'occurrence', 'staff', 'settings'
    entity_id = db.Column(db.String(100))  # ID of affected entity
    description = db.Column(db.Text, nullable=False)  # Human-readable description
    ip_address = db.Column(db.String(50))

class Overtime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.String(100))  # Super user who created this
    created_date = db.Column(db.DateTime, default=datetime.now)
    updated_date = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# Initialize scheduler
scheduler = BackgroundScheduler()

# Rotation Pattern Constants (reused across multiple functions)
# Reference date for rotation calculation - September 29, 2025 (Monday of Week 1)
ROTATION_REFERENCE_DATE = datetime(2025, 9, 29).date()

# Day shift rotation pattern (4-week cycle)
# Week number (0-3), Day of week (0=Monday, 6=Sunday)
DAY_SHIFT_ROTATION_PATTERN = {
    # Week 1
    (0, 0): 'blue', (0, 1): 'green', (0, 2): 'green', (0, 3): 'yellow',
    (0, 4): 'blue', (0, 5): 'red', (0, 6): ['red', 'yellow'],
    # Week 2
    (1, 0): 'red', (1, 1): 'blue', (1, 2): 'blue', (1, 3): 'green',
    (1, 4): 'red', (1, 5): 'yellow', (1, 6): ['yellow', 'green'],
    # Week 3
    (2, 0): 'yellow', (2, 1): 'red', (2, 2): 'red', (2, 3): 'blue',
    (2, 4): 'yellow', (2, 5): 'green', (2, 6): ['green', 'blue'],
    # Week 4
    (3, 0): 'green', (3, 1): 'yellow', (3, 2): 'yellow', (3, 3): 'red',
    (3, 4): 'green', (3, 5): 'blue', (3, 6): ['blue', 'red'],
}

# Night shift rotation pattern (separate 4-week cycle)
NIGHT_SHIFT_ROTATION_PATTERN = {
    # Week 1: Mon-Purple, Tue-Purple, Wed-DarkRed, Thu-DarkGreen, Fri-DarkGreen, Sat-BrownishYellow, Sun-BrownishYellow+Purple
    (0, 0): 'purple', (0, 1): 'purple', (0, 2): 'darkred', (0, 3): 'darkgreen',
    (0, 4): 'darkgreen', (0, 5): 'brownishyellow', (0, 6): ['brownishyellow', 'purple'],
    # Week 2: Mon-DarkRed, Tue-DarkRed, Wed-DarkGreen, Thu-BrownishYellow, Fri-BrownishYellow, Sat-Purple, Sun-Purple+DarkRed
    (1, 0): 'darkred', (1, 1): 'darkred', (1, 2): 'darkgreen', (1, 3): 'brownishyellow',
    (1, 4): 'brownishyellow', (1, 5): 'purple', (1, 6): ['purple', 'darkred'],
    # Week 3: Mon-DarkGreen, Tue-DarkGreen, Wed-BrownishYellow, Thu-Purple, Fri-Purple, Sat-DarkRed, Sun-DarkRed+DarkGreen
    (2, 0): 'darkgreen', (2, 1): 'darkgreen', (2, 2): 'brownishyellow', (2, 3): 'purple',
    (2, 4): 'purple', (2, 5): 'darkred', (2, 6): ['darkred', 'darkgreen'],
    # Week 4: Mon-BrownishYellow, Tue-BrownishYellow, Wed-Purple, Thu-DarkRed, Fri-DarkRed, Sat-DarkGreen, Sun-DarkGreen+BrownishYellow
    (3, 0): 'brownishyellow', (3, 1): 'brownishyellow', (3, 2): 'purple', (3, 3): 'darkred',
    (3, 4): 'darkred', (3, 5): 'darkgreen', (3, 6): ['darkgreen', 'brownishyellow'],
}

# Helper Functions for Rotation Calculations
def get_rotation_key(date, reference_date=None):
    """Calculate rotation pattern key (week_in_cycle, day_of_week) for a given date"""
    if reference_date is None:
        reference_date = ROTATION_REFERENCE_DATE
    days_diff = (date - reference_date).days
    week_in_cycle = (days_diff // 7) % 4
    day_of_week = date.weekday()
    return (week_in_cycle, day_of_week)

def normalize_colors(colors_off):
    """Ensure colors_off is always a list for uniform processing"""
    if colors_off and not isinstance(colors_off, list):
        return [colors_off]
    return colors_off or []

def get_staff_off_names_from_colors(colors_off, porter_groups, shift_types=None):
    """
    Get list of staff names who are off based on colors.
    
    Args:
        colors_off: Single color string or list of color strings
        porter_groups: Dictionary mapping colors to shifts
        shift_types: List of shift keys to include (e.g., ['shift1', 'shift2']) or None for all
    
    Returns:
        List of staff names who are off
    """
    colors_list = normalize_colors(colors_off)
    staff_names = []
    
    if shift_types is None:
        shift_types = ['shift1', 'shift2', 'shift3']
    
    for color in colors_list:
        if color in porter_groups:
            for shift_key in shift_types:
                if shift_key in porter_groups[color]:
                    staff_names.append(porter_groups[color][shift_key])
    
    return staff_names

def get_staff_off_for_date(date, porter_groups, include_night_shift=True):
    """
    Get list of staff names who are scheduled off for a given date based on rotation patterns.
    
    Args:
        date: Date object to check
        porter_groups: Dictionary mapping colors to shifts
        include_night_shift: Whether to include night shift in the result
    
    Returns:
        List of staff names who are scheduled off
    """
    pattern_key = get_rotation_key(date)
    
    # Get day shift colors off
    day_colors_off = normalize_colors(DAY_SHIFT_ROTATION_PATTERN.get(pattern_key))
    staff_off = get_staff_off_names_from_colors(day_colors_off, porter_groups, ['shift1', 'shift2'])
    
    # Add night shift if requested
    if include_night_shift:
        night_colors_off = normalize_colors(NIGHT_SHIFT_ROTATION_PATTERN.get(pattern_key))
        night_staff_off = get_staff_off_names_from_colors(night_colors_off, porter_groups, ['shift3'])
        staff_off.extend(night_staff_off)
    
    return staff_off

# Wrapper functions for scheduled tasks that need app context
def send_daily_report_with_context(report_date=None):
    """Wrapper for send_daily_report that provides Flask app context"""
    with app.app_context():
        return send_daily_report(report_date)

def cleanup_old_leave_data_with_context():
    """Wrapper for cleanup_old_leave_data that provides Flask app context"""
    with app.app_context():
        return cleanup_old_leave_data()

def backup_database_to_gdrive_with_context():
    """Wrapper for backup_database_to_gdrive that provides Flask app context"""
    with app.app_context():
        return backup_database_to_gdrive()

def get_porter_groups():
    """Get porter groups from database"""
    staff_members = StaffMember.query.filter_by(active=True).all()
    
    # Build porter_groups dictionary
    porter_groups = {}
    all_staff_by_shift = {'Shift 1': [], 'Shift 2': [], 'Night Shift': []}
    
    for staff in staff_members:
        color = staff.color
        shift_key = f'shift{staff.shift}'
        shift_name = f'Shift {staff.shift}' if staff.shift in [1, 2] else 'Night Shift'
        
        if color not in porter_groups:
            porter_groups[color] = {}
        porter_groups[color][shift_key] = staff.name
        
        all_staff_by_shift[shift_name].append(staff.name)
    
    return porter_groups, all_staff_by_shift

def send_daily_report(report_date=None):
    """Send daily report and clear data"""
    try:
        # Check if email is enabled
        settings = ScheduleSettings.query.first()
        if not settings or not settings.email_enabled:
            print(Fore.YELLOW + "Email sending is disabled")
            return
        
        # Use provided date or default to today
        if report_date is None:
            report_date = datetime.now().date()
        
        # Convert date to datetime for proper comparison with timestamp column
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date + timedelta(days=1), datetime.min.time())
        
        # Get occurrences for the specified date
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= start_datetime,
            DailyOccurrence.timestamp < end_datetime,
            DailyOccurrence.sent == False
        ).all()
        
        # Generate PDF and CSV for local backup (not sent via email)
        pdf_path = generate_daily_pdf(occurrences, report_date)
        csv_path = generate_daily_csv(occurrences, report_date)
        
        # Send email FIRST - only log if successful
        email_sent = send_email(f"Daily Report - {report_date}", settings.recipient_email)
        
        if email_sent:
            # Log the email only after successful send
            email_log = EmailLog(
                recipient=settings.recipient_email,
                subject=f"Daily Report - {report_date}",
                pdf_path=pdf_path  # Saved locally, not emailed
            )
            db.session.add(email_log)
            
            # Mark as sent if there were occurrences and email succeeded
            if occurrences:
                for occurrence in occurrences:
                    occurrence.sent = True
            
            # Single commit for both email log and sent status
            db.session.commit()
            
            print(Fore.GREEN + f"Daily report sent successfully for {report_date}")
            print(Fore.CYAN + f"Local backups saved - PDF: {pdf_path}, CSV: {csv_path}")
        else:
            print(Fore.YELLOW + f"⚠️ Email failed to send for {report_date}, but PDF/CSV saved locally")
            print(Fore.CYAN + f"PDF: {pdf_path}")
            print(Fore.CYAN + f"CSV: {csv_path}")
        
        return email_sent
    except Exception as e:
        print(Fore.RED + f"Error sending daily report: {e}")
        # Rollback any uncommitted database changes
        try:
            db.session.rollback()
        except Exception as rollback_error:
            print(Fore.YELLOW + f"Warning: Error during database rollback: {rollback_error}")
        return False

def generate_daily_pdf(occurrences, report_date=None):
    """Generate PDF report of daily occurrences"""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    
    # Use provided date or default to today
    if report_date is None:
        report_date = datetime.now().date()
    
    # Filename uses report date, with time suffix to avoid overwriting
    filename = f"daily_report_{report_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.pdf"
    reports_pdf_dir = os.path.join(BASE_PATH, 'reports', 'PDF')
    filepath = os.path.join(reports_pdf_dir, filename)
    
    # Create reports/PDF directory if it doesn't exist
    os.makedirs(reports_pdf_dir, exist_ok=True)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph(f"Daily Occurrences Report - {report_date.strftime('%B %d, %Y')}", title_style))
    story.append(Spacer(1, 20))
    
    # Add staff schedule section
    story.append(Paragraph("Staff Schedule", ParagraphStyle(
        'ScheduleTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=15,
        textColor=colors.darkblue
    )))
    
    # Get staff schedule from porter rota for the report date
    today = report_date
    
    # Get staff members from database
    porter_groups, all_staff = get_porter_groups()
    
    # Get staff who are scheduled off based on rotation patterns
    staff_off_names = get_staff_off_for_date(today, porter_groups, include_night_shift=True)
    
    # Check database for holidays and sick leave for today
    staff_on_leave = {}
    leave_records = StaffRota.query.filter_by(date=today).all()
    for record in leave_records:
        if record.status in ['holiday', 'sick', 'off']:
            staff_on_leave[record.staff_name] = record.status.upper()
    
    # Create staff schedule in 3-column layout (like the web page)
    # Build content for each shift box
    shift1_content = []
    shift2_content = []
    night_shift_content = []
    
    # Sort staff names to ensure consistent ordering (reverse to match web interface)
    shift1_staff = sorted(all_staff['Shift 1'], reverse=True)
    shift2_staff = sorted(all_staff['Shift 2'], reverse=True)
    night_shift_staff = sorted(all_staff['Night Shift'], reverse=True)
    
    for staff_name in shift1_staff:
        # Check if on leave first (higher priority than rotation)
        if staff_name in staff_on_leave:
            status = staff_on_leave[staff_name]
        else:
            is_off = staff_name in staff_off_names
            status = 'OFF' if is_off else 'ON'
        shift1_content.append(f"{staff_name}: {status}")
    
    for staff_name in shift2_staff:
        # Check if on leave first (higher priority than rotation)
        if staff_name in staff_on_leave:
            status = staff_on_leave[staff_name]
        else:
            is_off = staff_name in staff_off_names
            status = 'OFF' if is_off else 'ON'
        shift2_content.append(f"{staff_name}: {status}")
    
    for staff_name in night_shift_staff:
        # Check if on leave first (higher priority than rotation)
        if staff_name in staff_on_leave:
            status = staff_on_leave[staff_name]
        else:
            is_off = staff_name in staff_off_names
            status = 'OFF' if is_off else 'ON'
        night_shift_content.append(f"{staff_name}: {status}")
    
    # Create paragraphs for each box
    box_style = ParagraphStyle(
        'BoxContent',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=5,
        rightIndent=5,
        spaceBefore=3,
        spaceAfter=3
    )
    
    shift1_text = '<br/>'.join(shift1_content) if shift1_content else 'No staff assigned'
    shift2_text = '<br/>'.join(shift2_content) if shift2_content else 'No staff assigned'
    night_shift_text = '<br/>'.join(night_shift_content) if night_shift_content else 'No staff assigned'
    
    # Create the 3-column table
    schedule_data = [
        [
            Paragraph('<b>SHIFT 1</b><br/>(7am-2pm / 2pm-10pm)<br/>' + shift1_text, box_style),
            Paragraph('<b>SHIFT 2</b><br/>(2pm-10pm / 7am-2pm)<br/>' + shift2_text, box_style),
            Paragraph('<b>NIGHT SHIFT</b><br/>(10pm-7am)<br/>' + night_shift_text, box_style)
        ]
    ]
    
    schedule_table = Table(schedule_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e0f2f7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 2, colors.HexColor('#dee2e6')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
    ]))
    
    story.append(schedule_table)
    story.append(Spacer(1, 30))
    
    # Daily Occurrences section
    story.append(Paragraph("Daily Occurrences", ParagraphStyle(
        'OccurrencesTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=15,
        textColor=colors.darkblue
    )))
    
    # Check if there are no occurrences
    if not occurrences or len(occurrences) == 0:
        # Add a message indicating no occurrences
        no_occurrence_style = ParagraphStyle(
            'NoOccurrenceStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            textColor=colors.darkgreen,
            alignment=1,  # Center alignment
            spaceBefore=10,
            spaceAfter=10
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph("No incidents or occurrences were recorded today.", no_occurrence_style))
        story.append(Spacer(1, 10))
    else:
        # Create table data with proper text wrapping using Paragraph objects
        from reportlab.lib.styles import ParagraphStyle
        
        # Define paragraph style for wrapped text
        wrap_style = ParagraphStyle(
            'WrapStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            leftIndent=0,
            rightIndent=0,
            spaceBefore=0,
            spaceAfter=0
        )
        
        # Table data with wrapped text
        data = [['TIME', 'FLAT', 'BY', 'INCIDENT REPORT']]
        for occurrence in occurrences:
            # Create wrapped paragraph for description
            description_para = Paragraph(occurrence.description, wrap_style)
            
            data.append([
                occurrence.time,
                occurrence.flat_number,
                occurrence.reported_by,
                description_para
            ])
        
        # Create table with proper column widths and text wrapping
        table = Table(data, colWidths=[0.7*inch, 0.7*inch, 0.9*inch, 4.5*inch], repeatRows=1)
        table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (2, -1), 'CENTER'),  # Center TIME, FLAT, BY columns
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),    # Left align INCIDENT REPORT
            ('FONTNAME', (0, 1), (2, -1), 'Helvetica'),  # Only apply to first 3 columns
            ('FONTSIZE', (0, 1), (2, -1), 9),      # Only apply to first 3 columns
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6)
        ]))
        
        story.append(table)
    
    # Add spacing before water temperature section
    story.append(Spacer(1, 30))
    
    # Water Temperature section
    story.append(Paragraph("Water Temperature Readings", ParagraphStyle(
        'TempTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=15,
        textColor=colors.darkblue
    )))
    
    # Get water temperatures for the report date
    today_start = datetime.combine(report_date, datetime.min.time())
    today_end = datetime.combine(report_date, datetime.max.time())
    
    water_temps = WaterTemperature.query.filter(
        WaterTemperature.timestamp >= today_start,
        WaterTemperature.timestamp <= today_end
    ).order_by(WaterTemperature.time_recorded).all()
    
    if water_temps and len(water_temps) > 0:
        # Format temperatures as comma-separated text: "01:00 [53], 02:00 [57.1], ..."
        temp_entries = []
        for temp_reading in water_temps:
            # Format temperature with appropriate decimal places
            temp_value = temp_reading.temperature
            # If it's a whole number, show no decimals; otherwise show as is
            if temp_value == int(temp_value):
                temp_str = f"{int(temp_value)}"
            else:
                temp_str = f"{temp_value:.1f}".rstrip('0').rstrip('.')
            
            temp_entries.append(f"{temp_reading.time_recorded} [{temp_str}]")
        
        # Join all entries with commas
        temp_text = ", ".join(temp_entries)
        
        # Create a bordered paragraph with the temperature readings
        temp_style = ParagraphStyle(
            'TempReadings',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            leftIndent=10,
            rightIndent=10,
            spaceBefore=10,
            spaceAfter=10,
            alignment=0  # Left alignment
        )
        
        # Create a table with single cell to create the border effect
        temp_data = [[Paragraph(temp_text, temp_style)]]
        temp_table = Table(temp_data, colWidths=[6.5*inch])
        temp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        
        story.append(temp_table)
    else:
        # No temperature readings
        no_temp_style = ParagraphStyle(
            'NoTempStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            textColor=colors.gray,
            alignment=1,
            spaceBefore=10,
            spaceAfter=10
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph("No water temperature readings recorded today.", no_temp_style))
        story.append(Spacer(1, 10))
    
    doc.build(story)
    return filepath

def generate_daily_csv(occurrences, report_date=None):
    """Generate CSV backup of daily occurrences"""
    # Use provided date or default to today
    if report_date is None:
        report_date = datetime.now().date()
    
    # Filename uses report date, with time suffix to avoid overwriting
    filename = f"daily_report_{report_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.csv"
    reports_csv_dir = os.path.join(BASE_PATH, 'reports', 'CSV')
    filepath = os.path.join(reports_csv_dir, filename)
    
    # Create reports/CSV directory if it doesn't exist
    os.makedirs(reports_csv_dir, exist_ok=True)
    
    # Get date and staff schedule info for the report
    today = report_date
    porter_groups, all_staff = get_porter_groups()
    
    # Get staff who are scheduled off based on rotation patterns
    staff_off_names = get_staff_off_for_date(today, porter_groups, include_night_shift=True)
    
    # Check database for holidays and sick leave for today
    staff_on_leave = {}
    leave_records = StaffRota.query.filter_by(date=today).all()
    for record in leave_records:
        if record.status in ['holiday', 'sick', 'off']:
            staff_on_leave[record.staff_name] = record.status.upper()
    
    # Sort staff names to ensure consistent ordering (reverse to match web interface)
    shift1_staff = sorted(all_staff['Shift 1'], reverse=True)
    shift2_staff = sorted(all_staff['Shift 2'], reverse=True)
    night_shift_staff = sorted(all_staff['Night Shift'], reverse=True)
    
    # Write CSV file
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header information
        writer.writerow(['Daily Occurrences Report'])
        writer.writerow(['Date', today.strftime('%B %d, %Y')])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Staff schedule section
        writer.writerow(['STAFF SCHEDULE'])
        writer.writerow([])
        
        # Shift 1
        writer.writerow(['SHIFT 1 (7am-2pm / 2pm-10pm)'])
        for staff_name in shift1_staff:
            # Check if on leave first (higher priority than rotation)
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            writer.writerow([staff_name, status])
        if not shift1_staff:
            writer.writerow(['No staff assigned', ''])
        writer.writerow([])
        
        # Shift 2
        writer.writerow(['SHIFT 2 (2pm-10pm / 7am-2pm)'])
        for staff_name in shift2_staff:
            # Check if on leave first (higher priority than rotation)
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            writer.writerow([staff_name, status])
        if not shift2_staff:
            writer.writerow(['No staff assigned', ''])
        writer.writerow([])
        
        # Night Shift
        writer.writerow(['NIGHT SHIFT (10pm-7am)'])
        for staff_name in night_shift_staff:
            # Check if on leave first (higher priority than rotation)
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            writer.writerow([staff_name, status])
        if not night_shift_staff:
            writer.writerow(['No staff assigned', ''])
        writer.writerow([])
        
        # Daily occurrences section
        writer.writerow(['DAILY OCCURRENCES'])
        writer.writerow([])
        
        if not occurrences or len(occurrences) == 0:
            writer.writerow(['No incidents or occurrences were recorded today.'])
        else:
            # Column headers
            writer.writerow(['TIME', 'FLAT', 'REPORTED BY', 'INCIDENT REPORT'])
            
            # Occurrence data
            for occurrence in occurrences:
                writer.writerow([
                    occurrence.time,
                    occurrence.flat_number,
                    occurrence.reported_by,
                    occurrence.description
                ])
    
    return filepath

def generate_email_html(occurrences, report_date=None):
    """Generate HTML email body that matches the Daily Occurrences webpage styling"""
    # Use provided date or default to today
    if report_date is None:
        report_date = datetime.now().date()
    
    # Get staff schedule info
    today = report_date
    porter_groups, all_staff = get_porter_groups()
    
    # Get staff who are scheduled off based on rotation patterns
    staff_off_names = get_staff_off_for_date(today, porter_groups, include_night_shift=True)
    
    # Check database for holidays and sick leave
    staff_on_leave = {}
    leave_records = StaffRota.query.filter_by(date=today).all()
    for record in leave_records:
        if record.status in ['holiday', 'sick', 'off']:
            staff_on_leave[record.staff_name] = record.status.upper()
    
    # Sort staff names
    shift1_staff = sorted(all_staff['Shift 1'], reverse=True)
    shift2_staff = sorted(all_staff['Shift 2'], reverse=True)
    night_shift_staff = sorted(all_staff['Night Shift'], reverse=True)
    
    # Get water temperatures
    today_start = datetime.combine(report_date, datetime.min.time())
    today_end = datetime.combine(report_date, datetime.max.time())
    water_temps = WaterTemperature.query.filter(
        WaterTemperature.timestamp >= today_start,
        WaterTemperature.timestamp <= today_end
    ).order_by(WaterTemperature.time_recorded).all()
    
    # Build HTML email using list for efficient string building
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; margin: 0; padding: 20px;">
    <div style="max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 30px; text-align: center;">
            <h1 style="font-size: 2.5em; margin: 0 0 10px 0; font-weight: 300;">Daily Occurrences Report</h1>
            <p style="font-size: 1.1em; margin: 0; opacity: 0.9;">{report_date.strftime('%B %d, %Y')}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            
            <!-- Staff Schedule Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2c3e50; font-size: 1.5em; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Today's Staff Schedule</h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <!-- Shift 1 -->
                        <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                            <div style="background: #e0f2f7; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px 15px; text-align: center;">
                                <div style="font-weight: bold; font-size: 14px; color: #000; margin-bottom: 15px; background: #cce7f0; padding: 8px; border-radius: 4px;">SHIFT 1</div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 15px;">(7am-2pm / 2pm-10pm)</div>
""")
    
    # Add Shift 1 staff
    if shift1_staff:
        for staff_name in shift1_staff:
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            
            # Status styling
            if status == 'HOLIDAY':
                status_bg = '#fff3cd'
                status_color = '#856404'
            elif status == 'SICK':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            elif status == 'OFF':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            else:  # ON
                status_bg = '#d4edda'
                status_color = '#155724'
            
            html_parts.append(f"""
                                <table style="width: 100%; border-collapse: collapse; margin-bottom: 5px;">
                                    <tr>
                                        <td style="text-align: left; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 16px; font-weight: bold; color: #333;">{staff_name}</span>
                                        </td>
                                        <td style="text-align: right; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; background: {status_bg}; color: {status_color};">{status}</span>
                                        </td>
                                    </tr>
                                </table>
""")
    else:
        html_parts.append('<div style="font-size: 13px; color: #666;">No staff assigned</div>')
    
    html_parts.append("""
                            </div>
                        </td>
                        
                        <!-- Shift 2 -->
                        <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                            <div style="background: #e0f2f7; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px 15px; text-align: center;">
                                <div style="font-weight: bold; font-size: 14px; color: #000; margin-bottom: 15px; background: #cce7f0; padding: 8px; border-radius: 4px;">SHIFT 2</div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 15px;">(2pm-10pm / 7am-2pm)</div>
""")
    
    # Add Shift 2 staff
    if shift2_staff:
        for staff_name in shift2_staff:
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            
            if status == 'HOLIDAY':
                status_bg = '#fff3cd'
                status_color = '#856404'
            elif status == 'SICK':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            elif status == 'OFF':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            else:
                status_bg = '#d4edda'
                status_color = '#155724'
            
            html_parts.append(f"""
                                <table style="width: 100%; border-collapse: collapse; margin-bottom: 5px;">
                                    <tr>
                                        <td style="text-align: left; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 16px; font-weight: bold; color: #333;">{staff_name}</span>
                                        </td>
                                        <td style="text-align: right; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; background: {status_bg}; color: {status_color};">{status}</span>
                                        </td>
                                    </tr>
                                </table>
""")
    else:
        html_parts.append('<div style="font-size: 13px; color: #666;">No staff assigned</div>')
    
    html_parts.append("""
                            </div>
                        </td>
                        
                        <!-- Night Shift -->
                        <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                            <div style="background: #e0f2f7; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px 15px; text-align: center;">
                                <div style="font-weight: bold; font-size: 14px; color: #000; margin-bottom: 15px; background: #cce7f0; padding: 8px; border-radius: 4px;">NIGHT SHIFT</div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 15px;">(10pm-7am)</div>
""")
    
    # Add Night Shift staff
    if night_shift_staff:
        for staff_name in night_shift_staff:
            if staff_name in staff_on_leave:
                status = staff_on_leave[staff_name]
            else:
                is_off = staff_name in staff_off_names
                status = 'OFF' if is_off else 'ON'
            
            if status == 'HOLIDAY':
                status_bg = '#fff3cd'
                status_color = '#856404'
            elif status == 'SICK':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            elif status == 'OFF':
                status_bg = '#f8d7da'
                status_color = '#721c24'
            else:
                status_bg = '#d4edda'
                status_color = '#155724'
            
            html_parts.append(f"""
                                <table style="width: 100%; border-collapse: collapse; margin-bottom: 5px;">
                                    <tr>
                                        <td style="text-align: left; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 16px; font-weight: bold; color: #333;">{staff_name}</span>
                                        </td>
                                        <td style="text-align: right; padding: 8px 0; border-bottom: 1px solid #b8d4e0;">
                                            <span style="font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px; background: {status_bg}; color: {status_color};">{status}</span>
                                        </td>
                                    </tr>
                                </table>
""")
    else:
        html_parts.append('<div style="font-size: 13px; color: #666;">No staff assigned</div>')
    
    html_parts.append("""
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Daily Occurrences Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2c3e50; font-size: 1.5em; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Daily Occurrences</h2>
""")
    
    # Add occurrences table or "no occurrences" message
    if not occurrences or len(occurrences) == 0:
        html_parts.append("""
                <div style="background: #d4edda; color: #155724; padding: 20px; border-radius: 8px; text-align: center; font-size: 1.1em;">
                    No incidents or occurrences were recorded today.
                </div>
""")
    else:
        html_parts.append("""
                <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <thead>
                        <tr>
                            <th style="background: #e0f2f7; padding: 20px 15px; text-align: center; font-weight: 800; color: #000; border-bottom: 3px solid #dee2e6; font-size: 1.2em; letter-spacing: 0.5px; width: 80px;">TIME</th>
                            <th style="background: #e0f2f7; padding: 20px 15px; text-align: center; font-weight: 800; color: #000; border-bottom: 3px solid #dee2e6; font-size: 1.2em; letter-spacing: 0.5px; width: 80px;">FLAT</th>
                            <th style="background: #e0f2f7; padding: 20px 15px; text-align: center; font-weight: 800; color: #000; border-bottom: 3px solid #dee2e6; font-size: 1.2em; letter-spacing: 0.5px; width: 80px;">BY</th>
                            <th style="background: #e0f2f7; padding: 20px 15px; text-align: left; font-weight: 800; color: #000; border-bottom: 3px solid #dee2e6; font-size: 1.2em; letter-spacing: 0.5px;">INCIDENT REPORT</th>
                        </tr>
                    </thead>
                    <tbody>
""")
        
        for occurrence in occurrences:
            html_parts.append(f"""
                        <tr>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.time}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.flat_number}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.reported_by}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: left; background: white;">{occurrence.description}</td>
                        </tr>
""")
        
        html_parts.append("""
                    </tbody>
                </table>
""")
    
    html_parts.append("""
            </div>
            
            <!-- Water Temperature Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2c3e50; font-size: 1.5em; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Water Temperature Readings</h2>
""")
    
    # Add water temperature readings
    if water_temps and len(water_temps) > 0:
        temp_entries = []
        for temp_reading in water_temps:
            temp_value = temp_reading.temperature
            if temp_value == int(temp_value):
                temp_str = f"{int(temp_value)}"
            else:
                temp_str = f"{temp_value:.1f}".rstrip('0').rstrip('.')
            temp_entries.append(f"{temp_reading.time_recorded} [{temp_str}]")
        
        temp_text = ", ".join(temp_entries)
        
        html_parts.append(f"""
                <div style="background: white; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px; font-size: 1em; line-height: 1.6;">
                    {temp_text}
                </div>
""")
    else:
        html_parts.append("""
                <div style="background: #f8f9fa; color: #6c757d; padding: 20px; border-radius: 8px; text-align: center; font-size: 1.1em;">
                    No water temperature readings recorded today.
                </div>
""")
    
    html_parts.append("""
            </div>
            
        </div>
        
    </div>
</body>
</html>
""")
    
    return ''.join(html_parts)


def send_email(subject, recipient=None):
    """Send email with HTML content - supports multiple recipients"""
    # Ensure we're in app context (needed for scheduler jobs)
    # Check if we're in app context by trying to access current_app
    try:
        from flask import current_app
        current_app._get_current_object()  # This will raise RuntimeError if no context
    except RuntimeError:
        # Not in app context, need to wrap
        with app.app_context():
            return send_email(subject, recipient)
    
    server = None  # Initialize server variable for proper cleanup
    try:
        # Get email settings from database
        settings = ScheduleSettings.query.first()
        
        # Use database settings if available, otherwise fallback to config.py
        if settings and settings.sender_email:
            sender_email = settings.sender_email
            sender_password = settings.sender_password
            smtp_server = settings.smtp_server
            smtp_port = settings.smtp_port
        else:
            # Fallback to config.py - use .get() to avoid KeyError
            sender_email = EMAIL_CONFIG.get('email', '')
            sender_password = EMAIL_CONFIG.get('password', '')
            smtp_server = EMAIL_CONFIG.get('smtp_server', 'smtp.gmail.com')
            smtp_port = EMAIL_CONFIG.get('smtp_port', 587)
        
        # VALIDATION: Check email settings are configured
        if not sender_email or not sender_password:
            print(Fore.RED + "Error: Email sender credentials not configured")
            return False
        
        if not smtp_server or not smtp_port:
            print(Fore.RED + "Error: SMTP server settings not configured")
            return False
        
        if recipient is None:
            recipient = EMAIL_CONFIG.get('recipient', '')
        
        # Parse multiple email addresses (comma or semicolon separated)
        if isinstance(recipient, str):
            # Split by comma or semicolon and clean up whitespace
            recipients = [email.strip() for email in recipient.replace(';', ',').split(',') if email.strip()]
        else:
            recipients = recipient
        
        # VALIDATION: Check we have at least one valid recipient
        if not recipients:
            print(Fore.RED + "Error: No valid recipient email addresses provided")
            return False
            
        # Get occurrences and report date from the subject line
        # Extract date from subject like "Daily Report - 2025-10-21"
        try:
            report_date_str = subject.split(' - ')[1]
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        except:
            report_date = datetime.now().date()
        
        # Get occurrences for the report date - convert date to datetime for proper comparison
        try:
            start_datetime = datetime.combine(report_date, datetime.min.time())
            end_datetime = datetime.combine(report_date + timedelta(days=1), datetime.min.time())
            occurrences = DailyOccurrence.query.filter(
                DailyOccurrence.timestamp >= start_datetime,
                DailyOccurrence.timestamp < end_datetime
            ).all()
        except Exception as db_error:
            print(Fore.RED + f"Database error retrieving occurrences: {db_error}")
            return False
        
        # Generate HTML content
        try:
            html_body = generate_email_html(occurrences, report_date)
        except Exception as html_error:
            print(Fore.RED + f"Error generating email HTML: {html_error}")
            traceback.print_exc()
            return False
        
        # Build email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)  # Display all recipients in header
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email to all recipients with timeout to prevent hanging
        # Set timeout to 30 seconds for connection and operations
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        
        try:
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipients, text)  # Send to list of recipients
            
            # Close connection gracefully
            try:
                server.quit()
                server = None  # Mark as closed only after successful quit
            except Exception as quit_error:
                # If quit() fails, let finally block handle cleanup
                print(Fore.YELLOW + f"Warning: Error during email server quit: {quit_error}")
            
            print(Fore.GREEN + f"Email sent successfully from {sender_email} to: {', '.join(recipients)}")
            return True
        except Exception as smtp_error:
            # If any SMTP operation fails, ensure we don't leave connection open
            # The finally block will handle cleanup
            raise  # Re-raise to be caught by outer except block
        
    except smtplib.SMTPAuthenticationError as e:
        print(Fore.RED + f"Authentication error: Invalid email or password - {e}")
        return False
    except smtplib.SMTPException as e:
        print(Fore.RED + f"SMTP error sending email: {e}")
        return False
    except socket.timeout as e:
        print(Fore.RED + f"Timeout error: SMTP server did not respond within 30 seconds - {e}")
        return False
    except (smtplib.SMTPServerDisconnected, ConnectionError, OSError) as e:
        print(Fore.RED + f"Connection error sending email: {e}")
        return False
    except KeyError as e:
        print(Fore.RED + f"Configuration error: Missing email config key - {e}")
        return False
    except Exception as e:
        print(Fore.RED + f"Unexpected error sending email: {e}")
        traceback.print_exc()  # Print full traceback for debugging
        return False
    finally:
        # Ensure connection is always closed, even if an error occurred
        # This handles cases where connection was established but operations failed
        if server is not None:
            try:
                # Check if connection is still open before trying to close
                try:
                    server.quit()  # Try graceful close first
                except (smtplib.SMTPServerDisconnected, AttributeError):
                    # Connection already closed or in invalid state, try force close
                    try:
                        server.close()  # Force close if quit() fails
                    except (AttributeError, OSError):
                        pass  # Connection already closed or invalid
            except Exception as cleanup_error:
                # Last resort: try to close if possible, ignore all errors
                try:
                    if hasattr(server, 'close'):
                        server.close()
                except:
                    pass  # Ignore all errors during final cleanup
            finally:
                server = None  # Always mark as closed after cleanup attempt

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/daily-occurrences', methods=['GET', 'POST'])
def daily_occurrences():
    if request.method == 'POST':
        try:
            data = request.json
            occurrence = DailyOccurrence(
                time=data['time'],
                flat_number=data['flat_number'],
                reported_by=data['reported_by'],
                description=data['description']
            )
            db.session.add(occurrence)
            db.session.commit()
            return jsonify({'success': True, 'id': occurrence.id})
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error creating daily occurrence: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request - return today's occurrences
    try:
        today = datetime.now().date()
        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= today,
            DailyOccurrence.timestamp < tomorrow
        ).order_by(DailyOccurrence.timestamp.desc()).all()
        
        return jsonify([{
            'id': o.id,
            'time': o.time,
            'flat_number': o.flat_number,
            'reported_by': o.reported_by,
            'description': o.description,
            'timestamp': o.timestamp.isoformat()
        } for o in occurrences])
    except Exception as e:
        print(Fore.RED + f"Error fetching daily occurrences: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-occurrences/<int:occurrence_id>', methods=['DELETE'])
def delete_daily_occurrence(occurrence_id):
    occurrence = DailyOccurrence.query.get(occurrence_id)
    if occurrence:
        # Get user name from request
        data = request.get_json() or {}
        user_name = data.get('user_name', 'Unknown')
        
        # Log the deletion
        description = f"Deleted occurrence: {occurrence.time} - Flat {occurrence.flat_number} - {occurrence.description[:50]}..."
        log_activity(user_name, 'delete', 'occurrence', description, occurrence_id, request.remote_addr)
        
        db.session.delete(occurrence)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Occurrence not found'}), 404

@app.route('/api/staff-rota', methods=['GET', 'POST'])
def staff_rota():
    if request.method == 'POST':
        try:
            data = request.json
            rota = StaffRota(
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                staff_name=data['staff_name'],
                shift_start=data.get('shift_start'),
                shift_end=data.get('shift_end'),
                status=data.get('status', 'working'),
                notes=data.get('notes')
            )
            db.session.add(rota)
            db.session.commit()
            return jsonify({'success': True, 'id': rota.id})
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error creating staff rota entry: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request
    start_date = request.args.get('start_date', datetime.now().date().isoformat())
    end_date = request.args.get('end_date', (datetime.now() + timedelta(days=30)).date().isoformat())
    
    rotas = StaffRota.query.filter(
        StaffRota.date >= start_date,
        StaffRota.date <= end_date
    ).order_by(StaffRota.date).all()
    
    # Build response with working day calculation
    # Optimize: Load all staff members once to avoid N+1 queries
    all_staff_members = {s.name: s for s in StaffMember.query.all()}
    
    result = []
    for r in rotas:
        # Get staff member info from pre-loaded dict
        staff = all_staff_members.get(r.staff_name)
        is_working_day = True  # Default to true if we can't determine
        
        if staff:
            # Calculate rotation for this date
            pattern_key = get_rotation_key(r.date)
            is_scheduled_off = False
            
            if staff.shift in [1, 2]:
                # Day shift rotation
                colors_off = normalize_colors(DAY_SHIFT_ROTATION_PATTERN.get(pattern_key))
                if colors_off and staff.color in colors_off:
                    is_scheduled_off = True
                    
            elif staff.shift == 3:
                # Night shift rotation
                night_colors_off = normalize_colors(NIGHT_SHIFT_ROTATION_PATTERN.get(pattern_key))
                if night_colors_off and staff.color in night_colors_off:
                    is_scheduled_off = True
            
            is_working_day = not is_scheduled_off
        
        result.append({
            'id': r.id,
            'date': r.date.isoformat(),
            'staff_name': r.staff_name,
            'shift_start': r.shift_start,
            'shift_end': r.shift_end,
            'status': r.status,
            'notes': r.notes,
            'is_working_day': is_working_day
        })
    
    return jsonify(result)

@app.route('/api/staff-rota/<int:rota_id>', methods=['DELETE'])
def delete_staff_rota(rota_id):
    rota = StaffRota.query.get(rota_id)
    if rota:
        # Get user name from request
        data = request.get_json() or {}
        user_name = data.get('user_name', 'Unknown')
        
        # Log the deletion
        description = f"Deleted staff rota: {rota.staff_name} - {rota.date} - {rota.status}"
        log_activity(user_name, 'delete', 'staff_rota', description, rota_id, request.remote_addr)
        
        db.session.delete(rota)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Rota entry not found'}), 404

@app.route('/api/staff-rota-range', methods=['POST'])
def staff_rota_range():
    """Add leave for a date range (creates one entry per day, only counting working days)"""
    data = request.json
    staff_name = data['staff_name']
    date_from = datetime.strptime(data['date_from'], '%Y-%m-%d').date()
    date_to = datetime.strptime(data['date_to'], '%Y-%m-%d').date()
    status = data.get('status', 'holiday')
    notes = data.get('notes', '')
    
    # Validate date range
    if date_to < date_from:
        return jsonify({'success': False, 'error': 'To date must be after or equal to from date'}), 400
    
    # Get staff member to determine their shift and color
    staff = StaffMember.query.filter_by(name=staff_name).first()
    if not staff:
        return jsonify({'success': False, 'error': 'Staff member not found'}), 404
    
    # Create entries for each day in range
    current_date = date_from
    days_added = 0
    working_days_count = 0  # Only count days they were supposed to work
    
    while current_date <= date_to:
        # Calculate if this person was scheduled to work on this day
        pattern_key = get_rotation_key(current_date)
        is_scheduled_off = False
        
        if staff.shift in [1, 2]:
            # Day shift rotation
            colors_off = normalize_colors(DAY_SHIFT_ROTATION_PATTERN.get(pattern_key))
            if colors_off and staff.color in colors_off:
                is_scheduled_off = True
                
        elif staff.shift == 3:
            # Night shift rotation
            night_colors_off = normalize_colors(NIGHT_SHIFT_ROTATION_PATTERN.get(pattern_key))
            if night_colors_off and staff.color in night_colors_off:
                is_scheduled_off = True
        
        # Check if entry already exists for this date
        existing = StaffRota.query.filter_by(
            date=current_date,
            staff_name=staff_name,
            status=status
        ).first()
        
        if not existing:
            rota = StaffRota(
                date=current_date,
                staff_name=staff_name,
                status=status,
                notes=notes
            )
            db.session.add(rota)
            days_added += 1
            
            # Only count as a working day if they were scheduled to work
            if not is_scheduled_off:
                working_days_count += 1
        else:
            # If entry exists and they were scheduled to work, still count it
            if not is_scheduled_off:
                working_days_count += 1
        
        current_date += timedelta(days=1)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'days_added': days_added,
        'working_days_count': working_days_count,
        'message': f'Added {days_added} day(s) of {status} ({working_days_count} working day(s))'
    })

@app.route('/api/staff-schedule/<int:staff_id>', methods=['GET'])
def staff_schedule(staff_id):
    """Get individual staff member's schedule for a date range"""
    # Get staff member
    staff = StaffMember.query.get(staff_id)
    if not staff:
        return jsonify({'success': False, 'error': 'Staff member not found'}), 404
    
    # Get date range parameters
    start_date_str = request.args.get('start_date', datetime.now().date().isoformat())
    end_date_str = request.args.get('end_date', (datetime.now() + timedelta(days=30)).date().isoformat())
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get porter groups for rotation calculation
    porter_groups, all_staff = get_porter_groups()
    
    # Rotating shift schedule based on 4-week cycle
    # Week 1 & 3: Shift 1 = Late (2pm-10pm), Shift 2 = Early (7am-2pm)
    # Week 2 & 4: Shift 1 = Early (7am-2pm), Shift 2 = Late (2pm-10pm)
    # Night shift is always the same (10pm-7am)
    shift_schedule = {
        0: {'shift1_start': '14:00', 'shift1_end': '22:00', 'shift2_start': '07:00', 'shift2_end': '14:00'},  # Week 1
        1: {'shift1_start': '07:00', 'shift1_end': '14:00', 'shift2_start': '14:00', 'shift2_end': '22:00'},  # Week 2
        2: {'shift1_start': '14:00', 'shift1_end': '22:00', 'shift2_start': '07:00', 'shift2_end': '14:00'},  # Week 3
        3: {'shift1_start': '07:00', 'shift1_end': '14:00', 'shift2_start': '14:00', 'shift2_end': '22:00'}   # Week 4
    }
    
    # Night shift is constant
    night_shift_times = {'start': '22:00', 'end': '07:00'}
    
    # Get manual entries from StaffRota for this staff member
    manual_entries = StaffRota.query.filter(
        StaffRota.staff_name == staff.name,
        StaffRota.date >= start_date,
        StaffRota.date <= end_date
    ).all()
    
    # Create a dictionary of manual entries by date
    manual_by_date = {entry.date: entry for entry in manual_entries}
    
    # Build schedule for date range
    schedule = []
    current = start_date
    
    while current <= end_date:
        # Calculate rotation for this date
        pattern_key = get_rotation_key(current)
        week_in_cycle = pattern_key[0]
        
        # Get shift times based on week in cycle
        week_schedule = shift_schedule.get(week_in_cycle, shift_schedule[0])
        
        if staff.shift == 1:
            default_start = week_schedule['shift1_start']
            default_end = week_schedule['shift1_end']
        elif staff.shift == 2:
            default_start = week_schedule['shift2_start']
            default_end = week_schedule['shift2_end']
        else:  # shift 3 (night)
            default_start = night_shift_times['start']
            default_end = night_shift_times['end']
        
        # Check if there's a manual entry for this date
        if current in manual_by_date:
            entry = manual_by_date[current]
            schedule.append({
                'date': current.isoformat(),
                'day_of_week': current.strftime('%A'),
                'status': entry.status,
                'shift_start': entry.shift_start or default_start,
                'shift_end': entry.shift_end or default_end,
                'notes': entry.notes or '',
                'is_manual': True
            })
        else:
            # Use rotation schedule
            is_off = False
            
            if staff.shift in [1, 2]:
                # Day shift rotation
                colors_off = normalize_colors(DAY_SHIFT_ROTATION_PATTERN.get(pattern_key))
                if colors_off and staff.color in colors_off:
                    is_off = True
                    
            elif staff.shift == 3:
                # Night shift rotation
                night_colors_off = normalize_colors(NIGHT_SHIFT_ROTATION_PATTERN.get(pattern_key))
                if night_colors_off and staff.color in night_colors_off:
                    is_off = True
            
            schedule.append({
                'date': current.isoformat(),
                'day_of_week': current.strftime('%A'),
                'status': 'off' if is_off else 'working',
                'shift_start': default_start if not is_off else '',
                'shift_end': default_end if not is_off else '',
                'notes': '',
                'is_manual': False
            })
        
        current += timedelta(days=1)
    
    return jsonify({
        'success': True,
        'staff': {
            'id': staff.id,
            'name': staff.name,
            'shift': staff.shift,
            'color': staff.color
        },
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'schedule': schedule
    })

@app.route('/api/porter-rota', methods=['GET'])
def porter_rota():
    """Get porter rota schedule based on 4-week rotation pattern"""
    start_date = request.args.get('start_date', datetime.now().date().isoformat())
    end_date = request.args.get('end_date', (datetime.now() + timedelta(days=365)).date().isoformat())
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get staff members from database
    porter_groups, all_staff_by_shift = get_porter_groups()
    
    # Shift rotation: Alternating pattern - Weeks 1&3 have Late, Weeks 2&4 have Early for Shift 1
    # Week 1: Shift 1 = Late (2pm-10pm), Shift 2 = Early (7am-2pm), Night Shift = (10pm-7am)
    # Week 2: Shift 1 = Early (7am-2pm), Shift 2 = Late (2pm-10pm), Night Shift = (10pm-7am)
    # Week 3: Shift 1 = Late (2pm-10pm), Shift 2 = Early (7am-2pm), Night Shift = (10pm-7am)
    # Week 4: Shift 1 = Early (7am-2pm), Shift 2 = Late (2pm-10pm), Night Shift = (10pm-7am)
    shift_schedule = {
        1: {'shift1': 'Late (2pm-10pm)', 'shift2': 'Early (7am-2pm)', 'shift3': 'Night (10pm-7am)'},
        2: {'shift1': 'Early (7am-2pm)', 'shift2': 'Late (2pm-10pm)', 'shift3': 'Night (10pm-7am)'},
        3: {'shift1': 'Late (2pm-10pm)', 'shift2': 'Early (7am-2pm)', 'shift3': 'Night (10pm-7am)'},
        4: {'shift1': 'Early (7am-2pm)', 'shift2': 'Late (2pm-10pm)', 'shift3': 'Night (10pm-7am)'}
    }
    
    schedule = []
    current = start
    while current <= end:
        # Calculate which week in the 4-week cycle
        pattern_key = get_rotation_key(current)
        week_in_cycle = pattern_key[0]
        week_number = week_in_cycle + 1
        
        # Get which color group(s) are off
        colors_off = normalize_colors(DAY_SHIFT_ROTATION_PATTERN.get(pattern_key))
        
        # Build staff off list with shift information
        staff_off_list = []
        
        # Day shifts (1 & 2)
        if colors_off:
            for color in colors_off:
                # Only apply rotation to day shift colors (red, yellow, green, blue)
                if color in ['red', 'yellow', 'green', 'blue'] and color in porter_groups:
                    if 'shift1' in porter_groups[color]:
                        staff_off_list.append({
                            'name': porter_groups[color]['shift1'],
                            'shift': 1,
                            'color': color
                        })
                    if 'shift2' in porter_groups[color]:
                        staff_off_list.append({
                            'name': porter_groups[color]['shift2'],
                            'shift': 2,
                            'color': color
                        })
        
        # Night shift (shift 3) rotation pattern
        night_colors_off = normalize_colors(NIGHT_SHIFT_ROTATION_PATTERN.get(pattern_key))
        
        # Add night shift staff who are off
        if night_colors_off:
            for color in night_colors_off:
                if color in porter_groups:
                    if 'shift3' in porter_groups[color]:
                        staff_off_list.append({
                            'name': porter_groups[color]['shift3'],
                            'shift': 3,
                            'color': color
                        })
        
        # For display purposes, join colors if multiple
        color_off_display = ', '.join(colors_off) if colors_off else None
        
        # Get shift times for this week
        shift_times = shift_schedule.get(week_number, {})
        
        schedule.append({
            'date': current.isoformat(),
            'day_name': current.strftime('%A'),
            'week_in_cycle': week_number,
            'color_off': color_off_display,
            'staff_off': staff_off_list,
            'shift1_time': shift_times.get('shift1', ''),
            'shift2_time': shift_times.get('shift2', ''),
            'shift3_time': shift_times.get('shift3', ''),
            'is_today': current == datetime.now().date()
        })
        
        current += timedelta(days=1)
    
    return jsonify(schedule)

@app.route('/api/cctv-faults', methods=['GET', 'POST'])
def cctv_faults():
    if request.method == 'POST':
        try:
            data = request.json
            # Build location string from components for backwards compatibility
            location_parts = []
            if data.get('flat_number'):
                location_parts.append(f"Flat {data['flat_number']}")
            if data.get('block_number'):
                location_parts.append(f"Block {data['block_number']}")
            if data.get('floor_number'):
                location_parts.append(f"Floor {data['floor_number']}")
            location_string = ' | '.join(location_parts) if location_parts else data.get('location', '')
            
            fault = CCTVFault(
                fault_type=data['fault_type'],
                flat_number=data.get('flat_number', ''),
                block_number=data.get('block_number', ''),
                floor_number=data.get('floor_number', ''),
                location=location_string,
                description=data['description'],
                contact_details=data.get('contact_details', ''),
                additional_notes=data.get('additional_notes', ''),
                status=data.get('status', 'open')
            )
            db.session.add(fault)
            db.session.commit()
            return jsonify({'success': True, 'id': fault.id})
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error creating CCTV fault: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request
    faults = CCTVFault.query.order_by(CCTVFault.timestamp.desc()).all()
    return jsonify([{
        'id': f.id,
        'timestamp': f.timestamp.isoformat(),
        'fault_type': f.fault_type,
        'flat_number': f.flat_number,
        'block_number': f.block_number,
        'floor_number': f.floor_number,
        'location': f.location,
        'description': f.description,
        'contact_details': f.contact_details,
        'additional_notes': f.additional_notes,
        'status': f.status,
        'resolved_date': f.resolved_date.isoformat() if f.resolved_date else None
    } for f in faults])

@app.route('/api/water-temperature', methods=['GET', 'POST'])
def water_temperature():
    if request.method == 'POST':
        try:
            data = request.json
            # Validate temperature input
            if not data.get('temperature') or data['temperature'] == '':
                return jsonify({'success': False, 'error': 'Temperature is required'}), 400
            
            try:
                temperature_value = float(data['temperature'])
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid temperature value'}), 400
            
            temp = WaterTemperature(
                temperature=temperature_value,
                time_recorded=data['time']
            )
            db.session.add(temp)
            db.session.commit()
            return jsonify({'success': True, 'id': temp.id})
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error creating water temperature entry: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request with optional date range parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from and date_to:
        # Custom date range
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            temps = WaterTemperature.query.filter(
                WaterTemperature.timestamp >= start_datetime,
                WaterTemperature.timestamp <= end_datetime
            ).order_by(WaterTemperature.timestamp.desc()).all()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    else:
        # Default: return last 24 hours
        since = datetime.now() - timedelta(hours=24)
        temps = WaterTemperature.query.filter(
            WaterTemperature.timestamp >= since
        ).order_by(WaterTemperature.timestamp.desc()).all()
    
    return jsonify([{
        'id': t.id,
        'timestamp': t.timestamp.isoformat(),
        'temperature': t.temperature,
        'time_recorded': t.time_recorded
    } for t in temps])

@app.route('/api/water-temperature/<int:temp_id>', methods=['DELETE'])
def delete_water_temperature(temp_id):
    """Delete a water temperature record"""
    temp = WaterTemperature.query.get(temp_id)
    if not temp:
        return jsonify({'success': False, 'error': 'Temperature record not found'}), 404
    
    db.session.delete(temp)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/update-fault-status', methods=['POST'])
def update_fault_status():
    data = request.json
    fault = CCTVFault.query.get(data['id'])
    if fault:
        fault.status = data['status']
        if data['status'] == 'closed':
            fault.resolved_date = datetime.now()
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/delete-fault/<int:fault_id>', methods=['DELETE'])
def delete_fault(fault_id):
    fault = CCTVFault.query.get(fault_id)
    if fault:
        # Only allow deletion of closed faults
        if fault.status == 'closed':
            db.session.delete(fault)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Only closed faults can be deleted'})
    return jsonify({'success': False, 'error': 'Fault not found'})

@app.route('/api/test-export', methods=['POST'])
def test_export():
    """Test function to export PDF and CSV without sending email"""
    try:
        # Get today's occurrences
        today = datetime.now().date()
        next_day = today + timedelta(days=1)
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= today,
            DailyOccurrence.timestamp < next_day,
            DailyOccurrence.sent == False
        ).all()
        
        # Generate PDF regardless of whether there are occurrences
        pdf_path = generate_daily_pdf(occurrences, today)
        
        # Generate CSV backup for safety
        csv_path = generate_daily_csv(occurrences, today)
        
        if not occurrences or len(occurrences) == 0:
            return jsonify({
                'success': True, 
                'message': f'Reports exported successfully:\nPDF: {pdf_path}\nCSV: {csv_path}\n(No occurrences recorded)',
                'count': 0
            })
        
        return jsonify({
            'success': True, 
            'message': f'Reports exported successfully:\nPDF: {pdf_path}\nCSV: {csv_path}',
            'count': len(occurrences)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reprint-report', methods=['POST'])
def reprint_report():
    """Reprint a report for a specific date (from Settings tab)"""
    try:
        data = request.json
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'error': 'Date parameter required'}), 400
        
        # Parse the date
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        next_day = report_date + timedelta(days=1)
        
        # Get occurrences for the report date
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= report_date,
            DailyOccurrence.timestamp < next_day
        ).order_by(DailyOccurrence.time).all()
        
        # Get water temperatures for the report date
        today_start = datetime.combine(report_date, datetime.min.time())
        today_end = datetime.combine(report_date, datetime.max.time())
        water_temps = WaterTemperature.query.filter(
            WaterTemperature.timestamp >= today_start,
            WaterTemperature.timestamp <= today_end
        ).all()
        
        # Generate the PDF
        pdf_path = generate_daily_pdf(occurrences, report_date)
        
        # Get the filename
        pdf_filename = os.path.basename(pdf_path)
        
        print(Fore.GREEN + f"✓ Reprinted report for {report_date}: {pdf_filename}")
        print(Fore.CYAN + f"  - Occurrences: {len(occurrences)}")
        print(Fore.CYAN + f"  - Water temps: {len(water_temps)}")
        
        return jsonify({
            'success': True,
            'message': 'PDF report generated successfully',
            'pdf_path': pdf_path,
            'pdf_filename': pdf_filename,
            'occurrences_count': len(occurrences),
            'water_temps_count': len(water_temps)
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        print(Fore.RED + f"Error reprinting report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-email', methods=['POST'])
def test_email():
    """Send a test email with today's data"""
    try:
        # Get settings
        settings = ScheduleSettings.query.first()
        if not settings or not settings.email_enabled:
            return jsonify({
                'success': False, 
                'error': 'Email sending is disabled. Please enable it in settings first.'
            })
        
        # Verify email settings are configured
        if not settings.sender_email or not settings.sender_password:
            return jsonify({
                'success': False,
                'error': 'Sender email or password not configured. Please check Settings > Email Configuration.'
            })
        
        if not settings.recipient_email:
            return jsonify({
                'success': False,
                'error': 'Recipient email not configured. Please enter a recipient email address.'
            })
        
        print(Fore.CYAN + Style.BRIGHT + f"\n{'='*50}")
        print(Fore.CYAN + Style.BRIGHT + f"SENDING TEST EMAIL")
        print(Fore.CYAN + Style.BRIGHT + f"{'='*50}")
        print(Fore.CYAN + f"From: {settings.sender_email}")
        print(Fore.CYAN + f"To: {settings.recipient_email}")
        print(Fore.CYAN + f"SMTP Server: {settings.smtp_server}:{settings.smtp_port}")
        
        # Get today's occurrences
        today = datetime.now().date()
        next_day = today + timedelta(days=1)
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= today,
            DailyOccurrence.timestamp < next_day,
            DailyOccurrence.sent == False
        ).all()
        
        print(Fore.CYAN + f"Occurrences found: {len(occurrences)}")
        
        # Generate PDF and CSV for local backup (not sent via email)
        pdf_path = generate_daily_pdf(occurrences, today)
        csv_path = generate_daily_csv(occurrences, today)
        print(Fore.CYAN + f"PDF generated for local backup: {pdf_path}")
        print(Fore.CYAN + f"CSV generated for local backup: {csv_path}")
        
        # Send test email with HTML styling
        print(Fore.CYAN + f"Attempting to send HTML email...")
        email_sent = send_email(
            f"TEST - Daily Report - {today}", 
            settings.recipient_email
        )
        
        if email_sent:
            occurrence_count = len(occurrences) if occurrences else 0
            print(Fore.GREEN + f"✓ HTML email sent successfully!")
            print(Fore.CYAN + Style.BRIGHT + f"{'='*50}\n")
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {settings.recipient_email}!\n\nEmail includes:\n- Beautiful HTML styling\n- {occurrence_count} occurrence(s)\n- Staff schedule in 3 columns\n- Water temperature readings\n\nCheck your inbox!',
                'count': occurrence_count
            })
        else:
            print(Fore.RED + f"✗ Email failed to send!")
            print(Fore.CYAN + Style.BRIGHT + f"{'='*50}\n")
            return jsonify({
                'success': False,
                'error': 'Failed to send test email. Check console for details. Common issues:\n- Wrong email/password\n- Gmail: Need App Password, not regular password\n- Firewall blocking SMTP\n- Check spam folder'
            })
            
    except Exception as e:
        print(Fore.RED + f"✗ ERROR: {str(e)}")
        print(Fore.CYAN + Style.BRIGHT + f"{'='*50}\n")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error sending test email: {str(e)}'})

@app.route('/api/test-clear', methods=['POST'])
def test_clear():
    """Test function to clear today's diary entries"""
    try:
        # Get today's occurrences
        today = datetime.now().date()
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= today
        ).all()
        
        count = len(occurrences)
        
        # Delete all today's occurrences
        for occurrence in occurrences:
            db.session.delete(occurrence)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Cleared {count} diary entries'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backup-to-gdrive', methods=['POST'])
def manual_backup_to_gdrive():
    """Manually trigger a Google Drive backup"""
    try:
        print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "MANUAL GOOGLE DRIVE BACKUP")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        
        success = backup_database_to_gdrive()
        
        print(Fore.CYAN + Style.BRIGHT + "=" * 50 + "\n")
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Database successfully backed up to Google Drive!\n\nFile: diary_latest.db\nFolder: Diary_Backups\n\nOnly the latest backup is kept in Google Drive.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Backup failed. Check console for details.\n\nCommon issues:\n- service_account.json file missing\n- Invalid credentials\n- No internet connection\n- Google Drive API not enabled'
            })
    except Exception as e:
        print(Fore.RED + f"✗ Error in manual backup: {str(e)}")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50 + "\n")
        return jsonify({
            'success': False,
            'error': f'Error triggering backup: {str(e)}'
        })

def log_settings_access(staff_name, action, success, ip_address=None):
    """Log all settings access attempts to a file"""
    try:
        log_dir = os.path.join(BASE_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'settings_access.log')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'SUCCESS' if success else 'FAILED'
        ip_info = f" from {ip_address}" if ip_address else ""
        
        log_entry = f"[{timestamp}] {status} - {staff_name} - {action}{ip_info}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(Fore.CYAN + f"Settings access logged: {log_entry.strip()}")
    except Exception as e:
        print(Fore.RED + f"Error logging settings access: {e}")

def log_activity(user_name, action_type, entity_type, description, entity_id=None, ip_address=None):
    """Log user activity to database"""
    try:
        activity = ActivityLog(
            user_name=user_name,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            description=description,
            ip_address=ip_address
        )
        db.session.add(activity)
        db.session.commit()
        print(Fore.CYAN + f"Activity logged: {user_name} - {description}")
    except Exception as e:
        print(Fore.RED + f"Error logging activity: {e}")
        db.session.rollback()

def log_shutdown(reason="Normal shutdown"):
    """Log application shutdown to a text file"""
    try:
        log_dir = os.path.join(BASE_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'shutdown_log.txt')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] APPLICATION STOPPED - Reason: {reason}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(Fore.CYAN + f"Shutdown logged: {log_entry.strip()}")
    except Exception as e:
        print(Fore.RED + f"Error logging shutdown: {e}")

def log_startup():
    """Log application startup to a text file"""
    try:
        log_dir = os.path.join(BASE_PATH, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'shutdown_log.txt')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] APPLICATION STARTED\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(Fore.GREEN + f"Startup logged: {log_entry.strip()}")
    except Exception as e:
        print(Fore.RED + f"Error logging startup: {e}")

@app.route('/api/verify-settings-pin', methods=['POST'])
@rate_limit(max_attempts=5, window=300)
def verify_settings_pin():
    """Verify PIN for settings access - checks all shift leaders"""
    try:
        data = request.json
        pin = data.get('pin')
        
        if not pin:
            return jsonify({'success': False, 'error': 'PIN required'})
        
        # Check all active shift leaders for matching PIN using secure comparison
        all_leaders = ShiftLeader.query.filter_by(active=True).all()
        
        for shift_leader in all_leaders:
            if verify_pin_hash(pin, shift_leader.pin):
                # Success - found matching PIN
                shift_leader.last_login = datetime.now()
                db.session.commit()
                
                log_settings_access(shift_leader.name, 'Settings Access Granted', True, request.remote_addr)
                return jsonify({
                    'success': True,
                    'name': shift_leader.name,
                    'is_super_user': shift_leader.is_super_user,
                    'user_type': 'Super User' if shift_leader.is_super_user else 'Shift Leader'
                })
        
        # No matching PIN found
        log_settings_access('Unknown User', 'Settings Access Attempt - Invalid PIN', False, request.remote_addr)
        return jsonify({'success': False, 'error': 'Invalid PIN'})
        
    except Exception as e:
        print(Fore.RED + f"Error verifying settings PIN: {e}")
        log_settings_access('Unknown', f'Settings Access Error: {str(e)}', False, request.remote_addr)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/verify-leave-pin', methods=['POST'])
@rate_limit(max_attempts=5, window=300)
def verify_leave_pin():
    """Verify PIN for leave/overtime access - only super users allowed"""
    try:
        data = request.json
        pin = data.get('pin')
        
        if not pin:
            return jsonify({'success': False, 'error': 'PIN required'})
        
        # Only check super users
        super_users = ShiftLeader.query.filter(
            ShiftLeader.active == True,
            ShiftLeader.is_super_user == True
        ).all()
        
        for shift_leader in super_users:
            if verify_pin_hash(pin, shift_leader.pin):
                # Success - found matching PIN for super user
                shift_leader.last_login = datetime.now()
                db.session.commit()
                
                log_settings_access(shift_leader.name, 'Leave/Overtime Access Granted', True, request.remote_addr)
                return jsonify({
                    'success': True,
                    'name': shift_leader.name,
                    'is_super_user': True,
                    'user_type': 'Super User'
                })
        
        # No matching PIN found or not authorized
        log_settings_access('Unknown User', 'Leave/Overtime Access Attempt - Invalid/Unauthorized PIN', False, request.remote_addr)
        return jsonify({'success': False, 'error': 'Invalid PIN or unauthorized access. Only Super Users can access this section.'})
        
    except Exception as e:
        print(Fore.RED + f"Error verifying leave PIN: {e}")
        log_settings_access('Unknown', f'Leave/Overtime Access Error: {str(e)}', False, request.remote_addr)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/overtime', methods=['GET', 'POST'])
def overtime():
    """Handle overtime entries - GET: list all, POST: create new (super user only)"""
    if request.method == 'POST':
        try:
            # Verify super user authentication
            pin = request.headers.get('X-Super-User-PIN')
            if not pin:
                return jsonify({'success': False, 'error': 'Super user PIN required'}), 401
            
            # Verify PIN is for super user using secure comparison
            super_users = ShiftLeader.query.filter(
                ShiftLeader.active == True,
                ShiftLeader.is_super_user == True
            ).all()
            
            super_user = None
            for leader in super_users:
                if verify_pin_hash(pin, leader.pin):
                    super_user = leader
                    break
            
            if not super_user:
                return jsonify({'success': False, 'error': 'Unauthorized. Super user access required.'}), 403
            
            data = request.json
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Validate required fields
            if 'staff_name' not in data or not data.get('staff_name'):
                return jsonify({'success': False, 'error': 'Staff name is required'}), 400
            
            if 'date' not in data or not data.get('date'):
                return jsonify({'success': False, 'error': 'Date is required'}), 400
            
            if 'hours' not in data or data.get('hours') is None or data.get('hours') == '':
                return jsonify({'success': False, 'error': 'Hours is required'}), 400
            
            # Validate and parse date
            try:
                date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                return jsonify({'success': False, 'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'}), 400
            
            # Validate and parse hours
            try:
                hours_value = float(data['hours'])
                if hours_value < 0:
                    return jsonify({'success': False, 'error': 'Hours must be a positive number'}), 400
            except (ValueError, TypeError) as e:
                return jsonify({'success': False, 'error': f'Invalid hours value. Must be a number: {str(e)}'}), 400
            
            # Validate staff exists and is active
            staff = StaffMember.query.filter_by(
                name=data['staff_name'],
                active=True
            ).first()
            
            if not staff:
                return jsonify({
                    'success': False,
                    'error': f'Staff member "{data["staff_name"]}" not found or inactive'
                }), 400
            
            # Create overtime entry
            overtime_entry = Overtime(
                staff_name=data['staff_name'],
                date=date_obj,
                hours=hours_value,
                description=data.get('description', ''),
                created_by=super_user.name
            )
            db.session.add(overtime_entry)
            db.session.commit()
            
            return jsonify({'success': True, 'id': overtime_entry.id})
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            print(Fore.RED + f"Error saving overtime entry: {error_msg}")
            return jsonify({'success': False, 'error': f'Error saving overtime entry: {error_msg}'}), 500
    
    # GET request - filter by date range and staff
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    staff_name = request.args.get('staff_name')
    
    query = Overtime.query
    
    if start_date:
        query = query.filter(Overtime.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Overtime.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if staff_name:
        query = query.filter(Overtime.staff_name == staff_name)
    
    overtime_list = query.order_by(Overtime.date.desc(), Overtime.id.desc()).all()
    
    return jsonify({
        'success': True,
        'overtime': [{
            'id': ot.id,
            'staff_name': ot.staff_name,
            'date': ot.date.isoformat(),
            'hours': ot.hours,
            'description': ot.description,
            'created_by': ot.created_by,
            'created_date': ot.created_date.isoformat() if ot.created_date else None
        } for ot in overtime_list]
    })

@app.route('/api/overtime/<int:overtime_id>', methods=['PUT', 'DELETE'])
def overtime_entry(overtime_id):
    """Update or delete overtime entry (super user only)"""
    # Verify super user authentication
    pin = request.headers.get('X-Super-User-PIN')
    if not pin:
        return jsonify({'success': False, 'error': 'Super user PIN required'}), 401
    
    # Verify PIN is for super user using secure comparison
    super_users = ShiftLeader.query.filter(
        ShiftLeader.active == True,
        ShiftLeader.is_super_user == True
    ).all()
    
    super_user = None
    for leader in super_users:
        if verify_pin_hash(pin, leader.pin):
            super_user = leader
            break
    
    if not super_user:
        return jsonify({'success': False, 'error': 'Unauthorized. Super user access required.'}), 403
    
    overtime_entry = Overtime.query.get(overtime_id)
    if not overtime_entry:
        return jsonify({'success': False, 'error': 'Overtime entry not found'}), 404
    
    if request.method == 'DELETE':
        db.session.delete(overtime_entry)
        db.session.commit()
        return jsonify({'success': True})
    
    # PUT request - update
    data = request.json
    overtime_entry.staff_name = data.get('staff_name', overtime_entry.staff_name)
    if 'date' in data:
        overtime_entry.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    if 'hours' in data:
        overtime_entry.hours = float(data['hours'])
    if 'description' in data:
        overtime_entry.description = data['description']
    overtime_entry.updated_date = datetime.now()
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/settings-access-logs', methods=['GET'])
def get_settings_access_logs():
    """Get recent settings access logs"""
    try:
        log_file = os.path.join(BASE_PATH, 'logs', 'settings_access.log')
        
        if not os.path.exists(log_file):
            return jsonify({'logs': [], 'message': 'No access logs yet'})
        
        # Read last 50 lines from log file
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Get last 50 lines (most recent)
        recent_logs = lines[-50:] if len(lines) > 50 else lines
        recent_logs.reverse()  # Show newest first
        
        return jsonify({
            'logs': [line.strip() for line in recent_logs],
            'total_count': len(lines)
        })
        
    except Exception as e:
        print(Fore.RED + f"Error reading access logs: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activity-logs', methods=['GET'])
def get_activity_logs():
    """Get recent activity logs with filtering options"""
    try:
        # Get filter parameters
        days = request.args.get('days', 7, type=int)  # Default last 7 days
        user_name = request.args.get('user', None)
        action_type = request.args.get('action', None)
        limit = request.args.get('limit', 100, type=int)
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=days)
        
        # Build query
        query = ActivityLog.query.filter(ActivityLog.timestamp >= start_date)
        
        if user_name:
            query = query.filter(ActivityLog.user_name == user_name)
        if action_type:
            query = query.filter(ActivityLog.action_type == action_type)
        
        # Execute query
        logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'logs': [{
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_name': log.user_name,
                'action_type': log.action_type,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'description': log.description,
                'ip_address': log.ip_address
            } for log in logs],
            'total': len(logs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/schedule-settings', methods=['GET', 'POST'])
def schedule_settings():
    if request.method == 'POST':
        try:
            data = request.json
            settings = ScheduleSettings.query.first()
            
            if not settings:
                settings = ScheduleSettings()
                db.session.add(settings)
            
            settings.email_time = data['email_time']
            settings.email_enabled = data['email_enabled']
            settings.recipient_email = data['recipient_email']
            
            # Update sender email settings if provided
            if 'sender_email' in data:
                settings.sender_email = data['sender_email']
            if 'sender_password' in data:
                settings.sender_password = data['sender_password']
            if 'smtp_server' in data:
                settings.smtp_server = data['smtp_server']
            if 'smtp_port' in data:
                settings.smtp_port = int(data['smtp_port'])
                
            settings.last_updated = datetime.now()
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error updating schedule settings: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
        
        # Update the scheduler
        update_scheduler()
        
        # Log the settings change
        staff_name = data.get('staff_name', 'Unknown')
        log_settings_access(staff_name, 'Settings Modified', True, request.remote_addr)
        
        # Also log to activity log
        description = f"Modified email settings: Time={settings.email_time}, Enabled={settings.email_enabled}"
        log_activity(staff_name, 'modify', 'settings', description, None, request.remote_addr)
        
        return jsonify({'success': True})
    
    # GET request
    settings = ScheduleSettings.query.first()
    if not settings:
        # Create default settings with values from config.py
        settings = ScheduleSettings(
            sender_email=EMAIL_CONFIG.get('email', ''),
            sender_password=EMAIL_CONFIG.get('password', ''),
            smtp_server=EMAIL_CONFIG.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=EMAIL_CONFIG.get('smtp_port', 587)
        )
        db.session.add(settings)
        db.session.commit()
    
    return jsonify({
        'email_time': settings.email_time,
        'email_enabled': settings.email_enabled,
        'recipient_email': settings.recipient_email,
        'sender_email': settings.sender_email or '',
        'sender_password': settings.sender_password or '',
        'smtp_server': settings.smtp_server or 'smtp.gmail.com',
        'smtp_port': settings.smtp_port or 587,
        'last_updated': settings.last_updated.isoformat()
    })

@app.route('/api/email-logs', methods=['GET'])
def email_logs():
    """Get email history/logs"""
    # Get last 30 days of email logs
    thirty_days_ago = datetime.now() - timedelta(days=30)
    logs = EmailLog.query.filter(
        EmailLog.sent_date >= thirty_days_ago
    ).order_by(EmailLog.sent_date.desc()).all()
    
    return jsonify([{
        'id': log.id,
        'sent_date': log.sent_date.isoformat(),
        'recipient': log.recipient,
        'subject': log.subject,
        'pdf_path': log.pdf_path
    } for log in logs])

@app.route('/api/staff-members', methods=['GET', 'POST'])
def staff_members():
    if request.method == 'POST':
        try:
            data = request.json
            user_name = data.get('user_name', 'Unknown')
            
            staff = StaffMember(
                name=data['name'],
                color=data['color'],
                shift=data['shift'],
                active=data.get('active', True)
            )
            db.session.add(staff)
            db.session.commit()
            
            # Log the addition
            description = f"Added staff member: {staff.name} - Shift {staff.shift} - {staff.color}"
            log_activity(user_name, 'add', 'staff_member', description, staff.id, request.remote_addr)
            
            return jsonify({'success': True, 'id': staff.id})
        except Exception as e:
            db.session.rollback()
            print(Fore.RED + f"Error creating staff member: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request - return all active staff members
    staff_list = StaffMember.query.filter_by(active=True).order_by(StaffMember.shift, StaffMember.color).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'color': s.color,
        'shift': s.shift,
        'active': s.active
    } for s in staff_list])

@app.route('/api/staff-members/<int:staff_id>', methods=['PUT', 'DELETE'])
def staff_member(staff_id):
    staff = StaffMember.query.get(staff_id)
    if not staff:
        return jsonify({'success': False, 'error': 'Staff member not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        user_name = data.get('user_name', 'Unknown')
        
        # Track changes for logging
        changes = []
        if 'name' in data and data['name'] != staff.name:
            changes.append(f"name: {staff.name} → {data['name']}")
        if 'color' in data and data['color'] != staff.color:
            changes.append(f"color: {staff.color} → {data['color']}")
        if 'shift' in data and data['shift'] != staff.shift:
            changes.append(f"shift: {staff.shift} → {data['shift']}")
        
        staff.name = data.get('name', staff.name)
        staff.color = data.get('color', staff.color)
        staff.shift = data.get('shift', staff.shift)
        staff.active = data.get('active', staff.active)
        db.session.commit()
        
        # Log the modification
        if changes:
            description = f"Modified staff member {staff.name}: {', '.join(changes)}"
            log_activity(user_name, 'modify', 'staff_member', description, staff_id, request.remote_addr)
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        data = request.get_json() or {}
        user_name = data.get('user_name', 'Unknown')
        
        # Log the deletion (soft delete)
        description = f"Removed staff member: {staff.name} - Shift {staff.shift}"
        log_activity(user_name, 'delete', 'staff_member', description, staff_id, request.remote_addr)
        
        # Soft delete - just mark as inactive
        staff.active = False
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/verify-pin', methods=['POST'])
def verify_pin():
    """Verify shift leader PIN (PIN only, no name required)"""
    data = request.json
    pin = data.get('pin', '').strip()
    
    if not pin:
        return jsonify({'success': False, 'error': 'PIN is required'}), 400
    
    # Find shift leader by PIN using secure comparison
    all_leaders = ShiftLeader.query.filter_by(active=True).all()
    leader = None
    for l in all_leaders:
        if verify_pin_hash(pin, l.pin):
            leader = l
            break
    
    if not leader:
        return jsonify({'success': False, 'error': 'Invalid PIN'}), 401
    
    # Update last login time
    leader.last_login = datetime.now()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'leader': {
            'id': leader.id,
            'name': leader.name,
            'is_super_user': leader.is_super_user,
            'user_type': 'Super User' if leader.is_super_user else 'Shift Leader'
        }
    })

@app.route('/api/shift-leaders', methods=['GET'])
def get_shift_leaders():
    """Get list of active shift leaders (names only, no PINs)"""
    leaders = ShiftLeader.query.filter_by(active=True).order_by(ShiftLeader.name).all()
    return jsonify([{
        'id': leader.id,
        'name': leader.name,
        'is_super_user': leader.is_super_user,
        'user_type': 'Super User' if leader.is_super_user else 'Shift Leader'
    } for leader in leaders])

@app.route('/api/change-pin', methods=['POST'])
def change_pin():
    """Change shift leader PIN"""
    data = request.json
    name = data.get('name', '').strip()
    old_pin = data.get('old_pin', '').strip()
    new_pin = data.get('new_pin', '').strip()
    
    if not name or not old_pin or not new_pin:
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    if len(new_pin) < 4:
        return jsonify({'success': False, 'error': 'PIN must be at least 4 digits'}), 400
    
    # Find shift leader by name
    leader = ShiftLeader.query.filter(
        db.func.lower(ShiftLeader.name) == name.lower(),
        ShiftLeader.active == True
    ).first()
    
    if not leader:
        return jsonify({'success': False, 'error': 'Shift leader not found'}), 401
    
    # Verify old PIN using secure comparison
    if not verify_pin_hash(old_pin, leader.pin):
        return jsonify({'success': False, 'error': 'Current PIN is incorrect'}), 401
    
    # Update to new PIN using secure hashing
    leader.pin = hash_pin(new_pin)
    db.session.commit()
    
    # Log the PIN change
    description = f"Changed PIN for shift leader: {leader.name}"
    log_activity(leader.name, 'modify', 'pin', description, leader.id, request.remote_addr)
    
    return jsonify({'success': True, 'message': 'PIN changed successfully'})

def initialize_shift_leaders():
    """Initialize shift leaders with default PINs (default: 1234) and set super users"""
    try:
        shift_leader_names = ['Ricardo', 'Arpad', 'Carlos', 'Brian', 'Kojo', 'Peter', 'Konrad']
        super_users = ['Arpad', 'Carlos']  # Super users with special privileges
        default_pin = '1234'
        hashed_default_pin = hash_pin(default_pin)
        
        added_count = 0
        updated_count = 0
        for name in shift_leader_names:
            # Check if leader already exists
            existing = ShiftLeader.query.filter(
                db.func.lower(ShiftLeader.name) == name.lower()
            ).first()
            
            is_super = name in super_users
            
            if not existing:
                leader = ShiftLeader(
                    name=name,
                    pin=hashed_default_pin,
                    active=True,
                    is_super_user=is_super
                )
                db.session.add(leader)
                added_count += 1
                user_type = "Super User" if is_super else "Shift Leader"
                print(Fore.GREEN + f"✓ Added {user_type}: {name} (default PIN: {default_pin})")
            else:
                # Update existing leader if super user status changed
                if existing.is_super_user != is_super:
                    existing.is_super_user = is_super
                    updated_count += 1
                    user_type = "Super User" if is_super else "Shift Leader"
                    print(Fore.CYAN + f"✓ Updated {existing.name} to {user_type}")
        
        if added_count > 0 or updated_count > 0:
            db.session.commit()
            if added_count > 0:
                print(Fore.YELLOW + Style.BRIGHT + f"\n{'='*50}")
                print(Fore.YELLOW + Style.BRIGHT + f"IMPORTANT: {added_count} user(s) created with default PIN: {default_pin}")
                print(Fore.YELLOW + Style.BRIGHT + f"Please change PINs immediately for security!")
                print(Fore.YELLOW + Style.BRIGHT + f"{'='*50}\n")
            if updated_count > 0:
                print(Fore.CYAN + f"✓ Updated {updated_count} user(s) with new privileges")
        else:
            print(Fore.GREEN + "All shift leaders already exist in database with correct privileges.")
            
    except Exception as e:
        print(Fore.RED + f"Error initializing shift leaders: {e}")
        db.session.rollback()

def cleanup_old_leave_data():
    """Delete holiday and sick leave records older than 2 years"""
    try:
        two_years_ago = datetime.now().date() - timedelta(days=730)  # 2 years = 730 days
        
        # Find old leave records (holiday, sick, off status)
        old_records = StaffRota.query.filter(
            StaffRota.date < two_years_ago,
            StaffRota.status.in_(['holiday', 'sick', 'off'])
        ).all()
        
        if old_records:
            count = len(old_records)
            for record in old_records:
                db.session.delete(record)
            db.session.commit()
            print(Fore.GREEN + f"✓ Cleaned up {count} old leave record(s) from before {two_years_ago}")
        else:
            print(Fore.CYAN + f"No old leave records to clean up (older than {two_years_ago})")
            
    except Exception as e:
        print(Fore.RED + f"Error cleaning up old leave data: {e}")
        db.session.rollback()

def get_google_drive_credentials():
    """Get OAuth2 credentials for Google Drive, handling token refresh and authorization"""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pickle
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Limited scope for security
    
    creds = None
    
    # Get paths - token.pickle should be in same directory as .exe (user data)
    token_path = os.path.join(BASE_PATH, 'token.pickle')
    
    # credentials.json should be bundled or in same directory as .exe
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe - check bundled location first, then base path
        try:
            credentials_path = get_resource_path('credentials.json')
            if not os.path.exists(credentials_path):
                # Fallback to same directory as .exe
                credentials_path = os.path.join(BASE_PATH, 'credentials.json')
        except:
            credentials_path = os.path.join(BASE_PATH, 'credentials.json')
    else:
        # Running as script
        credentials_path = os.path.join(BASE_PATH, 'credentials.json')
    
    # Load existing token if available
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(Fore.YELLOW + f"  Could not load existing token: {e}")
    
    # If no valid credentials, try to refresh or get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print(Fore.GREEN + "✓ Refreshed Google Drive credentials")
            except Exception as e:
                print(Fore.YELLOW + f"  Could not refresh token: {e}")
                creds = None
        
        # If still no credentials, need user authorization
        if not creds:
            if not os.path.exists(credentials_path):
                print(Fore.RED + "✗ Google Drive backup failed: credentials.json not found")
                print(Fore.YELLOW + f"  Expected location: {credentials_path}")
                print(Fore.YELLOW + "  Please follow instructions in GOOGLE_DRIVE_SETUP.md")
                print(Fore.YELLOW + "  You need to create OAuth2 Client ID credentials (not service account)")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0, open_browser=True)
                print(Fore.GREEN + "✓ Google Drive authorization successful!")
                
                # Save credentials for next time (in same directory as .exe)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print(Fore.GREEN + "✓ Credentials saved for future use")
            except Exception as e:
                print(Fore.RED + f"✗ Authorization failed: {e}")
                return None
    
    return creds

def upload_to_google_drive(file_path, file_name='diary_latest.db'):
    """Upload file to Google Drive, replacing any existing backup"""
    service = None
    media = None
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        
        # Get OAuth2 credentials
        creds = get_google_drive_credentials()
        if not creds:
            return False
        
        # Build Drive API service
        service = build('drive', 'v3', credentials=creds)
        
        # Search for "Diary_Backups" folder (in shared folders or user's drive)
        folder_name = 'Diary_Backups'
        # Search in all accessible drives including shared folders
        # Note: corpora='allDrives' searches in shared drives, 'user' searches user's drive including shared items
        folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        folder_results = service.files().list(
            q=folder_query, 
            spaces='drive',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='files(id, name)'
        ).execute()
        folders = folder_results.get('files', [])
        
        if not folders:
            # Create folder if it doesn't exist (OAuth2 user credentials can create folders)
            print(Fore.CYAN + f"  Creating '{folder_name}' folder in Google Drive...")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id, name').execute()
            folder_id = folder.get('id')
            print(Fore.GREEN + f"✓ Created '{folder_name}' folder in Google Drive")
        else:
            folder_id = folders[0]['id']
            print(Fore.GREEN + f"✓ Found '{folder_name}' folder in Google Drive (ID: {folder_id})")
        
        # Search for existing backup file with the same name
        file_query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        file_results = service.files().list(
            q=file_query, 
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        existing_files = file_results.get('files', [])
        
        # Delete existing backup if found
        if existing_files:
            for existing_file in existing_files:
                service.files().delete(fileId=existing_file['id']).execute()
                print(Fore.CYAN + f"  Deleted old backup: {existing_file['name']}")
        
        # Upload new backup file
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='application/x-sqlite3', resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, name, size'
        ).execute()
        
        file_size_kb = int(uploaded_file.get('size', 0)) / 1024
        print(Fore.GREEN + f"✓ Database backed up to Google Drive successfully!")
        print(Fore.CYAN + f"  File: {uploaded_file.get('name')}")
        print(Fore.CYAN + f"  Size: {file_size_kb:.2f} KB")
        print(Fore.CYAN + f"  Folder: {folder_name}")
        print(Fore.GREEN + f"  Only latest backup kept (old backups deleted)")
        
        return True
        
    except Exception as e:
        print(Fore.RED + f"✗ Error uploading to Google Drive: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up resources
        # Note: Google API client library manages HTTP connections internally
        # Setting to None allows garbage collection to clean up connections
        # Service object cleanup is handled by Python garbage collection
        # HTTP connections are managed by the underlying httplib2 library
        service = None
        media = None

def backup_database_to_gdrive():
    """Create backup of database and upload to Google Drive"""
    import shutil
    import tempfile
    
    tmp_path = None
    try:
        # Source database file - ensure instance directory exists
        instance_dir = os.path.join(BASE_PATH, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, 'diary.db')
        
        if not os.path.exists(db_path):
            print(Fore.RED + "✗ Database file not found, skipping Google Drive backup")
            return False
        
        # Ensure all database transactions are committed before backup
        try:
            db.session.commit()
            print(Fore.CYAN + "✓ Committed pending database transactions")
        except Exception as commit_error:
            print(Fore.YELLOW + f"Warning: Error committing database transactions: {commit_error}")
            db.session.rollback()
        
        # Close database connections to ensure file is not locked during copy
        # For SQLite, we need to dispose the engine to close ALL connections
        try:
            db.session.remove()  # Close current session
            db.engine.dispose()  # Dispose engine to close all connections (SQLite specific)
            print(Fore.CYAN + "✓ Database connections closed")
        except Exception as close_error:
            print(Fore.YELLOW + f"Warning: Error closing database connections: {close_error}")
            try:
                db.engine.dispose()
            except:
                pass
        
        # Get file size for reporting
        file_size_kb = os.path.getsize(db_path) / 1024
        print(Fore.CYAN + f"Starting Google Drive backup...")
        print(Fore.CYAN + f"  Database size: {file_size_kb:.2f} KB")
        
        # Create temporary copy (in case upload takes time and db is being used)
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.db', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            shutil.copy2(db_path, tmp_path)
        
        # Upload to Google Drive
        success = upload_to_google_drive(tmp_path, 'diary_latest.db')
        
        return success
        
    except Exception as e:
        print(Fore.RED + f"✗ Error backing up database to Google Drive: {e}")
        return False
    finally:
        # Clean up temporary file - ensure it's always deleted
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                print(Fore.YELLOW + f"Warning: Could not delete temporary backup file: {cleanup_error}")

def check_missed_reports():
    """Check for missed daily reports and send them on startup"""
    try:
        settings = ScheduleSettings.query.first()
        if not settings or not settings.email_enabled:
            print(Fore.YELLOW + "Email not enabled, skipping missed report check")
            return
        
        # Check the last 7 days for missed reports
        today = datetime.now().date()
        
        for days_ago in range(1, 8):  # Check last 7 days
            check_date = today - timedelta(days=days_ago)
            
            # Check if report was already sent for this date (check by subject, not send date)
            expected_subject = f"Daily Report - {check_date}"
            existing_log = EmailLog.query.filter(
                EmailLog.subject == expected_subject
            ).first()
            
            if existing_log:
                # Report was already sent for this date
                continue
            
            # Check if there are any unsent occurrences for this date
            next_day = check_date + timedelta(days=1)
            unsent_occurrences = DailyOccurrence.query.filter(
                DailyOccurrence.timestamp >= check_date,
                DailyOccurrence.timestamp < next_day,
                DailyOccurrence.sent == False
            ).count()
            
            # Check if there are water temperatures for this date (even if no occurrences)
            temp_start = datetime.combine(check_date, datetime.min.time())
            temp_end = datetime.combine(check_date, datetime.max.time())
            water_temps = WaterTemperature.query.filter(
                WaterTemperature.timestamp >= temp_start,
                WaterTemperature.timestamp <= temp_end
            ).count()
            
            # If there's data (occurrences or water temps) and no email was sent, send it now
            if unsent_occurrences > 0 or water_temps > 0:
                print(Fore.YELLOW + Style.BRIGHT + f"⚠️ MISSED REPORT DETECTED for {check_date}")
                print(Fore.YELLOW + f"   - Unsent occurrences: {unsent_occurrences}")
                print(Fore.YELLOW + f"   - Water temperature readings: {water_temps}")
                print(Fore.YELLOW + f"   - Sending report now...")
                
                success = send_daily_report(check_date)
                if success:
                    print(Fore.GREEN + f"✓ Missed report for {check_date} sent successfully!")
                else:
                    print(Fore.RED + f"✗ Failed to send missed report for {check_date}")
        
        print(Fore.GREEN + "Missed report check completed")
        
    except Exception as e:
        print(Fore.RED + f"Error checking for missed reports: {e}")

def update_scheduler():
    """Update the scheduler with new time settings"""
    try:
        # Remove existing job if it exists
        try:
            scheduler.remove_job('daily_report')
        except Exception:
            pass  # Job doesn't exist yet, that's fine
        
        # Get new settings
        settings = ScheduleSettings.query.first()
        if settings and settings.email_enabled:
            # Parse time
            hour, minute = map(int, settings.email_time.split(':'))
            
            # Add new job
            scheduler.add_job(
                func=send_daily_report_with_context,
                trigger="cron",
                hour=hour,
                minute=minute,
                id='daily_report'
            )
            print(Fore.GREEN + f"Scheduler updated to send emails at {settings.email_time}")
    except Exception as e:
        print(Fore.RED + f"Error updating scheduler: {e}")

def migrate_database():
    """Migrate database to handle schema changes safely"""
    from sqlalchemy import text, inspect
    
    try:
        # Create inspector to check table structure
        inspector = inspect(db.engine)
        
        # Check if water_temperature table has the old structure
        if 'water_temperature' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('water_temperature')]
            
            if 'notes' in columns and 'time_recorded' not in columns:
                print("Migrating water_temperature table...")
                with db.engine.connect() as conn:
                    # Create new table with correct structure
                    conn.execute(text("""
                        CREATE TABLE water_temperature_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            temperature FLOAT NOT NULL,
                            time_recorded VARCHAR(5) NOT NULL
                        )
                    """))
                    
                    # Copy data from old table (if any)
                    try:
                        conn.execute(text("""
                            INSERT INTO water_temperature_new (id, timestamp, temperature, time_recorded)
                            SELECT id, timestamp, temperature, '00:00' FROM water_temperature
                        """))
                    except:
                        pass  # No data to migrate
                    
                    # Drop old table and rename new one
                    conn.execute(text("DROP TABLE water_temperature"))
                    conn.execute(text("ALTER TABLE water_temperature_new RENAME TO water_temperature"))
                    conn.commit()
                print(Fore.GREEN + "✓ water_temperature table migrated successfully!")
        
        # Check if schedule_settings table needs new sender email columns
        if 'schedule_settings' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('schedule_settings')]
            
            if 'sender_email' not in columns:
                print(Fore.CYAN + "Adding sender email configuration columns to schedule_settings...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE schedule_settings ADD COLUMN sender_email VARCHAR(200) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE schedule_settings ADD COLUMN sender_password VARCHAR(200) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE schedule_settings ADD COLUMN smtp_server VARCHAR(200) DEFAULT 'smtp.gmail.com'"))
                    conn.execute(text("ALTER TABLE schedule_settings ADD COLUMN smtp_port INTEGER DEFAULT 587"))
                    conn.commit()
                print(Fore.GREEN + "✓ Sender email columns added successfully!")
        
        # Check if shift_leader table needs is_super_user column
        if 'shift_leader' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('shift_leader')]
            
            if 'is_super_user' not in columns:
                print(Fore.CYAN + "Adding is_super_user column to shift_leader table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE shift_leader ADD COLUMN is_super_user BOOLEAN DEFAULT 0"))
                    conn.commit()
                
                # Set Arpad and Carlos as super users
                with db.engine.connect() as conn:
                    conn.execute(text("UPDATE shift_leader SET is_super_user = 1 WHERE LOWER(name) IN ('arpad', 'carlos')"))
                    conn.commit()
                print(Fore.GREEN + "✓ Super user column added and Arpad/Carlos set as super users!")
        
        # Check if cctv_fault table needs new detailed fields
        if 'cctv_fault' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('cctv_fault')]
            
            if 'flat_number' not in columns:
                print(Fore.CYAN + "Adding detailed fields to cctv_fault table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE cctv_fault ADD COLUMN flat_number VARCHAR(20) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE cctv_fault ADD COLUMN block_number VARCHAR(20) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE cctv_fault ADD COLUMN floor_number VARCHAR(20) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE cctv_fault ADD COLUMN contact_details VARCHAR(200) DEFAULT ''"))
                    conn.execute(text("ALTER TABLE cctv_fault ADD COLUMN additional_notes TEXT DEFAULT ''"))
                    conn.commit()
                print(Fore.GREEN + "✓ CCTV/Intercom fault detailed fields added successfully!")
        
        # Create all tables if they don't exist (includes ActivityLog and any new models)
        db.create_all()
        print(Fore.GREEN + "✓ Tables created/verified successfully!")
        
        # Refresh inspector after create_all to check for new tables
        inspector = inspect(db.engine)
        
        # Check if overtime table exists and has correct schema
        if 'overtime' not in inspector.get_table_names():
            print(Fore.CYAN + "Creating overtime table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE overtime (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        staff_name VARCHAR(100) NOT NULL,
                        date DATE NOT NULL,
                        hours FLOAT NOT NULL,
                        description TEXT,
                        created_by VARCHAR(100),
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
            print(Fore.GREEN + "✓ Overtime table created successfully!")
        else:
            # Check if overtime table has required columns (especially staff_name)
            columns = [col['name'] for col in inspector.get_columns('overtime')]
            required_columns = ['staff_name', 'date', 'hours', 'description', 'created_by', 'created_date', 'updated_date']
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(Fore.CYAN + f"Overtime table missing required columns: {missing_columns}")
                print(Fore.CYAN + "Recreating overtime table with correct schema...")
                try:
                    # Try to backup existing data if we can read it
                    with db.engine.connect() as conn:
                        try:
                            # Get column names from existing table to try to preserve data
                            existing_cols = [col['name'] for col in inspector.get_columns('overtime')]
                            backup_data = []
                            if existing_cols:
                                # Try to select what we can
                                select_cols = ', '.join([col for col in existing_cols if col in ['id', 'date', 'hours', 'description', 'created_by', 'created_date', 'updated_date']])
                                if select_cols:
                                    result = conn.execute(text(f"SELECT {select_cols} FROM overtime"))
                                    backup_data = [dict(row._mapping) for row in result]
                                    print(Fore.CYAN + f"Found {len(backup_data)} existing overtime entries to preserve")
                        except Exception as backup_error:
                            print(Fore.YELLOW + f"⚠ Could not backup existing data: {backup_error}")
                            backup_data = []
                    
                    # Drop and recreate table
                    with db.engine.connect() as conn:
                        conn.execute(text("DROP TABLE IF EXISTS overtime"))
                        conn.execute(text("""
                            CREATE TABLE overtime (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                staff_name VARCHAR(100) NOT NULL,
                                date DATE NOT NULL,
                                hours FLOAT NOT NULL,
                                description TEXT,
                                created_by VARCHAR(100),
                                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                                updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        conn.commit()
                    print(Fore.GREEN + "✓ Overtime table recreated successfully!")
                    
                    if backup_data:
                        print(Fore.YELLOW + "⚠ Note: Existing overtime entries were not automatically migrated due to schema change.")
                        print(Fore.YELLOW + "   Please re-enter any lost entries manually.")
                except Exception as recreate_error:
                    print(Fore.RED + f"✗ Error recreating overtime table: {recreate_error}")
                    print(Fore.YELLOW + "   You may need to manually fix the database schema.")
            else:
                print(Fore.GREEN + "✓ Overtime table already exists with correct schema")
        
        # Verify ActivityLog table was created
        if 'activity_log' in inspector.get_table_names():
            print(Fore.GREEN + "✓ ActivityLog table ready for user activity tracking")
        
    except Exception as e:
        print(Fore.RED + f"Migration error: {e}")
        # Only create tables if they don't exist - NEVER drop existing data
        try:
            db.create_all()
            print("Tables created/verified successfully!")
        except Exception as create_error:
            print(Fore.RED + f"Error creating tables: {create_error}")

if __name__ == '__main__':
    with app.app_context():
        # Migrate database if needed
        migrate_database()
        
        # Initialize shift leaders
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "INITIALIZING SHIFT LEADERS...")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        initialize_shift_leaders()
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        
        # Initialize scheduler with default settings
        settings = ScheduleSettings.query.first()
        if not settings:
            settings = ScheduleSettings()
            db.session.add(settings)
            db.session.commit()
        
        # Check for missed reports on startup (last 7 days)
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "CHECKING FOR MISSED REPORTS...")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        check_missed_reports()
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        
        # Clean up old leave data (older than 2 years)
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "CLEANING UP OLD LEAVE DATA...")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        cleanup_old_leave_data()
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        
        # Schedule daily report using settings
        if settings.email_enabled:
            hour, minute = map(int, settings.email_time.split(':'))
            scheduler.add_job(
                func=send_daily_report_with_context,
                trigger="cron",
                hour=hour,
                minute=minute,
                id='daily_report'
            )
        
        # Schedule daily cleanup of old leave data (runs at 3 AM every day)
        scheduler.add_job(
            func=cleanup_old_leave_data_with_context,
            trigger="cron",
            hour=3,
            minute=0,
            id='cleanup_old_leave'
        )
        
        # Schedule daily Google Drive backup (runs at 2 AM every day)
        scheduler.add_job(
            func=backup_database_to_gdrive_with_context,
            trigger="cron",
            hour=2,
            minute=0,
            id='daily_gdrive_backup'
        )
        
        scheduler.start()
        
        # Log application startup
        log_startup()
        
        # Shut down the scheduler and log shutdown when exiting the app
        def cleanup_on_exit():
            log_shutdown("Normal shutdown")
            scheduler.shutdown()
        
        atexit.register(cleanup_on_exit)
        
        # Handle forced shutdown signals (Ctrl+C, Windows termination, etc.)
        def handle_shutdown_signal(signum, frame):
            signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
            log_shutdown(f"Signal received: {signal_name}")
            scheduler.shutdown()
            sys.exit(0)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown_signal)   # Ctrl+C
        signal.signal(signal.SIGTERM, handle_shutdown_signal)  # Termination signal
        if hasattr(signal, 'SIGBREAK'):  # Windows-specific
            signal.signal(signal.SIGBREAK, handle_shutdown_signal)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Building Management Diary Application')
    parser.add_argument('--no-browser', action='store_true', 
                        help='Run without opening browser (for service/scheduled mode)')
    args = parser.parse_args()
    
    # Auto-open browser after server starts (unless --no-browser flag is set)
    if not args.no_browser:
        def open_browser():
            """Wait for server to start, then open default browser"""
            import urllib.request
            import time
            
            url = 'http://127.0.0.1:5000'
            max_attempts = 30  # Try for 15 seconds (30 * 0.5s)
            
            for attempt in range(max_attempts):
                try:
                    # Try to connect to the server
                    urllib.request.urlopen(url, timeout=1)
                    # Server is ready!
                    webbrowser.open(url)
                    print(Fore.GREEN + "✓ Browser opened automatically")
                    return
                except:
                    time.sleep(0.5)  # Wait 500ms before next attempt
            
            # Server didn't start in time
            print(Fore.YELLOW + f"⚠️ Could not verify server is ready, opening browser anyway...")
            webbrowser.open(url)
        
        # Start browser in background thread
        threading.Thread(target=open_browser, daemon=True).start()
    else:
        print(Fore.CYAN + "Running in service mode (browser disabled)")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
