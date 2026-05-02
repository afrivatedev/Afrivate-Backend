# BACKEND_CHANGES.md — Afrivate Backend (light branch)

> **Audience:** Developers who need to understand, run, contribute to, or deploy this backend.
> **Branch:** `light` — pre-merge candidate for `main`.
> **Last updated:** 2026-04-28

---

## Table of Contents

1. [Overview](#1-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Django Apps — Detailed Breakdown](#4-django-apps--detailed-breakdown)
5. [All API Endpoints](#5-all-api-endpoints)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Database Models](#7-database-models)
8. [Notification System](#8-notification-system)
9. [Bookmark System](#9-bookmark-system)
10. [Custom Questions Pattern](#10-custom-questions-pattern)
11. [File Uploads](#11-file-uploads)
12. [Email System](#12-email-system)
13. [Task Queue (Celery + Redis)](#13-task-queue-celery--redis)
14. [Security](#14-security)
15. [Environment Variables](#15-environment-variables)
16. [Local Development Setup](#16-local-development-setup)
17. [Deployment (Railway)](#17-deployment-railway)
18. [Running Migrations](#18-running-migrations)
19. [Testing](#19-testing)
20. [Known Issues & Limitations](#20-known-issues--limitations)
21. [Merge Instructions](#21-merge-instructions)
22. [Changelog](#22-changelog)

---

## 1. Overview

### What is this branch?

`light` is a hardened, integration-ready fork of `main`. It exists because `main` accumulated a set of critical bugs, security vulnerabilities, and dead code during rapid feature development. Rather than landing many fragile fixes directly to `main`, all changes were staged here for review.

### What it fixes

| Category | Summary |
|---|---|
| Critical bugs | Infinite-loop risk in `user_database/signals.py`; `ssl_require` hardcoded to `False` in production DB config; unverified users locked out of password reset |
| Security | Rate limiting on all 6 auth endpoints; URL validation on social links; reduced password reset timeout from 24h to 1h; debug-leaking `print()` calls replaced with proper logging |
| New features | Per-user targeted notifications (application submitted / accepted / rejected); expose `pathfinder_user_id` and `enabler_user_id` in bookmark list responses; preserve original document filename on credential upload; CORS origins configurable via env var; `BookmarkEnabler` model (pathfinders can bookmark enabler organizations) |
| Dead code removed | Entire empty `newsletter` app deleted; commented AWS S3 config block; commented SMTP block; unused URL patterns |
| Documentation | `.env.example` added; `Project_Flow.md` written; this file |

### Why it exists separately from main

`main` is the live production branch. `light` is the holding pen for all validated fixes that need to migrate to production together, since several of them are interdependent (e.g. the notification recipient FK requires a migration before the application views can send personal notifications).

---

## 2. Tech Stack

Dependencies are in [`app/requirements.txt`](app/requirements.txt).

### Core Framework

| Package | Version | Purpose |
|---|---|---|
| Django | 5.2.7 | Web framework |
| djangorestframework | 3.16.1 | REST API layer |
| gunicorn | 23.0.0 | WSGI server for production |
| whitenoise | 6.11.0 | Serve static files without a separate CDN |

### Authentication

| Package | Version | Purpose |
|---|---|---|
| djangorestframework-simplejwt | 5.5.1 | JWT access + refresh token generation, rotation, blacklisting |
| django-allauth | 65.14.3 | Social login infrastructure (used by Google OAuth flow) |
| dj-rest-auth | 7.1.1 | REST endpoints for allauth (registration, login) |
| google-auth | 2.49.1 | Verifies Google ID tokens server-side |
| PyJWT | 2.10.1 | Low-level JWT encoding/decoding (used internally by simplejwt) |

### Database

| Package | Version | Purpose |
|---|---|---|
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| dj-database-url | 3.1.0 | Parse `DATABASE_URL` connection string |
| django-redis | 6.0.0 | Redis cache backend for Django |
| redis | 7.4.0 | Redis client |

### Storage

| Package | Version | Purpose |
|---|---|---|
| cloudinary | 1.44.1 | Cloudinary SDK for signed URL generation |
| django-cloudinary-storage | 0.3.0 | Django storage backend wired to Cloudinary |
| django-storages | 1.14.6 | Generic storage backend framework (also supports S3) |
| pillow | 11.3.0 | Server-side image validation (format and size check) |
| boto3 / botocore | 1.42.23 | AWS SDK (present in requirements, S3 storage disabled in favour of Cloudinary) |

### Email

| Package | Version | Purpose |
|---|---|---|
| resend | 2.27.0 | Resend API — transactional OTP and auth emails |
| sendgrid | 6.12.5 | SendGrid SDK — waitlist welcome emails |
| django-sendgrid-v5 | 1.3.0 | Django email backend wrapper for SendGrid |

### Task Queue

| Package | Version | Purpose |
|---|---|---|
| celery | 5.6.3 | Distributed task queue |
| django-celery-results | 2.6.0 | Store Celery task results in the Django DB |

### API

| Package | Version | Purpose |
|---|---|---|
| drf-yasg | 1.21.11 | Auto-generates Swagger/ReDoc API docs from DRF views |
| django-filter | 25.2 | Filter querysets by URL query params |
| django-cors-headers | 4.9.0 | CORS middleware |

### Utilities

| Package | Version | Purpose |
|---|---|---|
| python-dotenv | 1.1.1 | Load `.env` file into `os.environ` |
| email-validator | 2.3.0 | Deep email validation (format, DNS, deliverability) — used by waitlist |
| pyotp | 2.9.0 | TOTP library (imported but OTP generation uses `random.randint` instead) |
| dnspython | 2.8.0 | DNS lookups (dependency of email-validator) |
| python-dateutil | 2.9.0 | Date utilities |
| cryptography | 46.0.3 | Cryptographic primitives (dependency) |

---

## 3. Project Structure

```
Afrivate-Backend/                   ← repo root
├── .env.example                    ← template for all required env vars
├── .gitignore
├── Procfile                        ← Railway/Heroku process declarations
├── README.md                       ← Quick-start (outdated; see this file)
├── Project_Flow.md                 ← User-facing flow and API reference for frontend devs
├── BACKEND_CHANGES.md              ← THIS FILE — developer reference
│
└── app/                            ← Django project root (manage.py lives here)
    ├── manage.py
    ├── requirements.txt            ← pinned production dependencies
    ├── requirements.dev.txt        ← pinned dev/CI snapshot
    ├── ROUTES_API_REQUIREMENTS.MD  ← legacy frontend route ↔ API mapping (partially outdated)
    │
    ├── Afrivate/                   ← Django project package (settings, root urls, wsgi, celery)
    │   ├── settings.py             ← single settings file; env-var driven
    │   ├── urls.py                 ← root URL dispatcher
    │   ├── celery.py               ← Celery app instance
    │   ├── asgi.py
    │   └── wsgi.py
    │
    ├── Authentication/             ← Registration, login, OTP, Google OAuth, password management
    │   ├── views.py
    │   ├── urls.py
    │   ├── utils.py                ← Celery tasks: send_signup_otp_email, sendotp_via_email, send_welcome_email
    │   ├── adapter.py              ← Custom allauth social account adapter (sets role on social signup)
    │   ├── backends.py             ← Custom auth backend (email-or-username login)
    │   ├── management/commands/
    │   │   └── clear_expired_token.py  ← Management command to purge expired EmailVerification rows
    │   └── test.py
    │
    ├── user_database/              ← Custom user model and EmailVerification
    │   ├── models.py               ← CustomUser (AbstractUser), EmailVerification
    │   ├── serializers.py          ← Registration, login, OTP, Google auth serializers
    │   ├── permissions.py          ← IsVerifiedUser, IsEnablerUser, IsPathfinderUser
    │   ├── signals.py              ← Intentionally empty — profile creation is in profiles/signals.py
    │   ├── apps.py
    │   └── admin.py
    │
    ├── profiles/                   ← Profile models and CRUD views for both user types
    │   ├── models.py               ← Profile, EnablerProfileExtra, PathfinderProfileExtra,
    │   │                             SocialLink, Credential, PathfinderSkill,
    │   │                             PathfinderEducation, PathfinderCertification
    │   ├── serializers.py          ← EnablerProfileSerializer, PathfinderProfileSerializer,
    │   │                             ProfilePictureSerializer, CredentialSerializer,
    │   │                             ApplicantProfileSerializer, OrganizationProfileSerializer
    │   ├── views.py                ← Profile, credential, social link views
    │   ├── urls.py
    │   ├── signals.py              ← Creates Profile + role-specific extras on user creation
    │   └── utils.py                ← custom_exception_handler (DRF exception hook)
    │
    ├── opportunities/              ← Opportunity CRUD + applicant viewing
    │   ├── models.py               ← Opportunity
    │   ├── serializers.py          ← OpportunitySerializer
    │   ├── views.py                ← List/create, detail, enabler's opportunities, applicant views
    │   ├── urls.py
    │   └── permissions.py          ← IsOwnerOrReadOnly, IsEnablerOrReadOnly, IsPathfinder, IsOpportunityOwner
    │
    ├── applications/               ← Application submit/withdraw/status-change
    │   ├── models.py               ← Application
    │   ├── serializers.py          ← ApplicationSerializer, ApplicationListSerializer
    │   ├── views.py                ← ApplicationViewSet with change_status action
    │   └── urls.py
    │
    ├── bookmark/                   ← Three bookmark types (opportunity, pathfinder, enabler)
    │   ├── models.py               ← Bookmark, BookmarkUser, BookmarkEnabler
    │   ├── serializers.py          ← BookmarkSerializer, BookmarkUserSerializer, BookmarkEnablerSerializer
    │   ├── views.py                ← Six views: list/create + delete for each bookmark type
    │   ├── urls.py
    │   └── permissions.py          ← IsEnablerUser, IsPathfinderUser
    │
    ├── notifications/              ← Notification read/mark-read
    │   ├── models.py               ← Notification (recipient FK, read_by M2M)
    │   ├── serializers.py          ← NotificationSerializer (current_user_read annotation)
    │   ├── views.py                ← NotificationViewSet with mark_read, mark_all_read actions
    │   └── urls.py
    │
    └── waitlist/                   ← Pre-launch email signup
        ├── models.py               ← WaitlistEmail
        ├── serializers.py          ← WaitlistEmailSerializer (strict email validation), WaitlistStatsSerializer
        ├── views.py                ← WaitlistEmailView, WaitlistStatsView
        ├── urls.py
        └── utils.py                ← SendGrid send_welcome_email, email domain validation helpers
```

---

## 4. Django Apps — Detailed Breakdown

### 4.1 Authentication

**Purpose:** Everything related to identity — creating accounts, proving you are who you say you are, and managing credentials.

**Models:** None (uses `user_database.CustomUser` and `user_database.EmailVerification`).

**Key views:**

| View | Method | What it does |
|---|---|---|
| `RegisterView` | POST | Creates user, generates OTP, sends signup email via Resend |
| `LoginView` | POST | Authenticates via custom backend, returns JWT tokens |
| `OtpVerifyView` | POST | Verifies 6-digit OTP, marks user as verified, returns tokens |
| `ResendOtpView` | POST | Issues a new OTP (max 3 resends per 30-min cooldown) |
| `ForgotPasswordView` | POST | Sends password-reset OTP (always returns 200 — doesn't reveal existence) |
| `VerifyPasswordResetOtpView` | POST | Validates reset OTP, returns user `pk` for next step |
| `ResetPasswordView` | POST | Sets new password; also marks account verified (unverified-user fix) |
| `ChangePasswordView` | POST | Authenticated users change their own password |
| `LogoutView` | POST | Blacklists refresh token |
| `GoogleLoginView` | POST | Verifies Google ID token, creates or logs in user with specified role |
| `SetPasswordView` | POST | Google users set an email/password for their account |
| `DeleteUserView` | DELETE | Permanently deletes the authenticated user's account |

**Throttle scopes (ScopedRateThrottle):**

| Scope | Rate | Applied to |
|---|---|---|
| `auth_register` | 5/hour | RegisterView |
| `auth_login` | 10/hour | LoginView |
| `auth_otp_verify` | 10/hour | OtpVerifyView |
| `auth_resend_otp` | 5/hour | ResendOtpView |
| `auth_forgot_password` | 5/hour | ForgotPasswordView |
| `auth_password_reset` | 10/hour | ResetPasswordView |

**Signals:** None in this app.

---

### 4.2 user_database

**Purpose:** Owns the custom user model and the reusable email-verification model. All other apps import their auth primitives from here.

**Models:**
- `CustomUser` — extends `AbstractUser`; adds `role`, `is_email_verified`, `auth_provider`; `USERNAME_FIELD = 'email'`; `tokens()` method mints JWT pair with custom claims.
- `EmailVerification` — dual-purpose model storing either a UUID token (for link-based verify) or a 6-digit OTP string. Used for user signup, password reset, and formerly waitlist.

**Key serializers:**
- `CustomUserRegistrationSerializer` — validates password strength and confirms match.
- `CustomUserLoginSerializer` — handles email-or-username lookup, detects Google-only accounts.
- `GoogleAuthSerializer` — verifies Google ID token against GOOGLE_CLIENT_ID.
- `CustomTokenObtainPairSerializer` — injects `role` and `email` into JWT payload.

**Permissions defined here (`user_database/permissions.py`):**
- `IsVerifiedUser` — blocks unverified users from all protected endpoints.
- `IsEnablerUser` — role check for enabler-only actions.

**`signals.py`:** Intentionally a comment-only file. Profile creation is handled entirely by `profiles/signals.py`. Do not add a second `post_save` handler here — it caused an infinite loop in an earlier version.

---

### 4.3 profiles

**Purpose:** User profile data — what the user presents to the world. Split into a shared `Profile` base and two role-specific extension models.

**Models:** Profile, EnablerProfileExtra, PathfinderProfileExtra, SocialLink, Credential, PathfinderSkill, PathfinderEducation, PathfinderCertification.

**Key views:**
- `PathfinderProfileAPIView` / `EnablerProfileAPIView` — GET own profile, PATCH own profile. `get_object()` uses `get_or_create` so the first GET always succeeds.
- `ProfilePictureAPIView` — accepts `multipart/form-data`, validates via Pillow, stores to Cloudinary.
- `CredentialViewSet` — full CRUD on documents; `perform_create` attaches to `request.user.profile`.
- `SocialLinkViewSet` — full CRUD; scoped to `request.user.profile`.
- `PublicPathfinderProfileView` / `PublicEnablerProfileView` — view another user's profile by their Django user ID.

**Signals (`profiles/signals.py`):**
`sync_user_profile_and_role` fires on `post_save` of `CustomUser`. On creation it:
1. Assigns `pathfinder` role if somehow missing (Google/Social fallback).
2. Creates `Profile` with contact_email, address, state, country defaults.
3. Creates `EnablerProfileExtra` (name = username) or `PathfinderProfileExtra` (first/last name from user) depending on role.

This is the single source of truth for profile initialisation. Nothing in `user_database/signals.py`.

---

### 4.4 opportunities

**Purpose:** Enables posting, browsing, filtering, and managing volunteer/job/internship/scholarship/grant opportunities.

**Models:** `Opportunity` — title, type (5 choices), description, link (HTTPS only), is_open, created_by (FK → CustomUser).

**Key views:**
- `OpportunityView` — `GET` (public, paginated, filterable) + `POST` (enabler only).
- `OpportunityDetailView` — `GET` (public) + `PUT/PATCH/DELETE` (owner-only, IsVerifiedUser).
  - `destroy()` soft-closes instead of deleting if applicants exist.
- `EnablerOpportunityListView` — `GET /mine/` shows only the logged-in enabler's postings.
- `OpportunityApplicantListView` — `GET /<id>/applicants/` for the opportunity owner.
- `ApplicantProfileView` — `GET /<id>/applicants/<applicant_id>/` returns full PathfinderProfileExtra.

**Permissions (`opportunities/permissions.py`):**
- `IsOwnerOrReadOnly` — write only if `obj.created_by == request.user`.
- `IsEnablerOrReadOnly` — write only if `user.role == 'enabler'`.
- `IsOpportunityOwner` — `has_permission` checks the opportunity's `created_by` at the view level.

---

### 4.5 applications

**Purpose:** Manages the lifecycle of a job/volunteer application from submission through review.

**Models:** `Application` — user (FK), opportunity (FK), cover_letter, status (pending/accepted/rejected), resume (Cloudinary file), profile_resume (FK → Credential), applied_at, reviewed_at. `unique_together = ('user', 'opportunity')`.

**Key views:**
- `ApplicationViewSet` — standard ModelViewSet plus `change_status` custom action.
  - `get_queryset()`: enablers see applications for their opportunities; pathfinders see their own.
  - `perform_create()`: prevents duplicates, creates a personal notification to the enabler.
  - `change_status()`: PATCH only; sets status, updates `reviewed_at`, creates a personal notification to the pathfinder.
  - `perform_destroy()`: only `pending` applications can be withdrawn.

---

### 4.6 bookmark

**Purpose:** Three independent bookmark systems — pathfinders save opportunities, enablers save pathfinders, pathfinders save enablers.

**Models:**
- `Bookmark` — user (FK CustomUser) + opportunity (FK Opportunity). Unique together.
- `BookmarkUser` — enabler (FK CustomUser) + pathfinder (FK PathfinderProfileExtra). Unique together.
- `BookmarkEnabler` — pathfinder (FK CustomUser) + enabler (FK EnablerProfileExtra). Unique together.

See [Section 9](#9-bookmark-system) for detailed design notes.

---

### 4.7 notifications

**Purpose:** Delivers targeted per-user notifications (application events) and broadcast system notifications.

**Models:** `Notification` — recipient (FK CustomUser, nullable = broadcast), title, message, priority, type, link, read_by (M2M → CustomUser).

See [Section 8](#8-notification-system) for detailed design notes.

---

### 4.8 waitlist

**Purpose:** Pre-launch email capture with strict validation.

**Models:** `WaitlistEmail` — email (unique), name, referral_source, is_verified.

**Key views:**
- `WaitlistEmailView` — POST; validates email using `email-validator` library (checks format, DNS, deliverability), rejects disposable/suspicious domains, calls SendGrid to send welcome email.
- `WaitlistStatsView` — GET; returns aggregate counts (total, verified, today, this week, this month).

---

## 5. All API Endpoints

> **Base URL (production):** `https://afrivate-backend-production.up.railway.app`  
> **Base URL (local):** `http://127.0.0.1:8000`  
> **Auth header:** `Authorization: Bearer <access_token>`  
> **Format:** JSON unless uploading files (then `multipart/form-data`).

### 5.1 Authentication — `/api/auth/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| POST | `/api/auth/register/` | `RegisterView` | No | `{username, email, password, password2, role}` | `{message, user{username,email,role}}` | Sends OTP email; throttled 5/hr |
| POST | `/api/auth/login/` | `LoginView` | No | `{username_or_email, password}` | `{message, user{...}, access, refresh}` | Accepts email or username; throttled 10/hr |
| POST | `/api/auth/verify-otp/` | `OtpVerifyView` | No | `{email, otp}` | `{success, message, user{...}, access, refresh}` | OTP valid 10 min; throttled 10/hr |
| POST | `/api/auth/resend-otp/` | `ResendOtpView` | No | `{email}` | `{message}` | Max 3 resends, 30-min cooldown; throttled 5/hr |
| POST | `/api/auth/forgot-password/` | `ForgotPasswordView` | No | `{email}` | `{success, message}` | Always 200; doesn't reveal account existence; throttled 5/hr |
| POST | `/api/auth/verify-password-reset-otp/` | `VerifyPasswordResetOtpView` | No | `{email, otp}` | `{success, message, uid}` | Returns user PK for next step |
| POST | `/api/auth/reset-password/` | `ResetPasswordView` | No | `{uid, new_password, confirm_password}` | `{message}` | Also marks account verified; throttled 10/hr |
| POST | `/api/auth/change-password/` | `ChangePasswordView` | Yes | `{old_password, new_password, confirm_password}` | `{message}` | |
| POST | `/api/auth/logout/` | `LogoutView` | Yes | `{refresh}` | `{message}` | Blacklists refresh token |
| POST | `/api/auth/google/pathfinder/` | `GoogleLoginView` | No | `{token}` (Google ID token) | `{message, user{...}, access, refresh}` | Creates user with role=pathfinder if new |
| POST | `/api/auth/google/enabler/` | `GoogleLoginView` | No | `{token}` (Google ID token) | `{message, user{...}, access, refresh}` | Creates user with role=enabler if new |
| POST | `/api/auth/set-password/` | `SetPasswordView` | Yes | `{new_password, confirm_password}` | `{message}` | Google users only |
| DELETE | `/api/auth/delete-account/` | `DeleteUserView` | Yes | — | `{message}` | Permanent deletion |
| POST | `/api/auth/token/refresh/` | `TokenRefreshView` | No | `{refresh}` | `{access, refresh}` | Rotates both tokens |

### 5.2 Profile — `/api/profile/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| GET | `/api/profile/pathfinderprofile/` | `PathfinderProfileAPIView` | Yes (Pathfinder) | — | Full PathfinderProfileExtra + nested profile, social links, credentials | |
| PATCH | `/api/profile/pathfinderprofile/` | `PathfinderProfileAPIView` | Yes (Pathfinder) | Any subset of profile fields | Updated profile | Partial update |
| GET | `/api/profile/enablerprofile/` | `EnablerProfileAPIView` | Yes (Enabler) | — | EnablerProfileExtra + nested profile, social links | |
| PATCH | `/api/profile/enablerprofile/` | `EnablerProfileAPIView` | Yes (Enabler) | Any subset | Updated profile | Partial update |
| GET | `/api/profile/profile/picture/` | `ProfilePictureAPIView` | Yes | — | `{id, profile_pic}` | |
| PATCH | `/api/profile/profile/picture/` | `ProfilePictureAPIView` | Yes | `profile_pic` (file) | `{id, profile_pic}` | Multipart; max 5MB; JPEG/JPG/PNG/WEBP |
| GET | `/api/profile/pathfinderprofile/user/<user_id>/` | `PublicPathfinderProfileView` | Yes | — | Full public profile | Any authenticated user can view |
| GET | `/api/profile/enablerprofile/user/<user_id>/` | `PublicEnablerProfileView` | Yes | — | Full public profile | |
| GET | `/api/profile/view-profile/<user_id>/` | `PublicPathfinderProfileView` | Yes | — | Same as above | Legacy URL alias |
| GET | `/api/profile/credentials/` | `CredentialViewSet` | Yes | — | List of credentials | |
| POST | `/api/profile/credentials/` | `CredentialViewSet` | Yes | `{document, document_name?}` | Created credential | Multipart; `document_name` auto-filled from filename if omitted |
| GET | `/api/profile/credentials/<id>/` | `CredentialViewSet` | Yes | — | Single credential with signed URL | |
| PATCH | `/api/profile/credentials/<id>/` | `CredentialViewSet` | Yes | Any subset | Updated credential | |
| DELETE | `/api/profile/credentials/<id>/` | `CredentialViewSet` | Yes | — | 204 | |
| GET | `/api/profile/social-links/` | `SocialLinkViewSet` | Yes | — | List of social links | |
| POST | `/api/profile/social-links/` | `SocialLinkViewSet` | Yes | `{platform_name, platform_url}` | Created link | URL must be http or https |
| DELETE | `/api/profile/social-links/<id>/` | `SocialLinkViewSet` | Yes | — | 204 | |

### 5.3 Opportunities — `/api/opportunities/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| GET | `/api/opportunities/` | `OpportunityView` | No | — | Paginated list | Filter: `opportunity_type`, `is_open`; Search: `title`, `description` |
| POST | `/api/opportunities/` | `OpportunityView` | Yes (Enabler) | `{title, opportunity_type, description, link}` | Created opportunity | `link` must start with `https://`; type: job/internship/volunteering/scholarship/grant |
| GET | `/api/opportunities/<id>/` | `OpportunityDetailView` | No | — | Single opportunity | |
| PUT | `/api/opportunities/<id>/` | `OpportunityDetailView` | Yes (Owner, Enabler) | Full fields | Updated opportunity | 12-hour edit window enforced in serializer |
| PATCH | `/api/opportunities/<id>/` | `OpportunityDetailView` | Yes (Owner, Enabler) | Partial fields | Updated opportunity | 12-hour window applies |
| DELETE | `/api/opportunities/<id>/` | `OpportunityDetailView` | Yes (Owner) | — | 200 or 204 | Soft-closes if applicants exist |
| GET | `/api/opportunities/mine/` | `EnablerOpportunityListView` | Yes | — | Enabler's own opportunities | |
| GET | `/api/opportunities/<id>/applicants/` | `OpportunityApplicantListView` | Yes (Owner) | — | List of ApplicationListSerializer | Opportunity creator only |
| GET | `/api/opportunities/<id>/applicants/<applicant_id>/` | `ApplicantProfileView` | Yes (Owner) | — | Full PathfinderProfileExtra | `applicant_id` = Django user ID |

### 5.4 Applications — `/api/applications/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| GET | `/api/applications/` | `ApplicationViewSet` | Yes | — | Pathfinder: own apps; Enabler: apps for their opportunities | |
| POST | `/api/applications/` | `ApplicationViewSet` | Yes (Pathfinder) | `{opportunity, cover_letter?, resume?, profile_resume?}` | Created application | One per opportunity; triggers notification to enabler |
| GET | `/api/applications/<id>/` | `ApplicationViewSet` | Yes | — | Single application | |
| DELETE | `/api/applications/<id>/` | `ApplicationViewSet` | Yes (Owner) | — | 204 | Only if status = pending |
| PATCH | `/api/applications/<id>/change_status/` | `ApplicationViewSet.change_status` | Yes (Enabler) | `{status: accepted|rejected}` | `{message}` | Triggers notification to pathfinder |

### 5.5 Bookmarks — `/api/bookmark/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| GET | `/api/bookmark/opportunities/saved/` | `BookmarkListCreateView` | Yes (Pathfinder) | — | Paginated list with nested opportunity | |
| POST | `/api/bookmark/opportunities/saved/` | `BookmarkListCreateView` | Yes (Pathfinder) | `{opportunity_id}` | Created bookmark | |
| DELETE | `/api/bookmark/opportunities/saved/<opportunity_id>/` | `BookmarkDeleteView` | Yes (Pathfinder) | — | 204 | |
| GET | `/api/bookmark/applicants/saved/` | `PathfinderBookmarkView` | Yes (Enabler) | — | Paginated list with pathfinder details | Includes `pathfinder_user_id` for DELETE routing |
| POST | `/api/bookmark/applicants/saved/` | `PathfinderBookmarkView` | Yes (Enabler) | `{pathfinder_id}` (Django user ID) | Created bookmark | |
| DELETE | `/api/bookmark/applicants/saved/<pathfinder_id>/` | `PathfinderBookmarkDeleteView` | Yes (Enabler) | — | 204 | `pathfinder_id` = Django user ID |
| GET | `/api/bookmark/enablers/saved/` | `EnablerBookmarkView` | Yes (Pathfinder) | — | Paginated list with enabler details | |
| POST | `/api/bookmark/enablers/saved/` | `EnablerBookmarkView` | Yes (Pathfinder) | `{enabler_id}` (Django user ID) | Created bookmark | |
| DELETE | `/api/bookmark/enablers/saved/<enabler_id>/` | `EnablerBookmarkDeleteView` | Yes (Pathfinder) | — | 204 | |

### 5.6 Notifications — `/api/notify/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| GET | `/api/notify/notifications/` | `NotificationViewSet` | Yes | — | List of notifications | Filtered to recipient=user OR broadcast (recipient=null); annotated with `current_user_read` |
| POST | `/api/notify/notifications/<id>/mark-read/` | `NotificationViewSet.mark_read` | Yes | — | `{message}` | Adds user to `read_by` M2M |
| POST | `/api/notify/notifications/mark-all-read/` | `NotificationViewSet.mark_all_read` | Yes | — | `{message, count}` | Marks all unread notifications for this user |
| POST | `/api/notify/notifications/` | `NotificationViewSet` | Yes (Admin) | `{title, message, priority, type, link, recipient?}` | Created notification | Admin-only |

### 5.7 Waitlist — `/api/waitlist/`

| Method | URL | View | Auth Required | Request Body | Response | Notes |
|---|---|---|---|---|---|---|
| POST | `/api/waitlist/` | `WaitlistEmailView` | No | `{email, name?}` | `{success, message, email}` | Strict validation; sends SendGrid welcome email |
| GET | `/api/waitlist/stats/` | `WaitlistStatsView` | No (should be admin) | — | `{success, data{total_signups, verified_signups, signups_today, ...}}` | Currently open — no auth guard |

---

## 6. Authentication & Authorization

### Registration → OTP → Login flow

```
User                     Backend                       Email (Resend)
 │                          │                               │
 │── POST /register ────────►                               │
 │                          │  create CustomUser (unverified)
 │                          │  create EmailVerification (otp, 10 min)
 │                          │── send_signup_otp_email ─────►│
 │◄── 201 {user, message} ──│                               │
 │                          │                               │
 │── POST /verify-otp ──────►                               │
 │   {email, otp}           │  validate OTP against EmailVerification
 │                          │  mark_verified(); user.is_email_verified=True
 │                          │  generate JWT pair (with role claim)
 │◄── 200 {access, refresh, user} ─┤
 │                          │
 │── POST /login ───────────►
 │   {username_or_email,    │  authenticate via CustomAuthenticationBackend
 │    password}             │  check is_email_verified
 │◄── 200 {access, refresh, user}
```

### Google OAuth flow

```
User                     Frontend                  Backend
 │                          │                          │
 │── click Google Sign In ──►                          │
 │                          │── Google popup ──►       │
 │                          │◄── Google ID token ──────│
 │                          │── POST /google/{role}/ ──►
 │                          │   {token: <id_token>}    │  verify with google-auth SDK
 │                          │                          │  lookup or create user
 │                          │                          │  user.is_email_verified=True
 │                          │◄── 200 {access, refresh, user}
```

- Role is fixed at the URL level (`/google/pathfinder/` vs `/google/enabler/`).
- Existing users who re-login via Google keep their original role — the URL role parameter is ignored.
- The `allauth` adapter (`Authentication/adapter.py`) handles the allauth-based flow separately (reads role from session).

### Password Reset flow

```
POST /forgot-password/ {email}
  → If user exists: generate OTP (EmailVerification, password_reset type)
  → Always return 200 (no email-existence disclosure)
  → Send OTP via Resend

POST /verify-password-reset-otp/ {email, otp}
  → Validate OTP not expired, not already used
  → mark_verified() on EmailVerification
  → Return {uid: user.pk}

POST /reset-password/ {uid, new_password, confirm_password}
  → set_password(new_password)
  → user.is_email_verified = True  ← IMPORTANT: fixes unverified-user lockout
  → Save user
```

### JWT Settings

| Setting | Value |
|---|---|
| Access token lifetime | 1 hour |
| Refresh token lifetime | 6 hours |
| Rotate refresh tokens | Yes — every refresh returns a new refresh token |
| Blacklist after rotation | Yes — old refresh token is immediately invalidated |
| Auth header type | `Bearer` |
| Custom claims | `role`, `email` embedded in both access and refresh tokens |

### Role System

Two roles, chosen at registration, immutable:

| Role | Can do |
|---|---|
| `pathfinder` | Browse opportunities, apply, bookmark opportunities/enablers, manage own profile |
| `enabler` | Post/edit/delete opportunities, view applicants, accept/reject, bookmark pathfinders |

### Permission classes

| Class | Location | What it does |
|---|---|---|
| `IsVerifiedUser` | `user_database/permissions.py` | Blocks any user whose `is_email_verified=False` |
| `IsEnablerUser` | `user_database/permissions.py`, `bookmark/permissions.py` | `role == 'enabler'` |
| `IsPathfinderUser` | `bookmark/permissions.py` | `role == 'pathfinder'` |
| `IsOwnerOrReadOnly` | `opportunities/permissions.py` | Write only if `obj.created_by == request.user` |
| `IsEnablerOrReadOnly` | `opportunities/permissions.py` | Write only if `role == 'enabler'` |
| `IsOpportunityOwner` | `opportunities/permissions.py` | Checks opportunity FK at view level (not object level) |
| `IsPathfinder` | `opportunities/permissions.py` | `role == 'pathfinder'` (for applying) |

---

## 7. Database Models

### CustomUser (user_database)

| Field | Type | Constraints |
|---|---|---|
| id | BigAutoField (PK) | |
| email | EmailField | unique, indexed, not null |
| username | CharField | unique (from AbstractUser) |
| first_name | CharField | (from AbstractUser) |
| last_name | CharField | (from AbstractUser) |
| role | CharField(20) | choices: `pathfinder`/`enabler`; indexed; default `pathfinder` |
| is_email_verified | BooleanField | default False |
| auth_provider | CharField(20) | choices: `email`/`google`; default `email` |
| password | CharField | hashed (from AbstractUser) |
| is_active | BooleanField | from AbstractUser |
| date_joined | DateTimeField | from AbstractUser |

**Custom method:** `tokens()` — mints JWT pair with `role` and `email` as custom claims.

### EmailVerification (user_database)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| user | FK → CustomUser | nullable (waitlist entries have no user) |
| email | EmailField | indexed |
| token | CharField(64) | unique, indexed; stores either UUID hex or 6-digit OTP |
| verification_type | CharField(20) | `waitlist` / `user_signup` / `password_reset` |
| is_verified | BooleanField | default False |
| expires_at | DateTimeField | |
| verified_at | DateTimeField | nullable |
| resend_count | IntegerField | tracks resend abuse |
| last_resend_at | DateTimeField | nullable |

**Class methods:** `create_verification()` (UUID token for links), `create_otp_verification()` (6-digit OTP).

### Profile (profiles)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| user | OneToOneField → CustomUser | `related_name="profile"` |
| profile_pic | ImageField | Cloudinary; nullable; path via `recipe_image_file_path()` |
| bio | TextField(150) | nullable |
| contact_email | EmailField(256) | nullable |
| phone_number | CharField(20) | nullable |
| address | TextField(256) | nullable |
| state | CharField(50) | nullable |
| country | CharField(50) | nullable |
| website | URLField(256) | nullable |
| created_at | DateTimeField | auto_now_add |

### EnablerProfileExtra (profiles)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| profile | OneToOneField → Profile | `related_name="enabler_extra"` |
| name | CharField(100) | organization name |
| employees | IntegerField | nullable |
| role | CharField(50) | user's role within organization (e.g. "HR Manager"); nullable |

### PathfinderProfileExtra (profiles)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| profile | OneToOneField → Profile | `related_name="pathfinder_extra"` |
| first_name | CharField(50) | |
| last_name | CharField(50) | |
| other_name | CharField(50) | nullable |
| title | CharField(100) | e.g. "Software Engineer"; nullable |
| about | TextField(1000) | nullable |
| work_experience | TextField | nullable |
| languages | CharField(200) | nullable |
| gmail | EmailField(256) | nullable |

**Related sets:** `pathfinder_skills`, `pathfinder_education`, `pathfinder_certifications` (all via FK).

### SocialLink (profiles)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| profile | FK → Profile | `related_name="social_links"` |
| platform_name | CharField(50) | |
| platform_url | URLField(150) | URLValidator(schemes=['http','https']) |

### Credential (profiles)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| profile | FK → Profile | `related_name="credentials"` |
| document_name | CharField(100) | Auto-populated from original filename if omitted |
| document | FileField | `RawMediaCloudinaryStorage()`; path via `credential_file_path()` |
| is_verified | BooleanField | default False; platform admin marks verified |

### PathfinderSkill / PathfinderEducation / PathfinderCertification (profiles)

All three follow the same pattern:

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| name | CharField(100) | |
| pathfinder | FK → PathfinderProfileExtra | respective `related_name` |

### Opportunity (opportunities)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| title | CharField(255) | |
| opportunity_type | CharField(100) | choices: `volunteering`/`internship`/`scholarship`/`job`/`grant`; indexed |
| description | TextField | Free text; see Section 10 for custom questions convention |
| link | URLField | must start with `https://` |
| posted_at | DateTimeField | auto_now_add; indexed via ordering |
| is_open | BooleanField | default True; indexed |
| created_by | FK → CustomUser | `related_name="created_opportunities"` |

**Constraint:** `unique_together = ('title', 'link')`.
**Custom method:** `can_edit()` — returns True if within 12 hours of `posted_at`.

### Application (applications)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| user | FK → CustomUser | `related_name="applications"` |
| opportunity | FK → Opportunity | `related_name="applicants"` |
| cover_letter | TextField | blank=True |
| status | CharField(10) | `pending`/`accepted`/`rejected`; default `pending` |
| resume | FileField | `RawMediaCloudinaryStorage()`; nullable |
| profile_resume | FK → Credential | nullable; alternative to uploading a new file |
| applied_at | DateTimeField | auto_now_add |
| reviewed_at | DateTimeField | nullable; set when status changes |

**Constraint:** `unique_together = ('user', 'opportunity')`.

### Bookmark (bookmark)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| user | FK → CustomUser | |
| opportunity | FK → Opportunity | |
| created_at | DateTimeField | auto_now_add |

**Constraint:** `unique_together = ("user", "opportunity")`.

### BookmarkUser (bookmark)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| enabler | FK → CustomUser | `related_name="bookmarked_pathfinders"` |
| pathfinder | FK → PathfinderProfileExtra | `related_name="favorited_by"` |
| created_at | DateTimeField | auto_now_add |

**Constraint:** `unique_together = ("enabler", "pathfinder")`.

### BookmarkEnabler (bookmark)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| pathfinder | FK → CustomUser | `related_name="bookmarked_enablers"` |
| enabler | FK → EnablerProfileExtra | `related_name="favorited_by_pathfinders"` |
| created_at | DateTimeField | auto_now_add |

**Constraint:** `unique_together = ("pathfinder", "enabler")`.

### Notification (notifications)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| recipient | FK → CustomUser | nullable = broadcast; `related_name="notifications"` |
| title | CharField(200) | |
| message | TextField | |
| priority | CharField(10) | `info`/`warning`/`critical`; default `info` |
| type | CharField(10) | `system`/`server`/`personal`; default `personal` |
| link | URLField | nullable |
| created_at | DateTimeField | auto_now_add |
| read_by | M2M → CustomUser | `related_name="read_notifications"` |

### WaitlistEmail (waitlist)

| Field | Type | Notes |
|---|---|---|
| id | BigAutoField (PK) | |
| email | EmailField | unique, indexed |
| name | CharField(255) | nullable |
| referral_source | CharField(100) | nullable |
| created_at | DateTimeField | auto_now_add |
| is_verified | BooleanField | default False |

### Model Relationship Diagram

```
CustomUser (1) ─────────────────────────── (1) Profile
     │                                           │
     │ (1)                              ┌────────┴────────┐
     │                                  │                 │
     ├── EmailVerification(*)     EnablerProfileExtra(1)  PathfinderProfileExtra(1)
     │                                                     │
     ├── Application(*)                                    ├── PathfinderSkill(*)
     │         │                                           ├── PathfinderEducation(*)
     │         └── Opportunity ──(FK)──►CustomUser          └── PathfinderCertification(*)
     │                  │
     ├── Bookmark(*)    └── Application(*)
     │         └── Opportunity
     │
     ├── BookmarkUser(*) [as enabler] ──► PathfinderProfileExtra
     │
     ├── BookmarkEnabler(*) [as pathfinder] ──► EnablerProfileExtra
     │
     └── Notification(*) [as recipient]
              └── read_by M2M ──► CustomUser(*)

Profile(1) ──► SocialLink(*)
Profile(1) ──► Credential(*)
Credential(1) ──► Application [profile_resume FK, nullable]
```

---

## 8. Notification System

### How it works end to end

Notifications are created imperatively in application views (not via signals). Two places trigger them:

**1. `applications/views.py — perform_create()`**

When a pathfinder submits an application, a `Notification` is created for the enabler who owns the opportunity:

```python
Notification.objects.create(
    recipient=opportunity.created_by,   # ← targeted at the enabler
    title="New Application Received",
    message=f"{user.username} has applied for your opportunity: '{opportunity.title}'.",
    type='personal',
    priority='info',
    link=f"/enabler/applicants/{opportunity.id}/",   # frontend route
)
```

**2. `applications/views.py — change_status()`**

When an enabler accepts or rejects an application, a `Notification` is created for the pathfinder:

```python
Notification.objects.create(
    recipient=application.user,         # ← targeted at the pathfinder
    title=f"Application {new_status.capitalize()}",
    message=f"Your application for '{application.opportunity.title}' has been {new_status}.",
    type='personal',
    priority='info' if new_status == 'accepted' else 'warning',
    link="/my-applications",           # frontend route
)
```

### How the frontend reads them

`GET /api/notify/notifications/` — the `get_queryset()` in `NotificationViewSet`:

```python
Notification.objects.filter(
    Q(recipient=user) | Q(recipient__isnull=True)  # personal OR broadcast
).annotate(
    current_user_read=Exists(...)  # True if user is in read_by M2M
)
```

- `current_user_read=False` → show unread badge on notification bell.
- Broadcast notifications (`recipient=None`) appear for every authenticated user.
- Personal notifications appear only for the specific recipient.

### Mark as read

- `POST /api/notify/notifications/<id>/mark-read/` — adds user to `read_by` M2M.
- `POST /api/notify/notifications/mark-all-read/` — iterates all unread notifications and adds user. Returns count of marked notifications.

**Note on mark_all_read:** The current implementation uses a for-loop instead of a bulk operation. For large notification counts this will be slow. This is a known performance limitation.

---

## 9. Bookmark System

There are three independent bookmark types, each with different FK targets.

### Type 1: Pathfinder bookmarks an Opportunity (`Bookmark`)

- **Write (POST):** send `{"opportunity_id": <opportunity_pk>}`.
- **Delete:** `DELETE /api/bookmark/opportunities/saved/<opportunity_id>/` where `opportunity_id` is the `Opportunity.pk`.
- Straightforward — both the read and delete IDs are the Opportunity's database PK.

### Type 2: Enabler bookmarks a Pathfinder (`BookmarkUser`)

This is where the write-only vs read-only ID pattern exists.

**Why it exists:** The `BookmarkUser.pathfinder` field is a FK to `PathfinderProfileExtra` (the profile object), not to the Django user. But the frontend needs the Django user ID to navigate to profiles and to construct the DELETE URL. If the list response only returned the `PathfinderProfileExtra.id`, the frontend would have no way to build the delete URL or navigate to the user's profile.

**The pattern:**
- `pathfinder_id` — **write-only** field in the serializer; accepts the Django user ID at POST time; the `validate()` method looks up the `PathfinderProfileExtra` from this user ID and stores it in `attrs['pathfinder']`.
- `pathfinder_user_id` — **read-only** field; `source='pathfinder.profile.user.id'`; included in list responses so the frontend knows the Django user ID.

**Write (POST):** `{"pathfinder_id": <django_user_id>}`  
**Read (GET):** response includes `pathfinder_user_id` (Django user ID)  
**Delete:** `DELETE /api/bookmark/applicants/saved/<pathfinder_id>/` where `pathfinder_id` = the Django user ID.

The delete view resolves: `BookmarkUser.objects.get(enabler=request.user, pathfinder__profile__user__id=user_id)`.

### Type 3: Pathfinder bookmarks an Enabler (`BookmarkEnabler`)

Same pattern as Type 2, reversed:

- `enabler_id` — write-only; accepts Django user ID.
- `enabler_user_id` — read-only; `source='enabler.profile.user.id'`.
- Delete: `DELETE /api/bookmark/enablers/saved/<enabler_id>/` where `enabler_id` = Django user ID.

---

## 10. Custom Questions Pattern

Afrivate's opportunity `description` field is a plain `TextField` with no separate database model for custom questions. The convention used by the team is to embed structured question data directly inside the description as a JSON block tagged with the marker `[CUSTOM_QUESTIONS]`.

**Example description value stored in the database:**

```
We are looking for a passionate community manager to help grow our network.

[CUSTOM_QUESTIONS]
[
  {"question": "Why do you want to volunteer with us?", "type": "textarea", "required": true},
  {"question": "How many hours per week can you commit?", "type": "text", "required": true},
  {"question": "Do you have prior community management experience?", "type": "boolean", "required": false}
]
[/CUSTOM_QUESTIONS]
```

**On the frontend (parseDescription):** The frontend splits the description on `[CUSTOM_QUESTIONS]` and `[/CUSTOM_QUESTIONS]`, renders the plain text portion as the description, and parses the JSON array to dynamically generate the application form fields.

**Why no separate model was needed:** The custom questions are effectively read-only from the backend's perspective — they're embedded at post-creation time and displayed verbatim. There is no separate submission model for custom question answers; the answers are stored in `Application.cover_letter` as a serialised JSON string by the frontend.

**Trade-offs:** Simple to implement and requires no schema changes to add custom questions to existing opportunities. The downside is that questions cannot be queried, validated, or aggregated server-side.

---

## 11. File Uploads

### Profile Pictures

- **Endpoint:** `PATCH /api/profile/profile/picture/`
- **Validation:** `ProfilePictureSerializer.validate_profile_pic()` opens the file with Pillow, calls `img.verify()`, checks the format string against `settings.PROFILE_PIC_ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}`, and checks file size against `settings.MAX_PROFILE_PIC_MB = 5`.
- **Storage:** `MediaCloudinaryStorage` (the default Django `STORAGES["default"]` backend).
- **Upload path:** `afrivate/profile_pics/user_<user_id>/<uuid><ext>` — the UUID ensures no filename collisions between uploads.
- **Old file cleanup:** `ProfilePictureSerializer.update()` deletes the previous file from Cloudinary storage after the new one is saved successfully. Storage errors are silently swallowed to avoid failing the request.

### Credential Documents

- **Endpoint:** `POST /api/profile/credentials/`
- **Storage:** `RawMediaCloudinaryStorage()` — uses the `raw` resource type so Cloudinary treats it as a binary file rather than trying to transform it as an image.
- **Upload path:** `afrivate/credentials/user_<user_id>/<uuid><ext>`.
- **Filename preservation:** `CredentialSerializer._resolve_document_name()` falls back to the original filename (from `InMemoryUploadedFile.name`) if `document_name` is omitted or blank. The UUID in the Cloudinary path is still used, but the `document_name` field in the database stores the human-readable original name.
- **File type:** No server-side type restriction on credentials — the constraint is at the Cloudinary storage level (`resource_type="raw"`).

### Resumes (Application uploads)

- **Endpoint:** `POST /api/applications/` with `resume` file field.
- **Storage:** `RawMediaCloudinaryStorage()`.
- **Upload path:** `afrivate/resumes/user_<user_id>/<uuid><ext>`.
- **Alternative:** Pathfinders can submit an existing `Credential` as their resume by passing `profile_resume=<credential_id>` instead of uploading a new file.

---

## 12. Email System

Two separate email providers are used — they are not interchangeable.

### Resend — Authentication emails

Used for: registration OTP, password-reset OTP, welcome-after-verification email.

All three functions are in `Authentication/utils.py` as Celery shared tasks (`@shared_task(bind=True, max_retries=3, default_retry_delay=60)`). They are called directly (not `.delay()`) in the current implementation, meaning they run synchronously.

| Function | Trigger | Subject |
|---|---|---|
| `send_signup_otp_email` | `/api/auth/register/` | "Verify your Afrivate Account" |
| `sendotp_via_email` | `/api/auth/forgot-password/` | "Password Reset OTP - Afrivate" |
| `send_welcome_email` | `/api/auth/verify-email/` (waitlist path) | "Welcome to Afrivate!" |

**Configuration:** `settings.RESEND_API_KEY`, `settings.DEFAULT_FROM_EMAIL`.

### SendGrid — Waitlist emails

Used for: welcome email on waitlist signup, verification link (function exists but is no longer called).

Both functions are in `waitlist/utils.py`. They are called synchronously from `WaitlistEmailView`.

| Function | Trigger | Subject |
|---|---|---|
| `send_welcome_email` | `POST /api/waitlist/` | "Welcome to Afrivate!" |
| `send_waitlist_verification_email` | Not currently called (legacy) | "Welcome - Afrivate Waitlist" |

**Configuration:** `settings.SENDGRID_API_KEY`, `settings.DEFAULT_FROM_EMAIL`.

### How to configure both

In `.env`:

```
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
RESEND_API_KEY=re_xxxx          # from https://resend.com
SENDGRID_API_KEY=SG.xxxx        # from https://sendgrid.com
```

Both providers use the same `DEFAULT_FROM_EMAIL` value as the sender address.

---

## 13. Task Queue (Celery + Redis)

### Configuration

In `settings.py`:

```python
CELERY_BROKER_URL = REDIS_URL       # Redis URL (also used for Django cache)
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'
```

The Celery app is defined in `app/Afrivate/celery.py` and auto-discovers tasks from all installed apps.

### Defined tasks

All email-sending functions in `Authentication/utils.py` are decorated as `@shared_task` with `max_retries=3, default_retry_delay=60`. However, they are currently called **directly** (not via `.delay()` or `.apply_async()`), which means they execute synchronously in the web process. To make them truly asynchronous, change call sites to `send_signup_otp_email.delay(...)`.

### Running workers locally

```bash
# From the app/ directory
celery -A Afrivate worker --loglevel=info
```

### Current state

Celery infrastructure is fully configured. Task functions exist and are properly decorated. The transition to async execution (calling `.delay()`) has not yet been made at the call sites.

---

## 14. Security

### Rate Limiting

`ScopedRateThrottle` is applied to six authentication endpoints. Throttle counts are cached in Redis (same `REDIS_URL`).

| Scope | Rate | Endpoint |
|---|---|---|
| `auth_register` | 5/hour | POST `/api/auth/register/` |
| `auth_login` | 10/hour | POST `/api/auth/login/` |
| `auth_otp_verify` | 10/hour | POST `/api/auth/verify-otp/` |
| `auth_resend_otp` | 5/hour | POST `/api/auth/resend-otp/` |
| `auth_forgot_password` | 5/hour | POST `/api/auth/forgot-password/` |
| `auth_password_reset` | 10/hour | POST `/api/auth/reset-password/` |

### CORS

Hardcoded allowed origins (in `settings.py`):

```
http://localhost:3000
https://afrivate-tech.github.io
https://afrivate-backend-production.up.railway.app
https://afrivate.org
https://www.afrivate.org
https://afrivate-volunteer-module-frontend.vercel.app
```

Additional origins can be injected at deploy time via `CORS_ALLOWED_ORIGINS` env var (comma-separated). The code merges hardcoded and env-var origins into a deduplicated set.

To add a new origin permanently: add it to `_CORS_ORIGINS_DEFAULT` in `settings.py`. For a temporary/environment-specific origin, set the env var.

`CORS_ALLOW_CREDENTIALS = True` — required for cookie-based auth from the frontend.

### SSL

`ssl_require=not DEBUG` in the database connection. In production (`DEBUG=0`), all PostgreSQL connections are encrypted. In local dev (`DEBUG=1`), SSL is disabled.

### JWT Security

- Refresh tokens are blacklisted after rotation (`BLACKLIST_AFTER_ROTATION = True`). Once used, a refresh token cannot be reused even if intercepted.
- `UPDATE_LAST_LOGIN = True` — updates `CustomUser.last_login` on every token refresh.

### Social Link URL Validation

`SocialLink.platform_url` has `URLValidator(schemes=['http', 'https'])`. This rejects `javascript:`, `data:`, `ftp://`, and other non-web schemes.

### Notification Auth Requirement

All write operations on notifications (create, update, delete) require `IsAdminUser`. All reads require `IsAuthenticated`. There is no public notification feed.

### Password Reset Timeout

`PASSWORD_RESET_TIMEOUT = 3600` (1 hour). OTPs also have their own 10-minute expiry enforced at the `EmailVerification.is_valid()` level.

### Unverified User Fix

Before this branch, calling `forgot-password` for an unverified account would send the OTP, but `verify-password-reset-otp` and `reset-password` would succeed, yet the user still couldn't log in because `is_email_verified` was `False`. The fix: `reset-password` now sets `user.is_email_verified = True`. Completing the password reset flow proves the user controls the inbox, which is equivalent to email verification.

### What was fixed from the original security audit

1. Removed debug `print()` function in `opportunities/permissions.py` that leaked user data.
2. Replaced `print()` calls with `logger.error()` across `profiles/serializers.py` and `waitlist/utils.py`.
3. Fixed `ssl_require=not True` (was hardcoded `False`).
4. Reduced `PASSWORD_RESET_TIMEOUT` from 86400s to 3600s.
5. Added rate limiting to all auth endpoints.
6. Added `URLValidator` to `SocialLink.platform_url`.
7. Fixed unverified-user password reset catch-22.
8. Removed duplicate `post_save` signal in `user_database/signals.py` (infinite loop risk).

---

## 15. Environment Variables

All variables are documented in [`.env.example`](.env.example). Copy it with `cp .env.example .env` and fill in values.

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | Yes | Django secret key for signing sessions, tokens | `django-insecure-xxx...` |
| `DEBUG` | Yes | `1` = dev; `0` = production | `1` |
| `DB_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/afrivate` |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames | `localhost,127.0.0.1` |
| `SITE_DOMAIN` | No | Backend public URL; used in redirects | `https://afrivate-backend-production.up.railway.app` |
| `FRONTEND_URL` | No | Frontend public URL; used in CORS and redirects | `https://afrivate-volunteer-module-frontend.vercel.app` |
| `DEFAULT_FROM_EMAIL` | Yes | Sender address for all emails | `noreply@afrivate.org` |
| `RESEND_API_KEY` | Yes | Resend API key for auth emails | `re_xxxxxxxxxxxx` |
| `SENDGRID_API_KEY` | Yes | SendGrid API key for waitlist emails | `SG.xxxxxxxxxxxx` |
| `CLOUDINARY_CLOUD_NAME` | Yes | Cloudinary cloud name | `afrivate` |
| `CLOUDINARY_API_KEY` | Yes | Cloudinary API key | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Yes | Cloudinary API secret | `abc123...` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID | `xxxxx.apps.googleusercontent.com` |
| `REDIS_URL` | No | Redis connection URL; defaults to `redis://127.0.0.1:6379/1` | `redis://localhost:6379/1` |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated extra CORS origins (merged with hardcoded list) | `https://staging.afrivate.org` |

**Where each is used in code:**

| Variable | File | Usage |
|---|---|---|
| `SECRET_KEY` | `settings.py` | `SECRET_KEY = os.environ.get('SECRET_KEY')` |
| `DEBUG` | `settings.py` | Controls `ssl_require`, `SITE_DOMAIN`, `FRONTEND_URL` |
| `DB_URL` | `settings.py` | `dj_database_url.parse(os.environ.get("DB_URL"), ssl_require=not DEBUG)` |
| `ALLOWED_HOSTS` | `settings.py` | Extended into `ALLOWED_HOSTS` list |
| `RESEND_API_KEY` | `Authentication/utils.py` | `resend.api_key = settings.RESEND_API_KEY` |
| `SENDGRID_API_KEY` | `waitlist/utils.py` | `SendGridAPIClient(settings.SENDGRID_API_KEY)` |
| `DEFAULT_FROM_EMAIL` | `Authentication/utils.py`, `waitlist/utils.py` | Used as `from_email` in all email sends |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | `settings.py` | `CLOUDINARY_STORAGE` dict |
| `GOOGLE_CLIENT_ID` | `settings.py` | Passed to `id_token.verify_oauth2_token()` |
| `REDIS_URL` | `settings.py` | Both `CACHES["default"]["LOCATION"]` and `CELERY_BROKER_URL` |
| `CORS_ALLOWED_ORIGINS` | `settings.py` | Merged into `CORS_ALLOWED_ORIGINS` list |

---

## 16. Local Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ running locally (or a Neon/Supabase connection string)
- Redis running locally (needed for caching and Celery)
- Git

### Step-by-step from scratch

**1. Clone the repository**

```bash
git clone https://github.com/AfriVate-Tech/Afrivate-Backend.git
cd Afrivate-Backend
git checkout light
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
cd app
pip install -r requirements.txt
```

**4. Set up environment variables**

```bash
# From the repo root
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```
SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=1
DB_URL=postgresql://your_user:your_password@localhost:5432/afrivate_dev
ALLOWED_HOSTS=localhost,127.0.0.1
DEFAULT_FROM_EMAIL=noreply@yourdevdomain.com
RESEND_API_KEY=re_xxx
SENDGRID_API_KEY=SG.xxx
CLOUDINARY_CLOUD_NAME=xxx
CLOUDINARY_API_KEY=xxx
CLOUDINARY_API_SECRET=xxx
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
```

For local testing without email, you can use placeholder values — email sending will fail gracefully.

**5. Create the database**

```bash
# In PostgreSQL
createdb afrivate_dev
```

Or use any PostgreSQL client. Update `DB_URL` in `.env` accordingly.

**6. Run migrations**

```bash
cd app  # already there if you followed step 3
python manage.py migrate
```

**7. Create a superuser (optional)**

```bash
python manage.py createsuperuser
```

**8. Start Redis**

```bash
# macOS (Homebrew)
brew services start redis
# Ubuntu/Debian
sudo service redis-server start
# Windows (WSL or standalone Redis)
redis-server
```

**9. Run the development server**

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000`.

**10. Run Celery worker (optional — only needed for async email tasks)**

In a separate terminal, from the `app/` directory:

```bash
celery -A Afrivate worker --loglevel=info
```

### Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `django.db.utils.OperationalError: FATAL: database ... does not exist` | Database not created | Run `createdb afrivate_dev` |
| `redis.exceptions.ConnectionError` | Redis not running | Start Redis (see step 8) |
| `KeyError: 'SECRET_KEY'` | `.env` not loaded or missing key | Ensure `.env` exists in repo root and `SECRET_KEY` is set |
| `cloudinary.exceptions.AuthorizationRequired` | Cloudinary keys not set | Add `CLOUDINARY_*` vars to `.env` |
| `AttributeError: 'NoneType' object has no attribute 'startswith'` | `DB_URL` is empty | Set `DB_URL` in `.env` |
| `OperationalError: SSL connection has been closed unexpectedly` | `DEBUG=0` with local (non-SSL) DB | Set `DEBUG=1` for local dev |

---

## 17. Deployment (Railway)

### Current deployment

- **Backend URL:** `https://afrivate-backend-production.up.railway.app`
- **Platform:** Railway
- **Root directory:** `/app` (Django project root where `manage.py` lives)

### Process declarations (`Procfile`)

```
web: gunicorn Afrivate.wsgi
worker: celery -A Afrivate worker --loglevel=info
```

Railway runs both processes. The `web` process handles HTTP requests. The `worker` process handles Celery tasks.

### Build command

Railway automatically runs:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

### Start command

```bash
gunicorn Afrivate.wsgi
```

### Environment variables needed on Railway

All variables from Section 15. Key production-specific values:

| Variable | Production value |
|---|---|
| `DEBUG` | `0` |
| `DB_URL` | Railway PostgreSQL provisioned URL (found in Railway dashboard) |
| `REDIS_URL` | Railway Redis provisioned URL |
| `ALLOWED_HOSTS` | `afrivate-backend-production.up.railway.app` |
| `SITE_DOMAIN` | `https://afrivate-backend-production.up.railway.app` |
| `FRONTEND_URL` | `https://afrivate-volunteer-module-frontend.vercel.app` |

### How to deploy this branch

1. Push `light` to the remote: `git push origin light`
2. In Railway dashboard → select service → Settings → Branch → change to `light`.
3. Railway will redeploy automatically.

### How to connect a new database

1. In Railway, provision a new PostgreSQL database add-on.
2. Copy the connection string.
3. Update the `DB_URL` environment variable.
4. Trigger a redeploy.
5. Run migrations manually if Railway doesn't auto-migrate: `railway run python manage.py migrate`.

---

## 18. Running Migrations

### How migrations work in this project

Each Django app has its own `migrations/` directory. Migrations are committed to the repo.

### Order of operations for a new migration

1. Edit the model.
2. `python manage.py makemigrations <app_name>`
3. Review the generated migration file.
4. `python manage.py migrate`

### Apps with notable migrations

| App | Notable migration | Reason |
|---|---|---|
| `profiles` | `0002_initial.py` | Second complete initial (after reset) |
| `profiles` | `0004_remove_profile_city_...` | Removed `city` field |
| `profiles` | `0005_alter_credential_document_alter_profile_profile_pic` | Storage backend change |
| `bookmark` | `0005_bookmarkuser` | Added BookmarkUser model |
| `bookmark` | `0007_bookmarkenabler` | Added BookmarkEnabler model |
| `notifications` | `0002_remove_notification_is_read_notification_read_by` | Replaced `is_read` bool with `read_by` M2M |
| `notifications` | `0003_alter_notification_priority_alter_notification_type` | Added type/priority field choices |
| `applications` | `0003_application_resume` | Added resume file field |
| `applications` | `0004_application_profile_resume` | Added profile_resume FK |

### On merge to main

After merging `light` into `main` and deploying, run:

```bash
python manage.py migrate
```

This applies all pending migrations. Railway will do this automatically on redeploy if the build command includes `python manage.py migrate`.

---

## 19. Testing

### What has been manually tested

- Full registration → OTP → login flow (email and Google).
- Password reset including unverified-user case.
- Profile create/update for both roles.
- Opportunity CRUD with 12-hour edit window.
- Application submit, withdraw, change_status.
- All bookmark types including delete by user ID.
- Notification delivery and read-marking.
- Waitlist signup with domain validation.
- Rate limiting on auth endpoints.
- File upload (profile pic and credential).

### How to run the test suite

```bash
cd app
python manage.py test
```

### What test coverage exists

Stub `tests.py` / `test.py` files exist in each app but contain no written tests as of this branch. The test suite will pass with 0 tests.

### What needs test coverage

- `Authentication/views.py` — OTP flow, rate limiting, Google login.
- `applications/views.py` — notification side effects on `perform_create` and `change_status`.
- `bookmark/views.py` — user ID lookup in delete views.
- `profiles/serializers.py` — credential filename preservation, profile picture validation.
- `notifications/views.py` — `get_queryset` filtering (personal vs broadcast).

---

## 20. Known Issues & Limitations

| Issue | Impact | Status |
|---|---|---|
| **Multi-tab frontend session conflict** | If a user opens the app in two tabs and logs out in one, the other tab's requests will silently fail with 401 until it also refreshes. | Open — needs frontend interceptor fix. |
| **Celery tasks called synchronously** | Email functions in `Authentication/utils.py` are decorated as Celery tasks but called without `.delay()`. Emails block the HTTP request. | Open — change call sites to use `.delay()`. |
| **No admin customisation** | Django admin is available at `/admin/` but no custom `ModelAdmin` classes are registered for any app. Management is via shell/Swagger. | Open. |
| **No 2FA** | Authentication only supports password + OTP (for registration/reset), not a persistent second factor. | Not planned. |
| **No WebSocket / real-time updates** | Notifications require polling. No Django Channels setup. | Open — WebSocket support would require channels + Redis. |
| **Waitlist stats endpoint open** | `GET /api/waitlist/stats/` has no auth guard — anyone can view signup counts. | Minor — add `IsAdminUser` permission when needed. |
| **`mark_all_read` uses for-loop** | `notifications/views.py mark_all_read` iterates notifications one by one; will be slow for users with many notifications. | Low priority — replace with `read_by.add(*notifications)` bulk call. |
| **`resend_count` on OTP capped at 3 then reset after 30 min** | Slightly inconsistent UX — the cooldown resets the counter, meaning a determined user can always get more OTPs. | Acceptable for now. |

---

## 21. Merge Instructions

### Pre-merge checklist

- [ ] All tests pass: `python manage.py test`
- [ ] No uncommitted changes: `git status`
- [ ] Migrations are committed: `git status app/*/migrations/`
- [ ] `.env.example` is up to date (all new env vars documented)
- [ ] `CORS_ALLOWED_ORIGINS` in `settings.py` includes all production frontends
- [ ] `ALLOWED_HOSTS` on Railway includes the production domain
- [ ] `DEBUG=0` on Railway

### Merge steps

```bash
# On a clean checkout
git checkout main
git pull origin main
git merge light --no-ff -m "merge: light branch — security hardening, notification system, bookmark fixes"
git push origin main
```

### Post-merge production steps

1. **Environment variables** — verify all new env vars from `.env.example` are set in Railway.
2. **Deploy** — Railway will auto-deploy on push to main. Watch the build log.
3. **Run migrations** — Railway auto-runs `python manage.py migrate` as part of the build command. Verify in Railway logs.
4. **Smoke test** — hit the health check endpoints, register a test user, verify OTP arrives, complete a login, submit an application, check notifications appear.
5. **Monitor logs** — watch Railway logs for errors in the first 15 minutes post-deploy.

### Rollback plan

If the deployment is broken:

```bash
# In Railway, rollback to the previous deployment via the Railway dashboard → Deployments → select previous → Redeploy.
# OR
git revert HEAD --no-edit
git push origin main
```

The only destructive migration on this branch is `notifications/0002` (replaces `is_read` BooleanField with `read_by` M2M). If you need to roll back past that migration, you must manually restore data:

```bash
python manage.py migrate notifications 0001
```

---

## 22. Changelog

All changes on `light` vs `main`, derived from commit history.

### Critical Bug Fixes

| Fix | File | Description |
|---|---|---|
| Remove duplicate `post_save` signal | `user_database/signals.py` | The original signal called `instance.save()` inside a `post_save` handler, creating a recursive loop risk on user creation. Signal neutered; profile creation moved entirely to `profiles/signals.py`. |
| Fix `ssl_require` hardcoded to False | `settings.py` | `ssl_require=not True` was effectively `ssl_require=False` in all environments. Changed to `ssl_require=not DEBUG` so production DB connections are encrypted. |
| Fix unverified-user password reset catch-22 | `Authentication/views.py` | Unverified users could request and verify a password reset OTP, but the reset did not mark them as verified — so they still couldn't log in. `ResetPasswordView` now sets `user.is_email_verified = True`. |

### Security Hardening

| Fix | File | Description |
|---|---|---|
| ScopedRateThrottle on all 6 auth endpoints | `settings.py`, `Authentication/views.py` | Prevents brute-force on register, login, OTP, resend-OTP, forgot-password, reset-password. |
| URL validation on `SocialLink.platform_url` | `profiles/models.py` | Added `URLValidator(schemes=['http','https'])` to reject non-web schemes. |
| Reduce `PASSWORD_RESET_TIMEOUT` | `settings.py` | From 86400s (24h) to 3600s (1h). |
| Remove leaking `print()` calls | `opportunities/permissions.py`, `profiles/serializers.py`, `waitlist/utils.py` | Replaced with `logger.error()` or removed entirely. |
| Add `CORS_ALLOWED_ORIGINS` env var support | `settings.py` | Extra origins can now be injected without changing code. |

### New Features

| Feature | Files | Description |
|---|---|---|
| Per-user notifications on application events | `applications/views.py`, `notifications/models.py` | `perform_create` notifies the enabler; `change_status` notifies the pathfinder. `recipient` FK is now used — previously all notifications were broadcast. |
| `recipient` FK filter in `get_queryset` | `notifications/views.py` | Notifications are now filtered to `(recipient=user) OR (recipient=null)`. Previously all notifications were visible to all authenticated users. |
| `pathfinder_user_id` in bookmark list response | `bookmark/serializers.py` | Enables frontend to construct DELETE URL without a separate profile lookup. |
| `enabler_user_id` in bookmark list response | `bookmark/serializers.py` | Same fix for the enabler bookmark type. |
| `BookmarkEnabler` model and endpoints | `bookmark/models.py`, `bookmark/serializers.py`, `bookmark/views.py`, `bookmark/urls.py` | Pathfinders can bookmark enabler profiles. Three new endpoints added. |
| Credential filename preservation | `profiles/serializers.py` | `document_name` is auto-populated from the uploaded file's original name if omitted. |
| `CORS_ALLOWED_ORIGINS` env var | `settings.py` | New origins can be injected at deploy time. |

### API Changes

| Change | Description |
|---|---|
| `GET /api/bookmark/applicants/saved/` response | Now includes `pathfinder_user_id` field. |
| `GET /api/bookmark/enablers/saved/` response | Now includes `enabler_user_id` field. |
| `GET /api/notify/notifications/` response | Now filtered per-user; `current_user_read` annotation added. |
| `POST /api/bookmark/applicants/saved/` request | `pathfinder_id` field is the Django user ID (not profile ID). |
| `DELETE /api/bookmark/applicants/saved/<id>/` | `<id>` is now the pathfinder's Django user ID. |
| New: `GET/POST/DELETE /api/bookmark/enablers/saved/` | Three new endpoints for pathfinder → enabler bookmarks. |
| Notification links | Changed from backend API paths to frontend routes (`/enabler/applicants/<id>/`, `/my-applications`). |

### Dead Code Removal

| Removed | File | Why |
|---|---|---|
| `newsletter` app (entire directory) | Multiple files | App was a stub — no models, no views, no registered URLs. Added noise. |
| Commented AWS S3 config block | `settings.py` | Cloudinary is in use; S3 is not. |
| Commented SMTP/SendGrid email backend block | `settings.py` | Resend is used for auth; config block was misleading. |
| Commented URL patterns (`api/users/`, `api/newsletter/`) | `urls.py` | Dead references to removed/unused apps. |
| Wildcard imports | `Authentication/views.py`, `profiles/serializers.py` | Replaced with explicit named imports. |

### Documentation

| Added | Description |
|---|---|
| `.env.example` | Complete list of all required environment variables with descriptions and example values. |
| `Project_Flow.md` | User-facing flow documentation and complete API reference for frontend developers. |
| `BACKEND_CHANGES.md` (this file) | Comprehensive developer reference for the light branch. |
| Inline code comments | Non-obvious logic documented in `settings.py`, `Authentication/views.py`, `applications/views.py`, `notifications/views.py`, `bookmark/serializers.py`, `bookmark/views.py`, `profiles/signals.py`, `profiles/serializers.py`, `opportunities/serializers.py`. |
