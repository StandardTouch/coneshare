# Monorepo & services

## Repository layout

| Directory | Technology | Purpose |
|-----------|------------|---------|
| `backend/` | Django 5 + DRF | REST API, business logic, Celery task definitions, pytest/BDD tests |
| `core/` | Go (chi router) | Tokenized upload/download/preview; path traversal guards |
| `frontend/` | Vite + React | Authenticated SPA + public share-link / upload pages |
| `portal/` | Next.js + MDX | Marketing, blog, integration landing pages |
| `e2e/` | Playwright | Full-stack browser tests |
| `mcp-server/` | Python FastMCP | Remote MCP tools calling Coneshare API |
| `docs/` | Markdown | Feature docs, strategy, this knowledge hub |
| `plans/` | Markdown | Feature plans not yet fully reflected in code/docs |

---

## Docker Compose (local dev)

Defined in root `docker-compose.yml`. Project name for Make targets: **`COMPOSE_PROJECT_NAME=coneshare`**.

| Service | Host port | Notes |
|---------|-----------|--------|
| `frontend` | 5173 | Dev server; proxies API to backend |
| `backend` | 8000 | `python manage.py runserver` |
| `core` | 8080 | Go file service |
| `portal` | 3000 | Next dev |
| `redis` | (internal) | Celery broker |
| `celery_worker` | — | Queue `celery`, concurrency from `CELERY_WORKER_CONCURRENCY` (default 4) |
| `video_worker` | — | Queue `video_processing`, default concurrency 1 |
| `celery_beat` | — | Scheduled tasks |
| `mcp_server` | 8001 (configurable) | `MCP_PORT`, `CONESHARE_API_URL` |

Storage mount (core): `~/.coneshare-data` → container `/storage` (`STORAGE_PATH`).

Optional profile: `make up.malware` adds ClamAV for file-request scanning.

---

## Common Make commands

From repo root (see `make help`):

| Target | Action |
|--------|--------|
| `make build` / `make up` / `make down` | Stack lifecycle |
| `make migrate` | Django migrations (**often run by maintainer manually**) |
| `make test` | Backend pytest in container |
| `make test.front` | Frontend **whitelisted** Vitest suite |
| `make test.bdd` | pytest-bdd |
| `make test.core` | Go tests in `core/` |
| `make test.e2e` | (if defined) / `cd e2e && npm test` locally |
| `make logs` | Follow compose logs |
| `make compile.po` | Compile i18n without GNU `msgfmt` (`compile_po.py`) |
| `make api.schema` | Regenerate `backend/docs/api/openapi.yaml` |

Shell helpers: `make back.sh`, `make front.sh`, `make core.sh`, `make mcp.sh`.

---

## Environment

- Copy `.env.template` → `.env` before first run.
- `SITE_DOMAIN` must match how you access the app locally.
- Sensitive values: JWT, `INTERNAL_API_TOKEN` (backend ↔ Go), cloud OAuth, etc. — never commit `.env`.

---

## Production deployment

Self-hosted production stacks live in the separate **[coneshare-compose](https://github.com/coneshare/coneshare-compose)** repository (SSL, nginx, production images). This repo is the application source; `make dist` builds production-oriented images for core, frontend, MCP, and the bundled backend image.

---

## Cross-service communication patterns

1. **Browser → Django:** Most JSON under `/api/v1/…` (JWT or API key in `Authorization`).
2. **Browser → Go:** Short-lived URLs like `/files/download/{token}` returned by Django after internal token generation.
3. **Django → Go:** Authenticated `POST /internal/v1/generate-*-url`, `delete-file`, `copy-file` with `INTERNAL_API_TOKEN`.
4. **Django → Redis/Celery:** Async preview, video transcode, cloud import, automations, trash purge.

Implementation detail for Go routes and security checks: [Core file service notes](./async-processing-and-queues.md#go-core-file-service) and `core/main.go`.
