# Google Drive Backup Setup Guide

⚠️ **NOTE: This application now uses OAuth2 instead of Service Account.**

Please use the **[OAuth2 Setup Guide](GOOGLE_DRIVE_SETUP_OAUTH2.md)** instead.

The OAuth2 method:
- ✅ Works with free Google accounts
- ✅ Uses your personal Google Drive storage
- ✅ One-time authorization, then automatic forever
- ✅ Easier to set up

---

## Quick Redirect

👉 **[Click here for OAuth2 Setup Instructions](GOOGLE_DRIVE_SETUP_OAUTH2.md)**

---

## Old Service Account Method (Deprecated)

The service account method is no longer supported. This file is kept for reference only.

1. Go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS** at the top
3. Select **Service Account**
4. Fill in the details:
   - **Service account name**: `diary-backup` (or any name you prefer)
   - **Service account ID**: Will auto-fill
   - **Description**: "Automated diary database backup"
5. Click **CREATE AND CONTINUE**
6. Skip the optional steps by clicking **DONE**

### Step 4: Create Service Account Key (Credentials)

1. On the **Credentials** page, find your new service account in the list
2. Click on the service account email address
3. Go to the **KEYS** tab
4. Click **ADD KEY** > **Create new key**
5. Select **JSON** format
6. Click **CREATE**
7. A JSON file will download automatically - this is your credentials file

### Step 5: Install Credentials File

1. Rename the downloaded JSON file to exactly: `service_account.json`
2. Move it to your Diary application folder (same folder as `app.py`)
3. **IMPORTANT**: Never share this file or commit it to git (it's already in .gitignore)

### Step 6: Get Service Account Email

1. Open the `service_account.json` file with a text editor
2. Find the line with `"client_email"` - it looks like:
   ```json
   "client_email": "diary-backup@your-project.iam.gserviceaccount.com"
   ```
3. Copy this email address

### Step 7: Share Google Drive Folder with Service Account

**Option A: Let the app create the folder (Recommended)**

1. Start your Diary application
2. The app will automatically create a `Diary_Backups` folder in the service account's Google Drive
3. You won't see this folder in YOUR Google Drive (it's in the service account's Drive)

**Option B: Use your own Google Drive folder**

If you want to see the backups in YOUR Google Drive:

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder called `Diary_Backups`
3. Right-click the folder > **Share**
4. Paste the service account email address from Step 6
5. Set permission to **Editor**
6. Uncheck "Notify people"
7. Click **Share**

---

## Verification

### Test the Backup

1. Make sure `service_account.json` is in your Diary folder
2. Start the Diary application: `python app.py`
3. Look for startup messages in the console
4. In your web browser, go to the Settings tab
5. Look for a "Backup to Google Drive" button (if you added one to the UI)
6. OR wait until 2 AM for the automatic backup to run

### Check Console Messages

Successful backup will show:
```
✓ Database backed up to Google Drive successfully!
  File: diary_latest.db
  Size: X.XX KB
  Folder: Diary_Backups
  Only latest backup kept (old backups deleted)
```

Failed backup will show:
```
✗ Google Drive backup failed: service_account.json not found
```

### Check Google Drive

**If using your own folder (Option B):**
- Go to [Google Drive](https://drive.google.com/)
- Open the `Diary_Backups` folder
- You should see `diary_latest.db` file
- Each new backup replaces the old one

**If using service account's Drive (Option A):**
- You won't see the folder in your Drive (it's in the service account's Drive)
- Trust the console messages to confirm backups are working

---

## Scheduled Backup Times

The system runs these automated tasks:

- **2:00 AM** - Google Drive backup (keeps only latest copy)
- **3:00 AM** - Cleanup old leave data (older than 2 years)
- **Your chosen time** - Send daily report email

---

## Troubleshooting

### Error: "service_account.json not found"

**Solution:** Make sure the `service_account.json` file is in the same folder as `app.py`

### Error: "Permission denied" or "Insufficient permissions"

**Solution:** 
1. Make sure you completed Step 2 (Enable Google Drive API)
2. If using your own folder (Option B), make sure you shared it with the service account email
3. Check that the service account has **Editor** permissions

### Error: "Invalid credentials"

**Solution:**
1. Download a new JSON key file from Google Cloud Console
2. Replace the old `service_account.json` with the new one
3. Restart the application

### Backup worked once, then stopped working

**Solution:**
1. Check your internet connection
2. Check if the Google Cloud Project is still active
3. Check if the Service Account key was deleted or disabled in Google Cloud Console

### I don't see the backup folder in my Google Drive

**Solution:**
- If you didn't do Step 7 Option B (sharing with your Drive), the folder exists only in the service account's Drive
- To see it in YOUR Drive, follow Step 7 Option B
- Alternatively, trust the console messages - if it says "backed up successfully", it worked

---

## File Locations

### Local Files
- Database: `instance/diary.db`
- Credentials: `service_account.json` (in project root)
- This guide: `GOOGLE_DRIVE_SETUP.md`

### Google Drive
- Backup folder: `Diary_Backups/`
- Backup file: `diary_latest.db` (always the most recent)

---

## Security Notes

⚠️ **IMPORTANT SECURITY INFORMATION:**

1. **Never share `service_account.json`** - This file gives full access to your Google Drive backup folder
2. **Never commit to git** - The file is already in `.gitignore` to prevent this
3. **Keep backups secure** - The database contains your diary data
4. **Service account only** - The service account can ONLY access folders you explicitly share with it

---

## Restoring from Backup

If your PC dies and you need to restore:

1. Install the Diary application on a new PC
2. Download `diary_latest.db` from your Google Drive `Diary_Backups` folder
3. Place it in the `instance/` folder as `diary.db`
4. Start the application - all your data is restored!

---

## Manual Backup

You can also trigger a manual backup anytime:

1. Use the web interface (if you add a backup button)
2. OR make a POST request to: `http://127.0.0.1:5050/api/backup-to-gdrive`

---

## Support

If you encounter issues:

1. Check the console for colored error messages (red = error, yellow = warning)
2. Verify all steps above were completed
3. Try a manual backup to see detailed error messages
4. Check Google Cloud Console to ensure the project and API are active

---

## Database Size Information

Based on your usage (10 diary entries/day, 24 temperature readings/day):

- **After 1 year:** ~1.6 MB
- **After 5 years:** ~8-9 MB
- **After 10 years:** ~16-17 MB

Google Drive free tier (15 GB) can easily store thousands of years of data!

---

**Setup Complete!** Your database will now automatically backup to Google Drive at 2 AM every day, keeping only the latest copy. 🎉

