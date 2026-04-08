# Project Flow — Afrivate Backend

> **Audience:** Frontend developers, project managers, and new team members.
> **Goal:** Understand the whole platform — how users move through it, what every API does, and what the UI needs to handle.

---

## Table of Contents

1. [What Is Afrivate?](#1-what-is-afrivate)
2. [The Two User Types](#2-the-two-user-types)
3. [High-Level System Overview](#3-high-level-system-overview)
4. [Screen Connection Map](#4-screen-connection-map)
5. [Step-by-Step User Flows](#5-step-by-step-user-flows)
6. [Complete API Reference](#6-complete-api-reference)
   - [A. Authentication](#a-authentication-endpoints)
   - [B. Profiles](#b-profile-endpoints)
   - [C. Opportunities](#c-opportunities-endpoints)
   - [D. Applications](#d-applications-endpoints)
   - [E. Bookmarks](#e-bookmark-endpoints)
   - [F. Notifications](#f-notifications-endpoints)
   - [G. Waitlist](#g-waitlist-endpoints)
7. [Business Rules for the Project Manager](#7-business-rules-for-the-project-manager)
8. [Frontend Developer Notes](#8-frontend-developer-notes)

---

## 1. What Is Afrivate?

Afrivate is a **marketplace platform for African professionals**. It connects two groups:

- **Pathfinders** — people looking for opportunities (jobs, internships, volunteering, scholarships, grants).
- **Enablers** — organizations and individuals who post those opportunities and want to hire or mentor Pathfinders.

Think of it like LinkedIn meets a volunteering board — designed specifically for the African professional ecosystem.

---

## 2. The Two User Types

| Feature | Pathfinder 🧭 | Enabler 🤝 |
|---|---|---|
| Who they are | Job seekers, volunteers, interns, scholars | Companies, NGOs, mentors, employers |
| Browse opportunities | ✅ Yes | ✅ Yes |
| Apply to opportunities | ✅ Yes | ❌ No |
| Post opportunities | ❌ No | ✅ Yes |
| Edit/delete opportunities | ❌ No | ✅ Yes (within 12 hours) |
| View applicants | ❌ No | ✅ Yes (own postings only) |
| Accept/reject applicants | ❌ No | ✅ Yes |
| Bookmark opportunities | ✅ Yes | ❌ No |
| Bookmark Pathfinders | ❌ No | ✅ Yes |
| Build personal profile | ✅ Yes (career-focused) | ✅ Yes (org-focused) |

> **Key rule:** A user chooses their role at registration and **cannot change it later**.

---

## 3. High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AFRIVATE PLATFORM                        │
│                                                                 │
│   ┌────────────────┐                 ┌────────────────────────┐ │
│   │   PATHFINDER   │                 │        ENABLER         │ │
│   │                │                 │                        │ │
│   │  • Browse jobs │◄────────────────►  • Post opportunities  │ │
│   │  • Apply       │                 │  • View applicants     │ │
│   │  • Bookmark    │                 │  • Accept / Reject     │ │
│   │  • Build       │                 │  • Bookmark pathfnders │ │
│   │    profile     │                 │  • Build org profile   │ │
│   └────────────────┘                 └────────────────────────┘ │
│            │                                      │             │
│            └──────────────┬───────────────────────┘             │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │  BACKEND    │                              │
│                    │  API        │                              │
│                    │  (Django)   │                              │
│                    └──────┬──────┘                              │
│                           │                                     │
│          ┌────────────────┼────────────────┐                    │
│          │                │                │                    │
│    ┌─────▼─────┐   ┌──────▼──────┐  ┌─────▼──────┐            │
│    │ PostgreSQL│   │  Cloudinary │  │   Gmail    │            │
│    │ Database  │   │  (Files &   │  │   SMTP     │            │
│    │           │   │   Images)   │  │  (Emails)  │            │
│    └───────────┘   └─────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**How data moves:**
1. The **frontend** sends HTTP requests (JSON) to the **Backend API**.
2. The API reads/writes data to the **PostgreSQL database**.
3. File uploads (profile pictures, resumes, documents) are stored on **Cloudinary** (a cloud file service).
4. Emails (OTP codes, welcome messages) are sent via **Gmail SMTP**.
5. The API sends back a **JSON response** which the frontend uses to update the UI.

**Authentication:**
- All protected actions require the frontend to include a **JWT access token** in the request header.
- Token format: `Authorization: Bearer <access_token>`
- Tokens expire after **1 hour**; the frontend must refresh them silently.

---

## 4. Screen Connection Map

Below is a simplified map showing how screens/pages connect to each other:

```
[Landing Page / Waitlist]
         │
         ▼
[Choose Role: Pathfinder or Enabler]
         │
    ┌────┴────┐
    │         │
[Sign Up]  [Log In]
    │         │
    ▼         │
[Verify OTP]  │
    │         │
    └────┬────┘
         │
         ▼
    [Dashboard]
    ┌────┴────────────────────────┐
    │                             │
    ▼                             ▼
[My Profile]              [Opportunities Feed]
    │                             │
    ▼                             ▼
[Edit Profile]           [Opportunity Detail]
[Upload Credentials]             │
[Add Social Links]          ┌────┴────┐
                            │         │
                    [Apply Here]  [Bookmark It]
                            │
                            ▼
                    [My Applications]  ──── (Pathfinder only)
                            │
                            ▼
                    [Application Status]


[For Enablers — different right side:]
[Post New Opportunity]
         │
         ▼
[My Posted Opportunities]
         │
         ▼
[View Applicants List]
         │
         ▼
[View Applicant Profile]
         │
         ▼
[Accept / Reject Applicant]


[Notifications Bell] ──► [Notifications Page] (always accessible)
[Bookmarks] ──► [Saved Opportunities / Saved Pathfinders]
[Settings] ──► [Change Password, Set Password (Google users)]
```

---

## 5. Step-by-Step User Flows

### 5.1 — Joining the Waitlist (Pre-Launch)

> This is a simple email signup before the full platform is open.

1. User visits the landing page.
2. User enters their **email** (and optionally name + how they heard about Afrivate).
3. Frontend calls `POST /api/waitlist/`.
4. Backend saves the email and sends a **welcome email**.
5. UI shows a success message: *"You're on the waitlist!"*

---

### 5.2 — Signing Up (Email & Password)

1. User chooses their role: **Pathfinder** or **Enabler**.
2. User fills in: `first name`, `last name`, `username`, `email`, `password`, `confirm password`.
3. Frontend calls `POST /api/auth/register/`.
4. Backend creates the account (unverified) and sends a **6-digit OTP** to the email.
5. UI shows: *"Check your email for a verification code."*
6. User enters the 6-digit OTP.
7. Frontend calls `POST /api/auth/verify-otp/`.
8. Backend verifies the OTP and returns **access + refresh tokens**.
9. Frontend stores tokens securely and redirects to the **Profile Setup** page.

> ⚠️ **User cannot log in until their email is verified.**

---

### 5.3 — Signing Up (Google)

1. User clicks *"Continue with Google as Pathfinder"* or *"Continue with Google as Enabler"*.
2. Google's popup appears; user selects their Google account.
3. Frontend receives a **Google ID token** from Google.
4. Frontend calls `POST /api/auth/google/pathfinder/` or `POST /api/auth/google/enabler/` with the token.
5. Backend verifies the token with Google, creates or finds the user, and returns **access + refresh tokens**.
6. Frontend stores tokens and redirects to the dashboard (or profile setup if new user).

> ✅ Google users skip the OTP step — their email is trusted by Google.

---

### 5.4 — Logging In

1. User enters **email or username** + **password**.
2. Frontend calls `POST /api/auth/login/`.
3. Backend authenticates the user and returns **access + refresh tokens** + user details (including their `role`).
4. Frontend stores tokens, saves the `role` to know which dashboard to show, and redirects.

> ⚠️ If the user has not verified their email, login will fail with an error.

---

### 5.5 — Forgot Password

1. User clicks *"Forgot Password?"* and enters their email.
2. Frontend calls `POST /api/auth/forgot-password/`.
3. Backend sends a **6-digit OTP** to that email.
4. UI shows: *"A reset code was sent to your email."*
5. User enters the OTP.
6. Frontend calls `POST /api/auth/verify-password-reset-otp/`.
7. Backend verifies OTP and returns the user's `uid` (a number).
8. User enters a new password.
9. Frontend should use the returned `uid` to set the new password *(endpoint to be confirmed with backend team)*.

---

### 5.6 — Profile Setup (Pathfinder)

After first login, the user should be guided to complete their profile:

1. Frontend calls `GET /api/profile/pathfinderprofile/` to load any existing data.
2. User fills in their **title, about, work experience, languages, skills, education, certifications**.
3. User uploads a **profile picture** via `PATCH /api/profile/profile/picture/`.
4. User adds **social media links** via `POST /api/profile/social-links/`.
5. User uploads **credential documents** (e.g., ID, certificates) via `POST /api/profile/credentials/`.
6. When saving, frontend calls `PATCH /api/profile/pathfinderprofile/` with all updated fields.

---

### 5.7 — Profile Setup (Enabler)

1. Frontend calls `GET /api/profile/enablerprofile/` to load existing data.
2. User fills in **organization name, role (e.g., HR Manager), number of employees**.
3. User uploads a **logo/profile picture** via `PATCH /api/profile/profile/picture/`.
4. User adds **social media links** and **contact details**.
5. When saving, frontend calls `PATCH /api/profile/enablerprofile/`.

---

### 5.8 — Browsing Opportunities (Pathfinder)

1. Frontend calls `GET /api/opportunities/` to load the opportunity feed.
2. Results are **paginated** (10 per page by default).
3. User can **filter** by type (job, internship, scholarship, volunteering, grant) and status (open/closed).
4. Filter example: `GET /api/opportunities/?opportunity_type=internship&is_open=true`
5. User can also **search** by keyword: `GET /api/opportunities/?search=marketing`
6. Clicking an opportunity shows its detail page — `GET /api/opportunities/<id>/`.

---

### 5.9 — Applying to an Opportunity (Pathfinder)

1. On the opportunity detail page, user clicks **Apply**.
2. User optionally writes a cover letter and attaches a resume.
3. Frontend calls `POST /api/applications/` with the `opportunity` ID, optional `cover_letter`, optional `resume` file or `profile_resume` (credential ID from their profile).
4. Backend creates the application with **status = "pending"**.
5. UI shows: *"Application submitted!"*

**To view all applications:**
- Frontend calls `GET /api/applications/` — lists all applications this user has submitted.

**To withdraw an application:**
- Only possible if status is still **"pending"**.
- Frontend calls `DELETE /api/applications/<id>/`.

---

### 5.10 — Posting an Opportunity (Enabler)

1. Enabler clicks **"Post New Opportunity"**.
2. Fills in: title, type (job/internship/etc.), description, and a link to the application page (must be HTTPS).
3. Frontend calls `POST /api/opportunities/`.
4. Backend creates the opportunity with `is_open = true`.
5. UI redirects to **"My Opportunities"** page.

**To view their own opportunities:**
- Frontend calls `GET /api/opportunities/mine/`.

**To edit an opportunity:**
- Only possible within **12 hours** of posting.
- Frontend calls `PUT /api/opportunities/<id>/` with updated fields.

**To delete an opportunity:**
- Frontend calls `DELETE /api/opportunities/<id>/`.
- If people have already applied, it becomes **"closed"** rather than fully deleted.

---

### 5.11 — Reviewing Applicants (Enabler)

1. Enabler goes to one of their posted opportunities.
2. Frontend calls `GET /api/opportunities/<id>/applicants/` — lists all people who applied.
3. Enabler clicks on an applicant to view their full profile.
4. Frontend calls `GET /api/opportunities/<id>/applicants/<applicant_id>/`.
5. Enabler decides to accept or reject:
   - Frontend calls `PATCH /api/applications/<application_id>/change_status/` with `{"status": "accepted"}` or `{"status": "rejected"}`.
6. The applicant's status is updated. They can see the change in their **My Applications** page.

---

### 5.12 — Bookmarking

**Pathfinder bookmarks an opportunity:**
1. User clicks the bookmark icon on an opportunity.
2. Frontend calls `POST /api/bookmark/opportunities/saved/` with `{"opportunity": <id>}`.
3. To view all saved opportunities: `GET /api/bookmark/opportunities/saved/`.
4. To remove a bookmark: `DELETE /api/bookmark/opportunities/saved/<opportunity_id>/`.

**Enabler bookmarks a Pathfinder:**
1. Enabler is viewing a pathfinder's profile and clicks *"Save Candidate"*.
2. Frontend calls `POST /api/bookmark/applicants/saved/` with `{"pathfinder": <pathfinder_profile_id>}`.
3. To view saved pathfinders: `GET /api/bookmark/applicants/saved/`.
4. To remove: `DELETE /api/bookmark/applicants/saved/<pathfinder_id>/`.

---

### 5.13 — Notifications

1. Frontend calls `GET /api/notify/notifications/` to load the notifications list.
2. Each notification includes a `current_user_read` flag — use this to show/hide the unread badge.
3. Notifications can be of type: `system`, `server`, or `personal`.
4. Priority levels: `info` (blue), `warning` (yellow), `critical` (red).

---

### 5.14 — Logging Out

1. User clicks **Log Out**.
2. Frontend calls `POST /api/auth/logout/` with the `refresh` token.
3. Backend blacklists the refresh token (it can no longer be used).
4. Frontend **deletes both tokens** from local storage.
5. Redirect to login page.

---

### 5.15 — Token Refresh (Background Process)

The frontend should handle this automatically and invisibly:

1. Access tokens expire every **1 hour**.
2. When an API call returns a `401 Unauthorized` error, it means the access token has expired.
3. The frontend should automatically call `POST /api/auth/token/refresh/` with the `refresh` token.
4. The backend returns a **new access token** (and a new refresh token).
5. Frontend updates the stored tokens and **retries the original request**.
6. If the refresh token is also expired, log the user out and redirect to the login page.

---

## 6. Complete API Reference

> **Base URL:** `https://afrivate-backend-production.up.railway.app`
> **Format:** All requests and responses use **JSON** unless uploading files (multipart/form-data).
> **Authentication:** Add header `Authorization: Bearer <access_token>` to all protected requests.

---

### A. Authentication Endpoints

---

#### `POST /api/auth/register/` — Create a New Account

- **What it does:** Registers a new user and sends a 6-digit OTP to their email for verification.
- **When to call:** When the user submits the Sign Up form.
- **Auth required:** No.

**Request body:**
```json
{
  "username": "jane_doe",
  "email": "jane@example.com",
  "password": "SecurePass123",
  "password2": "SecurePass123",
  "role": "pathfinder",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

> `role` must be either `"pathfinder"` or `"enabler"`.

**Success response (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "username": "jane_doe",
    "email": "jane@example.com",
    "role": "pathfinder",
    "first_name": "Jane",
    "last_name": "Doe"
  }
}
```

**UI states:**
- ⏳ **Loading:** Show spinner while request is in progress.
- ✅ **Success:** Hide form, show "Check your email for a 6-digit code."
- ❌ **Error (400):** Show field-level validation errors (e.g., "Email already exists", "Passwords do not match").
- ❌ **Error (500):** Show generic "Something went wrong, please try again."

---

#### `POST /api/auth/verify-otp/` — Verify Email with OTP

- **What it does:** Confirms the user's email address using the OTP code they received. Returns login tokens on success.
- **When to call:** When the user submits the 6-digit code from their email.
- **Auth required:** No.
- **OTP is valid for 10 minutes.**

**Request body:**
```json
{
  "email": "jane@example.com",
  "otp": "482910"
}
```

**Success response (200 OK):**
```json
{
  "success": true,
  "message": "Email verified successfully",
  "user": {
    "id": 42,
    "username": "jane_doe",
    "email": "jane@example.com",
    "role": "pathfinder"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci..."
}
```

**UI states:**
- ⏳ **Loading:** Disable submit button.
- ✅ **Success:** Store tokens, redirect to dashboard or profile setup.
- ❌ **Error (400):** Show "Invalid or expired code. Please try again." with option to resend.

---

#### `POST /api/auth/login/` — Log In

- **What it does:** Authenticates a user and returns JWT tokens.
- **When to call:** When the user submits the Login form.
- **Auth required:** No.

**Request body:**
```json
{
  "username_or_email": "jane@example.com",
  "password": "SecurePass123"
}
```

> The `username_or_email` field accepts both the username and the email address.

**Success response (200 OK):**
```json
{
  "message": "Login successful",
  "user": {
    "id": 42,
    "username": "jane_doe",
    "email": "jane@example.com",
    "role": "pathfinder",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci..."
}
```

**UI states:**
- ⏳ **Loading:** Disable button, show spinner.
- ✅ **Success:** Store `access` and `refresh` tokens and the user's `role`. Redirect to the correct dashboard based on role.
- ❌ **Error (401):** Show "Incorrect email or password."
- ❌ **Error (403):** Show "Please verify your email before logging in."

---

#### `POST /api/auth/google/pathfinder/` — Google Sign In as Pathfinder
#### `POST /api/auth/google/enabler/` — Google Sign In as Enabler

- **What it does:** Logs in or registers a user using their Google account.
- **When to call:** After the user completes Google's sign-in flow and you receive an `id_token`.
- **Auth required:** No.

**Request body:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

**Success response (200 OK):**
```json
{
  "message": "Google login successful",
  "user": {
    "id": 55,
    "username": "jane_smith",
    "email": "jane@gmail.com",
    "role": "enabler"
  },
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

**UI states:**
- ⏳ **Loading:** Show full-screen loader while processing.
- ✅ **Success:** Store tokens, redirect to dashboard.
- ❌ **Error (400):** Show "Google sign-in failed. Please try again."

---

#### `POST /api/auth/token/refresh/` — Refresh the Access Token

- **What it does:** Issues a new access token using the refresh token. Should be called automatically in the background.
- **When to call:** When any API call returns `401 Unauthorized` (access token expired).
- **Auth required:** No.

**Request body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

**Success response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

> Both a new `access` and `refresh` token are returned. **Save both.**

**UI states:**
- This happens silently — no UI changes needed unless it fails.
- ❌ **Error (401):** Refresh token is expired → log the user out and redirect to login.

---

#### `POST /api/auth/logout/` — Log Out

- **What it does:** Invalidates the refresh token so it can't be reused.
- **When to call:** When the user clicks "Log Out."
- **Auth required:** Yes (access token).

**Request body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}
```

**Success response (200 OK):**
```json
{
  "message": "Logout successful"
}
```

**UI states:**
- ✅ **Success:** Delete both tokens from storage, redirect to login page.
- ❌ **Error:** Even on error, clear local tokens and redirect to login.

---

#### `POST /api/auth/forgot-password/` — Request Password Reset

- **What it does:** Sends a 6-digit OTP to the user's email so they can reset their password.
- **When to call:** When the user submits the "Forgot Password" form.
- **Auth required:** No.

**Request body:**
```json
{
  "email": "jane@example.com"
}
```

**Success response (200 OK):**
```json
{
  "success": true,
  "message": "If an account with that email exists, a reset code has been sent."
}
```

> ⚠️ The message is intentionally vague — it does not reveal whether the email exists. This is a security best practice.

**UI states:**
- ✅ **Success:** Show "Check your email for a reset code" regardless of whether the email exists.
- ❌ **Error (400):** Show "Please enter a valid email address."

---

#### `POST /api/auth/verify-password-reset-otp/` — Verify Password Reset OTP

- **What it does:** Checks if the OTP entered for password reset is valid, and returns the user's `uid` if so.
- **When to call:** After the user submits the OTP code from their reset email.
- **Auth required:** No.

**Request body:**
```json
{
  "email": "jane@example.com",
  "otp": "731024"
}
```

**Success response (200 OK):**
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "uid": 42
}
```

**UI states:**
- ✅ **Success:** Save the `uid`, then show the "Set New Password" screen.
- ❌ **Error (400):** Show "Invalid or expired code."

---

#### `POST /api/auth/change-password/` — Change Password (Logged In)

- **What it does:** Lets an authenticated user update their password.
- **When to call:** When the user submits the "Change Password" form in account settings.
- **Auth required:** Yes.

**Request body:**
```json
{
  "old_password": "OldPass123",
  "new_password": "NewPass456",
  "confirm_password": "NewPass456"
}
```

**Success response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**UI states:**
- ✅ **Success:** Show "Password updated!" and optionally log the user out and ask them to log in again.
- ❌ **Error (400):** Show "Current password is incorrect" or "Passwords do not match."

---

#### `POST /api/auth/set-password/` — Set Password (Google Users)

- **What it does:** Allows users who signed up with Google to also set an email/password for their account.
- **When to call:** When a Google user opts to also enable email/password login.
- **Auth required:** Yes.

**Request body:**
```json
{
  "new_password": "MyNewPass123",
  "confirm_password": "MyNewPass123"
}
```

**Success response (200 OK):**
```json
{
  "message": "Password set successfully. You can now login with email and password."
}
```

---

### B. Profile Endpoints

---

#### `GET /api/profile/pathfinderprofile/` — Get My Profile (Pathfinder)

- **What it does:** Returns the logged-in Pathfinder's full profile data.
- **When to call:** When loading the profile page or the profile edit form.
- **Auth required:** Yes (Pathfinder role).

**Success response (200 OK):**
```json
{
  "id": 12,
  "user": 42,
  "first_name": "Jane",
  "last_name": "Doe",
  "title": "Software Engineer",
  "about": "Passionate developer from Lagos...",
  "work_experience": "2 years at TechCorp...",
  "languages": "English, French",
  "bio": "Short bio here...",
  "contact_email": "jane@example.com",
  "phone_number": "+2348012345678",
  "address": "15 Broad Street",
  "state": "Lagos",
  "country": "Nigeria",
  "website": "https://janedoe.dev",
  "profile_pic": "https://res.cloudinary.com/...",
  "social_links": [
    { "id": 1, "platform_name": "LinkedIn", "platform_url": "https://linkedin.com/in/janedoe" }
  ],
  "credentials": [
    { "id": 3, "document_name": "National ID", "document": "https://res.cloudinary.com/...", "is_verified": false }
  ]
}
```

---

#### `PATCH /api/profile/pathfinderprofile/` — Update My Profile (Pathfinder)

- **What it does:** Updates one or more fields on the Pathfinder's profile.
- **When to call:** When the user saves changes on the profile edit form.
- **Auth required:** Yes (Pathfinder role).

**Request body (only include fields you want to update):**
```json
{
  "title": "Senior Software Engineer",
  "about": "Updated bio...",
  "languages": "English, Yoruba, French"
}
```

**Success response (200 OK):** Full updated profile object (same structure as GET above).

**UI states:**
- ✅ **Success:** Show "Profile saved!" toast notification.
- ❌ **Error (400):** Show inline field errors.

---

#### `GET /api/profile/enablerprofile/` — Get My Profile (Enabler)

- **What it does:** Returns the logged-in Enabler's organization profile.
- **When to call:** On the Enabler's profile page.
- **Auth required:** Yes (Enabler role).

**Success response (200 OK):**
```json
{
  "id": 7,
  "user": 55,
  "name": "TechCorp Africa",
  "employees": 150,
  "role": "Hiring Manager",
  "bio": "We build great products...",
  "contact_email": "hr@techcorp.africa",
  "phone_number": "+2348011112222",
  "address": "Plot 5, Victoria Island",
  "state": "Lagos",
  "country": "Nigeria",
  "website": "https://techcorp.africa",
  "profile_pic": "https://res.cloudinary.com/...",
  "social_links": []
}
```

---

#### `PATCH /api/profile/enablerprofile/` — Update My Profile (Enabler)

- **What it does:** Updates the Enabler's organization profile.
- **When to call:** When the Enabler saves changes on their profile form.
- **Auth required:** Yes (Enabler role).

**Request body (only include fields to update):**
```json
{
  "name": "TechCorp Africa Ltd.",
  "employees": 200
}
```

---

#### `GET/PATCH /api/profile/profile/picture/` — Get or Update Profile Picture

- **What it does:** Retrieves the current profile picture URL, or uploads a new one.
- **When to call:** On profile picture load (GET) or when user uploads/changes their photo (PATCH).
- **Auth required:** Yes.
- **File format:** JPEG, JPG, PNG, or WEBP only. Max size: 5 MB.
- **Content-Type:** `multipart/form-data` (not JSON).

**PATCH request:**
```
profile_pic: [image file]
```

**Success response (200 OK):**
```json
{
  "profile_pic": "https://res.cloudinary.com/afrivate/image/upload/..."
}
```

**UI states:**
- ⏳ **Loading:** Show upload progress bar.
- ✅ **Success:** Display the new profile photo immediately.
- ❌ **Error:** Show "File too large" or "Unsupported format."

---

#### `GET /api/profile/pathfinderprofile/user/<user_id>/` — View Another Pathfinder's Profile

- **What it does:** Returns the public profile of any Pathfinder by their user ID.
- **When to call:** When an Enabler clicks on a Pathfinder's name.
- **Auth required:** Yes.

---

#### `GET /api/profile/enablerprofile/user/<user_id>/` — View Another Enabler's Profile

- **What it does:** Returns the public profile of any Enabler by their user ID.
- **When to call:** When a Pathfinder clicks on an Enabler's name on an opportunity.
- **Auth required:** Yes.

---

#### `GET /api/profile/credentials/` — List My Credentials

- **What it does:** Returns a list of all uploaded credential documents (IDs, certificates, etc.).
- **When to call:** On the credentials section of the profile page.
- **Auth required:** Yes.

**Success response (200 OK):**
```json
[
  {
    "id": 3,
    "document_name": "National ID",
    "document": "https://res.cloudinary.com/...",
    "is_verified": false,
    "profile": 12
  }
]
```

---

#### `POST /api/profile/credentials/` — Upload a Credential

- **What it does:** Uploads a new credential document.
- **When to call:** When the user clicks "Add Document."
- **Auth required:** Yes.
- **Content-Type:** `multipart/form-data`.

**Request:**
```
document_name: "University Degree"
document: [file]
```

**UI states:**
- ⏳ **Loading:** Show file upload progress.
- ✅ **Success:** Add the new credential to the list.
- ❌ **Error:** Show error message if file is too large or unsupported.

---

#### `DELETE /api/profile/credentials/<id>/` — Remove a Credential

- **What it does:** Deletes a credential document.
- **Auth required:** Yes.

---

#### `GET /api/profile/social-links/` — List Social Links

- **What it does:** Returns all social media links on the user's profile.
- **Auth required:** Yes.

---

#### `POST /api/profile/social-links/` — Add a Social Link

- **What it does:** Adds a new social media link.
- **Auth required:** Yes.

**Request body:**
```json
{
  "platform_name": "GitHub",
  "platform_url": "https://github.com/janedoe"
}
```

---

#### `DELETE /api/profile/social-links/<id>/` — Remove a Social Link

- **What it does:** Removes a social link.
- **Auth required:** Yes.

---

### C. Opportunities Endpoints

---

#### `GET /api/opportunities/` — Browse All Opportunities

- **What it does:** Returns a paginated list of all opportunities.
- **When to call:** On the main Opportunities Feed page, and whenever filters are changed.
- **Auth required:** No (anyone can browse, even unauthenticated).

**Query parameters (all optional):**

| Parameter | Values | Example |
|---|---|---|
| `opportunity_type` | job, internship, volunteering, scholarship, grant | `?opportunity_type=job` |
| `is_open` | true, false | `?is_open=true` |
| `search` | any keyword | `?search=marketing` |
| `page` | page number | `?page=2` |
| `page_size` | items per page (max 100) | `?page_size=20` |

**Example request:**
```
GET /api/opportunities/?opportunity_type=internship&is_open=true&page=1
```

**Success response (200 OK):**
```json
{
  "count": 48,
  "next": "https://.../api/opportunities/?page=2",
  "previous": null,
  "results": [
    {
      "id": 101,
      "title": "Marketing Intern at TechCorp",
      "opportunity_type": "internship",
      "description": "We are looking for a creative marketing intern...",
      "link": "https://techcorp.africa/apply",
      "posted_at": "2025-04-01T10:00:00Z",
      "is_open": true,
      "created_by": 55,
      "created_by_name": "TechCorp Africa"
    }
  ]
}
```

**UI states:**
- ⏳ **Loading:** Show skeleton cards while loading.
- ✅ **Success:** Render the list with pagination controls.
- 📭 **Empty state:** Show "No opportunities found. Try a different filter."
- ❌ **Error:** Show "Failed to load opportunities. Please refresh."

---

#### `GET /api/opportunities/<id>/` — View One Opportunity

- **What it does:** Returns the full details of a single opportunity.
- **When to call:** When the user clicks on an opportunity card.
- **Auth required:** No.

**Success response (200 OK):** Same structure as above, single object.

---

#### `POST /api/opportunities/` — Post a New Opportunity

- **What it does:** Creates a new opportunity posting.
- **When to call:** When an Enabler submits the "Post Opportunity" form.
- **Auth required:** Yes (Enabler role required).

**Request body:**
```json
{
  "title": "Volunteer Community Manager",
  "opportunity_type": "volunteering",
  "description": "We need a passionate community manager to help...",
  "link": "https://ourorg.africa/volunteer"
}
```

> ⚠️ The `link` field must start with `https://`.
> ⚠️ `opportunity_type` must be one of: `job`, `internship`, `volunteering`, `scholarship`, `grant`.

**Success response (201 Created):** The new opportunity object.

**UI states:**
- ✅ **Success:** Redirect to the new opportunity's detail page or "My Opportunities."
- ❌ **Error (400):** Show inline form errors.
- ❌ **Error (403):** User is not an Enabler — hide this form from Pathfinders entirely.

---

#### `PUT /api/opportunities/<id>/` — Edit an Opportunity

- **What it does:** Updates an existing opportunity.
- **When to call:** When an Enabler edits their posting.
- **Auth required:** Yes (must be the Enabler who created it, within 12 hours of posting).

**Request body:** Same as POST above (all fields required for PUT).

**UI states:**
- ❌ **Error (403):** "You can only edit an opportunity within 12 hours of posting."
- ❌ **Error (403):** "You can only edit your own opportunities."

> 💡 **UI Tip:** Hide or disable the "Edit" button if more than 12 hours have passed since posting.

---

#### `DELETE /api/opportunities/<id>/` — Delete an Opportunity

- **What it does:** Removes an opportunity. If people have applied, it's marked as "closed" instead of deleted.
- **When to call:** When the Enabler clicks "Delete" on their own posting.
- **Auth required:** Yes (must be the creator).

**UI states:**
- ✅ **Success:** Remove the item from the list.
- ❌ **Error (403):** "You can only delete your own opportunities."

---

#### `GET /api/opportunities/mine/` — My Posted Opportunities (Enabler)

- **What it does:** Returns all opportunities posted by the logged-in Enabler.
- **When to call:** On the Enabler's "My Opportunities" dashboard page.
- **Auth required:** Yes (Enabler role).

---

#### `GET /api/opportunities/<id>/applicants/` — List Applicants for an Opportunity

- **What it does:** Returns all applications submitted for a specific opportunity.
- **When to call:** When the Enabler clicks "View Applicants" on their posting.
- **Auth required:** Yes (must be the opportunity creator).

**Success response (200 OK):**
```json
[
  {
    "id": 201,
    "user_id": 42,
    "user_email": "jane@example.com",
    "cover_letter": "Dear Hiring Team...",
    "status": "pending",
    "applied_at": "2025-04-02T14:30:00Z"
  }
]
```

---

#### `GET /api/opportunities/<id>/applicants/<applicant_id>/` — View Applicant's Full Profile

- **What it does:** Returns the complete Pathfinder profile for a specific applicant, including their skills, education, certifications, and credentials.
- **When to call:** When the Enabler clicks on an applicant's name.
- **Auth required:** Yes (must be the opportunity creator).

---

### D. Applications Endpoints

---

#### `GET /api/applications/` — My Applications

- **What it does:**
  - **For Pathfinders:** Returns a list of all applications the user has submitted.
  - **For Enablers:** Returns all applications received for their opportunities.
- **When to call:** On the "My Applications" page.
- **Auth required:** Yes.

**Success response (200 OK):**
```json
[
  {
    "id": 201,
    "user": 42,
    "opportunity": 101,
    "cover_letter": "Dear Hiring Team...",
    "status": "pending",
    "resume": "https://res.cloudinary.com/...",
    "applied_at": "2025-04-02T14:30:00Z",
    "reviewed_at": null
  }
]
```

**Possible `status` values:**

| Status | Meaning | Badge Color (suggested) |
|---|---|---|
| `pending` | Not yet reviewed | Yellow |
| `accepted` | Application accepted | Green |
| `rejected` | Application rejected | Red |

---

#### `POST /api/applications/` — Submit an Application

- **What it does:** Creates a new job application.
- **When to call:** When a Pathfinder clicks "Apply" and submits the form.
- **Auth required:** Yes (Pathfinder role).
- **Content-Type:** `multipart/form-data` if uploading a resume file; otherwise `application/json`.

**Request body:**
```json
{
  "opportunity": 101,
  "cover_letter": "Dear Hiring Manager, I am excited to apply...",
  "profile_resume": 3
}
```

> `profile_resume` is the `id` of a Credential the user has already uploaded. This is an alternative to uploading a new resume file.

**Or with a file:**
```
opportunity: 101
cover_letter: "Dear Hiring Manager..."
resume: [PDF file]
```

**Success response (201 Created):** The new application object.

**UI states:**
- ✅ **Success:** Show "Application submitted! We'll notify you of updates."
- ❌ **Error (400):** "You have already applied to this opportunity."
- ❌ **Error (403):** Only Pathfinders can apply.

---

#### `DELETE /api/applications/<id>/` — Withdraw an Application

- **What it does:** Removes a submitted application.
- **When to call:** When the Pathfinder clicks "Withdraw Application."
- **Auth required:** Yes (must be the applicant).
- **Only possible if application status is "pending".**

**UI states:**
- ✅ **Success:** Remove the application from the list.
- ❌ **Error (400):** "You cannot withdraw an application that has already been reviewed."

---

#### `PATCH /api/applications/<id>/change_status/` — Accept or Reject an Application

- **What it does:** Changes the status of an application to `accepted` or `rejected`.
- **When to call:** When the Enabler clicks "Accept" or "Reject" on an applicant.
- **Auth required:** Yes (Enabler role, must be the opportunity creator).

**Request body:**
```json
{
  "status": "accepted"
}
```

**Success response (200 OK):**
```json
{
  "message": "Application marked as accepted"
}
```

**UI states:**
- ✅ **Success:** Update the applicant's status badge in the list.
- ❌ **Error (403):** "You can only review applicants for your own opportunities."

---

### E. Bookmark Endpoints

---

#### `GET /api/bookmark/opportunities/saved/` — My Saved Opportunities

- **What it does:** Returns all opportunities the logged-in Pathfinder has bookmarked.
- **When to call:** On the "Saved" tab or bookmarks page.
- **Auth required:** Yes.

---

#### `POST /api/bookmark/opportunities/saved/` — Save an Opportunity

- **What it does:** Bookmarks an opportunity for later.
- **When to call:** When the user clicks the bookmark icon on an opportunity.
- **Auth required:** Yes.

**Request body:**
```json
{
  "opportunity": 101
}
```

**Success response (201 Created):**
```json
{
  "id": 5,
  "user": 42,
  "opportunity": 101,
  "created_at": "2025-04-03T09:00:00Z"
}
```

**UI states:**
- ✅ **Success:** Fill/highlight the bookmark icon.
- ❌ **Error (400):** Already bookmarked — treat this as "already saved" silently.

---

#### `DELETE /api/bookmark/opportunities/saved/<opportunity_id>/` — Remove a Saved Opportunity

- **What it does:** Removes a bookmark.
- **When to call:** When the user un-bookmarks an opportunity.
- **Auth required:** Yes.

**Success response:** `204 No Content` (no response body).

---

#### `GET /api/bookmark/applicants/saved/` — My Saved Pathfinders (Enabler)

- **What it does:** Returns all Pathfinders the Enabler has bookmarked.
- **When to call:** On the Enabler's "Saved Candidates" page.
- **Auth required:** Yes (Enabler role).

---

#### `POST /api/bookmark/applicants/saved/` — Bookmark a Pathfinder (Enabler)

- **What it does:** Saves a Pathfinder to the Enabler's list of interesting candidates.
- **When to call:** When the Enabler clicks "Save Candidate" on a Pathfinder's profile.
- **Auth required:** Yes (Enabler role).

**Request body:**
```json
{
  "pathfinder": 12
}
```

> `pathfinder` is the Pathfinder's **profile ID** (not their user ID).

---

#### `DELETE /api/bookmark/applicants/saved/<pathfinder_id>/` — Remove a Saved Pathfinder (Enabler)

- **What it does:** Removes a Pathfinder from saved candidates.
- **Auth required:** Yes (Enabler role).

---

### F. Notifications Endpoints

---

#### `GET /api/notify/notifications/` — Get All Notifications

- **What it does:** Returns a list of all platform notifications.
- **When to call:** On the notifications page, or when the notification bell is clicked.
- **Auth required:** No (public) — but `current_user_read` flag requires auth context.

**Success response (200 OK):**
```json
[
  {
    "id": 10,
    "title": "New opportunities available!",
    "message": "5 new internships have been posted this week.",
    "priority": "info",
    "type": "system",
    "link": "https://afrivate.org/opportunities",
    "created_at": "2025-04-01T08:00:00Z",
    "current_user_read": false
  }
]
```

**`priority` values and suggested UI treatment:**

| Priority | Suggested Style |
|---|---|
| `info` | Blue badge / info icon |
| `warning` | Yellow badge / warning icon |
| `critical` | Red badge / alert icon |

**`type` values:**

| Type | Meaning |
|---|---|
| `system` | Platform-wide announcements |
| `server` | Technical/maintenance messages |
| `personal` | Directed at a specific user |

**UI states:**
- Show a **red dot/badge** on the bell icon if any notification has `current_user_read: false`.
- Mark notifications as read when the user views them.

---

### G. Waitlist Endpoints

---

#### `POST /api/waitlist/` — Join the Waitlist

- **What it does:** Adds an email to the pre-launch waitlist and sends a welcome email.
- **When to call:** When the user submits the waitlist/landing page form.
- **Auth required:** No.

**Request body:**
```json
{
  "email": "earlyuser@example.com",
  "name": "Alex Tunde",
  "referral_source": "Twitter"
}
```

> `name` and `referral_source` are optional.

**Success response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully signed up for the waitlist!",
  "email": "earlyuser@example.com"
}
```

**UI states:**
- ✅ **Success:** Show a thank-you message: *"You're on the list! We'll email you when we launch."*
- ❌ **Error (400):** Email already registered — show "You're already on the waitlist!"

---

#### `GET /api/waitlist/stats/` — Waitlist Statistics (Admin)

- **What it does:** Returns aggregate stats on waitlist signups.
- **When to call:** On the admin/analytics dashboard.
- **Auth required:** No.

**Success response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_waitlist": 1240,
    "verified_count": 980,
    "unverified_count": 260
  }
}
```

---

## 7. Business Rules for the Project Manager

> These are the important rules baked into the system that affect how the product works. Keep these in mind when making product decisions.

### User & Account Rules

- 📌 **One role per account.** Users pick either Pathfinder or Enabler at signup. This cannot be changed later.
- 📌 **Email verification is mandatory.** A user cannot log in without verifying their email first.
- 📌 **OTP codes expire in 10 minutes.** Users must enter the code quickly or request a new one.
- 📌 **Temporary email addresses are blocked.** The system rejects signups from known throwaway email services (e.g., mailinator.com, tempmail.com).

### Opportunity Rules

- 📌 **Only Enablers can post opportunities.** Pathfinders can browse and apply, but never create listings.
- 📌 **Opportunities can only be edited within 12 hours of posting.** After that, the posting is locked.
- 📌 **Deleting an opportunity with existing applicants closes it** instead of removing it. This protects applicants from losing their application history.
- 📌 **Opportunity links must be secure (HTTPS).** Plain HTTP links are rejected.
- 📌 **Opportunity types are fixed.** Must be one of: `job`, `internship`, `volunteering`, `scholarship`, `grant`.

### Application Rules

- 📌 **One application per opportunity per user.** A Pathfinder cannot apply twice to the same opportunity.
- 📌 **Only Pathfinders can apply.** Enablers cannot submit applications.
- 📌 **Applications can only be withdrawn if still "pending".** Once accepted or rejected, withdrawal is not allowed.
- 📌 **Only the opportunity creator (Enabler) can change application status.** Other Enablers cannot review applications they don't own.

### Bookmark Rules

- 📌 **Pathfinders bookmark opportunities; Enablers bookmark Pathfinders.** These are two separate systems.
- 📌 **No duplicate bookmarks.** Trying to bookmark something you've already bookmarked will return an error.

### Token & Session Rules

- 📌 **Access tokens expire in 1 hour.** The frontend must refresh them automatically using the refresh token.
- 📌 **Refresh tokens expire in 1 day.** After this, the user must log in again.
- 📌 **Tokens are invalidated on logout.** A logged-out refresh token cannot be reused.
- 📌 **Google OAuth users can add email/password later.** This is optional, using the `set-password` endpoint.

### File & Upload Rules

- 📌 **Profile pictures max 5 MB.** Formats: JPEG, JPG, PNG, WEBP.
- 📌 **All files are stored on Cloudinary** (a cloud CDN), not on the server itself.

---

## 8. Frontend Developer Notes

### Token Management

Store the `access` and `refresh` tokens securely (ideally in `httpOnly` cookies, or in-memory + sessionStorage as a fallback). Never store them in `localStorage` unless absolutely necessary.

Always include the access token in protected requests:
```
Authorization: Bearer <access_token>
```

Implement a **token refresh interceptor** that:
1. Catches any `401` error.
2. Calls `POST /api/auth/token/refresh/` automatically.
3. Retries the original failed request with the new token.
4. If the refresh also fails (expired/blacklisted), logs the user out.

---

### Role-Based UI

After login, read the `role` field from the response (`"pathfinder"` or `"enabler"`). Use this to:
- Show/hide the **"Post Opportunity"** button (Enabler only).
- Show/hide the **"Apply"** button (Pathfinder only).
- Show/hide the **"View Applicants"** section (Enabler only).
- Show/hide the **"My Applications"** tab (Pathfinder only).
- Show/hide the **"Saved Candidates"** section (Enabler only).

---

### Pagination

Opportunity listings are paginated. The response includes:
```json
{
  "count": 48,
  "next": "https://.../api/opportunities/?page=2",
  "previous": null,
  "results": [...]
}
```

Implement **infinite scroll** or **page navigation** using the `next` and `previous` URLs, or the `page` query parameter.

---

### File Uploads

When uploading files (profile pictures, credentials, resumes), use `multipart/form-data` as the `Content-Type`, **not** `application/json`.

---

### Error Handling Pattern

All error responses follow this general format:
```json
{
  "field_name": ["Error message here."],
  "non_field_errors": ["Error message for the whole form."]
}
```

Map field-level errors to the correct input fields. Show `non_field_errors` as a top-level alert.

---

### API Documentation

Live, interactive API documentation is available at:
- **Swagger UI:** `https://afrivate-backend-production.up.railway.app/api/v1/docs/`
- **ReDoc:** `https://afrivate-backend-production.up.railway.app/docs/`

These tools let you test every endpoint directly in the browser.

---

### Background Email Delays

Emails (OTPs, welcome messages) are sent **synchronously** on the server. This means:
- After calling `/api/auth/register/`, the OTP email might take a few seconds.
- Show a message like *"Email may take a few seconds to arrive."*
- Provide a **"Resend OTP"** option after a short timeout (e.g., 60 seconds).

---

### Quick Reference: Which Endpoints Need a Token?

| 🔓 No Token Required | 🔑 Token Required |
|---|---|
| `GET /api/opportunities/` | All profile endpoints |
| `POST /api/auth/register/` | `POST /api/applications/` |
| `POST /api/auth/login/` | `PATCH /api/applications/<id>/change_status/` |
| `POST /api/auth/verify-otp/` | `POST /api/bookmark/...` |
| `POST /api/auth/forgot-password/` | `DELETE /api/bookmark/...` |
| `POST /api/auth/token/refresh/` | `POST /api/auth/logout/` |
| `POST /api/auth/google/...` | `POST /api/auth/change-password/` |
| `POST /api/waitlist/` | `POST /api/opportunities/` (Enabler) |
| `GET /api/notify/notifications/` | All other write operations |

---

*Document prepared for the Afrivate Technology team. For questions or updates, contact the backend team.*
