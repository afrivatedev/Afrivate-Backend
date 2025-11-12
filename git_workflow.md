# Git Collaboration Workflow (Afrivate Backend)

This document defines how backend engineers collaborate using Git for the Afrivate project.

## Branch Structure

- **main**: Always stable and production-ready.
- **dev**: Integration branch where approved work from feature branches is merged.
- **feature branches**: Each new task or change is developed in its own feature branch.

### Branch Naming Conventions

Use descriptive names:
```
feature/<short-description>
fix/<short-description>
refactor/<short-description>
```
Examples:
```
feature/auth-endpoints
feature/docker-setup
fix/login-validation
```

## Workflow Steps

### 1. Starting Work

```bash
git checkout dev
git pull
git checkout -b feature/<short-description>
```

### 2. Commit and Push Your Work

```bash
git add .
git commit -m "message describing what was done"
git push -u origin feature/<short-description>
```

### 3. Open a Pull Request (PR)

- Go to GitHub
- Open a Pull Request from your feature branch into **dev**
- Request a review from another backend engineer

### 4. Review Process

Before merging a PR:
- Ensure the code is readable and clear
- Confirm no secrets or `.env` files are committed
- Verify tests or manual verification
- Ensure no breaking changes introduced without communication

Once review is complete:
- Merge PR into **dev**

### 5. Merging `dev` → `main`

Only when the project reaches a stable milestone:
- Open a PR from `dev` to `main`
- Review and confirm stability before merging

## Keeping Feature Branch Updated

If `dev` receives updates while working on your branch:

```bash
git fetch
git checkout dev
git pull
git checkout feature/<short-description>
git merge dev
```
Resolve conflicts if needed, then push.

## Protected Branches

The following rules apply:
- No direct pushes to `main`
- Require at least 1 review before merging
- No force pushes to `main` or `dev`

## `.env` and Secrets

Never commit `.env` or secret values.
Add to `.gitignore`:
```
.env
__pycache__/
*.pyc
vol/
```

Share environment variables privately, not through Git.


## Merging Feature Branches and Updating Remote

Merging a feature branch into `dev` locally does not automatically update the remote repository.

### Steps to Merge Locally and Push

```bash
git checkout dev
git pull
git merge feature/<short-description>
```

At this point, the merge exists only in your local environment. To update the remote `dev` branch:

```bash
git push origin dev
```

### Best Practice for Collaboration

Instead of merging locally, open a Pull Request from your feature branch into `dev` on GitHub. This allows for code review, CI checks, and cleaner history.

### After Successful Merge (Optional Cleanup)

Delete feature branch locally:
```bash
git branch -d feature/<short-description>
```

Delete feature branch on remote:
```bash
git push origin --delete feature/<short-description>
```
