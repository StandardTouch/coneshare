# Legal pages (Terms & Privacy)

## In-app routes (Allure / self-hosted SPA)

| Page | URL (relative to `SITE_DOMAIN`) |
|------|----------------------------------|
| Terms of Service | `/terms` |
| Privacy Policy | `/privacy` |

Default links in `frontend/src/lib/brandConfig.js` point to these paths. Login and signup footers use `BrandingProvider`, which can override URLs via **Admin → Branding** (`terms_url`, `privacy_policy_url` on the organization).

## Source files (edit content here)

- Terms body: `frontend/src/content/legal/termsOfServiceEn.jsx`
- Privacy body: `frontend/src/content/legal/privacyPolicyEn.jsx`
- Layout shell: `frontend/src/pages/LegalDocumentPage.jsx`
- Operator name comes from public branding API; contact email from `BRAND_CONFIG.contactEmail`

## Portal (marketing site)

Separate short policies for **coneshare.com** only:

- `portal/app/terms/page.js`
- `portal/app/privacy-policy/page.js`

Those do not apply to a self-hosted clinic deployment.

## Important

Generated text describes a Coneshare-style document platform (share links, datarooms, analytics, file requests, cloud import). **Have qualified legal counsel review** before production use, especially for healthcare (PDPL, patient data, retention).
