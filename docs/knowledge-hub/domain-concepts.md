# Domain concepts

Short conceptual map tying user-facing features to code locations. For field-level schemas see [Coneshare data model](../coneshare-data-model.md).

---

## Tenancy & identity

- **Organization** is the tenant boundary ( branding, users, storage policy ).
- **User** logs in with **email**; belongs to one organization; **personal quota** tracked in `total_document_size` with optional `custom_file_size_quota_mb`.
- **Roles:** member vs admin capabilities (admin API + `/admin/*` frontend routes).

---

## Folder taxonomy

Folders are not only “user directories” — they have explicit **folder_type**:

| Type | Meaning |
|------|---------|
| `root` | Organization root (`__root__`) |
| `personal` | User library (`created_by` set) |
| `vault` | Dataroom backing storage under `__datarooms__/{dataroom_id}/` |

**Invariant:** Vault folders use `created_by is NULL` with structural parent chain; documents in vault consume **dataroom storage quota**, not uploader personal quota (v2).

Soft delete: `deleted_at` / `deleted_by` on folders and documents; querysets use `.active()` patterns.

---

## Documents & versions

- **Document** — logical file; lives in a folder; has `created_by`.
- **DocumentVersion** — binary payload reference (`storage_key`), render pipeline state, optional `metadata` (e.g. cloud import etag).
- **DocumentPage** — per-page preview assets and link/text metadata for overlays.

Version promotion and cloud refresh use **row locks** (`select_for_update`) to avoid race on primary version.

---

## Share links

- **ShareLink** targets exactly one of: single **document** or **dataroom** (DB constraints enforce XOR).
- **Slug** drives public URL `/view/:slug`.
- Protections compose sequentially: expiry → password → email → NDA (session flags on view session).
- **ViewSession** binds a **Viewer** (anonymous or identified) to activity; **PageView** / video engagement segments power analytics.
- **DataroomVisit** records folder/document navigation and downloads with **snapshot fields** for renamed/deleted items.

Downloads are **logged server-side** on download GET handlers (not legacy frontend POST).

---

## Datarooms

- Structured collections with optional **collaborators**, **custom order** (`DataroomItemOrder`), branding (banner gallery, logo modes).
- **storage_version** 1 vs 2 controls vault layout; upgrade endpoint migrates legacy rooms.
- Share links can expose entire datarooms with scoped folder endpoints (see plans under `plans/sharelinks/`).

Collaborators may **view** documents in rooms they do not own; mutations remain owner-scoped.

---

## Viewers & analytics

- Owner dashboard: `analytics/dashboard`, document stats, link-level sessions.
- Public viewer emits page views, link clicks, video watch segments (media_type on PageView).
- Performance: dedicated dashboard serializers; composite indexes on hot filters.

---

## Automations & notifications

- **AutomationRule** + destinations (email, webhook, Slack).
- Per-link email toggles on `ShareLink` resolved at delivery time (single global rule design — see memory / automations doc).
- Dataroom-scoped rules for room owners.

---

## Cloud import

- **CloudConnection** stores OAuth tokens (encrypted); API exposes Hashid string ids.
- Import creates/updates **DocumentVersion**; Google Workspace files exported (Docs→PDF, etc.).
- Failed import rolls back primary version inside transaction.

---

## File requests

- Owner creates **FileRequest** with public slug `/upload/:slug`.
- Upload path parallels document upload (request/finalize + Go tokens).
- Optional ClamAV profile for malware scanning.

---

## Security primitives

| Concern | Implementation pointers |
|---------|-------------------------|
| API keys | HMAC hashed storage, tier permission class |
| Link passwords | Encrypted at rest (`django-cryptography`) |
| Overlay XSS | `isSafeUrl` + trim/control-char strip on URLs |
| Path traversal | Go token path validation |
| Video watermark bypass | Disable raw download when watermark required |

---

## ID & serializer conventions

- ULIDs (26 char strings) for most primary keys — use `CharField`, not `UUIDField`.
- Cloud `connection_id`: **CharField** (Hashids), not integer.
- API JSON: **snake_case**.
