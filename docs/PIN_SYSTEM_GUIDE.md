# PIN Authentication System - User Guide

## Overview
A PIN-based authentication system has been implemented to restrict access to staff management features (adding, editing, and removing staff members) to authorized shift leaders only.

## Authorized Shift Leaders
The following shift leaders have been granted access to staff management features:
- **Ricardo**
- **Arpad**
- **Carlos**
- **Brian**
- **Kojo**
- **Peter**
- **Konrad**

## Default PIN
All shift leaders are initially assigned the default PIN: **1234**

**⚠️ IMPORTANT: For security reasons, all shift leaders MUST change their default PIN immediately after first login.**

## How to Use the System

### 1. Adding/Editing/Removing Staff
When you attempt to add, edit, or remove a staff member:
1. A PIN authentication dialog will appear
2. Enter your PIN (no need to select your name - the system will identify you)
3. Click "Submit" or press Enter
4. If authenticated successfully, the requested action will proceed

### 2. Changing Your PIN
To change your PIN (highly recommended):
1. Navigate to the **Settings** tab
2. Scroll down to the **"🔐 Change Shift Leader PIN"** section
3. Fill in the form:
   - Select your name
   - Enter your current PIN
   - Enter your new PIN (minimum 4 digits)
   - Confirm your new PIN
4. Click **"Change PIN"**
5. You will receive a confirmation message

### 3. PIN Requirements
- Minimum length: 4 digits
- Maximum length: 10 digits
- Can contain numbers only (recommended) or alphanumeric characters
- Case-sensitive

## Security Features
- PINs are encrypted (hashed) using SHA-256 before storage
- PINs are never displayed in plain text
- Failed authentication attempts show generic error messages
- PIN verification is performed server-side

## Troubleshooting

### "Invalid PIN" Error
- Double-check you're entering the correct PIN
- Ensure you haven't accidentally enabled Caps Lock
- If you've forgotten your PIN, contact the system administrator

### "Invalid PIN" Error (No Name Dropdown)
- The system now identifies you automatically by your PIN
- Each shift leader must have a unique PIN
- If two leaders share the same PIN, only one will be recognized

### Form Not Appearing After PIN Entry
- Refresh the page and try again
- Clear your browser cache
- Check browser console for errors (F12)

## Administrator Notes

### Adding New Shift Leaders
To add a new shift leader, you'll need to modify the `initialize_shift_leaders()` function in `app.py`:

1. Open `app.py`
2. Find the line: `shift_leader_names = ['Ricardo', 'Arpad', 'Carlos', 'Brian', 'Kojo', 'Peter', 'Konrad']`
3. Add the new name to this list
4. Restart the application
5. The new shift leader will be created with the default PIN (1234)

### Resetting a Forgotten PIN
If a shift leader forgets their PIN, an administrator can reset it by:

1. Stop the application
2. Access the database file: `instance/diary.db`
3. Use a SQLite database tool to update the PIN
4. The default PIN hash is: `03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4` (for PIN: 1234)
5. Restart the application

### Database Table: shift_leader
The shift leader information is stored in the `shift_leader` table with the following fields:
- `id`: Primary key
- `name`: Shift leader's name (unique)
- `pin`: Hashed PIN (SHA-256)
- `active`: Status (True/False)
- `created_date`: Account creation timestamp
- `last_login`: Last successful authentication timestamp

## Support
For technical issues or questions about the PIN system, contact your system administrator or IT support team.

---
**Last Updated:** October 19, 2025

