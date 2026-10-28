# Google OAuth app branding verification (Allure / self-hosted)

Google Cloud Console → **Google Auth Platform → Branding** may reject verification for three common reasons. Use this checklist after deploying the latest frontend.

## 1. Domain ownership (`share.allureclinic.com`)

**Error:** *The website of your home page URL is not registered to you.*

**Fix:**

1. Use the **same Google account** that owns the Cloud project (`allure-clinics`).
2. Open [Google Search Console](https://search.google.com/search-console).
3. Add property **`https://share.allureclinic.com`** (URL-prefix or Domain property).
4. Verify via **DNS TXT** record at your DNS host (recommended) or HTML file upload.
5. Wait until Search Console shows **Verified** (can take minutes to 24 hours).
6. Retry branding verification.

Also verify the OAuth client **Authorized domains** includes `allureclinic.com` (and `allureclinics.net` if used in emails).

## 2. Privacy policy content

**Error:** *Privacy policy does not have sufficient content.*

**Fix:**

1. Deploy frontend with expanded policy at **`https://share.allureclinic.com/privacy`** (must load **without login**).
2. Policy must explicitly describe **Google user data** (Drive OAuth): what you access, why, storage, sharing, revocation — see `frontend/src/content/legal/privacyPolicyEn.jsx` Section 2.6.
3. In OAuth consent screen, set **Privacy policy URL** to exactly:  
   `https://share.allureclinic.com/privacy`
4. Open the URL in an incognito window and confirm full text is visible (not a blank SPA shell).

## 3. Application home page

**Error:** (Often tied to domain ownership.)

Set **Application home page** to the public landing page (no login required):

```text
https://share.allureclinic.com/welcome
```

Do **not** use `/` if it requires staff login for meaningful content. Route `/welcome` is `PublicAppHomePage.jsx`.

Optional: redirect marketing root `/` to `/welcome` at the reverse proxy.

## 4. Logo

**Error:** *Logo does not uniquely identify your brand.*

**Fix:**

1. Upload **`/brand/logo-full.png`** (wordmark + symbol) in Google Console, not a generic stock icon alone.
2. Logo must match **Allure Clinic** branding on the live site and your trademark (no other company’s mark).
3. Minimum size per Google guidelines (typically 120×120 px square canvas).
4. Ensure favicon and login page use the same brand assets.

## 5. Consistency

| Field | Recommended value |
|--------|-------------------|
| Application name | Allure Clinic (or exact product name shown to users) |
| User support email | `share@allureclinics.net` (match `BRAND_CONFIG.contactEmail`) |
| App logo | Allure full logo |
| Home page | `https://share.allureclinic.com/welcome` |
| Privacy policy | `https://share.allureclinic.com/privacy` |
| Authorized redirect URI | `https://share.allureclinic.com/auth/google_drive/callback` |

## 6. After fixes

1. Deploy updated build to production.
2. Wait **24 hours** after Search Console verification (Google’s own guidance).
3. In Branding → **Prepare for verification** → choose **I have fixed the issues**.
4. If rejected again, use **Request re-verification** with notes pointing to `/welcome` and `/privacy`.

Legal text is a template — counsel should review before relying on it for compliance.
