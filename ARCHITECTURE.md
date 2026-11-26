# Architecture: Afrivate Backend

Last updated: 26 November 2026

Afrivate connects volunteers (Pathfinders) with organisations (Enablers) that post opportunities.

## Stack

| Part | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | Django 5.2 with Django REST Framework 3.16 |
| Auth | JWT (simplejwt), Google sign-in (django-allauth and dj-rest-auth) |
| Database | PostgreSQL (hosted on Neon). Connected through `DB_URL`. |
| Cache and rate limits | Redis, through `REDIS_URL` |
| Background jobs | Celery is configured (`Afrivate/celery.py`). The worker is in the `Procfile` but not deployed. |
| File storage | Cloudinary (profile pictures, credentials, resumes, organisation documents) |
| Email | Resend (OTP and auth emails), SendGrid (waitlist emails). Gmail SMTP is set as the default Django backend but is not the main sender. |
| Static files | WhiteNoise |
| Web server | Gunicorn (`Procfile`: `web: gunicorn Afrivate.wsgi`) |
| API docs | Swagger at `/api/v1/docs/`, ReDoc at `/docs/` (drf-yasg) |

## Apps

| App | What it does |
|---|---|
| `Afrivate/` | Settings, root URLs, Celery setup |
| `Authentication/` | Register, login, OTP, password reset, Google sign-in, logout |
| `user_database/` | Custom user model (`CustomUser`) and verification records |
| `profiles/` | Pathfinder and Enabler profiles, credentials, social links, profile pictures |
| `opportunities/` | Opportunity posting, browsing, applicant lists |
| `applications/` | Application lifecycle (pending, accepted, rejected) |
| `bookmark/` | Saved opportunities (Pathfinders) and saved Pathfinders (Enablers) |
| `notifications/` | Per-user and broadcast notifications |
| `waitlist/` | Pre-launch email list and statistics |
| `engagements/` | Volunteer hours recorded and confirmed (attested) by organisations |
| `organizations/` | Organisation verification, documents and representatives |
| `adminpanel/` | Admin tools and broadcast emails |

## Request flow

```
Browser (Vercel frontend)
   │  JSON over HTTPS, Authorization: Bearer <access token>
   ▼
Django / DRF (Render web service, Gunicorn)
   │
   ├── PostgreSQL (Neon)        data
   ├── Redis                    rate-limit counters
   ├── Cloudinary               uploaded files
   ├── Resend / SendGrid        emails
   └── Google                   verifies Google sign-in tokens
```

## Authentication flow

1. Register creates an unverified user and emails a 6-digit OTP.
2. Verify OTP returns an access token (1 hour) and a refresh token (6 hours).
3. Login returns the same pair for verified users.
4. Google sign-in verifies the Google ID token, then returns the same pair.
5. Refresh rotates the refresh token. The old one is blacklisted.

## Environment variables

Names only. Values live in the hosting dashboard, never in the repo.

| Group | Variables |
|---|---|
| Core | `SECRET_KEY`, `DEBUG` |
| Database | `DB_URL` |
| URLs | `ALLOWED_HOSTS`, `SITE_DOMAIN`, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS` |
| Email | `DEFAULT_FROM_EMAIL`, `DJANGO_EMAIL_BACKEND`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `RESEND_API_KEY`, `SENDGRID_API_KEY` |
| Cloudinary | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Cache | `REDIS_URL` |
| Uploads | `MAX_ORG_DOCUMENT_MB` (optional, default 10) |

The `.env` file for local development goes in the **backend root** (next to `.env.example`). `settings.py` loads it from there.

## Hosting and environments

- **Live API:** Render web service. The team's live URL is `https://afrivate-backend-0z4m.onrender.com`.
- **Database:** Neon (PostgreSQL).
- **Frontend:** Vercel. Dev preview: `https://afrivate-volunteer-dev-branch.vercel.app`.
- **Branches:** `main` (the current local checkout), `dev` (on the remote). `git_workflow.md` says to merge into `dev`.

## Known differences between docs and code

These files disagree with each other. Confirm the right answer and update the docs.

| Topic | Older docs say | Code and live setup say | Action |
|---|---|---|---|
| Hosting | Railway (`README.md`, `Project_Flow.md`) | Render (live), and Railway URL still in CORS | Confirm Render is final. Remove the Railway origin if unused. |
| Refresh token life | 1 day (`Project_Flow.md`) | 6 hours (`settings.py`) | Update the docs to match the code. |
| Email | Gmail SMTP (`Project_Flow.md`) | Resend and SendGrid | Update the docs. |
| Target branch | `light` (`README.md`) | `dev` (`git_workflow.md`) | Choose one branch and update all docs. |
| `.env` location | Inside `app/` (`README.md`) | Backend root (`settings.py`) | Update the README. |
| Default API URL | Railway (frontend docs) | Render (`settings.py`) | Update the docs. |

## Where to look next

- `Project_Flow.md`: full API reference (note: some details are out of date, see above)
- `BACKEND_CHANGES.md`: change log and setup
- `git_workflow.md`: branches and pull requests
- `SECURITY.md`: security rules
- `CODE_STYLE.md`: coding rules
