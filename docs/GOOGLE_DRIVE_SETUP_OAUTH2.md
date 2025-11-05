# 📚 Google Drive Backup Setup - OAuth2 User Credentials

Complete step-by-step guide to set up automatic daily backups using OAuth2 user credentials (works with free Google accounts).

---

## 🎯 What This Does

- **Automatic daily backups** at 2:00 AM
- **Keeps only the latest backup** (saves space)
- **Uses YOUR Google account** (not a service account) - uses your storage quota
- **One-time authorization** - sign in once, then automatic forever
- **Works with free Google accounts** ✅

---

## ✅ Prerequisites

Before starting, make sure you have:

1. ✅ **Python packages installed** - Already installed:
   - `google-auth`
   - `google-auth-oauthlib`
   - `google-auth-httplib2`
   - `google-api-python-client`

2. ✅ **Google account** - Your personal Gmail/Google account

3. ✅ **Internet connection** - Required for backups

4. ✅ **15-20 minutes** - Time needed to complete the setup

---

## 📋 Quick Setup Checklist

- [ ] Install Python packages (already done)
- [ ] Create Google Cloud Project
- [ ] Enable Google Drive API
- [ ] Create OAuth2 Client ID (NOT service account)
- [ ] Download credentials.json file
- [ ] Place `credentials.json` in project folder
- [ ] Run first backup to authorize (one-time)

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**
   - Sign in with your Google account if prompted

2. Click **"Select a Project"** dropdown at the top
   - Click **"New Project"**

3. Fill in:
   - **Project name:** `Diary Backup` (or any name)
   - Click **"Create"**

4. **Select your new project** from the dropdown

---

### Step 2: Enable Google Drive API

1. In Google Cloud Console, go to: **APIs & Services** → **Library**
   - Or directly: https://console.cloud.google.com/apis/library

2. Search for: **"Google Drive API"**

3. Click on **"Google Drive API"**

4. Click **"ENABLE"**

5. Wait for it to enable (a few seconds)

---

### Step 3: Configure OAuth Consent Screen

1. Go to: **APIs & Services** → **OAuth consent screen**
   - Or: https://console.cloud.google.com/apis/credentials/consent

2. Select **"External"** (for personal use)
   - Click **"CREATE"**

3. Fill in **App information:**
   - **App name:** `Diary Backup` (or any name)
   - **User support email:** Your email address
   - **Developer contact:** Your email address
   - Click **"SAVE AND CONTINUE"**

4. **Scopes** (Step 2):
   - Click **"ADD OR REMOVE SCOPES"**
   - Search for: `drive.file`
   - Check the box for: **".../auth/drive.file"**
   - Click **"UPDATE"**
   - Click **"SAVE AND CONTINUE"**

5. **Test users** (Step 3):
   - Click **"ADD USERS"**
   - Add your own Google account email
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**

6. **Summary** (Step 4):
   - Review and click **"BACK TO DASHBOARD"**

---

### Step 4: Create OAuth2 Client ID Credentials

**IMPORTANT:** Create OAuth2 Client ID, NOT Service Account!

1. Go to: **APIs & Services** → **Credentials**
   - Or: https://console.cloud.google.com/apis/credentials

2. Click **"+ CREATE CREDENTIALS"** at the top

3. Select **"OAuth client ID"** (NOT Service Account!)

4. If prompted for **Application type:**
   - Select **"Desktop app"**
   - **Name:** `Diary Backup Client` (or any name)
   - Click **"CREATE"**

5. **A popup will appear** with your credentials:
   - **DO NOT CLOSE THIS POPUP YET!**

6. Click **"DOWNLOAD JSON"** button in the popup
   - A file named `client_secret_xxxxx.json` will download

7. **Close the popup** by clicking OK

---

### Step 5: Install Credentials File

1. **Find the downloaded file** in your Downloads folder
   - Name will be like: `client_secret_123456789-abcdefg.apps.googleusercontent.com.json`

2. **Rename it** to exactly: `credentials.json`
   - Remove the long client ID part from the filename

3. **Move the file** to your Diary application folder
   - Same folder as `app.py`
   - Example: `C:\Users\YourName\Desktop\Project\Diary\credentials.json`

4. **Verify location:**
   ```
   Your Project Folder/
   ├── app.py
   ├── config.py
   ├── credentials.json  ← Should be here
   ├── instance/
   └── ...
   ```

⚠️ **SECURITY:** Never share this file! It contains your OAuth2 credentials.

---

## ✅ First-Time Authorization

When you run your first backup, the app will ask you to authorize:

1. **Start your Diary app:**
   ```bash
   python app.py
   ```

2. **Trigger a manual backup:**
   - Option A: Wait for automatic backup at 2:00 AM
   - Option B: Use the web interface (Settings tab → Backup button)
   - Option C: API call: `POST http://localhost:5000/api/backup-to-gdrive`

3. **Browser will open automatically:**
   - Google sign-in page appears
   - Sign in with YOUR Google account
   - You may see: "Google hasn't verified this app"
   - Click **"Advanced"** → **"Go to Diary Backup (unsafe)"**

4. **Grant permissions:**
   - Click **"Allow"** to grant Drive access
   - You'll see: "The authentication flow has completed"

5. **Close the browser tab** - authorization is complete!

6. **Check the console:**
   ```
   ✓ Google Drive authorization successful!
   ✓ Credentials saved for future use
   ✓ Database backed up to Google Drive successfully!
   ```

7. **Done!** Future backups will be automatic - no sign-in needed!

---

## 📅 When Backups Run

- **2:00 AM daily** - Automatic Google Drive backup
- **Manual anytime** - Via web interface or API

---

## 🔧 Troubleshooting

### ❌ Error: "credentials.json not found"

**Solution:**
1. Make sure `credentials.json` is in the same folder as `app.py`
2. Check filename is exactly `credentials.json` (case-sensitive)
3. Verify it's not `credentials.json.txt` (Windows may hide extensions)

---

### ❌ Error: "Access blocked: This app's request is invalid"

**Solution:**
1. Make sure you added yourself as a test user (Step 3)
2. Check OAuth consent screen is configured (External app)
3. Verify you're signed in with the correct Google account

---

### ❌ "Google hasn't verified this app" warning

**Solution:**
- This is normal for personal projects
- Click **"Advanced"** → **"Go to [Your App Name] (unsafe)"**
- This is safe - you created the app yourself!

---

### ❌ Browser doesn't open automatically

**Solution:**
1. Check console for the authorization URL
2. Copy the URL from console
3. Paste it into your browser manually
4. Complete the authorization

---

### ❌ Token expired error

**Solution:**
- Delete `token.pickle` file
- Run backup again - it will re-authorize automatically
- Tokens refresh automatically, but if refresh fails, re-auth is needed

---

## 📁 File Locations

### Local Files
- **Database:** `instance/diary.db`
- **OAuth2 Credentials:** `credentials.json` (in project root)
- **Token (auto-created):** `token.pickle` (in project root, stores authorization)
- **This guide:** `docs/GOOGLE_DRIVE_SETUP_OAUTH2.md`

### Google Drive
- **Backup folder:** `Diary_Backups/` (created automatically if doesn't exist)
- **Backup file:** `diary_latest.db` (always the most recent)

---

## 🔒 Security Notes

⚠️ **IMPORTANT:**

1. **`credentials.json`** - Contains OAuth2 client ID and secret
   - Never share this file
   - Already in `.gitignore` (won't be committed to git)

2. **`token.pickle`** - Stores your authorization token
   - Allows automatic backups without re-signing
   - If compromised, delete it and re-authorize
   - Already in `.gitignore`

3. **OAuth2 Scope:**
   - Uses `drive.file` scope (limited access)
   - Only accesses files created by this app
   - Cannot access your other Drive files

4. **Automatic Token Refresh:**
   - Tokens refresh automatically
   - No action needed from you

---

## 🔄 Restoring from Backup

If your PC crashes:

1. **Install Diary app** on new PC
2. **Set up OAuth2 again** (Steps 1-5 above)
3. **Authorize on first backup** (automatic)
4. **Download backup from Google Drive:**
   - Go to: https://drive.google.com/
   - Open `Diary_Backups` folder
   - Download `diary_latest.db`
5. **Restore database:**
   - Place in `instance/` folder as `diary.db`
   - Start app - all data restored!

---

## 📊 Database Size

Your database is very small:
- **After 1 year:** ~1.6 MB
- **After 5 years:** ~8-9 MB
- **After 10 years:** ~16-17 MB

**Google Drive free tier:** 15 GB  
You can backup thousands of years of data! 📦

---

## 🎉 Setup Complete!

After first authorization, backups will be **fully automatic**:
- ✅ No sign-in needed after first time
- ✅ Runs at 2:00 AM daily
- ✅ Uses your Google Drive storage
- ✅ Only latest backup kept (saves space)

---

## 🔄 Switching from Service Account to OAuth2

If you were using service account before:

1. **Delete old files:**
   - Remove `service_account.json` (if exists)

2. **Follow this guide** to set up OAuth2

3. **On first backup:**
   - Browser opens for authorization
   - Sign in with your Google account
   - Authorization saved in `token.pickle`

4. **Done!** Future backups are automatic.

---

**Last Updated:** November 2024  
**Version:** OAuth2 User Credentials

