# Agent & developer playbook

Operational guide for making safe, reviewable changes in this repo. Aligns with root **`AGENTS.md`** and episodic notes in **`.agent/memory.md`**.

---

## Before you edit

1. Read [Knowledge hub README](./README.md) for orientation.
2. Scan `.agent/memory.md` for gotchas (migrations, Vitest whitelist, permission classes, vault quota, XSS, etc.).
3. Prefer **targeted tests** over full suite during iteration.

---

## “Where do I change X?”

| Goal | Start here |
|------|------------|
| New REST endpoint | App `views.py` + `urls.py`; serializer in `serializers.py`; OpenAPI via `make api.schema` |
| Upload/download bytes | `documents/views.py` (finalize), `documents/fileserver.py`, `core/main.go` |
| Preview / watermark | `documents/tasks.py`, `documents/renderers/`, frontend `*Viewer.jsx` |
| Public link behavior | `sharelinks/views.py`, `sharelinks/services.py`, `ShareLinkViewerPage.jsx` |
| Dataroom ordering / vault | `datarooms/services.py`, `datarooms/serializers.py`, `DataroomPage.jsx` |
| Quota | `documents/services.py`, `User.total_document_size`, dataroom `storage_quota_mb` |
| Admin org settings | `core/admin_views.py`, `AdminSettingsPage.jsx` |
| Cloud import | `cloudfiles/providers/`, `cloudfiles/tasks.py` |
| Email / webhooks | `automations/` |
| i18n strings | `frontend/src/locales/*/translation.json`, backend `.po` + `compile_po.py` |
| E2E flow | `e2e/tests/` |

---

## Docker test commands

Project name prefix: **`COMPOSE_PROJECT_NAME=coneshare`**

### Backend (pytest)

```bash
COMPOSE_PROJECT_NAME=coneshare docker-compose exec backend pytest -q tests/sharelinks/test_views.py
COMPOSE_PROJECT_NAME=coneshare docker-compose exec backend pytest -q tests/documents/test_vault_storage_refactor.py -k test_name
COMPOSE_PROJECT_NAME=coneshare docker-compose exec backend pytest
```

### Frontend (Vitest)

```bash
COMPOSE_PROJECT_NAME=coneshare docker-compose exec frontend npx vitest run src/tests/pages/ShareLinkViewerPage.test.jsx
COMPOSE_PROJECT_NAME=coneshare docker-compose exec frontend npm run test:whitelist
```

**Whitelist:** add new test file paths to `frontend/vitest.whitelist.json` before expecting CI/`make test.front` to run them.

### Core (Go)

```bash
make test.core
```

### BDD

```bash
make test.bdd
```

---

## Policies agents must respect

| Policy | Detail |
|--------|--------|
| **Migrations** | Do **not** run or create Django migrations unless the user explicitly asks. Call out schema needs in summary. |
| **Git commits** | Only when user requests; no `git config` changes; no force-push to main. |
| **Memory file** | Do not append `.agent/memory.md` without user confirmation (use draft format in AGENTS.md). |
| **DRF permissions** | Avoid overriding `permission_classes` in a way that drops `APIKeyTierPermission`. |
| **core imports** | Do not add feature-app imports to `core`. |
| **Security** | Sanitize overlay URLs; validate share-link session on all render/download paths; enforce share-link target ownership on create. |
| **TDD** | When fixing bugs per team preference: reproduce with failing test first, then fix. |

---

## Local package commands (without Docker)

```bash
cd frontend && npm run dev|build|test|lint
cd portal && npm run dev|build|lint
cd e2e && npm test
```

---

## Useful maintenance commands

```bash
make logs
make compile.po
make api.schema
COMPOSE_PROJECT_NAME=coneshare docker-compose exec backend python compile_po.py
scripts/check-vault-integrity.sh   # vault folder invariants
```

---

## Documentation expectations

- New **features:** add `docs/features/<name>.md` from [template](../features/_template.md) with strategy refs.
- **Knowledge hub:** update this folder when service topology or app boundaries change materially.
- **Plans:** exploratory design stays in `plans/` until shipped.

---

## MCP & external integrations

- Remote MCP server: `mcp-server/coneshare_mcp/server.py`, doc [remote-mcp-server](../features/remote-mcp-server.md).
- Portal content: MDX under `portal/content/`.

---

## Quick smoke test (manual)

After `make up` + migrate (user-run):

1. Upload a document at `:5173`
2. Create a share link
3. Open `/view/{slug}` in a private window
4. Confirm view-data and preview load

See root [README](../../README.md) troubleshooting for `.env`, Redis/Celery, and storage permissions.
