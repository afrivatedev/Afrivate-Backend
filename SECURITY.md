# Security Policy: Afrivate Backend

Last updated: 26 November 2026

## Reporting a vulnerability

Do not open a public GitHub issue for a security problem.

Email: **[security contact email, to be filled in]**

Include:
- The endpoint or file affected
- Steps to reproduce
- What an attacker could see or change

Only share real account data in a report if it is your own test account.

## How the backend protects users (current design)

**Login and tokens**
- Login uses JWT (djangorestframework-simplejwt).
- Access tokens last 1 hour. Refresh tokens last 6 hours.
- Refresh tokens rotate on every use, and the old one is blacklisted.
- Logout blacklists the refresh token.

**Codes and links**
- Email verification OTP: 6 digits, valid 10 minutes.
- Password reset: code expires after 15 minutes and is single use.
- No magic links exist today. If added, they must expire in about 30 minutes and work once.

**Rate limits (per IP, per hour, Redis-backed)**

| Scope | Limit |
|---|---|
| Register | 5/hour |
| Login | 10/hour |
| OTP verify | 10/hour |
| Resend OTP | 5/hour |
| Forgot password | 5/hour |
| Password reset | 10/hour |
| Admin login | 10/hour |
| Organisation create | 10/hour |
| Organisation document upload | 60/hour |
| Organisation representative register | 10/hour |
| Organisation vouch | 10/hour |

Anything over the limit returns HTTP 429.

**Data access**
- Every endpoint that reads or changes a record must check that the logged-in user owns it. If not, return 403.
- Database access uses the Django ORM with parameterised queries. Raw SQL is not allowed without review.
- Database connections use SSL when `DEBUG` is off.

**Input and output**
- Validate all input on the server, in serializers.
- Never put user-supplied text into HTML emails without escaping it.

**Uploads**
- Profile pictures: JPEG, PNG or WEBP only, max 5 MB.
- Organisation documents: max 10 MB by default (`MAX_ORG_DOCUMENT_MB`).
- Private documents (IDs, resumes, certificates, organisation papers) must sit behind login and use signed URLs that expire.

**Secrets**
- Keys, passwords and tokens live only in environment variables.
- `.env` is git-ignored. `.env.example` lists the variable names with no values.
- Never commit a real value. If one is committed, rotate it first, then remove it from git history.

**Production settings**
- `DEBUG` must be `0` in production. The default in code is `0`.
- Error pages must never show stack traces or internal details.

**CORS**
- Only Afrivate's own domains may be listed in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

**Logs**
- Never log passwords, tokens, OTP codes or the contents of uploaded documents.

## Rules for every change

- New endpoint: owner check, input validation, and a rate limit if it is public or handles login.
- New file upload: size and type checks, and private storage with expiring links if it holds personal documents.
- New email template: escape every variable.
- New secret: add the name to `.env.example` with no value, and document it in `ARCHITECTURE.md`.

## Known gaps

Open issues from the internal security review are tracked outside this repository. This file describes the rules, not the current list of open issues.

## Dependencies

- Versions are pinned in ranges in `app/requirements.txt`.
- Review and update them regularly. Check for security advisories before each release.
