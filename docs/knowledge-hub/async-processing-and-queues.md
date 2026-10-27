# Async processing & queues

Background work uses **Celery** with **Redis** as broker. Workers run in Docker services `celery_worker` and `video_worker`.

Restart workers after task code changes: `make reload.celery`.

---

## Queues

| Worker service | Queue | Concurrency env | Typical work |
|----------------|-------|-----------------|--------------|
| `celery_worker` | `celery` | `CELERY_WORKER_CONCURRENCY` (default 4) | PDF rasterization, office conversion, HEIC, spreadsheets, cloud import, automations, trash |
| `video_worker` | `video_processing` | `CELERY_VIDEO_WORKER_CONCURRENCY` (default 1) | FFmpeg HLS transcoding (`generate_video_stream_task`) |

`celery_beat` schedules periodic jobs (e.g. trash purge).

**Feature flag:** `ENABLE_VIDEO_PREVIEW=false` disables video preview paths; `video_worker` may idle but still runs.

**Lazy preview:** Heavy processing is often deferred until first preview request; see `enqueue_server_preview_render` and related services in `documents/`.

---

## `documents/tasks.py` (primary)

| Task | Purpose |
|------|---------|
| `convert_office_to_pdf_task` | LibreOffice pipeline for office formats |
| `generate_pdf_pages_task` | Poppler PNG pages, link annotation harvest → `DocumentPage` |
| `generate_video_stream_task` | Chunked FFmpeg → HLS segments uploaded via streams |
| `transcode_heic_image_task` | HEIC → previewable raster |
| `generate_spreadsheet_preview_task` | Spreadsheet render pipeline |
| `purge_expired_trash_documents_task` | Hard-delete expired trash |

Video task uses **stream processing** (8KB download buffers, per-segment upload) to limit RAM.

PDF/watermark OOM notes: enforce page limits for flattened raster downloads; close PIL images in `finally` blocks.

---

## Other apps

| Module | Tasks |
|--------|-------|
| `cloudfiles/tasks.py` | Cloud import / sync jobs |
| `sharelinks/tasks.py` | Link-related async delivery |
| `automations/tasks.py` | Rule evaluation, email/webhook delivery |
| `filerequests/tasks.py` | Reminders / scan follow-ups |
| `core/tasks.py` | Core maintenance |

---

## Go core file service

Source: `core/main.go`

**Internal (Bearer/shared token):**

- Generate single-use upload/download/preview URLs stored in **in-memory** map (note: multi-instance deployments need shared token store — see TODO in source).

**Public:**

- `PUT /files/upload/{token}` — single use
- `GET /files/download/{token}` — attachment
- `GET /files/preview/{token}` and `…/*` — inline / HLS segment proxy

**Security:**

- Path traversal: resolve abs paths; for wildcard preview routes, prefix-check against token’s authorized directory, not global storage root only.

Django integration: `documents/fileserver.py`.

---

## Preview engines & settings

Dynamic settings (database / admin) drive behavior, including:

- `PDF_PREVIEW_ENGINE` (`pdfjs` vs server-rendered)
- Watermark modes (viewer overlay vs flattened download)
- `MAX_PREVIEW_PAGES`, video size limits, `MAX_VIDEO_PREVIEW_SIZE_MB`

Document **`download_only`** is evaluated at **read time** via model property `is_download_only`, not a stale DB flag.

Deep dive: [document_preview_and_watermarking_deep_dive](../features/document_preview_and_watermarking_deep_dive.md).
