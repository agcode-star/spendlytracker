# Spec: Login and Logout

## Overview
This feature makes Spendly accounts usable by adding real session-based authentication. Today `GET /login` only renders a form, the form's `POST` has no handler, and `/logout` is a stub string — so a registered user can never actually sign in. This step adds `POST /login` (verify email + password against the `users` table, then establish a server-side session), implements `/logout` (clear the session), introduces an `app.secret_key` so Flask sessions work, and makes the shared navbar reflect logged-in vs logged-out state. It is the second authentication step in the roadmap (after Step 2 registration) and the prerequisite for every logged-in feature that follows (profile, expenses).

## Depends on
- **Step 1 — Database setup** (complete): `users` table and `get_db()`.
- **Step 2 — Registration** (complete): accounts to log in with, plus the `get_user_by_email()` helper and the lowercase-email convention, both reused here.

## Routes
- `GET /login` — render the login form — public *(already implemented; unchanged)*
- `POST /login` — verify credentials, set the session, redirect to the landing page — public *(new behavior)*
- `GET /logout` — clear the session and redirect to the landing page — logged-in *(replaces the current stub; harmless if already logged out)*

> `/logout` stays a `GET` route to match the CLAUDE.md roadmap (`GET /logout`) and the existing anchor-link navbar.

## Database changes
No database changes. Login reads via the existing `get_user_by_email()` helper and verifies the stored hash with `werkzeug.security.check_password_hash` — no new tables, columns, or helpers required.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/login.html` — change the hardcoded `action="/login"` to `url_for('login')`; repopulate the `email` field on error (never the password); the existing `{% if error %}` block already displays the message.
  - `templates/base.html` — make the navbar conditional on `session`: when logged in, show the user's name and a "Sign out" link (`url_for('logout')`); when logged out, keep the current "Sign in" / "Get started" links. Replace the hardcoded footer `/terms` and `/privacy` hrefs with `url_for()` while editing this file (existing convention violation).

## Files to change
- `app.py` — set `app.secret_key`; extend `login` to `methods=["GET", "POST"]` with credential verification; implement `logout` to clear the session. Import `session`, `flash` is **not** needed (inline `error=` re-render, consistent with registration).
- `templates/login.html` — `url_for` action + email repopulation.
- `templates/base.html` — session-aware navbar (+ footer `url_for` cleanup).

## Files to create
- `tests/test_login.py` — login/logout flow tests (reuses the `client` fixture added in Step 2).

## New dependencies
No new dependencies. Uses `flask.session`, `werkzeug.security.check_password_hash` (already available), and the standard library.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via existing `database/db.py` helpers only.
- Parameterised queries only — never f-strings in SQL.
- Passwords hashed with werkzeug — verify with `check_password_hash`; never compare plaintext, never store or log passwords.
- All DB access through `database/db.py` — no inline SQL in routes (reuse `get_user_by_email`).
- Use CSS variables — never hardcode hex values (any nav styling for the logged-in state must use existing variables).
- All templates extend `base.html`.
- Use `url_for()` for every internal link and form action.
- **Generic auth error:** on a wrong email *or* wrong password, show one identical message ("Invalid email or password.") — do not reveal which was wrong (avoids user enumeration).
- Normalize the submitted email with `.strip().lower()` before lookup, matching how registration stores it.
- Store only minimal data in the session (`user_id` and `name` for display) — never the password hash.
- `app.secret_key` from an environment variable with a dev fallback, so it is configurable without committing a real secret (no new pip package — use `os.environ`).

## Definition of done
- [ ] Registering a new account then submitting those exact credentials at `/login` logs the user in and redirects to the landing page.
- [ ] After login the navbar shows the user's name and a "Sign out" link instead of "Sign in" / "Get started".
- [ ] Wrong password (correct email) and unknown email both re-render `login.html` with the same generic "Invalid email or password." message and do **not** establish a session.
- [ ] On a failed login the submitted email stays pre-filled; the password is never echoed back.
- [ ] Visiting `/logout` clears the session, redirects to the landing page, and the navbar reverts to the logged-out links.
- [ ] The seeded demo user (`demo@spendly.com` / `demo123`) can log in successfully.
- [ ] The login form action and the navbar/footer links all resolve via `url_for()` (no hardcoded paths).
- [ ] `GET /login` still renders the form unchanged; the app starts on port 5001 with no console errors; existing tests still pass.
