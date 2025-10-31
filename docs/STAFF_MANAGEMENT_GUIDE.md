# Staff Management Guide

## Overview
The staff roster system has been updated to be fully editable. You can now easily add, edit, or remove staff members when people leave or new hires join.

## Features

### 1. **Editable Staff Roster**
- Staff members are now stored in a database instead of being hardcoded
- Changes are immediately reflected across all parts of the application:
  - Daily Schedule
  - Porter Rota Calendar
  - PDF Reports

### 2. **How to Manage Staff**

#### **View Staff**
1. Open the application in your browser: http://localhost:5000
2. Navigate to the **Staff Rota** tab
3. You'll see two boxes showing Shift 1 and Shift 2 staff members

#### **Add New Staff**
1. Click the **"+ Add Staff"** button in the appropriate shift box
2. Enter the staff member's name
3. Select their color assignment (Red, Yellow, Green, or Blue)
4. Click **"Save"**
5. The new staff member will immediately appear in all schedules

#### **Edit Staff Member**
1. Hover over any staff member's name in the legend boxes
2. Click the **"Edit"** button that appears
3. Modify the name or change the color assignment
4. Click **"Save"** to confirm changes
5. Click **"Cancel"** to discard changes

#### **Remove Staff Member**
1. Hover over the staff member's name
2. Click the **"Remove"** button
3. Confirm the removal
4. The staff member will be marked as inactive (not deleted from database)

### 3. **Color Assignments**
Each staff member is assigned a color that determines their rotation schedule:
- **Red**: Carlos (Shift 1) & Sunny (Shift 2)
- **Yellow**: Arpad K (Shift 1) & K. Essandoh (Shift 2)
- **Green**: R. Rodrigues (Shift 1) & Brian B (Shift 2)
- **Blue**: Charles (Shift 1) & Michael (Shift 2)

### 4. **Database Structure**
Staff information is stored in the `staff_member` table with:
- `id`: Unique identifier
- `name`: Staff member's name
- `color`: Color assignment (red, yellow, green, blue)
- `shift`: Shift number (1 or 2)
- `active`: Status (true = active, false = removed)

### 5. **Automatic Initialization**
- When you first run the application, it automatically creates the default staff roster
- The system preserves your data across restarts

### 6. **Integration with Reports**
- Daily PDF reports automatically include the current staff roster
- The porter rota calendar updates in real-time based on staff changes

## Technical Details

### API Endpoints
- `GET /api/staff-members` - Retrieve all active staff members
- `POST /api/staff-members` - Add a new staff member
- `PUT /api/staff-members/<id>` - Update an existing staff member
- `DELETE /api/staff-members/<id>` - Remove a staff member (soft delete)

### Files Modified
1. **app.py**
   - Added `StaffMember` database model
   - Created staff management API endpoints
   - Added `get_porter_groups()` helper function
   - Updated PDF generation to use dynamic staff data

2. **templates/index.html**
   - Made staff legend boxes editable
   - Added JavaScript functions for CRUD operations
   - Updated schedule loading to use API data

## Tips
- **Backup**: The database file `instance/diary.db` contains all your data. Back it up regularly.
- **Testing**: Use the edit feature to test staff changes before committing them.
- **Reports**: After making staff changes, generate a test PDF to ensure everything looks correct.

## Support
If you encounter any issues:
1. Check that the Flask server is running
2. Open browser console (F12) to check for JavaScript errors
3. Check the terminal for Python error messages
4. Verify the database file exists at `instance/diary.db`

---
**Version**: 2.0  
**Last Updated**: October 18, 2025

