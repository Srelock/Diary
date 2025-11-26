# Google App Password Setup Guide

Simple step-by-step guide to create a Google App Password for email sending.

---

## What is an App Password?

An App Password is a special password that allows third-party apps (like this Diary app) to access your Gmail account securely. You need this instead of your regular Gmail password.

---

## Quick Setup (5 minutes)

### Step 1: Enable 2-Step Verification

**You MUST have 2-Step Verification enabled first!**

1. Go to: https://myaccount.google.com/security
2. Sign in with your Google account
3. Find **"2-Step Verification"** section
4. If it says **"Off"**, click it and follow the setup:
   - Click **"Get Started"**
   - Choose your phone number
   - Enter the verification code sent to your phone
   - Click **"Turn On"**
5. Wait for it to enable (takes a few seconds)

**⚠️ IMPORTANT:** You cannot create an App Password without 2-Step Verification enabled!

---

### Step 2: Create App Password

1. Go to: https://myaccount.google.com/apppasswords
   - Or: Google Account → Security → 2-Step Verification → App Passwords

2. You may need to sign in again

3. **Select app:**
   - Click the dropdown under "Select app"
   - Choose **"Mail"** (or "Other (Custom name)")
   - If using "Other", type: **"Diary App"**

4. **Select device:**
   - Click the dropdown under "Select device"
   - Choose **"Windows Computer"** (or "Other (Custom name)")
   - If using "Other", type: **"Diary App"**

5. Click **"Generate"**

6. **Copy the password:**
   - A 16-character password will appear (like: `abcd efgh ijkl mnop`)
   - **Copy it immediately** - you won't see it again!
   - Click **"Done"**

---

### Step 3: Use in Diary App

1. Open your Diary app Settings
2. Go to **Email & Reports** section
3. Enter your email settings:
   - **Sender Email:** Your Gmail address (e.g., `yourname@gmail.com`)
   - **Email Password / App Password:** Paste the 16-character App Password you just copied
   - **SMTP Server:** `smtp.gmail.com`
   - **SMTP Port:** `587`
4. Click **"Save Settings"**

---

## Troubleshooting

### ❌ "App Passwords" option not showing

**Problem:** You don't see "App Passwords" in your Google Account settings.

**Solution:**
1. Make sure 2-Step Verification is **enabled** (Step 1 above)
2. Wait a few minutes after enabling 2-Step Verification
3. Sign out and sign back into your Google Account
4. Try the App Passwords link again: https://myaccount.google.com/apppasswords

---

### ❌ "Sign in using your app password" error

**Problem:** Gmail says "Sign in using your app password" when trying to send emails.

**Solution:**
1. Make sure you're using the **App Password** (16 characters), NOT your regular Gmail password
2. The App Password should have spaces: `abcd efgh ijkl mnop` (you can remove spaces when pasting)
3. Make sure 2-Step Verification is enabled

---

### ❌ "Less secure app access" error

**Problem:** Google says "Less secure app access" is disabled.

**Solution:**
- Google no longer supports "Less secure app access"
- You **MUST** use App Passwords instead
- Follow Step 1 and Step 2 above to create an App Password

---

### ❌ App Password not working

**Solution:**
1. Make sure you copied the entire 16-character password
2. Remove any spaces when pasting (or keep them, both work)
3. Make sure you're using the **App Password**, not your regular password
4. Try generating a new App Password and updating it in the app

---

## Quick Reference

**App Password Format:**
- 16 characters
- Example: `abcd efgh ijkl mnop`
- Can include spaces or not (both work)

**Settings in Diary App:**
- **SMTP Server:** `smtp.gmail.com`
- **SMTP Port:** `587` (or `465` for SSL)
- **Email:** Your Gmail address
- **Password:** Your 16-character App Password

---

## Security Notes

✅ **Safe to use:**
- App Passwords are secure
- They only work for the specific app/device you created them for
- You can revoke them anytime

⚠️ **Important:**
- Never share your App Password
- If you suspect it's compromised, delete it and create a new one
- Each app should have its own App Password

---

## Need Help?

If you're still having trouble:
1. Make sure 2-Step Verification is enabled
2. Wait a few minutes after enabling it
3. Try generating a new App Password
4. Check that you're using the App Password (not your regular password) in the Diary app settings

---

**Last Updated:** November 2024

