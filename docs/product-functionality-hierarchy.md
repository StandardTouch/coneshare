# Coneshare — Product functionality (hierarchy)

Brief capability map of what the application offers today, grouped for navigation and planning. For implementation detail, follow links in [Knowledge hub](./knowledge-hub/README.md) and [feature docs](./features/).

---

## 1. Platform foundation

- **Multi-tenant organization**
  - Single org per self-hosted deployment (tenant boundary for users, branding, storage policy)
  - Organization branding (logo, name, website, terms/privacy URLs)
- **Runtime configuration**
  - Admin-managed dynamic settings (quotas, feature toggles, cloud provider enablement, preview limits)
  - Public settings endpoint for frontend feature flags
- **Internationalization**
  - UI locales: English, Simplified Chinese, Russian, German, French, Dutch
  - Backend error messages mapped to frontend translations

---

## 2. Users, groups & authentication

- **Account lifecycle**
  - Email-based signup (request + verify) and login
  - JWT access/refresh tokens, logout (refresh blacklist)
  - Password set/change flows
- **User profile**
  - Name, avatar, language preference
  - Personal document storage quota (global default + per-user override)
- **User groups**
  - Org-scoped groups for membership organization
- **Roles**
  - Member vs admin (admin routes and APIs gated)
- **Security observability**
  - Login activity log (admin)
  - Security threat events (admin)

---

## 3. Document library & file operations

- **Folder tree**
  - Nested personal folders under org root
  - Root folder API, ensure-path creation, breadcrumbs
  - Folder types: root, personal, system vault (for dataroom backing storage)
- **Documents**
  - Create via direct upload or cloud import
  - Rename, move, copy, delete (soft delete)
  - Starred items, list sort persistence (documents page)
  - Search/sort-oriented library UX
- **Bulk actions**
  - Multi-select delete, move across folders
- **Trash**
  - Soft-deleted items recovery bin
  - Scheduled purge of expired trash (background)
- **Storage & quotas**
  - Personal quota on user library uploads
  - Dataroom vault uploads governed by room quota (not personal)
  - Secure file storage via Go file service (tokenized upload/download)

---

## 4. Upload & processing pipeline

- **Direct upload**
  - Two-step flow: request upload URL → finalize document/version
  - Progress-friendly uploads from web UI (including drag-and-drop folders)
- **Document versions**
  - Multiple versions per document; promote version to primary
  - Paginated version history page
  - Quota checks on promotion (personal vs dataroom vault)
- **Background processing**
  - Status lifecycle: uploading → processing → ready / error
  - Lazy preview generation on first view where applicable
- **Format handling (async)**
  - Office → PDF conversion
  - PDF page rasterization and link-annotation harvest
  - Spreadsheet preview generation
  - HEIC image transcoding
  - Video → HLS streaming (dedicated worker queue, optional feature flag)
- **Cloud import**
  - Connect: Google Drive, Dropbox, Nextcloud
  - Browse folders/files, import into library
  - Refresh document from cloud; import new version from cloud
  - Google Workspace export (Docs/Sheets/Slides) where direct download is blocked
- **Optional malware scanning**
  - ClamAV profile for file-request uploads (compose profile)

---

## 5. Preview, viewer & protection (owner & recipient)

- **Preview engines**
  - Client-side PDF (pdf.js)
  - Server-rendered PDF/image pages with text layer and safe link overlays
  - Markdown (in-browser, scroll analytics)
  - Spreadsheets
  - Video (HLS proxy playback, engagement segments)
- **Dynamic preview eligibility**
  - Read-time rules (size limits, MIME type, feature flags) — not stale upload-time flags
- **Watermarks**
  - Viewer overlay watermarks on supported types
  - Flattened/watermarked PDF download modes where configured
  - Video: no overlay watermark; download blocked when link requires watermarking
- **Copy/print restrictions**
  - Viewer-side protection hooks on supported preview types
- **Internal preview**
  - Document detail page preview for owners/collaborators
  - Rebuild preview action

---

## 6. Secure sharing (share links)

- **Link targets**
  - Single document **or** entire dataroom (mutually exclusive)
- **Access controls**
  - Active/inactive toggle, expiration
  - Password protection
  - Email collection and email verification
  - Custom NDA text + acceptance audit trail
- **Permissions**
  - Allow/disallow download
  - Watermark enablement and settings
  - Share link templates (reusable defaults)
- **Dataroom link scoping**
  - Per-item visibility/download/watermark via dataroom link settings
  - Folder-scoped navigation in public viewer (breadcrumbs, siblings)
- **Owner tools**
  - Create/edit/delete links from document or dataroom
  - Owner preview session (safe preview without resetting analytics)
  - Per-link analytics page
- **Public viewer experience** (`/view/:slug`)
  - Sequential gates: password → email → NDA → content
  - Document or dataroom navigation, inline viewers
  - Dataroom banner/branding in viewer chrome

---

## 7. Viewer Q&A (share links)

- **Threaded Q&A on shared links**
  - Viewer creates threads/messages under active view session
  - Owner manages threads (status, replies) in app
  - Gated by dataroom-level and link-level `enable_qna` flags
- **Automation hooks**
  - Events for new threads/messages/close/reopen

---

## 8. Virtual datarooms (VDR)

- **Room lifecycle**
  - Create, rename, delete datarooms
  - Storage v1 (legacy) vs v2 (org vault) with one-click upgrade
- **Content structure**
  - Folders and documents inside room (add from library, upload direct, remove, move)
  - Custom item ordering (independent of “show file index” badge)
  - Optional numeric index display on items
  - Replicate folder trees from personal library into room
- **Collaboration**
  - Invite collaborators to a dataroom
  - Collaborators view (and limited manage per rules) content uploaded by others
  - Ownership transfer
- **Branding & presentation**
  - Banner modes: single, gallery, none
  - Logo mode: organization vs custom dataroom logo
  - Accent/theme colors for viewer
- **Dataroom analytics**
  - View sessions scoped to room
  - Activity log with snapshots for deleted/renamed items
- **Admin governance** (org admin)
  - Cross-room list, KPIs, quota adjustment, vault upgrades

---

## 9. Analytics & engagement

- **Dashboard**
  - Summary KPIs, recent links, recent view sessions (optimized queries)
- **Link & session lists**
  - All share links, all view sessions (paginated)
  - Per-document and per-link session/detail views
- **Engagement telemetry**
  - Page views (duration, completion) for documents
  - Video watch segments (time range, speed, fullscreen, mute)
  - Link click tracking in PDF overlays
  - Dataroom folder/document visits and download timestamps
- **Viewer identity**
  - Viewer records (email when collected, IP, user agent, geo fields where available)

---

## 10. Automations & notifications

- **Destinations**
  - Email, generic webhook, Slack, Discord, WeChat Work, Feishu
- **Rules**
  - Scoped: global, share-link, dataroom
  - Event-driven delivery (views, uploads, file requests, Q&A, etc.)
- **Operations**
  - Delivery queue with retries, dead-letter, replay
  - Assignments for follow-up ownership
- **Per-link email preferences**
  - Boolean flags on share links resolved at send time

---

## 11. File requests (inbound uploads)

- **Owner-managed requests**
  - Create request links with slug, expiry, size/type constraints, active toggle
- **Public upload page** (`/upload/:slug`)
  - No account required for external contributors
  - Same tokenized upload pattern as document uploads
- **Received files**
  - Attribution metadata; files land as documents in owner’s workflow
  - Export/download collected submissions (owner)
- **Automations**
  - Upload completion triggers automation events

---

## 12. Administration (organization)

- **Users**
  - List, create, update, deactivate (last-admin safeguards)
  - User detail and storage quota adjustment
- **Organization**
  - Settings, branding admin pages
- **Datarooms**
  - Org-wide dataroom admin console
- **Security**
  - Login activity, security alerts

---

## 13. API & integrations (developers)

- **REST API**
  - Versioned `/api/v1/` JSON API (snake_case)
  - OpenAPI schema generation
- **API keys**
  - User-issued keys (`cs_live_…`) with tiers: read-only, read-write, full access
- **Remote MCP server**
  - AI/agent tools against Coneshare API (separate `mcp-server` service)
- **Cloud OAuth**
  - Provider callbacks integrated with frontend settings

---

## 14. Public & satellite surfaces

- **Marketing / docs website** (`portal/`)
  - Next.js site: product pages, blog, integration guides (not the authenticated app)
- **End-to-end tests** (`e2e/`)
  - Playwright coverage of critical flows (quality gate, not a user feature)

---

## 15. Known gaps (not offered today)

Summarized from [roadmap](./strategy/coneshare-roadmap.md) — not exhaustive:

- Resumable/chunked uploads (Tus-style)
- Dataroom grid view; drag-and-drop reorder in tree UI
- Group-based ACLs inside dataroom trees
- Single hierarchical dataroom analytics rollup view
- Full enterprise audit log beyond login activity
- SAML SSO; org-wide enforced share policies

---

## Related documents

| Need | Doc |
|------|-----|
| Code navigation | [Knowledge hub](./knowledge-hub/README.md) |
| Entities & fields | [Data model](./coneshare-data-model.md) |
| Shipped vs planned | [Roadmap](./strategy/coneshare-roadmap.md) |
