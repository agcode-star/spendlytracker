# Spec: Registration

## Overview
This feature turns the existing `/register` page into a working sign-up flow. Today `GET /register` only renders `register.html`, and the form's `POST` has no handler. This step adds `POST /register` so a visitor can create a real account: the server validates the submitted name, email, and password, hashes the password with werkzeug, and inserts a new row into the `users` table via a dedicated helper in `database/db.py`. It is the first authentication step in the Spendly roadmap (after the Step 1 database setup) and is a prerequisite for login, logout, and every logged-in feature that follows.

## Depends on
- **Step 1 — Database setup** (complete): `get_db()`, `init_db()`, and the `users` table must exist. This step relies on that schema and the `email UNIQUE` constraint.

## Routes
- `GET /register` — render the registration form — public *(already implemented; remains unchanged)*
- `POST /register` — validate input, create the user, redirect to login — public *(new behavior)*

## Database changes
No database changes. The `users` table from Step 1 already has every required column (`name`, `email`, `password_hash`, `created_at`) and the `email UNIQUE` constraint. Two new **helper functions** are added to `database/db.py` (no schema change):
- `get_user_by_email(email)` — return the user row for an email, or `None`.
- `create_user(name, email, password_hash)` — insert a user and return the new id.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/register.html` — change the hardcoded `action="/register"` to `url_for('register')` to comply with the no-hardcoded-URL rule. The existing `{% if error %}` block is already present and will display server-side validation errors; preserve submitted `name`/`email` values on re-render so the user does not retype them.

## Files to change
- `app.py` — extend the `register` route to accept `methods=["GET", "POST"]` and handle the POST branch (validate, hash, create user, redirect, or re-render with an error).
- `database/db.py` — add `get_user_by_email()` and `create_user()` helpers.
- `templates/register.html` — use `url_for('register')` for the form action and repopulate fields on error.

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security.generate_password_hash` (already a dependency) and the standard library.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — never f-strings or string concatenation in SQL.
- Passwords hashed with werkzeug (`generate_password_hash`) — never store plaintext.
- All DB access goes through helpers in `database/db.py` — no inline SQL in the route.
- Use CSS variables — never hardcode hex values (no template/style changes should introduce raw hex).
- All templates extend `base.html`.
- Use `url_for()` for every internal link and form action.
- Use `abort()` for HTTP errors, not bare string returns.
- Validation lives in the route (one responsibility: validate → delegate to db helper → render/redirect):
  - All three fields required and non-empty after trimming.
  - Basic email shape check; password minimum length 8 (matches the form's placeholder).
  - Duplicate email → re-render the form with a friendly error, not a 500.

## Definition of done
- [ ] Submitting the registration form with valid, unused details creates exactly one new row in `users` with a hashed (non-plaintext) `password_hash`.
- [ ] After a successful registration the user is redirected to the login page (`GET /login`).
- [ ] Submitting an email that already exists re-renders `register.html` with a visible error and does **not** create a duplicate row.
- [ ] Submitting with any field blank re-renders the form with an error and creates no row.
- [ ] On any validation error the previously entered name and email remain pre-filled.
- [ ] The form's action and the "Sign in" link both resolve via `url_for()` (no hardcoded paths).
- [ ] `GET /register` still renders the form unchanged.
- [ ] App starts and the full flow works on port 5001 with no errors in the console.
