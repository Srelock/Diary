# 📚 Google Drive Backup Setup Tutorial

Complete step-by-step guide to set up automatic daily backups of your Diary database to Google Drive.

---

## 🎯 What This Does

- **Automatic daily backups** at 2:00 AM
- **Keeps only the latest backup** (saves space)
- **Secure** - uses Google service accounts (no personal credentials)
- **Offsite backup** - protects your data if your PC fails

---

## ✅ Prerequisites

Before starting, make sure you have:

1. ✅ **Python packages installed** - Install required Google Drive libraries:
   ```bash
   pip install google-auth==2.25.2 google-auth-oauthlib==1.2.0 google-auth-httplib2==0.2.0 google-api-python-client==2.110.0
   ```
   Or install all requirements at once:
   ```bash
   pip install -r docs/requirements.txt
   ```

2. ✅ **Google account** - You need a Google account (Gmail account works)

3. ✅ **Internet connection** - Required for backups to work

4. ✅ **15-20 minutes** - Time needed to complete the setup

---

## 📋 Quick Setup Checklist

- [ ] Install Python packages (Prerequisites section above)
- [ ] Create Google Cloud Project
- [ ] Enable Google Drive API
- [ ] Create Service Account
- [ ] Download credentials JSON file
- [ ] Place `service_account.json` in project folder
- [ ] (Optional) Share folder in your Google Drive
- [ ] Test backup manually

---

## 🚀 Step-by-Step Setup

### Step 1: Install Required Packages

**Open PowerShell or Command Prompt** in your project folder and run:

```bash
pip install google-auth==2.25.2 google-auth-oauthlib==1.2.0 google-auth-httplib2==0.2.0 google-api-python-client==2.110.0
```

**Verify installation:**
```bash
python -c "import google.auth; print('✓ Google auth installed')"
python -c "from googleapiclient.discovery import build; print('✓ Google API client installed')"
```

---

### Step 2: Create Google Cloud Project

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**
   - Sign in with your Google account if prompted

2. Click **"Select a Project"** dropdown at the top of the page
   - It may show "My First Project" or "No project selected"

3. Click **"New Project"** button

4. Fill in the form:
   - **Project name:** `Diary Backup` (or any name you like)
   - **Location:** Leave default (No organization)

5. Click **"Create"** button
   - Wait 10-20 seconds for the project to be created

6. **Select your new project** from the project dropdown (top of page)
   - Make sure it shows your project name

---

### Step 3: Enable Google Drive API

1. In your Google Cloud Project, look for the left sidebar menu (☰ hamburger icon)
   - Click it if the menu is collapsed

2. Navigate to: **APIs & Services** → **Library**
   - Or go directly to: https://console.cloud.google.com/apis/library

3. In the search box at the top, type: **"Google Drive API"**

4. Click on **"Google Drive API"** from the search results

5. Click the blue **"ENABLE"** button
   - Wait a few seconds for it to enable
   - You should see "API enabled" confirmation

6. You're done! The API is now enabled for your project.

---

### Step 4: Create Service Account

A service account is a special type of Google account that applications can use (not a real person).

1. Still in Google Cloud Console, go to: **APIs & Services** → **Credentials**
   - Or directly: https://console.cloud.google.com/apis/credentials

2. Click the **"+ CREATE CREDENTIALS"** button at the top of the page

3. Select **"Service Account"** from the dropdown menu

4. Fill in the service account details:
   - **Service account name:** `diary-backup` (or any name)
   - **Service account ID:** Auto-filled (don't change)
   - **Description:** `Automated diary database backup`

5. Click **"CREATE AND CONTINUE"**

6. **Skip optional steps:**
   - Click **"SKIP"** or **"CONTINUE"** for Grant access (optional)
   - Click **"DONE"** to finish

7. You should now see your service account listed on the Credentials page.

---

### Step 5: Download Credentials (JSON Key File)

This JSON file contains the credentials your app needs to access Google Drive.

1. On the **Credentials** page, find your service account in the list
   - It will show an email like: `diary-backup@your-project.iam.gserviceaccount.com`

2. **Click on the service account email address** (the blue clickable link)

3. You're now in the Service Account details page. Click the **"KEYS"** tab

4. Click **"ADD KEY"** → **"Create new key"**

5. In the popup:
   - Select **JSON** format (radio button)
   - Click **"CREATE"**

6. **A JSON file will automatically download** to your Downloads folder
   - File name will be something like: `your-project-12345-abc123.json`

---

### Step 6: Install Credentials File

1. **Find the downloaded JSON file** in your Downloads folder

2. **Rename it** to exactly: `service_account.json`
   - Remove any project ID or random numbers from the filename
   - The name must match exactly

3. **Move the file** to your Diary application folder
   - It should be in the same folder as `app.py`
   - Example location: `C:\Users\YourName\Desktop\Project\Diary\service_account.json`

4. **Verify the file is in the correct location:**
   ```
   Your Project Folder/
   ├── app.py
   ├── config.py
   ├── service_account.json  ← Should be here
   ├── instance/
   └── ...
   ```

⚠️ **SECURITY WARNING:** Never share this file! It gives access to your Google Drive backups.

---

### Step 7: Get Service Account Email

You'll need this email address for the optional step of sharing a folder in your own Google Drive.

1. **Open `service_account.json`** with Notepad or any text editor

2. **Find the line** that looks like:
   ```json
   "client_email": "diary-backup@your-project-12345.iam.gserviceaccount.com"
   ```

3. **Copy the entire email address** (the part in quotes after `client_email`)
   - Example: `diary-backup@your-project-12345.iam.gserviceaccount.com`
   - Keep this handy for the next step

---

### Step 8: Choose Backup Location (Two Options)

#### Option A: Automatic Folder (Recommended - Easiest)

**What happens:** The app creates a folder in the service account's Google Drive. You won't see it in your personal Drive, but backups work automatically.

**Steps:**
1. **Do nothing!** Just make sure `service_account.json` is in your project folder
2. Start your Diary app
3. The app automatically creates `Diary_Backups` folder on first backup
4. **You're done!**

**Pros:** ✅ Easiest setup, no extra steps  
**Cons:** ❌ You can't see the backup in your own Google Drive

---

#### Option B: Use Your Own Google Drive Folder (Recommended for Visibility)

**What happens:** Backups are stored in a folder in YOUR Google Drive that you can see and access.

**Steps:**

1. Go to **[Google Drive](https://drive.google.com/)**
   - Sign in if needed

2. Click **"+ New"** button → **"Folder"**

3. Name the folder: `Diary_Backups`
   - Click **"Create"**

4. **Right-click** the new `Diary_Backups` folder → Click **"Share"**

5. In the sharing dialog:
   - Paste the service account email from Step 7
   - Change permission dropdown to **"Editor"**
   - **Uncheck** "Notify people" (important - no need to notify a service account)
   - Click **"Share"** or **"Send"**

6. You should see the service account email listed under "People with access"

**Pros:** ✅ You can see backups in your Drive, easy to download  
**Cons:** ❌ Extra setup step required

---

## ✅ Testing the Setup

### Test 1: Verify File Location

1. Check that `service_account.json` is in your project root folder (same folder as `app.py`)
2. Verify the filename is exactly `service_account.json` (not `service_account.json.txt` or anything else)

### Test 2: Manual Backup Test

1. **Start your Diary application:**
   ```bash
   python app.py
   ```

2. **Open the web interface** in your browser: `http://localhost:5000`

3. **Go to Settings tab**

4. **Look for console output** when the app starts:
   - ✅ Success: No error messages about `service_account.json`
   - ❌ Error: Red text saying "service_account.json not found"

5. **Trigger a manual backup:**
   - Option A: Use the web interface if there's a backup button
   - Option B: Make a POST request using curl or Postman:
     ```bash
     curl -X POST http://localhost:5000/api/backup-to-gdrive
     ```
   - Option C: Wait for automatic backup at 2:00 AM

### Test 3: Check Success Messages

**Successful backup shows in console:**
```
✓ Database backed up to Google Drive successfully!
  File: diary_latest.db
  Size: 245.67 KB
  Folder: Diary_Backups
  Only latest backup kept (old backups deleted)
```

**Failed backup shows:**
```
✗ Google Drive backup failed: service_account.json not found
  Please follow instructions in GOOGLE_DRIVE_SETUP.md to set up credentials
```

### Test 4: Verify in Google Drive (Option B only)

If you used Option B (your own folder):
1. Go to [Google Drive](https://drive.google.com/)
2. Open the `Diary_Backups` folder
3. You should see: `diary_latest.db` file
4. Check the file size matches what was shown in console

---

## 📅 When Backups Run

The system automatically runs:

- **2:00 AM daily** - Google Drive backup (keeps only latest copy)
- **3:00 AM daily** - Cleanup old leave data (older than 2 years)
- **Your chosen time** - Send daily report email

You can also trigger **manual backups anytime** via:
- Web interface (if you add a backup button)
- API endpoint: `POST http://localhost:5000/api/backup-to-gdrive`

---

## 🔧 Troubleshooting

### ❌ Error: "service_account.json not found"

**Problem:** The credentials file is missing or in the wrong location.

**Solution:**
1. Check the file exists in the same folder as `app.py`
2. Verify filename is exactly `service_account.json` (case-sensitive)
3. Make sure it's not `service_account.json.txt` (Windows sometimes hides extensions)
4. Check file path: Should be `C:\Users\YourName\Desktop\Project\Diary\service_account.json`

---

### ❌ Error: "Permission denied" or "Insufficient permissions"

**Problem:** Service account doesn't have access to Google Drive.

**Solution:**
1. Verify you completed Step 3 (Enable Google Drive API)
2. If using Option B (your own folder), check:
   - Folder is shared with the service account email
   - Permission is set to **Editor** (not Viewer)
   - Service account email matches exactly (copy-paste to avoid typos)

---

### ❌ Error: "Invalid credentials"

**Problem:** The JSON file is corrupted or from a different project.

**Solution:**
1. Go back to Google Cloud Console → Credentials
2. Delete the old key (if needed) and create a new one
3. Download a fresh JSON file
4. Replace `service_account.json` with the new file
5. Restart the application

---

### ❌ Error: "ModuleNotFoundError: No module named 'google'"

**Problem:** Python packages not installed.

**Solution:**
```bash
pip install google-auth==2.25.2 google-auth-oauthlib==1.2.0 google-auth-httplib2==0.2.0 google-api-python-client==2.110.0
```

---

### ❌ Backup worked once, then stopped working

**Problem:** Service account key deleted, project disabled, or network issue.

**Solution:**
1. Check internet connection
2. Verify Google Cloud Project is still active
3. Check if Service Account key was deleted in Google Cloud Console
4. Try downloading a new credentials file
5. Check console for specific error messages

---

### ❌ "I don't see the backup folder in my Google Drive"

**Problem:** You're using Option A (automatic folder), which stores backups in the service account's Drive, not yours.

**Solution:**
1. This is normal! Option A stores backups in the service account's Drive
2. To see backups in YOUR Drive, follow Step 8 Option B
3. Alternatively, trust the console messages - if it says "backed up successfully", it worked
4. You can restore by downloading the file programmatically if needed

---

### ❌ Backup fails silently with no error message

**Problem:** Connection issue or API quota exceeded.

**Solution:**
1. Check internet connection
2. Verify Google Drive API is enabled (Step 3)
3. Check Google Cloud Console for API quota limits
4. Try manual backup to see detailed error message
5. Check Windows Firewall isn't blocking the connection

---

## 📁 File Locations

### Local Files (Your Computer)
- **Database:** `instance/diary.db`
- **Credentials:** `service_account.json` (in project root, same folder as `app.py`)
- **This guide:** `docs/GOOGLE_DRIVE_SETUP.md`

### Google Drive
- **Backup folder:** `Diary_Backups/` (created automatically)
- **Backup file:** `diary_latest.db` (always the most recent - old backups are deleted)

---

## 🔒 Security Notes

⚠️ **IMPORTANT SECURITY INFORMATION:**

1. **Never share `service_account.json`**
   - This file gives full access to your Google Drive backup folder
   - Don't email it, don't upload it anywhere public

2. **Already protected**
   - The file is in `.gitignore` to prevent accidental git commits
   - Keep it secure on your computer only

3. **Service account permissions**
   - The service account can ONLY access folders you explicitly share with it
   - It has no access to your other Google Drive files

4. **Database security**
   - Your database contains diary data - backups are encrypted in transit (HTTPS)
   - Only you (and the service account) have access

---

## 🔄 Restoring from Backup

If your PC crashes and you need to restore your data:

1. **Install the Diary application** on your new PC
   - Follow normal installation instructions

2. **Set up Google Drive backup again** (Steps 1-6 above)
   - Or reuse your existing `service_account.json` if you have it

3. **Download the backup file:**
   - If using Option B: Go to Google Drive → `Diary_Backups` → Download `diary_latest.db`
   - If using Option A: You'll need to use Google Drive API or create a new backup setup

4. **Replace the database:**
   - Place `diary_latest.db` in the `instance/` folder
   - Rename it to `diary.db`
   - Location: `instance/diary.db`

5. **Start the application** - All your data is restored! 🎉

---

## 📊 Database Size Information

Your database is very small:

- **After 1 year:** ~1.6 MB (with 10 entries/day + 24 temperature readings/day)
- **After 5 years:** ~8-9 MB
- **After 10 years:** ~16-17 MB

**Google Drive free tier:** 15 GB  
**Your usage:** Even after 10 years, you're using less than 0.1% of free storage!

You can backup thousands of years of data with the free tier. 😊

---

## 🎉 Setup Complete!

Congratulations! Your database will now automatically backup to Google Drive at 2:00 AM every day.

**What happens next:**
- ✅ Backups run automatically every night at 2:00 AM
- ✅ Only the latest backup is kept (saves space)
- ✅ Your data is safe in the cloud
- ✅ No action needed from you

**To verify it's working:**
- Check console messages when backup runs
- Or trigger a manual backup via the API endpoint

**Need help?** Check the Troubleshooting section above or review the error messages in your console.

---

## 📞 Additional Help

**Common Issues:**
- Red error messages in console = Check Troubleshooting section
- Yellow warning messages = Usually informational (can often be ignored)
- Green success messages = Everything working correctly

**Manual Backup API:**
- Endpoint: `POST http://localhost:5000/api/backup-to-gdrive`
- Returns: JSON with `success: true/false` and message/error

**Check Google Cloud Console:**
- Project status: https://console.cloud.google.com/
- API status: https://console.cloud.google.com/apis/library
- Credentials: https://console.cloud.google.com/apis/credentials

---

**Last Updated:** November 2024  
**Guide Version:** 2.0
