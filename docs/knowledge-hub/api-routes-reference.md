# API routes reference

Base URL in dev: `http://localhost:8000/api/v1/`  
OpenAPI: `backend/docs/api/openapi.yaml` (regenerate with `make api.schema`)  
Swagger UI (DEBUG): `/api/schema/swagger/`

JSON field names are **snake_case** everywhere.

---

## Authentication & session

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/token/` | Public | JWT pair (email login) |
| POST | `/token/refresh/` | Refresh token | |
| POST | `/logout/` | JWT | Blacklist refresh |
| POST | `/signup/` | Public | Request signup |
| POST | `/signup/verify/` | Public | Complete signup |
| POST | `/users/set-password/` | JWT | |
| GET | `/languages/` | Public | Supported locales |
| GET | `/public/settings/` | Public | Feature flags / public config |
| GET | `/_health/` | Public | Health check (`core`) |

**API keys:** `Authorization: Bearer cs_live_…` — tier enforced globally unless view overrides permissions incorrectly.

---

## Core resources (router)

| Resource | Path prefix |
|----------|-------------|
| Organizations | `/organizations/` |
| Users | `/users/` |
| Groups | `/groups/` |
| API keys | `/api-keys/` |

---

## Documents & folders

| Method | Path | Notes |
|--------|------|-------|
| CRUD | `/folders/`, `/documents/` | ViewSets; soft-delete via trash |
| GET | `/folders/root/` | Org root folder id |
| POST | `/folders/ensure-paths/` | Create nested path segments |
| POST | `/uploads/document/request/` | Returns Go upload URL |
| POST | `/uploads/document/finalize/` | Creates document + version |
| POST | `/uploads/document/{id}/versions/request/` | New version upload |
| POST | `/uploads/document/{id}/versions/finalize/` | |
| GET | `/documents/{id}/preview-data/` | Viewer payload |
| GET | `/documents/{id}/download/` | Authorized download URL |
| POST | `/actions/move/` | Bulk move docs/folders |
| * | `/trash/` | Trash ViewSet |

Document ViewSet also exposes actions (stats, status, copy, versions list, promote version, rebuild preview) — see ViewSet `@action` methods in `documents/views.py`.

---

## Share links & viewer (authenticated + public)

**Authenticated router:** `/share-links/`, `/share-link-templates/`, `/view-sessions/`, `/viewers/`, `/qna-threads/`

**Public slug routes** (`/links/{slug}/…`):

| Path suffix | Purpose |
|-------------|---------|
| `public-meta/` | Link metadata without session |
| `verify-password/` | Password gate |
| `request-access/` | Email verification request |
| `verify-access-token/confirm/` | Email token confirm |
| `accept-nda/` | NDA acceptance |
| `view-data/` | Main viewer bootstrap (may 401 with `protectionType`) |
| `page/{n}/` | Server-rendered page image |
| `render-page/{n}/` | Watermarked render |
| `download-file/` | File download (logged server-side) |
| `download-folder/{folder_id}/` | Dataroom folder zip |
| `qna-summary/`, `qna-threads/`, `…/messages/` | Public Q&A |

**Telemetry:**

| POST | Path |
|------|------|
| | `/page-views/record/` |
| | `/link-clicks/record/` |

---

## Datarooms

| Router | Path |
|--------|------|
| Datarooms | `/datarooms/` |
| Folders in room | `/dataroom-folders/` |
| Document membership | `/dataroom-documents/` |

Notable actions on dataroom ViewSet (see `datarooms/views.py`): collaborators, upgrade storage, branding, reorder items.

**Admin:** `/api/v1/admin/datarooms/` — org-wide list, quotas, metrics.

---

## Analytics

| GET | Path |
|-----|------|
| | `/analytics/dashboard/` |
| | `/analytics/daily-visits/` |
| | `/analytics/links/` |
| | `/analytics/view-sessions/` |
| | `/analytics/view-sessions/{id}/` |

---

## Automations

Routers: `/automations/`, `/automation-destinations/`, `/automation-deliveries/`, `/automation-assignments/`

---

## Cloud files

Prefix: `/api/v1/cloud/`

| Path | Purpose |
|------|---------|
| `providers/` | List providers |
| `connections/` | OAuth connections (Hashid ids) |
| `connect/{provider}/`, `callback/{provider}/` | OAuth |
| `connections/{id}/list/`, `…/folders/` | Browse |
| `connections/{id}/import/` | Import into library |
| `documents/{id}/refresh/` | Sync from cloud |
| `documents/{id}/import_version/` | New version from cloud |

---

## File requests

| Path | Audience |
|------|----------|
| `/file-requests/` | Authenticated owners |
| `/public/file-requests/{slug}/` | Public meta |
| `…/request-upload/`, `…/finalize-upload/` | Public upload |

---

## Admin API

| Prefix | Content |
|--------|---------|
| `/api/v1/admin/organization/` | Org profile |
| `/api/v1/admin/settings/` | Dynamic settings |
| `/api/v1/admin/users/` | User admin |
| `/api/v1/admin/login-activities/` | |
| `/api/v1/admin/security-threat-events/` | |
| `/api/v1/admin/datarooms/` | Dataroom governance |

Admin UI pages map in [Frontend reference](./frontend-reference.md).

---

## Go file service (not Django)

Host: `http://localhost:8080` (typical)

| Method | Path | Caller |
|--------|------|--------|
| POST | `/internal/v1/generate-upload-url` | Backend (token auth) |
| POST | `/internal/v1/generate-download-url` | Backend |
| POST | `/internal/v1/generate-preview-url` | Backend |
| POST | `/internal/v1/delete-file`, `/copy-file` | Backend |
| PUT | `/files/upload/{token}` | Browser |
| GET | `/files/download/{token}` | Browser |
| GET | `/files/preview/{token}` (+ optional subpath for HLS) | Browser |

Wildcard preview paths must validate against the **authorized directory** for the token, not merely the storage root (path traversal).
