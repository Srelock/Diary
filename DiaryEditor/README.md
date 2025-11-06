# 📝 Diary Report Editor

A standalone admin tool for viewing and editing historical diary occurrence reports.

## 🎯 Purpose

This editor allows shift leaders to:
- ✅ View occurrences from any past date
- ✏️ Edit existing occurrence details
- ➕ Add missed occurrences to past dates
- 🗑️ Delete incorrect occurrences
- 🔍 Browse historical reports by date

## 🚀 How to Use

### 1. Start the Editor

Double-click **`start_editor.bat`** to launch the editor.

The editor will:
- Start on port 5001
- **Automatically open in your default browser**
- Display at: http://127.0.0.1:5001
- Connect to the main Diary database
- Load immediately (no PIN required)

### 2. Select a Date

- Use the date picker to select any date
- Click "Load Report" to view occurrences for that date

### 3. Edit Occurrences

- Click the **"Edit"** button next to any occurrence
- Modify the fields (time, flat, reporter, description)
- Click **"Save Changes"**

### 4. Add New Occurrences

- Click **"+ Add Occurrence"** button
- Fill in the occurrence details
- Click **"Add Occurrence"**

### 5. Delete Occurrences

- Click the **"Delete"** button next to any occurrence
- Confirm the deletion
- The occurrence will be permanently removed

## 📁 File Structure

```
DiaryEditor/
├── editor_app.py          # Main Flask application
├── templates/
│   └── editor.html        # Editor web interface
├── start_editor.bat       # Windows launcher
└── README.md             # This file
```

## 🔗 Database Connection

The editor connects to the main Diary database at:
- `../Diary/instance/diary.db`

All changes are immediately reflected in both the main diary app and the editor.

## ⚠️ Important Notes

### Security
- **No authentication** - Anyone with access to the editor can make changes
- Keep this tool private - only for authorized staff use
- Consider running only when needed, not continuously

### Data Integrity
- Changes are **permanent** and immediately saved to the database
- **No undo function** - be careful when editing or deleting
- Deleted occurrences cannot be recovered

### Best Practices
1. **Use for corrections** - Fix typos, add missed incidents
2. **Don't abuse** - Only edit when necessary
3. **Verify before saving** - Double-check your edits
4. **Document changes** - If needed, note what was changed and why

### Running Alongside Main App
- ✅ **Can run simultaneously** with the main diary app (port 5000)
- ✅ **Shares the same database** - changes sync automatically
- ✅ **Independent** - Can run without main app running

## 🛠️ Technical Details

### Requirements
- Python 3.x
- Flask
- Flask-SQLAlchemy
- reportlab (for PDF generation)
- Same dependencies as main Diary app

### Installation
```cmd
pip install Flask Flask-SQLAlchemy reportlab
```

### Ports
- Main Diary App: http://127.0.0.1:5000
- Report Editor: http://127.0.0.1:5001

### Database Models
Uses the same models as main app:
- `DailyOccurrence` - Incident records
- `ShiftLeader` - PIN authentication
- `StaffMember` - Staff data (read-only)
- `StaffRota` - Leave records (read-only)

## 📞 Support

If you encounter any issues:
1. Check that the main Diary database exists at `../Diary/instance/diary.db`
2. Ensure you're using a valid shift leader PIN
3. Check the console window for error messages

## 🔄 Updates

To update the editor:
1. Close the editor (Ctrl+C in console)
2. Replace the updated files
3. Restart using `start_editor.bat`

---

**Version:** 1.0  
**Created:** October 2025  
**Compatible with:** Building Management Diary v1.0+

