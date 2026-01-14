from flask import Flask, render_template, request, jsonify, send_file, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import json
import hashlib
import webbrowser
import threading
import signal
import sys
import socket
from werkzeug.utils import secure_filename
import uuid
from colorama import init, Fore, Back, Style

# Initialize colorama for Windows console colors
init(autoreset=True)

# Import configuration from config.py

# Import configuration from config.py
try:
    from config import EMAIL_CONFIG
    print(Fore.GREEN + "✓ Email configuration loaded from config.py")
except ImportError:
    print(Fore.YELLOW + "⚠️ Warning: config.py not found, using default email configuration")
    EMAIL_CONFIG = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': 'your-email@gmail.com',
        'password': 'your-app-password',
        'recipient': 'recipient@example.com'
    }

def get_user_data_dir():
    """Get writable user data directory for storing files"""
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe - use AppData
        if sys.platform == 'win32':
            appdata = os.getenv('LOCALAPPDATA')
            if not appdata:
                appdata = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'Local')
            user_data_dir = os.path.join(appdata, 'DiaryApp')
        else:
            from pathlib import Path
            if sys.platform == 'darwin':
                user_data_dir = os.path.join(str(Path.home()), 'Library', 'Application Support', 'DiaryApp')
            else:
                user_data_dir = os.path.join(str(Path.home()), '.local', 'share', 'DiaryApp')
    else:
        # Running as Python script - use project directory
        user_data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir

# Initialize user data directory
USER_DATA_DIR = get_user_data_dir()
print(Fore.CYAN + f"User data directory: {USER_DATA_DIR}")

if getattr(sys, 'frozen', False):
    # If running as a bundle, templates are in sys._MEIPASS
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)
# Use user data directory for database
db_path = os.path.join(USER_DATA_DIR, 'instance', 'diary.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
UPLOAD_FOLDER = os.path.join(USER_DATA_DIR, 'instance', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB per file (safe for 20MP+ photos)
MAX_IMAGES_PER_ENTRY = 5

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  # 150MB total request size (allows multiple large files)

# Create upload directories
os.makedirs(os.path.join(UPLOAD_FOLDER, 'occurrences'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'maintenance'), exist_ok=True)

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
    status = db.Column(db.String(20), default='pending')  # 'success', 'failed', 'pending'
    error_message = db.Column(db.Text, default='')  # Store error details if email failed

class ScheduleSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_time = db.Column(db.String(5), default='23:59')  # Format: HH:MM
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

class OccurrenceImage(db.Model):
    """Images attached to daily occurrences"""
    id = db.Column(db.Integer, primary_key=True)
    occurrence_id = db.Column(db.Integer, db.ForeignKey('daily_occurrence.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.now)
    file_size = db.Column(db.Integer)  # in bytes
    
class MaintenanceImage(db.Model):
    """Images attached to maintenance entries"""
    id = db.Column(db.Integer, primary_key=True)
    maintenance_id = db.Column(db.String(50), nullable=False)  # Links to Maintenance_Book_2.ID
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.now)
    file_size = db.Column(db.Integer)  # in bytes

# Maintenance_Backup database connection
# Always use USER_DATA_DIR (AppData for compiled .exe, project dir for scripts)
maintenance_db_path = os.path.join(USER_DATA_DIR, 'instance', 'Maintenance_Backup.db')
os.makedirs(os.path.dirname(maintenance_db_path), exist_ok=True)

# If running as compiled .exe, always use AppData location (no fallback)
# If running as script and database doesn't exist, try to copy from project directory
if getattr(sys, 'frozen', False):
    # Compiled .exe - use AppData location only
    if os.path.exists(maintenance_db_path):
        print(Fore.GREEN + f"✓ Maintenance_Backup.db found at: {maintenance_db_path}")
    else:
        print(Fore.YELLOW + f"⚠️  Maintenance_Backup.db not found at: {maintenance_db_path}")
        print(Fore.YELLOW + f"    Will be created when first maintenance entry is saved.")
else:
    # Running as script - check if exists, if not try project directory
    if not os.path.exists(maintenance_db_path):
        project_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'Maintenance_Backup.db')
        if os.path.exists(project_db_path):
            # Copy from project directory to user data directory
            import shutil
            shutil.copy2(project_db_path, maintenance_db_path)
            print(Fore.YELLOW + f"Copied Maintenance_Backup.db from project directory to: {maintenance_db_path}")
        else:
            print(Fore.YELLOW + f"⚠️  Maintenance_Backup.db not found at: {maintenance_db_path}")
            print(Fore.YELLOW + f"    Will be created when first maintenance entry is saved.")
    else:
        print(Fore.GREEN + f"✓ Maintenance_Backup.db found at: {maintenance_db_path}")

# Image upload helper functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(file, entry_type, entry_id):
    """
    Save uploaded image file and return metadata
    
    Args:
        file: FileStorage object from request.files
        entry_type: 'occurrence' or 'maintenance'
        entry_id: ID of the entry
    
    Returns:
        dict with filename, filepath, and file_size
    """
    if not file or not allowed_file(file.filename):
        return None
    
    # Generate unique filename
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{entry_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    
    # Determine save path
    subfolder = 'occurrences' if entry_type == 'occurrence' else 'maintenance'
    
    # Store path with forward slashes for database consistency (URL safe)
    relative_path = f"{subfolder}/{unique_filename}"
    
    # Use os-specific path for file system operations
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, unique_filename)
    
    # Save file
    file.save(full_path)
    file_size = os.path.getsize(full_path)
    
    return {
        'filename': original_filename,
        'filepath': relative_path,
        'file_size': file_size
    }

def delete_image_file(filepath):
    """Delete image file from filesystem"""
    try:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    except Exception as e:
        print(f"Error deleting image file: {e}")
    return False

def get_images_for_entry(entry_type, entry_id):
    """Get all images for a specific entry"""
    if entry_type == 'occurrence':
        images = OccurrenceImage.query.filter_by(occurrence_id=entry_id).all()
    else:
        images = MaintenanceImage.query.filter_by(maintenance_id=str(entry_id)).all()
    
    return [{
        'id': img.id,
        'filename': img.filename,
        'filepath': img.filepath,
        'url': f'/uploads/{img.filepath.replace("\\", "/")}',
        'upload_timestamp': img.upload_timestamp.isoformat() if img.upload_timestamp else None,
        'file_size': img.file_size
    } for img in images]

# Initialize scheduler
scheduler = BackgroundScheduler()

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

def backup_maintenance_database_to_gdrive():
    """Create backup of maintenance database and upload to Google Drive"""
    import shutil
    import tempfile
    
    try:
        # Source database file - use user data directory
        db_path = os.path.join(USER_DATA_DIR, 'instance', 'Maintenance_Backup.db')
        
        if not os.path.exists(db_path):
            print(Fore.RED + "✗ Maintenance database file not found, skipping Google Drive backup")
            return False
        
        # Get file size for reporting
        file_size_kb = os.path.getsize(db_path) / 1024
        print(Fore.CYAN + f"Starting Maintenance database Google Drive backup...")
        print(Fore.CYAN + f"  Database size: {file_size_kb:.2f} KB")
        
        # Create temporary copy (in case upload takes time and db is being used)
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.db', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            shutil.copy2(db_path, tmp_path)
        
        # Upload to Google Drive
        success = upload_to_google_drive(tmp_path, 'maintenance_latest.db')
        
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return success
        
    except Exception as e:
        print(Fore.RED + f"✗ Error backing up maintenance database to Google Drive: {e}")
        return False

def backup_maintenance_database_to_gdrive_with_context():
    """Wrapper for backup_maintenance_database_to_gdrive that provides Flask app context"""
    with app.app_context():
        return backup_maintenance_database_to_gdrive()

def backup_all_databases_to_gdrive():
    """Backup both databases to Google Drive simultaneously"""
    import threading
    
    diary_result = {'success': False}
    maintenance_result = {'success': False}
    
    def backup_diary():
        diary_result['success'] = backup_database_to_gdrive()
    
    def backup_maintenance():
        maintenance_result['success'] = backup_maintenance_database_to_gdrive()
    
    # Run both backups in parallel
    diary_thread = threading.Thread(target=backup_diary)
    maintenance_thread = threading.Thread(target=backup_maintenance)
    
    diary_thread.start()
    maintenance_thread.start()
    
    # Wait for both to complete
    diary_thread.join()
    maintenance_thread.join()
    
    return diary_result['success'], maintenance_result['success']

def backup_all_databases_to_gdrive_with_context():
    """Wrapper for backup_all_databases_to_gdrive that provides Flask app context"""
    with app.app_context():
        return backup_all_databases_to_gdrive()

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
        
        # Get occurrences for the specified date
        next_day = report_date + timedelta(days=1)
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= report_date,
            DailyOccurrence.timestamp < next_day,
            DailyOccurrence.sent == False
        ).all()
        
        # Generate PDF and CSV for local backup (not sent via email)
        pdf_path = generate_daily_pdf(occurrences, report_date)
        csv_path = generate_daily_csv(occurrences, report_date)
        
        # Log the email FIRST (before sending) to prevent duplicate sends on retry
        email_log = EmailLog(
            recipient=settings.recipient_email,
            subject=f"Daily Report - {report_date}",
            pdf_path=pdf_path,  # Saved locally, not emailed
            status='pending',
            error_message=''
        )
        db.session.add(email_log)
        db.session.commit()
        
        # Send email with HTML styling (no PDF attachment)
        email_sent, error_message = send_email_with_pdf(pdf_path, f"Daily Report - {report_date}", settings.recipient_email)
        
        # Update email log with result
        email_log.status = 'success' if email_sent else 'failed'
        email_log.error_message = error_message or ''
        db.session.commit()
        
        if email_sent:
            # Mark as sent if there were occurrences and email succeeded
            if occurrences:
                for occurrence in occurrences:
                    occurrence.sent = True
                db.session.commit()
            
            print(Fore.GREEN + f"Daily report sent successfully for {report_date}")
            print(Fore.CYAN + f"Local backups saved - PDF: {pdf_path}, CSV: {csv_path}")
        else:
            print(Fore.YELLOW + f"⚠️ Email failed to send for {report_date}, but PDF/CSV saved locally")
            if error_message:
                print(Fore.RED + f"Error details: {error_message}")
            print(Fore.CYAN + f"PDF: {pdf_path}")
            print(Fore.CYAN + f"CSV: {csv_path}")
        
        return email_sent
    except Exception as e:
        print(Fore.RED + f"Error sending daily report: {e}")
        return False

def generate_daily_pdf(occurrences, report_date=None):
    """Generate PDF report of daily occurrences"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    
    # Use provided date or default to today
    if report_date is None:
        report_date = datetime.now().date()
    
    # Filename uses report date, with time suffix to avoid overwriting
    filename = f"daily_report_{report_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.pdf"
    reports_dir = os.path.join(USER_DATA_DIR, 'reports', 'PDF')
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)
    
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
    
    rotation_pattern = {
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
    
    # Reference date (start of week 1) - September 29, 2025
    reference_date = datetime(2025, 9, 29).date()
    days_diff = (today - reference_date).days
    week_in_cycle = (days_diff // 7) % 4
    day_of_week = today.weekday()
    
    # Get which color group(s) are off
    pattern_key = (week_in_cycle, day_of_week)
    colors_off = rotation_pattern.get(pattern_key, None)
    
    # Ensure colors_off is always a list for uniform processing
    if colors_off and not isinstance(colors_off, list):
        colors_off = [colors_off]
    
    # Build list of staff who are off (only for day shifts 1 & 2)
    staff_off_names = []
    if colors_off:
        for color in colors_off:
            # Only apply rotation to day shift colors (red, yellow, green, blue)
            if color in ['red', 'yellow', 'green', 'blue'] and color in porter_groups:
                if 'shift1' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift1'])
                if 'shift2' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift2'])
    
    # Night shift rotation pattern (separate 4-week cycle)
    night_shift_rotation = {
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
    
    # Get night shift colors off for today
    night_colors_off = night_shift_rotation.get(pattern_key, None)
    if night_colors_off and not isinstance(night_colors_off, list):
        night_colors_off = [night_colors_off]
    
    # Add night shift staff who are off to the list
    if night_colors_off:
        for color in night_colors_off:
            if color in porter_groups:
                if 'shift3' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift3'])
    
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
            # cell_content can be a single Flowable or a list of Flowables
            cell_content = [Paragraph(occurrence.description, wrap_style)]
            
            # Fetch and add images
            images = OccurrenceImage.query.filter_by(occurrence_id=occurrence.id).all()
            if images:
                for img in images:
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filepath)
                    if os.path.exists(img_path):
                        try:
                            # Add some spacing before image
                            cell_content.append(Spacer(1, 5))
                            
                            # Add image - constrained to column width
                            # Using 0 for height means it will scale proportionally based on width
                            pdf_image = RLImage(img_path, width=3.5*inch, height=2.5*inch, kind='proportional')
                            cell_content.append(pdf_image)
                            
                            # Add caption with filename (optional, can be removed if too cluttered)
                            # caption_style = ParagraphStyle('Caption', parent=styles['Normal'], fontSize=8, textColor=colors.gray)
                            # cell_content.append(Paragraph(f"Image: {img.filename}", caption_style))
                            
                        except Exception as e:
                            print(f"Warning: Could not add image {img.filename} to PDF: {e}")
            
            data.append([
                occurrence.time,
                occurrence.flat_number,
                occurrence.reported_by,
                cell_content
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

def generate_maintenance_pdf(entries):
    """Generate PDF report for selected maintenance entries"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import Image as RLImage

    filename = f"maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    reports_dir = os.path.join(USER_DATA_DIR, 'reports', 'Maintenance')
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#4A7722')
    )
    story.append(Paragraph("Maintenance Entries Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))

    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10)
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#4A7722'), spaceBefore=10, spaceAfter=5)

    for i, entry in enumerate(entries):
        # Entry Header
        story.append(Paragraph(f"Entry ID: {entry.get('ID', 'N/A')} - {entry.get('Property', 'N/A')}", styles['Heading2']))
        
        # Details Table
        details_data = [
            [Paragraph("<b>Property:</b>", label_style), Paragraph(str(entry.get('Property', 'N/A')), value_style)],
            [Paragraph("<b>Department:</b>", label_style), Paragraph(str(entry.get('Department', 'N/A')), value_style)],
            [Paragraph("<b>Employee:</b>", label_style), Paragraph(str(entry.get('Employee', 'N/A')), value_style)],
            [Paragraph("<b>Date In:</b>", label_style), Paragraph(str(entry.get('DateIn', 'N/A')), value_style)],
            [Paragraph("<b>Time In:</b>", label_style), Paragraph(str(entry.get('TimeIn', 'N/A')), value_style)],
        ]
        
        details_table = Table(details_data, colWidths=[1.5*inch, 5*inch])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.grey),
        ]))
        story.append(details_table)
        
        # Fault Details
        story.append(Paragraph("Details of Fault", section_title_style))
        story.append(Paragraph(str(entry.get('Details of Fault', 'N/A')).replace('\n', '<br/>'), value_style))
        
        # Action Taken
        story.append(Paragraph("Action Taken", section_title_style))
        story.append(Paragraph(str(entry.get('Action taken', 'N/A')).replace('\n', '<br/>'), value_style))
        
        # Completion Info
        if entry.get('Maintenance Name') or entry.get('DateDone'):
            story.append(Paragraph("Maintenance Completion", section_title_style))
            comp_data = [
                [Paragraph("<b>Maintenance Name:</b>", label_style), Paragraph(str(entry.get('Maintenance Name', 'N/A')), value_style)],
                [Paragraph("<b>Date Done:</b>", label_style), Paragraph(str(entry.get('DateDone', 'N/A')), value_style)],
                [Paragraph("<b>Time Done:</b>", label_style), Paragraph(str(entry.get('TimeDone', 'N/A')), value_style)],
            ]
            comp_table = Table(comp_data, colWidths=[1.5*inch, 5*inch])
            comp_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            story.append(comp_table)
        
        # Images
        images_to_show = entry.get('images', [])
        if not images_to_show:
            # Fallback check if images weren't passed
            images_objs = MaintenanceImage.query.filter_by(maintenance_id=str(entry['ID'])).all()
            images_to_show = [{'filepath': img.filepath} for img in images_objs]

        if images_to_show:
            story.append(Paragraph(f"Attached Images ({len(images_to_show)})", section_title_style))
            img_row = []
            for img in images_to_show:
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], img['filepath'])
                if os.path.exists(img_path):
                    try:
                        pdf_img = RLImage(img_path, width=3*inch, height=2.2*inch, kind='proportional')
                        img_row.append(pdf_img)
                        # Two images per row
                        if len(img_row) == 2:
                            img_table = Table([img_row], colWidths=[3.2*inch, 3.2*inch])
                            story.append(img_table)
                            story.append(Spacer(1, 10))
                            img_row = []
                    except Exception as e:
                        print(f"Error adding image to maintenance PDF: {e}")
            
            if img_row:
                img_table = Table([img_row + ['']], colWidths=[3.2*inch, 3.2*inch])
                story.append(img_table)

        # Separator
        if i < len(entries) - 1:
            story.append(Spacer(1, 20))
            story.append(Table([['']], colWidths=[6.5*inch], style=[('LINEABOVE', (0,0), (-1,0), 2, colors.HexColor('#4A7722'))]))
            story.append(Spacer(1, 20))

    try:
        doc.build(story)
        return filepath
    except Exception as e:
        print(f"Error building maintenance PDF: {e}")
        raise e

def generate_daily_csv(occurrences, report_date=None):
    """Generate CSV backup of daily occurrences"""
    import csv
    
    # Use provided date or default to today
    if report_date is None:
        report_date = datetime.now().date()
    
    # Filename uses report date, with time suffix to avoid overwriting
    filename = f"daily_report_{report_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.csv"
    reports_dir = os.path.join(USER_DATA_DIR, 'reports', 'CSV')
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)
    
    # Get date and staff schedule info for the report
    today = report_date
    porter_groups, all_staff = get_porter_groups()
    
    # Calculate staff schedule
    rotation_pattern = {
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
    
    reference_date = datetime(2025, 9, 29).date()
    days_diff = (today - reference_date).days
    week_in_cycle = (days_diff // 7) % 4
    day_of_week = today.weekday()
    
    pattern_key = (week_in_cycle, day_of_week)
    colors_off = rotation_pattern.get(pattern_key, None)
    
    if colors_off and not isinstance(colors_off, list):
        colors_off = [colors_off]
    
    staff_off_names = []
    if colors_off:
        for color in colors_off:
            # Only apply rotation to day shift colors (red, yellow, green, blue)
            if color in ['red', 'yellow', 'green', 'blue'] and color in porter_groups:
                if 'shift1' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift1'])
                if 'shift2' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift2'])
    
    # Night shift rotation pattern (separate 4-week cycle)
    night_shift_rotation = {
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
    
    # Get night shift colors off for today
    night_colors_off = night_shift_rotation.get(pattern_key, None)
    if night_colors_off and not isinstance(night_colors_off, list):
        night_colors_off = [night_colors_off]
    
    # Add night shift staff who are off to the list
    if night_colors_off:
        for color in night_colors_off:
            if color in porter_groups:
                if 'shift3' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift3'])
    
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
    
    # Calculate staff schedule (same logic as PDF generation)
    rotation_pattern = {
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
    
    reference_date = datetime(2025, 9, 29).date()
    days_diff = (today - reference_date).days
    week_in_cycle = (days_diff // 7) % 4
    day_of_week = today.weekday()
    pattern_key = (week_in_cycle, day_of_week)
    colors_off = rotation_pattern.get(pattern_key, None)
    
    if colors_off and not isinstance(colors_off, list):
        colors_off = [colors_off]
    
    staff_off_names = []
    if colors_off:
        for color in colors_off:
            if color in ['red', 'yellow', 'green', 'blue'] and color in porter_groups:
                if 'shift1' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift1'])
                if 'shift2' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift2'])
    
    # Night shift rotation
    night_shift_rotation = {
        (0, 0): 'purple', (0, 1): 'purple', (0, 2): 'darkred', (0, 3): 'darkgreen',
        (0, 4): 'darkgreen', (0, 5): 'brownishyellow', (0, 6): ['brownishyellow', 'purple'],
        (1, 0): 'darkred', (1, 1): 'darkred', (1, 2): 'darkgreen', (1, 3): 'brownishyellow',
        (1, 4): 'brownishyellow', (1, 5): 'purple', (1, 6): ['purple', 'darkred'],
        (2, 0): 'darkgreen', (2, 1): 'darkgreen', (2, 2): 'brownishyellow', (2, 3): 'purple',
        (2, 4): 'purple', (2, 5): 'darkred', (2, 6): ['darkred', 'darkgreen'],
        (3, 0): 'brownishyellow', (3, 1): 'brownishyellow', (3, 2): 'purple', (3, 3): 'darkred',
        (3, 4): 'darkred', (3, 5): 'darkgreen', (3, 6): ['darkgreen', 'brownishyellow'],
    }
    
    night_colors_off = night_shift_rotation.get(pattern_key, None)
    if night_colors_off and not isinstance(night_colors_off, list):
        night_colors_off = [night_colors_off]
    
    if night_colors_off:
        for color in night_colors_off:
            if color in porter_groups:
                if 'shift3' in porter_groups[color]:
                    staff_off_names.append(porter_groups[color]['shift3'])
    
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
    
    # Build HTML email
    html = f"""<!DOCTYPE html>
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
"""
    
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
            
            html += f"""
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
"""
    else:
        html += '<div style="font-size: 13px; color: #666;">No staff assigned</div>'
    
    html += """
                            </div>
                        </td>
                        
                        <!-- Shift 2 -->
                        <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                            <div style="background: #e0f2f7; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px 15px; text-align: center;">
                                <div style="font-weight: bold; font-size: 14px; color: #000; margin-bottom: 15px; background: #cce7f0; padding: 8px; border-radius: 4px;">SHIFT 2</div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 15px;">(2pm-10pm / 7am-2pm)</div>
"""
    
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
            
            html += f"""
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
"""
    else:
        html += '<div style="font-size: 13px; color: #666;">No staff assigned</div>'
    
    html += """
                            </div>
                        </td>
                        
                        <!-- Night Shift -->
                        <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                            <div style="background: #e0f2f7; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px 15px; text-align: center;">
                                <div style="font-weight: bold; font-size: 14px; color: #000; margin-bottom: 15px; background: #cce7f0; padding: 8px; border-radius: 4px;">NIGHT SHIFT</div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 15px;">(10pm-7am)</div>
"""
    
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
            
            html += f"""
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
"""
    else:
        html += '<div style="font-size: 13px; color: #666;">No staff assigned</div>'
    
    html += """
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Daily Occurrences Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2c3e50; font-size: 1.5em; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Daily Occurrences</h2>
"""
    
    # Add occurrences table or "no occurrences" message
    if not occurrences or len(occurrences) == 0:
        html += """
                <div style="background: #d4edda; color: #155724; padding: 20px; border-radius: 8px; text-align: center; font-size: 1.1em;">
                    No incidents or occurrences were recorded today.
                </div>
"""
    else:
        html += """
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
"""
        
        for occurrence in occurrences:
            html += f"""
                        <tr>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.time}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.flat_number}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: center; background: white;">{occurrence.reported_by}</td>
                            <td style="padding: 12px 10px; border: 2px solid #dee2e6; text-align: left; background: white;">{occurrence.description}</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
"""
    
    html += """
            </div>
            
            <!-- Water Temperature Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2c3e50; font-size: 1.5em; margin-bottom: 20px; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Water Temperature Readings</h2>
"""
    
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
        
        html += f"""
                <div style="background: white; border: 2px solid #dee2e6; border-radius: 8px; padding: 20px; font-size: 1em; line-height: 1.6;">
                    {temp_text}
                </div>
"""
    else:
        html += """
                <div style="background: #f8f9fa; color: #6c757d; padding: 20px; border-radius: 8px; text-align: center; font-size: 1.1em;">
                    No water temperature readings recorded today.
                </div>
"""
    
    html += """
            </div>
            
        </div>
        
    </div>
</body>
</html>
"""
    
    return html


def log_email_to_file(sender_email, recipients, subject, status, error_message=None):
    """Log email attempts to a file for detailed debugging"""
    try:
        log_dir = os.path.join(USER_DATA_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'email_log.txt')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"From: {sender_email}\n")
            f.write(f"To: {', '.join(recipients) if isinstance(recipients, list) else recipients}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Status: {status}\n")
            if error_message:
                f.write(f"Error: {error_message}\n")
            f.write(f"{'='*80}\n")
    except Exception as e:
        print(Fore.YELLOW + f"Warning: Could not write to email log file: {e}")

def send_email_with_pdf(pdf_path, subject, recipient=None):
    """Send email with PDF attachment - supports multiple recipients
    Returns: (success: bool, error_message: str)"""
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
            # Fallback to config.py for backwards compatibility
            sender_email = EMAIL_CONFIG['email']
            sender_password = EMAIL_CONFIG['password']
            smtp_server = EMAIL_CONFIG['smtp_server']
            smtp_port = EMAIL_CONFIG['smtp_port']
        
        if recipient is None:
            recipient = EMAIL_CONFIG['recipient']
        
        # Parse multiple email addresses (comma or semicolon separated)
        if isinstance(recipient, str):
            # Split by comma or semicolon and clean up whitespace
            recipients = [email.strip() for email in recipient.replace(';', ',').split(',') if email.strip()]
        else:
            recipients = recipient
            
        # Get occurrences and report date from the subject line
        # Extract date from subject like "Daily Report - 2025-10-21"
        try:
            report_date_str = subject.split(' - ')[1]
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        except:
            report_date = datetime.now().date()
        
        # Get occurrences for the report date
        next_day = report_date + timedelta(days=1)
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= report_date,
            DailyOccurrence.timestamp < next_day
        ).all()
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)  # Display all recipients in header
        msg['Subject'] = subject
        
        # Generate beautiful HTML email body that matches the webpage styling
        html_body = generate_email_html(occurrences, report_date)
        msg.attach(MIMEText(html_body, 'html'))
        
        # Note: PDF attachment removed as per user request - email contains only HTML styling
        
        # Send email to all recipients
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipients, text)  # Send to list of recipients
        server.quit()
        
        print(Fore.GREEN + f"Email sent successfully from {sender_email} to: {', '.join(recipients)}")
        log_email_to_file(sender_email, recipients, subject, 'success')
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP Authentication Error: {str(e)}. Check your email and app password."
        print(Fore.RED + f"Error sending email: {error_msg}")
        log_email_to_file(sender_email if 'sender_email' in locals() else 'unknown', 
                         recipients if 'recipients' in locals() else [], 
                         subject, 'failed', error_msg)
        return False, error_msg
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"SMTP Recipients Refused: {str(e)}. One or more email addresses may be invalid."
        print(Fore.RED + f"Error sending email: {error_msg}")
        log_email_to_file(sender_email if 'sender_email' in locals() else 'unknown', 
                         recipients if 'recipients' in locals() else [], 
                         subject, 'failed', error_msg)
        return False, error_msg
    except smtplib.SMTPServerDisconnected as e:
        error_msg = f"SMTP Server Disconnected: {str(e)}. Server may have closed the connection."
        print(Fore.RED + f"Error sending email: {error_msg}")
        log_email_to_file(sender_email if 'sender_email' in locals() else 'unknown', 
                         recipients if 'recipients' in locals() else [], 
                         subject, 'failed', error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        print(Fore.RED + error_msg)
        log_email_to_file(sender_email if 'sender_email' in locals() else 'unknown', 
                         recipients if 'recipients' in locals() else [], 
                         subject, 'failed', error_msg)
        return False, error_msg

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon"""
    # Handle both development and compiled (PyInstaller) modes
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe - use PyInstaller's resource path
        base_path = sys._MEIPASS
    else:
        # Running as Python script - use project directory
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    ico_path = os.path.join(base_path, 'diary.ico')
    if os.path.exists(ico_path):
        return send_file(ico_path, mimetype='image/x-icon')
    return '', 404

@app.route('/doc')
def doc():
    """Serve the maintenance diary form"""
    response = make_response(render_template('doc.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/maintenance-entries', methods=['GET', 'POST'])
def maintenance_entries():
    """Handle GET (list/search) and POST (create) for maintenance entries"""
    import sqlite3
    
    if request.method == 'POST':
        # Create new entry
        data = request.json
        conn = None
        try:
            conn = sqlite3.connect(maintenance_db_path)
            cursor = conn.cursor()
            
            # Generate ID if not provided
            entry_id = data.get('id')
            if not entry_id:
                # Get max ID and increment
                cursor.execute('SELECT MAX(CAST(ID AS INTEGER)) FROM Maintenance_Book_2 WHERE ID GLOB "[0-9]*"')
                result = cursor.fetchone()
                max_id = result[0] if result[0] else 0
                entry_id = str(max_id + 1)
            
            cursor.execute("""
                INSERT INTO Maintenance_Book_2 
                (ID, Property, DateIn, TimeIn, Employee, "Details of Fault", 
                 "Maintenance Name", DateDone, TimeDone, "Action taken", 
                 "Further action details", Department, HW, CW, CH, CompletionDate, ContactDetails)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                data.get('property', ''),
                data.get('dateIn', ''),
                data.get('timeIn', ''),
                data.get('employee', ''),
                data.get('detailsOfFault', ''),
                data.get('maintenanceName', ''),
                data.get('dateDone', ''),
                data.get('timeDone', ''),
                data.get('actionTaken', ''),
                data.get('furtherAction', ''),
                data.get('department', ''),
                data.get('hw', '0'),
                data.get('cw', '0'),
                data.get('ch', '0'),
                data.get('completionDate', ''),
                data.get('contactDetails', '')
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'id': entry_id, 'message': 'Entry saved successfully'})
        except Exception as e:
            if conn:
                conn.close()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    # GET request - list entries
    entry_id = request.args.get('id')
    limit = request.args.get('limit', 100, type=int)
    date_from = request.args.get('dateFrom')
    date_to = request.args.get('dateTo')
    conn = None
    
    try:
        conn = sqlite3.connect(maintenance_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if entry_id:
            cursor.execute('SELECT * FROM Maintenance_Book_2 WHERE ID = ?', (entry_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                entry_data = dict(row)
                images = MaintenanceImage.query.filter_by(maintenance_id=str(entry_id)).all()
                entry_data['images'] = [{
                    'id': img.id,
                    'filename': img.filename,
                    'url': f'/uploads/{img.filepath.replace("\\", "/")}',
                    'file_size': img.file_size
                } for img in images]
                entry_data['image_count'] = len(images)
                return jsonify(entry_data)
            return jsonify({'error': 'Entry not found'}), 404
        else:
            # Build query with optional date filtering
            query = 'SELECT * FROM Maintenance_Book_2 WHERE 1=1'
            params = []
            
            if date_from:
                query += ' AND DateIn >= ?'
                params.append(date_from)
            
            if date_to:
                query += ' AND DateIn <= ?'
                params.append(date_to)
            
            query += ' ORDER BY DateIn DESC'
            
            # If limit is 0 or negative, load all entries (no limit)
            if limit > 0:
                query += ' LIMIT ?'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Enrich with images
            results = []
            for row in rows:
                entry_data = dict(row)
                images = MaintenanceImage.query.filter_by(maintenance_id=str(entry_data['ID'])).all()
                entry_data['images'] = [{
                    'id': img.id,
                    'filename': img.filename,
                    'url': f'/uploads/{img.filepath.replace("\\", "/")}',
                    'file_size': img.file_size
                } for img in images]
                entry_data['image_count'] = len(images)
                results.append(entry_data)
                
            return jsonify(results)
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/maintenance-entries/<entry_id>', methods=['PUT', 'DELETE'])
def maintenance_entry(entry_id):
    """Handle UPDATE and DELETE for a specific maintenance entry"""
    import sqlite3
    
    if request.method == 'PUT':
        # Update entry
        data = request.json
        conn = None
        try:
            conn = sqlite3.connect(maintenance_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE Maintenance_Book_2 SET
                Property = ?, DateIn = ?, TimeIn = ?, Employee = ?,
                "Details of Fault" = ?, "Maintenance Name" = ?, DateDone = ?,
                TimeDone = ?, "Action taken" = ?, "Further action details" = ?,
                Department = ?, HW = ?, CW = ?, CH = ?, CompletionDate = ?,
                ContactDetails = ?
                WHERE ID = ?
            """, (
                data.get('property', ''),
                data.get('dateIn', ''),
                data.get('timeIn', ''),
                data.get('employee', ''),
                data.get('detailsOfFault', ''),
                data.get('maintenanceName', ''),
                data.get('dateDone', ''),
                data.get('timeDone', ''),
                data.get('actionTaken', ''),
                data.get('furtherAction', ''),
                data.get('department', ''),
                data.get('hw', '0'),
                data.get('cw', '0'),
                data.get('ch', '0'),
                data.get('completionDate', ''),
                data.get('contactDetails', ''),
                entry_id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Entry updated successfully'})
        except Exception as e:
            if conn:
                conn.close()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        # Delete entry
        conn = None
        try:
            conn = sqlite3.connect(maintenance_db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM Maintenance_Book_2 WHERE ID = ?', (entry_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Entry deleted successfully'})
        except Exception as e:
            if conn:
                conn.close()
            return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/daily-occurrences', methods=['GET', 'POST'])
def daily_occurrences():
    if request.method == 'POST':
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
    
    # GET request - return today's occurrences
    today = datetime.now().date()
    tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
    
    occurrences = DailyOccurrence.query.filter(
        DailyOccurrence.timestamp >= today,
        DailyOccurrence.timestamp < tomorrow
    ).order_by(DailyOccurrence.timestamp.desc()).all()
    
    results = []
    for o in occurrences:
        # Fetch associated images
        images = OccurrenceImage.query.filter_by(occurrence_id=o.id).all()
        image_list = [{
            'id': img.id,
            'filename': img.filename,
            'url': f'/uploads/{img.filepath.replace("\\", "/")}',
            'file_size': img.file_size
        } for img in images]
        
        results.append({
            'id': o.id,
            'time': o.time,
            'flat_number': o.flat_number,
            'reported_by': o.reported_by,
            'description': o.description,
            'timestamp': o.timestamp.isoformat(),
            'images': image_list,
            'image_count': len(image_list)
        })
    
    return jsonify(results)

@app.route('/api/daily-occurrences/<int:occurrence_id>', methods=['DELETE'])
def delete_daily_occurrence(occurrence_id):
    occurrence = db.session.get(DailyOccurrence, occurrence_id)
    if occurrence:
        # Get user name from request
        data = request.get_json() or {}
        user_name = data.get('user_name', 'Unknown')
        
        # Log the deletion
        description = f"Deleted occurrence: {occurrence.time} - Flat {occurrence.flat_number} - {occurrence.description[:50]}..."
        log_activity(user_name, 'delete', 'occurrence', description, occurrence_id, request.remote_addr)
        
        # Delete associated images
        images = OccurrenceImage.query.filter_by(occurrence_id=occurrence_id).all()
        for img in images:
            delete_image_file(img.filepath)
            db.session.delete(img)
        
        db.session.delete(occurrence)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Occurrence not found'}), 404

# Image upload endpoints
@app.route('/api/upload-occurrence-image', methods=['POST'])
def upload_occurrence_image():
    """Upload image for a daily occurrence"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        occurrence_id = request.form.get('occurrence_id')
        
        if not occurrence_id:
            return jsonify({'success': False, 'error': 'No occurrence ID provided'}), 400
        
        # Check if occurrence exists
        occurrence = db.session.get(DailyOccurrence, int(occurrence_id))
        if not occurrence:
            return jsonify({'success': False, 'error': 'Occurrence not found'}), 404
        
        # Check image limit
        existing_count = OccurrenceImage.query.filter_by(occurrence_id=occurrence_id).count()
        if existing_count >= MAX_IMAGES_PER_ENTRY:
            return jsonify({'success': False, 'error': f'Maximum {MAX_IMAGES_PER_ENTRY} images per entry'}), 400
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File size exceeds 10MB limit'}), 400
        
        # Save image
        image_data = save_uploaded_image(file, 'occurrence', occurrence_id)
        if not image_data:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Create database record
        image_record = OccurrenceImage(
            occurrence_id=occurrence_id,
            filename=image_data['filename'],
            filepath=image_data['filepath'],
            file_size=image_data['file_size']
        )
        db.session.add(image_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image': {
                'id': image_record.id,
                'filename': image_record.filename,
                'url': f'/uploads/{image_record.filepath}',
                'file_size': image_record.file_size
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-maintenance-image', methods=['POST'])
def upload_maintenance_image():
    """Upload image for a maintenance entry"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        maintenance_id = request.form.get('maintenance_id')
        
        if not maintenance_id:
            return jsonify({'success': False, 'error': 'No maintenance ID provided'}), 400
        
        # Check image limit
        existing_count = MaintenanceImage.query.filter_by(maintenance_id=maintenance_id).count()
        if existing_count >= MAX_IMAGES_PER_ENTRY:
            return jsonify({'success': False, 'error': f'Maximum {MAX_IMAGES_PER_ENTRY} images per entry'}), 400
        
        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File size exceeds 10MB limit'}), 400
        
        # Save image
        image_data = save_uploaded_image(file, 'maintenance', maintenance_id)
        if not image_data:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Create database record
        image_record = MaintenanceImage(
            maintenance_id=maintenance_id,
            filename=image_data['filename'],
            filepath=image_data['filepath'],
            file_size=image_data['file_size']
        )
        db.session.add(image_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image': {
                'id': image_record.id,
                'filename': image_record.filename,
                'url': f'/uploads/{image_record.filepath.replace("\\", "/")}',
                'file_size': image_record.file_size
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/occurrence-images/<int:occurrence_id>', methods=['GET'])
def get_occurrence_images(occurrence_id):
    """Get all images for an occurrence"""
    try:
        images = get_images_for_entry('occurrence', occurrence_id)
        return jsonify({'success': True, 'images': images})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/maintenance-images/<maintenance_id>', methods=['GET'])
def get_maintenance_images(maintenance_id):
    """Get all images for a maintenance entry"""
    try:
        images = get_images_for_entry('maintenance', maintenance_id)
        return jsonify({'success': True, 'images': images})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image"""
    try:
        image_type = request.args.get('type', 'occurrence')
        
        if image_type == 'occurrence':
            image = db.session.get(OccurrenceImage, image_id)
        else:
            image = db.session.get(MaintenanceImage, image_id)
        
        if not image:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        # Delete file from filesystem
        delete_image_file(image.filepath)
        
        # Delete database record
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded images"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/maintenance-pdf', methods=['POST'])
def generate_maintenance_pdf_route():
    """Endpoint to generate PDF for selected maintenance entries"""
    data = request.json
    entry_ids = data.get('ids', [])
    
    if not entry_ids:
        return jsonify({'success': False, 'error': 'No entries selected'}), 400
    
    import sqlite3
    try:
        conn = sqlite3.connect(maintenance_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query for the selected IDs
        placeholders = ', '.join(['?'] * len(entry_ids))
        query = f'SELECT * FROM Maintenance_Book_2 WHERE ID IN ({placeholders}) ORDER BY DateIn DESC'
        cursor.execute(query, entry_ids)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return jsonify({'success': False, 'error': 'Entries not found'}), 404
            
        entries = []
        for row in rows:
            entry_data = dict(row)
            # Fetch images
            images = MaintenanceImage.query.filter_by(maintenance_id=str(entry_data['ID'])).all()
            entry_data['images'] = [{'filepath': img.filepath} for img in images]
            entries.append(entry_data)
            
        pdf_path = generate_maintenance_pdf(entries)
        return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-daily-pdf', methods=['GET'])
def generate_daily_pdf_route():
    """Manually trigger daily PDF generation for a specific date"""
    date_str = request.args.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format (YYYY-MM-DD)'}), 400
    else:
        report_date = datetime.now().date()
        
    # Get occurrences for the date
    next_day = report_date + timedelta(days=1)
    occurrences = DailyOccurrence.query.filter(
        DailyOccurrence.timestamp >= report_date,
        DailyOccurrence.timestamp < next_day
    ).all()
    
    try:
        pdf_path = generate_daily_pdf(occurrences, report_date)
        return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff-rota', methods=['GET', 'POST'])
def staff_rota():
    if request.method == 'POST':
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
    
    # GET request
    start_date = request.args.get('start_date', datetime.now().date().isoformat())
    end_date = request.args.get('end_date', (datetime.now() + timedelta(days=30)).date().isoformat())
    
    rotas = StaffRota.query.filter(
        StaffRota.date >= start_date,
        StaffRota.date <= end_date
    ).order_by(StaffRota.date).all()
    
    # Reference date for rotation calculation
    reference_date = datetime(2025, 9, 29).date()
    
    # Rotation patterns
    rotation_pattern = {
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
    
    night_shift_rotation = {
        # Week 1
        (0, 0): 'purple', (0, 1): 'purple', (0, 2): 'darkred', (0, 3): 'darkgreen',
        (0, 4): 'darkgreen', (0, 5): 'brownishyellow', (0, 6): ['brownishyellow', 'purple'],
        # Week 2
        (1, 0): 'darkred', (1, 1): 'darkred', (1, 2): 'darkgreen', (1, 3): 'brownishyellow',
        (1, 4): 'brownishyellow', (1, 5): 'purple', (1, 6): ['purple', 'darkred'],
        # Week 3
        (2, 0): 'darkgreen', (2, 1): 'darkgreen', (2, 2): 'brownishyellow', (2, 3): 'purple',
        (2, 4): 'purple', (2, 5): 'darkred', (2, 6): ['darkred', 'darkgreen'],
        # Week 4
        (3, 0): 'brownishyellow', (3, 1): 'brownishyellow', (3, 2): 'purple', (3, 3): 'darkred',
        (3, 4): 'darkred', (3, 5): 'darkgreen', (3, 6): ['darkgreen', 'brownishyellow'],
    }
    
    # Build response with working day calculation
    result = []
    for r in rotas:
        # Get staff member info
        staff = StaffMember.query.filter_by(name=r.staff_name).first()
        is_working_day = True  # Default to true if we can't determine
        
        if staff:
            # Calculate rotation for this date
            days_diff = (r.date - reference_date).days
            week_in_cycle = (days_diff // 7) % 4
            day_of_week = r.date.weekday()
            pattern_key = (week_in_cycle, day_of_week)
            
            is_scheduled_off = False
            
            if staff.shift in [1, 2]:
                # Day shift rotation
                colors_off = rotation_pattern.get(pattern_key, None)
                if colors_off and not isinstance(colors_off, list):
                    colors_off = [colors_off]
                
                if colors_off and staff.color in colors_off:
                    is_scheduled_off = True
                    
            elif staff.shift == 3:
                # Night shift rotation
                night_colors_off = night_shift_rotation.get(pattern_key, None)
                if night_colors_off and not isinstance(night_colors_off, list):
                    night_colors_off = [night_colors_off]
                
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
    rota = db.session.get(StaffRota, rota_id)
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
    
    # Reference date for rotation calculation
    reference_date = datetime(2025, 9, 29).date()
    
    # Rotation patterns (same as in staff_schedule function)
    rotation_pattern = {
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
    
    night_shift_rotation = {
        # Week 1
        (0, 0): 'purple', (0, 1): 'purple', (0, 2): 'darkred', (0, 3): 'darkgreen',
        (0, 4): 'darkgreen', (0, 5): 'brownishyellow', (0, 6): ['brownishyellow', 'purple'],
        # Week 2
        (1, 0): 'darkred', (1, 1): 'darkred', (1, 2): 'darkgreen', (1, 3): 'brownishyellow',
        (1, 4): 'brownishyellow', (1, 5): 'purple', (1, 6): ['purple', 'darkred'],
        # Week 3
        (2, 0): 'darkgreen', (2, 1): 'darkgreen', (2, 2): 'brownishyellow', (2, 3): 'purple',
        (2, 4): 'purple', (2, 5): 'darkred', (2, 6): ['darkred', 'darkgreen'],
        # Week 4
        (3, 0): 'brownishyellow', (3, 1): 'brownishyellow', (3, 2): 'purple', (3, 3): 'darkred',
        (3, 4): 'darkred', (3, 5): 'darkgreen', (3, 6): ['darkgreen', 'brownishyellow'],
    }
    
    # Create entries for each day in range
    current_date = date_from
    days_added = 0
    working_days_count = 0  # Only count days they were supposed to work
    
    while current_date <= date_to:
        # Calculate if this person was scheduled to work on this day
        days_diff = (current_date - reference_date).days
        week_in_cycle = (days_diff // 7) % 4
        day_of_week = current_date.weekday()
        pattern_key = (week_in_cycle, day_of_week)
        
        is_scheduled_off = False
        
        if staff.shift in [1, 2]:
            # Day shift rotation
            colors_off = rotation_pattern.get(pattern_key, None)
            if colors_off and not isinstance(colors_off, list):
                colors_off = [colors_off]
            
            if colors_off and staff.color in colors_off:
                is_scheduled_off = True
                
        elif staff.shift == 3:
            # Night shift rotation
            night_colors_off = night_shift_rotation.get(pattern_key, None)
            if night_colors_off and not isinstance(night_colors_off, list):
                night_colors_off = [night_colors_off]
            
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

@app.route('/api/staff-rota-duplicates', methods=['GET', 'DELETE'])
def staff_rota_duplicates():
    """Find and optionally remove duplicate staff rota entries"""
    try:
        # Find all rota entries
        all_rotas = StaffRota.query.all()
        
        # Group by staff_name, date, and status to find duplicates
        seen = {}
        duplicates = []
        
        for rota in all_rotas:
            key = (rota.staff_name, rota.date, rota.status)
            if key in seen:
                # This is a duplicate
                duplicates.append({
                    'id': rota.id,
                    'staff_name': rota.staff_name,
                    'date': rota.date.isoformat(),
                    'status': rota.status,
                    'notes': rota.notes,
                    'original_id': seen[key]
                })
            else:
                seen[key] = rota.id
        
        if request.method == 'GET':
            # Just return the list of duplicates
            return jsonify({
                'success': True,
                'count': len(duplicates),
                'duplicates': duplicates
            })
        
        elif request.method == 'DELETE':
            # Remove the duplicate entries (keep the first one)
            deleted_count = 0
            for dup in duplicates:
                rota = db.session.get(StaffRota, dup['id'])
                if rota:
                    db.session.delete(rota)
                    deleted_count += 1
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Removed {deleted_count} duplicate entries'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/staff-schedule/<int:staff_id>', methods=['GET'])
def staff_schedule(staff_id):
    """Get individual staff member's schedule for a date range"""
    # Get staff member
    staff = db.session.get(StaffMember, staff_id)
    if not staff:
        return jsonify({'success': False, 'error': 'Staff member not found'}), 404
    
    # Get date range parameters
    start_date_str = request.args.get('start_date', datetime.now().date().isoformat())
    end_date_str = request.args.get('end_date', (datetime.now() + timedelta(days=30)).date().isoformat())
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get porter groups for rotation calculation
    porter_groups, all_staff = get_porter_groups()
    
    # Rotation patterns
    rotation_pattern = {
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
    
    night_shift_rotation = {
        # Week 1
        (0, 0): 'purple', (0, 1): 'purple', (0, 2): 'darkred', (0, 3): 'darkgreen',
        (0, 4): 'darkgreen', (0, 5): 'brownishyellow', (0, 6): ['brownishyellow', 'purple'],
        # Week 2
        (1, 0): 'darkred', (1, 1): 'darkred', (1, 2): 'darkgreen', (1, 3): 'brownishyellow',
        (1, 4): 'brownishyellow', (1, 5): 'purple', (1, 6): ['purple', 'darkred'],
        # Week 3
        (2, 0): 'darkgreen', (2, 1): 'darkgreen', (2, 2): 'brownishyellow', (2, 3): 'purple',
        (2, 4): 'purple', (2, 5): 'darkred', (2, 6): ['darkred', 'darkgreen'],
        # Week 4
        (3, 0): 'brownishyellow', (3, 1): 'brownishyellow', (3, 2): 'purple', (3, 3): 'darkred',
        (3, 4): 'darkred', (3, 5): 'darkgreen', (3, 6): ['darkgreen', 'brownishyellow'],
    }
    
    # Reference date for rotation calculation
    reference_date = datetime(2025, 9, 29).date()
    
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
        days_diff = (current - reference_date).days
        week_in_cycle = (days_diff // 7) % 4
        day_of_week = current.weekday()
        pattern_key = (week_in_cycle, day_of_week)
        
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
                colors_off = rotation_pattern.get(pattern_key, None)
                if colors_off and not isinstance(colors_off, list):
                    colors_off = [colors_off]
                
                if colors_off and staff.color in colors_off:
                    is_off = True
                    
            elif staff.shift == 3:
                # Night shift rotation
                night_colors_off = night_shift_rotation.get(pattern_key, None)
                if night_colors_off and not isinstance(night_colors_off, list):
                    night_colors_off = [night_colors_off]
                
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
    
    # 4-week rotation pattern (which color is off on which day)
    # Week number (0-3), Day of week (0=Monday, 6=Sunday)
    # Sundays can have multiple colors (as list) - 2 people off per shift
    rotation_pattern = {
        # Week 1
        (0, 0): 'blue',   # Monday
        (0, 1): 'green',  # Tuesday
        (0, 2): 'green',  # Wednesday
        (0, 3): 'yellow', # Thursday
        (0, 4): 'blue',   # Friday
        (0, 5): 'red',    # Saturday
        (0, 6): ['red', 'yellow'],    # Sunday - 2 colors = 4 people
        # Week 2
        (1, 0): 'red',
        (1, 1): 'blue',
        (1, 2): 'blue',
        (1, 3): 'green',
        (1, 4): 'red',
        (1, 5): 'yellow',
        (1, 6): ['yellow', 'green'],  # Sunday - 2 colors = 4 people
        # Week 3
        (2, 0): 'yellow',
        (2, 1): 'red',
        (2, 2): 'red',
        (2, 3): 'blue',
        (2, 4): 'yellow',
        (2, 5): 'green',
        (2, 6): ['green', 'blue'],    # Sunday - 2 colors = 4 people
        # Week 4
        (3, 0): 'green',
        (3, 1): 'yellow',
        (3, 2): 'yellow',
        (3, 3): 'red',
        (3, 4): 'green',
        (3, 5): 'blue',
        (3, 6): ['blue', 'red'],      # Sunday - 2 colors = 4 people
    }
    
    # Reference date (start of week 1) - set this to a known Monday
    # Week 3 is Oct 13-19, so Week 1 started on Sept 29, 2025
    reference_date = datetime(2025, 9, 29).date()  # Monday of Week 1
    
    schedule = []
    current = start
    while current <= end:
        # Calculate which week in the 4-week cycle
        days_diff = (current - reference_date).days
        week_in_cycle = (days_diff // 7) % 4
        day_of_week = current.weekday()  # 0=Monday, 6=Sunday
        
        week_number = week_in_cycle + 1
        
        # Get which color group(s) are off
        pattern_key = (week_in_cycle, day_of_week)
        colors_off = rotation_pattern.get(pattern_key, None)
        
        # Ensure colors_off is always a list for uniform processing
        if colors_off and not isinstance(colors_off, list):
            colors_off = [colors_off]
        
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
        night_rotation = {
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
        
        # Get night shift colors off
        night_pattern_key = (week_in_cycle, day_of_week)
        night_colors_off = night_rotation.get(night_pattern_key, None)
        if night_colors_off and not isinstance(night_colors_off, list):
            night_colors_off = [night_colors_off]
        
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
    temp = db.session.get(WaterTemperature, temp_id)
    if not temp:
        return jsonify({'success': False, 'error': 'Temperature record not found'}), 404
    
    db.session.delete(temp)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/update-fault-status', methods=['POST'])
def update_fault_status():
    data = request.json
    fault = db.session.get(CCTVFault, data['id'])
    if fault:
        fault.status = data['status']
        if data['status'] == 'closed':
            fault.resolved_date = datetime.now()
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/cctv-faults/<int:fault_id>', methods=['PUT'])
def update_cctv_fault(fault_id):
    """Update an existing CCTV/Intercom fault (only open/in_progress faults can be edited)"""
    fault = db.session.get(CCTVFault, fault_id)
    if not fault:
        return jsonify({'success': False, 'error': 'Fault not found'}), 404
    
    # Only allow editing of open or in_progress faults
    if fault.status == 'closed':
        return jsonify({'success': False, 'error': 'Closed faults cannot be edited'}), 400
    
    data = request.json
    
    # Update editable fields
    if 'fault_type' in data:
        fault.fault_type = data['fault_type']
    if 'flat_number' in data:
        fault.flat_number = data.get('flat_number', '')
    if 'block_number' in data:
        fault.block_number = data.get('block_number', '')
    if 'floor_number' in data:
        fault.floor_number = data.get('floor_number', '')
    if 'description' in data:
        fault.description = data['description']
    if 'contact_details' in data:
        fault.contact_details = data.get('contact_details', '')
    if 'additional_notes' in data:
        fault.additional_notes = data.get('additional_notes', '')
    
    # Rebuild location string from components for backwards compatibility
    location_parts = []
    if fault.flat_number:
        location_parts.append(f"Flat {fault.flat_number}")
    if fault.block_number:
        location_parts.append(f"Block {fault.block_number}")
    if fault.floor_number:
        location_parts.append(f"Floor {fault.floor_number}")
    fault.location = ' | '.join(location_parts) if location_parts else ''
    
    db.session.commit()
    return jsonify({'success': True, 'id': fault.id})

@app.route('/api/delete-fault/<int:fault_id>', methods=['DELETE'])
def delete_fault(fault_id):
    fault = db.session.get(CCTVFault, fault_id)
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
        
        # Send test email with HTML styling (no PDF attachment)
        print(Fore.CYAN + f"Attempting to send HTML email (no PDF attachment)...")
        email_sent, error_message = send_email_with_pdf(
            pdf_path, 
            f"TEST - Daily Report - {today}", 
            settings.recipient_email
        )
        
        if email_sent:
            occurrence_count = len(occurrences) if occurrences else 0
            print(Fore.GREEN + f"✓ HTML email sent successfully (no PDF attachment)!")
            print(Fore.CYAN + Style.BRIGHT + f"{'='*50}\n")
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {settings.recipient_email}!\n\nEmail includes:\n- Beautiful HTML styling\n- {occurrence_count} occurrence(s)\n- Staff schedule in 3 columns\n- Water temperature readings\n\nNo PDF attachment (as requested)\n\nCheck your inbox!',
                'count': occurrence_count
            })
        else:
            error_details = error_message if error_message else 'Unknown error'
            print(Fore.RED + f"✗ Email failed to send!")
            if error_message:
                print(Fore.RED + f"Error: {error_message}")
            print(Fore.CYAN + Style.BRIGHT + f"{'='*50}\n")
            return jsonify({
                'success': False,
                'error': f'Failed to send test email.\n\nError: {error_details}\n\nCommon issues:\n- Wrong email/password\n- Gmail: Need App Password, not regular password\n- Firewall blocking SMTP\n- Check spam folder\n\nCheck the email log file at {os.path.join(USER_DATA_DIR, "logs", "email_log.txt")} for more details.'
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
    """Manually trigger a Google Drive backup for both databases"""
    try:
        print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "MANUAL GOOGLE DRIVE BACKUP")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        
        # Backup both databases simultaneously
        diary_success, maintenance_success = backup_all_databases_to_gdrive()
        
        print(Fore.CYAN + Style.BRIGHT + "=" * 50 + "\n")
        
        if diary_success and maintenance_success:
            return jsonify({
                'success': True,
                'message': 'Both databases successfully backed up to Google Drive!\n\nFiles:\n- diary_latest.db\n- maintenance_latest.db\n\nFolder: Diary_Backups\n\nOnly the latest backups are kept in Google Drive.'
            })
        elif diary_success:
            return jsonify({
                'success': True,
                'message': 'Diary database backed up successfully!\n\nMaintenance database backup failed. Check console for details.\n\nFile: diary_latest.db\nFolder: Diary_Backups'
            })
        elif maintenance_success:
            return jsonify({
                'success': True,
                'message': 'Maintenance database backed up successfully!\n\nDiary database backup failed. Check console for details.\n\nFile: maintenance_latest.db\nFolder: Diary_Backups'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Backup failed. Check console for details.\n\nCommon issues:\n- credentials.json file missing\n- Invalid or expired OAuth2 token\n- No internet connection\n- Google Drive API not enabled\n- Need to re-authorize (delete token.pickle and try again)'
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
        log_dir = os.path.join(USER_DATA_DIR, 'logs')
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
        log_dir = os.path.join(USER_DATA_DIR, 'logs')
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
        log_dir = os.path.join(USER_DATA_DIR, 'logs')
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
def verify_settings_pin():
    """Verify PIN for settings access - checks all shift leaders"""
    try:
        data = request.json
        pin = data.get('pin')
        
        if not pin:
            return jsonify({'success': False, 'error': 'PIN required'})
        
        # Hash the entered PIN
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        
        # Check all active shift leaders for matching PIN
        all_leaders = ShiftLeader.query.filter_by(active=True).all()
        
        for shift_leader in all_leaders:
            if shift_leader.pin == pin_hash:
                # Success - found matching PIN
                shift_leader.last_login = datetime.now()
                db.session.commit()
                
                log_settings_access(shift_leader.name, 'Settings Access Granted', True, request.remote_addr)
                return jsonify({
                    'success': True,
                    'name': shift_leader.name
                })
        
        # No matching PIN found
        log_settings_access('Unknown User', 'Settings Access Attempt - Invalid PIN', False, request.remote_addr)
        return jsonify({'success': False, 'error': 'Invalid PIN'})
        
    except Exception as e:
        print(Fore.RED + f"Error verifying settings PIN: {e}")
        log_settings_access('Unknown', f'Settings Access Error: {str(e)}', False, request.remote_addr)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings-access-logs', methods=['GET'])
def get_settings_access_logs():
    """Get recent settings access logs"""
    try:
        log_file = os.path.join(USER_DATA_DIR, 'logs', 'settings_access.log')
        
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
        'pdf_path': log.pdf_path,
        'status': getattr(log, 'status', 'unknown'),  # Handle old records without status
        'error_message': getattr(log, 'error_message', '')  # Handle old records without error_message
    } for log in logs])

@app.route('/api/staff-members', methods=['GET', 'POST'])
def staff_members():
    if request.method == 'POST':
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
    staff = db.session.get(StaffMember, staff_id)
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
    
    # Hash the provided PIN
    hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
    
    # Find shift leader by PIN hash
    leader = ShiftLeader.query.filter(
        ShiftLeader.pin == hashed_pin,
        ShiftLeader.active == True
    ).first()
    
    if not leader:
        return jsonify({'success': False, 'error': 'Invalid PIN'}), 401
    
    # Update last login time
    leader.last_login = datetime.now()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'leader': {
            'id': leader.id,
            'name': leader.name
        }
    })

@app.route('/api/shift-leaders', methods=['GET'])
def get_shift_leaders():
    """Get list of active shift leaders (names only, no PINs)"""
    leaders = ShiftLeader.query.filter_by(active=True).order_by(ShiftLeader.name).all()
    return jsonify([{
        'id': leader.id,
        'name': leader.name
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
    
    # Verify old PIN
    hashed_old_pin = hashlib.sha256(old_pin.encode()).hexdigest()
    if leader.pin != hashed_old_pin:
        return jsonify({'success': False, 'error': 'Current PIN is incorrect'}), 401
    
    # Update to new PIN
    leader.pin = hashlib.sha256(new_pin.encode()).hexdigest()
    db.session.commit()
    
    # Log the PIN change
    description = f"Changed PIN for shift leader: {leader.name}"
    log_activity(leader.name, 'modify', 'pin', description, leader.id, request.remote_addr)
    
    return jsonify({'success': True, 'message': 'PIN changed successfully'})

def initialize_shift_leaders():
    """Initialize shift leaders with default PINs (default: 1234)"""
    try:
        shift_leader_names = ['Ricardo', 'Arpad', 'Carlos', 'Brian', 'Kojo', 'Peter', 'Konrad']
        default_pin = '1234'
        hashed_default_pin = hashlib.sha256(default_pin.encode()).hexdigest()
        
        added_count = 0
        for name in shift_leader_names:
            # Check if leader already exists
            existing = ShiftLeader.query.filter(
                db.func.lower(ShiftLeader.name) == name.lower()
            ).first()
            
            if not existing:
                leader = ShiftLeader(
                    name=name,
                    pin=hashed_default_pin,
                    active=True
                )
                db.session.add(leader)
                added_count += 1
                print(Fore.GREEN + f"✓ Added shift leader: {name} (default PIN: {default_pin})")
        
        if added_count > 0:
            db.session.commit()
            print(Fore.YELLOW + Style.BRIGHT + f"\n{'='*50}")
            print(Fore.YELLOW + Style.BRIGHT + f"IMPORTANT: {added_count} shift leader(s) created with default PIN: {default_pin}")
            print(Fore.YELLOW + Style.BRIGHT + f"Please change PINs immediately for security!")
            print(Fore.YELLOW + Style.BRIGHT + f"{'='*50}\n")
        else:
            print(Fore.GREEN + "All shift leaders already exist in database.")
            
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

def upload_to_google_drive(file_path, file_name='diary_latest.db'):
    """Upload file to Google Drive, replacing any existing backup"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import pickle
        
        # OAuth2 credentials and token paths
        # Get the directory where the app is running (works for both .exe and .py)
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try app directory first for credentials (may be in installation folder)
        CREDENTIALS_FILE = os.path.join(app_dir, 'credentials.json')
        # If not found, try user data directory
        if not os.path.exists(CREDENTIALS_FILE):
            CREDENTIALS_FILE = os.path.join(USER_DATA_DIR, 'credentials.json')
        
        # Token always goes to user data directory (needs write access)
        TOKEN_FILE = os.path.join(USER_DATA_DIR, 'token.pickle')
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        
        # Check if credentials.json exists
        if not os.path.exists(CREDENTIALS_FILE):
            print(Fore.RED + "✗ Google Drive backup failed: credentials.json not found")
            print(Fore.YELLOW + f"  Looked in: {app_dir}")
            print(Fore.YELLOW + f"  And in: {USER_DATA_DIR}")
            print(Fore.YELLOW + "  Please follow instructions in GOOGLE_DRIVE_SETUP_OAUTH2.md to set up OAuth2 credentials")
            return False
        
        # Load or create credentials
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(Fore.YELLOW + f"⚠ Could not load token from {TOKEN_FILE}: {e}")
                creds = None
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print(Fore.GREEN + "✓ Refreshed Google Drive credentials")
                except Exception as e:
                    print(Fore.YELLOW + f"⚠ Token refresh failed, re-authorizing: {e}")
                    creds = None
            
            if not creds:
                print(Fore.CYAN + "Starting OAuth2 authorization flow...")
                print(Fore.CYAN + "A browser window will open for you to sign in.")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                print(Fore.GREEN + "✓ Google Drive authorization successful!")
            
            # Save the credentials for the next run
            try:
                # Ensure the user data directory exists and is writable
                os.makedirs(USER_DATA_DIR, exist_ok=True)
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
                print(Fore.GREEN + f"✓ Credentials saved to: {TOKEN_FILE}")
            except PermissionError as e:
                print(Fore.RED + f"✗ Permission denied: Cannot save token.pickle to {USER_DATA_DIR}")
                print(Fore.YELLOW + "  This should not happen with user data directory.")
                print(Fore.YELLOW + f"  Please check folder permissions for: {USER_DATA_DIR}")
                raise  # Re-raise to show the error in the API response
            except Exception as e:
                print(Fore.RED + f"✗ Error saving token file: {e}")
                raise  # Re-raise to show the error
        
        # Build Drive API service
        service = build('drive', 'v3', credentials=creds)
        
        # Search for "Diary_Backups" folder
        folder_name = 'Diary_Backups'
        folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        folder_results = service.files().list(q=folder_query, spaces='drive', fields='files(id, name)').execute()
        folders = folder_results.get('files', [])
        
        # Create folder if it doesn't exist
        if not folders:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(Fore.GREEN + f"✓ Created '{folder_name}' folder in Google Drive")
        else:
            folder_id = folders[0]['id']
        
        # Search for existing backup file with the same name
        file_query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        file_results = service.files().list(q=file_query, spaces='drive', fields='files(id, name)').execute()
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
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, name, size').execute()
        
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

def backup_database_to_gdrive():
    """Create backup of database and upload to Google Drive"""
    import shutil
    import tempfile
    
    try:
        # Source database file - use user data directory
        db_path = os.path.join(USER_DATA_DIR, 'instance', 'diary.db')
        
        if not os.path.exists(db_path):
            print(Fore.RED + "✗ Database file not found, skipping Google Drive backup")
            return False
        
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
        
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return success
        
    except Exception as e:
        print(Fore.RED + f"✗ Error backing up database to Google Drive: {e}")
        return False

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

def check_missed_backups():
    """Check if today's backup time has passed and run backups if missed"""
    try:
        now = datetime.now()
        # Scheduled backup time (both run at the same time)
        backup_time = now.replace(hour=0, minute=5, second=0, microsecond=0)
        
        # Check if backup time has passed today
        time_since_backup = now - backup_time
        
        # Run backups if:
        # 1. Backup time has passed (positive timedelta)
        # 2. We're within 3 hours of the scheduled time (to avoid running multiple times)
        # 3. It's still the same day (not checking yesterday's backups)
        
        if timedelta(minutes=0) < time_since_backup < timedelta(hours=3):
            print(Fore.YELLOW + Style.BRIGHT + "⚠️ Today's backup time has passed, running backups now...")
            print(Fore.CYAN + f"   Scheduled backup time: {backup_time.strftime('%H:%M')}")
            print(Fore.CYAN + f"   Current time: {now.strftime('%H:%M')}")
            
            # Run both backups simultaneously
            diary_success, maintenance_success = backup_all_databases_to_gdrive()
            
            if diary_success and maintenance_success:
                print(Fore.GREEN + "✓ Both backups completed successfully!")
            elif diary_success or maintenance_success:
                print(Fore.YELLOW + "⚠️ Some backups completed, but others failed. Check console for details.")
            else:
                print(Fore.RED + "✗ Backup attempts failed. Check console for details.")
        else:
            print(Fore.GREEN + "✓ Backup check completed - backups scheduled for later today or already completed")
        
    except Exception as e:
        print(Fore.RED + f"Error checking for missed backups: {e}")
        import traceback
        traceback.print_exc()

def update_scheduler():
    """Update the scheduler with new time settings"""
    try:
        # Remove existing job
        scheduler.remove_job('daily_report')
        
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
                id='daily_report',
                misfire_grace_time=3600  # Allow job to run up to 1 hour late
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
        
        # Check if email_log table needs status and error_message columns
        if 'email_log' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('email_log')]
            
            if 'status' not in columns:
                print(Fore.CYAN + "Adding status and error_message columns to email_log...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE email_log ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
                    conn.execute(text("ALTER TABLE email_log ADD COLUMN error_message TEXT DEFAULT ''"))
                    conn.commit()
                print(Fore.GREEN + "✓ Email log status columns added successfully!")
        
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
        
        # Create all tables if they don't exist (includes ActivityLog)
        db.create_all()
        print(Fore.GREEN + "✓ Tables created/verified successfully!")
        
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
        
        # Check for missed backups on startup
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        print(Fore.CYAN + Style.BRIGHT + "CHECKING FOR MISSED BACKUPS...")
        print(Fore.CYAN + Style.BRIGHT + "=" * 50)
        check_missed_backups()
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
                id='daily_report',
                misfire_grace_time=3600  # Allow job to run up to 1 hour late
            )
        
        # Schedule daily cleanup of old leave data (runs at 3 AM every day)
        scheduler.add_job(
            func=cleanup_old_leave_data_with_context,
            trigger="cron",
            hour=3,
            minute=0,
            id='cleanup_old_leave',
            misfire_grace_time=7200  # Allow job to run up to 2 hours late
        )
        
        # Schedule daily Google Drive backups for both databases (runs at 12:05 AM after daily report)
        scheduler.add_job(
            func=backup_all_databases_to_gdrive_with_context,
            trigger="cron",
            hour=0,
            minute=5,
            id='daily_gdrive_backup',
            misfire_grace_time=7200,  # Allow job to run up to 2 hours late
            coalesce=True,  # Combine multiple missed runs into one
            max_instances=1  # Only one instance can run at a time
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
    
    # Get port from environment variable, default to 5000 for production
    port = int(os.getenv('PORT', 5000))
    
    # Get computer hostname and IP for network access
    hostname = socket.gethostname()
    
    def get_local_ip():
        try:
            # Create a dummy socket to detect the preferred interface
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    local_ip = get_local_ip()
    
    # Auto-open browser after server starts
    def open_browser():
        """Wait for server to start, then open default browser"""
        import time
        time.sleep(1.5)  # Give Flask time to start
        webbrowser.open(f'http://127.0.0.1:{port}')
        print(Fore.GREEN + f"✓ Browser opened automatically on port {port}")
    
    # Start browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(Fore.CYAN + Style.BRIGHT + f"\n{'='*60}")
    print(Fore.CYAN + Style.BRIGHT + f"       BUILDING MANAGEMENT DIARY v2026.1.8")
    print(Fore.CYAN + f"{'-'*60}")
    print(Fore.CYAN + f"       Lead Developer: Arpad Kelemen")
    print(Fore.CYAN + f"       Email Support:  kelemen.arpad@gmail.com")
    print(Fore.CYAN + Style.BRIGHT + f"{'='*60}\n")
    
    print(Fore.CYAN + f"Local access:   http://127.0.0.1:{port}")
    print(Fore.GREEN + Style.BRIGHT + f"Network access: http://{local_ip}:{port}")
    print(Fore.GREEN + f"Hostname access: http://{hostname}:{port} (or http://{hostname}.local:{port})")
    print(Fore.YELLOW + f"Devices on the same Wi-Fi should use: http://{local_ip}:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
