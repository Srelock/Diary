# Security Setup Guide

## Initial Configuration

### Email Configuration Setup

**IMPORTANT:** The application requires email credentials to function, but these should NEVER be committed to git.

1. **Copy the example config:**
   ```bash
   cp config.example.py config.py
   ```

2. **Edit `config.py` with your credentials:**
   - Update `email` with your Gmail address
   - Update `password` with your Gmail App Password (not your regular password)
   - Update `recipient` with the default recipient email
   - **NEVER commit this file to git** (it's already in `.gitignore`)

3. **For Gmail users:**
   - You need to use an "App Password" instead of your regular password
   - See: https://support.google.com/accounts/answer/185833

### If You Previously Cloned This Repository

If you cloned this repository before November 3, 2025, the git history was rewritten to remove exposed credentials. You'll need to:

1. **Backup your local `config.py`** (if you've customized it)
2. **Re-clone the repository:**
   ```bash
   git clone https://github.com/Srelock/Diary
   ```
   OR
   **Reset your local repository:**
   ```bash
   git fetch origin
   git reset --hard origin/optimized  # or origin/main
   ```
3. **Restore your `config.py`** from backup

### Security Best Practices

- ✅ `config.py` is in `.gitignore` and will not be committed
- ✅ Use `config.example.py` as a template
- ✅ Store sensitive credentials only in `config.py`
- ❌ Never commit `config.py` to version control
- ❌ Never share your `config.py` file
- ❌ Never use your regular email password (use App Passwords)

## Credentials Changed on November 3, 2025

**If you saw the exposed credentials in git history before this date:**

The following credentials were exposed and have been removed from git history:
- Email: `diaryparkwest@gmail.com`
- App Password: `izcl aluk xxri mxit`

**RECOMMENDED ACTIONS:**
1. ✅ Generate a new Gmail App Password
2. ✅ Update your `config.py` with the new credentials
3. ✅ Delete the old App Password from your Google Account
   - Visit: https://myaccount.google.com/apppasswords
   - Revoke the old password

## Questions?

If you have questions about setting up email credentials, see:
- `docs/GOOGLE_DRIVE_SETUP_OAUTH2.md` for Google integration
- `docs/STAFF_MANAGEMENT_GUIDE.md` for general setup

