> **Note:** This README is a quick-start guide. For a complete developer reference — including all API endpoints, architecture decisions, security configuration, deployment steps, and the full changelog — see [BACKEND_CHANGES.md](BACKEND_CHANGES.md).

# Afrivate Backend

Backend service for Afrivate: a marketplace platform connecting African professionals (Pathfinders) with organizations posting opportunities (Enablers). Built with Django and Django REST Framework.

## Tech Stack

- Python 3.11+
- Django 5.2.7
- Django REST Framework 3.16
- PostgreSQL (via dj-database-url)
- Redis (cache + Celery broker)
- JWT auth (djangorestframework-simplejwt)
- Cloudinary (file storage)
- Resend (auth emails) + SendGrid (waitlist emails)
- Railway (deployment)

## Quick Setup

```bash
# 1. Clone and checkout
git clone https://github.com/AfriVate-Tech/Afrivate-Backend.git
cd Afrivate-Backend
git checkout light

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# or: source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
cd app
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum: SECRET_KEY, DB_URL, RESEND_API_KEY, SENDGRID_API_KEY,
# CLOUDINARY_*, GOOGLE_CLIENT_ID

# 5. Migrate and run
python manage.py migrate
python manage.py runserver
```

See [BACKEND_CHANGES.md — Local Development Setup](BACKEND_CHANGES.md#16-local-development-setup) for full instructions including Redis setup and common error fixes.

## API Documentation

Interactive docs available when the server is running:
- Swagger UI: `http://127.0.0.1:8000/api/v1/docs/`
- ReDoc: `http://127.0.0.1:8000/docs/`

Production docs: `https://afrivate-backend-production.up.railway.app/api/v1/docs/`

## Authentication

All protected endpoints require `Authorization: Bearer <access_token>`.

- Access tokens expire in **1 hour** — refresh with `POST /api/auth/token/refresh/`.
- Registration requires email OTP verification before login is permitted.

## Key Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register/` | POST | Register (Pathfinder or Enabler) |
| `/api/auth/login/` | POST | Login with email/username + password |
| `/api/auth/verify-otp/` | POST | Verify registration OTP |
| `/api/auth/google/pathfinder/` | POST | Google OAuth as Pathfinder |
| `/api/auth/google/enabler/` | POST | Google OAuth as Enabler |
| `/api/opportunities/` | GET | Browse all opportunities |
| `/api/applications/` | POST | Submit an application |
| `/api/notify/notifications/` | GET | Fetch notifications |

For the full endpoint table see [BACKEND_CHANGES.md — All API Endpoints](BACKEND_CHANGES.md#5-all-api-endpoints).

## Project Structure

```
app/
├── Afrivate/        settings, urls, celery
├── Authentication/  register, login, OTP, Google OAuth
├── user_database/   CustomUser model, EmailVerification
├── profiles/        profile CRUD, credentials, social links
├── opportunities/   opportunity CRUD + applicant viewing
├── applications/    application lifecycle
├── bookmark/        three bookmark types
├── notifications/   per-user and broadcast notifications
└── waitlist/        pre-launch email capture
```

## Contributing

1. Create a feature branch from `light` (not `main`).
2. Follow the existing code patterns.
3. Run `python manage.py test` before opening a PR.
4. Target PRs at `light`, not `main`.
