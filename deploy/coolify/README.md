# Coneshare Allure Deployment for Coolify

This deployment configuration is for Allure Clinic's Coneshare installation on Coolify v4.

## Prerequisites

### GitHub Container Registry Authentication

The `ghcr.io/standardtouch/coneshare:allure` image is **private**. Before deploying, configure registry authentication in Coolify:

1. Generate a GitHub Classic Personal Access Token with `read:packages` scope
2. In Coolify Server settings, add the registry login:
   - **Registry**: `ghcr.io`
   - **Username**: Your GitHub username
   - **Password**: The generated PAT

## Deployment Overview

- **Application**: Coneshare file sharing platform
- **Domain**: `share.allureclinic.com`
- **Architecture**: All-in-one Docker image with Django + Go file service + React frontend
- **Proxy**: Traefik (managed by Coolify) handles SSL and routing to internal port 80
- **Services**: Web, Celery workers (main + video), Beat scheduler, PostgreSQL 14, Redis, ClamAV

## Coolify Configuration

### Environment Variables

Configure these environment variables in Coolify's Docker Compose resource settings. Variables marked **REQUIRED** must be set; others have sensible defaults.

#### Security & Authentication (REQUIRED)

```bash
# REQUIRED: Django secret key (use Coolify magic var or generate: openssl rand -base64 64)
SECRET_KEY=${SERVICE_BASE64_64_SECRET}

# REQUIRED: Internal API token for backend <-> core service communication
INTERNAL_API_TOKEN=${SERVICE_BASE64_64_INTERNAL_API_TOKEN}

# REQUIRED: PostgreSQL password (use Coolify magic var)
SERVICE_PASSWORD_POSTGRES=${SERVICE_PASSWORD_POSTGRES}
```

#### Core Application Settings

```bash
# Site domain (REQUIRED)
SITE_DOMAIN=https://share.allureclinic.com

# Django debug mode (keep False for production)
DEBUG=False

# Display timezone
DISPLAY_TIME_ZONE=Asia/Riyadh

# Public signup (disabled for Allure Clinic)
ENABLE_PUBLIC_SIGNUP=False

# Storage backend
STORAGE_TYPE=FILESYSTEM
```

#### Database & Redis (Auto-configured)

These use Coolify defaults and the postgres/redis services in the compose file:

```bash
DATABASE_URL=postgresql://postgres:${SERVICE_PASSWORD_POSTGRES}@postgres:5432/coneshare
REDIS_URL=redis://redis:6379
```

#### Trusted Proxies (for Traefik)

Coneshare must trust Traefik to correctly determine client IPs and HTTPS status. The default works for most Coolify setups:

```bash
TRUSTED_PROXIES=127.0.0.1,::1,172.16.0.0/12
```

If your Traefik runs in a custom network, add its CIDR range.

#### Malware Scanning (Enabled)

ClamAV malware scanning is active by default:

```bash
MALWARE_SCAN_ENABLED=true
MALWARE_SCAN_FAIL_MODE=closed  # reject uploads if scanner is unavailable
MALWARE_SCAN_TIMEOUT_MS=10000
```

#### Email Configuration (REQUIRED for production use)

Configure SMTP for password resets and notifications:

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=noreply@allureclinic.com
SERVER_EMAIL=errors@allureclinic.com
ADMINS=Admin:admin@allureclinic.com
```

#### Optional Performance Tuning

```bash
# Gunicorn workers (default: 2)
GUNICORN_WORKERS=2
GUNICORN_THREADS=2

# Celery concurrency (default: 4 for main, 1 for video)
CELERY_WORKER_CONCURRENCY=4
CELERY_VIDEO_WORKER_CONCURRENCY=1

# Document preview features
PDF_PREVIEW_ENGINE=server_pages
ENABLE_OFFICE_PREVIEW=true
ENABLE_VIDEO_PREVIEW=false  # Disabled due to high CPU requirements

# Logging
LOG_LEVEL=INFO
```

#### Error Monitoring

Sentry is disabled for self-hosted deployments. If you have your own Sentry instance, configure:

```bash
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

## Post-Deployment Steps

### 1. Create the First Superuser

After the stack is running, create an admin account:

```bash
docker exec -it coneshare-web gosu coneshare python manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

### 2. Verify Health

Check that all services are healthy:

```bash
docker ps
```

All containers should show `healthy` status.

Access the health endpoint:

```bash
curl https://share.allureclinic.com/api/v1/_health/
```

Should return HTTP 200 with status information.

### 3. Login and Configure

1. Navigate to `https://share.allureclinic.com/`
2. Log in with the superuser account
3. Configure organization settings as needed

## Volumes

The following named volumes persist application data:

- `coneshare-postgres` — PostgreSQL database
- `coneshare-redis` — Redis cache and queue
- `coneshare-data` — Uploaded files and storage
- `coneshare-logs` — Application logs
- `coneshare-media` — User-uploaded media
- `coneshare-clamav` — ClamAV virus definitions

**Important**: Ensure regular backups of `coneshare-postgres` and `coneshare-data`.

## Traefik Configuration

Coolify automatically configures Traefik to:

- Route `share.allureclinic.com` to the `web` service's internal port 80
- Handle SSL/TLS termination (Let's Encrypt)
- Set `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Real-IP` headers

The application's nginx and Django middleware correctly handle these headers to:

- Determine the real client IP address
- Detect HTTPS connections for secure session cookies and CSRF protection

## Upgrading

To upgrade to a new commit:

1. The GitHub Actions workflow automatically builds and pushes new images on push to the `allure` branch
2. In Coolify, restart the Docker Compose resource to pull the latest `:allure` tag
3. Check logs for any migration messages or errors

## Troubleshooting

### Container fails to start

Check logs:

```bash
docker logs coneshare-web
docker logs coneshare-celery
docker logs coneshare-postgres
```

### ClamAV taking too long to start

ClamAV downloads virus definitions on first start, which can take 5-10 minutes. Check:

```bash
docker logs coneshare-clamav
```

Wait for "Daemon started" message before the app will fully function.

### Authentication/CSRF errors

Ensure `SITE_DOMAIN` is set to `https://share.allureclinic.com` (with https) and `TRUSTED_PROXIES` includes Traefik's network.

### Files not uploading

Check that:

1. The `coneshare-data` volume is mounted correctly
2. `MALWARE_SCAN_ENABLED=true` and ClamAV is running and healthy
3. Logs show no timeout errors from ClamAV

## Support

For issues specific to this deployment, contact StandardTouch support.

For general Coneshare documentation, see the main repository: https://github.com/coneshare/coneshare
