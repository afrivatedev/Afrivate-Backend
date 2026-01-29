# Routes Requiring API or Connection Functionality

This document lists all routes that depend on an external API, backend service, or connection (e.g. localStorage) and what each requires.

---

## Routes Requiring Backend API

### `/login` (Login.js)
- **API:** `POST https://afrivate-backend-test.onrender.com/api/auth/login/`
- **Payload:** `{ username_or_email, password }`
- **Functionality:** User authentication; returns `access` token.
- **Connection:** Saves `token` to `localStorage` on success; redirects to `/dashf`.

### `/signup` (SignUp.js)
- **API:** `POST https://afrivate-backend-test.onrender.com/api/auth/register/`
- **Payload:** `username`, `email`, `first_name`, `last_name`, `password`, `password2`, `role` (enabler or pathfinder).
- **Functionality:** User registration.
- **Connection:** Sets `hasCompletedProfile` and optionally `hasCompletedEnablerProfile` in localStorage; redirects to `/enabler/profile-setup` (enabler) or `/edit-new-profile` (pathfinder).

---

## Routes Using localStorage (No Backend Call on Load)

### `/edit-new-profile` (EditNewProfile.js)
- **Functionality:** Pathfinder profile form.
- **Connection:** Writes `userProfile` and `hasCompletedProfile` to localStorage on save; no API call. Redirects to `/pathf` after save.

### `/bookmarks` (Bookmarks.js)
- **Functionality:** List of bookmarked opportunities.
- **Connection:** Reads/writes `bookmarkedJobsData` and `bookmarkedJobs` in localStorage. No API; data is local only.

### `/volunteer-details` (VolunteerDetails.js)
- **Functionality:** Single volunteer/opportunity detail and bookmark toggle.
- **Connection:** Reads/writes `bookmarkedJobs` and `bookmarkedJobsData` in localStorage. No API for opportunity data (assumed from route state or local data).

### `/create-opportunity` (CreateOpportunity.js)
- **Functionality:** Enabler creates a new opportunity.
- **Connection:** Reads/updates `enablerOpportunities` in localStorage. No backend API; opportunities are stored locally.

### `/enabler/opportunity/:id` (OpportunityDetails.js)
- **Functionality:** View/edit single opportunity.
- **Connection:** Reads `enablerOpportunities` from localStorage; no API for opportunity fetch.

### `/enabler/dashboard` (EnablerDashboard.js)
- **Functionality:** Enabler dashboard with analytics and applicants.
- **Connection:** Reads `enablerOpportunities` from localStorage for opportunity list. Analytics/applicants are sample or local; no API specified.

### `/enabler/profile-setup` (EnablerProfileSetup.js)
- **Functionality:** Enabler onboarding profile form.
- **Connection:** Writes `enablerProfile` and `hasCompletedEnablerProfile` to localStorage on save; no API call.

### `/enabler/opportunities-posted` (OpportunitiesPosted.js)
- **Functionality:** List of opportunities posted by enabler.
- **Connection:** Full CRUD on `enablerOpportunities` in localStorage; sample data can be seeded. No API.

### `/enabler/pathfinder/:id` (PathfinderProfile.js)
- **Functionality:** View pathfinder profile and bookmark pathfinder.
- **Connection:** Reads/writes `bookmarkedPathfinders` in localStorage. Pathfinder data is sample/mock; comment says “in production would come from an API.”

---

## Routes With Placeholder / Future API

### `/profile` (Profile.js)
- **Functionality:** User profile view/edit.
- **Connection:** Comment indicates “API call to update the profile” would be added; currently no fetch.

### `/verify-otp` (VerifyOTP.js)
- **Functionality:** OTP verification step.
- **Connection:** “Simulate API call”; no real API wired.

### `/forgot-password`, `/reset-password`
- **Functionality:** Password reset flow.
- **Connection:** Not audited in this list; assume backend endpoints would be required for production.

### `/enabler/applicants/:id` (Applicants.js)
- **Functionality:** List applicants for an opportunity.
- **Connection:** Comment: “in production, this would come from an API”; currently sample data.

### `UserContext.js`
- **Functionality:** Global user state.
- **Connection:** Comment: “API call to get user data” / “Simulate API call”; no real API.

---

## Summary Table

| Route | API / Backend | localStorage | Notes |
|-------|----------------|--------------|--------|
| `/login` | ✅ Auth API | ✅ token | Afrivate backend |
| `/signup` | ✅ Register API | ✅ flags | Afrivate backend |
| `/edit-new-profile` | ❌ | ✅ profile | Local only |
| `/bookmarks` | ❌ | ✅ bookmarks | Local only |
| `/volunteer-details` | ❌ | ✅ bookmarks | Local only |
| `/create-opportunity` | ❌ | ✅ opportunities | Local only |
| `/enabler/opportunity/:id` | ❌ | ✅ opportunities | Local only |
| `/enabler/dashboard` | ❌ | ✅ opportunities | Local only |
| `/enabler/profile-setup` | ❌ | ✅ profile | Local only |
| `/enabler/opportunities-posted` | ❌ | ✅ opportunities | Local only |
| `/enabler/pathfinder/:id` | ❌ (future API) | ✅ bookmarks | Sample data |
| `/enabler/applicants/:id` | ❌ (future API) | ❌ | Sample data |
| `/profile` | ❌ (future API) | ❌ | Placeholder |
| `/verify-otp` | ❌ (simulated) | ❌ | Placeholder |

---

## Backend Base URL

- **Auth (login/register):** `https://afrivate-backend-test.onrender.com/api/auth/`

No other backend base URLs are currently used in the codebase for these routes.
