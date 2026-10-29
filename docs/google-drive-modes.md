# Google Drive Integration Modes

Coneshare supports two integration modes for Google Drive to balance functionality with OAuth consent requirements.

## Overview

### Picker Mode (Default, Recommended)

**What it does:** Uses the official Google Picker UI (a popup file chooser) with limited, non-sensitive OAuth scopes. Users pick files directly in the Google Drive interface, and Coneshare imports them.

**OAuth scopes requested:**
- `openid`
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/userinfo.profile`
- `https://www.googleapis.com/auth/drive.file` (access only to files the user explicitly picks)

**Benefits:**
- **No Google verification required** — all scopes are non-sensitive, so users see a standard OAuth consent screen without "Google hasn't verified this app" warnings
- Faster deployment — no need to wait for Google's restricted scope review
- User-friendly file picker UI with search, shared drives, and folder navigation

**Limitations:**
- Users must pick files one at a time via the popup (no server-side folder browsing in the Coneshare UI)
- Admins cannot browse Google Drive folders within Coneshare

### Browse Mode (Legacy)

**What it does:** Provides server-side folder browsing directly in the Coneshare import/export dialogs, similar to Dropbox and Nextcloud integrations.

**OAuth scopes requested:**
- `openid`
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/userinfo.profile`
- `https://www.googleapis.com/auth/drive.readonly` **(restricted scope)**
- `https://www.googleapis.com/auth/drive.file`

**Benefits:**
- Full server-side folder browsing and navigation
- Consistent UX with other cloud providers

**Limitations:**
- **Requires Google verification** — `drive.readonly` is a restricted scope, triggering the "Google hasn't verified this app" warning until Google reviews and approves your OAuth app
- Verification process can take weeks and requires providing justification and video demos to Google

## Configuration

### Required Settings (Both Modes)

Set these in the Coneshare admin settings UI (or via environment variables):

1. **GOOGLE_DRIVE_CLIENT_ID** — OAuth 2.0 Client ID from Google Cloud Console
2. **GOOGLE_DRIVE_CLIENT_SECRET** — OAuth 2.0 Client Secret

### Picker Mode Additional Settings

3. **GOOGLE_DRIVE_MODE** — Set to `picker` (default)
4. **GOOGLE_DRIVE_API_KEY** — Browser API key (see setup below)
5. **GOOGLE_DRIVE_APP_ID** — Google Cloud project number (see setup below)

### Browse Mode Settings

3. **GOOGLE_DRIVE_MODE** — Set to `browse`

## Google Cloud Setup for Picker Mode

### 1. Enable APIs

In the [Google Cloud Console](https://console.cloud.google.com/), navigate to **APIs & Services > Library** and enable:
- Google Drive API
- Google Picker API

### 2. Create or Update OAuth 2.0 Client

1. Go to **APIs & Services > Credentials**
2. Edit your existing OAuth 2.0 Client ID (or create a new one of type "Web application")
3. **Authorized JavaScript origins:** Add `https://share.allureclinic.com`
4. **Authorized redirect URIs:** Add `https://share.allureclinic.com/auth/google_drive/callback`
5. Note the **Client ID** and **Client Secret** — save these in Coneshare admin settings

### 3. OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. **Scopes:** Add only the following non-sensitive scopes:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `.../auth/drive.file`
3. **Do NOT add** `drive.readonly` — this is a restricted scope that triggers verification warnings
4. Publishing: You can publish the app to "External" immediately without Google review

### 4. Create a Browser API Key

1. Go to **APIs & Services > Credentials > Create Credentials > API Key**
2. Click **Edit API key** (the key you just created)
3. **Application restrictions:** Set to "HTTP referrers"
   - Add referrer: `https://share.allureclinic.com/*`
4. **API restrictions:** Restrict to "Google Picker API"
5. Save the API key — this is your **GOOGLE_DRIVE_API_KEY**

### 5. Get the Project Number (App ID)

1. Go to **IAM & Admin > Settings**
2. Copy the **Project number** — this is your **GOOGLE_DRIVE_APP_ID**

### 6. Configure Coneshare

In Coneshare admin settings:
- **GOOGLE_DRIVE_CLIENT_ID:** (from step 2)
- **GOOGLE_DRIVE_CLIENT_SECRET:** (from step 2)
- **GOOGLE_DRIVE_MODE:** `picker`
- **GOOGLE_DRIVE_API_KEY:** (from step 4)
- **GOOGLE_DRIVE_APP_ID:** (from step 5)

## Google Cloud Setup for Browse Mode

Follow steps 1-3 above, but:
- In step 3, **add** the `drive.readonly` scope to the OAuth consent screen
- Skip steps 4-5 (browser API key and project number are not needed)
- In Coneshare admin settings, set **GOOGLE_DRIVE_MODE** to `browse`

**Important:** With `drive.readonly` added, users will see a "Google hasn't verified this app" warning until you complete [Google's OAuth app verification process](https://support.google.com/cloud/answer/9110914).

## Switching Modes

### From Browse to Picker

1. In Google Cloud Console:
   - Remove `drive.readonly` from the OAuth consent screen scopes
   - Create a browser API key (step 4 above) if you haven't already
   - Get the project number (step 5 above)
2. In Coneshare admin settings:
   - Set **GOOGLE_DRIVE_MODE** to `picker`
   - Add **GOOGLE_DRIVE_API_KEY** and **GOOGLE_DRIVE_APP_ID**
   - Save settings
3. **Users must reconnect Google Drive:** Existing tokens include `drive.readonly` and will be rejected. Users will see a reconnect prompt.

### From Picker to Browse

1. In Google Cloud Console:
   - Add `drive.readonly` to the OAuth consent screen scopes
   - Submit for Google verification (or accept the "unverified app" warning)
2. In Coneshare admin settings:
   - Set **GOOGLE_DRIVE_MODE** to `browse`
   - Save settings (API key and App ID are ignored in browse mode but can be left configured)
3. **Users must reconnect Google Drive:** Existing tokens lack `drive.readonly` and cannot list folders. Users will see a reconnect prompt.

## How It Works

### Picker Mode Flow

1. User clicks "Import from Google Drive" in Coneshare
2. Coneshare frontend fetches a short-lived access token from the backend (the refresh token never leaves the server)
3. Frontend loads the Google Picker API and opens the picker with the access token
4. User selects a file in the Google Drive picker
5. Picker returns the file's `id`, `name`, `size`, and `mimeType` to Coneshare
6. Coneshare imports the file using the same backend flow as browse mode

### Browse Mode Flow

1. User clicks "Import from Google Drive" in Coneshare
2. Coneshare backend lists folders and files using the `drive.readonly` scope
3. User navigates folders in the Coneshare UI
4. User clicks "Import" on a file
5. Coneshare imports the file

Both modes:
- Support importing Google Docs/Sheets/Slides (exported as PDF/XLSX/PPTX)
- Support refresh/sync (importing new versions of previously imported files)
- Work with shared drives (Team Drives)

## Troubleshooting

### "Google hasn't verified this app" warning

You're in browse mode with `drive.readonly` enabled. Either:
- Switch to picker mode (recommended for faster deployment), or
- Complete [Google's verification process](https://support.google.com/cloud/answer/9110914)

### "Failed to open Google Drive Picker"

1. Check that **GOOGLE_DRIVE_API_KEY** and **GOOGLE_DRIVE_APP_ID** are configured in admin settings
2. Verify the API key is restricted to the Google Picker API and your domain referrer
3. Check browser console for CORS or API key errors
4. Ensure the Google Picker API is enabled in Google Cloud Console

### "Your authorization has expired. Please reconnect."

Users see this after switching modes. They must:
1. Go to Settings > Cloud Connections
2. Disconnect Google Drive
3. Reconnect with the new scopes

### List endpoint returns 400 in picker mode

Expected behavior — server-side folder listing is disabled in picker mode. Use the picker UI instead.

## FAQ

**Q: Can I use picker mode for some users and browse mode for others?**  
A: No, the mode is a global setting per Coneshare instance.

**Q: Does picker mode work on mobile?**  
A: Yes, the Google Picker is responsive and works on mobile browsers.

**Q: Can users import multiple files at once in picker mode?**  
A: The picker supports multi-select in the implementation, but the current flow imports one file per dialog open. Users can open the dialog multiple times.

**Q: What happens to documents already imported from Google Drive when I switch modes?**  
A: They remain accessible. The refresh/sync feature continues to work if users reconnect with the new scopes.

**Q: Do exported files (uploading to Google Drive) work in both modes?**  
A: Yes. Picker mode uses the picker to select a destination folder; browse mode uses server-side folder browsing. Both use `drive.file` scope to write.
