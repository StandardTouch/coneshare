# E-sign large PDF E2E

## Prerequisites

- Docker Compose stack: `make up` (backend, core, frontend, **celery_worker**)
- Playwright browsers: `cd e2e && npm ci && npx playwright install chromium`

## Run

```bash
COMPOSE_PROJECT_NAME=coneshare docker-compose exec -T backend python manage.py prepare_esign_e2e
cd e2e && npx playwright test esign-large-pdf-flow.spec.js --project=esign-e2e
```

Artifacts (screenshots): `artifacts/esign-e2e/placement-last-page-thumbnails.png`, `signing-*.png`

## Checks

- HTTP **206** Range responses on `/api/v1/esign/.../pdf/`; total bytes transferred ≪ full PDF size
- Dual signer OTP flow (OTP read via `get_signer_otp` management command)
- `verify_esign_e2e` pypdf validation (page count, stamped text, audit page)
- 403 for signer PDF without OTP; outsider denied; signed download for owner + signers only
