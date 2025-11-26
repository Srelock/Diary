# Fix "Access Blocked" Error for Google Drive Backup

## Problem
You see: **"Access blocked: Diary Backup has not completed the Google verification process"**

This happens because your OAuth2 app is in "Testing" mode and you haven't added yourself as a test user.

---

## Quick Fix (2 minutes)

### Step 1: Go to OAuth Consent Screen

1. Go to: **https://console.cloud.google.com/**
2. **Select your project** (the one you created for Diary Backup)
3. Go to: **APIs & Services** → **OAuth consent screen**
   - Direct link: https://console.cloud.google.com/apis/credentials/consent

### Step 2: Add Yourself as Test User

1. Scroll down to **"Test users"** section (Step 3 of 4)
2. Click **"+ ADD USERS"** button
3. Enter your Google account email:
   - **If backups go to portersparkwest account:** Enter `portersparkwest@gmail.com`
   - **If backups go to diaryparkwest account:** Enter `diaryparkwest@gmail.com`
   - **Use the account where you want backups stored!**
4. Click **"ADD"**
5. Click **"SAVE AND CONTINUE"** (or just "SAVE" if you're done)

### Step 3: Try Authorization Again

1. Go back to your Diary app
2. Click **"Backup to Google Drive"** button
3. Browser will open - sign in with the account you just added
4. Click **"Allow"** to grant permissions
5. **Token.pickle will be created automatically!**

---

## Alternative: Publish Your App (Advanced)

If you want to allow ANY Google account to use the backup (not just test users):

### Option A: Keep in Testing Mode (Recommended for Personal Use)
- Just add yourself as test user (Steps 1-2 above)
- Simple and works perfectly for personal use
- No verification needed

### Option B: Publish Your App (For Multiple Users)

**⚠️ WARNING:** Publishing requires Google verification which can take days/weeks and may require:
- Privacy policy URL
- Terms of service URL
- App verification process
- Only do this if you need multiple users

**Steps:**
1. Go to OAuth consent screen
2. Click **"PUBLISH APP"** button at the top
3. Confirm you want to publish
4. Wait for Google to review (can take days)

**For personal use, just add yourself as test user - it's much easier!**

---

## Which Account to Add?

**Important:** Add the account where you want backups stored!

- **If you see backups in `portersparkwest@gmail.com` Drive:** Add that account
- **If you see backups in `diaryparkwest@gmail.com` Drive:** Add that account
- **The account you authorize with = the account that stores backups**

---

## Verify It's Fixed

After adding yourself as test user:

1. ✅ Try backup again
2. ✅ Browser opens without "Access blocked" error
3. ✅ You can sign in and grant permissions
4. ✅ `token.pickle` file gets created in your Diary folder
5. ✅ Backup completes successfully

---

## Troubleshooting

### ❌ Still getting "Access blocked" after adding test user

**Solutions:**
1. **Wait 1-2 minutes** - Google needs time to update
2. **Make sure you added the correct email** - Check spelling
3. **Sign out and sign back in** to Google in your browser
4. **Clear browser cache** and try again
5. **Check you're using the right Google account** when authorizing

### ❌ "Test users" section not showing

**Solution:**
- Make sure your OAuth consent screen is set to **"External"** (not Internal)
- Internal apps don't have test users (they're for Google Workspace only)

### ❌ Token.pickle still not created

**Check:**
1. Did authorization complete successfully? (Did you click "Allow"?)
2. Check the console/terminal for error messages
3. Make sure you have write permissions in the Diary folder
4. Try running the app as administrator

---

## Summary

**For personal use (recommended):**
1. Add yourself as test user in Google Cloud Console
2. Authorize with that account
3. Done! Token.pickle will be created automatically

**No need to publish the app** - test users work perfectly for personal backups!

---

**Last Updated:** November 2024

