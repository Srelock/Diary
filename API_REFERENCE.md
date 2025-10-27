# API Reference Guide

This document contains all available API endpoints for the Diary application.

---

## Table of Contents
1. [Daily Occurrences](#daily-occurrences)
2. [Staff Rota](#staff-rota)
3. [Porter Rota](#porter-rota)
4. [CCTV Faults](#cctv-faults)
5. [Water Temperature](#water-temperature)
6. [Reports & Email](#reports--email)
7. [Settings & Configuration](#settings--configuration)
8. [Staff Management](#staff-management)
9. [Shift Leaders & PIN Management](#shift-leaders--pin-management)
10. [Logs & Activity](#logs--activity)

---

## Daily Occurrences

### Get Daily Occurrences
**Endpoint:** `GET /api/daily-occurrences`

**Description:** Returns all occurrences for today.

**Response:**
```json
[
  {
    "id": 1,
    "time": "14:30",
    "flat_number": "12A",
    "reported_by": "John Doe",
    "description": "Water leak reported",
    "timestamp": "2025-10-25T14:30:00"
  }
]
```

### Add Daily Occurrence
**Endpoint:** `POST /api/daily-occurrences`

**Request Body:**
```json
{
  "time": "14:30",
  "flat_number": "12A",
  "reported_by": "John Doe",
  "description": "Water leak reported"
}
```

**Response:**
```json
{
  "success": true,
  "id": 1
}
```

### Delete Daily Occurrence
**Endpoint:** `DELETE /api/daily-occurrences/<occurrence_id>`

**Request Body:**
```json
{
  "user_name": "John Doe"
}
```

**Response:**
```json
{
  "success": true
}
```

---

## Staff Rota

### Get Staff Rota
**Endpoint:** `GET /api/staff-rota`

**Query Parameters:**
- `start_date` (optional): Start date in `YYYY-MM-DD` format (default: today)
- `end_date` (optional): End date in `YYYY-MM-DD` format (default: 30 days from today)

**Response:**
```json
[
  {
    "id": 1,
    "date": "2025-10-25",
    "staff_name": "John Doe",
    "shift_start": "09:00",
    "shift_end": "17:00",
    "status": "working",
    "notes": "Regular shift"
  }
]
```

### Add Staff Rota Entry
**Endpoint:** `POST /api/staff-rota`

**Request Body:**
```json
{
  "date": "2025-10-25",
  "staff_name": "John Doe",
  "shift_start": "09:00",
  "shift_end": "17:00",
  "status": "working",
  "notes": "Regular shift"
}
```

**Status Options:** `working`, `holiday`, `sick`, `training`, `absent`

**Response:**
```json
{
  "success": true,
  "id": 1
}
```

### Delete Staff Rota Entry
**Endpoint:** `DELETE /api/staff-rota/<rota_id>`

**Request Body:**
```json
{
  "user_name": "John Doe"
}
```

**Response:**
```json
{
  "success": true
}
```

### Add Staff Rota Range
**Endpoint:** `POST /api/staff-rota-range`

**Description:** Add leave for a date range (creates one entry per day).

**Request Body:**
```json
{
  "staff_name": "John Doe",
  "date_from": "2025-10-25",
  "date_to": "2025-10-30",
  "status": "holiday",
  "notes": "Annual leave"
}
```

**Response:**
```json
{
  "success": true,
  "days_added": 6,
  "message": "Added 6 day(s) of holiday"
}
```

---

## Porter Rota

### Get Porter Rota
**Endpoint:** `GET /api/porter-rota`

**Description:** Returns porter rota schedule based on 4-week rotation pattern.

**Query Parameters:**
- `start_date` (optional): Start date in `YYYY-MM-DD` format (default: today)
- `end_date` (optional): End date in `YYYY-MM-DD` format (default: 1 year from today)

**Response:**
```json
[
  {
    "date": "2025-10-25",
    "day_name": "Friday",
    "week_in_cycle": 2,
    "color_off": "red",
    "staff_off": [
      {
        "name": "John Doe",
        "shift": 1,
        "color": "red"
      }
    ],
    "shift1_time": "Early (7am-2pm)",
    "shift2_time": "Late (2pm-10pm)",
    "shift3_time": "Night (10pm-7am)",
    "is_today": true
  }
]
```

---

## CCTV Faults

### Get CCTV Faults
**Endpoint:** `GET /api/cctv-faults`

**Description:** Returns all CCTV faults ordered by timestamp (newest first).

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-10-25T14:30:00",
    "fault_type": "Camera Offline",
    "flat_number": "12A",
    "block_number": "B",
    "floor_number": "3",
    "location": "Flat 12A | Block B | Floor 3",
    "description": "Camera not responding",
    "contact_details": "John Doe - 555-1234",
    "additional_notes": "Requires technician visit",
    "status": "open",
    "resolved_date": null
  }
]
```

### Add CCTV Fault
**Endpoint:** `POST /api/cctv-faults`

**Request Body:**
```json
{
  "fault_type": "Camera Offline",
  "flat_number": "12A",
  "block_number": "B",
  "floor_number": "3",
  "description": "Camera not responding",
  "contact_details": "John Doe - 555-1234",
  "additional_notes": "Requires technician visit",
  "status": "open"
}
```

**Fault Types:** `Camera Offline`, `Poor Image Quality`, `Camera Damaged`, `Recording Issue`, `Other`

**Response:**
```json
{
  "success": true,
  "id": 1
}
```

### Update Fault Status
**Endpoint:** `POST /api/update-fault-status`

**Request Body:**
```json
{
  "id": 1,
  "status": "closed"
}
```

**Status Options:** `open`, `in_progress`, `closed`

**Response:**
```json
{
  "success": true
}
```

### Delete Fault
**Endpoint:** `DELETE /api/delete-fault/<fault_id>`

**Description:** Delete a CCTV fault (only closed faults can be deleted).

**Response:**
```json
{
  "success": true
}
```

---

## Water Temperature

### Get Water Temperature Records
**Endpoint:** `GET /api/water-temperature`

**Query Parameters:**
- `date_from` (optional): Start date in `YYYY-MM-DD` format
- `date_to` (optional): End date in `YYYY-MM-DD` format
- **Default:** Returns last 24 hours if no parameters provided

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-10-25T14:30:00",
    "temperature": 55.5,
    "time_recorded": "14:30"
  }
]
```

### Add Water Temperature Record
**Endpoint:** `POST /api/water-temperature`

**Request Body:**
```json
{
  "temperature": 55.5,
  "time": "14:30"
}
```

**Response:**
```json
{
  "success": true,
  "id": 1
}
```

### Delete Water Temperature Record
**Endpoint:** `DELETE /api/water-temperature/<temp_id>`

**Response:**
```json
{
  "success": true
}
```

---

## Reports & Email

### Test Export (Generate PDF/CSV)
**Endpoint:** `POST /api/test-export`

**Description:** Export PDF and CSV reports without sending email.

**Response:**
```json
{
  "success": true,
  "message": "Reports exported successfully:\nPDF: reports/PDF/daily_report_20251025.pdf\nCSV: reports/CSV/daily_report_20251025.csv",
  "count": 5
}
```

### Reprint Report
**Endpoint:** `POST /api/reprint-report`

**Description:** Regenerate a report for a specific date.

**Request Body:**
```json
{
  "date": "2025-10-25"
}
```

**Response:**
```json
{
  "success": true,
  "message": "PDF report generated successfully",
  "pdf_path": "reports/PDF/daily_report_20251025.pdf",
  "pdf_filename": "daily_report_20251025.pdf",
  "occurrences_count": 5,
  "water_temps_count": 3
}
```

### Send Test Email
**Endpoint:** `POST /api/test-email`

**Description:** Send a test email with today's data.

**Response:**
```json
{
  "success": true,
  "message": "Test email sent successfully to example@example.com!",
  "count": 5
}
```

### Test Clear
**Endpoint:** `POST /api/test-clear`

**Description:** Clear all today's diary entries (for testing purposes).

**Response:**
```json
{
  "success": true,
  "count": 5,
  "message": "Cleared 5 diary entries"
}
```

### Backup to Google Drive
**Endpoint:** `POST /api/backup-to-gdrive`

**Description:** Manually trigger a Google Drive backup of the database. Uploads `diary_latest.db` to the `Diary_Backups` folder in Google Drive, replacing any existing backup.

**Requirements:**
- `service_account.json` file must be present in project root
- Google Drive API must be enabled
- See `GOOGLE_DRIVE_SETUP.md` for setup instructions

**Response (Success):**
```json
{
  "success": true,
  "message": "Database successfully backed up to Google Drive!\n\nFile: diary_latest.db\nFolder: Diary_Backups\n\nOnly the latest backup is kept in Google Drive."
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Backup failed. Check console for details.\n\nCommon issues:\n- service_account.json file missing\n- Invalid credentials\n- No internet connection\n- Google Drive API not enabled"
}
```

**Note:** The system automatically backs up to Google Drive daily at 2:00 AM. This endpoint allows manual backup on demand.

### Get Email Logs
**Endpoint:** `GET /api/email-logs`

**Description:** Get email history for the last 30 days.

**Response:**
```json
[
  {
    "id": 1,
    "sent_date": "2025-10-25T18:00:00",
    "recipient": "example@example.com",
    "subject": "Daily Report - 2025-10-25",
    "pdf_path": "reports/PDF/daily_report_20251025.pdf"
  }
]
```

---

## Settings & Configuration

### Get Schedule Settings
**Endpoint:** `GET /api/schedule-settings`

**Response:**
```json
{
  "email_time": "18:00",
  "email_enabled": true,
  "recipient_email": "example@example.com",
  "sender_email": "sender@example.com",
  "sender_password": "app_password_here",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "last_updated": "2025-10-25T14:30:00"
}
```

### Update Schedule Settings
**Endpoint:** `POST /api/schedule-settings`

**Request Body:**
```json
{
  "email_time": "18:00",
  "email_enabled": true,
  "recipient_email": "example@example.com",
  "sender_email": "sender@example.com",
  "sender_password": "app_password_here",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587
}
```

**Response:**
```json
{
  "email_time": "18:00",
  "email_enabled": true,
  "recipient_email": "example@example.com",
  "sender_email": "sender@example.com",
  "sender_password": "app_password_here",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "last_updated": "2025-10-25T14:30:00"
}
```

### Verify Settings PIN
**Endpoint:** `POST /api/verify-settings-pin`

**Description:** Verify PIN for settings access (checks all shift leaders).

**Request Body:**
```json
{
  "pin": "1234"
}
```

**Response:**
```json
{
  "success": true,
  "name": "John Doe"
}
```

---

## Staff Management

### Get Staff Members
**Endpoint:** `GET /api/staff-members`

**Description:** Returns all active staff members.

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "color": "red",
    "shift": 1,
    "active": true
  }
]
```

### Add Staff Member
**Endpoint:** `POST /api/staff-members`

**Request Body:**
```json
{
  "name": "John Doe",
  "color": "red",
  "shift": 1,
  "active": true,
  "user_name": "Admin"
}
```

**Color Options:** `red`, `yellow`, `green`, `blue`, `purple`, `darkred`, `darkgreen`, `brownishyellow`

**Shift Options:** `1`, `2`, `3`

**Response:**
```json
{
  "success": true,
  "id": 1
}
```

### Update Staff Member
**Endpoint:** `PUT /api/staff-members/<staff_id>`

**Request Body:**
```json
{
  "name": "John Doe",
  "color": "blue",
  "shift": 2,
  "active": true,
  "user_name": "Admin"
}
```

**Response:**
```json
{
  "success": true
}
```

### Delete Staff Member (Soft Delete)
**Endpoint:** `DELETE /api/staff-members/<staff_id>`

**Request Body:**
```json
{
  "user_name": "Admin"
}
```

**Response:**
```json
{
  "success": true
}
```

---

## Shift Leaders & PIN Management

### Get Shift Leaders
**Endpoint:** `GET /api/shift-leaders`

**Description:** Get list of active shift leaders (names only, no PINs).

**Response:**
```json
[
  {
    "id": 1,
    "name": "Ricardo"
  },
  {
    "id": 2,
    "name": "Arpad"
  }
]
```

**Default Shift Leaders:** Ricardo, Arpad, Carlos, Brian, Kojo, Peter, Konrad

### Verify PIN
**Endpoint:** `POST /api/verify-pin`

**Description:** Verify shift leader PIN (PIN only, no name required).

**Request Body:**
```json
{
  "pin": "1234"
}
```

**Response:**
```json
{
  "success": true,
  "leader": {
    "id": 1,
    "name": "Ricardo"
  }
}
```

### Change PIN
**Endpoint:** `POST /api/change-pin`

**Description:** Change shift leader PIN.

**Request Body:**
```json
{
  "name": "Ricardo",
  "old_pin": "1234",
  "new_pin": "5678"
}
```

**Requirements:**
- All fields are required
- PIN must be at least 4 digits
- Old PIN must be correct

**Response:**
```json
{
  "success": true,
  "message": "PIN changed successfully"
}
```

---

## Logs & Activity

### Get Settings Access Logs
**Endpoint:** `GET /api/settings-access-logs`

**Description:** Get recent settings access logs (last 50 entries).

**Response:**
```json
{
  "logs": [
    "[2025-10-25 14:30:00] SUCCESS - Ricardo - Settings Access Granted from 192.168.1.1",
    "[2025-10-25 14:25:00] FAILED - Unknown User - Settings Access Attempt - Invalid PIN from 192.168.1.2"
  ],
  "total_count": 150
}
```

### Get Activity Logs
**Endpoint:** `GET /api/activity-logs`

**Description:** Get recent activity logs with filtering options.

**Query Parameters:**
- `days` (optional): Number of days to look back (default: 7)
- `user` (optional): Filter by user name
- `action` (optional): Filter by action type (`add`, `modify`, `delete`)
- `limit` (optional): Maximum number of results (default: 100)

**Response:**
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "timestamp": "2025-10-25T14:30:00",
      "user_name": "John Doe",
      "action_type": "delete",
      "entity_type": "occurrence",
      "entity_id": "123",
      "description": "Deleted occurrence: 14:30 - Flat 12A - Water leak reported...",
      "ip_address": "192.168.1.1"
    }
  ],
  "total": 50
}
```

---

## General Notes

### Authentication
- Most endpoints require PIN verification for settings-related operations
- Use the `/api/verify-settings-pin` or `/api/verify-pin` endpoints to authenticate

### Date Format
- All dates use ISO 8601 format: `YYYY-MM-DD`
- All timestamps use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`

### Error Responses
All endpoints return error responses in the following format:
```json
{
  "success": false,
  "error": "Error message here"
}
```

### Common HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid PIN)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

---

## Application Configuration

### Default Settings
- **Default PIN:** `1234` (for all shift leaders)
- **SMTP Server:** `smtp.gmail.com:587`
- **Database:** SQLite (`instance/diary.db`)

### Scheduled Tasks
- **2:00 AM** - Automatic Google Drive backup (daily)
- **3:00 AM** - Cleanup old leave data (older than 2 years)
- **User-configured time** - Send daily report email

### File Locations
- **PDF Reports:** `reports/PDF/`
- **CSV Reports:** `reports/CSV/`
- **Logs:** `logs/`
- **Database:** `instance/diary.db`
- **Google Drive Backup:** `Diary_Backups/diary_latest.db` (in Google Drive)
- **Credentials:** `service_account.json` (not committed to git)

---

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/api/daily-occurrences` | GET, POST | Manage daily occurrences |
| `/api/daily-occurrences/<id>` | DELETE | Delete occurrence |
| `/api/staff-rota` | GET, POST | Manage staff rota |
| `/api/staff-rota/<id>` | DELETE | Delete rota entry |
| `/api/staff-rota-range` | POST | Add rota date range |
| `/api/porter-rota` | GET | Get porter rotation schedule |
| `/api/cctv-faults` | GET, POST | Manage CCTV faults |
| `/api/update-fault-status` | POST | Update fault status |
| `/api/delete-fault/<id>` | DELETE | Delete closed fault |
| `/api/water-temperature` | GET, POST | Manage water temps |
| `/api/water-temperature/<id>` | DELETE | Delete temp record |
| `/api/test-export` | POST | Generate PDF/CSV |
| `/api/reprint-report` | POST | Regenerate report |
| `/api/test-email` | POST | Send test email |
| `/api/test-clear` | POST | Clear today's entries |
| `/api/backup-to-gdrive` | POST | Backup database to Google Drive |
| `/api/schedule-settings` | GET, POST | Email schedule settings |
| `/api/email-logs` | GET | Email history |
| `/api/staff-members` | GET, POST | Manage staff members |
| `/api/staff-members/<id>` | PUT, DELETE | Update/delete staff |
| `/api/shift-leaders` | GET | Get shift leaders |
| `/api/verify-pin` | POST | Verify leader PIN |
| `/api/verify-settings-pin` | POST | Verify settings PIN |
| `/api/change-pin` | POST | Change leader PIN |
| `/api/settings-access-logs` | GET | Settings access history |
| `/api/activity-logs` | GET | Activity history |

---

**Last Updated:** October 27, 2025  
**Version:** 1.1 - Added Google Drive backup functionality

