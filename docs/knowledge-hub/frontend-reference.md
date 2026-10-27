# Frontend SPA reference

Stack: **Vite + React**, **React Router**, **Tailwind**, **Radix**-based UI under `src/components/ui/`, **Axios** client in `src/services/api.js`, **i18next** locales in `src/locales/`.

Dev URL: `http://localhost:5173` — API calls use relative `/api/v1` (proxied to Django in dev).

---

## Application shell

| File | Role |
|------|------|
| `src/App.jsx` | Route table |
| `src/main.jsx` | Bootstrap, providers |
| `src/layouts/MainLayout.jsx` | Authenticated chrome + sidebar |

### Global providers (`contexts/`)

| Provider | Purpose |
|----------|---------|
| `UserProvider.jsx` | Current user, quota; expose `refreshUser()` after uploads/deletes/settings |
| `UploadProvider.jsx` | Upload queue / progress |
| `BrandingProvider.jsx` | Org branding for viewer and gates |

---

## Routes (`App.jsx`)

**Public (no main layout):**

| Path | Page |
|------|------|
| `/login`, `/signup`, `/signup/verify` | Auth |
| `/view/:slug` | `ShareLinkViewerPage` — external viewer |
| `/upload/:slug` | `PublicUploadPage` — file request uploads |
| `/auth/:providerName/callback` | Cloud OAuth return |
| `/500` | Error page |

**Authenticated (`MainLayout`):**

| Path | Page |
|------|------|
| `/` | Home dashboard |
| `/documents`, `/documents/folders/:folderId` | Library |
| `/documents/:documentId` | Document detail + internal preview |
| `/documents/:documentId/versions` | Version history |
| `/documents/:documentId/links/:linkId` | Link analytics |
| `/trash` | Trash |
| `/datarooms`, `/datarooms/:dataroomId` | Dataroom list & room |
| `/file-requests`, `/file-requests/:requestId` | File requests |
| `/analytics/links`, `/analytics/view-sessions` | Analytics lists |
| `/automations` | Automation rules |
| `/settings/*` | User settings, integrations, API keys |
| `/admin/*` | Org admin (settings, branding, users, datarooms, security) |

---

## API client (`services/api.js`)

- Attaches JWT from `localStorage` (`access_token`, `refresh_token`).
- **401 handling:** refreshes token except for public link protection responses (`protectionType`: password/email/nda).
- Errors mapped via `utils/errorTranslator.js` → i18n keys in toasts.

Most domain calls are named exports on the default axios instance (documents, share links, datarooms, cloud, admin, analytics). When adding endpoints, extend this file and mirror patterns (pagination query params, slug-based public routes).

Auth helpers: `services/authService.js`.

---

## Document & preview UI

| Component | Use case |
|-----------|----------|
| `PreviewViewer.jsx` | Chooses engine from preview-data |
| `PdfJsViewer.jsx` | Client-side PDF (`PDF_PREVIEW_ENGINE=pdfjs`) |
| `PdfPage.jsx` | Server-rendered page + text layer overlays |
| `VideoViewer.jsx` | HLS / native; engagement segments |
| `MarkdownViewer.jsx` | `.md` synchronous render |
| `SpreadsheetViewer.jsx` | Tabular previews |

**Share link / dataroom viewer:** `components/viewer/`

- `DataroomViewer.jsx`, `DataroomFileTree.jsx`, `DataroomBannerGallery.jsx`
- Gates: `PasswordForm`, `EmailForm`, `NDAForm`
- `QnAPanel.jsx`, `ViewerToolbar.jsx`

**Lists & library:** `components/documents/` — `DocumentsList.jsx` (dropzone + folder drag), `FolderBrowser.jsx`, dialogs under `components/dialogs/`.

---

## Hooks & utilities (selected)

| Path | Notes |
|------|-------|
| `hooks/useSortedList.js` | Sort persistence via `storageKey` (documents list uses `coneshare_documents_sort`; dataroom intentionally unpersisted) |
| `hooks/useLinkClickTracking.js` | Use `sendBeacon` / `keepalive` for navigation-safe telemetry |
| `lib/apiErrors.js` | Error parsing helpers |
| `utils/isSafeUrl` (or equivalent) | **Required** for overlay `href` — blocks `javascript:`, `data:`, etc. |

---

## Styling & UI gotchas

- Default `Button` variant may still use hardcoded grays instead of `bg-primary` — theming via CSS variables in `index.css`.
- Radix `DropdownMenu.Item`: avoid `e.preventDefault()` in `onSelect` if the menu should close (use `stopPropagation` only when needed).

---

## Tests

| Location | Runner |
|----------|--------|
| `src/tests/**` | Vitest + Testing Library |
| Whitelist | `frontend/vitest.whitelist.json` — **new tests must be listed** for `make test.front` / CI |

Mock `window.location` with full shape (`origin`, `pathname`, `search`, `hash`, `assign`) when testing Router components.

Local (host): `cd frontend && npm run dev|test|lint`  
Container: see [playbook](./agent-development-playbook.md).

---

## i18n

Locales: `en`, `zh-hans`, `ru`, `de`, `fr`, `nl` under `src/locales/*/translation.json`.  
Backend errors: map raw English strings in `errorTranslator.js`. Strategy: [i18n doc](../strategy/i18n-strategy-and-architecture.md).
