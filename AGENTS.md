# AGENTS.md: Afrivate Backend

Instructions for AI coding agents and new contributors. Read this first, then `ARCHITECTURE.md`, `SECURITY.md` and `CODE_STYLE.md`.

## Ground rules

1. **Preserve working features and content.** Do not delete or rewrite code or docs unless the owner asks.
2. **Audits are report-only.** When asked for a security or launch check, report findings first. Change code only after the owner approves.
3. **Never touch secrets.** Do not open, print, copy or commit `.env` files or any key, token or password. Do not paste credentials into chat or tickets.
4. **Explain trade-offs in plain words.** When a fix has a cost, say what it is.
5. **Ask before big changes.** Changes to auth, permissions, storage or settings need owner approval.

## Setup

```bash
git clone <repo-url>
cd <repo>
python -m venv venv
venv\Scripts\activate          # Windows
# or: source venv/bin/activate  # macOS/Linux

cd app
pip install -r requirements.txt
```

Create `.env` in the **backend root** (next to `.env.example`). Fill in values from the owner. Never commit it.

## Commands

Run these from `app/`:

```bash
python manage.py migrate          # apply migrations
python manage.py runserver        # local server on http://127.0.0.1:8000
python manage.py test             # run tests
python manage.py makemigrations   # after changing models
```

Local API docs: `http://127.0.0.1:8000/api/v1/docs/`

## Git workflow

Follow `git_workflow.md`:

- Branch from `dev`: `feature/<short-name>`, `fix/<short-name>` or `refactor/<short-name>`.
- Open a pull request into `dev`. Never push to `main` directly. Never force-push `main` or `dev`.
- Do not commit `.env` or any secret.
- Note: `README.md` says to target `light`. Confirm the target branch with the owner before opening a pull request.

## Definition of done

- `python manage.py test` passes.
- New or changed endpoints have tests (success, 401, 403, 400).
- Every new endpoint checks ownership and validates input (see `SECURITY.md`).
- New environment variables are added to `.env.example` with no value and to `ARCHITECTURE.md`.
- Migrations are committed with the model change.
- If an endpoint changed, update the API docs (`Project_Flow.md`).

## Files to be careful with

| File | Why |
|---|---|
| `Afrivate/settings.py` | Security settings, CORS, throttle rates, storage. Changes need review. |
| `*/migrations/` | Never edit by hand. Never delete a migration that has run in production. |
| `.env`, `.env.example` | Secrets. `.env.example` must never contain real values. |
| `requirements.txt` | Version ranges. Test after any change. |
