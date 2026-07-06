# LibreGrades

Free, self-hosted student information system (SIS) for school districts — an open alternative to proprietary grade portals.

## Features

- **Grades & gradebooks** with HTMX inline editing (web) and API for mobile/desktop
- **Missing assignments** with nightly email alerts
- **High school credits** tracking and PDF transcript export
- **Medical information** (allergies, medications, conditions, immunizations)
- **Emergency contacts** with pickup authorization
- **Attendance** (daily and per-section)
- **Behavior incidents** (positive and disciplinary)
- **Parent accounts** with child linking
- **Email alerts** via district SMTP (grades, missing work, attendance, behavior, weekly digest)
- **Profile pictures** — upload your photo; name and avatar appear beside the menu button
- **Server code** — each installation gets a unique 6-digit ID so users can confirm they are on the correct district server

## Clients

| Client | Technology |
|--------|------------|
| Web portal | Django + Bootstrap 5 + HTMX |
| Windows desktop | KivyMD + PyInstaller |
| Android app | KivyMD + Buildozer |
| API | Django REST Framework + JWT |

## Quick start (Docker — recommended for district IT)

```bash
cp .env.example .env
# Edit .env: SECRET_KEY, POSTGRES_PASSWORD, SMTP settings, DISTRICT_NAME

docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_data
```

Open **http://localhost** and sign in. The login page shows your district's **6-digit server code** (also in the page footer and at `/api/v1/server/`).

| Username | Password | Role |
|----------|----------|------|
| admin | demo1234 | District admin |
| teacher1 | demo1234 | Teacher |
| student1 | demo1234 | Student |
| parent1 | demo1234 | Parent |

Django admin: **http://localhost/admin/**

API docs: **http://localhost/api/docs/**

## Local development (without Docker)

When you run `manage.py` on your PC, LibreGrades automatically uses **SQLite** if `.env` points at Docker hostnames (`db`, `redis`).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -e ../shared
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open **http://127.0.0.1:8000/login/** — verify the **Server** badge matches your district. Use **Profile** to set your name and profile picture.

**Background jobs:** start Redis, then Celery.

**Linux / macOS / Docker:**

```bash
celery -A config worker -B -l info
```

**Windows** (two terminals):

```powershell
cd backend
.\scripts\start_celery_worker.ps1
.\scripts\start_celery_beat.ps1
```

## Kivy mobile app

On setup, enter the server URL **and** the 6-digit code shown on the district login page so the app connects to the correct server.

```bash
cd kivy_client
pip install -r requirements.txt
python main.py
```

## Server code

Each LibreGrades installation generates a unique **6-digit server code** on first migrate. It appears on:

- Web login page and footer
- `GET /health/` and `GET /api/v1/server/`
- Kivy app setup (must match before saving)

Optional: set a fixed code in `.env` with `SERVER_CODE=123456` before the first migrate.

## Project structure

```
backend/          Django web + API + Celery
shared/           libregrades_sdk Python API client
kivy_client/      KivyMD mobile/desktop app
docker-compose.yml
nginx/            Reverse proxy config
docs/             Deployment guide
```

## Documentation

- [Deployment guide](docs/DEPLOYMENT.md) — SSL, SMTP, backups, updates
- [Roles & permissions](docs/ROLES.md)

## License

Open source — deploy on your own servers with no license fees.
