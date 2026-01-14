from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import sys
import socket
import webbrowser
import threading
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

app = Flask(__name__)

# Connect to the main Diary database using absolute path
# Use the same location as main app (AppData for compiled, project dir for dev)

# First, check if running as compiled .exe - use AppData location (same as main app)
if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    # Running as compiled .exe - use AppData (same as main app)
    appdata = os.getenv('LOCALAPPDATA')
    if not appdata:
        appdata = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'Local')
    user_data_dir = os.path.join(appdata, 'DiaryApp')
    db_path = os.path.join(user_data_dir, 'instance', 'diary.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
else:
    # Running as Python script - check project directory locations
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # Check if we're in installed location (DiaryApp\DiaryEditor)
    # or development location (project\DiaryEditor)
    if os.path.exists(os.path.join(parent_dir, 'instance', 'diary.db')):
        # Installed location: DiaryApp\DiaryEditor -> DiaryApp\instance\diary.db
        db_path = os.path.join(parent_dir, 'instance', 'diary.db')
    else:
        # Development location: project\DiaryEditor -> project\Diary\instance\diary.db
        db_path = os.path.join(parent_dir, 'Diary', 'instance', 'diary.db')
    
    # Convert to absolute path for SQLAlchemy
    db_path = os.path.abspath(db_path)

# Debug output
if getattr(sys, 'frozen', False) and sys.platform == 'win32':
    print(f"Editor running from: {os.path.dirname(sys.executable)}")
    print(f"User data directory: {user_data_dir}")
else:
    print(f"Editor running from: {os.path.dirname(os.path.abspath(__file__))}")
print(f"Looking for database at: {db_path}")
if os.path.exists(db_path):
    print(f"✓ Database found!")
else:
    print(f"✗ WARNING: Database not found at expected location!")
    print(f"  Please ensure database exists at: {db_path}")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models (same as main app)
class DailyOccurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.String(10), nullable=False)
    flat_number = db.Column(db.String(20), nullable=False)
    reported_by = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sent = db.Column(db.Boolean, default=False)

# ShiftLeader model removed - PIN authentication not needed for editor

class StaffMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    shift = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True)

class StaffRota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    staff_name = db.Column(db.String(100), nullable=False)
    shift_start = db.Column(db.String(10))
    shift_end = db.Column(db.String(10))
    status = db.Column(db.String(20), default='working')
    notes = db.Column(db.Text)

class WaterTemperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    temperature = db.Column(db.Float, nullable=False)
    time_recorded = db.Column(db.String(5), nullable=False)  # Format: HH:MM

# Helper Functions
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
    
    # Save to main Diary app's reports folder (same location as main app)
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        # Use AppData location (same as main app)
        appdata = os.getenv('LOCALAPPDATA')
        if not appdata:
            appdata = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'Local')
        user_data_dir = os.path.join(appdata, 'DiaryApp')
        reports_dir = os.path.join(user_data_dir, 'reports', 'PDF')
    else:
        # Use project directory for development
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        reports_dir = os.path.join(parent_dir, 'Diary', 'reports', 'PDF')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Filename uses report date, with time suffix to avoid overwriting
    filename = f"daily_report_{report_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.pdf"
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

# Routes
@app.route('/')
def index():
    return render_template('editor.html')

@app.route('/api/occurrences', methods=['GET'])
def get_occurrences():
    """Get occurrences for a specific date"""
    date_str = request.args.get('date')
    
    if not date_str:
        return jsonify({'success': False, 'error': 'Date parameter required'}), 400
    
    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        next_day = report_date + timedelta(days=1)
        
        occurrences = DailyOccurrence.query.filter(
            DailyOccurrence.timestamp >= report_date,
            DailyOccurrence.timestamp < next_day
        ).order_by(DailyOccurrence.time).all()
        
        return jsonify({
            'success': True,
            'date': date_str,
            'count': len(occurrences),
            'occurrences': [{
                'id': o.id,
                'time': o.time,
                'flat_number': o.flat_number,
                'reported_by': o.reported_by,
                'description': o.description,
                'timestamp': o.timestamp.isoformat(),
                'sent': o.sent
            } for o in occurrences]
        })
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

@app.route('/api/occurrences/<int:occurrence_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_occurrence(occurrence_id):
    """Get, update, or delete a specific occurrence"""
    occurrence = DailyOccurrence.query.get(occurrence_id)
    
    if not occurrence:
        return jsonify({'success': False, 'error': 'Occurrence not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'occurrence': {
                'id': occurrence.id,
                'time': occurrence.time,
                'flat_number': occurrence.flat_number,
                'reported_by': occurrence.reported_by,
                'description': occurrence.description,
                'timestamp': occurrence.timestamp.isoformat(),
                'sent': occurrence.sent
            }
        })
    
    elif request.method == 'PUT':
        data = request.json
        occurrence.time = data.get('time', occurrence.time)
        occurrence.flat_number = data.get('flat_number', occurrence.flat_number)
        occurrence.reported_by = data.get('reported_by', occurrence.reported_by)
        occurrence.description = data.get('description', occurrence.description)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Occurrence updated successfully',
            'occurrence': {
                'id': occurrence.id,
                'time': occurrence.time,
                'flat_number': occurrence.flat_number,
                'reported_by': occurrence.reported_by,
                'description': occurrence.description
            }
        })
    
    elif request.method == 'DELETE':
        db.session.delete(occurrence)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Occurrence deleted successfully'})

@app.route('/api/occurrences/add', methods=['POST'])
def add_occurrence():
    """Add a new occurrence to a specific date"""
    data = request.json
    
    try:
        # Parse the date and time
        date_str = data.get('date')
        time_str = data.get('time')
        
        # Create timestamp from date
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        timestamp = datetime.combine(report_date, datetime.min.time())
        
        occurrence = DailyOccurrence(
            time=time_str,
            flat_number=data.get('flat_number', ''),
            reported_by=data.get('reported_by', ''),
            description=data.get('description', ''),
            timestamp=timestamp,
            sent=False
        )
        
        db.session.add(occurrence)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Occurrence added successfully',
            'occurrence': {
                'id': occurrence.id,
                'time': occurrence.time,
                'flat_number': occurrence.flat_number,
                'reported_by': occurrence.reported_by,
                'description': occurrence.description
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/dates-with-occurrences', methods=['GET'])
def get_dates_with_occurrences():
    """Get all dates that have occurrences"""
    # Get distinct dates from occurrences
    occurrences = DailyOccurrence.query.all()
    dates = set()
    
    for occ in occurrences:
        dates.add(occ.timestamp.date().isoformat())
    
    return jsonify({
        'success': True,
        'dates': sorted(list(dates), reverse=True)  # Most recent first
    })

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF report for a specific date"""
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
        
        # Generate the PDF
        pdf_path = generate_daily_pdf(occurrences, report_date)
        
        # Get the relative path for display
        pdf_filename = os.path.basename(pdf_path)
        
        return jsonify({
            'success': True,
            'message': f'PDF report generated successfully',
            'pdf_path': pdf_path,
            'pdf_filename': pdf_filename,
            'occurrences_count': len(occurrences)
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-occurrences', methods=['POST'])
def search_occurrences():
    """Search all occurrences by keyword"""
    try:
        data = request.json
        keyword = data.get('keyword', '').strip()
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if not keyword:
            return jsonify({'success': False, 'error': 'Keyword is required'}), 400
        
        # Build base query with case-insensitive search
        query = DailyOccurrence.query.filter(
            db.or_(
                DailyOccurrence.description.ilike(f'%{keyword}%'),
                DailyOccurrence.flat_number.ilike(f'%{keyword}%'),
                DailyOccurrence.reported_by.ilike(f'%{keyword}%')
            )
        )
        
        # Add date range filter if provided
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(DailyOccurrence.timestamp >= from_date)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                # Include the entire end date
                to_date_end = datetime.combine(to_date, datetime.max.time())
                query = query.filter(DailyOccurrence.timestamp <= to_date_end)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date_to format'}), 400
        
        # Execute query
        occurrences = query.order_by(DailyOccurrence.timestamp.desc()).all()
        
        # Format results
        results = []
        for occ in occurrences:
            results.append({
                'id': occ.id,
                'date': occ.timestamp.date().isoformat(),
                'time': occ.time,
                'flat_number': occ.flat_number,
                'reported_by': occ.reported_by,
                'description': occ.description
            })
        
        print(f"✓ Search completed: '{keyword}' - Found {len(results)} results")
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        print(f"Error searching occurrences: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        # Check if database exists
        db_exists = os.path.exists(db_path)
        
        # Get computer hostname for network access
        hostname = socket.gethostname()
        
        print("\n" + "="*60)
        print("DIARY REPORT EDITOR")
        print("="*60)
        print(f"Database: {db_path}")
        print(f"Database exists: {'✓ Yes' if db_exists else '✗ No - Please check path!'}")
        print(f"Local access:   http://127.0.0.1:5001")
        print(f"Network access: http://{hostname}:5001")
        print("="*60)
        
        if not db_exists:
            print("\n⚠️  WARNING: Database file not found!")
            print(f"Looking for: {db_path}")
            print("\nPlease ensure:")
            print("1. The main Diary app has been run at least once")
            print("2. The database file exists at the correct location")
            print("="*60 + "\n")
        else:
            print("✓ Database connected successfully")
            print(f"Other PCs on the network can connect using: http://{hostname}:5001")
            print("="*60 + "\n")
    
    # Auto-open browser after server starts
    def open_browser():
        """Wait for server to start, then open default browser"""
        import time
        time.sleep(1.5)  # Give Flask time to start
        webbrowser.open('http://127.0.0.1:5001')
        print("✓ Browser opened automatically")
    
    # Start browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=False, host='0.0.0.0', port=5001)

