# LibreGrades Deployment Guide

This guide is for district IT staff deploying LibreGrades on a Linux server.

## Requirements

- Docker and Docker Compose v2
- 2 GB RAM minimum (4 GB recommended)
- Domain name pointed at your server (for HTTPS)
- SMTP relay credentials (Google Workspace, Microsoft 365, or local Exchange)

## Install

1. Copy the entire `libregrades` folder to your server.
2. Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Long random string (50+ chars) |
| `POSTGRES_PASSWORD` | Strong database password |
| `DISTRICT_NAME` | Display name in portal header |
| `SMTP_*` | Your mail relay settings |
| `ALLOWED_HOSTS` | Your domain, e.g. `grades.yourdistrict.org` |

3. Start services:

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

4. Visit your server in a browser and sign in.

## HTTPS with Let's Encrypt

Place a TLS-terminated reverse proxy in front of nginx, or extend nginx with certbot:

```bash
# Example using certbot standalone (stop nginx first)
certbot certonly --standalone -d grades.yourdistrict.org
```

Mount certificates into nginx and add a `listen 443 ssl` server block.

## SMTP examples

**Google Workspace:**

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=libregrades@yourdistrict.org
SMTP_PASSWORD=<app password>
EMAIL_USE_TLS=True
```

**Microsoft 365:**

```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
```

## Backups

Run nightly:

```bash
./scripts/backup.sh
```

Store backups off-server. To restore:

```bash
docker compose exec -T db psql -U libregrades libregrades < backup.sql
```

## Updates

```bash
docker compose pull
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

## Celery worker

The `worker` service handles email alerts and nightly missing-assignment checks. Verify it is running:

```bash
docker compose logs worker
```

## Mobile/desktop apps

Distribute the Windows `.exe` or Android APK to users. Each user enters your server URL on first launch — no app store account required for sideloaded Android APKs.

## Support

Use Django admin (`/admin/`) for user management, school setup, and CSV imports.
