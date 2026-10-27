# Coneshare Knowledge Hub

Central reference for navigating the **coneshare** monorepo: services, Django apps, API surface, frontend SPA, background jobs, and agent/developer workflows.

**Audience:** AI coding agents, new contributors, and maintainers who need a fast mental model before diving into feature-specific docs.

**Last curated:** 2026-10-26 (from repository scan; refresh after major architectural changes).

---

## How to use this hub

| If you need… | Start here |
|--------------|------------|
| What runs where (ports, Docker, Makefile) | [Monorepo & services](./monorepo-and-services.md) |
| Which Django app owns what | [Backend apps reference](./backend-apps-reference.md) |
| API path → app mapping | [API routes reference](./api-routes-reference.md) |
| React routes, viewers, API client | [Frontend reference](./frontend-reference.md) |
| Celery tasks and queues | [Async processing & queues](./async-processing-and-queues.md) |
| Tenancy, folders, links, vaults (conceptual) | [Domain concepts](./domain-concepts.md) |
| Product capabilities (hierarchy) | [Product functionality hierarchy](../product-functionality-hierarchy.md) |
| Tests, migrations policy, “where do I edit?” | [Agent & developer playbook](./agent-development-playbook.md) |

---

## Existing documentation (feature & strategy)

This hub **does not replace** deep-dive feature docs. Use both: hub for orientation, linked docs for behavior and design decisions.

### Data & architecture

- [Coneshare data model](../coneshare-data-model.md) — entities, relations, sensitive fields
- [Technology stack](../strategy/coneshare-techstack.md)
- [Open API strategy](../strategy/coneshare-open-api.md)
- [Backend OpenAPI snapshot](../../backend/docs/api/openapi.yaml) — generate with `make api.schema`
- [Dataroom vault storage refactor](../../backend/docs/dataroom-vault-storage-refactor.md)

### Features (`docs/features/`)

| Topic | Doc |
|-------|-----|
| Auth | [auth-flow.md](../features/auth-flow.md) |
| Upload | [document-upload.md](../features/document-upload.md) |
| Processing pipeline | [document-process.md](../features/document-process.md) |
| Preview & watermark | [document_preview_and_watermarking_deep_dive.md](../features/document_preview_and_watermarking_deep_dive.md) |
| Internal preview | [document-internal-preview.md](../features/document-internal-preview.md) |
| Versions | [document-version.md](../features/document-version.md) |
| Storage | [file-storage.md](../features/file-storage.md) |
| Datarooms | [dataroom-implementation.md](../features/dataroom-implementation.md) |
| Share links (view logic) | [share-link-view-logic.md](../features/share-link-view-logic.md) |
| Share links (view data) | [share-link-record-view-data.md](../features/share-link-record-view-data.md) |
| Password / email gates | [share-link-verify-pwd-email.md](../features/share-link-verify-pwd-email.md) |
| Owner preview | [share-link-owner-preview.md](../features/share-link-owner-preview.md) |
| Q&A on links | [share-link-qna.md](../features/share-link-qna.md) |
| Automations | [automations.md](../features/automations.md) |
| API keys | [api-keys-and-permissions.md](../features/api-keys-and-permissions.md) |
| Cloud import | [cloud-drive-import.md](../features/cloud-drive-import.md) |
| File requests | [file-requests.md](../features/file-requests.md) |
| Virus scan (file requests) | [file-request-virus-scan.md](../features/file-request-virus-scan.md) |
| Remote MCP | [remote-mcp-server.md](../features/remote-mcp-server.md) |

### Strategy (`docs/strategy/`)

See [strategy README](../strategy/README.md) for roadmap, i18n, testing, data ownership, and related guides.

### Plans & workflows

- `plans/` — in-progress design notes (preview refactors, admin datarooms, etc.)
- [Feature delivery workflows](../workflows/) — script vs pure-agent delivery
- `AGENTS.md` (repo root) — agent boundary, memory policy, commit/test conventions
- `.agent/memory.md` — episodic project memory (gotchas, commands); **do not auto-edit without user consent**

### Other packages

| Path | Role |
|------|------|
| `portal/` | Next.js marketing/docs site (port **3000** in dev) |
| `e2e/` | Playwright end-to-end tests |
| `mcp-server/` | FastMCP server for AI integrations (port **8001** default) |

---

## High-level system diagram

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ frontend   │  │  portal    │  │ mcp_server │
    │ Vite/React │  │  Next.js   │  │  FastMCP   │
    │ :5173      │  │  :3000     │  │  :8001     │
    └─────┬──────┘  └────────────┘  └─────┬──────┘
          │ proxy /api/v1                  │ HTTP API
          ▼                                ▼
    ┌─────────────────────────────────────────────┐
    │ backend (Django + DRF) :8000                │
    │  core · documents · sharelinks · datarooms  │
    │  analytics · automations · cloudfiles · …   │
    └───────┬─────────────────────┬───────────────┘
            │ internal HTTP       │ Celery tasks
            ▼                     ▼
    ┌──────────────┐        ┌─────────────┐
    │ core (Go)    │        │ redis       │
    │ file tokens  │        │ + workers   │
    │ :8080        │        │ celery /    │
    └──────┬───────┘        │ video_queue │
           │                └─────────────┘
           ▼
    ┌──────────────┐
    │ STORAGE_PATH │  (~/.coneshare-data in dev compose)
    │ PostgreSQL   │  (production / compose prod stacks)
    └──────────────┘
```

For the official diagram asset, see [architecture PNG](../assets/readme/architecture-v1.3.png) referenced from the root [README](../../README.md).
