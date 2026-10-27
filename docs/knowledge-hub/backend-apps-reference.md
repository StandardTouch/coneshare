# Backend Django apps reference

All apps are registered in `backend/backend/settings.py` → `INSTALLED_APPS`. URL mounting is in `backend/backend/urls.py`.

**Dependency rule:** `core` must not import runtime code from feature apps (`documents`, `sharelinks`, …). Shared utilities (e.g. `StandardResultsSetPagination`) live under `core/`.

Primary keys across domain models are typically **ULID strings** (26 chars), not UUIDs — use `CharField` in serializers for IDs and Hashid-encoded cloud connection IDs.

---

## `core`

**Prefix:** `/api/v1/` (router) + `/api/v1/admin/` (admin API)

| Area | Location | Responsibility |
|------|----------|----------------|
| Models | `core/models.py` | `Organization`, `User`, `UserGroup`, `APIKey`, dynamic settings, login activity, security events |
| Auth | `core/authentication.py`, `core/views.py` | JWT login/refresh/logout, signup verify, `APIKeyAuthentication` (must run before JWT) |
| Permissions | `core/permissions.py` | `IsAdmin`, `APIKeyTierPermission` (read_only / read_write / full_access) |
| Pagination | `core/pagination.py` | `StandardResultsSetPagination` — import from here, not from documents |
| Admin API | `core/admin_views.py`, `core/admin_urls.py` | Org settings, users, login activity, security threats |
| i18n | `core/i18n_utils.py` | Backend translation helpers |
| Tasks | `core/tasks.py` | Misc maintenance (see file) |

**Global DRF defaults** (`settings.py`):

- `DEFAULT_AUTHENTICATION_CLASSES`: API key, then JWT
- `DEFAULT_PERMISSION_CLASSES`: `IsAuthenticated` + `APIKeyTierPermission`

**Gotcha:** Setting `permission_classes = [IsAuthenticated]` on a ViewSet **replaces** defaults and drops `APIKeyTierPermission`. Prefer inheriting defaults or `super().get_permissions()`.

---

## `documents`

**Prefix:** `/api/v1/`

| Module | Role |
|--------|------|
| `models.py` | `Folder` (types: root / personal / vault), `Document`, `DocumentVersion`, `DocumentPage`; soft delete |
| `views.py` | ViewSets + upload request/finalize, preview data, download, move, trash |
| `services.py` | Upload finalization, delete, version promote, quota checks, vault detection |
| `tasks.py` | PDF pages, office→PDF, video HLS, HEIC, spreadsheet preview, trash purge |
| `fileserver.py` | Client to Go internal API |
| `renderers/` | Server-side preview render pipeline pieces |
| `signals.py` | Lifecycle hooks |
| `malware_scan.py` | ClamAV integration when enabled |

Key non-router routes (`documents/urls.py`):

- `POST uploads/document/request/` + `finalize/` — direct upload flow via Go tokens
- `GET documents/{id}/preview-data/` — viewer bootstrap (engines, pages, watermark flags)
- `GET documents/{id}/download/`

Deep dives: [document-upload](../features/document-upload.md), [document-process](../features/document-process.md), [file-storage](../features/file-storage.md).

---

## `sharelinks`

**Prefix:** `/api/v1/`

| Module | Role |
|--------|------|
| `models.py` | `ShareLink`, `ViewSession`, `PageView`, `Viewer`, `DataroomVisit`, Q&A, NDA, templates |
| `views.py` | CRUD + **public** slug routes (`/links/{slug}/…`) |
| `services.py` | Session authorization helpers, watermark/download policy |
| `tasks.py` | Notification/async side effects |

Public viewer flow (password → email → NDA → view-data) is centralized in helpers such as `_verify_share_link_session_authorization` (see code reviews in `docs/code-reviews/`).

Analytics on links: also consumed by `analytics` app and frontend `ShareLinkAnalyticsPage`.

---

## `datarooms`

**Prefix:** `/api/v1/datarooms`, `dataroom-folders`, `dataroom-documents`

| Module | Role |
|--------|------|
| `models.py` | `Dataroom`, folders/documents junction, `DataroomItemOrder`, collaborators, branding |
| `views.py` | User-scoped dataroom CRUD, folder tree, ordering |
| `services.py` | Vault folder creation, storage upgrade v1→v2, quota |
| `admin_views.py` | `/api/v1/admin/datarooms/` — org-wide governance |

**Storage versions:**

- **v1:** Legacy user-scoped upload folders
- **v2:** Org vault under `__root__/__datarooms__/{id}/`; quota on `dataroom.storage_quota_mb`, not uploader personal quota

See [dataroom-implementation](../features/dataroom-implementation.md) and [vault refactor doc](../../backend/docs/dataroom-vault-storage-refactor.md).

---

## `analytics`

**Prefix:** `/api/v1/analytics/…`

Dashboard summary, daily visits, paginated links and view sessions. Uses **lightweight serializers** in `analytics/serializers.py` to avoid N+1 from nested share-link serializers.

---

## `automations`

**Prefix:** `/api/v1/automations`, destinations, deliveries, assignments

Event-driven notifications (email, webhooks, Slack). Rules tie to scopes (e.g. DATAROOM). Share-link booleans often gate per-link email preferences.

---

## `cloudfiles`

**Prefix:** `/api/v1/cloud/…`

OAuth connect/callback, connections, browse, import, refresh, import-version. Providers under `cloudfiles/providers/` (Google Drive, Dropbox, Nextcloud, etc.).

Tasks in `cloudfiles/tasks.py` for async import. Version metadata on `DocumentVersion.metadata` JSON (`cloud_import`, etag).

---

## `filerequests`

**Prefix:** `/api/v1/file-requests` + `/api/v1/public/file-requests/{slug}/…`

Owner-managed upload requests; public upload pages mirror document upload token flow.

---

## Project package `backend/`

| Path | Role |
|------|------|
| `backend/settings.py` | Django settings, Celery, storage, feature flags |
| `backend/urls.py` | Root URLconf |
| `backend/celery.py` | Celery app |
| `backend/utils.py` | Shared helpers |

---

## Tests

| Suite | Path |
|-------|------|
| Unit/integration | `backend/tests/<app>/` |
| BDD | `backend/bdd/features/`, `backend/bdd/step_definitions/` |
| Config | `backend/pytest.ini`, `backend/bdd/conftest.py`, `backend/tests/conftest.py` |

Run targeted pytest files inside the backend container rather than the full suite during iterative work (see [playbook](./agent-development-playbook.md)).
